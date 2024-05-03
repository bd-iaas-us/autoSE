from enum import Enum
import uuid
from datetime import datetime
import os

class TaskStatus(Enum):
    NEW = 0
    INITIALIZED = 1
    RUNNING = 2
    DONE = 2
    ERROR = -1

    def __str__(self):
        return str(self.value)

class Task:
    def __init__(self, title):
        self.title = title
        self.status = TaskStatus.NEW
        self.id = str(uuid.uuid4())
        self.data_dir = ""
        self.last_history_idx = 0

    def set_status(self, status):
        self.status = status

    def get_status(self):
        return self.status
    
    def set_data_dir(self, dir):
        self.data_dir = dir

    # TODO: Hard coded file for testing
    def get_history_file(self):
        files = [f for f in os.listdir(self.data_dir) if f.endswith("traj")]
        return self.data_dir + "/" + files[0] if len(files) > 0 else None

    def get_last_history_idx(self):
        return self.last_history_idx
    
    def set_last_history_idx(self, index):
        self.last_history_idx = index
        self.last_modified = datetime.now()

    def get_last_modified(self):
        return self.last_modified