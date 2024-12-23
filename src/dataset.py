import pandas as pd


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
        }, "stop_id")

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

        self._stop_times_by_stop = self._stop_times_by_trip.reset_index().set_index(["stop_id", "departure_time"])

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
        Reads a CSV file into a Pandas DataFrame.

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
            dataframe = dataframe.set_index(index)
        
        return dataframe
