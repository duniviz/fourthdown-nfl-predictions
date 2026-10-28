#!/usr/bin/env python3
"""Retrieve official NFL inactive-report source evidence without guessing player eligibility."""
import argparse,json,urllib.request,urllib.parse,ssl
from datetime import datetime,timezone
from pathlib import Path

ALLOWED={"nfl.com","www.nfl.com"}
def source_url(value):
    p=urllib.parse.urlsplit(str(value or ""))
    if p.scheme!="https" or p.hostname not in ALLOWED or p.username or p.password or p.port not in (None,443):
        raise ValueError("Source must be a direct HTTPS nfl.com URL")
    return p.geturl()
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError("Redirects forbidden: verify the canonical NFL source URL")

def retrieve(url,opener=None):
    canonical=source_url(url)
    client=opener or urllib.request.build_opener(NoRedirect)
    req=urllib.request.Request(canonical,headers={"User-Agent":"FOURTHDOWN-source-evidence/1.0","Accept":"text/html"})
    with client.open(req,timeout=15) as response:
        final=source_url(response.geturl())
        if final!=canonical: raise ValueError("Unexpected final URL")
        ctype=response.headers.get("Content-Type","").lower()
        if "text/html" not in ctype: raise ValueError("Not an HTML report")
        data=response.read(2_000_001)
        if len(data)>2_000_000: raise ValueError("Source exceeds 2 MB")
        if not data: raise ValueError("Empty report")
        return {"url":canonical,"bytes":len(data),"retrieved_at_utc":datetime.now(timezone.utc).isoformat(),"http_status":response.status,"content_type":ctype}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-url",action="append",default=[],help="Direct official nfl.com report URL; may repeat")
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    reports=[];errors=[]
    for url in a.source_url:
        try: reports.append(retrieve(url))
        except Exception as exc: errors.append({"url":url,"error":str(exc)})
    result={"status":"official_site_evidence_only","generated_at_utc":datetime.now(timezone.utc).isoformat(),"reports":reports,"errors":errors,"game_day_status_verified":False,"note":"Fetching official-site HTML does not prove report date, game, player identity or inactive designation. No eligibility changes or betting recommendations."}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+"\n")
    print("Official NFL page fetches:",len(reports),"errors:",len(errors),"; no game-day status certification")
if __name__=="__main__":main()
