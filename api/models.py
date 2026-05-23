from pydantic import BaseModel, HttpUrl
from typing import Optional

class TestSetupRequest(BaseModel):
    url: HttpUrl
    goal: str
    max_steps: int = 10
    mode: str = "dynamic" # dynamic или visual_only
    baseline_image_path: Optional[str] = None

class TaskResponse(BaseModel):
    task_id: str
    status: str