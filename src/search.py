from dataclasses import dataclass
from datetime import datetime, timedelta
from queue import PriorityQueue

from .dataset import Dataset
from .visitor import StopVisitor, Visitor
from .connection import Connection, OpenConnection


SEARCH_TIME_LIMIT = timedelta(hours=24)
"""The maximum time the algorithm will search through before giving up."""


@dataclass
class SearchParams:
    """Represents all the parameters the user can set when searching for a connection."""
    origin_stop_id: str
    destination_stop_id: str
    departure: datetime


@dataclass
class SearchResult:
    """
    Represents the result of the search algorithm.
    Currently, this is just a single optional Connection, but it may be extended.
    """
    connection: Connection | None


def search(params: SearchParams, dataset: Dataset) -> SearchResult:
    """Perform the search algorithm with the specified parameters on the specified dataset and return its results."""
    queue: PriorityQueue[Visitor] = PriorityQueue()
    visited_stops: dict[str, Connection] = {}
    visited_trips: dict[str, OpenConnection] = {}
    time_limit = params.departure + SEARCH_TIME_LIMIT
    destination = params.destination_stop_id

    origin_visitor = StopVisitor.create_at_origin(dataset, params.origin_stop_id, params.departure)
    if origin_visitor is None:
        # No valid departures from the origin stop in 24 hours
        return SearchResult(connection=None)
    queue.put(origin_visitor)
    visited_stops[params.origin_stop_id] = Connection.empty()

    while not queue.empty():
        visitor = queue.get()
        if visitor.next_event() > time_limit:
            break
        new_visitors = visitor.next(visited_stops, visited_trips)
        if destination in visited_stops:
            return SearchResult(connection=visited_stops[destination])
        for new_visitor in new_visitors:
            queue.put(new_visitor)
    
    return SearchResult(connection=None)
