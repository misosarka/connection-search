from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from .dataset import Dataset


class MalformedGTFSError(Exception):
    """An exception signifying that the GTFS dataset does not comply with the specification."""


class LocationType(Enum):
    """
    An enumeration for the stops.location_type field.

    Determines what kind of location a Stop object represents - a normal stop or platform, a station
    containing multiple platforms, an entrance to or exit from a station, a generic node used for
    pathway linking, or a boarding area on a platform.
    """

    STOP_OR_PLATFORM = 0
    STATION = 1
    ENTRANCE_OR_EXIT = 2
    GENERIC_NODE = 3
    BOARDING_AREA = 4

    @staticmethod
    def from_field(field: str) -> LocationType:
        """Convert a string field from a CSV file to a LocationType."""
        value = int(field)
        if 0 <= value <= 4:
            return LocationType(value)
        else:
            raise MalformedGTFSError("stops.location_type not in valid range")


@dataclass
class Stop:
    """
    A single record in the stops.txt file in the GTFS dataset.

    Represents a location where passengers can board and disembark vehicles, some related location
    (e.g. a station entrance) or a group of locations presented as one station.
    """

    _dataset: Dataset = field(repr=False)
    stop_id: str
    stop_name: str | None
    location_type: LocationType
    parent_station: str | None
    transfer_node_id: str | None

    def get_all_transfers(self) -> Iterable[Transfer]:
        """
        Return all transfers that originate at this stop.

        The transfer lookup depends on the "TRANSFER_MODE" value of the configuration.
        """
        return self._dataset.get_all_transfers_from(self)

    def get_departures(self) -> list[StopTime]:
        """Return a list of all StopTimes that occur at this stop."""
        return self._dataset.get_stop_times_by_stop_id(self.stop_id)


class RouteType(Enum):
    """
    An enumeration for the routes.route_type field.

    Represents the mode of transport that this route uses.
    """

    TRAM_LIGHT_RAIL = 0
    METRO_SUBWAY = 1
    RAIL = 2
    BUS = 3
    FERRY = 4
    CABLE_TRAM = 5
    AERIAL_LIFT = 6
    FUNICULAR = 7
    TROLLEYBUS = 11
    MONORAIL = 12

    @staticmethod
    def from_field(field: str) -> RouteType:
        """
        Convert a string field from a CSV file to a RouteType.

        All values from the standard specification are supported, along with some (but not all) values from
        the Google Transit extension specification.
        """

        match int(field):
            case x if x == 0 or 900 <= x <= 906:
                return RouteType.TRAM_LIGHT_RAIL
            case x if x == 1 or 400 <= x <= 404:
                return RouteType.METRO_SUBWAY
            case x if x == 2 or 100 <= x <= 117:
                return RouteType.RAIL
            case x if x == 3 or 200 <= x <= 209 or 700 <= x <= 716:
                return RouteType.BUS
            case 4 | 1000 | 1200:
                return RouteType.FERRY
            case 5:
                return RouteType.CABLE_TRAM
            case x if x == 6 or 1300 <= x <= 1307:
                return RouteType.AERIAL_LIFT
            case 7 | 1400:
                return RouteType.FUNICULAR
            case 11 | 800:
                return RouteType.TROLLEYBUS
            case 12 | 405:
                return RouteType.MONORAIL
            case x if x in (1100, 1700, 1702) or 1500 <= x <= 1507:
                raise RuntimeError(f"routes.route_type {x} is not supported")
            case _:
                raise MalformedGTFSError(f"routes.route_type {x} not in valid range")

    def __str__(self) -> str:
        """Get a string representation of this route type."""
        match self:
            case RouteType.TRAM_LIGHT_RAIL | RouteType.CABLE_TRAM:
                return "tramvaj"
            case RouteType.METRO_SUBWAY:
                return "metro"
            case RouteType.RAIL | RouteType.MONORAIL:
                return "vlak"
            case RouteType.BUS:
                return "autobus"
            case RouteType.FERRY:
                return "přívoz"
            case RouteType.AERIAL_LIFT | RouteType.FUNICULAR:
                return "lanová dráha"
            case RouteType.TROLLEYBUS:
                return "trolejbus"
            case _:
                raise MalformedGTFSError("routes.route_type not in valid range")


@dataclass
class Route:
    """
    A single record in the routes.txt file in the GTFS dataset.

    Represents a group of trips that are referred to by a common name (e.g. a Metro line or a bus route).
    """

    _dataset: Dataset = field(repr=False)
    route_id: str
    route_short_name: str | None
    route_long_name: str | None
    route_type: RouteType

    def get_route_short_name(self) -> str:
        """Get a short string representation of this route."""
        if self.route_short_name is not None:
            return self.route_short_name 
        if self.route_long_name is not None:
            return self.route_long_name
        raise MalformedGTFSError("both routes.route_short_name and routes.route_long_name are empty")

    def get_route_full_name(self) -> str:
        """Get a full string representation of this route, including its route type."""
        route_type = str(self.route_type).capitalize()
        if self.route_short_name is None:
            return f"{route_type} ({self.route_long_name})"
        elif self.route_long_name is None:
            return f"{route_type} {self.route_short_name}"
        else:
            return f"{route_type} {self.route_short_name} ({self.route_long_name})"


