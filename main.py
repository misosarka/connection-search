from src.dataset import Dataset

dataset = Dataset("data")

"""trip = dataset.get_trip_by_id("201_5955_240701")
print(trip.get_trip_name())
route = dataset.get_route_by_id(trip.route_id)
print(route.get_route_short_name())
print(route.get_route_full_name())"""

"""sl = dataset._stop_times_by_stop.index.get_loc("U115Z9P")
print(dataset._stop_times_by_stop.iloc[sl])"""

"""print(dataset.get_stop_times_slice_by_trip_id("201_5955_240701"))"""

sl = dataset.get_stop_times_slice_by_stop_id("U115Z9P")
for i in range(sl.start, sl.stop):
    print(dataset.get_stop_time_by_stop_on_index(i))
