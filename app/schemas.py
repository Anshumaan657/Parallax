import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import WorkspaceRole


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
