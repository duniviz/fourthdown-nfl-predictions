import unittest
from research.coach_matchup_context import build


def fixture():
    games, plays = [], []
    for week in range(1, 6):
        gid = f'2025_{week:02d}_A_B'
        games.append({'game_id': gid, 'season': 2025, 'week': week, 'game_type': 'REG',
                      'home_team': 'B', 'away_team': 'A', 'home_score': 20, 'away_score': 10,
                      'home_coach': 'Coach B', 'away_coach': 'Coach A'})
        for offense, defense in [('A', 'B'), ('B', 'A')]:
            for kind, diff in [('pass', 0), ('run', 0), ('pass', -10), ('run', -10)]:
                plays.append({'game_id': gid, 'posteam': offense, 'defteam': defense,
                              'play_type': kind, 'score_differential': diff, 'yards_gained': 4})
    return games, plays


class ContextTests(unittest.TestCase):
    def test_target_game_and_future_plays_cannot_change_features(self):
        games, plays = fixture()
        before = build(games, plays)['2025_04_A_B']
        for p in plays:
            if p['game_id'] in ('2025_04_A_B', '2025_05_A_B'):
                p['yards_gained'] = 999
                p['play_type'] = 'pass'
        self.assertEqual(before, build(games, plays)['2025_04_A_B'])
        self.assertEqual(before['defense'], [4, 4, 4, 4])

    def test_no_retroactive_coach_change(self):
        games, plays = fixture()
        before = build(games, plays)['2025_04_A_B']
        games[3]['home_coach'] = 'New coach'
        self.assertEqual(before, build(games, plays)['2025_04_A_B'])

    def test_incomplete_games_do_not_enter_history(self):
        games, plays = fixture()
        games[1]['home_score'] = None
        self.assertNotIn('2025_04_A_B', build(games, plays))


if __name__ == '__main__':
    unittest.main()
