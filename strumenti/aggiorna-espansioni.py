"""Rigenera espansioni.json.

Uso: python3 strumenti/aggiorna-espansioni.py
Serve solo quando escono nuove espansioni.

Fonti:
- TCGdex (api.tcgdex.net): elenco, nomi italiani, simboli e loghi.
- pokemon-tcg-data (GitHub, immagini su images.pokemontcg.io / images.scrydex.com):
  simboli e loghi dei set che TCGdex non ha.
- TCGplayer tramite tcgcsv.com: per i set che non hanno un simbolo (Trainer Kit,
  McDonald's, My First Battle...) la scansione di una loro carta, da mostrare al posto del simbolo.
Nel file ci sono solo gli indirizzi: le immagini restano sui siti d'origine.
"""
import concurrent.futures as cf
import json
import pathlib
import re
import struct
import urllib.error
import urllib.request

API = "https://api.tcgdex.net/v2"
PTCG_SETS = "https://raw.githubusercontent.com/PokemonTCG/pokemon-tcg-data/master/sets/en.json"
# Alcuni server rifiutano le richieste senza un User-Agent.
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ricercaDB/1.0; +https://github.com/claudio-git-poke/ricercaDB)"}
TCGCSV = "https://tcgcsv.com/tcgplayer/3"
TCGP_IMG = "https://tcgplayer-cdn.tcgplayer.com/product/{}_in_1000x1000.jpg"
# set TCGdex senza simbolo -> gruppo TCGplayer e, per i kit, il Pokémon che dà il nome al mazzo
NO_SYMBOL_GROUPS = {
    "30th": (24722, ""), "30th-c": (24837, ""), "mep": (24451, ""), "2024sv": (24163, ""), "2023sv": (23306, ""),
    "mfb": (23330, "Pikachu"), "jumbo": (1528, ""),
    "tk-sm-r": (2069, "Raichu"), "tk-sm-l": (2069, "Lycanroc"),
    "tk-xy-su": (1796, "Suicune"), "tk-xy-p": (1796, "Pikachu"),
    "tk-xy-latio": (1536, "Latios"), "tk-xy-latia": (1536, "Latias"),
    "tk-xy-w": (1533, "Wigglytuff"), "tk-xy-b": (1533, "Bisharp"),
    "tk-xy-sy": (1532, "Sylveon"), "tk-xy-n": (1532, "Noivern"),
    "tk-bw-z": (1538, "Zoroark"), "tk-bw-e": (1538, "Excadrill"),
    "tk-hs-r": (1540, "Raichu"), "tk-hs-g": (1540, "Gyarados"),
    "tk-dp-m": (1541, "Manaphy"), "tk-dp-l": (1541, "Lucario"),
}
OUT = pathlib.Path(__file__).resolve().parent.parent / "espansioni.json"


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30) as r:
        return json.load(r)


