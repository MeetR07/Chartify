import re
import math
import hashlib
import logging
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np

try:
    from dateutil import parser as dateutil_parser
    HAS_DATEUTIL = True
except ImportError:
    dateutil_parser = None
    HAS_DATEUTIL = False

logger = logging.getLogger("chartify.profiler")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Configurable constants for large dataset performance
LARGE_DATASET_ROW_THRESHOLD = 50_000
PROFILER_SAMPLE_SIZE = 25_000

# Cache of dataset profiles keyed by dataframe fingerprint
_PROFILE_CACHE: Dict[str, Dict[str, Any]] = {}


def compute_df_fingerprint(df: pd.DataFrame) -> str:
    """Computes a fast, deterministic fingerprint for a DataFrame based on shape, columns, and head/tail data."""
    try:
        col_str = "_".join(str(c) for c in df.columns)
        shape_str = f"{len(df)}x{len(df.columns)}"
        head_bytes = pd.util.hash_pandas_object(df.head(5)).values.tobytes() if len(df) > 0 else b""
        tail_bytes = pd.util.hash_pandas_object(df.tail(5)).values.tobytes() if len(df) > 5 else b""
        h = hashlib.sha256(col_str.encode("utf-8") + shape_str.encode("utf-8") + head_bytes + tail_bytes)
        return h.hexdigest()
    except Exception:
        return f"df_{id(df)}_{len(df)}_{len(df.columns)}"


def normalize_col_name(col_name: str) -> str:
    """Normalizes a column name for matching: lowercase, alphanumeric and underscores only."""
    clean = re.sub(r"[^\w\s]", "", str(col_name).strip().lower())
    return re.sub(r"\s+", "_", clean)


def _is_excel_serial_date(series: pd.Series, col_name: str) -> bool:
    """Checks if numeric series represents Excel serial dates (approx 1982 to 2064)."""
    col_lower = str(col_name).lower()
    temporal_cues = ["date", "day", "time", "timestamp", "dob", "created", "updated", "period"]
    if not any(cue in col_lower for cue in temporal_cues):
        return False
    
    clean_series = pd.to_numeric(series.dropna(), errors="coerce").dropna()
    if len(clean_series) == 0:
        return False
    
    # 30000 = 1982-02-18, 60000 = 2064-05-18
    in_range = ((clean_series >= 30000) & (clean_series <= 60000)).mean()
    return in_range >= 0.85


def robust_date_detection(series: pd.Series, col_name: str) -> Tuple[bool, float]:
    """
    Robust Date Parsing Fallback Chain:
    1. Strict ISO-8601 (YYYY-MM-DD, YYYY-MM-DD HH:MM:SS)
    2. Common standard date formats (MM/DD/YYYY, DD/MM/YYYY)
    3. dateutil.parser with consistency checks
    4. Excel serial date detection
    Returns (is_datetime, confidence)
    """
    non_null = series.dropna()
    if len(non_null) == 0:
        return False, 0.0

    # If already native datetime
    if pd.api.types.is_datetime64_any_dtype(series):
        return True, 1.0

    # Check for Excel serial dates if numeric
    if pd.api.types.is_numeric_dtype(series):
        if _is_excel_serial_date(series, col_name):
            return True, 0.88
        # General numeric columns MUST NOT be auto-converted to dates
        return False, 0.0

    # For string/object columns, test on sample of up to 100 non-empty string values
    sample_vals = [str(v).strip() for v in non_null.head(100) if str(v).strip()]
    if not sample_vals:
        return False, 0.0

    # Quick filter: avoid pure single numbers or obvious non-dates
    digits_only = sum(1 for v in sample_vals if v.isdigit())
    if digits_only / len(sample_vals) > 0.5:
        # Check if year only (4 digits between 1900 and 2100)
        years = [int(v) for v in sample_vals if v.isdigit() and len(v) == 4 and 1900 <= int(v) <= 2100]
        if len(years) / len(sample_vals) >= 0.85:
            # Treated as year dimension
            return True, 0.90
        return False, 0.0

    # 1. Strict ISO-8601 regex
    iso_regex = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?$")
    iso_matches = sum(1 for v in sample_vals if iso_regex.match(v))
    iso_ratio = iso_matches / len(sample_vals)
    if iso_ratio >= 0.85:
        return True, 0.98

    # 2. Common standard formats regex (MM/DD/YYYY or DD/MM/YYYY)
    std_regex = re.compile(r"^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}(?:[ T]\d{1,2}:\d{2})?$")
    std_matches = sum(1 for v in sample_vals if std_regex.match(v))
    std_ratio = std_matches / len(sample_vals)
    if std_ratio >= 0.85:
        return True, 0.92

    # 3. dateutil fallback with strict confidence
    if HAS_DATEUTIL and dateutil_parser:
        parsed_count = 0
        for v in sample_vals:
            # Exclude very short or purely alphabetical non-month strings
            if len(v) < 6 and not any(m in v.lower() for m in ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]):
                continue
            try:
                dateutil_parser.parse(v, fuzzy=False)
                parsed_count += 1
            except Exception:
                pass

        ratio = parsed_count / len(sample_vals)
        if ratio >= 0.85:
            return True, round(ratio * 0.9, 2)
        elif ratio > 0.2:
            logger.warning(f"[DATE PARSE WARNING] Column '{col_name}' had mixed/low-confidence date values ({ratio*100:.1f}%), kept as text.")
            return False, round(ratio, 2)

    return False, 0.0


