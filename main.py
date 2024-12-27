import datetime
from src.dataset import Dataset

dataset = Dataset("data")

print(dataset.runs_on_day("1111111-1", datetime.date(2024, 11, 11)))
