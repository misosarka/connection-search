from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, time
from functools import total_ordering
from .structures import Route, Stop, StopTime, Transfer, Trip


MIDNIGHT = time(0, 0)


@dataclass
class TripConnectionSegment:
    """
    A single segment of a connection representing a single trip.
    
    The start_stoptime and end_stoptime represent where and when the user should get on and get off.
    The service_day represents a date for which the trip runs, as in trips.txt.
    For example, if the trip was from 0:30 to 1:00 on Tuesday, but the dataset described it as a trip
    on Monday from 24:30 to 25:00, the service_day would be the date for Monday.
    """

    start_stoptime: StopTime
    end_stoptime: StopTime
    service_day: date

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
    def start_departure(self) -> datetime:
        return datetime.combine(self.service_day, MIDNIGHT) + self.start_stoptime.departure_time
    
    @property
    def end_arrival(self) -> datetime:
        return datetime.combine(self.service_day, MIDNIGHT) + self.end_stoptime.arrival_time
    
    @property
    def route(self) -> Route:
        return self.trip.get_route()


@dataclass
class OpenTripConnectionSegment:
    """
    An open segment of a connection representing a trip with no defined end stop.
    
    For field explanations, see TripConnectionSegment.
    """
    
    start_stoptime: StopTime
    service_day: date

    @property
    def trip(self) -> Trip:
        return self.start_stoptime.get_trip()
    
    @property
    def start_stop(self) -> Stop:
        return self.start_stoptime.get_stop()
    
    @property
    def start_departure(self) -> datetime:
        return datetime.combine(self.service_day, MIDNIGHT) + self.start_stoptime.departure_time
    
    @property
    def route(self) -> Route:
        return self.trip.get_route()


@dataclass
class TransferConnectionSegment:
    """A single segment of a connection representing a single transfer between two stops."""

    transfer: Transfer
    start_departure: datetime
    end_arrival: datetime

    @property
    def start_stop(self) -> Stop:
        return self.transfer.get_from_stop()
    
    @property
    def end_stop(self) -> Stop:
        return self.transfer.get_to_stop()


@total_ordering
@dataclass
class ConnectionQuality:
    """
    A measure of quality of Connections and OpenConnections.

    An empty Connection has a ConnectionQuality with first_departure=None and transfer_count=0.

    Only instances with the same endpoint (stop for Connections and trip for OpenConnections) should be compared.
    The comparison is defined as follows:
    1. A ConnectionQuality with first_departure=None is better than any other.
    2. The instance with the later first departure time is better (meaning its ConnectionQuality is higher).
    3. If both instances have the same first departure time, the instance with fewer transfers is better.
    4. If the first departure times and transfer counts are both the same, the qualities are equal.
    """
    
    first_departure: datetime | None
    transfer_count: int

    def __lt__(self, other: ConnectionQuality) -> bool:
        # self < other => True if self has lower quality => earlier departure or higher transfer count
        if self.first_departure is None:
            return False
        if other.first_departure is None:
            return True
        if self.first_departure < other.first_departure:
            return True
        if self.first_departure > other.first_departure:
            return False
        return self.transfer_count > other.transfer_count


@dataclass
class Connection:
    """A sequence of trips and transfers, starting and ending in a stop."""

    segments: list[TripConnectionSegment | TransferConnectionSegment]

    @classmethod
    def empty(cls) -> Connection:
        return cls([])
    
    def to_open_connection(self, last_departure: StopTime, last_departure_service_day: date) -> OpenConnection:
        return OpenConnection(self.segments, OpenTripConnectionSegment(last_departure, last_departure_service_day))
    
    def with_transfer(self, transfer: Transfer, start_departure: datetime, end_arrival: datetime) -> Connection:
        return Connection(self.segments + [TransferConnectionSegment(transfer, start_departure, end_arrival)])
    
    @property
    def first_departure(self) -> datetime | None:
        if not self.segments:
            return None
        return self.segments[0].start_departure
    
    @property
    def last_arrival(self) -> datetime | None:
        if not self.segments:
            return None
        return self.segments[-1].end_arrival

    @property
    def transfer_count(self) -> int:
        trip_segments = sum(1 for segment in self.segments if isinstance(segment, TripConnectionSegment))
        return max(trip_segments - 1, 0)
    
    @property
    def quality(self) -> ConnectionQuality:
        return ConnectionQuality(first_departure=self.first_departure, transfer_count=self.transfer_count)


@dataclass
class OpenConnection:
    """A sequence of trips and transfers, starting in a stop and ending on a trip."""

    segments: list[TripConnectionSegment | TransferConnectionSegment]
    final_segment: OpenTripConnectionSegment

    def to_connection(self, last_arrival: StopTime) -> Connection:
        last_segment = TripConnectionSegment(self.final_segment.start_stoptime, last_arrival, self.final_segment.service_day)
        return Connection(self.segments + [last_segment])

    @property
    def first_departure(self) -> datetime:
        if not self.segments:
            return self.final_segment.start_departure
        else:
            return self.segments[0].start_departure

    @property
    def transfer_count(self) -> int:
        return sum(1 for segment in self.segments if isinstance(segment, TripConnectionSegment))
    
    @property
    def quality(self) -> ConnectionQuality:
        return ConnectionQuality(first_departure=self.first_departure, transfer_count=self.transfer_count)
