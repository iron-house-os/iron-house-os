import pytest
from pydantic import ValidationError

from app.schemas.employee_onboarding import (
    EmployeeOnboardingCreate,
    EmploymentCategory,
    EmploymentPosition,
    POSITION_OPTIONS,
    PortalPayroll,
    PortalTaxForms,
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
    assert len(POSITION_OPTIONS) == 16
    assert len({item.value for item in POSITION_OPTIONS}) == 16


def test_field_position_accepts_field_category():
    model = EmployeeOnboardingCreate.model_validate(payload())
    assert model.position == EmploymentPosition.GREEN_LABOURER


def test_equipment_operator_is_a_controlled_field_position():
    model = EmployeeOnboardingCreate.model_validate(
        payload(position=EmploymentPosition.EQUIPMENT_OPERATOR)
    )
    assert model.position == EmploymentPosition.EQUIPMENT_OPERATOR


def test_office_position_rejects_field_category():
    with pytest.raises(ValidationError):
        EmployeeOnboardingCreate.model_validate(payload(position=EmploymentPosition.CEO))


def test_office_position_accepts_office_category():
    model = EmployeeOnboardingCreate.model_validate(
        payload(category=EmploymentCategory.OFFICE_STAFF, position=EmploymentPosition.PRESIDENT)
    )
    assert model.position == EmploymentPosition.PRESIDENT


def test_cfo_is_a_controlled_office_position():
    model = EmployeeOnboardingCreate.model_validate(
        payload(category=EmploymentCategory.OFFICE_STAFF, position=EmploymentPosition.CFO)
    )
    assert model.position == EmploymentPosition.CFO


def test_direct_deposit_requires_complete_authorised_bank_details():
    with pytest.raises(ValidationError, match="direct-deposit"):
        PortalPayroll.model_validate(
            {
                "payment_method": "direct_deposit",
                "account_holder_name": "Alex Worker",
                "institution_number": "001",
                "transit_number": "12345",
                "account_number": "1234567",
                "direct_deposit_authorized": False,
            }
        )


def test_tax_forms_reject_invalid_sin_and_require_both_certifications():
    with pytest.raises(ValidationError, match="Social Insurance Number"):
        PortalTaxForms.model_validate(
            {
                "social_insurance_number": "123456789",
                "federal_claim_amounts": ["0"] * 12,
                "bc_claim_amounts": ["0"] * 10,
                "federal_certified": True,
                "bc_certified": True,
            }
        )


def test_tax_forms_accept_valid_2026_td1_packet():
    packet = PortalTaxForms.model_validate(
        {
            "social_insurance_number": "046454286",
            "federal_claim_amounts": ["16452", *(["0"] * 11)],
            "bc_claim_amounts": ["13216", *(["0"] * 9)],
            "federal_certified": True,
            "bc_certified": True,
        }
    )
    assert packet.form_year == 2026


def test_non_resident_tax_forms_require_the_world_income_answer():
    with pytest.raises(ValidationError, match="world-income question"):
        PortalTaxForms.model_validate(
            {
                "social_insurance_number": "046454286",
                "country_of_permanent_residence": "United States",
                "federal_claim_amounts": ["0"] * 12,
                "bc_claim_amounts": ["0"] * 10,
                "federal_certified": True,
                "bc_certified": True,
            }
        )


def test_non_resident_no_answer_requires_zero_federal_claims():
    with pytest.raises(ValidationError, match="must enter zero"):
        PortalTaxForms.model_validate(
            {
                "social_insurance_number": "046454286",
                "country_of_permanent_residence": "United States",
                "federal_claim_amounts": ["16452", *(["0"] * 11)],
                "bc_claim_amounts": ["0"] * 10,
                "non_resident_world_income_90_percent_or_more": False,
                "federal_certified": True,
                "bc_certified": True,
            }
        )


def test_non_resident_no_answer_accepts_zero_federal_claims():
    packet = PortalTaxForms.model_validate(
        {
            "social_insurance_number": "046454286",
            "country_of_permanent_residence": "United States",
            "federal_claim_amounts": ["0"] * 12,
            "bc_claim_amounts": ["13216", *(["0"] * 9)],
            "non_resident_world_income_90_percent_or_more": False,
            "federal_certified": True,
            "bc_certified": True,
        }
    )
    assert packet.non_resident_world_income_90_percent_or_more is False
