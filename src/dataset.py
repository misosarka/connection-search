from datetime import date
from functools import cache
import pandas as pd
from typing import Any, Iterable
from .structures import LocationType, MalformedGTFSError, PickupDropoffType, Route, RouteType, Stop, StopTime, Trip


class Dataset:
    """
    An interface with the GTFS dataset.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """
        Construct a Dataset object from a folder with a GTFS dataset.

        :param dataset_path: Path to the dataset folder.
        """

        self.config = config

        match config["TRANSFER_MODE"]:
            case "by_node_id":
                self._stops = self._read_csv_file("stops", {
                    "stop_id": "string",
                    "stop_name": "string",
                    "location_type": "int",
                    "parent_station": "string",
                    config["TRANSFER_NODE_ID"]: "string",
                }, "stop_id")

                self._stops_by_transfer_node_id = self._reindex(self._stops, config["TRANSFER_NODE_ID"])

            case mode:
                self._stops = self._read_csv_file("stops", {
                    "stop_id": "string",
                    "stop_name": "string",
                    "location_type": "int",
                    "parent_station": "string",
                }, "stop_id")

                if mode == "by_parent_station":
                    self._stops_by_parent_station = self._reindex(self._stops, "parent_station")

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

        self.stop_times_length = self._stop_times_by_trip.shape[0]


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
        
        dataset_path = self.config["DATASET_PATH"]
        dataframe = pd.read_csv(
            f"{dataset_path}/{name}.txt",
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
        if isinstance(stop, pd.DataFrame):
            raise MalformedGTFSError("stops.stop_id is not unique")
        return Stop(
            _dataset=self,
            stop_id=stop_id,
            stop_name=_replace_na(stop["stop_name"]),
            location_type=LocationType(stop["location_type"]),
            parent_station=_replace_na(stop["parent_station"]),
            transfer_node_id=(
                None if self.config["TRANSFER_MODE"] != "by_node_id"
                else _replace_na(stop[self.config["TRANSFER_NODE_ID"]])
            ),
        )
    

    def get_stop_ids_by_parent_station(self, parent_station_id: str) -> Iterable[str]:
        """Get a list of stop_ids of stops in the dataset whose parent station matches the specified id."""
        # def to_stop(stop: pd.Series) -> Stop:
        #     return Stop(
        #         _dataset=self,
        #         stop_id=stop["stop_id"],
        #         stop_name=_replace_na(stop["stop_name"]),
        #         location_type=LocationType(stop["location_type"]),
        #         parent_station=parent_station_id,
        #     )
        
        if self.config["TRANSFER_MODE"] != "by_parent_station":
            raise RuntimeError("called get_stops_by_parent_station when the transfer mode is not 'by_parent_station'")
        stops = self._stops_by_parent_station.loc[parent_station_id, "stop_id"]
        #return stops.apply(to_stop, axis=1) # type: ignore[call-overload, arg-type]
        if isinstance(stops, pd.Series):
            return stops
        else:
            return [stops] # type: ignore[list-item]


    def get_stop_ids_by_transfer_node_id(self, transfer_node_id: str) -> Iterable[str]:
        """Get a list of stop_ids of stops in the dataset by their TRANSFER_NODE_ID as specified in the configuration."""
        if self.config["TRANSFER_MODE"] != "by_node_id":
            raise RuntimeError("called get_stop_ids_by_transfer_node_id when the transfer mode is not 'by_node_id'")
        stops = self._stops_by_transfer_node_id.loc[transfer_node_id, "stop_id"]
        if isinstance(stops, pd.Series):
            return stops
        else:
            return [stops] # type: ignore[list-item]


    def get_route_by_id(self, route_id: str) -> Route:
        """Get a Route object from the dataset by its route_id."""
        route = self._routes.loc[route_id]
        if isinstance(route, pd.DataFrame):
            raise MalformedGTFSError("routes.route_id is not unique")
        return Route(
            _dataset=self,
            route_id=route_id,
            route_short_name=_replace_na(route["route_short_name"]),
            route_long_name=_replace_na(route["route_long_name"]),
            route_type=RouteType(route["route_type"]),
        )
    
    
    def get_trip_by_id(self, trip_id: str) -> Trip:
        """Get a Trip object from the dataset by its trip_id."""
        trip = self._trips.loc[trip_id]
        if isinstance(trip, pd.DataFrame):
            raise MalformedGTFSError("trips.trip_id is not unique")
        return Trip(
            _dataset=self,
            trip_id=trip_id,
            route_id=trip["route_id"],
            service_id=trip["service_id"],
            trip_short_name=_replace_na(trip["trip_short_name"]),
        )


    def get_index_in_stop_times_by_trip(self, trip_id: str, stop_sequence: int) -> int:
        """
        Get an index where a stop time with the specified trip_id and stop_sequence is located.
        Subsequent indices, when put into get_stop_time_by_trip_on_index(), should return subsequent StopTimes for the trip
        (up until the final stop).
        """
        location = self._stop_times_by_trip.index.get_loc((trip_id, stop_sequence))
        if isinstance(location, int):
            return location
        raise MalformedGTFSError("(stop_times.trip_id, stop_times.stop_sequence) is not unique")
    

    def get_stop_times_slice_by_stop_id(self, stop_id: str) -> slice:
        """
        Get a slice of numeric indices where stop times for stop with the specified stop_id are located.
        These indices are to be put into get_stop_time_by_stop_on_index().
        """
        try:
            location = self._stop_times_by_stop.index.get_loc(stop_id)
        except KeyError:
            return slice(0, 0)
        if isinstance(location, int):
            location = slice(location, location + 1)
        if isinstance(location, slice):
            return location
        raise RuntimeError("Dataset._stop_times_by_stop_id: index not properly sorted")
    

    def get_stop_time_by_trip_on_index(self, index: int) -> StopTime:
        """Get a StopTime at a specified index in Dataset.stop_times_by_trip,
        such as the one received from get_index_in_stop_times_by_trip()."""
        stop_time = self._stop_times_by_trip.iloc[index]
        return StopTime(
            _dataset=self,
            trip_id=stop_time.name[0], # type: ignore[index]
            stop_sequence=stop_time.name[1], # type: ignore[index]
            arrival_time=stop_time["arrival_time"],
            departure_time=stop_time["departure_time"],
            stop_id=stop_time["stop_id"],
            pickup_type=PickupDropoffType(_replace_na(stop_time["pickup_type"], 0)),
            drop_off_type=PickupDropoffType(_replace_na(stop_time["drop_off_type"], 0)),
        )
    

    def get_stop_time_by_stop_on_index(self, index: int) -> StopTime:
        """Get a StopTime at a specified index in Dataset.stop_times_by_stop,
        such as an index in the slice received from get_stop_times_slice_by_stop_id()."""
        stop_time = self._stop_times_by_stop.iloc[index]
        return StopTime(
            _dataset=self,
            trip_id=stop_time["trip_id"],
            stop_sequence=stop_time["stop_sequence"],
            arrival_time=stop_time["arrival_time"],
            departure_time=stop_time.name[1], # type: ignore[index]
            stop_id=stop_time.name[0], # type: ignore[index]
            pickup_type=PickupDropoffType(_replace_na(stop_time["pickup_type"], 0)),
            drop_off_type=PickupDropoffType(_replace_na(stop_time["drop_off_type"], 0)),
        )


    @cache
    def runs_on_day(self, service_id: str, day: date) -> bool:
        """Returns True if the specified service_id runs on the specified date and False otherwise."""
        timestamp = pd.Timestamp(day)
        if (service_id, timestamp) in self._calendar_dates.index:
            calendar_dates_record = self._calendar_dates.loc[service_id, timestamp] # type: ignore[index]
            if calendar_dates_record["exception_type"] == 1:
                return True
            elif calendar_dates_record["exception_type"] == 2:
                return False
            else:
                raise MalformedGTFSError("calendar_dates.exception_type has invalid value")
        weekday = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][day.weekday()]
        calendar_record = self._calendar.loc[service_id]
        if isinstance(calendar_record, pd.DataFrame):
            raise MalformedGTFSError("calendar.service_id is not unique")
        return (
            day >= calendar_record["start_date"].date() and
            day <= calendar_record["end_date"].date() and
            calendar_record[weekday]
        )
    

    def get_all_stop_ids_and_names(self) -> Iterable[tuple[str, str]]:
        """For every stop, return a tuple (stop_id, stop_name)."""
        return ((stop_id, stop_name) for (stop_id, stop_name, location_type) in (
            (stop_id, _replace_na(stop_name), LocationType(location_type)) for (stop_id, stop_name, location_type) in zip(
                self._stops.index, self._stops["stop_name"], self._stops["location_type"]
            )
        ) if stop_name != None and location_type == LocationType.STOP_OR_PLATFORM)


def _replace_na(value: Any, replace_with: Any = None) -> Any:
    """Replace a Pandas <NA> value with a specified value (or None by default)."""
    if pd.isna(value):
        return replace_with
    else:
        return value
