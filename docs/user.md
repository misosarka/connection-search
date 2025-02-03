# Uživatelská dokumentace

## Instalace
Pro instalaci a spuštění aplikace je nutné mít nainstalovaný Python, a to ve verzi 3.13 nebo novější, a správce balíčků `pip`.

Naklonujte repozitář na vlastní zařízení:
```
git clone https://github.com/misosarka/connection-search
cd connection-search
```
Vytvořte virtuální prostředí Pythonu a aktivujte jej:
```
python -m venv .venv
```
*Pro Windows:*
```
.venv\Scripts\activate
```
*Pro Linux / macOS:*
```
.venv/bin/activate
```
Nainstalujte všechny potřebné knihovny:
```
pip install -r requirements.txt
```
Spusťte hlavní skript:
```
python main.py
```

## Uživatelské rozhraní
Aplikace komunikuje přes standardní uživatelské rozhraní (standardní vstup a výstup).

Po spuštění programu dojde k načtení datové sady. To může chvíli trvat (pro obvyklé datové sady cca 5 až 20 sekund, pro rozsáhlejší i více). V případě, že v této fázi dojde k chybě, je to pravděpodobně způsobeno nesprávnou konfigurací - zkontrolujte, zda obsah souboru `config.py` odpovídá používané datové sadě. Pro ukázková data je soubor ve výchozím nastavení nakonfigurován správně.

Aplikace nejprve požádá o zadání názvu výchozí a cílové zastávky. Při zadávání nehraje roli velikost písmen ani diakritika a stačí zadat pouze začátek názvu zastávky (ale mezery a další interpunkční znaménka roli hrají), tj. například po zadání řetězce `sva` v ukázkové datové sadě jsou vyhledány zastávky *Švandovo divadlo* a *Svatoplukova*. Pokud řetězec odpovídá pouze jedné zastávce, zobrazí se její název a možnost volbu potvrdit nebo hledat znovu. Odpovídá-li řetězec více zastávkám, zobrazí se jich až 9 a uživatel zadáním jednoho z čísel 1-9 vybere správnou zastávku, případně může hledat znovu.

Následně se aplikace zeptá na datum a čas odjezdu. Aplikace podporuje obvyklé evropské způsoby zápisu data a času, například ten, který aplikace vypíše jako ukázku (14. 3. 2025 12:34). Je důležité zajistit, aby datum a čas spadaly do období, po které platí používaná datová sada (pro ukázková data je to období 30. 1. 2025 až 12. 2. 2025 včetně), jinak aplikace žádné spojení nenajde.

Po finálním potvrzení dojde k vyhledání spojení. Tato fáze může trvat různou dobu v závislosti na velikosti datové sady, vzdálenosti mezi výchozí a cílovou zastávkou, množství spojů v daném období apod. Vyhledané spojení je vždy takové spojení, které dorazí do cílové zastávky nejdříve, a pokud je takových spojení více, je to to, které v první řadě vyrazí z výchozí zastávky nejpozději (tj. je časově nejkratší) a v druhé řadě obsahuje co nejméně přestupů.

Aplikace nakonec vypíše vyhledané spojení - jeho celkový čas, počet přestupů a postupně všechny jeho části včetně názvů (čísel) linek a spojů, časů odjezdu a příjezdu, názvů zastávek a pěších přesunů. Jestliže nebylo žádné spojení nalezeno, vypíše aplikace tuto informaci, stejně tak aplikace upozorní, pokud se výchozí a cílová zastávka shodují. Uživatel má poté možnost vyhledat další spojení nebo ukončit aplikaci.

## Přidání vlastní datové sady
Pro přidání vlastní datové sady ve formátu GTFS stačí tuto datovou sadu stáhnout, extrahovat z formátu ZIP a vložit její obsah do některé z podsložek aplikace (například do složky `data`, která je ignorovaná Gitem). Následně bude třeba provést změny v [konfiguraci](#konfigurace).

Zde jsou některé veřejně dostupné datové sady českých a slovenských dopravců:
- [PID](https://pid.cz/o-systemu/opendata/) (Praha a Středočeský kraj)
- [IDS JMK](https://hub.arcgis.com/datasets/379d2e9a7907460c8ca7fda1f3e84328/about) (Jihomoravský kraj)
- [DPMO](https://www.dpmo.cz/informace-pro-cestujici/jizdni-rady/jizdni-rady-gtfs/) (Olomouc a blízké okolí)
- [ŽSR](https://data.europa.eu/data/datasets/ca4cb74c-7192-4198-b074-34acd9d295e7?locale=sk) (slovenské železnice)

## Konfigurace
Konfigurace vyhledávání se provádí v souboru `config.py` v kořenové složce repozitáře. Možnosti konfigurace jsou následující:
- `"DATASET_PATH"`: Relativní cesta ke složce, ve které jsou uloženy soubory používané datové sady, například `"data-example"` nebo `"data/prague/pid/latest"`.
- `"MAX_SEARCH_TIME_HOURS"`: Čas v hodinách, po který se bude aplikace snažit vyhledat spojení - tj. pokud neexistuje spojení, které do cíle dorazí nejpozději po tomto počtu hodin od zadaného času odjezdu, aplikace vypíše, že spojení neexistuje. Při zadání hodnot vyšších než 24 není zaručeno, že nejlepší spojení bude nalezeno správně.
- `"TRANSFER_MODE"`: Způsob, jakým mají být v datové sadě vyhodnocovány pěší přesuny mezi zastávkami. Možné hodnoty jsou:
    - `"by_node_id"`: V souboru `stops.txt` v datové sadě existuje sloupec, v němž mají stejnou hodnotu právě ty zastávky, mezi kterými je možné přestupovat. Název tohoto sloupce je pak hodnotou konfigurace `"TRANSFER_NODE_ID"`. *Tento způsob je vhodné využít například pro datovou sadu PID (název sloupce je `"asw_node_id"`) a DPMO (název sloupce je `"stop_code"`).*
    - `"by_parent_station"`: Je možné přestupovat právě mezi zastávkami, které mají v datové sadě stejnou rodičovskou stanici.
    - `"by_transfers_txt"`: Pěší přesuny jsou specifikovány v samostatném souboru `transfers.txt` v datové sadě. Je možné přestupovat mezi zastávkami, které mají v tomto souboru záznam obsahující pouze ID výchozí a cílové zastávky (nikoli spoje nebo linky). *Tento způsob je vhodné využít například pro datovou sadu IDS JMK.*
    - `"none"`: Není možné přestupovat mezi různými zastávkami. *Tento způsob je vhodné využít například pro datovou sadu ŽSR.*
- `"TRANSFER_NODE_ID"`: Viz možnost `"TRANSFER_MODE": "by_node_id"` výše.
- `"MIN_TRANSFER_TIME_SECONDS"`: Minimální čas v sekundách nutný k pěšímu přesunu mezi dvěma zastávkami v režimech přestupu `"by_node_id"`, `"by_parent_station"` a `"by_transfers_txt"`. Je-li v režimu `"by_transfers_txt"` v záznamu o přestupu vyplněn minimální čas nutný k přestupu, využije se vyšší z obou hodnot.
- `"PROFILE"`: Je-li možnost nastavena na `"True"`, běh algoritmu je profilován pomocí knihovny `cProfile` a výsledky jsou uloženy do souboru `profile.prof`.
