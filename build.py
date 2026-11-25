"""Merge researched place JSON + diner-review JSON into data.js for the map page.

Usage: python3 build.py <places.json>... --reviews <reviews.json>... [--host-picks name,name]
"""
import json, re, sys, datetime, pathlib, hashlib

args = sys.argv[1:]
places_files, review_files, host = [], [], set()
mode = places_files
i = 0
while i < len(args):
    a = args[i]
    if a == "--reviews":
        mode = review_files
    elif a == "--host-picks":
        i += 1
        host = {s.strip().lower() for s in args[i].split(",")}
    else:
        mode.append(a)
    i += 1

key = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
reviews = {}
for f in review_files:
    for r in json.load(open(f)):
        reviews[key(r["name"])] = r

out, problems = [], []
for f in places_files:
    for p in json.load(open(f)):
        try:
            p["lat"], p["lng"] = float(p["lat"]), float(p["lng"])
        except (TypeError, ValueError, KeyError):
            problems.append(f"no coords: {p.get('name')}")
            p["lat"] = p["lng"] = None
        if p["lat"] is not None and not (40.4 < p["lat"] < 41.0 and -74.3 < p["lng"] < -73.6):
            problems.append(f"coords outside NYC: {p['name']} {p['lat']},{p['lng']}")
        if p.get("category") not in ("eat", "drink", "do"):
            problems.append(f"bad category: {p.get('name')} {p.get('category')}")
        if not p.get("what_to_order") and p.get("what_to_do_there"):
            p["what_to_order"] = p.pop("what_to_do_there")
        fx = (reviews.get(key(p["name"])) or {}).get("fixes") or {}
        p.update({k: v for k, v in fx.items() if v})
        p["host_pick"] = key(p["name"]) in {key(h) for h in host}
        r = reviews.get(key(p["name"]))
        if r:
            p["reddit"] = {  # field name kept for the page template
                "verdict": r.get("verdict") or r.get("reddit_verdict"),
                "summary": r.get("summary") or r.get("reddit_summary"),
                "complaints": r.get("complaints") or r.get("real_complaints") or [],
                "tips": r.get("tips") or r.get("booking_tips") or "",
                "threads": r.get("threads", []),
            }
        if "reddit" in pathlib.Path(f).name:
            p["tags"] = sorted(set((p.get("tags") or []) + ["crowd-favorite"]))
        p["id"] = key(p["name"])
        out.append(p)

copy_path = pathlib.Path("research/copy.json")
if copy_path.exists():
    copy = json.loads(copy_path.read_text())
    for p in out:
        c = copy.get(p["id"])
        if not c:
            problems.append(f"no copy: {p['name']}")
            continue
        for f in ("cuisine", "why", "price_note", "reservations", "what_to_order", "vibe", "hours_note", "accolades", "say", "heads_up", "tip", "note"):
            if f in c:
                p[f] = c[f]
        if "reddit" in p:
            p["reddit"]["summary"] = c.get("review_summary", p["reddit"]["summary"])
            p["reddit"]["complaints"] = c.get("review_complaints", p["reddit"]["complaints"])
            p["reddit"]["tips"] = c.get("review_tips", p["reddit"]["tips"])
rn_path = pathlib.Path("research/reddit_notes.json")
if rn_path.exists():
    rn = {key(k): v for k, v in json.loads(rn_path.read_text()).items()}
    extra = pathlib.Path("research/reddit_notes_added.json")
    if extra.exists():
        rn.update({key(k): v for k, v in json.loads(extra.read_text()).items()})
    for p in out:
        v = rn.get(p["id"])
        if v and v.get("verdict") != "thin":
            p["rd"] = {"verdict": v["verdict"], "note": v.get("note", ""), "gripes": v.get("gripes", []),
                       "tip": v.get("tip", ""), "threads": v.get("threads", [])}
