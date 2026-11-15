"""Rigenera foto-speciali.json: per le stampe speciali del catalogo, il prodotto TCGplayer con la loro scansione.

Uso: python3 strumenti/aggiorna-foto-speciali.py

Il catalogo registra Battle Academy, mazzi dei Mondiali, buste premio, Trick or Trade e My First Battle
senza una foto propria. TCGplayer (elenchi pubblici su tcgcsv.com) le vende come prodotti separati,
ognuno con la sua scansione. Lo script abbina le due cose e salva solo i numeri dei prodotti:
le immagini restano su tcgplayer-cdn.tcgplayer.com.

Le stampe che arrivano da TCGdex hanno già il numero TCGplayer nel catalogo: la pagina lo legge da sola.
"""
import json
import pathlib
import re
import unicodedata
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "foto-speciali.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ricercaDB/1.0; +https://github.com/claudio-git-poke/ricercaDB)"}
TCGCSV = "https://tcgcsv.com/tcgplayer/3/{}/products"

# Stessi indirizzo e chiave pubblica (sola lettura) di index.html.
API = "https://vjpvbsvpumzrqzoupxee.supabase.co/rest/v1/catalog_search_entries"
KEY = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZqcHZic3ZwdW16cnF6b3VweGVlIiwicm9sZSI6"
       "ImFub24iLCJpYXQiOjE3OTQ1NzMzNTQsImV4cCI6MjExMDE0OTM1NH0.PTxmaA8_5CyPz8tZclfgoRT2DexYvhCQg1hPn5azpGw")

BA_GROUPS = {2020: 2686, 2022: 3051, 2024: 23520}
TT_GROUPS = {2022: 3179, 2023: 23266, 2024: 23561}
WCD_GROUP, PPS_GROUP, MFB_GROUP = 2282, 22880, 23330
# nomi italiani usati dal catalogo per le carte My First Battle
MFB_NAMES = {"energia base acqua": "basic water energy", "energia base erba": "basic grass energy",
             "energia base fuoco": "basic fire energy", "energia base lampo": "basic lightning energy",
             "pozione": "potion", "scambio": "switch"}


def get(url, headers=None):
    with urllib.request.urlopen(urllib.request.Request(url, headers={**HEADERS, **(headers or {})}), timeout=90) as r:
        return json.load(r)


