# ricercaDB

Pagina di ricerca sul catalogo carte [pokemon-catalog](https://github.com/claudio-git-poke/pokemon-catalog).

Una sola schermata, quattro zone:

1. **Ricerca testuale**: scrivi quello che sai della carta (`charizard 4/102 base1 holo`).
2. **Anatomia della carta**: una carta con le proporzioni e la disposizione di quella vera (63 × 88), che prende il colore del tipo scelto. I dati si scrivono dove stanno sulla carta: in alto il nome, la sigla che lo segue (ex, GX, V, VMAX, VSTAR, Mega, Radioso, LEGEND…) e il simbolo Energia del tipo; in basso, come sulle carte dal 2023, la sigla dell'espansione (scelta dal suo simbolo o dal logo della bustina), la lingua, il numero e il simbolo di rarità. Attacchi, debolezza e ritirata sono solo disegnati. Testo e campi restano allineati. Gli altri riquadri tratteggiati servono per i simboli che distinguono una stampa dalle altre: agli angoli bassi dell'illustrazione gli stampini (zucca Trick or Trade, logo Play! Pokémon delle buste premio, fiocco di neve, firma dei mazzi dei Mondiali, STAFF, 1ª Edizione e altri), accanto al numero il simbolo di rarità e la stella PROMO, nell'angolo della carta la sagoma di Battle Academy e My First Battle, e in alto sull'illustrazione il motivo dell'olografia (Cosmos, Cracked Ice, reverse Poké Ball e Master Ball…).
3. **Carte che corrispondono**: si aggiorna a ogni modifica. Per le stampe speciali (Battle Academy, mazzi dei Mondiali, buste premio, Trick or Trade, My First Battle, promo timbrate) mostra la scansione TCGplayer di quella stampa, non quella della carta normale.
4. **Ultimi inserimenti**: le carte aperte, salvate nel browser.

È un unico file statico, `index.html`, senza build. Legge in sola lettura la tabella `catalog_search_entries` del database Supabase del catalogo con la chiave pubblica (ruolo anon).

## File

- `index.html`: la pagina.
- `espansioni.json`: tutte le espansioni presenti nel catalogo, in tutte le lingue (anche quelle uscite solo in Asia), con nome, sigle, anno, lingue e tutti i simboli e i loghi che l'archivio simboli del catalogo (tabella `catalog_visual_assets`) le attribuisce. La stessa espansione registrata con più codici (ME03 e POR, XY7 e XY7-B) è un solo elemento. Nomi e date vengono da TCGdex e da Limitless; gli indirizzi che non rispondono restano fuori. Si rigenera con `python3 strumenti/aggiorna-espansioni.py` (qualche minuto; `--cache CARTELLA` riusa i dati già scaricati).
- `foto-speciali.json`: per circa 2.600 stampe speciali del catalogo, il numero del prodotto TCGplayer con la loro scansione. Si rigenera con `python3 strumenti/aggiorna-foto-speciali.py`. Le stampe che arrivano da TCGdex hanno già questo numero nel catalogo e non servono qui.
- Rarità (comprese ACE SPEC e Nero e Bianco), timbri (zucca Trick or Trade, 1ª Edizione), simboli Energia dei tipi, simbolo Mega e loghi dei negozi la pagina li legge dal vivo dall'archivio simboli del catalogo: un simbolo aggiunto lì con il suo tag compare nel menu da solo. I simboli Energia sono disegnati come sulla carta: cerchio del colore del tipo con il glifo del catalogo. Restano fuori solo i simboli di TCG Pocket (gioco digitale) e le icone delle mosse dei videogiochi.
- `simboli/simboli.json`: per ogni simbolo, la scansione ufficiale di una carta che lo ha (TCGdex o TCGplayer) e il punto da ingrandire nei menu. Come aggiungerne altre è spiegato in `simboli/LEGGIMI.md`.
