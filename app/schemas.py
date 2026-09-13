import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import MissionStatus, WorkspaceRole


class ErrorResponse(BaseModel):
    detail: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    workspace_name: str = Field(min_length=2, max_length=120)
    workspace_slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    workspace_id: uuid.UUID | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    workspace_id: uuid.UUID


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    display_name: str
    is_active: bool
    created_at: datetime


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    role: WorkspaceRole


class MeResponse(BaseModel):
    user: UserRead
    current_workspace: WorkspaceRead
    workspaces: list[WorkspaceRead]


class WorkspaceSummary(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    role: WorkspaceRole


class MemberRead(BaseModel):
    user_id: uuid.UUID
    email: EmailStr
    display_name: str
    role: WorkspaceRole


class MemberRoleUpdate(BaseModel):
    role: WorkspaceRole


class MissionCreate(BaseModel):
    prompt: str = Field(min_length=3, max_length=10_000)
    project: str = Field(default="General", min_length=1, max_length=120)

    @field_validator("prompt", "project")
    @classmethod
    def strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Value must not be blank")
        return stripped


class MissionStepRead(BaseModel):
    id: uuid.UUID
    sequence: int
    name: str
    status: str
    detail: str
    created_at: datetime


class MissionRead(BaseModel):
    id: uuid.UUID
    prompt: str
    project: str
    status: MissionStatus
    progress_current: int
    progress_total: int
    result_summary: str | None
    steps: list[MissionStepRead]
    created_at: datetime
    updated_at: datetime


class ActivityRead(BaseModel):
    id: uuid.UUID
    mission_id: uuid.UUID | None
    icon: str
    title: str
    detail: str
    created_at: datetime


class ProjectRead(BaseModel):
    id: uuid.UUID
    name: str
    icon: str
    health_pct: int


class IntegrationStatusRead(BaseModel):
    name: Literal["GitHub", "Jira", "Notion", "Slack"]
    connected: bool
    detail: str


class IntegrationCapabilityRead(BaseModel):
    operation: str
    access: Literal["read", "write"]
    description: str


class IntegrationCapabilitiesRead(BaseModel):
    name: Literal["GitHub", "Jira", "Notion", "Slack"]
    mode: Literal["mock", "real"]
    capabilities: list[IntegrationCapabilityRead]


class DashboardStatsRead(BaseModel):
    active_tasks: int
    completed_this_week: int
    blocked: int
    awaiting_approval: int
    project_health_pct: int
