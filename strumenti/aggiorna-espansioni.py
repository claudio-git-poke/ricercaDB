"""Rigenera espansioni.json.

Uso: python3 strumenti/aggiorna-espansioni.py
Serve quando il catalogo aggiunge espansioni o simboli. Impiega qualche minuto.

Un elemento per ogni espansione presente nel catalogo pokemon-catalog (tutte le lingue), con TUTTI
i simboli e i loghi che l'archivio del catalogo (tabella catalog_visual_assets) le attribuisce.

Come si abbinano i simboli dell'archivio alle espansioni, dal più sicuro al meno sicuro:
1. regola del catalogo (match_code TCGdex) -> le carte TCGdex di quell'espansione;
2. identificativo nel nome del file (1niceroli, SilphGhost: sv3pt5, ja_sv2d, mcd19...);
3. nome inglese (pokesymbols, xero/pokemon), anche per i set giapponesi tramite l'elenco di Limitless.
I simboli digitali (TCG Pocket) e i segnaposto restano fuori.

Altre fonti, solo per nomi e date: TCGdex (nomi in italiano, serie, date, sigle ufficiali) e
limitlesstcg.com (nomi inglesi dei set giapponesi e sigle inglesi).
Per i set senza alcun simbolo resta, se c'è, la scansione di una loro carta su TCGplayer.
Nel file ci sono solo gli indirizzi: le immagini restano sui siti d'origine.
"""
import collections
import concurrent.futures as cf
import datetime
import html
import json
import pathlib
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ricercaDB/1.0; +https://github.com/claudio-git-poke/ricercaDB)"}
TCGDEX = "https://api.tcgdex.net/v2"
TCGDEX_LANGS = ["en", "it", "fr", "de", "es", "pt", "ja", "ko", "zh-tw", "zh-cn", "id", "th"]
LIMITLESS = {"en": "https://limitlesstcg.com/cards", "jp": "https://limitlesstcg.com/cards/jp"}
TCGCSV = "https://tcgcsv.com/tcgplayer/3"
TCGP_IMG = "https://tcgplayer-cdn.tcgplayer.com/product/{}_in_1000x1000.jpg"
# Stesso indirizzo di index.html: API pubblica in sola lettura del catalogo (Turso), senza chiavi.
CATALOG = "https://pokemon-catalog-zeta.vercel.app/api/catalog-db/rest/v1"
CATALOG_KEY = "catalog-public"
CATALOG_HEADERS = {**HEADERS, "apikey": CATALOG_KEY, "Authorization": "Bearer " + CATALOG_KEY}
# Fonti dell'archivio dalla più nitida alla meno nitida (TCGdex spesso ha simboli di 25 pixel).
SOURCE_RANK = ["PokemonSymbols", "Xero_Community", "1niceroli_AssetRepo", "SilphGhost", "PokemonTCG_Storico", "TCGdex", "DexTCG"]
# Immagini dell'archivio che non sono il simbolo stampato (segnaposto con la sola sigla) e il Set Base, che non ne ha.
NOT_A_SYMBOL = {"https://raw.githubusercontent.com/1niceroli/ptcg-assets/main/sv09/symbol.png",
                "https://raw.githubusercontent.com/1niceroli/ptcg-assets/main/sv9/symbol.png"}
