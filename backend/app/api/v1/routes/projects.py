from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import CurrentUser
from app.db.session import get_db
from app.schemas.project import (
    ProjectCreate,
    ProjectDashboard,
    ProjectList,
    ProjectRead,
    ProjectUpdate,
)
from app.schemas.project_folder import AwardedProjectWorkspace, ProjectFolderManifest, ProjectFolderRequest
from app.schemas.project_launch import ProjectLaunchDashboard
from app.schemas.project_readiness import ProjectReadinessResponse
from app.schemas.project_start import ProjectStartChecklistRead, ProjectStartChecklistUpdate
from app.services import project_folders, project_launch, project_readiness, projects

router = APIRouter()
DBSession = Annotated[Session, Depends(get_db)]
OptionalStatusQuery = Annotated[str | None, Query()]


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: DBSession) -> ProjectRead:
    return projects.create_project(db, payload)


@router.get("", response_model=ProjectList)
def list_projects(db: DBSession, status: OptionalStatusQuery = None) -> ProjectList:
    return projects.list_projects(db, status=status)


@router.post("/folder-manifest", response_model=ProjectFolderManifest)
def build_folder_manifest(payload: ProjectFolderRequest) -> ProjectFolderManifest:
    return project_folders.build_project_folder_manifest(payload)


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


@router.get("/{project_id}/readiness", response_model=ProjectReadinessResponse)
def read_project_readiness(project_id: UUID, db: DBSession) -> ProjectReadinessResponse:
    return project_readiness.get_project_readiness(db, project_id)


@router.get("/{project_id}/workspace", response_model=AwardedProjectWorkspace)
def read_awarded_project_workspace(project_id: UUID, db: DBSession) -> AwardedProjectWorkspace:
    return projects.get_awarded_workspace(db, project_id)


@router.get("/{project_id}/start-checklist", response_model=ProjectStartChecklistRead)
def read_project_start_checklist(project_id: UUID, db: DBSession) -> ProjectStartChecklistRead:
    return projects.get_project_start_checklist(db, project_id)


@router.get("/{project_id}/launch-dashboard", response_model=ProjectLaunchDashboard)
def read_project_launch_dashboard(
    project_id: UUID,
    user: CurrentUser,
    db: DBSession,
) -> ProjectLaunchDashboard:
    if user.role not in {"admin", "operations_manager", "estimator"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Management or estimating access is required for the job launch dashboard.",
        )
    return project_launch.get_project_launch_dashboard(db, project_id)


@router.patch("/{project_id}/start-checklist/{code}", response_model=ProjectStartChecklistRead)
def update_project_start_checklist_item(
    project_id: UUID,
    code: str,
    payload: ProjectStartChecklistUpdate,
    user: CurrentUser,
    db: DBSession,
) -> ProjectStartChecklistRead:
    return projects.update_project_start_checklist_item(
        db,
        project_id,
        code,
        payload.completed,
        user.email,
    )
