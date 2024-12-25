import pandas as pd
from typing import Any, Iterable
from .structures import LocationType, Stop


class Dataset:
    """
    An interface with the GTFS dataset.
    """

    def __init__(self, dataset_path: str) -> None:
        """
        Construct a Dataset object from a folder with a GTFS dataset.

        :param dataset_path: Path to the dataset folder.
        """

        self._dataset_path = dataset_path

        self._stops = self._read_csv_file("stops", {
            "stop_id": "string",
            "stop_name": "string",
            "location_type": "int",
            "parent_station": "string",
            "asw_node_id": "string",
        }, "stop_id")

        self._stops_by_parent_station = self._reindex(self._stops, "parent_station")
        self._stops_by_asw_node_id = self._reindex(self._stops, "asw_node_id")

        self._routes = self._read_csv_file("routes", {
            "route_id": "string",
            "route_short_name": "string",
            "route_long_name": "string",
            "route_type": "int",
        }, "route_id")

        self._trips = self._read_csv_file("trips", {
            "trip_id": "string",
            "route_id": "string",
            "service_id": "string",
            "trip_short_name": "string",
        }, "trip_id")

        self._stop_times_by_trip = self._read_csv_file("stop_times", {
            "trip_id": "string",
            "stop_sequence": "int",
            "arrival_time": "timedelta",
            "departure_time": "timedelta",
            "stop_id": "string",
            "pickup_type": "int",
            "drop_off_type": "int",
        }, ["trip_id", "stop_sequence"])

        self._stop_times_by_stop = self._reindex(self._stop_times_by_trip, ["stop_id", "departure_time"])

        self._calendar = self._read_csv_file("calendar", {
            "service_id": "string",
            "monday": "bool",
            "tuesday": "bool",
            "wednesday": "bool",
            "thursday": "bool",
            "friday": "bool",
            "saturday": "bool",
            "sunday": "bool",
            "start_date": "datetime",
            "end_date": "datetime",
        }, "service_id")

        self._calendar_dates = self._read_csv_file("calendar_dates", {
            "service_id": "string",
            "date": "datetime",
            "exception_type": "int",
        }, ["service_id", "date"])


    def _read_csv_file(self, name: str, column_types: dict[str, str], index: None | str | list[str] = None) -> pd.DataFrame:
        """
        Read a CSV file into a Pandas DataFrame.

        :param name: The name of the file to read, without the .txt extension.
        :param column_types: The columns to read, along with their datatypes. \
            Valid datatypes are 'int', 'string', 'bool', 'datetime' and 'timedelta'.
        :param index: The column (or tuple of columns) to use as the DataFrame index.
        :returns: A DataFrame with the data from the CSV file.
        """

        convert_to_timedelta = []
        convert_to_datetime = []
        for column in column_types:
            if column_types[column] == "timedelta":
                convert_to_timedelta.append(column)
                column_types[column] = "string"
            elif column_types[column] == "datetime":
                convert_to_datetime.append(column)
                column_types[column] = "string"
        
        dataframe = pd.read_csv(
            f"{self._dataset_path}/{name}.txt",
            usecols=list(column_types.keys()),
            dtype=column_types
        )

        for column in convert_to_timedelta:
            dataframe[column] = pd.to_timedelta(dataframe[column])
        for column in convert_to_datetime:
            dataframe[column] = pd.to_datetime(dataframe[column])
        if index is not None:
            dataframe = dataframe.set_index(index).sort_index(inplace=False)
        
        return dataframe
    

    def _reindex(self, frame: pd.DataFrame, new_index: str | list[str]) -> pd.DataFrame:
        """
        Create a new DataFrame from an existing one, using a different column as index.

        :param frame: The original DataFrame.
        :param new_index: The column name to use as the new index, or a list of those column names.
        :returns: A DataFrame with the new index.
        """
        return frame.reset_index().set_index(new_index).sort_index(inplace=False)


    def get_stop_by_id(self, stop_id: str) -> Stop:
        """Get a Stop object from the dataset by its stop_id."""
        stop = self._stops.loc[stop_id]
        return Stop(
            _dataset=self,
            stop_id=stop_id,
            stop_name=_replace_na(stop["stop_name"]),
            location_type=LocationType(stop["location_type"]),
            parent_station=_replace_na(stop["parent_station"]),
            asw_node_id=_replace_na(stop["asw_node_id"]),
        )
    

    def get_stops_by_parent_station(self, parent_station_id: str) -> Iterable[Stop]:
        """Get a list of Stop objects from the dataset whose parent station matches the specified id."""
        def to_stop(stop: pd.Series) -> Stop:
            return Stop(
                _dataset=self,
                stop_id=stop["stop_id"],
                stop_name=_replace_na(stop["stop_name"]),
                location_type=LocationType(stop["location_type"]),
                parent_station=parent_station_id,
                asw_node_id=_replace_na(stop["asw_node_id"]),
            )
        
        stops = self._stops_by_parent_station.loc[parent_station_id]
        return stops.apply(to_stop, axis=1) # type: ignore[call-overload, arg-type]


    def get_stops_by_asw_node_id(self, asw_node_id: str) -> Iterable[Stop]:
        """Get a list of Stop objects from the dataset by their asw_node_id."""
        def to_stop(stop: pd.Series) -> Stop:
            return Stop(
                _dataset=self,
                stop_id=stop["stop_id"],
                stop_name=_replace_na(stop["stop_name"]),
                location_type=LocationType(stop["location_type"]),
                parent_station=_replace_na(stop["parent_station"]),
                asw_node_id=asw_node_id,
            )
        
        stops = self._stops_by_asw_node_id.loc[asw_node_id]
        return stops.apply(to_stop, axis=1) # type: ignore[call-overload, arg-type]


def _replace_na(value: pd.Series | pd.DataFrame, replace_with: Any = None) -> Any:
    """Replace a Pandas <NA> value with a specified value (or None by default)."""
    if pd.isna(value):
        return replace_with
    else:
        return value