def infer_semantic_roles(
    col_name: str,
    logical_type: str,
    dtype_str: str,
    unique_count: int,
    total_count: int,
    unique_ratio: float,
    sample_values: List[Any],
    stats: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Infers semantic roles (measure, dimension, identifier, date, location, currency, quantity, count) with confidence scores."""
    roles = []
    col_lower = str(col_name).lower()
    norm_name = normalize_col_name(col_name)

    # 1. Identifier
    id_tokens = ["id", "uuid", "guid", "code", "key", "number", "no", "index"]
    has_id_token = any(token in norm_name.split("_") for token in id_tokens)
    if has_id_token and (unique_ratio > 0.85 or unique_count == total_count):
        roles.append({"role": "identifier", "confidence": 0.98})
    elif unique_ratio > 0.99 and total_count > 10 and logical_type in ["categorical", "text"]:
        roles.append({"role": "identifier", "confidence": 0.90})

    # 2. Date / Time
    if logical_type == "datetime":
        roles.append({"role": "date", "confidence": 0.98})
        if "year" in norm_name.split("_"):
            roles.append({"role": "year", "confidence": 0.99})
        if "month" in norm_name.split("_"):
            roles.append({"role": "month", "confidence": 0.99})

    # Year columns stored as numeric (e.g. 2015, 2020)
    if logical_type == "numeric" and ("year" in norm_name or norm_name == "yr"):
        min_v = stats.get("min", 0)
        max_v = stats.get("max", 0)
        if 1900 <= min_v <= 2100 and 1900 <= max_v <= 2100:
            roles.append({"role": "year", "confidence": 0.96})
            roles.append({"role": "dimension", "confidence": 0.94})

    # 3. Numeric Measure
    if logical_type == "numeric":
        currency_cues = ["price", "sales", "revenue", "cost", "profit", "amount", "salary", "expense", "budget", "fee", "val", "value", "gdp"]
        qty_cues = ["count", "quantity", "qty", "volume", "rooms", "beds", "units", "score", "rate", "percentage", "pct", "ratio", "age", "population"]

        is_currency = any(cue in norm_name for cue in currency_cues)
        is_qty = any(cue in norm_name for cue in qty_cues)

        base_measure_conf = 0.92
        if is_currency:
            roles.append({"role": "price", "confidence": 0.96})
            roles.append({"role": "measure", "confidence": 0.99})
        elif is_qty:
            roles.append({"role": "quantity", "confidence": 0.95})
            roles.append({"role": "measure", "confidence": 0.98})
        else:
            if not has_id_token:
                roles.append({"role": "measure", "confidence": base_measure_conf})

    # 4. Categorical Dimension
    if logical_type in ["categorical", "text", "boolean"]:
        dim_cues = ["category", "type", "group", "region", "city", "country", "state", "status", "name", "brand", "model", "segment", "department", "tier"]
        loc_cues = ["city", "country", "state", "region", "territory", "location", "address", "zip", "postal", "province", "continent"]

        is_loc = any(cue in norm_name for cue in loc_cues)
        if is_loc:
            roles.append({"role": "location", "confidence": 0.95})
            roles.append({"role": "dimension", "confidence": 0.98})
        elif any(cue in norm_name for cue in dim_cues):
            roles.append({"role": "dimension", "confidence": 0.97})
        elif unique_count <= 100:
            roles.append({"role": "dimension", "confidence": 0.90})
        else:
            roles.append({"role": "dimension", "confidence": 0.75})

    # Sort roles descending by confidence
    roles.sort(key=lambda r: r["confidence"], reverse=True)
    if not roles:
        fallback_role = "measure" if logical_type == "numeric" else "dimension"
        roles.append({"role": fallback_role, "confidence": 0.50})

    return roles


def profile_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Comprehensive Dataset Profiler Module:
    Produces a detailed, dataset-agnostic semantic schema for any uploaded DataFrame.
    """
    if df is None or not isinstance(df, pd.DataFrame):
        raise ValueError("Valid pandas DataFrame must be provided to profile_dataset")

    total_rows = len(df)
    total_cols = len(df.columns)

    # Check cache first
    fingerprint = compute_df_fingerprint(df)
    if fingerprint in _PROFILE_CACHE:
        return dict(_PROFILE_CACHE[fingerprint])

    # Sample subset for high-cost computations if dataset exceeds threshold
    is_large = total_rows > LARGE_DATASET_ROW_THRESHOLD
    calc_df = df.sample(PROFILER_SAMPLE_SIZE, random_state=42) if is_large else df

    column_profiles = []
    candidate_dims = []
    candidate_measures = []
    candidate_dates = []
    candidate_ids = []

    seen_normalized: Dict[str, int] = {}

    for col in df.columns:
        series = df[col]
        non_null_count = int(series.count())
        null_count = total_rows - non_null_count
        null_pct = round((null_count / total_rows * 100.0), 2) if total_rows > 0 else 0.0

        # Edge Case: All-null columns dropped from candidates
        if non_null_count == 0:
            logger.info(f"[COLUMN PROFILE] dropped: all-null column '{col}'")
            continue

        # Disambiguate duplicate normalized names
        base_norm = normalize_col_name(col) or "col"
        if base_norm in seen_normalized:
            seen_normalized[base_norm] += 1
            norm_alias = f"{base_norm}_{seen_normalized[base_norm]}"
            logger.info(f"[COLUMN PROFILE] disambiguated duplicate alias '{base_norm}' -> '{norm_alias}'")
        else:
            seen_normalized[base_norm] = 1
            norm_alias = base_norm

        dtype_str = str(series.dtype)

        # Unique count & ratio calculation
        if is_large:
            sample_series = calc_df[col].dropna()
            sample_unique = int(sample_series.nunique())
            sample_size = len(sample_series)
            unique_ratio = round(sample_unique / sample_size, 4) if sample_size > 0 else 0.0
            # Scaled estimate for total unique count
            estimated_unique = min(total_rows, max(sample_unique, int(sample_unique * (total_rows / max(sample_size, 1)) ** 0.5)))
            unique_count = estimated_unique
        else:
            unique_count = int(series.nunique())
            unique_ratio = round(unique_count / total_rows, 4) if total_rows > 0 else 0.0

        # Logical type detection & robust date parsing
        is_date, date_conf = robust_date_detection(calc_df[col], col)
        if is_date:
            logical_type = "datetime"
        elif pd.api.types.is_numeric_dtype(series):
            # Check if boolean represented as 0/1 with exactly 2 unique values
            if unique_count <= 2 and set(series.dropna().unique()).issubset({0, 1}):
                logical_type = "boolean"
            else:
                logical_type = "numeric"
        elif pd.api.types.is_bool_dtype(series):
            logical_type = "boolean"
        elif unique_ratio < 0.20 or unique_count <= 50:
            logical_type = "categorical"
        else:
            logical_type = "text"

        # Descriptive stats for numeric columns
        stats = {}
        if logical_type == "numeric":
            num_clean = pd.to_numeric(series.dropna(), errors="coerce").dropna()
            if len(num_clean) > 0:
                stats = {
                    "min": float(np.min(num_clean)),
                    "max": float(np.max(num_clean)),
                    "mean": float(round(np.mean(num_clean), 2)),
                    "median": float(round(np.median(num_clean), 2)),
                    "std": float(round(np.std(num_clean), 2)) if len(num_clean) > 1 else 0.0
                }

        # Representative sample values (up to 5 distinct clean values)
        clean_non_null = series.dropna()
        if logical_type in ["categorical", "text"]:
            top_frequent = clean_non_null.value_counts().head(5).index.tolist()
            sample_vals = [str(v) for v in top_frequent]
        elif logical_type == "numeric":
            sample_vals = [float(v) if isinstance(v, (int, float, np.number)) else v for v in clean_non_null.head(5).tolist()]
        else:
            sample_vals = [str(v) for v in clean_non_null.head(5).tolist()]

        # Anomaly detection
        anomalies = []
        if unique_count == 1:
            anomalies.append("constant_column")
        if null_pct > 50.0:
            anomalies.append("high_null_ratio")
        if logical_type in ["categorical", "text"] and unique_ratio > 0.95 and total_rows > 50:
            anomalies.append("high_cardinality_nominal")
        if logical_type == "text":
            # Check if numeric values stored as text
            num_coerced = pd.to_numeric(clean_non_null.head(50), errors="coerce")
            if num_coerced.notnull().mean() > 0.8:
                anomalies.append("numeric_stored_as_string")

        # Semantic roles inference
        semantic_roles = infer_semantic_roles(
            col_name=col,
            logical_type=logical_type,
            dtype_str=dtype_str,
            unique_count=unique_count,
            total_count=total_rows,
            unique_ratio=unique_ratio,
            sample_values=sample_vals,
            stats=stats
        )

        col_profile = {
            "column": col,
            "normalized_name": norm_alias,
            "dtype": dtype_str,
            "logical_type": logical_type,
            "total_rows": total_rows,
            "non_null_count": non_null_count,
            "null_count": null_count,
            "null_percentage": null_pct,
            "unique_count": unique_count,
            "unique_ratio": unique_ratio,
            "stats": stats,
            "sample_values": sample_vals,
            "anomalies": anomalies,
            "semantic_roles": semantic_roles
        }

        column_profiles.append(col_profile)

        # Categorize candidates for rapid schema lookup
        top_role = semantic_roles[0]["role"] if semantic_roles else ""
        if any(r["role"] == "identifier" and r["confidence"] >= 0.85 for r in semantic_roles):
            candidate_ids.append(col)
        if any(r["role"] in ["date", "year", "month"] and r["confidence"] >= 0.80 for r in semantic_roles):
            candidate_dates.append(col)
        if any(r["role"] in ["measure", "price", "quantity"] and r["confidence"] >= 0.70 for r in semantic_roles):
            candidate_measures.append(col)
        if any(r["role"] in ["dimension", "location"] and r["confidence"] >= 0.70 for r in semantic_roles) or logical_type in ["categorical", "boolean"]:
            candidate_dims.append(col)

        roles_summary = ", ".join(f"'{r['role']}': {r['confidence']}" for r in semantic_roles[:2])
        logger.info(
            f"[COLUMN PROFILE] col=\"{col}\", dtype={dtype_str}, logical=\"{logical_type}\", roles={{{roles_summary}}}"
        )

    schema = {
        "dataset_fingerprint": fingerprint,
        "row_count": total_rows,
        "column_count": len(column_profiles),
        "columns": [cp["column"] for cp in column_profiles],
        "column_profiles": column_profiles,
        "candidate_dimensions": candidate_dims,
        "candidate_measures": candidate_measures,
        "candidate_dates": candidate_dates,
        "candidate_identifiers": candidate_ids
    }

    logger.info(f"[DATASET PROFILE] rows={total_rows}, cols={len(column_profiles)}, candidates(dims={len(candidate_dims)}, measures={len(candidate_measures)}, dates={len(candidate_dates)})")

    _PROFILE_CACHE[fingerprint] = schema
    return schema


def get_dataset_schema(df: pd.DataFrame) -> Dict[str, Any]:
    """Retrieves cached semantic schema or profiles dataset immediately."""
    fp = compute_df_fingerprint(df)
    if fp in _PROFILE_CACHE:
        return _PROFILE_CACHE[fp]
    return profile_dataset(df)


def clear_profile_cache() -> None:
    """Clears all cached dataset profiles."""
    global _PROFILE_CACHE
    _PROFILE_CACHE.clear()
