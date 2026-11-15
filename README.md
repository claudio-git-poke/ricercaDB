# ricercaDB

Pagina di ricerca sul catalogo carte [pokemon-catalog](https://github.com/claudio-git-poke/pokemon-catalog).

Una sola schermata, quattro zone:

1. **Ricerca testuale**: scrivi quello che sai della carta (`charizard 4/102 base1 holo`).
2. **Anatomia della carta**: gli stessi dati, compilabili nei campi dove si trovano sulla carta. Testo e campi restano allineati. Due pulsanti + agli angoli bassi dell'illustrazione servono per i simboli in più delle stampe speciali (zucca Trick or Trade, logo Play! Pokémon delle buste premio, fiocco di neve, firma dei mazzi dei Mondiali, STAFF, 1ª Edizione e altri).
3. **Carte che corrispondono**: si aggiorna a ogni modifica.
4. **Ultimi inserimenti**: le carte aperte, salvate nel browser.

È un unico file statico, `index.html`, senza build. Legge in sola lettura la tabella `catalog_search_entries` del database Supabase del catalogo con la chiave pubblica (ruolo anon).
