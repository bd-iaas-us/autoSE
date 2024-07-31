import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List

from pydantic import BaseModel


class TrajStatus(BaseModel):
    api_calls: int
    tokens_sent: int
    tokens_received: int
    total_cost: float
    instance_cost: float


class TrajPoint(TrajStatus):
    time: datetime
    exit_status: str


@dataclass
class LintPoint:
    time: datetime
    dur: float


def find_traj_files(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.traj'):
                full_path = os.path.join(root, file)
                ctime = os.path.getctime(full_path)
                creation_datetime = datetime.fromtimestamp(ctime)
                with open(full_path) as f:
                    file_content = f.read()
                yield (creation_datetime, file_content)


def parse_swe_traj(directory) -> List[TrajPoint]:
    ret = []
    for ctime, file_content in find_traj_files(directory):
        data = json.loads(file_content)
        try:
            exit_status = data["info"]["exit_status"]
        except Exception as _:
            exit_status = "unknown"
        tp = TrajPoint(time=ctime,
                       **data["info"]["model_stats"],
                       exit_status=exit_status)
        ret.append(tp)
    return ret


def parse_log_line(line: str) -> LintPoint:
    """
    parse format: 
    """
    parts = line.split()
    # 日期和时间部分 "2024-06-05 17:49:28"
    datetime_part = parts[1] + " " + parts[2]

    for part in parts:
        if part.startswith("dur:"):
            duration_str = part.split(':')[1]
            break
    from logger import DATE_FORMAT

    time_obj = datetime.strptime(datetime_part, DATE_FORMAT)
    return LintPoint(time=time_obj, dur=float(duration_str))


def parse_lint(log_path: str) -> List[LintPoint]:
    ret = []
    with open(log_path, 'r') as f:
        for line in f:
            if "lint code len" in line:
                lint_point = parse_log_line(line)
                ret.append(lint_point)
    return ret


if __name__ == "__main__":
    print(parse_swe_traj("."))
    print(parse_lint("lint.log"))
