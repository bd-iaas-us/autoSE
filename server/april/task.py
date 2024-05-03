from enum import Enum
import uuid

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

    def set_status(self, status):
        self.status = status

    def get_status(self):
        return self.status