NO_SYMBOL_IDS = {"base1", "base-expansion-pack"}
# Set senza simbolo stampato: gruppo TCGplayer e, per i kit, il Pokémon che dà il nome al mazzo.
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
# Identificativi e nomi dei file dell'archivio che non coincidono con TCGdex (pokemontcg.io, pokesymbols, xero/pokemon).
ALIASES = {
    "mcd11": "2011bw", "mcd12": "2012bw", "mcd14": "2014xy", "mcd15": "2015xy", "mcd16": "2016xy", "mcd17": "2017sm",
    "mcd18": "2018sm", "mcd19": "2019sm", "mcd21": "2021swsh", "mcd22": "2022swsh", "base6": "lc", "bp": "bog",
    "pgo": "swsh10.5", "fut20": "fut2020", "hsp": "hgssp", "cel25c": "cel25cc", "tk1a": "tk-ex-latia", "tk1b": "tk-ex-latio",
    "tk2a": "tk-ex-p", "tk2b": "tk-ex-m", "rsv10pt5": "sv10.5w", "zsv10pt5": "sv10.5b",
    "heart-gold-and-soul-silver": "hgss1", "firered-leafgreen": "ex6", "expedition": "ecard1", "ruby-and-sapphire-fixed": "ex1",
    "scarlet-and-violet-black-star-promos": "svp", "scarlet-and-violet-energies": "sve", "pokemon-futsal-collection": "fut2020",
    "fustal-promos": "fut2020", "xy-trainer-kit-libre-pikachu": "tk-xy-p", "mcdonalds-collection-dragon-discovery-2024": "2024sv",
    "30th-celebration-classic-collection": "30th-c", "sun-and-moon-trainer-kit-lycanroc": "tk-sm-l",
    "sun-and-moon-trainer-kit-alolan-raichu": "tk-sm-r", "sun-and-moon-trainer-kit-raichu": "tk-sm-r",
    "black-and-white-trainer-kit-zoroark": "tk-bw-z", "black-and-white-trainer-kit-excadrill": "tk-bw-e",
    "diamond-and-pearl-trainer-kit-lucario": "tk-dp-l", "diamond-and-pearl-trainer-kit-manaphy": "tk-dp-m",
    "heartgold-and-soulsilver-trainer-kit-raichu": "tk-hs-r", "heartgold-and-soulsilver-trainer-kit-gyarados": "tk-hs-g",
}
# Set giapponesi: nome inglese del file (xero/pokemon) o identificativo (1niceroli) -> sigla del catalogo.
# Per i set dal 2010 in poi basta l'elenco di Limitless; qui i più vecchi e le traduzioni diverse.
JP_ALIASES = {
    "base-expansion-pack": "PMCG1", "pokemon-jungle": "PMCG2", "mystery-of-the-fossils": "PMCG3", "rocket-gang": "PMCG4",
    "leaders-stadium": "PMCG5", "challenge-from-the-darkness": "PMCG6", "gold-silver-to-a-new-world": "NEO1",
    "crossing-the-ruins": "NEO2", "awakening-legends": "NEO3", "darkness-and-to-light": "NEO4", "pokemon-vs": "VS1",
    "the-town-on-no-map": "E2", "wind-from-the-sea": "E3", "split-earth": "E4", "mysterious-mountains": "E5",
    "flight-of-legends": "PCG1", "clash-of-the-blue-sky": "PCG2", "rocket-gang-strikes-back": "PCG3",
    "golden-sky-silvery-ocean": "PCG4", "mirage-forest": "PCG5", "holon-research-tower": "PCG6", "holon-phantom": "PCG7",
    "miracle-crystal": "PCG8", "offense-and-defense-of-the-furthest-ends": "PCG9", "world-champions-pack": "WCP",
    "space-time-creation-diamond-collection": "DP1", "pearl-collection": "DP1", "secret-of-the-lakes": "DP2",
    "shining-darkness": "DP3", "moonlit-pursuit": "DP4", "dawn-dash": "DP4", "temple-of-anger": "DP5",
    "cry-from-the-mysterious": "DP5", "galactics-conquest": "DPT1-B", "bonds-to-the-end-of-time": "DPT2-B",
    "beat-of-the-frontier": "DPT3-B", "advent-of-arceus": "DPT4-B", "heartgold-collection": "L1-BHG",
    "heart-gold-collection": "L1-BHG", "soulsilver-collection": "L1-BSS", "soul-silver-collection": "L1-BSS",
    "reviving-legends": "L2-B", "clash-at-the-summit": "L3-B", "lost-link": "LL", "thunder-knuckle": "BW8-BRN",
    "spiral-force": "BW8-BRF", "dragon-blast": "BW5-BRZ", "dragon-blade": "BW5-BRN", "darkness-that-consumes-light": "SM3N",
    "to-have-seen-the-battle-rainbow": "SM3H", "sky-splitting-charisma": "SM7", "ultradimensional-beasts": "SM4A",
    "facing-a-new-trial": "SM2P", "pikachus-new-friends": "SM0", "tag-team-gx-tag-all-stars": "SM12A",
    "great-detective-pikachu": "SMP2", "champion-road": "SM6B", "fever-burst-fighter": "XY11-BB", "cruel-traitor": "XY11-BR",
    "rage-of-the-broken-heavens": "XY9-B", "awakening-psychic-king": "XY10-B", "red-flash": "XY8-BR", "blue-shock": "XY8-BB",
    "premium-champion-pack": "CP4", "legendary-shine-collection": "CP2", "mythical-and-legendary-dream-shine-collection": "CP5",
    "magma-gang-vs-aqua-gang-double-crisis": "CP1", "expansion-pack-20th-anniversary": "CP6", "hot-wind-arena": "SV9A",
    "glory-of-the-rocket-gang": "SV10", "rebellion-crash": "S2", "peerless-fighters": "S5A",
    "xy-p-promotional-cards": "XY-P", "sm-p-promotional-cards": "SM-P", "s-p-promotional-cards": "S-P",
    "sv-p-promotional-cards": "SV-P", "m-p-promotional-cards": "M-P", "bw-p-promotional-cards": "BW-P",
    "l-p-promotional-cards": "L-P", "dp-p-promotional-cards": "DP-P", "dp-promos": "DP-P", "dpt-p-promotional-cards": "DPT-P",
    "dpt-promos": "DPT-P", "adv-p-promotional-cards": "ADV-P", "pcg-p-promotional-cards": "PCG-P", "p-promotional-cards": "P",
    "t-promotional-cards": "T", "j-promotional-cards": "J", "play-promotional-cards": "PLAY", "ppp-promotional-cards": "PPP",
    "ppp-promos": "PPP", "mc-donalds-original-minimum-pack": "MCDONALDS", "promo-card-pack-25th-anniversary-edition": "S8A-P",
    "southern-islands": "SI1", "svp": "SV-P", "sp": "S-P", "vs": "VS1", "base1": "PMCG1",
}
ASIA = {"JP": "Giappone", "KOR": "Corea", "CHN-T": "Taiwan e Hong Kong", "CHN": "Cina", "TH": "Thailandia", "ID": "Indonesia"}
OUT = pathlib.Path(__file__).resolve().parent.parent / "espansioni.json"


