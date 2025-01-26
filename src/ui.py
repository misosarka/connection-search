from dataclasses import dataclass, field
from datetime import datetime, timedelta
from dateutil.parser import parse, ParserError
from typing import Iterable
from cProfile import Profile

from .structures import TransferType
from .connection import TransferConnectionSegment
from .search import SearchParams, SearchResult, search
from .dataset import Dataset


@dataclass
class StopTrieNode:
    stops: dict[str, list[str]] = field(default_factory=dict)
    """A mapping of full stop names to all stop_ids of stops with this name."""
    next_letters: dict[str, "StopTrieNode"] = field(default_factory=dict)

    def yield_all_stops(self) -> Iterable[tuple[str, list[str]]]:
        for name, ids in self.stops.items():
            yield name, ids
        for child in self.next_letters.values():
            yield from child.yield_all_stops()


class StopTrie:
    """A trie data structure for fast stop name search."""
    root: StopTrieNode

    def __init__(self) -> None:
        self.root = StopTrieNode()
    
    @staticmethod
    def _map_letter(letter: str) -> str:
        MAPPING = {"á": "a", "ä": "a", "č": "c", "ď": "d", "é": "e", "ě": "e", "ë": "e", "í": "i", "ľ": "l", "ň": "n",
                   "ó": "o", "ö": "o", "ř": "r", "š": "s", "ť": "t", "ú": "u", "ů": "u", "ü": "u", "ý": "y", "ž": "z"}
        letter = letter.lower()
        if letter in MAPPING:
            return MAPPING[letter]
        else:
            return letter

    def add_stop(self, stop_name: str, stop_id: str) -> None:
        """Add a stop with a specified name and id into the trie."""
        current_node = self.root
        for letter in stop_name:
            letter = StopTrie._map_letter(letter)
            if letter in current_node.next_letters:
                current_node = current_node.next_letters[letter]
            else:
                new_node = StopTrieNode()
                current_node.next_letters[letter] = new_node
                current_node = new_node
        if stop_name in current_node.stops:
            current_node.stops[stop_name].append(stop_id)
        else:
            current_node.stops[stop_name] = [stop_id]
    
    def _traverse(self, stop_name: str) -> StopTrieNode | None:
        current_node = self.root
        for letter in stop_name:
            letter = StopTrie._map_letter(letter)
            if letter in current_node.next_letters:
                current_node = current_node.next_letters[letter]
            else:
                return None
        return current_node

    def search_by_prefix(self, stop_name_prefix: str) -> Iterable[tuple[str, list[str]]]:
        """
        Yield all stops whose name starts with the specified prefix.
        
        For every stop, yield a tuple consisting of its name and a list of stop_ids of all stops with this name.
        """
        prefix_node = self._traverse(stop_name_prefix)
        if prefix_node is None:
            return
        yield from prefix_node.yield_all_stops()


