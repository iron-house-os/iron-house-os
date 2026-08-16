from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from app.schemas.employee_onboarding import (
    EmployeeOnboardingCreate,
    EmploymentCategory,
    EmploymentPosition,
    REQUIRED_ORIENTATION_TOPIC_CODES,
    WorkerOrientationCreate,
)


def orientation_topics() -> list[dict[str, str]]:
    return [
        {"code": code, "applicability": "applicable", "evidence": f"Reviewed {code}."}
        for code in REQUIRED_ORIENTATION_TOPIC_CODES
    ]


def test_field_position_must_match_category() -> None:
    payload = EmployeeOnboardingCreate(
        legal_first_name="Test",
        legal_last_name="Employee",
        personal_email="employee@example.com",
        category=EmploymentCategory.FIELD_STAFF,
        position=EmploymentPosition.GREEN_LABOURER,
        employment_type="full_time",
        start_date=date(2026, 8, 10),
    )
    assert payload.position == EmploymentPosition.GREEN_LABOURER


def test_office_position_is_controlled() -> None:
    payload = EmployeeOnboardingCreate(
        legal_first_name="Office",
        legal_last_name="Employee",
        personal_email="office@example.com",
        category=EmploymentCategory.OFFICE_STAFF,
        position=EmploymentPosition.PROJECT_MANAGER,
        employment_type="salary",
        start_date=date(2026, 8, 10),
    )
    assert payload.position == EmploymentPosition.PROJECT_MANAGER


def test_orientation_requires_every_regulatory_topic_once() -> None:
    payload = WorkerOrientationCreate(
        scope="company",
        trigger="new_hire",
        orientation_date=date(2026, 8, 16),
        instructor_name="Safety Lead",
        supervisor_name="Supervisor",
        document_version="IHOS-OHS-1",
        topics=orientation_topics(),
        competency_result="passed",
        ppe_verified=True,
        qualifications_verified=True,
        worker_acknowledged=True,
        worker_acknowledged_at=datetime(2026, 8, 16, 18, tzinfo=UTC),
    )
    assert len(payload.topics) == 13


def test_orientation_rejects_missing_topic() -> None:
    with pytest.raises(ValidationError, match="exactly once"):
        WorkerOrientationCreate(
            scope="company",
            trigger="new_hire",
            orientation_date=date(2026, 8, 16),
            instructor_name="Safety Lead",
            supervisor_name="Supervisor",
            document_version="IHOS-OHS-1",
            topics=orientation_topics()[:-1],
            competency_result="passed",
            ppe_verified=True,
            qualifications_verified=True,
            worker_acknowledged=True,
            worker_acknowledged_at=datetime(2026, 8, 16, 18, tzinfo=UTC),
        )


def test_not_applicable_topic_requires_a_recorded_basis() -> None:
    topics = orientation_topics()
    topics[0] = {"code": topics[0]["code"], "applicability": "not_applicable"}
    with pytest.raises(ValidationError, match="basis is required"):
        WorkerOrientationCreate(
            scope="company",
            trigger="new_hire",
            orientation_date=date(2026, 8, 16),
            instructor_name="Safety Lead",
            supervisor_name="Supervisor",
            document_version="IHOS-OHS-1",
            topics=topics,
            competency_result="passed",
            ppe_verified=True,
            qualifications_verified=True,
            worker_acknowledged=True,
            worker_acknowledged_at=datetime(2026, 8, 16, 18, tzinfo=UTC),
        )
