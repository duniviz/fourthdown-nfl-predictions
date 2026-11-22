"""Optional sourced ESPN pregame context; never modifies projection values."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import math
import re
import urllib.request
import json
from urllib.parse import urlparse

BASE='https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event='
ALIASES={'JAC':'JAX','LAR':'LA','WAS':'WSH'}

def canon(team):
    team=str(team or '').upper()
    return ALIASES.get(team,team)

def stamp(value):
    try:
        d=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return d if d.tzinfo else None
    except (ValueError, TypeError): return None

def fetch_summary(event_id):
    req=urllib.request.Request(BASE+event_id,headers={'User-Agent':'fourthdown-context/1.0'})
    try:
        with urllib.request.urlopen(req,timeout=6) as response:
            return json.loads(response.read(1_500_000))
    except (OSError,ValueError,TimeoutError): return None

class TextOnly(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]; self.suppress=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'): self.suppress+=1
        elif tag in ('p','br','div','li'): self.parts.append(' ')
    def handle_endtag(self,tag):
        if tag in ('script','style') and self.suppress: self.suppress-=1
        elif tag in ('p','div','li'): self.parts.append(' ')
    def handle_data(self,data):
        if not self.suppress:self.parts.append(data)

def quote_from_story(story):
    if not isinstance(story,str): return None
    parser=TextOnly()
    try: parser.feed(story[:80000])
    except Exception: return None
    text=' '.join(''.join(parser.parts).split())
    sentences=re.split(r'(?<=[.!?])\s+',text)
    # Copy just one short, attributed extract; leave full articles at the source.
    topics=('blitz','pressure','red zone','red-zone','rushing','run game','pass rush','defense','defence','coverage')
    candidates=[s.strip() for s in sentences if 7<=len(s.split())<=20 and any(k in s.lower() for k in topics) and not re.search(r'https?://|<|>',s)]
    return candidates[0] if candidates else None

def extract(game,event,summary,now):
    kickoff=stamp(game.get('kickoff_utc')); event_time=stamp(event.get('date'))
    if not kickoff or not event_time or now>=kickoff or abs((event_time-kickoff).total_seconds())>900: return None
    eid=str(event.get('id') or '')
    if not eid.isdigit() or not isinstance(summary,dict): return None
    competitors=((event.get('competitions') or [{}])[0].get('competitors') or [])
    sides={c.get('homeAway'):c for c in competitors if c.get('homeAway') in ('home','away')}
    if any(canon(sides.get(side,{}).get('team',{}).get('abbreviation'))!=canon(game.get(side)) for side in ('home','away')): return None
    pred=summary.get('predictor') or {}
    try:
        h=pred['homeTeam']; a=pred['awayTeam']
        hp=float(h['gameProjection']); ap=float(a['gameProjection'])
        if str(h['id'])!=str(sides['home'].get('id')) or str(a['id'])!=str(sides['away'].get('id')): raise ValueError('team mismatch')
        if not all(math.isfinite(n) and 0<=n<=100 for n in (hp,ap)) or abs(hp+ap-100)>2: raise ValueError('invalid probabilities')
        predictor={'source':'ESPN Matchup Predictor','home_pct':hp,'away_pct':ap,
                   'retrieved_at_utc':now.isoformat(),'url':'https://www.espn.com/nfl/game/_/gameId/'+eid}
    except (KeyError,ValueError,TypeError): predictor=None
    article=summary.get('article') or {}
    published=stamp(article.get('published')); modified=stamp(article.get('lastModified')) or published
    url=(article.get('links') or {}).get('web',{}).get('href','')
    parsed=urlparse(url)
    # Upgrade ESPN's http links; never follow or render another host.
    if parsed.scheme in ('http','https') and parsed.hostname=='www.espn.com': url=parsed._replace(scheme='https').geturl()
    else: url=''
    quoted=quote_from_story(article.get('story'))
    preview=None
    if str(article.get('gameId'))==eid and str(article.get('type','')).lower()=='preview' and published and modified and published<=now and modified<=now and modified<kickoff and url and quoted and not article.get('premium',False):
        preview={'source':str(article.get('source') or 'ESPN')[:80], 'headline':str(article.get('headline') or 'Game preview')[:180],
                 'excerpt':quoted, 'published_at_utc':published.isoformat(),'updated_at_utc':modified.isoformat(),'url':url}
    if not predictor and not preview: return None
    return {'event_id':eid,'kickoff_utc':kickoff.isoformat(),'predictor':predictor,'article':preview}

def collect(games,scoreboard,now=None,fetch=fetch_summary):
    now=now or datetime.now(timezone.utc)
    def one(game):
        kickoff=stamp(game.get('kickoff_utc'))
        if not kickoff or now>=kickoff: return game.get('game_id'),None
        matches=[]
        for event in scoreboard.get('events',[]):
            et=stamp(event.get('date')); c=((event.get('competitions') or [{}])[0].get('competitors') or [])
            sides={v.get('homeAway'):canon(v.get('team',{}).get('abbreviation')) for v in c}
            if et and abs((kickoff-et).total_seconds())<=900 and sides.get('away')==canon(game.get('away')) and sides.get('home')==canon(game.get('home')): matches.append(event)
        if len(matches)!=1:return game.get('game_id'),None
        event=matches[0];eid=str(event.get('id') or '')
        if not eid.isdigit():return game.get('game_id'),None
        try: summary=fetch(eid)
        except (OSError,ValueError,TimeoutError): return game.get('game_id'),None
        return game.get('game_id'),extract(game,event,summary,now)
    with ThreadPoolExecutor(max_workers=4) as pool: return dict(pool.map(one,games))
