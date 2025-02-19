# connection-search
Konzolová aplikace pro vyhledání dopravního spojení mezi dvěma zastávkami, pracující s daty specifikace [GTFS](https://gtfs.org/documentation/schedule/reference/).

## Instalace a použití
Návod k instalaci a k použití aplikace najdete v [uživatelské dokumentaci](docs/user.md).

## Popis fungování
Podrobný popis použitého algoritmu, datových struktur a funkcí najdete v [programátorské dokumentaci](docs/programmer.md).

## Limitace
Informace o tom, které funkce datové sady GTFS nejsou aktuálně podporovány, najdete [zde](docs/features.md).

## Zdroje a inspirace
[Ukázková data](data-example) v repozitáři jsou upravenou verzí dat [Pražské integrované dopravy](https://pid.cz/o-systemu/opendata/), konkrétně datové sady "Jízdní řády PID ve formátu GTFS" s platností od 30. 1. do 12. 2. 2025, ze kterých byla vybrána pouze data o tramvajovém provozu v Praze a pouze soubory relevantní pro tuto aplikaci. Data jsou opatřena licencí [CC-BY](https://creativecommons.org/licenses/by/4.0/).

Hlavní inspirací pro vytvoření programu je aplikace [IDOS](https://idos.cz/) od společnosti [CHAPS](https://www.chaps.cz/).

Tato aplikace byla vytvořena jako zápočtový program pro předmět Programování I na [Matematicko-fyzikální fakultě Univerzity Karlovy v Praze](https://www.mff.cuni.cz/), a to v zimním semestru akademického roku 2024/2025.
