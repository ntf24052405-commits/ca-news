#!/usr/bin/env python3
"""Fetch CA-related news feeds and rebuild index.html. Standard library only."""
import json, re, sys, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

IST = timezone(timedelta(hours=5, minutes=30))

def gn(q):  # Google News RSS search, India edition, last 14 days
    return ("https://news.google.com/rss/search?q=" + urllib.parse.quote(q + " when:14d")
            + "&hl=en-IN&gl=IN&ceid=IN:en")

FEEDS = [
    gn('CBDT OR "Income-tax Act 2025" OR "Income-tax Rules 2026"'),
    gn('"GST Council" OR CBIC OR "GST notification"'),
    gn('ICAI OR "Institute of Chartered Accountants of India"'),
    gn('"Companies Act" OR MCA OR NCLT'),
    gn('SEBI OR RBI circular compliance'),
    gn('"tax audit" OR "ITR due date" OR TDS'),
    "https://taxguru.in/feed/",   # edit/add feeds here; any RSS URL works
]

CATS = [
    ("GST", r"\bgst\b|cbic|gstn"),
    ("ICAI", r"icai|chartered accountant|udin|\bca (final|inter|exam)"),
    ("Companies Act", r"companies act|\bmca\b|nclt|\broc\b|llp"),
    ("Markets & Regulators", r"sebi|\brbi\b|stock|ind as|nfra"),
    ("Income Tax", r"income.tax|cbdt|\bitr\b|\btds\b|tax audit|itat|section \d+"),
]

def category(text):
    t = text.lower()
    for name, pat in CATS:
        if re.search(pat, t):
            return name
    return "Other"

def parse(xml_bytes):
    out = []
    root = ET.fromstring(xml_bytes)
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = it.findtext("pubDate")
        if not title or not link or not pub:
            continue
        try:
            dt = parsedate_to_datetime(pub).astimezone(IST)
        except Exception:
            continue
        src = it.find("source")
        out.append({"t": title, "u": link, "d": dt.strftime("%Y-%m-%d"),
                    "ts": int(dt.timestamp()),
                    "s": (src.text if src is not None and src.text else
                          urllib.parse.urlparse(link).netloc),
                    "c": category(title)})
    return out

def fetch_all():
    items, seen = [], set()
    for url in FEEDS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 CA-News"})
            data = urllib.request.urlopen(req, timeout=25).read()
            for x in parse(data):
                key = re.sub(r"\W+", "", x["t"].lower())[:80]
                if key not in seen:
                    seen.add(key); items.append(x)
        except Exception as e:
            print("skip feed:", url[:70], e, file=sys.stderr)
    items.sort(key=lambda x: -x["ts"])
    return items[:300]

