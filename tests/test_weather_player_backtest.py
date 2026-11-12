import unittest

from research.weather_player_backtest import candidate_projection, classify_weather


class WeatherPlayerBacktestTests(unittest.TestCase):
    def test_observed_weather_categories_use_report_cutoffs(self):
        categories = classify_weather({
            "roof": "outdoors",
            "game_weather": "Light Rain",
            "wind": 15,
            "temp": 31,
        })
        self.assertEqual(categories, {"rain", "windy", "freezing"})

    def test_indoor_games_do_not_receive_weather_tags(self):
        categories = classify_weather({
            "roof": "dome",
            "game_weather": "Rain",
            "wind": 25,
            "temp": 20,
        })
        self.assertEqual(categories, {"indoor"})

    def test_temperature_bands_match_p3_definitions(self):
        cases = [
            (31.9, "freezing"), (32, "cold"), (44.9, "cold"),
            (45, "cool"), (59.9, "cool"), (60, "mild"),
            (74.9, "mild"), (75, "warm"), (84.9, "warm"),
            (85, "hot"),
        ]
        for temp, expected in cases:
            with self.subTest(temp=temp):
                self.assertIn(expected, classify_weather({"roof": "outdoors", "temp": temp}))

    def test_candidate_applies_shrunk_p3_position_split(self):
        adjusted, category = candidate_projection(200, "QB", "passing_yards", {"rain"})
        self.assertAlmostEqual(adjusted, 191.0)
        self.assertEqual(category, "rain")

    def test_p3_running_back_yardage_split_is_applied(self):
        adjusted, category = candidate_projection(80, "RB", "rushing_yards", {"rain"})
        self.assertAlmostEqual(adjusted, 81.2)
        self.assertEqual(category, "rain")

    def test_p3_running_back_catch_snow_split_is_applied(self):
        adjusted, category = candidate_projection(4, "RB", "receptions", {"snow"})
        self.assertAlmostEqual(adjusted, 3.76)
        self.assertEqual(category, "snow")

    def test_unsupported_position_market_keeps_baseline(self):
        adjusted, category = candidate_projection(80, "QB", "rushing_yards", {"rain"})
        self.assertEqual(adjusted, 80)
        self.assertIsNone(category)

    def test_overlapping_weather_uses_strongest_split_once(self):
        adjusted, category = candidate_projection(200, "QB", "passing_yards", {"rain", "windy"})
        self.assertAlmostEqual(adjusted, 191.0)
        self.assertEqual(category, "rain")


if __name__ == "__main__":
    unittest.main()