PUBLIC_DROP = ("notes", "rd")  # research notes + community-thread data never ship
# reader-facing cleanup: one consistent neighborhood list, a short human "vibe" list, tidy names
HOOD_MAP = {"West Village": "West & Greenwich Village", "Greenwich Village": "West & Greenwich Village",
    "Flatiron": "Flatiron, NoMad & Gramercy", "NoMad": "Flatiron, NoMad & Gramercy", "NoMad / Rose Hill": "Flatiron, NoMad & Gramercy",
    "Gramercy": "Flatiron, NoMad & Gramercy", "Chelsea": "Chelsea & Hudson Yards", "Hudson Yards": "Chelsea & Hudson Yards",
    "East Village": "East Village & Lower East Side", "Lower East Side": "East Village & Lower East Side",
    "SoHo": "SoHo, Nolita & Tribeca", "NoLita / NoHo border": "SoHo, Nolita & Tribeca", "Tribeca": "SoHo, Nolita & Tribeca",
    "Midtown (Fifth Ave)": "Midtown", "Midtown East": "Midtown", "Midtown (Grand Central)": "Midtown",
    "Lincoln Square / Columbus Circle": "Lincoln Center & Columbus Circle", "Columbus Circle": "Lincoln Center & Columbus Circle",
    "Lincoln Center, Upper West Side": "Lincoln Center & Columbus Circle",
    "Boerum Hill, Brooklyn": "Brooklyn", "Greenpoint": "Brooklyn"}
TAG_MAP = {"splurge": "Splurge", "luxe": "Splurge", "tasting-menu": "Tasting menu", "hard-to-book": "Hard to book",
    "walk-in": "Walk-ins welcome", "date-night": "Date night", "cocktails": "Cocktails", "late-night": "Late night",
    "classic": "Classic New York", "historic": "Classic New York", "hotel": "Hotel bar", "hot-new": "New this year",
    "queer": "Queer bars", "brunch": "Brunch", "culture": "Museums & culture", "museum": "Museums & culture",
    "art": "Museums & culture", "delivery": "Delivery", "crowd-favorite": "Crowd favorite", "holiday": "Holiday season",
    "spa": "Spa", "casual": "Casual"}
NAME_MAP = {"King Cole Bar (St. Regis)": "King Cole Bar at the St. Regis", "Raines Law Room (Chelsea)": "Raines Law Room",
    "The Met Opera (December)": "The Met Opera",
    "NYC Ballet: George Balanchine's The Nutcracker": "The Nutcracker at NYC Ballet", "Nordstrom NYC Flagship": "Nordstrom (57th St flagship)"}
PRICE_FIX = {"bordertown": "$$", "iara": "$$", "bemelmansbar": "$$$", "minettatavern": "$$$$",
             "fifthaveholidaywindowssakslightshow": "Free", "fifthavenueholidaywindowsandthesakslightshow": "Free"}
TAG_DROP = {"clementatthepeninsulanewyork": {"hotel"}, "clementatthepeninsula": {"hotel"},
            "thefrickcollectionmonkmanatthecabinetgallery": {"luxe", "splurge"}, "thefrickkentmonkmanshow": {"luxe", "splurge"},
            "iara": {"late-night"}}
TAG_ADD = {"graciela": {"date-night", "splurge"}}
ov_path = pathlib.Path("research/overrides.json")
overrides = json.loads(ov_path.read_text()) if ov_path.exists() else {}
for p in out:
    p["tags"] = sorted((set(p.get("tags") or []) - TAG_DROP.get(p["id"], set())) | TAG_ADD.get(p["id"], set()))
    if p["id"] in PRICE_FIX: p["price"] = PRICE_FIX[p["id"]]
    p.update({k: v for k, v in overrides.get(p["id"], {}).items() if v})
VOCAB = {"Splurge", "Tasting menu", "Hard to book", "Walk-ins welcome", "Date night", "Cocktails", "Wine bar", "Late night",
         "Classic New York", "Hotel bar", "New this year", "Queer bars", "Brunch", "Coffee & breakfast", "Museums & culture",
         "Shows & music", "Holiday season", "Spa", "Shopping", "Views", "Delivery", "Easy on the feet"}