def exists(url):
    req = urllib.request.Request(url, method="HEAD", headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 200 and r.headers.get("content-type", "").startswith("image/")
    except urllib.error.URLError:
        return False


def png_size(url):
    """Larghezza e altezza di un PNG leggendo solo l'intestazione."""
    try:
        req = urllib.request.Request(url, headers={**HEADERS, "Range": "bytes=0-31"})
        with urllib.request.urlopen(req, timeout=30) as r:
            head = r.read(32)
    except urllib.error.URLError:
        return None
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def plausible_symbol(url):
    """Un simbolo di espansione è piccolo e quasi quadrato: scarta loghi messi al posto del simbolo."""
    size = png_size(url)
    return bool(size) and max(size) <= 600 and max(size) <= 3 * min(size)


def norm(name):
    return re.sub(r"[^a-z0-9]+", "", name.lower().replace("&", "and"))


def image(url):
    """TCGdex dà l'indirizzo senza estensione e a volte sotto univ/: provo le varianti note."""
    if not url:
        return ""
    for candidate in (url + ".png", url.replace("/univ/", "/en/") + ".png"):
        if exists(candidate):
            return candidate
    return ""


def one(item):
    d = get(f"{API}/en/sets/{item['id']}")
    abbr = (d.get("abbreviation") or {}).get("official") or d.get("tcgOnline") or ""
    return {
        "id": d["id"],
        "code": d["id"].upper(),
        "name": d["name"],
        "serie": (d.get("serie") or {}).get("name", ""),
        "year": (d.get("releaseDate") or "")[:4],
        "date": d.get("releaseDate") or "",
        "abbr": abbr,
        "total": (d.get("cardCount") or {}).get("official") or 0,
        "symbol": image(d.get("symbol")),
        "logo": image(d.get("logo")),
    }


def add_ptcg_images(rows):
    """Completa simboli e loghi mancanti con pokemon-tcg-data: stessa sigla, oppure stesso nome e stessa data."""
    ptcg = get(PTCG_SETS)
    by_code = {p["ptcgoCode"]: p for p in ptcg if p.get("ptcgoCode")}
    by_id = {p["id"].lower(): p for p in ptcg}
    by_name = {(norm(p["name"]), p["releaseDate"].replace("/", "-")): p for p in ptcg}
    by_name_only = {}
    for p in ptcg:
        by_name_only.setdefault(norm(p["name"]), []).append(p)

    def match(r):
        if r["abbr"] and r["abbr"] in by_code:
            return by_code[r["abbr"]]
        if (norm(r["name"]), r["date"]) in by_name:
            return by_name[(norm(r["name"]), r["date"])]
        same = by_name_only.get(norm(r["name"]), [])
        if len(same) == 1:
            return same[0]
        # stesso identificativo scritto nell'altro modo: sv08.5 -> sv8pt5, swsh01 -> swsh1
        alt = re.sub(r"(?<=[a-z])0+(?=\d)", "", r["id"].lower()).replace(".", "pt")
        return by_id.get(alt)

    def fill(r):
        p = match(r)
        if not p:
            return
        img = p.get("images") or {}
        if not r["symbol"] and img.get("symbol") and plausible_symbol(img["symbol"]):
            r["symbol"] = img["symbol"]
            r["source"] = "pokemon-tcg-data"
        if not r["logo"] and img.get("logo") and png_size(img["logo"]):
            r["logo"] = img["logo"]

    with cf.ThreadPoolExecutor(8) as pool:
        list(pool.map(fill, [r for r in rows if not r["symbol"] or not r["logo"]]))


def image_ok(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={**HEADERS, "Range": "bytes=0-15"}), timeout=30) as r:
            return r.read(3) == b"\xff\xd8\xff"
    except urllib.error.URLError:
        return False


def add_card_samples(rows):
    """Per i set senza simbolo, l'indirizzo della scansione di una loro carta su TCGplayer."""
    cache = {}
    for r in rows:
        if r["symbol"] or r["id"] not in NO_SYMBOL_GROUPS:
            continue
        group, wanted = NO_SYMBOL_GROUPS[r["id"]]
        if group not in cache:
            cache[group] = get(f"{TCGCSV}/{group}/products").get("results", [])
        cards = [p for p in cache[group] if any(e["name"] == "Number" for e in p.get("extendedData", []))] or cache[group]
        cards = [p for p in cards if wanted.lower() in p["name"].lower()] or cards
        for p in cards[:6]:
            url = TCGP_IMG.format(p["productId"])
            if image_ok(url):
                r["card"] = url
                break


def main():
    sets = get(f"{API}/en/sets")
    italian = {s["id"]: s["name"].strip() for s in get(f"{API}/it/sets")}
    with cf.ThreadPoolExecutor(8) as pool:
        rows = list(pool.map(one, sets))
    for r in rows:
        if italian.get(r["id"]) and italian[r["id"]] != r["name"]:
            r["it"] = italian[r["id"]]
    # TCG Pocket è digitale: il catalogo fisico non lo contiene.
    rows = [r for r in rows if "pocket" not in r["serie"].lower()]
    add_ptcg_images(rows)
    add_card_samples(rows)
    rows.sort(key=lambda r: (r["date"], r["id"]), reverse=True)
    for r in rows:
        del r["date"]
    OUT.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{len(rows)} espansioni, {sum(1 for r in rows if r['symbol'])} con simbolo, "
          f"{sum(1 for r in rows if r.get('card'))} con una carta d'esempio, "
          f"{sum(1 for r in rows if r['logo'])} con logo -> {OUT.name}")


if __name__ == "__main__":
    main()
