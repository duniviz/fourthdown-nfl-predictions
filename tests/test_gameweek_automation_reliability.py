"""Prevent anonymous GitHub rate-limit regressions in player count publishing."""
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

class CountSourceReliabilityTests(unittest.TestCase):
    def test_github_release_lookup_is_authenticated_in_ci_and_publish(self):
        workflow=(ROOT/'.github/workflows/publish-count-props.yml').read_text()
        self.assertEqual(workflow.count('GITHUB_TOKEN: ${{ github.token }}'),2)
        downloader=(ROOT/'tools/download_current_player_stats.py').read_text()
        self.assertIn('headers["Authorization"]="Bearer "+token',downloader)

    def test_retry_403_then_success(self):
        from tools.download_current_player_stats import fetch
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self):return b'valid'
        error=urllib.error.HTTPError('https://api.github.com/x',403,'rate limit',{},None)
        with patch.dict('os.environ',{'GITHUB_TOKEN':'test-token'}):
            with patch('tools.download_current_player_stats.urllib.request.urlopen',side_effect=[error,Response()]) as open_url:
                with patch('tools.download_current_player_stats.time.sleep') as sleep:
                    self.assertEqual(fetch('https://api.github.com/x'),b'valid')
                    self.assertEqual(sleep.call_count,1)
                    self.assertEqual(open_url.call_args[0][0].get_header('Authorization'),'Bearer test-token')

    def test_do_not_retry_permanent_errors(self):
        from tools.download_current_player_stats import fetch
        error=urllib.error.HTTPError('https://api.github.com/x',404,'not found',{},None)
        with patch('tools.download_current_player_stats.urllib.request.urlopen',side_effect=error) as open_url:
            with self.assertRaises(urllib.error.HTTPError):
                fetch('https://api.github.com/x')
            self.assertEqual(open_url.call_count,1)

    def test_failed_count_projections_are_retried_once_before_alerting(self):
        workflow=(ROOT/'.github/workflows/automation-failure-alerts.yml').read_text()
        self.assertIn('actions: write',workflow)
        self.assertIn("run.name === 'Publish count prop projections'",workflow)
        self.assertIn("run.head_branch === 'main'",workflow)
        self.assertIn('Number(run.run_attempt || 1) === 1',workflow)
        self.assertIn('reRunWorkflowFailedJobs',workflow)
        self.assertIn('const title =',workflow)

    def test_backstop_wakes_on_failed_sunday_preset(self):
        workflow=(ROOT/'.github/workflows/sunday-preset-backstop.yml').read_text()
        self.assertIn('Sunday preset game-day refresh]',workflow)
        self.assertIn('result.reason',workflow)

if __name__=='__main__':
    unittest.main()
