from datetime import datetime, timezone

import pytest
from app.models.bid import Bid
from app.models.project import Project
from app.services.bennett_strata_staging_import import import_bennett_strata_estimates
from app.services.drive_tender_import import ImportValidationError
from conftest import TestingSessionLocal
from sqlalchemy import func, select

IMPORTED_AT = datetime(2026, 8, 25, 14, 0, tzinfo=timezone.utc)


def test_dry_run_reports_two_estimates_without_mutation() -> None:
    with TestingSessionLocal() as db:
        report = import_bennett_strata_estimates(
            db,
            actor="Staging Operator",
            imported_at=IMPORTED_AT,
        )

        assert report["status"] == "dry_run"
        assert report["staging_only"] is True
        assert {item["estimate_key"] for item in report["records"]} == {"concrete", "asphalt"}
        concrete = next(item for item in report["records"] if item["estimate_key"] == "concrete")
        asphalt = next(item for item in report["records"] if item["estimate_key"] == "asphalt")
        assert concrete["cost_basis_cad"] == 26660.93
        assert concrete["target_30_percent_before_gst_cad"] == 38087.04
        assert asphalt["cost_basis_cad"] == 12300.0
        assert asphalt["target_30_percent_before_gst_cad"] == 17571.43
        assert db.scalar(select(func.count()).select_from(Project)) == 0
        assert db.scalar(select(func.count()).select_from(Bid)) == 0


def test_apply_is_idempotent_and_creates_two_separate_workspaces() -> None:
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
            actor="Staging Operator",
            apply=True,
            imported_at=IMPORTED_AT,
        )
        db.commit()

        assert first["status"] == "applied"
        assert db.scalar(select(func.count()).select_from(Project)) == 1
        assert db.scalar(select(func.count()).select_from(Bid)) == 2
        assert all(item["action"] == "update" for item in second["records"])

        project = db.scalar(select(Project))
        assert project.client_owner == "Bennett Strata"
        assert project.project_address == "Bennett Road, Richmond, BC"
        assert project.project_number == "STAGE-BENNETT-2026"
        assert project.metadata_json["bennett_strata_issue_314"]["site_photo_count"] == 19

        bids = list(db.scalars(select(Bid)).all())
        assert {item.bid_json["estimate_key"] for item in bids} == {"concrete", "asphalt"}
        for bid in bids:
            assert bid.status == "draft"
            assert bid.bid_json["source"] == "bennett_strata_issue_314"
            assert bid.bid_json["pricing_scenarios"]["20_percent_margin"]["before_gst"] > 0
            assert bid.bid_json["pricing_scenarios"]["30_percent_margin"]["before_gst"] > 0
            assert bid.bid_json["site_photo_count"] == 19


def test_actor_is_required() -> None:
    with TestingSessionLocal() as db, pytest.raises(ImportValidationError, match="audit actor"):
        import_bennett_strata_estimates(db, actor=" ")
