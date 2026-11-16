"""Safety checks for the presentation-only mobile-first pass."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MobileFirstPresentationTests(unittest.TestCase):
    def test_all_main_pages_load_mobile_stylesheet(self):
        tag = 'assets/fd-mobile-first-2026.css?v=1'
        for page in ('index.html', 'bets.html', 'history.html', 'model-lab.html'):
            with self.subTest(page=page):
                text = (ROOT / page).read_text(encoding='utf-8')
                self.assertEqual(text.count(tag), 1)
                self.assertLess(text.rfind(tag), text.rfind('</body>'))

    def test_mobile_rules_keep_predictions_visible_and_touchable(self):
        css = (ROOT / 'assets/fd-mobile-first-2026.css').read_text(encoding='utf-8')
        for selector in ('#scoreboard-cards', '.fd-market-picks', '.fd-top-picks-tabs',
                         '.fd-app-nav', '#fd-modal', '.fd-mobile-prop-numbers'):
            with self.subTest(selector=selector):
                self.assertIn(selector, css)
        self.assertIn('min-height:48px', css)
        self.assertIn('grid-template-columns:minmax(0,1fr)', css)
        self.assertNotIn('display:none', css)
        self.assertNotIn('visibility:hidden', css)

    def test_no_mobile_script_or_data_pipeline_changes(self):
        css = (ROOT / 'assets/fd-mobile-first-2026.css').read_text(encoding='utf-8')
        self.assertNotIn('@import', css)
        self.assertNotIn('url(', css)


if __name__ == '__main__':
    unittest.main()
