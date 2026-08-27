from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from app.models.bid import Bid
from app.models.project import Project
from app.services.bennett_strata_staging_import import (
    LEGACY_PROJECT_NUMBER,
    PROJECT_NAME,
    SOURCE_KEY,
    SOURCE_REVISION,
    import_bennett_strata_estimates,
)
from app.services.drive_tender_import import ImportValidationError
from conftest import TestingSessionLocal

IMPORTED_AT = datetime(2026, 8, 27, 19, 0, tzinfo=timezone.utc)


def test_dry_run_reports_authoritative_final_estimates_without_mutation() -> None:
    with TestingSessionLocal() as db:
        report = import_bennett_strata_estimates(
            db,
            actor="Staging Operator",
            imported_at=IMPORTED_AT,
        )

        assert report["status"] == "dry_run"
        assert report["source_revision"] == SOURCE_REVISION
        assert report["staging_only"] is True
        assert report["project_action"] == "create"
        assert report["project_number_action"] == "none"
        concrete = next(item for item in report["records"] if item["estimate_key"] == "concrete")
        asphalt = next(item for item in report["records"] if item["estimate_key"] == "asphalt")
        assert concrete["cost_basis_cad"] == 26660.93
        assert concrete["approved_before_gst_cad"] == 36266.67
        assert concrete["approved_gst_cad"] == 1813.33
        assert concrete["approved_total_cad"] == 38080.0
        assert concrete["calculated_approved_cad"] == 36266.67
        assert asphalt["approved_before_gst_cad"] == 19260.65
        assert asphalt["approved_gst_cad"] == 963.03
        assert asphalt["approved_total_cad"] == 20223.68
        assert asphalt["calculated_approved_cad"] == 19260.65
        assert db.scalar(select(func.count()).select_from(Project)) == 0
        assert db.scalar(select(func.count()).select_from(Bid)) == 0


def test_apply_is_idempotent_and_creates_immutable_revision_workspaces() -> None:
    with TestingSessionLocal() as db:
        first = import_bennett_strata_estimates(
            db,
            actor="Staging Operator",
            apply=True,
            imported_at=IMPORTED_AT,
        )
        db.commit()
        second = import_bennett_strata_estimates(
            db,
            actor="Second Staging Operator",
            apply=True,
            imported_at=datetime(2026, 8, 27, 20, 0, tzinfo=timezone.utc),
        )
        db.commit()

        assert first["status"] == "applied"
        assert first["project_action"] == "create"
        assert second["project_action"] == "reuse"
        assert db.scalar(select(func.count()).select_from(Project)) == 1
        assert db.scalar(select(func.count()).select_from(Bid)) == 2
        assert all(item["action"] == "reuse" for item in second["records"])

        project = db.scalar(select(Project))
        assert project is not None
        assert project.client_owner == "Bennett Strata"
        assert project.project_address == "Bennett Road, Richmond, BC"
        assert project.project_number is None
        assert project.status == "opportunity"
        source_metadata = project.metadata_json[SOURCE_KEY]
        assert source_metadata["latest_source_revision"] == SOURCE_REVISION
        assert source_metadata["revisions"][SOURCE_REVISION]["status"] == "draft_source"

        bids = list(db.scalars(select(Bid)).all())
        assert {item.bid_json["estimate_key"] for item in bids} == {"concrete", "asphalt"}
        for bid in bids:
            assert bid.status == "draft"
            assert bid.bid_json["source"] == SOURCE_KEY
            assert bid.bid_json["source_revision"] == SOURCE_REVISION
            assert bid.bid_json["pricing_scenarios"]["20_percent_margin_floor"]["before_gst"] > 0
            assert bid.bid_json["pricing_scenarios"]["approved_final"]["total"] > 0
            assert bid.bid_json["site_photo_count"] == 19
            assert bid.bid_json["audit_actor"] == "Staging Operator"

        asphalt = next(bid for bid in bids if bid.bid_json["estimate_key"] == "asphalt")
        options = asphalt.bid_json["customer_options"]
        assert options["mutually_exclusive"] is True
        assert options["selected_option_id"] is None
        assert options["draft_selected_options_total"] == 0
        assert [item["total"] for item in options["items"]] == [3990.0, 8561.54, 8960.0]


def test_apply_repairs_only_the_exact_legacy_opportunity_marker_and_versions_old_bids() -> None:
    with TestingSessionLocal() as db:
        project = Project(
            name=PROJECT_NAME,
            project_number=LEGACY_PROJECT_NUMBER,
            status="opportunity",
            metadata_json={SOURCE_KEY: {"issue": 314}},
        )
        db.add(project)
        db.flush()
        old_bid = Bid(
            project_id=project.id,
            status="draft",
            bid_json={"source": SOURCE_KEY, "estimate_key": "concrete", "summary": {"final_price": 1}},
        )
        db.add(old_bid)
        db.commit()

        report = import_bennett_strata_estimates(
            db,
            actor="Staging Operator",
            apply=True,
            imported_at=IMPORTED_AT,
        )
        db.commit()

        db.refresh(project)
        assert report["project_number_action"] == "clear_legacy_marker"
        assert project.project_number is None
        bids = list(db.scalars(select(Bid).where(Bid.project_id == project.id)).all())
        assert len(bids) == 3
        assert old_bid in bids
        assert sum((bid.bid_json or {}).get("source_revision") == SOURCE_REVISION for bid in bids) == 2


@pytest.mark.parametrize(
    ("project_number", "status", "message"),
    [
        (LEGACY_PROJECT_NUMBER, "awarded", "cannot be cleared"),
        ("UNKNOWN-STAGING-ID", "opportunity", "unexpected non-empty"),
        ("IH2026001", "awarded", "unexpected non-empty"),
    ],
)
def test_apply_fails_closed_for_ineligible_project_numbers(
    project_number: str,
    status: str,
    message: str,
) -> None:
    with TestingSessionLocal() as db:
        db.add(Project(name=PROJECT_NAME, project_number=project_number, status=status))
        db.commit()

        with pytest.raises(ImportValidationError, match=message):
            import_bennett_strata_estimates(
                db,
                actor="Staging Operator",
                apply=True,
                imported_at=IMPORTED_AT,
            )


def test_existing_final_revision_is_never_mutated_when_contents_differ() -> None:
    with TestingSessionLocal() as db:
        import_bennett_strata_estimates(
            db,
            actor="Staging Operator",
            apply=True,
            imported_at=IMPORTED_AT,
        )
        db.commit()
        bid = db.scalar(
            select(Bid).where(
                Bid.bid_json["source_revision"].as_string() == SOURCE_REVISION,
                Bid.bid_json["estimate_key"].as_string() == "concrete",
            )
        )
        assert bid is not None
        changed = dict(bid.bid_json)
        changed_summary = dict(changed["summary"])
        changed_summary["final_price"] = 1
        changed["summary"] = changed_summary
        bid.bid_json = changed
        db.commit()

        with pytest.raises(ImportValidationError, match="differs from the approved immutable source"):
            import_bennett_strata_estimates(
                db,
                actor="Staging Operator",
                apply=True,
                imported_at=IMPORTED_AT,
            )


def test_actor_is_required() -> None:
    with TestingSessionLocal() as db, pytest.raises(ImportValidationError, match="audit actor"):
        import_bennett_strata_estimates(db, actor=" ")
