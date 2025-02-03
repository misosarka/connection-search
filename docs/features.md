# Seznam aktuálně nepodporovaných možností datové sady
Následující možnosti jsou součástí specifikace GTFS a mohou být relevantní pro hledání spojení, ale aplikace je aktuálně nepodporuje. To může znamenat, že jejich přítomnost v datové sadě nebere v potaz, že je nevyhodnocuje správně, nebo dokonce vrátí chybu při spuštění s datovou sadou obsahující tyto možnosti.

- Průběžný nástup a výstup, tj. pole `continuous_pickup` a `continuous_drop_off` v `routes.txt`, pole `shape_id` v `trips.txt`, pole `continuous_pickup`, `continuous_drop_off` a `shape_dist_traveled` v `stop_times.txt` a soubor `shapes.txt` (aplikace tyto informace ignoruje).
- Odhadované (nepřesné) časy příjezdu a odjezdu, tj. hodnota `timepoint=0` v `stop_times.txt` (aplikace nebude fungovat, jestliže u některého záznamu ve `stop_times.txt` nebude definován čas příjezdu a odjezdu).
- Zónový poptávkový provoz, tj. pole `location_group_id`, `location_id`, `start_pickup_drop_off_window` a `end_pickup_drop_off_window` v `stop_times.txt` a soubory `location_groups.txt`, `location_group_stops.txt` a `locations.geojson` (aplikace nebude fungovat, jestliže u některého záznamu ve `stop_times.txt` nebude definován čas příjezdu a odjezdu nebo pole `stop_id`).
- Provoz podle pravidelných intervalů, tj. soubor `frequencies.txt` (aplikace tyto spoje ignoruje).
- Přestupy mezi konkrétními spoji nebo linkami, včetně garantovaných přestupů a přestupů bez nutnosti opuštění vozidla, tj. pole `from_route_id`, `to_route_id`, `from_trip_id` a `to_trip_id` v `transfers.txt` (aplikace tyto přestupy ignoruje).
- Pěší přesuny po definovaných cestách a rozdělení stanic na patra, tj. pole `level_id` v `stops.txt` a soubory `pathways.txt` a `levels.txt` (aplikace tyto pěší přesuny ignoruje).
- Pravidla rezervace míst, tj. pole `pickup_booking_rule_id` a `drop_off_booking_rule_id` v `stop_times.txt` a soubor `booking_rules.txt` (aplikace tyto informace ignoruje).