class Ui:
    """An interface between the search algorithm and user."""
    dataset: Dataset
    stop_trie: StopTrie

    def __init__(self, dataset: Dataset) -> None:
        self.dataset = dataset
        self.stop_trie = StopTrie()
        for stop_id, stop_name in dataset.get_all_stop_ids_and_names():
            self.stop_trie.add_stop(stop_name, stop_id)
    
    def run(self) -> None:
        print()
        print("Vyhledávač spojení connection-search")
        print("------------------------------------")
        while True:
            print()
            params = self._request_search_params()
            print("Probíhá vyhledávání...")
            if self.dataset.config["PROFILE"]:
                with Profile() as prof:
                    result = search(params, self.dataset)
                prof.dump_stats("profile.prof")
            else:
                result = search(params, self.dataset)
            print("Vyhledávání dokončeno.")
            print()
            self._display_result(result)
            print()
            print("[0] pro ukončení, [Enter] nebo jiná klávesa pro další vyhledávání")
            command = input()
            if command == "0":
                break

    def _request_search_params(self) -> SearchParams:
        while True:
            origin_name, origin_ids = self._ask_for_stop("Zadejte výchozí zastávku: ")
            destination_name, destination_ids = self._ask_for_stop("Zadejte cílovou zastávku: ")
            departure = self._ask_for_datetime(
                "Zadejte datum a čas odjezdu (např. ve formátu '14. 3. 2025 12:34'): "
            )
            print("Vyhledat spojení:")
            print(f"\t{origin_name} -> {destination_name}")
            print(f"\tOdjezd: {self._format_datetime(departure)}")
            print("[Enter] pro potvrzení, [0] pro nové vyhledání")
            command = input().strip()
            if command == "":
                return SearchParams(origin_ids, destination_ids, departure)
            elif command != "0":
                print("Neznámý příkaz. Zkuste vyhledávat znovu.")
    
    def _display_result(self, result: SearchResult) -> None:
        if result.connection is None:
            print("Žádné spojení nebylo mezi danými zastávkami nalezeno.")
            return
        if not result.connection.segments:
            print("Výchozí a cílová zastávka jsou stejné.")
            return
        total_time = result.connection.last_arrival - result.connection.first_departure # type: ignore[operator]
        transfer_count = result.connection.transfer_count
        transfer_count_str = f"{transfer_count} přestup"
        if transfer_count in (2, 3, 4):
            transfer_count_str += "y"
        elif transfer_count >= 5:
            transfer_count_str += "ů"
        elif transfer_count == 0:
            transfer_count_str = "bez přestupu"
        print(f"Spojení: {transfer_count_str}, celkem {self._format_timedelta(total_time)}")
        for segment in result.connection.segments:
            start_stop = segment.start_stop.stop_name
            start_departure = self._format_datetime(segment.start_departure)
            end_stop = segment.end_stop.stop_name
            end_arrival = self._format_datetime(segment.end_arrival)
            if isinstance(segment, TransferConnectionSegment):
                match segment.transfer.transfer_type:
                    case TransferType.BY_TRANSFERS_GUARANTEED:
                        print("\tPěší přesun: garantovaný přestup")
                    case TransferType.BY_TRANSFERS_TIMED:
                        print(f"\tPěší přesun: cca {segment.transfer.transfer_time} min")
                    case _:
                        print("\tPěší přesun")
            else:
                transport_type = str(segment.route.route_type).capitalize()
                trip_name = segment.trip.get_trip_name()
                print(f"\t{transport_type} {trip_name}")
                print(f"\t\t{start_departure} {start_stop}")
                print(f"\t\t{end_arrival} {end_stop}")

    def _ask_for_stop(self, prompt: str) -> tuple[str, list[str]]:
        while True:
            prefix = input(prompt).strip()
            options = dict(zip(range(1, 10), self.stop_trie.search_by_prefix(prefix)))
            if len(options) == 0:
                print("Žádná zastávka nebyla nalezena. Zkuste vyhledávat znovu.")
            elif len(options) == 1:
                name, ids = options[1]
                print(f"Nalezena zastávka: {name}")
                print("[Enter] pro potvrzení, [0] pro nové vyhledání")
                command = input().strip()
                if command == "":
                    return name, ids
                elif command != "0":
                    print("Neznámý příkaz. Zkuste vyhledávat znovu.")
            else:
                print("Vyberte z nabídky:")
                for i, (name, _) in options.items():
                    print(f"[{i}] {name}")
                print("[0] pro nové vyhledání")
                command = input().strip()
                if command == "0":
                    continue
                if command.isdecimal() and int(command) in options:
                    name, ids = options[int(command)]
                    return name, ids
                else:
                    print("Neznámý příkaz. Zkuste vyhledávat znovu.")
    
    def _ask_for_datetime(self, prompt: str) -> datetime:
        while True:
            string = input(prompt)
            try:
                return parse(string, dayfirst=True)
            except ParserError:
                print("Nesprávný formát. Zkuste zadat datum a čas znovu.")

    def _format_datetime(self, dt: datetime) -> str:
        return f"{dt.day}. {dt.month}. {dt.year} {dt.hour}:{str(dt.minute).zfill(2)}"
    
    def _format_timedelta(self, td: timedelta) -> str:
        hours, seconds = divmod(td.total_seconds(), 3600)
        minutes = seconds // 60
        return f"{int(hours)} h {int(minutes)} min"
