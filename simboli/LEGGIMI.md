# Foto dei simboli

Le voci del menu "+ simbolo", "+ rarità" e "+ sagoma" mostrano la foto di una carta vera,
ingrandita sul punto dov'è il simbolo. Se per un simbolo non c'è una foto, resta l'icona disegnata.

La foto può essere:
- una **scansione ufficiale** già online (TCGdex o images.pokemontcg.io), indicata con `url`: non serve scaricare niente;
- una **foto tua** salvata in questa cartella, indicata con `file`.

## Usare una scansione ufficiale

Trova la carta su TCGdex (es. `https://api.tcgdex.net/v2/en/cards/swshp-SWSH153`), prendi il campo `image`
e aggiungi `/high.webp`:

```json
"snow": {"url": "https://assets.tcgdex.net/en/swsh/swshp/SWSH153/high.webp", "card": "Pikachu SWSH153", "x": 87, "y": 40}
```

`card` è facoltativo: compare come suggerimento passando sopra la foto.

## Aggiungere una foto tua

1. Metti la foto di una carta intera, dritta e senza bordi intorno, in questa cartella (`.png`, `.jpg` o `.webp`).
2. Aggiungi una riga a `simboli.json` con il nome del simbolo, il file e il punto dove si trova:

   ```json
   "staff": {"file": "luxio-staff.jpg", "x": 85, "y": 52}
   ```

   - `x` è la distanza dal bordo sinistro, `y` dal bordo alto, in percentuale della carta (0–100).
   - `zoom` (facoltativo, predefinito 4) è quanto ingrandire: più alto per simboli piccoli come cerchio e rombo.

Se `x` e `y` mancano, la pagina usa la posizione tipica di quel simbolo.

## Nomi dei simboli

| Nome | Simbolo |
|---|---|
| `trick` | Zucca (Trick or Trade) |
| `snow` | Fiocco di neve (Calendario delle feste) |
| `prize` | Logo Play! Pokémon (buste premio) |
| `wcd` | Firma di un giocatore (mazzi dei Mondiali) |
| `mfbball` | Etichetta con Poké Ball (My First Battle) |
| `first` | 1ª Edizione |
| `staff` | Scritta STAFF |
| `prerelease` | Scritta Prerelease |
| `winner` | Scritta WINNER |
| `champs` | Nome di un campionato |
| `setlogo` | Logo di un'espansione |
| `pcenter` | Logo Pokémon Center |
| `league` | Simbolo della Lega Pokémon |
| `professor` | Scritta Pokémon Professor |
| `25th` | Logo 25° anniversario |
| `pokeday` | Logo Pokémon Day |
| `mcd` | Logo McDonald's |
| `store` | GameStop o EB Games |
| `ba` | Sagoma colorata (Battle Academy) |
| `mfb` | Piccolo Pokémon del mazzo (My First Battle) |
| `promo` | Stella nera con scritto PROMO |
| `common` | Cerchio |
| `uncommon` | Rombo |
| `rare` | Una stella nera |
| `double` | Due stelle nere |
| `ultra` | Due stelle argento |
| `illus` | Una o due stelle oro |
| `secret` | Tre stelle oro |
