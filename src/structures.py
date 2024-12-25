from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .dataset import Dataset


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
