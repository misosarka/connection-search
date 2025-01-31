from src.new_dataset import Dataset
from src.ui import Ui
from config import CONFIG

dataset = Dataset(CONFIG)
ui = Ui(dataset)
ui.run()
