from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TYPE_CHECKING
import pandas as pd

if TYPE_CHECKING:
    from .dataset import Dataset


def _replace_na(value: pd.Series | pd.DataFrame, replace_with: Any = None) -> Any:
    if pd.isna(value):
        return replace_with
    else:
        return value


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

    def __init__(self, dataset: Dataset, stop_id: str) -> None:
        self._dataset = dataset
        self.stop_id = stop_id
        stop = self._dataset.get_stop(self.stop_id)
        self.stop_name = _replace_na(stop["stop_name"])
        self.location_type = LocationType(stop["location_type"])
        self.parent_station = _replace_na(stop["parent_station"])
