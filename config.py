CONFIG = {
    # Path to the dataset folder, relative to this file, with no leading or trailing slashes.
    "DATASET_PATH": "data-example",

    # The maximum time the algorithm will search through before giving up, in hours. Values over 24 are not guaranteed
    # to work correctly.
    "MAX_SEARCH_TIME_HOURS": 24,

    # Determines how transfers between different stops in the same station/area are realized. Available options:
    "TRANSFER_MODE": "by_node_id", # A transfer can be realized between two stops that have the same value of a field
                                     # specified by TRANSFER_NODE_ID, and the minimum time needed for the transfer is
                                     # specified in MIN_TRANSFER_TIME_SECONDS.
    # "TRANSFER_MODE": "by_parent_station", # A transfer can be realized between two stops that have the same parent station,
                                            # and the minimum time needed for the transfer is specified
                                            # in MIN_TRANSFER_TIME_SECONDS.
    # "TRANSFER_MODE": "by_transfers_txt", # A transfer can be realized between two stops that have a record in transfers.txt.
                                           # Currently, only transfers with the lowest specificity (just from_stop_id and
                                           # to_stop_id) are supported. The minimum transfer time is then the value of the field
                                           # transfers.min_transfer_time or the constant MIN_TRANSFER_TIME_SECONDS, whichever is
                                           # higher.
    # "TRANSFER_MODE": "none", # No transfers between stops are possible.

    # The field name to use for transfers if TRANSFER_MODE is "by_node_id". For more information, see TRANSFER_MODE.
    "TRANSFER_NODE_ID": "asw_node_id",
    # "TRANSFER_NODE_ID": "stop_code",
    # "TRANSFER_NODE_ID": None,

    # The minimum time, in seconds, needed for a transfer between two stops in the same station/area.
    # For more information, see TRANSFER_MODE.
    "MIN_TRANSFER_TIME_SECONDS": 180,

    # If true, the main search function is profiled and the profiling results are saved into profile.prof.
    "PROFILE": False,
}
