from datetime import datetime
from src.dataset import Dataset
from src.search import SearchParams, search

dataset = Dataset("data")
params_nh_kuchynka = SearchParams("U115Z9P", "U305Z1P", datetime(2024, 11, 11, 9, 0))
params_nh_kuchynka_night = SearchParams("U115Z9P", "U305Z1P", datetime(2024, 11, 11, 0, 0))
params_nh_ms = SearchParams("U115Z1P", "U361Z1P", datetime(2024, 11, 11, 9, 7))
params_ms_pelc_saturday = SearchParams("U361Z2P", "U536Z3P", datetime(2024, 11, 16, 9, 0))

result = search(params_nh_kuchynka_night, dataset)

if result.connection is None:
    print("No connection found")
else:
    for segment in result.connection.segments:
        print(f"route: {segment.route.get_route_short_name()}")
        print(f"from stop: {segment.start_stop.stop_name} at {segment.start_stoptime.departure_time}")
        print(f"to stop: {segment.end_stop.stop_name} at {segment.end_stoptime.arrival_time}")
        print()
