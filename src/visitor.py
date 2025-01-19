from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from functools import total_ordering
from abc import ABC, abstractmethod

import pandas as pd

from .dataset import Dataset
from .connection import Connection, OpenConnection
from .structures import PickupDropoffType, Stop, StopTime, Trip


MIDNIGHT = time(0, 0)
ONE_DAY = timedelta(days=1)
TWENTY_FOUR_HOURS = pd.Timedelta("24 hours")
FORTY_EIGHT_HOURS = pd.Timedelta("48 hours")


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
    def create(cls, departure_stoptime: StopTime, service_day: date) -> "TripVisitor | None":
        """
        Attempt to create a TripVisitor for a trip starting with the specified departure and running on a specified service day.
        If there are no more valid stops on the trip after the departure, do not create anything and return None.
        """
        visitor = TripVisitor(
            trip=departure_stoptime.get_trip(),
            service_day=service_day,
            next_stoptime=departure_stoptime,
            next_stoptime_idx=-1
        )
        if not visitor._initial_find_next_stop(): # No valid stop after this one
            return None
        return visitor

    def next_event(self) -> datetime:
        return datetime.combine(self.service_day, MIDNIGHT) + self.next_stoptime.arrival_time

    def next(self, visited_stops: dict[str, Connection], visited_trips: dict[str, OpenConnection]) -> list[Visitor]:
        next_stop_id = self.next_stoptime.stop_id
        new_connection = visited_trips[self.trip.trip_id].to_connection(self.next_stoptime)
        visitors_to_return: list[Visitor] = []

        if next_stop_id in visited_stops:
            if new_connection.quality > visited_stops[next_stop_id].quality:
                # Found a better connection to an already visited stop - just replace it in visited_stops
                # (no need to create a new StopVisitor - one already exists)
                visited_stops[next_stop_id] = new_connection
        else:
            # Found a new stop
            new_stop_visitor = StopVisitor.create(self.next_stoptime, self.service_day)
            if new_stop_visitor is not None:
                visitors_to_return.append(new_stop_visitor)
                visited_stops[next_stop_id] = new_connection

        if self._update_next_stop():
            # There are still more stops on this trip
            visitors_to_return.append(self)

        return visitors_to_return

    def _update_next_stop(self) -> bool:
        """
        Update the next_stoptime and next_stoptime_idx to refer to the next stop on this trip where passengers can get off.
        If there is no such stop, return False. Otherwise return True.
        """
        dataset = self.trip._dataset
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
        dataset = self.trip._dataset
        self.next_stoptime_idx = dataset.get_index_in_stop_times_by_trip(self.trip.trip_id, self.next_stoptime.stop_sequence)
        return self._update_next_stop()


