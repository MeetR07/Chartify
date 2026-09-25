import os
import sys
import unittest
from fastapi.testclient import TestClient

# Ensure project root is on sys.path (fallback for python -m unittest invocations)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from server import app
import backend.charts as charts

client = TestClient(app)


class TestSurpriseMeAndApplyStyle(unittest.TestCase):

    def test_apply_style_with_contract_preservation(self):
        """Verify /api/apply-style preserves contract metadata and generates valid 2D PNG."""
        sample_contract = {
            "contract_version": "1.1",
            "chart_type": "kpi",
            "query": "Total Customer Acquisition Cost",
            "axis_metadata": {
                "x_type": "none",
                "y_type": "numeric",
                "format": "currency"
            },
            "data_points": [
                {"label": "Total CAC", "val": 450000.0}
            ]
        }
        res = client.post("/api/apply-style", json={
            "chart_type": "kpi",
            "title": "Total Customer Acquisition Cost",
            "style": "dark_background",
            "palette": "magma",
            "unified_contract": sample_contract
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertTrue(data.get("chart_url", "").startswith("data:image/png;base64,"))
        self.assertEqual(data.get("chart_data", {}).get("contract_version"), "1.1")

    def test_apply_style_with_fallback_contract(self):
        """Verify /api/apply-style reads unified_contract from chart_data field if unified_contract key is absent."""
        sample_contract = {
            "contract_version": "1.1",
            "chart_type": "bar",
            "data_points": [
                {"label": "Group A", "val": 100.0},
                {"label": "Group B", "val": 200.0}
            ]
        }
        res = client.post("/api/apply-style", json={
            "chart_type": "bar",
            "title": "Group Comparison",
            "style": "whitegrid",
            "palette": "deep",
            "chart_data": sample_contract
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertTrue(data.get("chart_url", "").startswith("data:image/png;base64,"))

    def test_apply_style_multi_line_contract(self):
        """Verify /api/apply-style works seamlessly on multi_line contract chart in 2D."""
        multi_line_contract = {
            "contract_version": "1.1",
            "chart_type": "multi_line",
            "query": "Performance by Quarter",
            "series": [
                {"name": "Series 1", "axis": "y", "data": [10.0, 20.0, 30.0]},
                {"name": "Series 2", "axis": "y", "data": [15.0, 25.0, 35.0]}
            ],
            "axis_metadata": {
                "x_type": "categorical",
                "y_type": "numeric",
                "x_categories": ["Q1", "Q2", "Q3"]
            },
            "data_points": [
                {"label": "Q1", "val": 10.0},
                {"label": "Q2", "val": 20.0},
                {"label": "Q3", "val": 30.0}
            ]
        }
        res = client.post("/api/apply-style", json={
            "chart_type": "multi_line",
            "title": "Quarterly Trend",
            "style": "dark_background",
            "palette": "vibrant",
            "unified_contract": multi_line_contract
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertTrue(data.get("chart_url", "").startswith("data:image/png;base64,"))

    def test_apply_style_pie_chart(self):
        """Verify /api/apply-style correctly restyles pie charts without index errors."""
        res = client.post("/api/apply-style", json={
            "chart_type": "pie",
            "x_col": "gender",
            "title": "Distribution of Gender",
            "style": "dark_background",
            "palette": "magma"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("chart_type"), "pie")
        self.assertTrue(data.get("chart_url", "").startswith("data:image/png;base64,"))
        self.assertIn("pie_slices", data.get("chart_data", {}))


    def test_apply_style_pie_chart_stays_pie_with_contract(self):
        """Verify /api/apply-style with a pie chart contract stays pie and retains slices."""
        pie_contract = {
            "contract_version": "1.1",
            "chart_type": "pie",
            "query": "Gender Distribution",
            "x_col": "gender",
            "data_signature": "sig_12345",
            "indicators": [{"type": "reference", "val": 50}],
            "axis_metadata": {
                "x_type": "categorical",
                "y_type": "numeric",
                "x_label": "Gender",
                "y_label": "Count"
            },
            "data_points": [
                {"label": "Male", "val": 12000.0},
                {"label": "Female", "val": 13000.0}
            ]
        }
        # Even if chart_type is omitted or generic "chart" in payload
        res = client.post("/api/apply-style", json={
            "chart_type": "chart",
            "title": "Gender Distribution",
            "style": "whitegrid",
            "palette": "cyberpunk",
            "unified_contract": pie_contract
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("chart_type"), "pie")
        self.assertTrue(data.get("chart_url", "").startswith("data:image/png;base64,"))
        # Ensure contract data points, indicators, and signature are preserved
        cd = data.get("chart_data", {})
        self.assertEqual(cd.get("chart_type"), "pie")
        self.assertEqual(cd.get("data_signature"), "sig_12345")
        self.assertEqual(len(cd.get("data_points", [])), 2)
        self.assertEqual(cd.get("data_points")[0]["label"], "Male")
        self.assertEqual(cd.get("data_points")[0]["val"], 12000.0)
        self.assertIn("indicators", cd)

    def test_apply_style_line_chart_preserves_data_points(self):
        """Verify /api/apply-style preserves exact data points on line charts without re-aggregating."""
        line_contract = {
            "contract_version": "1.1",
            "chart_type": "line",
            "query": "Revenue by Month",
            "x_col": "Month",
            "y_col": "Revenue",
            "data_signature": "sig_line_678",
            "axis_metadata": {
                "x_type": "temporal",
                "y_type": "numeric",
                "x_label": "Month",
                "y_label": "Revenue"
            },
            "data_points": [
                {"label": "Jan", "val": 100.0},
                {"label": "Feb", "val": 150.0},
                {"label": "Mar", "val": 200.0}
            ]
        }
        res = client.post("/api/apply-style", json={
            "chart_type": "line",
            "title": "Revenue by Month",
            "style": "dark_background",
            "palette": "sunset",
            "unified_contract": line_contract
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("chart_type"), "line")
        self.assertTrue(data.get("chart_url", "").startswith("data:image/png;base64,"))
        cd = data.get("chart_data", {})
        self.assertEqual(cd.get("chart_type"), "line")
        self.assertEqual(cd.get("data_signature"), "sig_line_678")
        self.assertEqual(len(cd.get("data_points", [])), 3)

    def test_apply_style_area_chart_preserves_data_points(self):
        """Verify /api/apply-style preserves exact data points on area charts."""
        area_contract = {
            "contract_version": "1.1",
            "chart_type": "area",
            "query": "Sales over Time",
            "x_col": "Period",
            "y_col": "Sales",
            "axis_metadata": {
                "x_type": "temporal",
                "y_type": "numeric"
            },
            "data_points": [
                {"label": "2021", "val": 500.0},
                {"label": "2022", "val": 750.0}
            ]
        }
        res = client.post("/api/apply-style", json={
            "chart_type": "area",
            "title": "Sales over Time",
            "style": "whitegrid",
            "palette": "emerald",
            "unified_contract": area_contract
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("chart_type"), "area")
        self.assertTrue(data.get("chart_url", "").startswith("data:image/png;base64,"))


if __name__ == "__main__":
    unittest.main()

