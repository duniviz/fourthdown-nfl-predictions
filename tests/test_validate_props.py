import unittest
from live.validate_props import validate

def sample(stat="rushing_yards",value=75):
    return {"player":"Test","stat_key":stat,"projection":value,"opportunity_type":"carries"}

class TestPropValidation(unittest.TestCase):
    def test_yardage(self): self.assertEqual(validate([sample()]),1)
    def test_impossible_yardage(self):
        with self.assertRaises(ValueError): validate([sample(value=999)])
    def test_td_probability(self):
        with self.assertRaises(ValueError): validate([{"player":"Test","stat_key":"anytime_td","projection":72.7,"projection_probability":.4}])
    def test_valid_td(self):
        self.assertEqual(validate([{"player":"Test","stat_key":"anytime_td","projection":72.7,"projection_probability":.727}]),1)
    def test_missing(self):
        with self.assertRaises(ValueError): validate([])
if __name__=="__main__": unittest.main()
