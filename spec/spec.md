# Specifikace
Program je konzolovou aplikací umožňující vyhledání dopravního spojení mezi dvěma zastávkami. Hlavní inspirací pro vytvoření tohoto zápočtového programu je aplikace [IDOS](https://idos.cz/) od společnosti [CHAPS](https://www.chaps.cz/).

## Popis fungování
Program po svém spuštění načte data z uživatelem poskytnutého datového setu formátu [General Transit Feed Specification (GTFS)](https://gtfs.org/documentation/schedule/reference/). Následně umožní uživateli provést vyhledání spojení. Při něm uživatel zadá výchozí a cílovou zastávku (respektive zadá prvních pár písmen jejich názvu a program je automaticky doplní, popř. nechá uživatele vybrat), datum a čas odjezdu. Program pak vyhledá (jedno) nejrychlejší spojení mezi zadanými zastávkami a přehledně jej zobrazí v konzoli. Uživatel poté může provést další vyhledání spojení bez nutnosti spouštět program znovu (a načítat tak znovu celý datový set).

## Technické údaje
Program je napsán v jazyce Python (verze 3.13) a pro efektivní zpracování velkého množství dat využívá knihovnu [pandas](https://pandas.pydata.org/). Data o dopravních společnostech jsou předávána ve standardizovaném formátu [GTFS Schedule](https://gtfs.org/documentation/schedule/reference/). Program umí pracovat i s mírným rozšířením specifikace, které se využívá v datech [Pražské integrované dopravy](https://pid.cz/o-systemu/opendata/) - na těchto datech je také primárně testován.

## Cíle
Program by měl spojení vyhledat v co možná nejkratším čase, a to i na úkor časově náročnějšího načtení dat na začátku běhu programu. Toho je dosaženo například využíváním vhodných indexů v datových strukturách a omezením počtu přestupů ve spojení. Dále je důležité, aby program byl jednoduše rozšiřitelný - tzn. aby bylo možné k němu přidat další funkce bez větších změn dříve vytvořeného kódu. Možnými rozšířeními jsou například možnost vyhledávat více alternativ spojení nebo zadat další podmínky pro vyhledané spojení (použité dopravní prostředky, minimální čas na přestup apod.).