tags_path, access_path = pathlib.Path("research/tags.json"), pathlib.Path("research/access.json")
TAGS = json.loads(tags_path.read_text()) if tags_path.exists() else {}
ACCESS = json.loads(access_path.read_text()) if access_path.exists() else {}
for p in out:
    p["neighborhood"] = HOOD_MAP.get(p.get("neighborhood"), p.get("neighborhood"))
    raw = TAGS.get(p["id"], p.get("tags") or [])
    p["tags"] = sorted({t if t in VOCAB else TAG_MAP.get(t) for t in raw} - {None})
    a = ACCESS.get(p["id"])
    if a:
        p["access"] = a.get("access", "")
        if a.get("easy"): p["tags"] = sorted(set(p["tags"]) | {"Easy on the feet"})
        else: p["tags"] = [t for t in p["tags"] if t != "Easy on the feet"]
    p["name"] = NAME_MAP.get(p["name"], p["name"])
PUBLIC_FIELDS = ("id", "name", "address", "neighborhood", "lat", "lng", "category", "cuisine", "price",
                 "price_note", "reservations", "booking_url", "website", "hours_note", "what_to_order", "vibe",
                 "why", "accolades", "tags", "host_pick", "note", "say", "heads_up", "tip", "access")
out = [{k: p[k] for k in PUBLIC_FIELDS if k in p} for p in out]  # allowlist: only what the page shows
body = json.dumps(out, indent=1, ensure_ascii=False)
body = re.sub(r"\s*\(unverified[^)]*\)", " (check before going)", body)
body = re.sub(r"\bunverified\b", "not confirmed", body, flags=re.I)
page_copy = copy.get("_page", {}) if copy_path.exists() else {}
pathlib.Path("data.js").write_text(
    f"window.PAGE_COPY={json.dumps(page_copy, ensure_ascii=False)};\n"
    f"window.PLACES_UPDATED={json.dumps(datetime.date.today().isoformat())};\n"
    f"window.PLACES={body};\n"
)
print(f"{len(out)} places, {sum(1 for p in out if p.get('note'))} with notes")
for x in problems:
    print("WARN", x)

# cache-bust: point index.html at data.js?v=<content hash> so updates show immediately
v = hashlib.sha1(pathlib.Path("data.js").read_bytes()).hexdigest()[:8]
idx = pathlib.Path("index.html")
idx.write_text(re.sub(r'<script src="data\.js(\?v=[0-9a-f]+)?"></script>', f'<script src="data.js?v={v}"></script>', idx.read_text()))

# bake page copy (intro + check note) into index.html so it shows without JS or cache lag
if page_copy:
    t = idx.read_text()
    if page_copy.get("lede"):
        t = re.sub(r'<p class="lede" id="lede">.*?</p>', lambda m: f'<p class="lede" id="lede">{page_copy["lede"]}</p>', t, flags=re.S)
    if page_copy.get("checknote"):
        t = re.sub(r'<p class="checknote" id="checknote">.*?</p>', lambda m: f'<p class="checknote" id="checknote">{page_copy["checknote"]}</p>', t, flags=re.S)
    idx.write_text(t)

# agent-readable copy: a plain-text list of every place inside <noscript>, so AI agents that read raw HTML see it
import html as _h
rows = []
for p in sorted(out, key=lambda x: (x["category"], x["name"])):
    bits = [f"<h3>{_h.escape(p['name'])}</h3>",
            f"<p>{_h.escape(p['category'].title())} · {_h.escape(p.get('neighborhood',''))} · {_h.escape(p.get('cuisine',''))} · {_h.escape(p.get('price',''))}</p>"]
    for label, f in (("Why", "why"), ("Notes", "note"), ("Cost", "price_note"), ("Getting in", "reservations"),
                     ("Get this", "what_to_order"), ("The feel", "vibe"), ("Access", "access"), ("Hours", "hours_note"),
                     ("Address", "address"), ("Book", "booking_url"), ("Website", "website")):
        if p.get(f): bits.append(f"<p>{label}: {_h.escape(str(p[f]))}</p>")
    if p.get("tags"): bits.append(f"<p>Tags: {_h.escape(', '.join(p['tags']))}</p>")
    rows.append("<article>" + "".join(bits) + "</article>")
block = '<noscript id="agent-list"><h2>All places</h2>' + "".join(rows) + "</noscript>"
t = idx.read_text()
t = re.sub(r'<noscript id="agent-list">.*?</noscript>', lambda m: block, t, flags=re.S) if 'id="agent-list"' in t else t.replace('<p class="note" id="footnote"></p>', '<p class="note" id="footnote"></p>\n' + block)
idx.write_text(t)
