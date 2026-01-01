import unittest

from app.tools import t1d_math


class T1dMathTests(unittest.TestCase):
    def test_conversions(self):
        self.assertAlmostEqual(t1d_math.mgdl_to_mmoll(180), 10.0)
        self.assertAlmostEqual(t1d_math.mmoll_to_mgdl(5.5), 99.0)

    def test_carb_exchanges(self):
        self.assertAlmostEqual(t1d_math.carb_exchanges(45), 3.0)

    def test_bolus_calc(self):
        result = t1d_math.bolus_calc(
            icr=10,
            isf=3,
            target_bg=5.5,
            current_bg=7.5,
            carbs_g=60,
            iob=1,
        )
        self.assertAlmostEqual(result["meal_bolus"], 6.0)
        self.assertAlmostEqual(result["correction"], (7.5 - 5.5) / 3)
        self.assertAlmostEqual(result["total"], 6.0 + (7.5 - 5.5) / 3 - 1)
        self.assertIn("default_targets", result)
        self.assertIsInstance(result["warnings"], list)


if __name__ == "__main__":
    unittest.main()