def fetch(url, headers=HEADERS, tries=4, raw=False):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
                data = r.read()
                return data.decode("utf-8") if raw else json.loads(data)
        except urllib.error.HTTPError as e:
            if e.code in (400, 403, 404):
                raise
        except (urllib.error.URLError, OSError, ValueError):
            pass
        time.sleep(2 + attempt * 3)  # errori passeggeri: riprova
    raise RuntimeError("non raggiungibile: " + url)


def alive(url):
    """L'immagine risponde davvero? (alcuni indirizzi dell'archivio non esistono più). GET intero: pokesymbols ignora Range."""
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=40) as r:
                head = r.read(4096)
                return r.status == 200 and (head[:4] in (b"\x89PNG", b"RIFF", b"GIF8") or head[:3] == b"\xff\xd8\xff" or b"<svg" in head)
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 410):
                return False
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(2 + attempt * 3)
    return True  # errore passeggero: non lo scarto


def catalog(path, params):
    return fetch(f"{CATALOG}/{path}?{urllib.parse.urlencode(params)}", CATALOG_HEADERS)


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower().replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "", s)


def asia_keys(code):
    """Sigle asiatiche equivalenti: XY8-BR dell'archivio ufficiale è XY8r di Limitless, BW1-BB è BW1b."""
    keys = {code.lower()}
    m = re.match(r"^([A-Z]+\d+)-B([A-Z]*)$", code.upper())
    if m:
        keys.add((m.group(1) + (m.group(2)[-1] if m.group(2) else "")).lower())
    return keys


