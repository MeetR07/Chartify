import os
import sys
import unittest
import pandas as pd

# Ensure project root is on sys.path (fallback for python -m unittest invocations)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.chart_planner import ChartPlanner, SUPPORTED_CHARTS, build_unified_data_contract
import backend.charts as charts


class TestContractV11(unittest.TestCase):

    def test_chart_planner_enabled_charts(self):
        """Verify ChartPlanner.enabled_charts matches exactly the supported charts."""
        expected_charts = {
            "bar", "column", "horizontal_bar", "grouped_bar", "stacked_bar",
            "line", "multi_line", "area", "pie", "donut", "scatter", "histogram",
            "heatmap", "treemap", "lollipop", "waterfall", "funnel", "radar",
            "violin", "box", "kpi", "bubble", "pairplot",
        }
        self.assertEqual(ChartPlanner.enabled_charts, expected_charts)
        self.assertEqual(SUPPORTED_CHARTS, expected_charts)

    def test_contract_multi_line(self):
        """Test multi_line reads 'series' and 'x_categories' from contract."""
        sample_contract = {
            "contract_version": "1.1",
            "chart_type": "multi_line",
            "query": "Revenue and Profit over Quarters",
            "series": [
                {"name": "Revenue", "axis": "y", "data": [100.0, 150.0, 220.0, 310.0]},
                {"name": "Profit", "axis": "y", "data": [25.0, 40.0, 65.0, 95.0]}
            ],
            "axis_metadata": {
                "x_type": "categorical",
                "y_type": "numeric",
                "x_label": "Quarter",
                "y_label": "Amount ($)",
                "x_categories": ["Q1", "Q2", "Q3", "Q4"],
                "format": "currency"
            },
            "data_points": [
                {"label": "Q1", "val": 100.0, "raw_row": {"Quarter": "Q1", "Revenue": 100.0, "Profit": 25.0}},
                {"label": "Q2", "val": 150.0, "raw_row": {"Quarter": "Q2", "Revenue": 150.0, "Profit": 40.0}},
                {"label": "Q3", "val": 220.0, "raw_row": {"Quarter": "Q3", "Revenue": 220.0, "Profit": 65.0}},
                {"label": "Q4", "val": 310.0, "raw_row": {"Quarter": "Q4", "Revenue": 310.0, "Profit": 95.0}}
            ]
        }

        result = charts.generate_chart.invoke({
            "chart_type": "multi_line",
            "title": "Revenue & Profit by Quarter",
            "output_path": ":memory:",
            "unified_contract": sample_contract
        })

        self.assertTrue(result.startswith("data:image/png;base64,"))
        self.assertIsNotNone(charts.LAST_CHART_DATA)
        self.assertEqual(charts.LAST_CHART_DATA.get("series"), sample_contract["series"])
        self.assertEqual(len(charts.LAST_CHART_DATA["series"]), 2)

    def test_contract_grouped_bar(self):
        """Test grouped_bar reads 'series' and 'x_categories' from contract."""
        sample_contract = {
            "contract_version": "1.1",
            "chart_type": "grouped_bar",
            "query": "Sales and Target across Regions",
            "series": [
                {"name": "Sales", "axis": "y", "data": [85.0, 92.0, 78.0]},
                {"name": "Target", "axis": "y", "data": [80.0, 90.0, 85.0]}
            ],
            "axis_metadata": {
                "x_type": "categorical",
                "y_type": "numeric",
                "x_label": "Region",
                "y_label": "Units",
                "x_categories": ["North", "South", "East"]
            },
            "data_points": [
                {"label": "North", "val": 85.0, "raw_row": {"Region": "North", "Sales": 85.0, "Target": 80.0}},
                {"label": "South", "val": 92.0, "raw_row": {"Region": "South", "Sales": 92.0, "Target": 90.0}},
                {"label": "East", "val": 78.0, "raw_row": {"Region": "East", "Sales": 78.0, "Target": 85.0}}
            ]
        }

        result = charts.generate_chart.invoke({
            "chart_type": "grouped_bar",
            "title": "Regional Performance",
            "output_path": ":memory:",
            "unified_contract": sample_contract
        })

        self.assertTrue(result.startswith("data:image/png;base64,"))
        self.assertIsNotNone(charts.LAST_CHART_DATA)
        self.assertEqual(charts.LAST_CHART_DATA.get("series"), sample_contract["series"])
        self.assertEqual(len(charts.LAST_CHART_DATA["series"]), 2)

    def test_contract_stacked_bar(self):
        """Test stacked_bar reads 'series' and 'x_categories' from contract."""
        sample_contract = {
            "contract_version": "1.1",
            "chart_type": "stacked_bar",
            "query": "Product Tier Breakdown by Segment",
            "series": [
                {"name": "Tier 1", "axis": "y", "data": [45.0, 60.0]},
                {"name": "Tier 2", "axis": "y", "data": [30.0, 45.0]},
                {"name": "Tier 3", "axis": "y", "data": [15.0, 20.0]}
            ],
            "axis_metadata": {
                "x_type": "categorical",
                "y_type": "numeric",
                "x_label": "Segment",
                "y_label": "Accounts",
                "x_categories": ["Enterprise", "Mid-Market"]
            },
            "data_points": [
                {"label": "Enterprise", "val": 90.0, "raw_row": {"Segment": "Enterprise"}},
                {"label": "Mid-Market", "val": 125.0, "raw_row": {"Segment": "Mid-Market"}}
            ]
        }

        result = charts.generate_chart.invoke({
            "chart_type": "stacked_bar",
            "title": "Tier Breakdown by Segment",
            "output_path": ":memory:",
            "unified_contract": sample_contract
        })

        self.assertTrue(result.startswith("data:image/png;base64,"))
        self.assertIsNotNone(charts.LAST_CHART_DATA)
        self.assertEqual(charts.LAST_CHART_DATA.get("series"), sample_contract["series"])
        self.assertEqual(len(charts.LAST_CHART_DATA["series"]), 3)

    def test_contract_kpi(self):
        """Test kpi reads 'data_points' and currency from contract."""
        sample_contract = {
            "contract_version": "1.1",
            "chart_type": "kpi",
            "query": "Total Annual Recurring Revenue",
            "axis_metadata": {
                "format": "currency",
                "currency": "INR",
                "currency_symbol": "₹",
                "y_label": "Total ARR"
            },
            "data_points": [
                {
                    "label": "Total ARR",
                    "val": 14500000.0,
                    "raw_row": {"metric": "Total ARR", "val": 14500000.0}
                }
            ]
        }

        result = charts.generate_chart.invoke({
            "chart_type": "kpi",
            "title": "Total ARR",
            "output_path": ":memory:",
            "unified_contract": sample_contract
        })

        self.assertTrue(result.startswith("data:image/png;base64,"))
        self.assertIsNotNone(charts.LAST_CHART_DATA)
        self.assertEqual(charts.LAST_CHART_DATA.get("data_points"), sample_contract["data_points"])
        self.assertEqual(charts.LAST_CHART_DATA["data_points"][0]["val"], 14500000.0)

    def test_contract_heatmap(self):
        """Test heatmap reads 'matrix' (values, x_labels, y_labels) from contract."""
        sample_contract = {
            "contract_version": "1.1",
            "chart_type": "heatmap",
            "query": "Correlation / Cross-tabulation Matrix",
            "matrix": {
                "x_labels": ["Marketing", "Sales", "Support"],
                "y_labels": ["Q1", "Q2", "Q3"],
                "values": [
                    [10.5, 14.2, 8.1],
                    [12.0, 16.5, 9.4],
                    [15.1, 19.8, 11.2]
                ]
            },
            "axis_metadata": {
                "x_type": "categorical",
                "y_type": "categorical",
                "x_label": "Department",
                "y_label": "Quarter"
            },
            "data_points": [
                {"label": "Q1 x Marketing", "val": 10.5},
                {"label": "Q2 x Sales", "val": 16.5}
            ]
        }

        result = charts.generate_chart.invoke({
            "chart_type": "heatmap",
            "title": "Department Activity by Quarter",
            "output_path": ":memory:",
            "unified_contract": sample_contract
        })

        self.assertTrue(result.startswith("data:image/png;base64,"))
        self.assertIsNotNone(charts.LAST_CHART_DATA)
        self.assertEqual(charts.LAST_CHART_DATA.get("matrix"), sample_contract["matrix"])
        self.assertEqual(len(charts.LAST_CHART_DATA["matrix"]["values"]), 3)


if __name__ == "__main__":
    unittest.main()
