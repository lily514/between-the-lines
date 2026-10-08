# Name sources

Where the names in `backend/src/btl/league/names.py` come from. This is a living reference: update it whenever a pool changes.

## How names are built

- **Clubs:** a real English market town with no professional football club, plus an invented nickname, e.g. "Kendal Kestrels".
- **Players:** a real first name plus an invented surname, both in the same style. First names are common boys' names for people born about 1990–2008 (aged roughly 17–35 now). Surnames are built from invented syllables, so a full name is never a real person's on purpose.
- **Private check:** `tests/league/test_real_names.py` checks the pools against a gitignored list of real names (see `docs/setup.md`), and fails if any style could produce a listed full name.

## First-name pools

Each style has 30 first names. "Verified" means each name was checked against the registry's own data rows: it ranks in the top 100 boys' names (top 50 for Spain, where INE publishes no more) for at least one birth year or decade between 1990 and 2008, in at least one of the style's countries. Checked on 2026-10-07.

| Style | Status | Sources |
|---|---|---|
| British | Verified | [ONS baby names, England and Wales, 1996–2008](https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/livebirths/datasets/babynamesinenglandandwalesfrom1996); [CSO Ireland, VSA50, 1990–2008](https://www.cso.ie/en/statistics/birthsdeathsandmarriages/irishbabiesnames/). Scottish data (NRS) not read. |
| Dutch and German | Mostly verified | [Meertens Voornamenbank, Netherlands top 100, 1990–2008](https://nvb.meertens.knaw.nl/); [GfdS most popular first names, Germany](https://gfds.de/vornamen/beliebteste-vornamen/) (top 10 only). Flemish data (Statbel) could not be downloaded. German names outside the top 10 rest on GfdS press releases. |
| French | Verified | [INSEE fichier des prénoms, France, 1990–2008](https://www.insee.fr/fr/statistiques/2540004) |
| Portuguese-speaking | Verified for Brazil | [IBGE Censo 2010 Nomes, births in the 1990s and 2000s](https://censo2010.ibge.gov.br/nomes/). Some ranks are relative to 229 common names looked up individually, not a full ranking. Portugal publishes names only from 2017, so Portuguese-only names were left out. |
| Spanish-speaking | Verified | [INE, names by decade of birth, Spain](https://www.ine.es/daco/daco42/nombyapel/nombyapel2.htm) (top 50); [Argentina historical names dataset](https://datos.gob.ar/dataset/otros-nombres-personas-fisicas), 1990–2008. Mexico, Colombia and Uruguay not checked. |
| West African | Not verified | [Forebears](https://forebears.io/) frequency data for Nigeria, Ghana, Côte d'Ivoire, Cameroon, Mali and Senegal (all ages, not a 1990–2008 cohort), plus general knowledge of common names. None of these countries publishes name statistics. |
| Nordic | Not verified | Named sources: [SCB Sweden](https://www.scb.se/hitta-statistik/statistik-efter-amne/befolkning-och-levnadsforhallanden/ovrigt/namnstatistik/), [Danmarks Statistik](https://www.dst.dk/da/Statistik/emner/borgere/navne), [SSB Norway](https://www.ssb.no/navn), [Hagstofa Iceland](https://hagstofa.is/talnaefni/ibuar/mannfjoldi/nofn/). The list was assembled from these, but not checked row by row. |
| Slavic | Not verified | Named sources: [Poland PESEL data](https://dane.gov.pl/pl/dataset/219,imiona-nadawane-dzieciom-w-polsce), [Czech ČSÚ](https://www.czso.cz/csu/czso/cetnost-jmen-a-prijmeni), [Croatia DZS](https://podaci.dzs.hr/), [Serbia RZS](https://www.stat.gov.rs/). Ukraine publishes no national statistics; its names rest on general knowledge. |
| North African | Not verified | [Forebears](https://forebears.io/) frequency data for Morocco, Algeria, Egypt and Tunisia (all ages), plus general knowledge of common names. None of these countries publishes name statistics. |

### Changes made by the check

The first draft of the pools was assembled from search results and general knowledge. Checking the five largest pools against registry rows confirmed 145 of 150 names and led to these changes:

- **British:** "Seán" became "Sean", the spelling both ONS and CSO use.
- **Dutch and German:** Fabian (not in the top lists found) became Christian (Germany #2, 1990). Robbe (Flemish, data unavailable) became Milan (Netherlands #5).
- **French:** "Jérémy" became "Jeremy", which INSEE ranks much higher (#9 against #80).
- **Portuguese-speaking:** Gonçalo, Rúben and Tomás (Portuguese, no data for the range; rare in Brazil) became Davi, Samuel and Arthur (Brazil, births in the 2000s).
- **Spanish-speaking:** Ricardo (outside the Spanish top 50 and Argentina's top 200) became Víctor (Spain #18, 1990s).

## Club towns

The towns are real English market towns chosen because none has a professional football club. One town was left out because its name is famous as a top club's stadium. The nicknames are invented and avoid the well-known nicknames of real clubs.

## Style weights

See the T4 notes in `docs/milestone-1/implementation-notes.md` for how the style weights were chosen.
