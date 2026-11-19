"""Verify free-source research runs from independently generated completed-game rows."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class FeatureWorkflowTests(unittest.TestCase):
    def test_training_is_built_before_feature_evaluation(self):
        workflow=(ROOT/'.github/workflows/free-nfl-feature-lab.yml').read_text()
        build='python -m tools.refresh_weekly_player_ml_data --start 2016 --output data/weekly-player-ml-training.csv'
        use='python -m research.free_nfl_feature_lab --start 2016 --input data/weekly-player-ml-training.csv'
        self.assertIn(build,workflow)
        self.assertIn(use,workflow)
        self.assertLess(workflow.index(build),workflow.index(use))
        self.assertIn('test -s data/weekly-player-ml-training.csv',workflow)
        self.assertIn('github.event_name != \'pull_request\'',workflow)
if __name__=='__main__': unittest.main()
