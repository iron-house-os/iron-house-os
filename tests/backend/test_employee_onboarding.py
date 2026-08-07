from datetime import date

from app.schemas.employee_onboarding import (
    EmployeeOnboardingCreate,
    EmploymentCategory,
    EmploymentPosition,
)


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
