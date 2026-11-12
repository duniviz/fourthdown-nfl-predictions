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
        self.assertEqual(categories, set())

    def test_candidate_applies_shrunk_p3_position_split(self):
        adjusted, category = candidate_projection(200, "QB", "passing_yards", {"rain"})
        self.assertAlmostEqual(adjusted, 190.9)
        self.assertEqual(category, "rain")

    def test_unsupported_position_market_keeps_baseline(self):
        adjusted, category = candidate_projection(80, "RB", "rushing_yards", {"rain"})
        self.assertEqual(adjusted, 80)
        self.assertIsNone(category)

    def test_overlapping_weather_uses_strongest_split_once(self):
        adjusted, category = candidate_projection(200, "QB", "passing_yards", {"rain", "windy"})
        self.assertAlmostEqual(adjusted, 188.0)
        self.assertEqual(category, "snow" if False else "rain")


if __name__ == "__main__":
    unittest.main()
