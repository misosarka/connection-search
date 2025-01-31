from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from functools import total_ordering
from abc import ABC, abstractmethod
from typing import Iterable

from .new_dataset import Dataset
from .connection import Connection, OpenConnection
from .structures import PickupDropoffType, Stop, StopTime, Transfer, Trip


MIDNIGHT = time(0, 0)
ONE_DAY = timedelta(days=1)


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
    
    def __lt__(self, other: Visitor) -> bool:
        return self.next_event() < other.next_event()

    @abstractmethod
    def next_event(self) -> datetime:
        """
        Returns the datetime of the next event (departure for StopVisitor or arrival for TripVisitor).
        Visitor instances are compared according to this value.
        """

    @abstractmethod
    def next(self, visited_stops: dict[str, Connection], visited_trips: dict[str, OpenConnection]) -> list[Visitor]:
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
    trip_stoptimes: list[StopTime]
    next_stoptime_idx: int

    @classmethod
    def create(cls, departure_stoptime: StopTime, service_day: date) -> TripVisitor | None:
        """
        Attempt to create a TripVisitor for a trip starting with the specified departure and running on a specified service day.
        If there are no more valid stops on the trip after the departure, do not create anything and return None.
        """

        visitor = cls(
            trip=departure_stoptime.get_trip(),
            service_day=service_day,
            trip_stoptimes=[], # placeholder
            next_stoptime_idx=-1, # placeholder
        )
        if not visitor._initial_find_next_stop(departure_stoptime): # No valid stop after this one
            return None
        return visitor

    def next_event(self) -> datetime:
        return datetime.combine(self.service_day, MIDNIGHT) + self.trip_stoptimes[self.next_stoptime_idx].arrival_time

    def next(self, visited_stops: dict[str, Connection], visited_trips: dict[str, OpenConnection]) -> list[Visitor]:
        next_stoptime = self.trip_stoptimes[self.next_stoptime_idx]
        next_stop_id = next_stoptime.stop_id
        new_connection = visited_trips[self.trip.trip_id].to_connection(next_stoptime)
        visitors_to_return: list[Visitor] = []
        add_transfers = False

        if next_stop_id in visited_stops:
            if new_connection.quality > visited_stops[next_stop_id].quality:
                # Found a better connection to an already visited stop - just replace it in visited_stops
                # (no need to create a new StopVisitor - one already exists)
                visited_stops[next_stop_id] = new_connection
                add_transfers = True
        else:
            # Found a new stop
            new_stop_visitor = StopVisitor.create(next_stoptime, self.service_day)
            if new_stop_visitor is not None:
                visitors_to_return.append(new_stop_visitor)
                visited_stops[next_stop_id] = new_connection
            add_transfers = True
        
        if add_transfers:
            visitors_to_return.extend(TransferVisitor.create_all(
                next_stoptime.get_stop(),
                self.next_event(),
                new_connection
            ))

        if self._update_next_stop():
            # There are still more stops on this trip
            visitors_to_return.append(self)

        return visitors_to_return

    def _update_next_stop(self) -> bool:
        """
        Update the next_stoptime_idx to refer to the next stop on this trip where passengers can get off.
        If there is no such stop, return False. Otherwise return True.
        """

        index = self.next_stoptime_idx
        trip_stoptimes_len = len(self.trip_stoptimes)
        while True:
            index += 1
            if index >= trip_stoptimes_len: # Past the end of the list
                return False
            next_stoptime = self.trip_stoptimes[index]
            if next_stoptime.drop_off_type != PickupDropoffType.NOT_AVAILABLE:
                self.next_stoptime_idx = index
                return True
    
    def _initial_find_next_stop(self, initial_stoptime: StopTime) -> bool:
        """
        Should be called after creating a new TripVisitor to find the index into Dataset.stop_times_by_trip.

        Gets the list of all StopTimes on this trip, searches for the index of the initial StopTime in it
        and writes it into next_stoptime_idx. Finally calls _update_next_stop() and returns its result.
        """

        self.trip_stoptimes = trip_stoptimes = self.trip.get_stop_times()
        initial_stop_sequence = initial_stoptime.stop_sequence

        start = 0
        end = len(self.trip_stoptimes) - 1
        middle = (start + end) // 2
        while trip_stoptimes[middle].stop_sequence != initial_stop_sequence:
            if trip_stoptimes[middle].stop_sequence < initial_stop_sequence:
                start = middle + 1
            else:
                end = middle - 1
            middle = (start + end) // 2
        self.next_stoptime_idx = middle

        return self._update_next_stop()


