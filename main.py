from src.dataset import Dataset
from src.ui import Ui
from config import CONFIG

if __name__ == "__main__":
    dataset = Dataset(CONFIG)
    ui = Ui(dataset)
    ui.run()    
