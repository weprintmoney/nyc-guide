"""Merge researched place JSON + diner-review JSON into data.js for the map page.

Usage: python3 build.py <places.json>... --reviews <reviews.json>... [--host-picks name,name]
"""
import json, re, sys, datetime, pathlib

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
        for f in ("cuisine", "why", "price_note", "reservations", "what_to_order", "vibe", "hours_note", "accolades"):
            if f in c:
                p[f] = c[f]
        if "reddit" in p:
            p["reddit"]["summary"] = c.get("review_summary", p["reddit"]["summary"])
            p["reddit"]["complaints"] = c.get("review_complaints", p["reddit"]["complaints"])
            p["reddit"]["tips"] = c.get("review_tips", p["reddit"]["tips"])
PUBLIC_DROP = ("notes",)  # internal research notes never ship
for p in out:
    for f in PUBLIC_DROP:
        p.pop(f, None)
body = json.dumps(out, indent=1, ensure_ascii=False)
body = re.sub(r"\s*\(unverified[^)]*\)", " (check before going)", body)
body = re.sub(r"\bunverified\b", "not confirmed", body, flags=re.I)
pathlib.Path("data.js").write_text(
    f"window.PLACES_UPDATED={json.dumps(datetime.date.today().isoformat())};\n"
    f"window.PLACES={body};\n"
)
print(f"{len(out)} places, {sum(1 for p in out if 'reddit' in p)} with reviews")
for x in problems:
    print("WARN", x)
