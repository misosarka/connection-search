from dataclasses import dataclass, field
from typing import Iterable

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
    
    def _ask_for_stop(prompt: str) -> tuple[str, list[str]]:
        while True:
            prefix = input(prompt)
            # TODO: find and display 9 possible names + 0 for retry, let the user choose
