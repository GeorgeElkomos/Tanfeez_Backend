from pydantic import BaseModel

class NavigationResponse(BaseModel):
    response: str
    navigation_link: str = ""

class ManagerDecision(BaseModel):
    next_agent: str
    next_task_description: str
    stop: bool = False

class DatabaseResponse(BaseModel):
    response: str
    executed_query: str = ""
    execution_status: str = "success"
