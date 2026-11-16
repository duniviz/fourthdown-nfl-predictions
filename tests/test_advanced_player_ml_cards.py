import json,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from research.publish_advanced_player_ml import fit_selected,features_for_player
from live.advanced_player_ml import candidate,load_pair,FAMILY

BASE=[100.,95.,7.,28.,110.,65.,1.,10.]
MODEL={"variant":"baseline_features","feature_groups":[],
       "coefficients":[1.0]+[0.0]*7,"intercept":1.0,
       "trained_season":2026,"trained_week":9,"active":False}
RUNTIME={"family":FAMILY,"target_season":2026,"target_week":10,
         "generated_at_utc":"2026-11-15T14:00:00Z","models":{"passing_yards":MODEL},
         "research_only":True}
FEATURES={"family":FAMILY,"target_season":2026,"target_week":10,
          "generated_at_utc":"2026-11-15T14:00:00Z",
          "research_only":True,"players":{"p1":{"passing_yards":{
             "ngs":[1.0,2.0,3.0,1.0],"snap":[0.8,1.0],"pfr":[0.,0.,0.,0.]}}}}

def run(model=None,runtime=None,features=None):
 return candidate(runtime or RUNTIME,features or FEATURES,"passing_yards","p1",
          2026,10,*BASE)

class AdvancedCardInferenceTests(unittest.TestCase):
 def test_research_candidate_without_production_promotion(self):
  result=run()
  self.assertEqual(result["candidate"],101.)
  self.assertFalse(result["active"])
  self.assertTrue(result["research_only"])
  self.assertEqual(result["variant"],"baseline_features")
 def test_stale_target_and_leakage_block(self):
  self.assertIsNone(candidate(RUNTIME,FEATURES,"passing_yards","p1",2026,11,*BASE))
  runtime=json.loads(json.dumps(RUNTIME))
  runtime["models"]["passing_yards"]["trained_week"]=10
  self.assertIsNone(run(runtime=runtime))
 def test_missing_source_for_combined_model(self):
  runtime=json.loads(json.dumps(RUNTIME))
  m=runtime["models"]["passing_yards"]
  m.update(variant="combined",feature_groups=["ngs","snap","pfr"],
           coefficients=[1.0]+[0.0]*17)
  features=json.loads(json.dumps(FEATURES))
  features["players"]["p1"]["passing_yards"].update(ngs=[0.,0.,0.,0.],snap=[0.,0.])
  self.assertIsNone(run(runtime=runtime,features=features))
 def test_invalid_coefficients_and_paired_snapshot_mismatch(self):
  runtime=json.loads(json.dumps(RUNTIME))
  runtime["models"]["passing_yards"]["coefficients"]=[1.0]
  self.assertIsNone(run(runtime=runtime))
  with TemporaryDirectory() as folder:
   root=Path(folder);a=root/"a.json";b=root/"b.json"
   a.write_text(json.dumps(RUNTIME))
   other=json.loads(json.dumps(FEATURES));other["target_week"]=11
   b.write_text(json.dumps(other))
   self.assertEqual(load_pair(a,b),({},{}))
 def test_fitted_coefficients_require_strict_prior_week_rows(self):
  data=[]
  for i in range(110):
   week=8 if i<60 else 9
   data.append({"market":"passing_yards","key":(2026,week),
     "base":[100.+i,95.,7.,28.,110.,65.,1.,float(week)],
     "actual":100.+i,"ngs":[0.]*4,"snap":[0.]*2,"pfr":[0.]*4})
  data.append({"market":"passing_yards","key":(2026,10),
     "base":[999.]*8,"actual":9999.,"ngs":[0.]*4,"snap":[0.]*2,"pfr":[0.]*4})
  selection={"player":{"passing_yards":{"research_winner":"baseline_features",
    "relative_improvement_pct":3.0,"samples":200,"weeks":8}}}
  models=fit_selected(data,selection,(2026,10))
  self.assertEqual(models["passing_yards"]["training_rows"],110)
  self.assertEqual(models["passing_yards"]["trained_week"],9)
 def test_player_feature_vectors_exclude_target_week(self):
  series={("passing","p1"):[((2026,9),[1.,2.,3.]),((2026,10),[99.,99.,99.])]}
  self.assertEqual(features_for_player(series,{},"p1","passing_yards",(2026,10))["ngs"],
                   [1.,2.,3.,1.])
 def test_no_production_activation_by_training(self):
  data=[]
  for i in range(120):
   data.append({"market":"receiving_yards","key":(2026,9),
       "base":[float(i+10),10.,8.,3.,23.,55.,1.1,9.],
       "actual":float(i+11),"ngs":[2.,1.,10.,1.],
       "snap":[.8,1.],"pfr":[0.]*4})
  selection={"player":{"receiving_yards":{"research_winner":"combined",
       "relative_improvement_pct":1.86,"samples":932,"weeks":8}}}
  m=fit_selected(data,selection,(2026,10))["receiving_yards"]
  self.assertFalse(m["active"])
  self.assertEqual(m["feature_groups"],["ngs","snap","pfr"])
  self.assertEqual(len(m["coefficients"]),18)

if __name__=="__main__":unittest.main()
