from enum import Enum
import uuid
from datetime import datetime
import os
from threading import Thread, Lock
from logger import init_logger
logger = init_logger(__name__)

class TaskStatus(Enum):
    NEW = 0
    INITIALIZED = 1
    RUNNING = 2
    DONE = 3
    TIMED_OUT = 4
    ERROR = -1

    def __str__(self):
        return str(self.value)

# If the task has been idle for more than 5 minutes
# time out
#TaskTimedOut = 300

class Task:
    def __init__(self, title):
        self._lock = Lock()
        self.title = title
        self.status = TaskStatus.NEW
        self.id = str(uuid.uuid4())
        self.data_dir = ""
        #self.last_history_idx = -1
        #self.last_modified = datetime.now()
        #self.history_file = None
        self.patch_file = None
        self.histories = []


    def get_id(self):
        with self._lock:
            return self.id

    def set_status(self, status):
        with self._lock:
            self.status = status

    def get_status(self):
        with self._lock:
            return self.status
    
    def set_data_dir(self, dir):
        with self._lock:
            self.data_dir = dir

    # Only support single file, only set once
    def get_history_file(self):
        if self.history_file is not None:
            return self.history_file

        with self._lock:
            files = [f for f in os.listdir(self.data_dir) if f.endswith("traj")]
            if len(files) > 0:
                self.history_file = self.data_dir + "/" + files[0]
        return self.history_file

    # Only support single file, only set once
    def get_patch_file(self):
        if self.patch_file is not None:
            return self.patch_file

        with self._lock:
            for root, dir_names, file_names in os.walk(self.data_dir):
                for f in file_names:
                    if f.endswith(".patch"):
                        self.patch_file = os.path.join(root, f)
                        return self.patch_file
        return None

    #def get_last_history_idx(self):
    #    with self._lock:
    #        return self.last_history_idx
    #
    #def set_last_history_idx(self, index):
    #    with self._lock:
    #        self.last_history_idx = index
    #        self.last_modified = datetime.now()

    #def get_last_modified(self):
    #    with self._lock:
    #        return self.last_modified

    #def timed_out(self):
    #    with self._lock:
    #        delta = datetime.now() - self.last_modified

    #        if delta.total_seconds() >= TaskTimedOut:
    #            self.status = TaskStatus.TIMED_OUT
    #            return True
    #        return False

    #def timed_out2(self, t1, t2):
    #    delta = t2 - t2
    #    if delta.total_seconds() >= TaskTimedOut:
    #        self.status = TaskStatus.TIMED_OUT
    #        return True
    #    return False

    # entry must be a valid json object
    def append_history(self, entry):
        with self._lock:
            logger.info(f'APPEND history: {entry}')
            self.histories.append(entry)

    def get_history_len(self):
        return len(self.histories)

    def get_history(self, index):
        return self.histories[index]

    def clear_history(self):
        self.histories.clear()