def id_keys(code):
    """Forme equivalenti di un identificativo: sv03.5 = sv3pt5 = sv35, swsh01 = swsh1."""
    c = code.lower().replace("pt", ".") if re.search(r"\dpt\d", code.lower()) else code.lower()
    c = re.sub(r"(?<=[a-z])0+(?=\d)", "", c)
    return {c, c.replace(".", "")}


# ---------------- espansioni del catalogo ----------------

def catalog_codes():
    """Tutte le sigle delle carte (SV02@IT, SV2D@JP...), con la fonte della prima carta. Lettura a salti, in parallelo."""
    bounds = [""] + list("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ["￿"]
    parts = list(zip(bounds[:-1], bounds[1:]))

    def scan(part):
        start, end = part
        out, last = [], start
        while True:
            r = catalog("cards", {"select": "sigla,source_uid", "sigla": "gt." + last, "order": "sigla.asc", "limit": 1})
            if not r or r[0]["sigla"] >= end:
                return out
            last = r[0]["sigla"]
            out.append(r[0])

    with cf.ThreadPoolExecutor(10) as pool:
        rows = [x for part in pool.map(scan, parts) for x in part]
    return {x["sigla"]: x for x in rows}


# ---------------- nomi, serie e date ----------------

def tcgdex_sets():
    names = {lang: {s["id"]: s["name"].strip() for s in fetch(f"{TCGDEX}/{lang}/sets")} for lang in TCGDEX_LANGS}
    serie = {}
    for s in fetch(f"{TCGDEX}/en/series"):
        for x in fetch(f"{TCGDEX}/en/series/{urllib.parse.quote(s['id'])}").get("sets", []):
            serie[x["id"]] = s["name"]

    def detail(sid):
        try:
            d = fetch(f"{TCGDEX}/en/sets/{urllib.parse.quote(sid)}")
        except (urllib.error.HTTPError, RuntimeError):
            return sid, {}
        return sid, {"date": d.get("releaseDate") or "", "total": (d.get("cardCount") or {}).get("official") or 0,
                     "abbr": (d.get("abbreviation") or {}).get("official") or d.get("tcgOnline") or ""}

    with cf.ThreadPoolExecutor(8) as pool:
        details = dict(pool.map(detail, list(names["en"])))
    return names, serie, details


def limitless():
    """Sigla, nome inglese e data dei set inglesi e giapponesi."""
    out = {}
    for region, url in LIMITLESS.items():
        page = fetch(url, raw=True)
        rows = []
        for m in re.finditer(r'<td><a href="/cards/[^"]+"><img[^>]*>\s*(.*?)\s*<span class="code annotation">([^<]+)</span></a></td>'
                             r'\s*<td><a[^>]*>([^<]*)</a></td>', page, re.S):
            date = ""
            try:
                date = datetime.datetime.strptime(m.group(3).strip(), "%d %b %y").strftime("%Y-%m-%d")
            except ValueError:
                pass
            rows.append({"code": m.group(2).strip(), "name": html.unescape(re.sub("<[^>]+>", "", m.group(1))).strip(), "date": date})
        out[region] = rows
    return out


# ---------------- simboli dell'archivio del catalogo ----------------

def visual_assets():
    rows, after = [], ""
    while True:
        page = catalog("catalog_visual_assets", {
            "select": "asset_key,kind,source_code,source_language,name,scope,image_url,image_sha256,availability,match_mode,match_code,original_path,provenance",
            "kind": "in.(set_symbol,japanese_set,set_logo)", "availability": "eq.available", "scope": "neq.digital",
            "asset_key": "gt." + after, "order": "asset_key", "limit": 1000})
        rows += page
        if len(page) < 1000:
            return rows
        after = page[-1]["asset_key"]


def main():
    t0 = time.time()
    cache = pathlib.Path(sys.argv[sys.argv.index("--cache") + 1]) if "--cache" in sys.argv else None

    def cached(name, fn):
        """Con --cache CARTELLA i dati scaricati si riusano tra un'esecuzione e l'altra."""
        f = cache / (name + ".json") if cache else None
        if f and f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
        data = fn()
        if f:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return data

    codes = cached("sigle", catalog_codes)
    print(f"{len(codes)} sigle nel catalogo ({time.time() - t0:.0f} s)")
    names, serie_of, details = cached("tcgdex", tcgdex_sets)
    lim = cached("limitless", limitless)
    assets = cached("archivio", visual_assets)
    print(f"{len(assets)} simboli e loghi nell'archivio")

    # --- un elemento per codice base (la parte prima di @) ---
    sets = {}
    for sigla, row in codes.items():
        base, _, lang = sigla.partition("@")
        e = sets.setdefault(base, {"code": base, "langs": set(), "tcgdex": set(), "providers": set()})
        e["langs"].add(lang or "INT")
        uid = row.get("source_uid") or ""
        provider = uid.split(":")[0]
        e["providers"].add(provider)
        m = re.match(r"tcgdex:([a-z-]+):(.+)-[^-]+$", uid)
        if m:
            e["tcgdex"].add((m.group(1), m.group(2)))
    # sigle inglesi di TCGdex e di Limitless: stessa espansione registrata con due codici (ME03 e POR)
    abbr_of = {}
    for e in sets.values():
        for lang, sid in e["tcgdex"]:
            if lang == "en" and details.get(sid, {}).get("abbr"):
                abbr_of.setdefault(details[sid]["abbr"].upper(), e["code"])
    lim_en = {x["code"].upper(): x for x in lim["en"]}
    lim_jp = {x["code"].upper(): x for x in lim["jp"]}
    for base in list(sets):
        e = sets[base]
        target = abbr_of.get(base.upper())
        if target and target != base and not e["tcgdex"] and target in sets:
            t = sets[target]
            tname = next((names["en"].get(sid) for lang, sid in t["tcgdex"] if lang == "en"), "")
            if base.upper() in lim_en and norm(lim_en[base.upper()]["name"]) not in (norm(tname),) and norm(tname) not in norm(lim_en[base.upper()]["name"]):
                continue  # stessa sigla ma nome diverso: non le unisco
            t.setdefault("extra", []).append(base)
            t["langs"] |= e["langs"]
            t["providers"] |= e["providers"]
            del sets[base]

    # stesse espansioni registrate da altre fonti con un codice diverso (EPO = BW2, SWSH = SWSHP, BEST OF GAME = BOG)
    en_name = collections.defaultdict(set)
    for e in sets.values():
        for lang, sid in e["tcgdex"]:
            if names["en"].get(sid):
                en_name[norm(names["en"][sid])].add(e["code"])
    for base in list(sets):
        e = sets.get(base)
        if not e or e["tcgdex"] or e["langs"] <= set(ASIA) | {"und"}:
            continue
        target = base + "P" if base + "P" in sets and sets[base + "P"]["tcgdex"] else None
        if not target:
            wanted = norm((lim_en.get(base.upper()) or {}).get("name") or base)
            hits = en_name.get(wanted, set()) or {c for n, cs in en_name.items() if len(wanted) >= 8 and n.startswith(wanted) for c in cs}
            target = next(iter(hits)) if len(hits) == 1 else None
        if target and target != base:
            t = sets[target]
            t.setdefault("extra", []).append(base)
            t["langs"] |= e["langs"]
            t["providers"] |= e["providers"]
            del sets[base]

    # stesso set asiatico con due sigle (XY7 da TCGdex e XY7-B dall'archivio ufficiale): uno solo
    for base in list(sets):
        e = sets.get(base)
        if not e or e["tcgdex"]:
            continue
        for k in asia_keys(base) - {base.lower()}:
            t = next((sets[c] for c in sets if c.lower() == k and c != base), None)
            if t and (t["langs"] & e["langs"]):
                t.setdefault("extra", []).append(base)
                t["langs"] |= e["langs"]
                t["providers"] |= e["providers"]
                del sets[base]
                break

    # --- nomi, serie, date ---
    for e in sets.values():
        ids = {lang: sid for lang, sid in sorted(e["tcgdex"])}
        en_id = ids.get("en") or next((sid for lang, sid in sorted(e["tcgdex"]) if sid in names["en"]), "")
        e["id"] = (en_id or next(iter(ids.values()), "")).lower()
        d = details.get(en_id, {})
        name = names["en"].get(en_id, "")
        it = next((names["it"].get(sid) for lang, sid in e["tcgdex"] if names["it"].get(sid)), "")
        ja = next((names["ja"].get(sid) for lang, sid in e["tcgdex"] if lang == "ja" and names["ja"].get(sid)), "")
        up = e["code"].upper()
        asia_only = e["langs"] <= set(ASIA) | {"und"}
        lj = next((lim_jp[k.upper()] for c in [e["code"]] + e.get("extra", []) for k in asia_keys(c) if k.upper() in lim_jp), None) \
            if (asia_only or "JP" in e["langs"]) else None
        le = lim_en.get(up)
        if not name:
            name = (lj or le or {}).get("name") or ja or next((names[l].get(sid) for l, sid in e["tcgdex"] if names.get(l, {}).get(sid)), "") or e["code"]
        if asia_only and (name == e["code"] or not name.isascii()):
            slug = next((k for k, v in JP_ALIASES.items() if "-" in k and v in [e["code"]] + e.get("extra", [])), "")
            if slug:
                name = slug.replace("-", " ").title().replace("Gx", "GX").replace("Xy", "XY").replace(" Vs ", " VS ")
        e["name"] = name
        if it and it != name:
            e["it"] = it
        if ja and ja != name:
            e["ja"] = ja
        date = d.get("date") or (lj or le or {}).get("date") or ""
        e["date"] = date
        e["year"] = date[:4]
        e["abbr"] = d.get("abbr") or (le["code"] if le and not asia_only else "")
        if d.get("total"):
            e["total"] = d["total"]
        if serie_of.get(en_id) and not asia_only:
            e["serie"] = serie_of[en_id]
        else:
            region = next((ASIA[l] for l in ASIA if l in e["langs"]), "")
            e["serie"] = ("Solo " + region) if asia_only and region else (serie_of.get(en_id) or "Altre uscite")

    # --- indici per abbinare i simboli ---
    by_tcgdex = collections.defaultdict(set)      # (lingua tcgdex, id) -> codici base
    by_idkey = collections.defaultdict(set)       # id normalizzato (set internazionali) -> codici base
    by_asia_code = collections.defaultdict(set)   # sigla asiatica normalizzata -> codici base
    by_name = collections.defaultdict(set)        # nome inglese normalizzato -> codici base
    for e in sets.values():
        asia_only = e["langs"] <= set(ASIA) | {"und"}
        for lang, sid in e["tcgdex"]:
            by_tcgdex[(lang, sid.lower())].add(e["code"])
            if lang != "ja" and not asia_only:
                for k in id_keys(sid):
                    by_idkey[k].add(e["code"])
        if asia_only or e["langs"] & set(ASIA):
            for c in [e["code"]] + e.get("extra", []):
                for k in asia_keys(c):
                    by_asia_code[k].add(e["code"])
        for n in {e["name"], names["en"].get(e["id"], "")}:
            if n and not asia_only:
                by_name[norm(n)].add(e["code"])
    jp_by_name = collections.defaultdict(set)
    for x in lim["jp"]:
        for c in by_asia_code.get(x["code"].lower(), ()):
            jp_by_name[norm(x["name"])].add(c)
    for slug, c in JP_ALIASES.items():
        jp_by_name[norm(slug)] |= by_asia_code.get(c.lower(), set())
    all_tcgdex_ids = collections.defaultdict(set)
    for (lang, sid), cs in by_tcgdex.items():
        all_tcgdex_ids[sid].update(cs)

    def name_candidates(slug, index):
        """Nome dal file (xy-generations, hs-unleashed, classic-charizard...) -> espansioni con quel nome."""
        s = slug.lower().replace("pokemon-trading-card-game-", "pokemon-tcg-")
        tries = [s]
        for pre in ("xy-", "hs-", "sm-", "bw-", "dp-", "sun-and-moon-", "black-and-white-", "diamond-and-pearl-",
                    "heartgold-and-soulsilver-", "heart-gold-and-soul-silver-", "sword-and-shield-", "scarlet-and-violet-", "ex-"):
            if s.startswith(pre):
                tries.append(s[len(pre):])
        if s.startswith("classic-"):
            tries.append("pokemon-tcg-" + s)
        for t in tries:
            hit = index.get(norm(t))
            if hit:
                return hit
        return set()

    def targets(a):
        """Espansioni del catalogo a cui appartiene un simbolo dell'archivio, e quanto è sicuro l'abbinamento."""
        code, lang = a["source_code"] or "", (a["source_language"] or "").lower()
        source = (a.get("provenance") or {}).get("source", "")
        if a.get("match_mode") == "tcgdex-set" and a.get("match_code"):
            mc = a["match_code"].lower()
            hit = set()
            for (l, sid), cs in by_tcgdex.items():
                if sid == mc and (lang in ("und", "", l) or lang == "en"):
                    hit |= cs
            return hit or all_tcgdex_ids.get(mc, set()), 0
        if source == "TCGdex":
            m = re.search(r"/(?:univ|[a-z-]+)/[^/]+/([^/]+)/(?:symbol|logo)", a.get("original_path", "") + "/" + (a["image_url"] or ""))
            sid = (m.group(1) if m else code).lower()
            l = {"univ": ""}.get(lang, lang)
            hit = set()
            for (tl, tsid), cs in by_tcgdex.items():
                if tsid == sid and (not l or tl == l or l == "en"):
                    hit |= cs
            return hit, 1
        if source in ("1niceroli_AssetRepo", "SilphGhost", "PokemonTCG_Storico") or a["kind"] == "set_logo" and re.fullmatch(r"[a-z]{0,3}_?[a-z0-9.]+", code.lower()):
            m = re.match(r"(de|ja|fr|it|es|pt|ko|zh)_(.+)", code.lower())
            prefix, rest = (m.group(1), m.group(2)) if m else ("", code.lower())
            if prefix in ("ja", "ko"):
                rest = JP_ALIASES.get(rest, rest).lower()
                return by_asia_code.get(rest, set()), 1
            rest = ALIASES.get(rest, rest)
            hit = set()
            for k in id_keys(rest):
                hit |= by_idkey.get(k, set())
            if not hit and rest.startswith("c") and lang in ("en", "zh", "und"):
                hit = by_asia_code.get(rest, set()) or by_asia_code.get(rest[1:], set())
            if hit:
                return hit, 1
        if a["kind"] == "japanese_set" or lang == "ja":
            return jp_by_name.get(norm(code), set()) or name_candidates(code, jp_by_name), 2
        if code.lower() in ALIASES:
            return all_tcgdex_ids.get(ALIASES[code.lower()], set()), 1
        return name_candidates(code, by_name), 2

    found = collections.defaultdict(lambda: {"symbols": [], "logos": []})
    unmatched = collections.Counter()
    for a in assets:
        url = a.get("image_url") or ""
        if not url.startswith("https://") or url in NOT_A_SYMBOL:
            continue
        if a["kind"] != "set_logo" and re.sub(r"^[a-z]{2}_", "", (a["source_code"] or "").lower()) in NO_SYMBOL_IDS:
            continue
        hit, certainty = targets(a)
        if not hit:
            unmatched[a["kind"]] += 1
            if "--report" in sys.argv:
                print("  senza espansione:", a["kind"], a["source_code"], a["source_language"], (a.get("provenance") or {}).get("source"))
            continue
        if len(hit) > 3 and certainty > 0:
            continue  # nome troppo generico per decidere
        source = (a.get("provenance") or {}).get("source", "")
        # loghi: prima quello italiano, poi l'inglese (il logo cambia con la lingua della bustina)
        lang_rank = {"it": 0, "en": 1, "und": 2}.get((a["source_language"] or "").lower(), 3) if a["kind"] == "set_logo" else 0
        rank = (certainty, lang_rank, a["scope"] != "physical", SOURCE_RANK.index(source) if source in SOURCE_RANK else 9)
        key = "logos" if a["kind"] == "set_logo" else "symbols"
        for c in hit:
            found[c][key].append((rank, a.get("image_sha256") or url, url))

    candidates = sorted({u for f in found.values() for key in ("symbols", "logos") for _, _, u in f[key]})
    checked = cached("verifiche", lambda: {})
    todo = [u for u in candidates if u not in checked]
    with cf.ThreadPoolExecutor(12) as pool:
        for u, ok in zip(todo, pool.map(alive, todo)):
            checked[u] = ok
    if cache:
        (cache / "verifiche.json").write_text(json.dumps(checked), encoding="utf-8")
    dead = {u for u, ok in checked.items() if not ok}
    print(f"{len(candidates)} immagini controllate, {len(dead & set(candidates))} non rispondono e restano fuori")
    for c, e in sets.items():
        for key in ("symbols", "logos"):
            seen, urls = set(), []
            for rank, sha, url in sorted(found[c][key]):
                if url in dead:
                    continue
                if sha in seen or url in urls:
                    continue
                seen.add(sha)
                urls.append(url)
            e[key] = urls[:8] if key == "symbols" else urls[:4]

    # --- carta d'esempio per i set che non hanno un simbolo ---
    cache = {}
    for e in sets.values():
        key = e["id"] if e["id"] in NO_SYMBOL_GROUPS else e["code"].lower()
        if e["symbols"] or key not in NO_SYMBOL_GROUPS:
            continue
        group, wanted = NO_SYMBOL_GROUPS[key]
        try:
            if group not in cache:
                cache[group] = fetch(f"{TCGCSV}/{group}/products").get("results", [])
        except (urllib.error.HTTPError, RuntimeError):
            continue
        cards = [p for p in cache[group] if any(x["name"] == "Number" for x in p.get("extendedData", []))] or cache[group]
        cards = [p for p in cards if wanted.lower() in p["name"].lower()] or cards
        if cards:
            e["card"] = TCGP_IMG.format(cards[0]["productId"])

    for code, name in {"MFB": "My First Battle"}.items():
        if code in sets and sets[code]["name"] == code:
            sets[code]["name"] = name
    rows = []
    for e in sets.values():
        out = {"code": e["code"], "name": e["name"]}
        for k in ("it", "ja"):
            if e.get(k):
                out[k] = e[k]
        out.update({"serie": e["serie"], "year": e["year"], "langs": sorted(e["langs"])})
        if e.get("extra"):
            out["codes"] = [e["code"]] + sorted(e["extra"])
        for k in ("id", "abbr", "total", "card"):
            if e.get(k):
                out[k] = e[k]
        out["symbols"] = e["symbols"]
        if e["logos"]:
            out["logos"] = e["logos"]
        out["_date"] = e["date"]
        rows.append(out)
    rows.sort(key=lambda r: (r["_date"], r["code"]), reverse=True)
    for r in rows:
        del r["_date"]
    OUT.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    with_sym = sum(1 for r in rows if r["symbols"])
    print(f"{len(rows)} espansioni, {with_sym} con simbolo, {sum(len(r['symbols']) for r in rows)} simboli, "
          f"{sum(len(r.get('logos', [])) for r in rows)} loghi, {sum(1 for r in rows if r.get('card'))} con una carta d'esempio "
          f"-> {OUT.name} ({time.time() - t0:.0f} s)")
    print("riferimenti dell'archivio senza espansione corrispondente:", dict(unmatched))


if __name__ == "__main__":
    main()
