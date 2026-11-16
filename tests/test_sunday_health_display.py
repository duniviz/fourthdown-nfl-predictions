"""The Sunday health view must not confuse wrapper success with a refresh."""
import unittest
from pathlib import Path

class SundayHealthDisplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page=Path("pipeline-health.html").read_text(encoding="utf-8")

    def test_successful_recovery_preferred_over_failed_primary(self):
        self.assertIn("if(lines?.conclusion==='success'&&forecastJob?.conclusion==='success')", self.page)
        self.assertIn("good=run;break;", self.page)
        self.assertIn("Refresh steps completed", self.page)

    def test_skipped_jobs_are_not_green(self):
        self.assertIn("lines.conclusion==='skipped'||forecastJob.conclusion==='skipped'", self.page)
        self.assertIn("No refresh performed", self.page)

    def test_historical_feed_times_not_used_as_false_proof(self):
        self.assertIn("Earlier slot output cannot be verified", self.page)
        self.assertIn("latest files alone", self.page)

    def test_api_cache_buster_handles_existing_query(self):
        self.assertIn("url.includes('?')?'&':'?'", self.page)

if __name__=="__main__":
    unittest.main()