def norm(text):
    text = unicodedata.normalize("NFD", text or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", text)


def number(value):
    """018/147 -> 18, SWSH065 -> swsh65"""
    value = (value or "").split("/")[0].strip().lower()
    return re.sub(r"(?<![0-9])0+(?=[0-9])", "", value)


def base_name(product_name):
    """'Charmander - 18/147 (#1 Charizard Stamped)' -> 'charmander'"""
    name = re.sub(r"\s*[\(\[].*$", "", product_name)
    name = re.split(r"\s+-\s+", name)[0]
    return norm(name)


def ext(product, field):
    for e in product.get("extendedData", []):
        if e["name"] == field:
            return e["value"]
    return ""


def entries(tag):
    rows, offset = [], 0
    while True:
        q = urllib.parse.urlencode({
            "select": "entry_key,name,collector_number,label,tags,release_year,deck_code,deck_number,source_payload",
            "tags": "cs.{" + tag + "}", "limit": 1000, "offset": offset, "order": "entry_key"})
        page = get(API + "?" + q, {"apikey": KEY, "Authorization": "Bearer " + KEY})
        rows += page
        if len(page) < 1000:
            return rows
        offset += 1000


def products(group, numbered=True):
    return [p for p in get(TCGCSV.format(group)).get("results", []) if ext(p, "Number") or not numbered]


def match_battle_academy(found):
    for year, group in BA_GROUPS.items():
        by_slot, by_card = {}, {}
        for p in products(group):
            m = re.search(r"#?(\d+)\s+([A-Za-z]+)\s*Stamped|[-(]\s*([A-Za-z]+)\s+(\d+)\)?\s*$|\(([A-Za-z]+)\s+Stamped\)", p["name"])
            if not m:
                continue
            if m.group(1):
                deck, slot = m.group(2), int(m.group(1))
            elif m.group(3):
                deck, slot = m.group(3), int(m.group(4))
            else:
                deck, slot = m.group(5), None
            deck = norm(deck)
            if slot is not None:
                by_slot[(deck, slot)] = p["productId"]
            by_card.setdefault((deck, base_name(p["name"]), number(ext(p, "Number"))), p["productId"])
        for r in entries("family:battle-academy"):
            if r["release_year"] != year:
                continue
            deck = norm(r["deck_code"])
            pid = by_slot.get((deck, r["deck_number"])) if r["deck_number"] else None
            pid = pid or by_card.get((deck, norm(r["name"]), number(r["collector_number"])))
            if pid:
                found[r["entry_key"]] = pid


def match_worlds(found):
    index, by_name = {}, {}
    for p in products(WCD_GROUP, numbered=False):
        m = re.search(r"-\s*(\d{4})\s*\(([^)]+)\)", p["name"])
        if not m or "gold" in p["name"].lower():
            continue
        player = norm(m.group(2).split()[-1])
        index.setdefault((int(m.group(1)), player, number(ext(p, "Number")), base_name(p["name"])), p["productId"])
        index.setdefault((int(m.group(1)), player, number(ext(p, "Number")), ""), p["productId"])
        by_name.setdefault((int(m.group(1)), player, base_name(p["name"])), set()).add(p["productId"])
    for r in entries("family:world-championships"):
        words = ((r.get("source_payload") or {}).get("player") or "").split()
        player = norm(words[-1]) if words else ""
        key = (r["release_year"], player, number(r["collector_number"]))
        pid = index.get(key + (norm(r["name"]),)) or index.get(key + ("",))
        same = by_name.get((r["release_year"], player, norm(r["name"])), set())
        if not pid and len(same) == 1:  # prodotti senza numero (mazzi recenti): basta nome e giocatore
            pid = next(iter(same))
        if pid:
            found[r["entry_key"]] = pid


def match_by_name_number(found, tag, groups, year=None):
    index = {}
    for group in groups:
        for p in products(group):
            holo = "holo" in p["name"].lower()
            index.setdefault((base_name(p["name"]), number(ext(p, "Number")), holo), p["productId"])
    for r in entries(tag):
        if year and r["release_year"] != year:
            continue
        holo = "finish:holo" in r["tags"]
        key = (norm(r["name"]), number(r["collector_number"]))
        pid = index.get(key + (holo,)) or index.get(key + (not holo,))
        if pid:
            found[r["entry_key"]] = pid


def match_my_first_battle(found):
    index = {}
    for p in products(MFB_GROUP, numbered=False):
        m = re.match(r"(.+?)(?:\s*\((.+)\))?$", p["name"])
        index[(norm(m.group(1)), norm(m.group(2) or ""))] = p["productId"]
    for r in entries("family:my-first-battle"):
        name = MFB_NAMES.get(r["name"].lower(), r["name"])
        deck = norm(r.get("deck_code") or "")
        blue = "subtype:blue-border" in r["tags"]
        pid = (index.get((norm(name), "blueborder")) if blue else None) or index.get((norm(name), deck)) or index.get((norm(name), ""))
        if pid:
            found[r["entry_key"]] = pid


def main():
    found = {}
    match_battle_academy(found)
    match_worlds(found)
    match_by_name_number(found, "family:prize-pack", [PPS_GROUP])
    for year, group in TT_GROUPS.items():
        match_by_name_number(found, "family:trick-or-trade", [group], year)
    match_my_first_battle(found)
    OUT.write_text(json.dumps(dict(sorted(found.items())), separators=(",", ":")) + "\n", encoding="utf-8")
    counts = {}
    for k in found:
        fam = k.split(":")[0].rsplit("-", 1)[0] if not k.startswith(("card:", "tcgdex:")) else k.split(":")[0]
        counts[fam] = counts.get(fam, 0) + 1
    print(f"{len(found)} stampe abbinate -> {OUT.name}", counts)


if __name__ == "__main__":
    main()