@dataclass
class Trip:
    """
    A single record in the trips.txt file in the GTFS dataset.

    Represents a single service running on a specified time and along a specified path according to a schedule.
    """

    _dataset: Dataset = field(repr=False)
    trip_id: str
    route_id: str
    service_id: str
    trip_short_name: str | None

    def get_trip_name(self) -> str:
        """Get a string representation of this trip (or its route, if this trip does not have one)."""
        route_short_name = self._dataset.get_route_by_id(self.route_id).get_route_short_name()
        if self.trip_short_name is not None:
            return f"{self.trip_short_name} ({route_short_name})"
        else:
            return route_short_name

    def get_route(self) -> Route:
        """Get a Route to which this trip belongs."""
        return self._dataset.get_route_by_id(self.route_id)

    def get_stop_times(self) -> list[StopTime]:
        """Return a list of all StopTimes that occur on this trip."""
        return self._dataset.get_stop_times_by_trip_id(self.trip_id)

    def runs_on_day(self, service_day: date) -> bool:
        """Return whether this trip runs on the specified service day."""
        return self._dataset.runs_on_day(self.service_id, service_day)


class PickupDropoffType(Enum):
    """
    An enumeration for the stop_times.pickup_type and stop_times.drop_off_type fields.

    Represents whether passengers can board and disembark a vehicle on this stop, and if so, what they need
    to do to achieve that.
    """

    REGULAR = 0
    NOT_AVAILABLE = 1
    PHONE_AGENCY = 2
    COORDINATE_WITH_DRIVER = 3

    @staticmethod
    def from_field(field: str) -> PickupDropoffType:
        """Convert a string field from a CSV file to a PickupDropoffType."""
        value = int(field)
        if 0 <= value <= 3:
            return PickupDropoffType(value)
        else:
            raise MalformedGTFSError("stop_times.pickup_type or stop_times.drop_off_type not in valid range")


@dataclass
class StopTime:
    """
    A single record in the stop_times.txt file in the GTFS dataset.

    Represents a scheduled time when a trip arrives to and departs from a stop.
    """

    _dataset: Dataset = field(repr=False)
    trip_id: str
    stop_sequence: int
    arrival_time: timedelta
    departure_time: timedelta
    stop_id: str
    pickup_type: PickupDropoffType
    drop_off_type: PickupDropoffType

    def get_stop(self) -> Stop:
        """Get a Stop at which this stop time occurs."""
        return self._dataset.get_stop_by_id(self.stop_id)

    def get_trip(self) -> Trip:
        """Get a Trip on which this stop time occurs."""
        return self._dataset.get_trip_by_id(self.trip_id)


@dataclass
class CalendarRecord:
    """
    A single record in the calendar.txt file in the GTFS dataset.

    Describes a regular weekly schedule for a service that can be referred to by multiple routes.
    """

    _dataset: Dataset = field(repr=False)
    service_id: str
    weekday_services: dict[int, bool]
    start_date: date
    end_date: date


@dataclass
class CalendarDatesRecord:
    """
    A single record in the calendar_dates.txt file in the GTFS dataset.

    Describes an exception to the regular weekly schedule.
    """

    _dataset: Dataset = field(repr=False)
    service_id: str
    date: date
    service_available: bool


class TransferType(Enum):
    """
    An enumeration for the transfers.transfer_type field.

    The values starting with BY_TRANSFERS correspond to the allowed values of the field. Additionally,
    a TransferType can signify that the transfer did not originate from a transfers.txt record, but from
    a matching node_id (specified in the configuration) or a matching parent station.
    """

    BY_TRANSFERS_UNTIMED = 0
    BY_TRANSFERS_GUARANTEED = 1
    BY_TRANSFERS_TIMED = 2
    BY_TRANSFERS_PROHIBITED = 3
    BY_TRANSFERS_INSEAT = 4
    BY_TRANSFERS_REBOARD = 5
    BY_NODE_ID = -1
    BY_PARENT_STATION = -2

    @staticmethod
    def from_field(field: str) -> TransferType:
        """Convert a string field from a CSV file to a TransferType."""
        value = int(field)
        if 0 <= value <= 5:
            return TransferType(value)
        else:
            raise MalformedGTFSError("transfers.transfer_type not in valid range")


@dataclass
class Transfer:
    """
    A single record in the transfers.txt file in the GTFS dataset.

    Represents a possible walking connection between two different stops. Can also represent a transfer
    that is not in transfers.txt - either a transfer by node_id, or by parent_station.
    """

    _dataset: Dataset = field(repr=False)
    from_stop_id: str
    to_stop_id: str
    transfer_type: TransferType
    transfer_time: int

    def get_from_stop(self) -> Stop:
        """Get a Stop from which this transfer originates."""
        return self._dataset.get_stop_by_id(self.from_stop_id)

    def get_to_stop(self) -> Stop:
        """Get a Stop to which this transfer leads."""
        return self._dataset.get_stop_by_id(self.to_stop_id)
