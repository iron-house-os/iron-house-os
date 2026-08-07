import pytest
from pydantic import ValidationError

from app.schemas.employee_onboarding import (
    EmployeeOnboardingCreate,
    EmploymentCategory,
    EmploymentPosition,
    POSITION_OPTIONS,
)


def payload(**overrides):
    values = {
        "legal_first_name": "Alex",
        "legal_last_name": "Worker",
        "personal_email": "alex@example.com",
        "category": EmploymentCategory.FIELD_STAFF,
        "position": EmploymentPosition.GREEN_LABOURER,
        "employment_type": "full_time",
        "start_date": "2026-08-10",
    }
    values.update(overrides)
    return values


def test_all_approved_positions_are_exposed_once():
    assert len(POSITION_OPTIONS) == 13
    assert len({item.value for item in POSITION_OPTIONS}) == 13


def test_field_position_accepts_field_category():
    model = EmployeeOnboardingCreate.model_validate(payload())
    assert model.position == EmploymentPosition.GREEN_LABOURER


def test_office_position_rejects_field_category():
    with pytest.raises(ValidationError):
        EmployeeOnboardingCreate.model_validate(payload(position=EmploymentPosition.CEO))


def test_office_position_accepts_office_category():
    model = EmployeeOnboardingCreate.model_validate(
        payload(category=EmploymentCategory.OFFICE_STAFF, position=EmploymentPosition.PROJECT_MANAGER)
    )
    assert model.position == EmploymentPosition.PROJECT_MANAGER
