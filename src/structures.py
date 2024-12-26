from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .dataset import Dataset


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
    asw_node_id: str | None


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
    _dataset: Dataset
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
    _dataset: Dataset
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