@dataclass
class StopVisitor(Visitor):
    stop: Stop
    next_departure: StopTime
    next_departure_time: datetime
    stop_departures_slice: slice
    """Slice into Dataset.stop_times_by_stop where departures for this stop are located."""
    next_departure_base_idx: int
    """Index after which to search for subsequent departures with times between 0:00 and 23:59."""
    next_departure_next_day_idx: int
    """Index after which to search for subsequent departures with times between 24:00 and 47:59."""

    @classmethod
    def create(self, arrival_stoptime: StopTime, service_day: date) -> "StopVisitor | None":
        """
        Attempt to create a StopVisitor for a stop after the arrival of a trip running on a specified service day.
        If there are no more valid trips from the stop in 24 hours, do not create anything and return None.
        """
        visitor = StopVisitor(
            stop=arrival_stoptime.get_stop(),
            next_departure=arrival_stoptime, # placeholder
            next_departure_time=datetime.combine(service_day, MIDNIGHT) + arrival_stoptime.arrival_time.to_pytimedelta(),
            stop_departures_slice=slice(0), # placeholder
            next_departure_base_idx=-1, # placeholder
            next_departure_next_day_idx=-1 # placeholder
        )
        if not visitor._initial_find_next_departure(): # No valid departure in 24 hours
            return None
        return visitor

    @classmethod
    def create_at_origin(self, dataset: Dataset, origin_stop_id: str, start_time: datetime) -> "StopVisitor | None":
        """
        Attempt to create a StopVisitor at the origin of the connection search.
        If there are no valid trips from the stop in 24 hours, do not create anything and return None.
        """
        origin_stop = dataset.get_stop_by_id(origin_stop_id)
        visitor = StopVisitor(
            stop=origin_stop,
            # It is OK to pass None here since next_departure will be set afterwards by _update_next_departure()
            next_departure=None, # type: ignore[arg-type]
            next_departure_time=start_time,
            stop_departures_slice=slice(0), # placeholder
            next_departure_base_idx=-1, # placeholder
            next_departure_next_day_idx=-1 # placeholder
        )
        if not visitor._initial_find_next_departure(): # No valid departure in 24 hours
            return None
        return visitor

    def next_event(self):
        return self.next_departure_time
    
    def next(self, visited_stops: dict[str, Connection], visited_trips: dict[str, OpenConnection]) -> list[Visitor]:
        next_trip_id = self.next_departure.trip_id
        next_trip_service_day = (self.next_departure_time - self.next_departure.departure_time).date()
        new_connection = visited_stops[self.stop.stop_id].to_open_connection(self.next_departure, next_trip_service_day)
        visitors_to_return: list[Visitor] = []

        if next_trip_id in visited_trips:
            if new_connection.quality > visited_trips[next_trip_id].quality:
                # Found a better connection to an already visited trip - just replace it in visited_trips
                # (no need to create a new TripVisitor - one already exists)
                visited_trips[next_trip_id] = new_connection
        else:
            # Found a new trip
            new_trip_visitor = TripVisitor.create(self.next_departure, next_trip_service_day)
            if new_trip_visitor is not None:
                visitors_to_return.append(new_trip_visitor)
                visited_trips[next_trip_id] = new_connection
        
        if self._update_next_departure():
            # There are still more departures from this stop
            visitors_to_return.append(self)
        
        return visitors_to_return

    def _update_next_departure(self) -> bool:
        """
        Update the next_departure, next_departure_time and both indices to refer to the next departure from this stop
        which passengers can get on. If there is no such departure in 24 hours, return False. Otherwise return True.

        This function looks both in the base times (0:00 to 23:59) and next-day times (24:00 to 47:59). This is because,
        for example, if the last stoptime is at 0:30, the next one can be at 24:40 of the previous service day.
        Currently, only times up to 47:59 are supported.
        """
        base_index = self.next_departure_base_idx
        next_day_index = self.next_departure_next_day_idx
        today = self.next_departure_time.date()

        # Search today using base times of this day
        today_base, base_index = self._first_valid_departure(
            index_before_start=base_index,
            service_day=today,
            until=TWENTY_FOUR_HOURS
        )

        # Search today using next-day times of the previous day
        today_next_day, next_day_index = self._first_valid_departure(
            index_before_start=next_day_index,
            service_day=today - ONE_DAY,
            until=FORTY_EIGHT_HOURS
        )

        # Get the earlier departure of the two if both exist, or only the one that exists
        if today_base is not None and (
            today_next_day is None or today_base.departure_time <= today_next_day.departure_time - TWENTY_FOUR_HOURS
        ):
            # Base is earlier (or they are equal), or only base exists
            self.next_departure = today_base
            self.next_departure_time = datetime.combine(today, MIDNIGHT) + today_base.departure_time.to_pytimedelta()
            self.next_departure_base_idx = base_index
            self.next_departure_next_day_idx = (next_day_index - 1) if today_next_day is not None else next_day_index
            return True
        elif today_next_day is not None:
            # Next-day is earlier, or only next-day exists
            self.next_departure = today_next_day
            self.next_departure_time = datetime.combine(today - ONE_DAY, MIDNIGHT) + today_next_day.departure_time.to_pytimedelta()
            self.next_departure_base_idx = (base_index - 1) if today_base is not None else base_index
            self.next_departure_next_day_idx = next_day_index
            return True
        # None of them exist => continue and search tomorrow
        
        tomorrow = today + ONE_DAY
        max_time = pd.Timedelta(self.next_departure_time - datetime.combine(today, MIDNIGHT))

        # Search tomorrow using base times of that day
        tomorrow_base, base_index_temp = self._first_valid_departure(
            index_before_start=self.stop_departures_slice.start - 1, # Search from the start
            service_day=tomorrow,
            until=max_time
        )

        # Search tomorrow using next-day times of the previous day
        tomorrow_next_day, next_day_index = self._first_valid_departure(
            index_before_start=base_index, # Search from current base index - the end of the base times
            service_day=tomorrow - ONE_DAY,
            until=TWENTY_FOUR_HOURS + max_time
        )

        base_index = base_index_temp

        # Get the earlier departure of the two if both exist, or only the one that exists
        if tomorrow_base is not None and (
            tomorrow_next_day is None or tomorrow_base.departure_time <= tomorrow_next_day.departure_time - TWENTY_FOUR_HOURS
        ):
            # Base is earlier (or they are equal), or only base exists
            self.next_departure = tomorrow_base
            self.next_departure_time = datetime.combine(tomorrow, MIDNIGHT) + tomorrow_base.departure_time.to_pytimedelta()
            self.next_departure_base_idx = base_index
            self.next_departure_next_day_idx = (next_day_index - 1) if tomorrow_next_day is not None else next_day_index
            return True
        elif tomorrow_next_day is not None:
            # Next-day is earlier, or only next-day exists
            self.next_departure = tomorrow_next_day
            self.next_departure_time = datetime.combine(tomorrow - ONE_DAY, MIDNIGHT) + tomorrow_next_day.departure_time.to_pytimedelta()
            self.next_departure_base_idx = (base_index - 1) if tomorrow_base is not None else base_index
            self.next_departure_next_day_idx = next_day_index
            return True
        # No valid departure in the next 24 hours
        return False
    
    def _initial_find_next_departure(self) -> bool:
        """
        Should be called after creating a new StopVisitor to find the indices into Dataset.stop_times_by_stop.

        Searches for the first departure that is after the initial arrival (whose time is passed in next_departure_time).
        Searches in both base and next-day times and sets their indices. Also sets stop_departures_slice.
        Finally calls _update_next_departure and returns its result.
        """
        dataset = self.stop._dataset
        self.stop_departures_slice = dataset.get_stop_times_slice_by_stop_id(self.stop.stop_id)
        arrival_time = pd.Timedelta(self.next_departure_time - datetime.combine(self.next_departure_time.date(), MIDNIGHT))
        time_to_search_base = arrival_time
        time_to_search_next_day = arrival_time + TWENTY_FOUR_HOURS

        start: int = self.stop_departures_slice.start
        end: int = self.stop_departures_slice.stop - 1
        while start <= end:
            middle = (start + end) // 2
            stoptime = dataset.get_stop_time_by_stop_on_index(middle).departure_time
            if stoptime < time_to_search_base:
                start = middle + 1
            elif stoptime > time_to_search_base:
                end = middle - 1
            else: # exact time match => need to check if this is the last one that is equal
                if middle + 1 >= self.stop_departures_slice.stop \
                        or dataset.get_stop_time_by_stop_on_index(middle + 1).departure_time > time_to_search_base:
                    end = middle
                    break
                else:
                    start = middle + 1
        self.next_departure_base_idx = end
        
        start = self.stop_departures_slice.start
        end = self.stop_departures_slice.stop - 1
        while start <= end:
            middle = (start + end) // 2
            stoptime = dataset.get_stop_time_by_stop_on_index(middle).departure_time
            if stoptime < time_to_search_next_day:
                start = middle + 1
            elif stoptime > time_to_search_next_day:
                end = middle - 1
            else: # exact time match => need to check if this is the last one that is equal
                if middle + 1 >= self.stop_departures_slice.stop \
                        or dataset.get_stop_time_by_stop_on_index(middle + 1).departure_time > time_to_search_next_day:
                    end = middle
                    break
                else:
                    start = middle + 1
        self.next_departure_next_day_idx = end

        return self._update_next_departure()

    def _first_valid_departure(
        self,
        index_before_start: int,
        service_day: date,
        until: pd.Timedelta
    ) -> tuple[StopTime | None, int]:
        """
        Find the first departure after index_before_start running on service_day with a departure time earlier than
        the specified "until" parameter. If it exists, return its StopTime and index. If it does not, return None
        and the index of the last departure that matched by the stop_id and "until" parameter.

        The service_day parameter is passed to the dataset directly. This means that, for example, if a service runs
        on Monday at 24:30 according to the dataset, it can be returned if a Monday is passed as the service_day parameter,
        but it will not be returned if Tuesday is passed.
        """
        dataset = self.stop._dataset
        index = index_before_start
        while True:
            index += 1
            if index >= dataset.stop_times_length:
                return None, index - 1
            next_stoptime = dataset.get_stop_time_by_stop_on_index(index)
            if next_stoptime.stop_id != self.stop.stop_id:
                return None, index - 1
            if next_stoptime.departure_time >= until:
                return None, index - 1
            service_id = dataset.get_trip_by_id(next_stoptime.trip_id).service_id
            if dataset.runs_on_day(service_id, service_day) and next_stoptime.pickup_type != PickupDropoffType.NOT_AVAILABLE:
                return next_stoptime, index
