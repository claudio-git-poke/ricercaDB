"""Rigenera espansioni.json dall'API pubblica di TCGdex.

Uso: python3 strumenti/aggiorna-espansioni.py
Serve solo quando escono nuove espansioni. Le immagini (simbolo e logo)
restano su assets.tcgdex.net: nel file ci sono solo gli indirizzi.
"""
import concurrent.futures as cf
import json
import pathlib
import urllib.error
import urllib.request

API = "https://api.tcgdex.net/v2"
OUT = pathlib.Path(__file__).resolve().parent.parent / "espansioni.json"


def get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def exists(url):
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 200 and r.headers.get("content-type", "").startswith("image/")
    except urllib.error.URLError:
        return False


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
    rows.sort(key=lambda r: (r["date"], r["id"]), reverse=True)
    for r in rows:
        del r["date"]
    OUT.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{len(rows)} espansioni, {sum(1 for r in rows if r['symbol'])} con simbolo, "
          f"{sum(1 for r in rows if r['logo'])} con logo -> {OUT.name}")


if __name__ == "__main__":
    main()
