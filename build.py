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
        for f in ("cuisine", "why", "price_note", "reservations", "what_to_order", "vibe", "hours_note", "accolades", "say", "heads_up", "tip"):
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
PUBLIC_FIELDS = ("id", "name", "address", "neighborhood", "lat", "lng", "category", "cuisine", "price",
                 "price_note", "reservations", "booking_url", "website", "hours_note", "what_to_order", "vibe",
                 "why", "accolades", "tags", "host_pick", "say", "heads_up", "tip", "sources")
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
print(f"{len(out)} places, {sum(1 for p in out if p.get('say'))} with notes")
for x in problems:
    print("WARN", x)

# cache-bust: point index.html at data.js?v=<content hash> so updates show immediately
v = hashlib.sha1(pathlib.Path("data.js").read_bytes()).hexdigest()[:8]
idx = pathlib.Path("index.html")
idx.write_text(re.sub(r'<script src="data\.js(\?v=[0-9a-f]+)?"></script>', f'<script src="data.js?v={v}"></script>', idx.read_text()))