@dataclass
class StopVisitor(Visitor):
    stop: Stop
    next_departure_time: datetime
    stop_departures: list[StopTime]
    """A list of all departures from this stop, ordered by departure time (modulo 24 hours)."""
    next_departure_idx: int
    """Index into stop_departures of the next departure from this stop."""

    @classmethod
    def create(cls, arrival_stoptime: StopTime, service_day: date) -> StopVisitor | None:
        """
        Attempt to create a StopVisitor for a stop after the arrival of a trip running on a specified service day.
        If there are no more valid trips from the stop in 24 hours, do not create anything and return None.
        """

        visitor = cls(
            stop=arrival_stoptime.get_stop(),
            next_departure_time=datetime.combine(service_day, MIDNIGHT) + arrival_stoptime.arrival_time,
            stop_departures=[], # placeholder
            next_departure_idx=-1, # placeholder
        )
        if not visitor._initial_find_next_departure(): # No valid departure in 24 hours
            return None
        return visitor

    @classmethod
    def create_at_origin(cls, dataset: Dataset, origin_stop_id: str, start_time: datetime) -> StopVisitor | None:
        """
        Attempt to create a StopVisitor at the origin of the connection search.
        If there are no valid trips from the stop in 24 hours, do not create anything and return None.
        """

        origin_stop = dataset.get_stop_by_id(origin_stop_id)
        visitor = cls(
            stop=origin_stop,
            # We can allow finding a trip that departs exactly at the start time of the search
            next_departure_time=start_time - timedelta(microseconds=1),
            stop_departures=[], # placeholder
            next_departure_idx=-1, # placeholder
        )
        if not visitor._initial_find_next_departure(): # No valid departure in 24 hours
            return None
        return visitor

    @classmethod
    def create_from_transfer(cls, transfer: Transfer, transfer_arrival_time: datetime) -> StopVisitor | None:
        """
        Attempt to create a StopVisitor at the end of the specified transfer.
        If there are no valid trips from the stop in 24 hours, do not create anything and return None.
        """

        stop = transfer.get_to_stop()
        visitor = cls(
            stop=stop,
            # We can allow finding a trip that departs exactly at the arrival of the transfer
            next_departure_time=transfer_arrival_time - timedelta(microseconds=1),
            stop_departures=[], # placeholder
            next_departure_idx=-1, # placeholder
        )
        if not visitor._initial_find_next_departure(): # No valid departure in 24 hours
            return None
        return visitor

    def next_event(self) -> datetime:
        return self.next_departure_time
    
    def next(self, visited_stops: dict[str, Connection], visited_trips: dict[str, OpenConnection]) -> list[Visitor]:
        next_departure = self.stop_departures[self.next_departure_idx]
        next_trip_id = next_departure.trip_id
        next_trip_service_day = (self.next_departure_time - next_departure.departure_time).date()
        new_connection = visited_stops[self.stop.stop_id].to_open_connection(next_departure, next_trip_service_day)
        visitors_to_return: list[Visitor] = []

        if next_trip_id in visited_trips:
            if new_connection.quality > visited_trips[next_trip_id].quality:
                # Found a better connection to an already visited trip - just replace it in visited_trips
                # (no need to create a new TripVisitor - one already exists)
                visited_trips[next_trip_id] = new_connection
        else:
            # Found a new trip
            new_trip_visitor = TripVisitor.create(next_departure, next_trip_service_day)
            if new_trip_visitor is not None:
                visitors_to_return.append(new_trip_visitor)
                visited_trips[next_trip_id] = new_connection
        
        if self._update_next_departure():
            # There are still more departures from this stop
            visitors_to_return.append(self)
        
        return visitors_to_return

    def _update_next_departure(self) -> bool:
        """
        Update the next_departure_time and next_departure_idx to refer to the next departure from this stop which
        passengers can get on. If there is no such departure in 24 hours, return False. Otherwise return True.
        """

        index = self.next_departure_idx
        today = self.next_departure_time.date()
        stop_departures_len = len(self.stop_departures)

        while True: # Search from the next departure up until midnight
            index += 1
            if index >= stop_departures_len: # Past the end of list => need to search from the start again
                break
            next_departure = self.stop_departures[index]
            next_departure_full_days = next_departure.departure_time // ONE_DAY
            next_departure_service_day = today - timedelta(days=next_departure_full_days)
            if (
                next_departure.get_trip().runs_on_day(next_departure_service_day)
                and next_departure.pickup_type != PickupDropoffType.NOT_AVAILABLE
            ):
                self.next_departure_idx = index
                self.next_departure_time = datetime.combine(next_departure_service_day, MIDNIGHT) + next_departure.departure_time
                return True
        
        index = -1
        tomorrow = today + ONE_DAY
        time_limit = self.next_departure_time - datetime.combine(self.next_departure_time.date(), MIDNIGHT)

        while True: # Search from midnight up until 24 hours after the last departure
            index += 1
            if index >= stop_departures_len: # Past the end of list again => no departure in the next 24 hours
                return False
            next_departure = self.stop_departures[index]
            next_departure_full_days, next_departure_base_time = divmod(next_departure.departure_time, ONE_DAY)
            if next_departure_base_time >= time_limit: # Past the 24 hour limit
                return False
            next_departure_service_day = tomorrow - timedelta(days=next_departure_full_days)
            if (
                next_departure.get_trip().runs_on_day(next_departure_service_day)
                and next_departure.pickup_type != PickupDropoffType.NOT_AVAILABLE
            ):
                self.next_departure_idx = index
                self.next_departure_time = datetime.combine(next_departure_service_day, MIDNIGHT) + next_departure.departure_time
                return True

    def _initial_find_next_departure(self) -> bool:
        """
        Should be called after creating a new StopVisitor.

        Searches for the first departure that is after the initial arrival (whose time is passed in next_departure_time).
        Then calls _update_next_departure and returns its result.
        """

        self.stop_departures = stop_departures = self.stop.get_departures()
        time_to_search = self.next_departure_time - datetime.combine(self.next_departure_time.date(), MIDNIGHT)
        stop_departures_len = len(stop_departures)

        if stop_departures_len == 0:
            return False

        start = 0
        end = stop_departures_len # The first departure after the initial arrival can be past the end of the list
        middle = (start + end) // 2
        while not (
            # Either at the end of the list with the previous departure still before or at time_to_search...
            (middle == stop_departures_len and stop_departures[middle - 1].departure_time % ONE_DAY <= time_to_search) or (
                # ...or at a departure which is after time_to_search...
                stop_departures[middle].departure_time % ONE_DAY > time_to_search and (
                    # ...and the previous one either does not exist,...
                    middle == 0 or
                    # ...or it is before or at time_to_search.
                    stop_departures[middle - 1].departure_time % ONE_DAY <= time_to_search
                )
            )
        ):
            if stop_departures[middle].departure_time % ONE_DAY <= time_to_search:
                start = middle + 1
            else:
                end = middle - 1
            middle = (start + end) // 2
        
        self.next_departure_idx = middle - 1
        return self._update_next_departure()


