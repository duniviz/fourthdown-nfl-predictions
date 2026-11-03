"""Offline safety tests for the pregame editorial pipeline."""
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("previews",ROOT/"tools/generate_ai_game_previews.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class PreviewTests(unittest.TestCase):
    def test_evidence_omits_unverified_injury(self):
        game={"home":"SEA","away":"CHI","projected_home_score":21.4,
              "projected_away_score":18.7,"predicted_winner":"SEA",
              "analysis":{"home":{"offense_rank":25},"away":{"defense_rank":14}}}
        context={"availability":{"status":"unavailable","players":[{"name":"Unverified Player"}]},
                 "recent":{"home":{"status":"unavailable","wins":4}}}
        facts=mod.evidence(game,context)
        self.assertNotIn("verified_availability",facts)
        self.assertNotIn("home_recent_results",facts)
        self.assertIn("model_projection",facts)

    def test_rejects_fabricated_evidence_key(self):
        preview={"headline":"A game worth watching","stories":[{"title":"The battle up front",
            "body":"A"*80,"evidence_keys":["made_up_injury"]}]}
        self.assertFalse(mod.validate(preview,{"teams":{"home":"SEA","away":"CHI"}},{}))

    def test_rejects_repeated_titles(self):
        preview={"headline":"A game worth watching","stories":[{"title":"The battle up front",
            "body":"A"*80,"evidence_keys":["teams"]}]}
        previous={"other":{"stories":[{"title":"The battle up front"}]}}
        self.assertFalse(mod.validate(preview,{"teams":{"home":"SEA","away":"CHI"}},previous))

    def test_accepts_unique_grounded_draft(self):
        preview={"headline":"Seattle's unusual challenge","stories":[{"title":"Seattle's difficult offensive test",
            "body":"A"*80,"evidence_keys":["teams","model_projection"]}]}
        facts={"teams":{"home":"SEA","away":"CHI"},"model_projection":{"winner":"SEA"}}
        self.assertTrue(mod.validate(preview,facts,{}))

if __name__=="__main__":unittest.main()
