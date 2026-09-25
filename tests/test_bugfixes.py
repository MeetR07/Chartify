import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from server import app, CHARTS_CACHE_DIR

client = TestClient(app)


class TestBugFixes(unittest.TestCase):

    def setUp(self):
        # Ensure a dummy valid chart exists in CHARTS_CACHE_DIR for positive testing
        os.makedirs(CHARTS_CACHE_DIR, exist_ok=True)
        self.dummy_chart_name = "test_valid_chart.png"
        self.dummy_chart_path = os.path.join(CHARTS_CACHE_DIR, self.dummy_chart_name)
        with open(self.dummy_chart_path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4")

    def tearDown(self):
        if os.path.exists(self.dummy_chart_path):
            try:
                os.remove(self.dummy_chart_path)
            except Exception:
                pass

    # =========================================================================
    # BUG-01: Path Traversal / Arbitrary File Read in /api/charts/{filename}
    # =========================================================================

    def test_bug_01_path_traversal_dot_env(self):
        """BUG-01 Repro: Attempting to read .env file directly via /api/charts/.env must NOT return 200."""
        res = client.get("/api/charts/.env")
        # Under the bug, this returns 200 and exposes API keys in .env
        self.assertIn(res.status_code, [400, 403, 404], f"Vulnerability reproduced: Server returned {res.status_code} with body: {res.text[:100]}")

    def test_bug_01_path_traversal_variants(self):
        """BUG-01 Repro: Test encoded, Windows-style (..\\), and absolute paths."""
        traversal_attempts = [
            "/api/charts/..%2f.env",
            "/api/charts/%2e%2e%2f.env",
            r"/api/charts/..\.env",
            "/api/charts/C:/Windows/win.ini",
            "/api/charts/server.py",
        ]
        for url in traversal_attempts:
            res = client.get(url)
            self.assertIn(
                res.status_code,
                [400, 403, 404],
                f"Path traversal variant {url} succeeded with {res.status_code}: {res.text[:60]}"
            )

    def test_bug_01_legitimate_chart_access(self):
        """Legitimate chart in CHARTS_CACHE_DIR must succeed with 200."""
        res = client.get(f"/api/charts/{self.dummy_chart_name}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["content-type"], "image/png")

    # =========================================================================
    # BUG-02: Arbitrary File Write / Path Traversal in /api/save-chart & /api/export-to-downloads
    # =========================================================================

    def test_bug_02_arbitrary_file_write_save_chart(self):
        """BUG-02 Repro: Traversal in /api/save-chart must NOT escape CHARTS_CACHE_DIR."""
        escaped_file = os.path.join(os.getcwd(), "bug02_escape_save.png")
        if os.path.exists(escaped_file):
            os.remove(escaped_file)

        b64_pixel = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        try:
            res = client.post("/api/save-chart", json={
                "filename": "../bug02_escape_save.png",
                "image_data": b64_pixel
            })
            # Under the bug, the file was written to os.getcwd() (outside CHARTS_CACHE_DIR)
            self.assertFalse(
                os.path.exists(escaped_file),
                f"Vulnerability reproduced: File was written outside CHARTS_CACHE_DIR at {escaped_file}"
            )
        finally:
            if os.path.exists(escaped_file):
                os.remove(escaped_file)

    def test_bug_02_arbitrary_file_write_export_to_downloads_traversal_variants(self):
        """BUG-02 Repro: Test encoded, Windows-style (..\\), and absolute paths in export-to-downloads."""
        b64_pixel = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        escaped_project_file = os.path.join(os.getcwd(), "bug02_downloads_escape.png")
        if os.path.exists(escaped_project_file):
            os.remove(escaped_project_file)

        traversal_filenames = [
            "../bug02_downloads_escape.png",
            r"..\bug02_downloads_escape.png",
            "%2e%2e%2fbug02_downloads_escape.png",
            "C:/bug02_downloads_escape.png",
        ]

        try:
            for fn in traversal_filenames:
                res = client.post("/api/export-to-downloads", json={
                    "filename": fn,
                    "image_data": b64_pixel
                })
                self.assertFalse(
                    os.path.exists(escaped_project_file),
                    f"Vulnerability reproduced: Traversal variant '{fn}' wrote outside allowed directory!"
                )
        finally:
            if os.path.exists(escaped_project_file):
                os.remove(escaped_project_file)

    def test_bug_02_download_endpoint_traversal_blocked(self):
        """BUG-02: /api/charts/download/{filename} must reject traversal paths."""
        traversal_attempts = [
            "/api/charts/download/..%2f..%2fserver.py",
            r"/api/charts/download/..\..\server.py",
            "/api/charts/download/%2e%2e%2f%2e%2e%2fserver.py",
        ]
        for url in traversal_attempts:
            res = client.get(url)
            self.assertIn(
                res.status_code,
                [400, 403, 404],
                f"Path traversal variant {url} on download endpoint returned {res.status_code}"
            )

    # =========================================================================
    # BUG-03: MONTH_CHRONO_ORDER missing 'may' in full month names
    # =========================================================================

    def test_bug_03_month_chrono_order_contains_may_in_full_names(self):
        """BUG-03: MONTH_CHRONO_ORDER must have 24 elements with 'may' at index 16 between april and june."""
        import engine
        self.assertEqual(
            len(engine.MONTH_CHRONO_ORDER),
            24,
            f"Expected 24 month names (12 short + 12 full), got {len(engine.MONTH_CHRONO_ORDER)}"
        )
        self.assertEqual(engine.MONTH_CHRONO_ORDER[16], "may")

    def test_bug_03_sort_chronologically_full_month_order(self):
        """BUG-03: sort_chronologically must sort 'May' before 'June' and all 12 full months in order."""
        import pandas as pd
        from engine import sort_chronologically

        # Case 1: June and May inverted
        df_june_may = pd.DataFrame({
            "month": ["June", "May"],
            "revenue": [200, 100]
        })
        sorted_jm = sort_chronologically(df_june_may, "month")
        self.assertEqual(
            sorted_jm["month"].tolist(),
            ["May", "June"],
            f"Expected ['May', 'June'], got {sorted_jm['month'].tolist()}"
        )

        # Case 2: All 12 months in reverse order
        full_months_rev = [
            "December", "November", "October", "September", "August", "July",
            "June", "May", "April", "March", "February", "January"
        ]
        expected_order = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        df_all = pd.DataFrame({
            "month": full_months_rev,
            "sales": range(12)
        })
        sorted_all = sort_chronologically(df_all, "month")
        self.assertEqual(
            sorted_all["month"].tolist(),
            expected_order,
            f"Full months were not sorted chronologically: got {sorted_all['month'].tolist()}"
        )

    def test_bug_03_short_and_full_month_keys_match(self):
        """BUG-03: Each short and full month pair must have the exact same chrono key index."""
        import engine
        month_map = {m: i % 12 for i, m in enumerate(engine.MONTH_CHRONO_ORDER)}
        pairs = [
            ("jan", "january", 0),
            ("feb", "february", 1),
            ("mar", "march", 2),
            ("apr", "april", 3),
            ("may", "may", 4),
            ("jun", "june", 5),
            ("jul", "july", 6),
            ("aug", "august", 7),
            ("sep", "september", 8),
            ("oct", "october", 9),
            ("nov", "november", 10),
            ("dec", "december", 11),
        ]
        for short_m, full_m, expected_idx in pairs:
            self.assertEqual(
                month_map.get(short_m),
                expected_idx,
                f"Short month '{short_m}' key expected {expected_idx}, got {month_map.get(short_m)}"
            )
            self.assertEqual(
                month_map.get(full_m),
                expected_idx,
                f"Full month '{full_m}' key expected {expected_idx}, got {month_map.get(full_m)}"
            )

    # =========================================================================
    # BUG-04: planner.py PlanValidator crash on empty valid_cols
    # =========================================================================

    def test_bug_04_plan_validator_empty_valid_cols_target_column(self):
        """BUG-04: PlanValidator must not crash with ValueError when valid_cols is empty for target_column."""
        from planner import PlanValidator

        empty_schema = {"columns": [], "column_profiles": []}
        plan_with_target = {
            "steps": [{"operation": "group_aggregate", "target_column": "sales"}]
        }
        # In unpatched code, this raises ValueError: max() arg is an empty sequence
        valid, msg, fix = PlanValidator.validate_plan(plan_with_target, empty_schema)
        self.assertFalse(valid)
        self.assertIn("does not exist", msg)
        self.assertIsNone(fix)

    def test_bug_04_plan_validator_empty_valid_cols_group_by(self):
        """BUG-04: PlanValidator must not crash with ValueError when valid_cols is empty for group_by."""
        from planner import PlanValidator

        empty_schema = {"columns": [], "column_profiles": []}
        plan_with_groupby = {
            "steps": [{"operation": "group_aggregate", "group_by": ["city"]}]
        }
        valid, msg, fix = PlanValidator.validate_plan(plan_with_groupby, empty_schema)
        self.assertFalse(valid)
        self.assertIn("does not exist", msg)
        self.assertIsNone(fix)

    def test_bug_04_plan_validator_empty_valid_cols_filters(self):
        """BUG-04: PlanValidator must not crash with ValueError when valid_cols is empty for filters."""
        from planner import PlanValidator

        empty_schema = {"columns": [], "column_profiles": []}
        plan_with_filter = {
            "filters": [{"column": "status", "operator": "eq", "value": "active"}]
        }
        valid, msg, fix = PlanValidator.validate_plan(plan_with_filter, empty_schema)
        self.assertFalse(valid)
        self.assertIn("does not exist", msg)
        self.assertIsNone(fix)

    # =========================================================================
    # BUG-06: server.py cache_key missing dataset_fingerprint
    # =========================================================================

    def test_bug_06_cache_key_includes_dataset_fingerprint(self):
        """BUG-06: /api/generate-chart cache must not return stale results across different datasets."""
        import pandas as pd
        import main
        from server import LLM_CACHE

        original_df = main.df
        try:
            LLM_CACHE.clear()

            # Dataset 1: Paris and London
            main.df = pd.DataFrame({"city": ["Paris", "London"], "revenue": [100.0, 200.0]})
            res1 = client.post("/api/generate-chart", json={"query": "total revenue by city"})
            self.assertEqual(res1.status_code, 200)
            data1 = res1.json()
            sig1 = data1.get("data_signature")
            labels1 = [pt["label"] for pt in data1.get("chart_data", {}).get("data_points", [])]
            self.assertIn("Paris", labels1)

            # Dataset 2: Tokyo and Seoul (same query, completely different dataset)
            main.df = pd.DataFrame({"city": ["Tokyo", "Seoul"], "revenue": [500.0, 600.0]})
            res2 = client.post("/api/generate-chart", json={"query": "total revenue by city"})
            self.assertEqual(res2.status_code, 200)
            data2 = res2.json()
            sig2 = data2.get("data_signature")
            labels2 = [pt["label"] for pt in data2.get("chart_data", {}).get("data_points", [])]

            # Under the bug, cache_key does not include dataset fingerprint, so res2 returns data1 (Paris/London)
            self.assertNotEqual(
                sig1,
                sig2,
                "BUG-06 Reproduced: Dataset 2 returned identical data signature as Dataset 1 from cache collision!"
            )
            self.assertIn("Tokyo", labels2)
            self.assertNotIn("Paris", labels2)
        finally:
            main.df = original_df
            LLM_CACHE.clear()

    # =========================================================================
    # BUG-08: server.py unbounded file upload (needs MAX_UPLOAD_SIZE = 50MB guard)
    # =========================================================================

    def test_bug_08_max_upload_size_constant_defined(self):
        """BUG-08: server must define MAX_UPLOAD_SIZE equal to 50MB."""
        import server
        self.assertTrue(
            hasattr(server, "MAX_UPLOAD_SIZE"),
            "server.py must define MAX_UPLOAD_SIZE constant"
        )
        self.assertEqual(
            server.MAX_UPLOAD_SIZE,
            50 * 1024 * 1024,
            "MAX_UPLOAD_SIZE must be set to 50MB (52428800 bytes)"
        )

    def test_bug_08_upload_csv_exceeding_max_size_rejected_with_413(self):
        """BUG-08: /api/upload-csv must reject files larger than MAX_UPLOAD_SIZE with HTTP 413."""
        import io
        import server

        orig_max = getattr(server, "MAX_UPLOAD_SIZE", None)
        try:
            server.MAX_UPLOAD_SIZE = 1000  # 1 KB limit for fast unit test
            oversized_payload = b"col1,col2\n" + (b"val1,val2\n" * 100)  # > 1000 bytes
            res = client.post(
                "/api/upload-csv",
                files={"file": ("test_huge.csv", io.BytesIO(oversized_payload), "text/csv")}
            )
            self.assertEqual(
                res.status_code,
                413,
                f"Expected HTTP 413 Payload Too Large for oversized file, got {res.status_code}: {res.text}"
            )
        finally:
            if orig_max is not None:
                server.MAX_UPLOAD_SIZE = orig_max
            elif hasattr(server, "MAX_UPLOAD_SIZE"):
                delattr(server, "MAX_UPLOAD_SIZE")

    # =========================================================================
    # BUG-07: server.py unbounded SESSION_STORE dictionary
    # =========================================================================

    def test_bug_07_session_store_is_bounded_lru_cache(self):
        """BUG-07: SESSION_STORE must be a ScalableLRUCache with maxsize=1000 and ttl=7200."""
        import server
        self.assertTrue(
            hasattr(server, "ScalableLRUCache"),
            "server must define ScalableLRUCache"
        )
        self.assertIsInstance(
            server.SESSION_STORE,
            server.ScalableLRUCache,
            f"SESSION_STORE should be ScalableLRUCache, got {type(server.SESSION_STORE)}"
        )
        self.assertEqual(server.SESSION_STORE.maxsize, 1000)
        self.assertEqual(server.SESSION_STORE.ttl, 7200)

    def test_bug_07_session_store_evicts_at_maxsize(self):
        """BUG-07: SESSION_STORE must evict oldest items when maxsize is exceeded."""
        import server
        server.SESSION_STORE.clear()
        try:
            # Insert 1005 items
            for i in range(1005):
                server.SESSION_STORE[f"session_{i}"] = {"last_query": f"query_{i}"}

            # Size must be strictly capped at maxsize (1000)
            cache_len = len(server.SESSION_STORE.cache) if hasattr(server.SESSION_STORE, "cache") else len(server.SESSION_STORE)
            self.assertLessEqual(cache_len, 1000)
            # Oldest items (session_0 to session_4) must have been evicted
            self.assertNotIn("session_0", server.SESSION_STORE)
            self.assertNotIn("session_4", server.SESSION_STORE)
            # Newest items must be present
            self.assertIn("session_1004", server.SESSION_STORE)
        finally:
            server.SESSION_STORE.clear()

    def test_bug_07_session_store_get_supports_default(self):
        """BUG-07: ScalableLRUCache.get must support a default parameter like dict.get(key, default)."""
        import server
        server.SESSION_STORE.clear()
        try:
            fallback = {"dummy": "data"}
            res = server.SESSION_STORE.get("non_existent_session_id", fallback)
            self.assertEqual(res, fallback)
        finally:
            server.SESSION_STORE.clear()

    # =========================================================================
    # BUG-05: server.py CORS allow_origins=["*"] with allow_credentials=True
    # =========================================================================

    def test_bug_05_cors_does_not_combine_wildcard_with_credentials(self):
        """BUG-05: CORS must not allow wildcard '*' when allow_credentials=True."""
        from fastapi.middleware.cors import CORSMiddleware
        import server

        cors_mw = next((m for m in server.app.user_middleware if m.cls == CORSMiddleware), None)
        self.assertIsNotNone(cors_mw, "CORSMiddleware must be installed")
        if cors_mw.kwargs.get("allow_credentials"):
            origins = cors_mw.kwargs.get("allow_origins", [])
            self.assertNotIn(
                "*",
                origins,
                "Insecure CORS: allow_origins cannot contain '*' when allow_credentials=True!"
            )

    def test_bug_05_cors_blocks_untrusted_origins(self):
        """BUG-05: CORS preflight must not reflect arbitrary untrusted origins with credentials."""
        res = client.options("/api/dataset", headers={
            "Origin": "http://evil-attacker-site.com",
            "Access-Control-Request-Method": "GET"
        })
        allowed_origin = res.headers.get("access-control-allow-origin")
        self.assertNotEqual(
            allowed_origin,
            "http://evil-attacker-site.com",
            "CORS vulnerability: Arbitrary untrusted origin allowed with credentials!"
        )

    def test_bug_05_cors_allows_trusted_frontend(self):
        """BUG-05: CORS preflight must allow legitimate frontend (localhost:5173)."""
        res = client.options("/api/dataset", headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET"
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("access-control-allow-origin"), "http://localhost:5173")
        self.assertEqual(res.headers.get("access-control-allow-credentials"), "true")

    # =========================================================================
    # BUG-10: engine.py unhandled TypeError in filter comparisons (gt, lt, gte, lte)
    # =========================================================================

    def test_bug_10_engine_filter_type_error_string_column_numeric_gt(self):
        """BUG-10: Comparing string column with numeric value in gt/lt must not raise unhandled TypeError."""
        import pandas as pd
        from engine import DeterministicDataEngine

        df = pd.DataFrame({"city": ["Paris", "London"], "revenue": [100, 200]})
        plan = {
            "steps": [{"operation": "group_aggregate", "group_by": ["city"], "target_column": "revenue", "aggregation": "sum"}],
            "filters": [{"column": "city", "operator": "gt", "value": 100}]
        }
        # In unpatched code, raises TypeError: '>' not supported between instances of 'str' and 'int'
        res_df, meta = DeterministicDataEngine.execute_plan(df, plan)
        self.assertIsNotNone(res_df)
        self.assertTrue(any("Incompatible" in w for w in meta.get("warnings", [])))

    def test_bug_10_engine_filter_type_error_numeric_column_string_gt(self):
        """BUG-10: Comparing numeric column with non-numeric string value in gt/lt must not raise TypeError."""
        import pandas as pd
        from engine import DeterministicDataEngine

        df = pd.DataFrame({"city": ["Paris", "London"], "revenue": [100, 200]})
        plan = {
            "steps": [{"operation": "group_aggregate", "group_by": ["city"], "target_column": "revenue", "aggregation": "sum"}],
            "filters": [{"column": "revenue", "operator": "gt", "value": "invalid_string"}]
        }
        # In unpatched code, raises TypeError: '>' not supported between instances of 'int' and 'str'
        res_df, meta = DeterministicDataEngine.execute_plan(df, plan)
        self.assertIsNotNone(res_df)
        self.assertTrue(any("Incompatible" in w for w in meta.get("warnings", [])))

    def test_bug_10_engine_filter_numeric_string_coercion_gt(self):
        """BUG-10: Numeric strings in column should be coerced and filtered safely without error."""
        import pandas as pd
        from engine import DeterministicDataEngine

        df = pd.DataFrame({"item": ["A", "B", "C"], "score_str": ["10", "50", "100"]})
        plan = {
            "steps": [],
            "filters": [{"column": "score_str", "operator": "gt", "value": 25}]
        }
        res_df, meta = DeterministicDataEngine.execute_plan(df, plan)
        self.assertEqual(len(res_df), 2)
        self.assertEqual(res_df["item"].tolist(), ["B", "C"])

    # =========================================================================
    # BUG-09: frontend/src/App.jsx export & chart download endpoints missing API_BASE
    # =========================================================================

    def test_bug_09_frontend_export_endpoints_use_api_base(self):
        """BUG-09: Export and chart download endpoints in App.jsx must use ${API_BASE} prefix."""
        app_jsx_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "src", "App.jsx")
        self.assertTrue(os.path.isfile(app_jsx_path), "App.jsx must exist")
        with open(app_jsx_path, "r", encoding="utf-8") as f:
            content = f.read()

        # In unpatched code:
        # fetch('/api/export-to-downloads', ...
        # link.href = url.startsWith('data:') ? url : `/api/charts/download/${encodeURIComponent(filename)}`;
        self.assertNotIn(
            "fetch('/api/export-to-downloads'",
            content,
            "BUG-09: Hardcoded relative path '/api/export-to-downloads' lacks ${API_BASE} prefix!"
        )
        self.assertNotIn(
            ": `/api/charts/download/",
            content,
            "BUG-09: Hardcoded relative path `/api/charts/download/` lacks ${API_BASE} prefix!"
        )
        self.assertIn(
            "${API_BASE}/api/export-to-downloads",
            content,
            "BUG-09: Export endpoint must be prefixed with ${API_BASE}"
        )
        self.assertIn(
            "${API_BASE}/api/charts/download/",
            content,
            "BUG-09: Chart download endpoint must be prefixed with ${API_BASE}"
        )


if __name__ == "__main__":
    unittest.main()


