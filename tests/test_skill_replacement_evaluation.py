import unittest
from research.skill_replacement_evaluation import evaluate

def row(week,pid,carries,yards):
    return {'season':2025,'week':week,'season_type':'REG','team':'A','position':'RB','player_id':pid,'carries':carries,'rushing_yards':yards}

class SkillReplacementTests(unittest.TestCase):
    def test_leader_absence_cohort_and_future_does_not_leak(self):
        history=[row(w,'leader',20,90) for w in (1,2,3)]+[row(w,'backup',9,40) for w in (1,2,3)]
        target=[row(4,'backup',10,50)]
        result=evaluate(history+target)
        self.assertEqual(result['by_position']['RB']['games'],1)
        self.assertEqual(result,evaluate(history+target+[row(5,'other',1,4)]))
    def test_present_leader_not_selected(self):
        history=[row(w,'leader',20,90) for w in (1,2,3)]+[row(w,'backup',9,40) for w in (1,2,3)]
        self.assertEqual(evaluate(history+[row(4,'leader',15,60),row(4,'backup',10,40)])['by_position']['RB']['games'],0)
if __name__=='__main__': unittest.main()
