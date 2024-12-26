from src.dataset import Dataset

dataset = Dataset("data")
trip = dataset.get_trip_by_id("201_5955_240701")
print(trip.get_trip_name())
route = dataset.get_route_by_id(trip.route_id)
print(route.get_route_short_name())
print(route.get_route_full_name())
