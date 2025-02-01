from __future__ import annotations
from abc import abstractmethod
from collections import defaultdict
from csv import DictReader
from datetime import date, timedelta
from functools import cache
from os.path import isfile
from typing import Any, Callable, Iterable, Protocol, Self, overload

from .structures import (
    CalendarDatesRecord, CalendarRecord, LocationType, PickupDropoffType,
    Route, RouteType, Stop, StopTime, Transfer, TransferType, Trip
)


class Dataset:
    """An interface with the GTFS dataset."""

    config: dict[str, Any]
    _stops_by_id: dict[str, Stop]
    _stops_by_transfer_node_id: defaultdict[str, list[Stop]] = defaultdict()
    _stops_by_parent_station: defaultdict[str, list[Stop]] = defaultdict()
    _transfers_by_origin_stop_id: defaultdict[str, list[Transfer]] = defaultdict()
    _stop_times_by_trip: defaultdict[str, list[StopTime]]
    _stop_times_by_stop: defaultdict[str, list[StopTime]]
    _calendar_by_service_id: dict[str, CalendarRecord]
    _calendar_dates_by_service_id: dict[tuple[str, date], CalendarDatesRecord]

    def __init__(self, config: dict[str, Any]) -> None:
        """
        Load a GTFS dataset from a folder into a Dataset object.

        Parameters:
        :param config: The configuration dictionary (CONFIG in config.py).
        """

        self.config = config

        stops = self._read_csv_file("stops", self._to_stop)
        self._stops_by_id = self._index_by(stops, lambda stop: stop.stop_id)

        match config["TRANSFER_MODE"]:
            case "by_node_id":
                self._stops_by_transfer_node_id = self._group_by(stops, lambda stop: stop.transfer_node_id)
            case "by_parent_station":
                self._stops_by_parent_station = self._group_by(stops, lambda stop: stop.parent_station)
            case "by_transfers_txt":
                transfers = self._read_csv_file("transfers", self._to_transfer)
                self._transfers_by_origin_stop_id = self._group_by(transfers, lambda transfer: transfer.from_stop_id)

        routes = self._read_csv_file("routes", self._to_route)
        self._routes_by_id = self._index_by(routes, lambda route: route.route_id)

        trips = self._read_csv_file("trips", self._to_trip)
        self._trips_by_id = self._index_by(trips, lambda trip: trip.trip_id)

        stop_times = self._read_csv_file("stop_times", self._to_stop_time)
        self._stop_times_by_trip = self._group_by(
            stop_times, lambda stop_time: stop_time.trip_id, lambda stop_time: stop_time.stop_sequence
        )
        self._stop_times_by_stop = self._group_by(
            stop_times, lambda stop_time: stop_time.stop_id, lambda stop_time: stop_time.departure_time % timedelta(days=1)
        )

        calendar = self._read_optional_csv_file("calendar", self._to_calendar_record)
        self._calendar_by_service_id = self._index_by(calendar, lambda record: record.service_id)

        calendar_dates = self._read_optional_csv_file("calendar_dates", self._to_calendar_dates_record)
        self._calendar_dates_by_service_id = self._index_by(calendar_dates, lambda record: (record.service_id, record.date))

    def _read_csv_file[T](self, name: str, to_object: Callable[[dict[str, str]], T | None]) -> list[T]:
        """
        Read a CSV file from the dataset and convert it to a list of objects.

        Parameters:
        :param name: The name of the file to read, without the .txt extension.
        :param to_object: A function receiving a dictionary representing a single row (keys are headers) \
            and returning an object representing this row, or None to discard this row.
        """

        dataset_path = self.config["DATASET_PATH"]
        with open(f"{dataset_path}/{name}.txt", encoding="utf-8-sig", newline="") as csv_file:
            csv_reader = DictReader(csv_file, strict=True)
            return [obj for obj in map(to_object, csv_reader) if obj is not None]

    def _read_optional_csv_file[T](self, name: str, to_object: Callable[[dict[str, str]], T]) -> list[T]:
        """
        Read a CSV file from the dataset and convert it to a list of objects. If the file does not exist,
        return an empty list.

        Parameters:
        :param name: The name of the file to read, without the .txt extension.
        :param to_object: A function receiving a dictionary representing a single row (keys are headers) \
            and returning an object representing this row, or None to discard this row.
        """

        dataset_path = self.config["DATASET_PATH"]
        if isfile(f"{dataset_path}/{name}.txt"):
            return self._read_csv_file(name, to_object)
        else:
            return []

    def _index_by[T, I](self, table: list[T], get_index: Callable[[T], I]) -> dict[I, T]:
        """
        Index the contents of a list and return them as a dictionary.

        Parameters:
        :param table: The list to index.
        :param get_index: A function taking an element of the list and returning a value that should \
            be used as its index in the returned dictionary. The returned values should be unique.
        """

        return {get_index(record): record for record in table}

    def _group_by[T, I](
        self,
        table: list[T],
        get_index: Callable[[T], I | None],
        get_inner_sort_key: Callable[[T], Comparable] | None = None,
    ) -> defaultdict[I, list[T]]:
        """
        Group the contents of a list into smaller lists (groups) by some index, optionally order those \
            lists and return them as a defaultdict mapping indices to groups.

        Parameters:
        :param table: The list to group.
        :param get_index: A function taking an element of the list and returning a value that should \
            be used as the index of its group.
        :param get_inner_sort_key: A function taking an element of the list and returning a sort key \
            for the individual groups. If None (default), elements are not sorted.
        """

        new_table: defaultdict[I, list[T]] = defaultdict(list)
        for record in table:
            idx = get_index(record)
            if idx is not None:
                new_table[idx].append(record)
        if get_inner_sort_key is not None:
            for lst in new_table.values():
                lst.sort(key=get_inner_sort_key)
        return new_table

    def _to_stop(self, row: dict[str, str]) -> Stop:
        """Convert a dictionary obtained from a CSV row to a Stop object."""
        return Stop(
            _dataset=self,
            stop_id=row["stop_id"],
            stop_name=_get_or_default(row, "stop_name", None),
            location_type=_get_or_default(row, "location_type", LocationType.STOP_OR_PLATFORM, LocationType.from_field),
            parent_station=_get_or_default(row, "parent_station", None),
            transfer_node_id=(
                None if self.config["TRANSFER_MODE"] != "by_node_id"
                else _get_or_default(row, self.config["TRANSFER_NODE_ID"], None)
            ),
        )

    def _to_route(self, row: dict[str, str]) -> Route:
        """Convert a dictionary obtained from a CSV row to a Route object."""
        return Route(
            _dataset=self,
            route_id=row["route_id"],
            route_short_name=_get_or_default(row, "route_short_name", None),
            route_long_name=_get_or_default(row, "route_long_name", None),
            route_type=RouteType.from_field(row["route_type"]),
        )

    def _to_trip(self, row: dict[str, str]) -> Trip:
        """Convert a dictionary obtained from a CSV row to a Trip object."""
        return Trip(
            _dataset=self,
            trip_id=row["trip_id"],
            route_id=row["route_id"],
            service_id=row["service_id"],
            trip_short_name=_get_or_default(row, "trip_short_name", None),
        )

    def _to_stop_time(self, row: dict[str, str]) -> StopTime:
        """Convert a dictionary obtained from a CSV row to a StopTime object."""
        return StopTime(
            _dataset=self,
            trip_id=row["trip_id"],
            stop_sequence=int(row["stop_sequence"]),
            arrival_time=_parse_time(row["arrival_time"]),
            departure_time=_parse_time(row["departure_time"]),
            stop_id=row["stop_id"],
            pickup_type=_get_or_default(row, "pickup_type", PickupDropoffType.REGULAR, PickupDropoffType.from_field),
            drop_off_type=_get_or_default(row, "drop_off_type", PickupDropoffType.REGULAR, PickupDropoffType.from_field),
        )

    def _to_calendar_record(self, row: dict[str, str]) -> CalendarRecord:
        """Convert a dictionary obtained from a CSV row to a CalendarRecord object."""
        return CalendarRecord(
            _dataset=self,
            service_id=row["service_id"],
            weekday_services={i: bool(int(row[day])) for i, day in enumerate((
                "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
            ))},
            start_date=_parse_date(row["start_date"]),
            end_date=_parse_date(row["end_date"]),
        )

    def _to_calendar_dates_record(self, row: dict[str, str]) -> CalendarDatesRecord:
        """Convert a dictionary obtained from a CSV row to a CalendarDatesRecord object."""
        return CalendarDatesRecord(
            _dataset=self,
            service_id=row["service_id"],
            date=_parse_date(row["date"]),
            service_available=(row["exception_type"] == "1"),
        )

    def _to_transfer(self, row: dict[str, str]) -> Transfer | None:
        """Convert a dictionary obtained from a CSV row to a Transfer object, or None for an unsupported transfer."""
        for unsupported_header in ("from_trip_id", "to_trip_id", "from_route_id", "to_route_id"):
            if unsupported_header in row and row[unsupported_header] != "":
                return None
        transfer_time = max(
            self.config["MIN_TRANSFER_TIME"],
            _get_or_default(row, "min_transfer_time", self.config["MIN_TRANSFER_TIME"], int)
        )
        return Transfer(
            _dataset=self,
            from_stop_id=row["from_stop_id"],
            to_stop_id=row["to_stop_id"],
            transfer_type=_get_or_default(row, "transfer_type", TransferType.BY_TRANSFERS_UNTIMED, TransferType.from_field),
            transfer_time=transfer_time,
        )

    def get_stop_by_id(self, stop_id: str) -> Stop:
        """Get a Stop object from the dataset by its stop_id."""
        return self._stops_by_id[stop_id]

    def get_all_transfers_from(self, stop: Stop) -> Iterable[Transfer]:
        """
        Get all transfers from the dataset by the stop_id of the stop they start on.

        The transfer lookup depends on the "TRANSFER_MODE" value of the configuration.
        """

        match self.config["TRANSFER_MODE"]:
            case "by_node_id":
                if stop.transfer_node_id is None:
                    return []
                return (Transfer(
                    _dataset=self,
                    from_stop_id=stop.stop_id,
                    to_stop_id=target_stop.stop_id,
                    transfer_type=TransferType.BY_NODE_ID,
                    transfer_time=self.config["MIN_TRANSFER_TIME"],
                ) for target_stop in self._stops_by_transfer_node_id[stop.transfer_node_id])

            case "by_parent_station":
                if stop.parent_station is None:
                    return []
                return (Transfer(
                    _dataset=self,
                    from_stop_id=stop.stop_id,
                    to_stop_id=target_stop.stop_id,
                    transfer_type=TransferType.BY_PARENT_STATION,
                    transfer_time=self.config["MIN_TRANSFER_TIME"],
                ) for target_stop in self._stops_by_parent_station[stop.parent_station])

            case "by_transfers_txt":
                return self._transfers_by_origin_stop_id[stop.stop_id]

            case _: # either "none" or some invalid/unsupported value
                return []

    def get_route_by_id(self, route_id: str) -> Route:
        """Get a Route object from the dataset by its route_id."""
        return self._routes_by_id[route_id]

    def get_trip_by_id(self, trip_id: str) -> Trip:
        """Get a Trip object from the dataset by its trip_id."""
        return self._trips_by_id[trip_id]

    def get_stop_times_by_trip_id(self, trip_id: str) -> list[StopTime]:
        """Get a list of StopTimes occurring on the specified trip."""
        return self._stop_times_by_trip[trip_id]

    def get_stop_times_by_stop_id(self, stop_id: str) -> list[StopTime]:
        """Get a list of StopTimes occurring at the specified stop."""
        return self._stop_times_by_stop[stop_id]

    @cache
    def runs_on_day(self, service_id: str, service_day: date) -> bool:
        """Return True if the specified service_id runs on the specified service_date and False otherwise."""
        if (service_id, service_day) in self._calendar_dates_by_service_id:
            return self._calendar_dates_by_service_id[service_id, service_day].service_available
        else:
            calendar_record = self._calendar_by_service_id[service_id]
            return (
                service_day >= calendar_record.start_date and
                service_day <= calendar_record.end_date and
                calendar_record.weekday_services[service_day.weekday()]
            )

    def get_all_stop_ids_and_names(self) -> Iterable[tuple[str, str]]:
        """For every stop (location_type=0) in the dataset, return a tuple (stop_id, stop_name)."""
        return (
            (stop.stop_id, stop.stop_name) for stop in self._stops_by_id.values()
            if stop.stop_name is not None and stop.location_type == LocationType.STOP_OR_PLATFORM
        )

