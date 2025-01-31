from dataclasses import dataclass
from datetime import datetime, timedelta
from queue import PriorityQueue

from .new_dataset import Dataset
from .visitor import StopVisitor, TransferVisitor, Visitor
from .connection import Connection, OpenConnection


@dataclass
class SearchParams:
    """Represents all the parameters the user can set when searching for a connection."""
    origin_stop_ids: list[str]
    destination_stop_ids: list[str]
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
    time_limit = params.departure + timedelta(hours=dataset.config["MAX_SEARCH_TIME_HOURS"])
    destinations = params.destination_stop_ids

    for origin_stop_id in params.origin_stop_ids:
        # Create StopVisitor at the origin stop
        origin_visitor = StopVisitor.create_at_origin(dataset, origin_stop_id, params.departure)
        if origin_visitor is not None:
            queue.put(origin_visitor)
            visited_stops[origin_stop_id] = Connection.empty()
        
        # Create TransferVisitors for transfers directly from the origin stop
        for transfer_visitor in TransferVisitor.create_all(
            dataset.get_stop_by_id(origin_stop_id), params.departure, Connection.empty()
        ):
            if transfer_visitor.transfer.to_stop_id not in params.origin_stop_ids:
                queue.put(transfer_visitor)

    previous_time = params.departure
    while not queue.empty():
        visitor = queue.get()
        if visitor.next_event() > previous_time:
            # Time has incremented, check if we have found a connection or passed the time limit
            previous_time = visitor.next_event()
            found_connections: list[Connection] = []
            for destination in destinations:
                if destination in visited_stops:
                    found_connections.append(visited_stops[destination])
            if found_connections:
                best_connection = max(found_connections, key=lambda conn: conn.quality)
                return SearchResult(connection=best_connection)
            if previous_time > time_limit:
                break
        new_visitors = visitor.next(visited_stops, visited_trips)
        for new_visitor in new_visitors:
            queue.put(new_visitor)
    
    return SearchResult(connection=None)
