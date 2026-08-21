from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectFolderRequest(BaseModel):
    project_name: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    project_code: str = Field(min_length=1)
    close_date: date
    consultant: str | None = None
    estimator: str | None = None


class ProjectFolderEntry(BaseModel):
    path: str
    kind: str = Field(pattern="^(folder|file)$")
    description: str


class ProjectFolderManifest(BaseModel):
    root_folder: str
    entries: list[ProjectFolderEntry]
    project_index: str


class AwardedProjectWorkspace(ProjectFolderManifest):
    project_id: UUID
    job_number: str
    provisioned_at: datetime