@overload
def _get_or_default[T](row: dict[str, str], key: str, default: T, mapping: None = None) -> str | T: ...

@overload
def _get_or_default[T](row: dict[str, str], key: str, default: T, mapping: Callable[[str], T]) -> T: ...

def _get_or_default[T](row: dict[str, str], key: str, default: str | T, mapping: Callable[[str], T] | None = None) -> str | T:
    """
    Try reading a key from a row dictionary. If it exists and its value is non-empty, return it, optionally
    passed through a mapping function. Otherwise return the provided default value.

    Parameters:
    :param row: A dictionary describing a CSV file row.
    :param key: The key to search for in the row.
    :param default: The value to return if the key is not present in the row or its value is an empty string.
    :param mapping: A function to call on the value if it is found in the row. If None (default), the value \
        is returned directly.
    """

    if key in row and row[key] != "":
        if mapping is None:
            return row[key]
        else:
            return mapping(row[key])
    else:
        return default


def _parse_time(time_str: str) -> timedelta:
    """Parse a time string in HH:MM:SS or H:MM:SS format."""
    h, m, s = map(int, time_str.split(":"))
    return timedelta(hours=h, minutes=m, seconds=s)

def _parse_date(date_str: str) -> date:
    """Parse a date string in YYYYMMDD format."""
    y, m, d = map(int, (date_str[:4], date_str[4:6], date_str[6:]))
    return date(year=y, month=m, day=d)


class Comparable(Protocol):
    """A type whose instances can be compared by the '<' operator."""

    @abstractmethod
    def __lt__(self, other: Self) -> bool:
        ...