@dataclass
class TransferVisitor(Visitor):
    transfer: Transfer
    transfer_start_time: datetime
    transfer_end_time: datetime
    connection: Connection
    """
    Unlike TripVisitors and StopVisitors, TransferVisitors have their connection saved inside them, which ensures that it cannot
    be modified in the middle of the transfer.
    """

    @staticmethod
    def create_all(origin_stop: Stop, arrival_time: datetime, connection: Connection) -> Iterable[TransferVisitor]:
        """Find all transfers that can be realised from a stop and create a TransferVisitor for each of them."""
        return (TransferVisitor(
            transfer=transfer,
            transfer_start_time=arrival_time,
            transfer_end_time=arrival_time + timedelta(seconds=transfer.transfer_time),
            connection=connection
        ) for transfer in origin_stop.get_all_transfers())

    def next_event(self) -> datetime:
        return self.transfer_end_time
    
    def next(self, visited_stops: dict[str, Connection], _: dict[str, OpenConnection]) -> list[Visitor]:
        new_connection = self.connection.with_transfer(self.transfer, self.transfer_start_time, self.transfer_end_time)
        target_stop_id = self.transfer.to_stop_id

        if target_stop_id in visited_stops:
            if new_connection.quality > visited_stops[target_stop_id].quality:
                # Found a better connection to an already visited stop - just replace it in visited_stops
                # (no need to create a new StopVisitor - one already exists)
                visited_stops[target_stop_id] = new_connection
        else:
            # Found a new stop
            new_stop_visitor = StopVisitor.create_from_transfer(self.transfer, self.transfer_end_time)
            if new_stop_visitor is not None:
                visited_stops[target_stop_id] = new_connection
                return [new_stop_visitor]

        return []
