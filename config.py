CONFIG = {
    # Path to the dataset folder, relative to this file, with no leading or trailing slashes.
    "DATASET_PATH": "data",

    # The maximum time the algorithm will search through before giving up, in hours.
    "MAX_SEARCH_TIME_HOURS": 24,

    # Determines how transfers between different stops in the same station/area are realized. Available options:
    # - "by_asw_node_id": A transfer can be realized between two stops that have the same stops.asw_node_id field, and the minimum time
    # needed for the transfer is specified in MIN_TRANSFER_TIME. Should be used for PID (Prague) data.
    # - "by_parent_station": A transfer can be realized between two stops that have the same parent station, and the minimum time
    # needed for the transfer is specified in MIN_TRANSFER_TIME.
    # - "by_transfers_txt": A transfer can be realized between two stops that have a record in transfers.txt. Currently, only transfers
    # with the lowest specificity (just from_stop_id and to_stop_id) are supported. The minimum time is then the value of the field
    # transfers.min_transfer_time or the constant MIN_TRANSFER_TIME, whichever is higher.
    # - "none": No transfers between stops are possible.
    "TRANSFER_MODE": "none",

    # The minimum time needed for a transfer between two stops in the same station/area. For more information, see TRANSFER_MODE.
    "MIN_TRANSFER_TIME": 3,

    # If true, the main search function is profiled and the profiling results are saved into profile.prof.
    "PROFILE": False,
}
