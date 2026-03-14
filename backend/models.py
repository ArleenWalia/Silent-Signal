from pydantic import BaseModel
from typing import List

class Signal(BaseModel):
    year: int
    barriers: List[str]
    workload: int
    visibility: str