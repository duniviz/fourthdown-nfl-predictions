"""Research-only chronological walk-forward scoring across 2018-2025."""
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from player_impact_research import metric

def evaluate(rows, label):
    out = {"research_only": True, "promotion_eligible": False, "seasons": {}}
    for year in range(2018, 2026):
        test = [r for r in rows if r[0] == year]
        out["seasons"][str(year)] = {}
        for window in ("all", "recent3", "decay"):
            train = [r for r in rows if r[0] < year and (window != "recent3" or r[0] >= year-3)]
            if len(train) < 100 or len(test) < 30:
                out["seasons"][str(year)][window] = {"status": "INSUFFICIENT_DATA", "train_n": len(train), "test_n": len(test)}
                continue
            weights = np.array([0.5 ** ((year - 1 - r[0]) / 2) if window == "decay" else 1.0 for r in train])
            predictions = {}
            for name, enhanced in (("baseline", False), (label, True)):
                x = np.array([r[1] + (r[2] if enhanced else []) for r in train])
                xt = np.array([r[1] + (r[2] if enhanced else []) for r in test])
                estimates = []
                for index in (3, 4):
                    model = make_pipeline(StandardScaler(), Ridge(alpha=100))
                    model.fit(x, [r[index] for r in train], ridge__sample_weight=weights)
                    estimates.append(model.predict(xt))
                predictions[name] = estimates
            h = np.array([r[3] for r in test])
            a = np.array([r[4] for r in test])
            result = {"train_n": len(train), "test_n": len(test)}
            for target, truth in (("spread", h-a), ("total", h+a)):
                scores = {}
                for name, (ph, pa) in predictions.items():
                    scores[name] = metric(truth, ph-pa if target == "spread" else ph+pa)
                scores["mae_change"] = round(scores[label]["mae"] - scores["baseline"]["mae"], 4)
                result[target] = scores
            out["seasons"][str(year)][window] = result
    return out
