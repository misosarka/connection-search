# Programátorská dokumentace
Tato dokumentace slouží především k popisu celkového fungování programu. Jednotlivé datové struktury a funkce jsou popsány podrobně v tzv. dokumentačních řetězcích *(docstrings)* přímo v kódu.

## Použité technologie
Aplikace je napsaná v programovacím jazyce Python, její vývoj probíhá v (aktuálně) nejnovější verzi 3.13.1. Používá několik vestavěných knihoven Pythonu, konkrétně tyto:
- `abc` (definice abstraktních tříd a metod)
- `collections` (datová struktura `defaultdict`)
- `cProfile` (profilování běhu programu)
- `csv` (čtení souborů ve formátu CSV)
- `dataclasses` (jednodušší definice tříd pro ukládání dat)
- `datetime` (práce s časovými údaji)
- `enum` (definice enumerací)
- `functools` (cachování volání funkcí a automatické doplnění porovnávacích metod)
- `os` (zjišťování existence souborů)
- `queue` (datová struktura `PriorityQueue`)
- `typing` (pomůcky pro statické typování)

Dále používá externí knihovnu [`dateutil`](https://pypi.org/project/python-dateutil/), která slouží k parsování data a času z textového vstupu. Původní plán byl pro ukládání načtené datové sady GTFS používat datové struktury knihovny [`pandas`](https://pandas.pydata.org/), ale interakce s těmito datovými strukturami byla pro tento účel příliš pomalá. Datová sada se proto ukládá v nativních typech jazyka Python, což přináší výrazné zrychlení a zvýšení čitelnosti kódu.

Program je schopen zpracovávat data ve standardizovaném formátu General Transit Feed Specification (GTFS), konkrétně ve formátu [GTFS Schedule](https://gtfs.org/documentation/schedule/reference/) určeném k distribuci dat o jízdních řádech dopravních společností. Data jsou v datové sadě GTFS rozdělena do jednotlivých souborů, z nichž každý je ve formátu CSV (soubor s oddělovači). Kromě "kanonické" specifikace existuje ještě specifikace [GTFS Static od Google Transit](https://developers.google.com/transit/gtfs/reference), která se v některých detailech liší. Tato specifikace je také zčásti aplikací podporována (konkrétně jsou podporovány některé z [odlišných typů linek](https://developers.google.com/transit/gtfs/reference/extended-route-types)).

## Popis algoritmu
Algoritmus pro vyhledávání spojení je postaven na prohledávání grafu do hloubky.

Základní datovou strukturou je prioritní fronta `queue`. Jejími prvky jsou tzv. návštěvníci (`Visitor`), kteří reprezentují právě prohledávané zastávky, spoje a přestupy. Návštěvník zastávky (`StopVisitor`) prochází všechny odjezdy z dané zastávky a pro každý z nich vytváří nového návštěvníka spoje (`TripVisitor`). Ten zase prochází všechny zastávky na trase daného spoje a vytváří na nich návštěvníky zastávek a také návštěvníky přestupů (`TransferVisitor`), kteří reprezentují pěší přesuny mezi zastávkami.

Program si také ukládá nejlepší dosud nalezená spojení do všech navštívených zastávek a spojů. K tomu slouží slovníky `visited_stops` a `visited_trips`. Spojení do dané zastávky či spoje je lepší než jiné tehdy, když jeho odjezd z výchozí zastávky je pozdější. V případě rovnosti časů odjezdů je lepší to spojení, které obsahuje méně přestupů.

Návštěvníci jsou v prioritní frontě řazeny podle času, kdy se v nich odehrává následující událost - to je u zastávek čas následujícího odjezdu, u spojů čas následujícího příjezdu do zastávky a u přestupů čas příchodu do cílové zastávky. Tento čas vrací návštěvníci jako výsledek volání metody `next_event()`. Z fronty je vždy odebrán návštěvník s nejdřívějším časem. Na něm je vždy zavolána metoda `next()`, jejímž úkolem je vyřešit následující událost. To obvykle znamená nejprve zkontrolovat, zda dosažená zastávka či spoj byla již navštívena, případně jestli nově vzniklé spojení je lepší než to předchozí, a podle toho aktualizovat jeden ze slovníků a v případě nově dosažené zastávky či spoje vytvořit i nového návštěvníka. Dále je potřeba aktualizovat sebe sama - najít další odjezd nebo zastávku na trase. Metoda `next()` nakonec vrací seznam všech návštěvníků, kteří mají být následně přidáni do fronty.

Celý algoritmus začíná vytvořením návštěvníků výchozích zastávek (a přestupů z nich). Následně probíhá výše uvedené odebírání z fronty podle času následující události, volání metody `next()` a přidávání dalších návštěvníků do fronty. Hledání skončí ve chvíli, kdy je nalezeno spojení do cílové zastávky, vyprší časový limit hledání nebo je fronta prázdná. V prvním případě program vypíše vyhledané spojení, ve zbylých dvou ohlásí, že spojení nebylo nalezeno.

## Dekompozice
Aplikace je rozdělena na jednotlivé moduly reprezentované soubory.

V souboru `structures.py` jsou definovány základní třídy reprezentující záznamy v jednotlivých souborech datové sady - třídy `Stop`, `Route`, `Trip`, `StopTime`, `CalendarRecord`, `CalendarDatesRecord` a `Transfer`. Některé z těchto tříd využívají i speciální enumerace pro některá svá pole a tyto enumerace jsou zde také definovány.

Soubor `dataset.py` obsahuje třídu `Dataset`, která reprezentuje celou datovou sadu a ve svém konstruktoru tuto datovou sadu podle zadané konfigurace s pomocí dalších metod načte. Jednotlivé soubory datové sady jsou ve třídě `Dataset` reprezentovány slovníky mapujícími obvykle identifikátory na struktury ze `structures.py`, případně na seznamy těchto struktur, často seřazené podle určitého klíče pro rychlejší vyhledávání. Třída nabízí veřejné metody pro čtení dat z datové sady, které jsou často následně volány metodami na strukturách ve `structures.py`.

Soubor `connection.py` definuje struktury pro reprezentaci nalezených spojení - `Connection` reprezentující spojení ze zastávky do zastávky a `OpenConnection` reprezentující spojení ze zastávky na určitý spoj. Stavebními bloky těchto spojení jsou jednotlivé segmenty - `TripConnectionSegment` popisuje úsek spojení uražený jedním spojem, `TransferConnectionSegment` jeden pěší přesun mezi zastávkami a `OpenTripConnectionSegment` poslední úsek spojení `OpenConnection`, tj. bez cílové zastávky. Také je zde definována pomocná třída `ConnectionQuality` pro porovnávání spojení.

Soubor `visitor.py` obsahuje výše zmíněné třídy návštěvníků - abstraktní třídu `Visitor` a její implementace `TripVisitor`, `StopVisitor` a `TransferVisitor`. Kromě "povinných" metod `next_event()` a `next()` obsahují návštěvníci různé konstruktory pro vytvoření v různých situacích a také pomocné metody pro nalezení následující události.

V souboru `search.py` jsou definované třídy `SearchParams` a `SearchResult`, které definují podobu parametrů a výsledků hledání spojení. Ty se objevují jako vstup, respektive výstup funkce `search()`, která v sobě obsahuje celý algoritmus hledání spojení.

Soubor `ui.py` definuje uživatelské rozhraní. Metody třídy `Ui` se starají o čtení a interpretaci hodnot ze vstupu a vypisování výsledků. Pro vyhledávání v seznamu zastávek podle začátku názvu zastávky používá rozhraní datovou strukturu *trie* definovanou ve třídách `StopTrie` a `StopTrieNode`.

Konfigurační soubor `config.py` sestává z jednoho konfiguračního slovníku. Význam jednotlivých možností je specifikován v [uživatelské dokumentaci](user.md).

Hlavní skript `main.py` pouze čte konfigurační soubor, vytváří datovou sadu a spouští uživatelské rozhraní.
