from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.project import (
    ProjectCreate,
    ProjectDashboard,
    ProjectList,
    ProjectRead,
    ProjectUpdate,
)
from app.services import projects

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]
OptionalStatusQuery = Annotated[str | None, Query()]


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: DBSession) -> ProjectRead:
    return projects.create_project(db, payload)


@router.get("", response_model=ProjectList)
def list_projects(db: DBSession, status: OptionalStatusQuery = None) -> ProjectList:
    return projects.list_projects(db, status=status)


@router.get("/{project_id}", response_model=ProjectRead)
def read_project(project_id: UUID, db: DBSession) -> ProjectRead:
    return projects.get_project(db, project_id)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(project_id: UUID, payload: ProjectUpdate, db: DBSession) -> ProjectRead:
    return projects.update_project(db, project_id, payload)


@router.post("/{project_id}/archive", response_model=ProjectRead)
def archive_project(project_id: UUID, db: DBSession) -> ProjectRead:
    return projects.archive_project(db, project_id)


@router.get("/{project_id}/dashboard", response_model=ProjectDashboard)
def read_project_dashboard(project_id: UUID, db: DBSession) -> ProjectDashboard:
    return projects.get_project_dashboard(db, project_id)
