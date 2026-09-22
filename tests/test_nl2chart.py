import os
import sys
import unittest
import pandas as pd
import numpy as np

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from profiler import profile_dataset, robust_date_detection
from planner import (
    check_column_ambiguity,
    RuleBasedFallbackPlanner,
    PlanValidator,
    LLMQueryPlanner
)
from engine import DeterministicDataEngine, ResultValidator, compute_data_signature
from chart_planner import ChartPlanner, build_unified_data_contract


class TestNL2ChartUniversalEngine(unittest.TestCase):

    def setUp(self):
        # Sample dataset 1: Retail Sales & Profit
        self.retail_df = pd.DataFrame({
            "Month": ["Jan", "Feb", "Mar", "Apr", "May"],
            "Sales": [15000, 22000, 18000, 27000, 31000],
            "Profit": [3000, 4500, -1200, 6000, 7500],
            "Region": ["North", "South", "North", "West", "South"]
        })

        # Sample dataset 2: Customers & Cities
        self.cust_df = pd.DataFrame({
            "customer_id": ["C1", "C2", "C3", "C4", "C5", "C6"],
            "city": ["New York", "London", "New York", "Tokyo", "London", "London"],
            "revenue": [1000.0, 1500.0, 2500.0, 3000.0, 500.0, 2000.0]
        })

        # Sample dataset 3: Housing Rooms
        self.housing_df = pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "total_rooms": [120, 85, 340, 210, 95],
            "neighborhood": ["A", "B", "C", "D", "E"]
        })

    # ==========================================================================
    # 1. GOLDEN TESTS
    # ==========================================================================

    def test_golden_city_customers_count(self):
        """Query: 'how many customers by city' -> group by city, count"""
        schema = profile_dataset(self.cust_df)
        plan, _ = LLMQueryPlanner.generate_plan("how many customers by city", self.cust_df)

        self.assertFalse(plan.get("clarification_needed", False))
        self.assertEqual(plan["steps"][0]["group_by"], ["city"])
        self.assertEqual(plan["steps"][0]["aggregation"], "count")

        result_df, meta = DeterministicDataEngine.execute_plan(self.cust_df, plan)
        self.assertTrue(len(result_df) > 0)
        self.assertIn("city", result_df.columns)
        self.assertIn("count", result_df.columns)
        # London has 3 customers
        london_row = result_df[result_df["city"] == "London"]
        self.assertEqual(int(london_row["count"].iloc[0]), 3)

    def test_golden_total_revenue_by_city(self):
        """Query: 'total revenue by city' -> group by city, sum(revenue)"""
        plan, _ = LLMQueryPlanner.generate_plan("total revenue by city", self.cust_df)
        self.assertEqual(plan["steps"][0]["group_by"], ["city"])
        self.assertEqual(plan["steps"][0]["target_column"], "revenue")
        self.assertEqual(plan["steps"][0]["aggregation"], "sum")

        result_df, meta = DeterministicDataEngine.execute_plan(self.cust_df, plan)
        self.assertTrue(len(result_df) > 0)
        ny_row = result_df[result_df["city"] == "New York"]
        self.assertEqual(float(ny_row["revenue"].iloc[0]), 3500.0)

    def test_golden_highest_total_rooms(self):
        """Query: 'highest total_rooms' -> sort desc, no phantom group"""
        plan, _ = LLMQueryPlanner.generate_plan("highest total_rooms", self.housing_df)
        self.assertEqual(plan["sort"]["column"], "total_rooms")
        self.assertEqual(plan["sort"]["direction"], "desc")
        self.assertEqual(plan["steps"], [])  # no grouping!

        result_df, meta = DeterministicDataEngine.execute_plan(self.housing_df, plan)
        self.assertEqual(int(result_df["total_rooms"].iloc[0]), 340)

    def test_golden_chronological_month_sorting(self):
        """Query: 'profit by month' -> chronological sorting on months"""
        # Shuffle months to test non-alphabetical sort
        shuffled = self.retail_df.sample(frac=1.0, random_state=123).reset_index(drop=True)
        plan, _ = LLMQueryPlanner.generate_plan("profit by month", shuffled)
        result_df, meta = DeterministicDataEngine.execute_plan(shuffled, plan)

        # First month must be Jan, second Feb, third Mar
        months = result_df["Month"].tolist()
        self.assertEqual(months[0], "Jan")
        self.assertEqual(months[1], "Feb")
        self.assertEqual(months[2], "Mar")

    def test_golden_top_n_after_aggregation(self):
        """Query: 'top 2 cities by revenue' -> group, sum, limit 2"""
        plan, _ = LLMQueryPlanner.generate_plan("top 2 city by revenue", self.cust_df)
        result_df, meta = DeterministicDataEngine.execute_plan(self.cust_df, plan)
        self.assertEqual(len(result_df), 2)
        # London (4000) and New York (3500)
        self.assertEqual(result_df["city"].iloc[0], "London")
        self.assertEqual(result_df["city"].iloc[1], "New York")

    # ==========================================================================
    # 2. ADVERSARIAL & AMBIGUITY TESTS
    # ==========================================================================

    def test_ambiguity_detection_multiple_sales(self):
        """Ambiguity: dataset with Sales and Sale Price, query: 'Show sales'"""
        df_multi = pd.DataFrame({
            "Category": ["A", "B"],
            "Sales": [100, 200],
            "Sale Price": [10, 20]
        })
        schema = profile_dataset(df_multi)
        is_ambig, candidates, msg = check_column_ambiguity("Show sales", schema)
        self.assertTrue(is_ambig)
        self.assertIn("Sales", candidates)
        self.assertIn("Sale Price", candidates)
        self.assertIn("Which column would you like to visualize?", msg)

    def test_adversarial_single_numeric_column(self):
        """Adversarial: 1-column dataset with query 'highest value'"""
        single_df = pd.DataFrame({"value": [10, 50, 30, 90, 20]})
        plan, _ = LLMQueryPlanner.generate_plan("highest value", single_df)
        result_df, meta = DeterministicDataEngine.execute_plan(single_df, plan)
        self.assertEqual(result_df["value"].iloc[0], 90)

    # ==========================================================================
    # 3. EDGE CASES TESTS
    # ==========================================================================

    def test_edge_case_division_by_zero_percentage(self):
        """Edge Case: Percentage on column whose sum is 0"""
        zero_df = pd.DataFrame({
            "category": ["A", "B"],
            "metric": [0.0, 0.0]
        })
        plan = {
            "intent": "share",
            "steps": [{"operation": "percentage", "target_column": "metric"}]
        }
        result_df, meta = DeterministicDataEngine.execute_plan(zero_df, plan)
        self.assertIn("metric_pct", result_df.columns)
        self.assertEqual(result_df["metric_pct"].tolist(), [0.0, 0.0])
        self.assertFalse(np.isnan(result_df["metric_pct"]).any())

    def test_edge_case_zero_rows_after_filter(self):
        """Edge Case: Filter matches 0 rows"""
        plan = {
            "filters": [{"column": "Region", "operator": "eq", "value": "NonExistent"}]
        }
        result_df, meta = DeterministicDataEngine.execute_plan(self.retail_df, plan)
        self.assertEqual(len(result_df), 0)
        valid, msg = ResultValidator.validate(result_df, plan, meta)
        self.assertTrue(valid)
        self.assertIn("No records match", msg)

    def test_edge_case_all_null_column_dropped(self):
        """Edge Case: Column with 100% null values dropped from schema candidates"""
        null_df = pd.DataFrame({
            "A": [1, 2, 3],
            "all_empty": [None, None, None]
        })
        schema = profile_dataset(null_df)
        self.assertNotIn("all_empty", schema["columns"])
        self.assertIn("A", schema["columns"])

    def test_edge_case_duplicate_normalized_names(self):
        """Edge Case: 'Sale Price' and 'sale_price' disambiguated"""
        dup_df = pd.DataFrame({
            "Sale Price": [10, 20],
            "sale_price": [15, 25]
        })
        schema = profile_dataset(dup_df)
        aliases = [cp["normalized_name"] for cp in schema["column_profiles"]]
        self.assertEqual(len(set(aliases)), 2)
        self.assertIn("sale_price", aliases)
        self.assertIn("sale_price_2", aliases)

    # ==========================================================================
    # 4. CHART CONFLICT RESOLUTION TESTS
    # ==========================================================================

    def test_chart_conflict_pie_high_cardinality(self):
        """Conflict Resolution: Pie requested with 12 categories -> auto fallback to bar"""
        df_12 = pd.DataFrame({
            "Category": [f"Cat {i}" for i in range(12)],
            "Value": list(range(1, 13))
        })
        plan = {
            "chart_request": {"explicit": True, "type": "pie"},
            "intent": "comparison"
        }
        meta = {"primary_group_col": "Category", "primary_metric_col": "Value"}
        chosen_chart, note = ChartPlanner.select_and_validate_chart(df_12, plan, meta)
        self.assertEqual(chosen_chart, "bar")
        self.assertIsNotNone(note)
        self.assertIn("Switched from pie to bar chart", note)

    # ==========================================================================
    # 5. 2D / 3D SINGLE SOURCE OF TRUTH & SIGNATURE TESTS
    # ==========================================================================

    def test_unified_contract_data_signature(self):
        """2D/3D Parity: Unified data contract produces consistent cryptographic signature"""
        plan = {"explanation": "Total sales by region", "intent": "aggregation"}
        exec_meta = {"primary_group_col": "Region", "primary_metric_col": "Sales"}
        contract1 = build_unified_data_contract(self.retail_df, plan, exec_meta, "bar")
        contract2 = build_unified_data_contract(self.retail_df, plan, exec_meta, "bar")

        self.assertEqual(contract1["data_signature"], contract2["data_signature"])
        self.assertTrue(contract1["data_signature"].startswith("sha256:"))
        self.assertEqual(len(contract1["data_points"]), len(self.retail_df))

    def test_vertical_bar_column_chart_selection(self):
        """User request for vertical bar / column chart selects column type"""
        plan, _ = LLMQueryPlanner.generate_plan("vertical bar chart of sales by region", self.retail_df)
        self.assertEqual(plan["chart_request"]["type"], "column")
        res_df, exec_meta = DeterministicDataEngine.execute_plan(self.retail_df, plan)
        chart_type, _ = ChartPlanner.select_and_validate_chart(res_df, plan, exec_meta)
        self.assertEqual(chart_type, "column")


if __name__ == "__main__":
    unittest.main()
