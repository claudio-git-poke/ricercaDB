# ricercaDB

Pagina di ricerca sul catalogo carte [pokemon-catalog](https://github.com/claudio-git-poke/pokemon-catalog).

Una sola schermata, quattro zone:

1. **Ricerca testuale**: scrivi quello che sai della carta (`charizard 4/102 base1 holo`).
2. **Anatomia della carta**: gli stessi dati, compilabili nei campi dove si trovano sulla carta. L'espansione si sceglie dal suo simbolo. Testo e campi restano allineati. Quattro pulsanti + servono per i simboli che distinguono una stampa dalle altre: agli angoli bassi dell'illustrazione gli stampini (zucca Trick or Trade, logo Play! Pokémon delle buste premio, fiocco di neve, firma dei mazzi dei Mondiali, STAFF, 1ª Edizione e altri), accanto al numero il simbolo di rarità e la stella PROMO, nell'angolo della carta la sagoma di Battle Academy e My First Battle.
3. **Carte che corrispondono**: si aggiorna a ogni modifica.
4. **Ultimi inserimenti**: le carte aperte, salvate nel browser.

È un unico file statico, `index.html`, senza build. Legge in sola lettura la tabella `catalog_search_entries` del database Supabase del catalogo con la chiave pubblica (ruolo anon).

## File

- `index.html`: la pagina.
- `espansioni.json`: elenco delle espansioni con nome italiano, sigla, anno e indirizzo di simbolo e logo. Le immagini vengono da TCGdex e, per i set che TCGdex non ha, da pokemon-tcg-data (images.pokemontcg.io). Si rigenera con `python3 strumenti/aggiorna-espansioni.py` quando escono nuove espansioni.
- `simboli/`: foto di carte vere usate nei menu dei simboli, ingrandite sul punto giusto. Come aggiungerne altre è spiegato in `simboli/LEGGIMI.md`.
