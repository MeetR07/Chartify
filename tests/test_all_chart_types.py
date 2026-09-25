import os
import sys
import unittest
import pandas as pd
import numpy as np

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import backend.charts as charts
from backend.chart_planner import ChartPlanner, build_unified_data_contract
from backend.engine import DeterministicDataEngine

class TestAllChartTypes(unittest.TestCase):

    def setUp(self):
        self.df = pd.DataFrame({
            "Category": ["Electronics", "Clothing", "Home", "Books", "Toys", "Sports"],
            "Sales": [45000.0, 32000.0, 28000.0, 15000.0, 19000.0, 24000.0],
            "Profit": [12000.0, 8000.0, -3000.0, 4500.0, 3200.0, 6100.0],
            "Quantity": [150, 220, 85, 310, 190, 140],
            "Region": ["North", "South", "North", "East", "West", "South"],
            "Date": ["2023-01-01", "2023-02-01", "2023-03-01", "2023-04-01", "2023-05-01", "2023-06-01"]
        })

    def _generate(self, chart_type, x_col=None, y_col=None, hue_col=None, orientation="auto"):
        args = {
            "chart_type": chart_type,
            "x_col": x_col or "Category",
            "y_col": y_col or "Sales",
            "hue_col": hue_col,
            "title": f"Test {chart_type}",
            "orientation": orientation,
            "output_path": ":memory:",
            "precomputed_df": self.df
        }
        res = charts.generate_chart.invoke(args)
        return res

    def test_bar_charts(self):
        for ct in ["bar", "column", "vertical_bar", "horizontal_bar"]:
            res = self._generate(ct)
            self.assertTrue(isinstance(res, str) and res.startswith("data:image/png;base64,"),
                            f"Failed for {ct}: {res[:100]}")

    def test_grouped_and_stacked_bars(self):
        for ct in ["grouped_bar", "stacked_bar"]:
            res = self._generate(ct, x_col="Category", y_col="Sales", hue_col="Region")
            self.assertTrue(isinstance(res, str) and res.startswith("data:image/png;base64,"),
                            f"Failed for {ct}: {res[:100]}")

    def test_line_charts(self):
        for ct in ["line", "multi_line", "area"]:
            res = self._generate(ct, x_col="Date", y_col="Sales", hue_col="Region" if ct == "multi_line" else None)
            self.assertTrue(isinstance(res, str) and res.startswith("data:image/png;base64,"),
                            f"Failed for {ct}: {res[:100]}")

    def test_pie_and_donut(self):
        for ct in ["pie", "donut"]:
            res = self._generate(ct, x_col="Category", y_col="Sales")
            self.assertTrue(isinstance(res, str) and res.startswith("data:image/png;base64,"),
                            f"Failed for {ct}: {res[:100]}")

    def test_scatter_and_bubble(self):
        for ct in ["scatter", "bubble"]:
            res = self._generate(ct, x_col="Sales", y_col="Profit")
            self.assertTrue(isinstance(res, str) and res.startswith("data:image/png;base64,"),
                            f"Failed for {ct}: {res[:100]}")

    def test_statistical_charts(self):
        for ct in ["histogram", "box", "violin"]:
            x = "Sales" if ct == "histogram" else "Category"
            y = None if ct == "histogram" else "Sales"
            res = self._generate(ct, x_col=x, y_col=y)
            self.assertTrue(isinstance(res, str) and res.startswith("data:image/png;base64,"),
                            f"Failed for {ct}: {res[:100]}")

    def test_advanced_business_charts(self):
        for ct in ["heatmap", "treemap", "lollipop", "waterfall", "funnel", "radar"]:
            res = self._generate(ct, x_col="Category", y_col="Sales")
            self.assertTrue(isinstance(res, str) and res.startswith("data:image/png;base64,"),
                            f"Failed for {ct}: {res[:100]}")

    def test_kpi_card(self):
        res = self._generate("kpi", x_col=None, y_col="Sales")
        self.assertTrue(isinstance(res, str) and res.startswith("data:image/png;base64,"),
                        f"Failed for kpi: {res[:100]}")

    def test_pairplot(self):
        res = self._generate("pairplot")
        self.assertTrue(isinstance(res, str) and res.startswith("data:image/png;base64,"),
                        f"Failed for pairplot: {res[:100]}")


if __name__ == "__main__":
    unittest.main()
