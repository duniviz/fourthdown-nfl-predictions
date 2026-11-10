import unittest
from live.player_research import replacement_qb_trial

def row(season, week, attempts, yards):
    return {'season':season,'week':week,'attempts':attempts,'passing_yards':yards}

class ReplacementQBTrialTests(unittest.TestCase):
    def test_wentz_prior_game_example(self):
        prior=[row(2025,3,20,173),row(2025,4,46,350),row(2025,5,34,236),row(2025,7,42,313),row(2025,8,27,144)]
        current=[row(2026,1,19,133),row(2026,2,20,143)]
        out=replacement_qb_trial(current,prior,{'status':'confirmed'},True)
        self.assertEqual(out['projection'],232.0)
        self.assertEqual(out['games'],5)
    def test_fails_closed_for_disabled_or_unverified_or_thin_history(self):
        current=[row(2026,1,20,140)]
        prior=[row(2025,i,30,210) for i in (1,2,3)]
        self.assertIsNone(replacement_qb_trial(current,prior,{'status':'confirmed'},False))
        self.assertIsNone(replacement_qb_trial(current,prior,None,True))
        self.assertIsNone(replacement_qb_trial(current,[],{'status':'projected'},True))

if __name__=='__main__': unittest.main()

class TrialStartTests(unittest.TestCase):
    def test_trial_starts_week_ten(self):
        from live.player_research import trial_enabled
        self.assertFalse(trial_enabled(2026,9))
        self.assertTrue(trial_enabled(2026,10))
        self.assertTrue(trial_enabled(2027,1))
