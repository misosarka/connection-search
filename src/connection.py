from dataclasses import dataclass
from .structures import Route, Stop, StopTime, Trip


@dataclass
class TripConnectionSegment:
    """A single segment of a connection representing a single trip."""

    start_stoptime: StopTime
    end_stoptime: StopTime

    @property
    def trip(self) -> Trip:
        return self.start_stoptime.get_trip()
    
    @property
    def start_stop(self) -> Stop:
        return self.start_stoptime.get_stop()
    
    @property
    def end_stop(self) -> Stop:
        return self.end_stoptime.get_stop()
    
    @property
    def route(self) -> Route:
        return self.trip.get_route()


class OpenTripConnectionSegment:
    """An open segment of a connection representing a trip with no defined end stop."""
    
    start_stoptime: StopTime

    @property
    def trip(self) -> Trip:
        return self.start_stoptime.get_trip()
    
    @property
    def start_stop(self) -> Stop:
        return self.start_stoptime.get_stop()
    
    @property
    def route(self) -> Route:
        return self.trip.get_route()


@dataclass
class Connection:
    """A sequence of trips (todo: and transfers), starting and ending in a stop."""

    segments: list[TripConnectionSegment]


@dataclass
class OpenConnection:
    """A sequence of trips (todo: and transfers), starting in a stop and ending on a trip."""

    segments: list[TripConnectionSegment]
    final_segment: OpenTripConnectionSegment
