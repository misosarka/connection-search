from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from .new_dataset import Dataset


class MalformedGTFSError(Exception):
    pass


class LocationType(Enum):
    STOP_OR_PLATFORM = 0
    STATION = 1
    ENTRANCE_OR_EXIT = 2
    GENERIC_NODE = 3
    BOARDING_AREA = 4


@dataclass
class Stop:
    _dataset: Dataset = field(repr=False)
    stop_id: str
    stop_name: str | None
    location_type: LocationType
    parent_station: str | None
    transfer_node_id: str | None

    def get_all_transfers(self) -> Iterable[Transfer]:
        return self._dataset.get_all_transfers_from(self)

    def get_departures(self) -> list[StopTime]:
        return self._dataset.get_stop_times_by_stop_id(self.stop_id)


class RouteType(Enum):
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

    def __str__(self) -> str:
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
    _dataset: Dataset = field(repr=False)
    route_id: str
    route_short_name: str | None
    route_long_name: str | None
    route_type: RouteType

    def get_route_short_name(self) -> str:
        if self.route_short_name is not None:
            return self.route_short_name 
        if self.route_long_name is not None:
            return self.route_long_name
        raise MalformedGTFSError("both routes.route_short_name and routes.route_long_name are empty")
    
    def get_route_full_name(self) -> str:
        route_type = str(self.route_type).capitalize()
        if self.route_short_name is None:
            return f"{route_type} ({self.route_long_name})"
        elif self.route_long_name is None:
            return f"{route_type} {self.route_short_name}"
        else:
            return f"{route_type} {self.route_short_name} ({self.route_long_name})"


@dataclass
class Trip:
    _dataset: Dataset = field(repr=False)
    trip_id: str
    route_id: str
    service_id: str
    trip_short_name: str | None

    def get_trip_name(self) -> str:
        route_short_name = self._dataset.get_route_by_id(self.route_id).get_route_short_name()
        if self.trip_short_name is not None:
            return f"{self.trip_short_name} ({route_short_name})"
        else:
            return route_short_name

    def get_route(self) -> Route:
        return self._dataset.get_route_by_id(self.route_id)

    def get_stop_times(self) -> list[StopTime]:
        return self._dataset.get_stop_times_by_trip_id(self.trip_id)

    def runs_on_day(self, service_day: date) -> bool:
        return self._dataset.runs_on_day(self.service_id, service_day)


class PickupDropoffType(Enum):
    REGULAR = 0
    NOT_AVAILABLE = 1
    PHONE_AGENCY = 2
    COORDINATE_WITH_DRIVER = 3


@dataclass
class StopTime:
    _dataset: Dataset = field(repr=False)
    trip_id: str
    stop_sequence: int
    arrival_time: timedelta
    departure_time: timedelta
    stop_id: str
    pickup_type: PickupDropoffType
    drop_off_type: PickupDropoffType

    def get_stop(self) -> Stop:
        return self._dataset.get_stop_by_id(self.stop_id)
    
    def get_trip(self) -> Trip:
        return self._dataset.get_trip_by_id(self.trip_id)


@dataclass
class CalendarRecord:
    _dataset: Dataset = field(repr=False)
    service_id: str
    weekday_services: dict[int, bool]
    start_date: date
    end_date: date


@dataclass
class CalendarDatesRecord:
    _dataset: Dataset = field(repr=False)
    service_id: str
    date: date
    service_available: bool


class TransferType(Enum):
    BY_TRANSFERS_UNTIMED = 0
    BY_TRANSFERS_GUARANTEED = 1
    BY_TRANSFERS_TIMED = 2
    BY_TRANSFERS_PROHIBITED = 3
    BY_TRANSFERS_INSEAT = 4
    BY_TRANSFERS_REBOARD = 5
    BY_NODE_ID = -1
    BY_PARENT_STATION = -2


@dataclass
class Transfer:
    _dataset: Dataset = field(repr=False)
    from_stop_id: str
    to_stop_id: str
    transfer_type: TransferType
    transfer_time: int

    def get_from_stop(self) -> Stop:
        return self._dataset.get_stop_by_id(self.from_stop_id)
    
    def get_to_stop(self) -> Stop:
        return self._dataset.get_stop_by_id(self.to_stop_id)
