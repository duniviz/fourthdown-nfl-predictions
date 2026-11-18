"""Join completed-game FTN charting to play-by-play and aggregate by week.

FTN Data via nflverse, CC BY-SA 4.0. Play IDs are cast only after checking
that play-by-play IDs are integral. Ambiguous duplicate join keys are dropped.
"""
from collections import defaultdict
import math


def load_joined(nfl, season, finals):
    import polars as pl
    pbp=nfl.load_pbp([season]).select(['game_id','play_id','season','week','season_type',
        'play_type','passer_player_id','receiver_player_id','rusher_player_id','defteam'])
    pbp=pbp.filter(pl.col('game_id').is_in(list(finals)) & (pl.col('season_type')=='REG')
                   & pl.col('play_id').is_not_null() & ((pl.col('play_id') % 1)==0))
    pbp=pbp.with_columns(pl.col('play_id').cast(pl.Int64))
    chart=nfl.load_ftn_charting([season]).select(['nflverse_game_id','nflverse_play_id',
        'is_play_action','is_screen_pass','is_catchable_ball','is_contested_ball',
        'read_thrown','n_defense_box','is_motion','is_rpo','n_blitzers','n_pass_rushers'])
    chart=chart.rename({'nflverse_game_id':'game_id','nflverse_play_id':'play_id'})
    chart=chart.filter(pl.col('game_id').is_in(list(finals)) & pl.col('play_id').is_not_null())
    chart=chart.with_columns(pl.col('play_id').cast(pl.Int64))
    keys=['game_id','play_id']
    pbp=pbp.filter(~pl.struct(keys).is_duplicated())
    chart=chart.filter(~pl.struct(keys).is_duplicated())
    joined=pbp.join(chart,on=keys,how='inner',validate='1:1')
    print('FTN_JOIN',season,'matched',len(joined),'completed_chart_plays',len(chart),flush=True)
    return joined.to_dicts()


def num(v):
    if v is None:return None
    try:
        x=float(v)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):return None


def add_charted_features(series, rows):
    weekly=defaultdict(lambda:[[],[],[]])
    def add(key,values):
        for i,v in enumerate(values):
            v=num(v)
            if v is not None:weekly[key][i].append(v)
    for r in rows:
        try: season,week=int(r['season']),int(r['week'])
        except (KeyError,ValueError,TypeError):continue
        if week<1 or r.get('season_type')!='REG':continue
        defense=r.get('defteam')
        if r.get('play_type')=='pass':
            pid=r.get('passer_player_id')
            if pid:add(('ftn_passing_yards',str(pid),season,week),[r.get('is_play_action'),r.get('is_screen_pass'),r.get('n_pass_rushers')])
            pid=r.get('receiver_player_id')
            read=r.get('read_thrown')
            first=None if read is None else (1.0 if str(read)=='0' else 0.0)
            if pid:add(('ftn_receiving_yards',str(pid),season,week),[r.get('is_screen_pass'),r.get('is_catchable_ball'),first])
            if defense:
                add(('ftn_defense_passing_yards',str(defense),season,week),[r.get('n_pass_rushers'),r.get('n_blitzers'),r.get('is_play_action')])
                add(('ftn_defense_receiving_yards',str(defense),season,week),[r.get('is_screen_pass'),r.get('is_catchable_ball'),r.get('is_contested_ball')])
        elif r.get('play_type')=='run':
            values=[r.get('n_defense_box'),r.get('is_motion'),r.get('is_rpo')]
            pid=r.get('rusher_player_id')
            if pid:add(('ftn_rushing_yards',str(pid),season,week),values)
            if defense:add(('ftn_defense_rushing_yards',str(defense),season,week),values)
    for (source,identifier,season,week),values in weekly.items():
        result=[sum(v)/len(v) if v else None for v in values]
        if any(v is not None for v in result):series[(source,identifier)].append(((season,week),result))
    return len(rows)
