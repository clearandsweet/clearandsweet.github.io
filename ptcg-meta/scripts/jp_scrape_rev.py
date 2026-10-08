"""Scrape JP major events (bulk decklist pages) and City League lists from limitlesstcg.com.
Usage: python3 -I jp_scrape.py OUTDIR SINCE(YYYY-MM-DD) MAJOR_IDS(comma)
"""
import json, os, re, sys, time, html, urllib.request, datetime
OUT, SINCE, MAJORS = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
BASE = "https://limitlesstcg.com"
def get(path):
    for i in range(5):
        try:
            req = urllib.request.Request(BASE + path, headers={"User-Agent": "Mozilla/5.0 (ptcg-meta-research)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(2 * (2 ** i))
    return ""
def text(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()
CARD_RE = re.compile(r'<div class="decklist-card" data-set="([^"]*)" data-number="([^"]*)" data-lang="([^"]*)".*?<span class="card-count">([^<]*)</span>\s*<span class="card-name">([^<]*)</span>', re.S)
def parse_list_block(block):
    cards = []
    cols = re.split(r'<div class="decklist-column-heading">', block)
    for col in cols[1:]:
        heading = text(col.split("</div>", 1)[0])
        cat = "pokemon" if heading.startswith("Pok") else ("energy" if heading.startswith("Energy") else "trainer")
        for st, num, lang, cnt, name in CARD_RE.findall(col):
            cards.append({"count": int(cnt), "name": html.unescape(name), "set": st, "number": num, "lang": lang, "cat": cat})
    m = re.search(r'<div class="decklist-title">\s*(.*?)\s*<', block, re.S)
    return (text(m.group(1)) if m else None), cards
def save(p, o):
    json.dump(o, open(p + ".tmp", "w"), ensure_ascii=False); os.replace(p + ".tmp", p)

# majors
for tid in MAJORS:
    p = os.path.join(OUT, f"major_{tid}.json")
    if os.path.exists(p):
        continue
    s = get(f"/tournaments/{tid}/decklists")
    title = text(re.search(r"<title>(.*?)</title>", s, re.S).group(1))
    parts = s.split('<div class="tournament-decklist">')[1:]
    lists = []
    for part in parts:
        label = text(re.search(r'data-toggle data-target="[^"]*">(.*?)</div>', part, re.S).group(1))
        deck, cards = parse_list_block(part)
        m = re.match(r"(\d+)\w*\s+(.*)", label)
        lists.append({"placing": int(m.group(1)) if m else None, "player": m.group(2) if m else label, "deck": deck, "cards": cards})
    save(p, {"id": tid, "title": title, "lists": lists})
    print("major", tid, title, len(lists), flush=True)
    time.sleep(1)

# city leagues
idx_p = os.path.join(OUT, "cityleague_index.json")
events = json.load(open(idx_p)) if os.path.exists(idx_p) else []
if not events:
    page = 1
    while True:
        s = get(f"/tournaments/jp?show=100&page={page}")
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", s, re.S)[1:]
        stop = False
        for r in rows:
            link = re.search(r'href="(?:https://limitlesstcg.com)?/tournaments/jp/(\d+)"', r)
            cells = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
            if not link or not cells:
                continue
            d = datetime.datetime.strptime(cells[0], "%d %b %y").date().isoformat()
            if d < SINCE:
                stop = True; continue
            events.append({"id": link.group(1), "date": d, "pref": cells[1] if len(cells) > 1 else None, "shop": cells[2] if len(cells) > 2 else None})
        print("index page", page, len(events), flush=True)
        if stop or not rows:
            break
        page += 1; time.sleep(1)
    save(idx_p, events)
cl_p = os.path.join(OUT, "cityleague_lists_rev.json"); events = events[::-1]
done = json.load(open(cl_p)) if os.path.exists(cl_p) else {}
for n, ev in enumerate(events):
    if ev["id"] in done:
        continue
    s = get(f"/tournaments/jp/{ev['id']}")
    title = text(re.search(r"<title>(.*?)</title>", s, re.S).group(1)).replace(" – Limitless", "")
    pm = re.search(r"\n\s*•\s*([\d,]+)\s*Players", s)
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", s, re.S)[1:]
    entries = []
    for r in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)
        lm = re.search(r'/decks/list/jp/(\d+)', r)
        dm = re.search(r'/decks/(\d+)[^"]*"', r)
        icons = re.findall(r'<img class="pokemon"[^>]*alt="([^"]+)"', r)
        if not cells:
            continue
        place = text(cells[0])
        entries.append({"placing": int(place) if place.isdigit() else None, "player": text(cells[1]) if len(cells) > 1 else None,
                        "deck_id": dm.group(1) if dm else None, "icons": icons, "deck": None,
                        "list_id": lm.group(1) if lm else None})
    for e in entries:
        if e["list_id"]:
            ls = get(f"/decks/list/jp/{e['list_id']}")
            deck, cards = parse_list_block(ls)
            e["cards"] = cards
            e["deck"] = e["deck"] or deck
            time.sleep(0.6)
    done[ev["id"]] = {**ev, "title": title, "entries": entries}
    if n % 5 == 0:
        save(cl_p, done)
        print("cityleague", n + 1, "/", len(events), flush=True)
save(cl_p, done)
print("done", len(done), flush=True)
