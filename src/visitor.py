from dataclasses import dataclass
from datetime import date, datetime, time
from functools import total_ordering
from abc import ABC, abstractmethod
from .connection import Connection, OpenConnection
from .structures import PickupDropoffType, StopTime, Trip


MIDNIGHT = time(0, 0)


@total_ordering
class Visitor(ABC):
    """
    An abstract class, generalizing for both StopVisitor and TripVisitor.

    Derived classes need to implement the next_event() and next() methods.
    """

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Visitor):
            return self.next_event() == other.next_event()
        return NotImplemented
    
    def __lt__(self, other: "Visitor") -> bool:
        return self.next_event() < other.next_event()

    @abstractmethod
    def next_event(self) -> datetime:
        """
        Returns the datetime of the next event (departure for StopVisitor or arrival for TripVisitor).
        Visitor instances are compared according to this value.
        """

    @abstractmethod
    def next(self, visited_stops: dict[str, Connection], visited_trips: dict[str, OpenConnection]) -> list["Visitor"]:
        """
        Handle the next event (departure or stop).

        :param visited_stops: A dictionary with the current best Connections to all stops that have already been reached. \
        The function can mutate this dictionary.
        :param visited_trips: A dictionary with the current best OpenConnections to all trips that have already been reached. \
        The function can mutate this dictionary.
        :returns: A list of Visitors that should be enqueued.
        """


@dataclass
class TripVisitor(Visitor):
    trip: Trip
    service_day: date
    next_stoptime: StopTime
    next_stoptime_idx: int

    @classmethod
    def create(cls, departure_stoptime: StopTime, service_day: date) -> "TripVisitor" | None:
        """
        Attempt to create a TripVisitor for a trip starting with the specified departure and running on a specified service day.
        If there are no more valid stops on the trip after the departure, do not create anything and return None.
        """
        visitor = TripVisitor(
            trip=departure_stoptime._dataset.get_trip_by_id(departure_stoptime.trip_id),
            service_day=service_day,
            next_stoptime=departure_stoptime,
            next_stoptime_idx=-1
        )
        if not visitor._initial_find_next_stop(): # No valid stop after this one
            return None
        return visitor

    def next_event(self) -> datetime:
        return datetime.combine(self.service_day, MIDNIGHT) + self.next_stoptime.arrival_time

    def next(self, visited_stops: dict[str, Connection], visited_trips: dict[str, OpenConnection]) -> list["Visitor"]:
        pass # TODO

    def _update_next_stop(self) -> bool:
        """
        Update the next_stoptime and next_stoptime_idx to refer to the next stop on this trip where passengers can get off.
        If there is no such stop, return False. Otherwise return True.
        """
        dataset = self.next_stoptime._dataset
        index = self.next_stoptime_idx
        while True:
            index += 1
            if index >= dataset.stop_times_length: # End of the DataFrame
                return False
            next_stoptime = dataset.get_stop_time_by_trip_on_index(index)
            if next_stoptime.trip_id != self.trip.trip_id: # End of the sequence for this trip
                return False
            if next_stoptime.drop_off_type != PickupDropoffType.NOT_AVAILABLE:
                self.next_stoptime = next_stoptime
                self.next_stoptime_idx = index
                return True
    
    def _initial_find_next_stop(self) -> bool:
        """
        Should be called after creating a new TripVisitor to find the index into Dataset.stop_times_by_trip.

        Searches for the initial StopTime (passed in next_stoptime) in the dataset, writes its index into next_stoptime_idx,
        calls _update_next_stop() and returns its result.
        """
        dataset = self.next_stoptime._dataset
        self.next_stoptime_idx = dataset.get_index_in_stop_times_by_trip(self.trip.trip_id, self.next_stoptime.stop_sequence)
        return self._update_next_stop()
