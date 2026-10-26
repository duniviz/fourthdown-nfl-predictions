import unittest
from datetime import datetime,timezone
from live.generate import forecast

class LiveForecastTests(unittest.TestCase):
    def test_future_games_without_scores_and_same_week_freeze(self):
        games=[];epa=[]
        for week in range(1,6):
            games.append(dict(season=2026,week=week,game_type="REG",game_id=f"g{week}",home_team="A",away_team="B",home_score=24 if week<5 else None,away_score=17 if week<5 else None,gameday=f"2026-09-{week+1:02d}" if week<5 else "2026-11-01",gametime="13:00"))
            if week<5:
                epa.extend([dict(season=2026,week=week,team="A",offense_epa=.1,defense_epa=-.05),dict(season=2026,week=week,team="B",offense_epa=-.05,defense_epa=.1)])
        result=forecast(games,epa,datetime(2026,10,25,tzinfo=timezone.utc))
        self.assertEqual(result["week"],5)
        self.assertEqual(len(result["games"]),1)
        self.assertEqual(result["games"][0]["predicted_winner"],"A")

if __name__=="__main__":unittest.main()
