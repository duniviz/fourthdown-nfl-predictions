import unittest
from tools.audit_player_result_grading import audit

class ResultAuditTests(unittest.TestCase):
    def row(self,**changes):
        r={"game_id":"2026_09_GB_CHI","player_id":"123","stat_key":"receiving_yards",
           "dk_line":55.5,"recommended_side":"over","actual":61,
           "recommendation_result":"hit"}
        r.update(changes)
        return r
    def test_valid_hit(self):
        self.assertEqual(audit([self.row()]),[])
    def test_under_hit(self):
        self.assertEqual(audit([self.row(recommended_side="under",actual=40)]),[])
    def test_push(self):
        self.assertEqual(audit([self.row(actual=55.5,recommendation_result="push")]),[])
    def test_wrong_grade(self):
        self.assertTrue(audit([self.row(recommendation_result="miss")]))
    def test_missing_line_not_graded(self):
        self.assertEqual(audit([self.row(dk_line=None,recommended_side=None,recommendation_result="not_available")]),[])
        self.assertTrue(audit([self.row(dk_line=None)]))
    def test_duplicate_market(self):
        self.assertTrue(audit([self.row(),self.row()]))
if __name__=="__main__":unittest.main()
