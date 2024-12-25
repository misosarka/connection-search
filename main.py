from src.dataset import Dataset

dataset = Dataset("data")
for stop in dataset.get_stops_by_asw_node_id("305"):
    print(stop)

for stop in dataset.get_stops_by_parent_station("U115S1"):
    print(stop)
