from pydantic import BaseModel


class DashboardSummary(BaseModel):
    active_cases: int = 0
    urgent_cases: int = 0
    available_participants: int = 0
    unverified_participants: int = 0
    recent_reports: int = 0
    system_status: str = "ok"
    warnings: list[str] = []