PAGE = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="900"><title>CA Live Update</title>
<style>
:root{--bg:#faf8f3;--card:#fff;--ink:#1d2433;--mut:#5f6879;--line:#e4e0d6;--acc:#0f5c4d;--accbg:#e1f0ec}
@media(prefers-color-scheme:dark){:root{--bg:#14171d;--card:#1d222b;--ink:#e8eaee;--mut:#9aa3b2;--line:#2c333f;--acc:#5fc9b0;--accbg:#173a33}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif}
main{max-width:720px;margin:0 auto;padding:18px 14px 40px}h1{font:700 26px Georgia,serif;margin:4px 0}
.m{color:var(--mut);font-size:13px}input{box-sizing:border-box;padding:10px;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--ink);font:15px system-ui}
#q{width:100%}.r{display:flex;gap:8px;margin:10px 0;align-items:center}.r input{flex:1}
.chips{display:flex;gap:6px;overflow-x:auto;padding:8px 0}.chip{flex:none;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:99px;padding:6px 12px;font-size:13px;cursor:pointer}
.chip[aria-pressed=true]{background:var(--acc);color:var(--bg);border-color:var(--acc)}
.tabs{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin:14px 0 4px;position:sticky;top:0;background:var(--bg);padding:6px 0;z-index:2}
.tabs button{padding:11px;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--ink);font:600 15px system-ui;cursor:pointer}
.tabs button[aria-selected=true]{background:var(--acc);color:var(--bg);border-color:var(--acc)}
a.i{display:block;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:11px 13px;margin:9px 0;color:inherit;text-decoration:none}
.tag{font:600 11px system-ui;text-transform:uppercase;letter-spacing:.5px;background:var(--accbg);color:var(--acc);border-radius:6px;padding:2px 7px}
.t{margin:6px 0 2px;font-weight:600}.e{text-align:center;color:var(--mut);padding:24px}
</style></head><body><main>
<h1>CA Live Update</h1>
<div class="m">Auto-updated: __STAMP__ IST · rebuilt every 3 hours · page reloads every 15 min</div>
<div class="tabs" role="tablist"><button id="t1" role="tab" aria-selected="true">All news</button><button id="t2" role="tab" aria-selected="false">News by date</button></div>

<section id="s1">
<input id="q" type="search" placeholder="Search all news…"><div class="chips" id="chips"></div><div id="l1"></div>
</section>

<section id="s2" hidden>
<div class="r"><button class="chip" id="prev">‹</button><input id="dt" type="date"><button class="chip" id="next">›</button></div>
<div class="m">Recent days with news:</div><div class="chips" id="days"></div>
<div class="m" id="cnt"></div><div id="l2"></div>
</section>

<p class="m">Headlines come from public news feeds and link to the publisher. Verify against the official notification before acting.</p>
</main><script>
var D=__DATA__,cat="All",C=["All","Income Tax","GST","ICAI","Companies Act","Markets & Regulators","Other"];
var $=function(i){return document.getElementById(i)};
function card(x){var a=document.createElement("a");a.className="i";a.href=x.u;a.target="_blank";a.rel="noopener";
var g=document.createElement("span");g.className="tag";g.textContent=x.c;var t=document.createElement("div");t.className="t";t.textContent=x.t;
var m=document.createElement("div");m.className="m";m.textContent=x.d+" · "+x.s;a.append(g,t,m);return a}
function fill(el,arr,msg){el.innerHTML="";if(!arr.length){el.innerHTML='<div class="e">'+msg+'</div>';return}arr.forEach(function(x){el.appendChild(card(x))})}
function chips(){$("chips").innerHTML="";C.forEach(function(c){var b=document.createElement("button");b.className="chip";b.textContent=c;b.setAttribute("aria-pressed",c===cat);b.onclick=function(){cat=c;chips();all()};$("chips").appendChild(b)})}
function all(){var q=$("q").value.toLowerCase();fill($("l1"),D.filter(function(x){return(cat==="All"||x.c===cat)&&(!q||x.t.toLowerCase().indexOf(q)>=0)}),"No news matches.")}
function byDate(){var v=$("dt").value,r=D.filter(function(x){return x.d===v});$("cnt").textContent=v?r.length+" item(s) on "+v:"";fill($("l2"),r,"No news found for this date.");
Array.prototype.forEach.call($("days").children,function(b){b.setAttribute("aria-pressed",b.dataset.d===v)})}
function shift(n){var v=$("dt").value||D[0].d,d=new Date(v+"T00:00:00Z");d.setUTCDate(d.getUTCDate()+n);$("dt").value=d.toISOString().slice(0,10);byDate()}
function days(){var c={};D.forEach(function(x){c[x.d]=(c[x.d]||0)+1});Object.keys(c).sort().reverse().slice(0,10).forEach(function(k){var b=document.createElement("button");b.className="chip";b.dataset.d=k;b.textContent=k.slice(5)+" ("+c[k]+")";b.onclick=function(){$("dt").value=k;byDate()};$("days").appendChild(b)})}
function tab(n){$("s1").hidden=n!==1;$("s2").hidden=n!==2;$("t1").setAttribute("aria-selected",n===1);$("t2").setAttribute("aria-selected",n===2)}
$("t1").onclick=function(){tab(1)};$("t2").onclick=function(){tab(2)};
$("q").oninput=all;$("dt").onchange=byDate;$("prev").onclick=function(){shift(-1)};$("next").onclick=function(){shift(1)};
if(D.length){$("dt").value=D[0].d}chips();all();days();byDate();
</script></body></html>"""

def build(items):
    stamp = datetime.now(IST).strftime("%d %b %Y, %H:%M")
    data = json.dumps(items, ensure_ascii=False).replace("</", "<\\/")
    return PAGE.replace("__STAMP__", stamp).replace("__DATA__", data)

if __name__ == "__main__":
    items = fetch_all()
    if not items:
        sys.exit("No items fetched; keeping existing index.html")
    open("index.html", "w", encoding="utf-8").write(build(items))
    print("Wrote index.html with", len(items), "items")
