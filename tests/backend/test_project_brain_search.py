from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.assistant import ProjectMemory
from app.services.project_brain import search_memory


def _memory(
    source_id: str,
    title: str,
    content: str,
    *,
    authority: int,
    source_kind: str = "chatgpt_conversation",
    source_date: datetime | None = None,
) -> ProjectMemory:
    return ProjectMemory(
        source_id=source_id,
        source_kind=source_kind,
        title=title,
        content=content,
        authority=authority,
        source_date=source_date,
        imported_by="test",
    )


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    ProjectMemory.__table__.create(engine)
    return Session(engine)


def test_search_excludes_unrelated_high_authority_records() -> None:
    with _session() as db:
        db.add_all([
            _memory(
                "canonical:policy",
                "Agent policy",
                "Management approvals and audit requirements.",
                authority=100,
                source_kind="management_decision",
            ),
            _memory(
                "chatgpt:rfq",
                "Supplier RFQ workflow",
                "Send pipe RFQs to EMCO and compare supplier quotes.",
                authority=60,
            ),
        ])
        db.commit()

        results = search_memory(db, query="supplier RFQ")

        assert [item.source_id for item in results] == ["chatgpt:rfq"]


def test_exact_phrase_match_ranks_above_individual_term_matches() -> None:
    now = datetime.now(UTC)
    with _session() as db:
        db.add_all([
            _memory(
                "chatgpt:terms",
                "Supplier planning",
                "The RFQ process is documented separately.",
                authority=80,
                source_date=now,
            ),
            _memory(
                "chatgpt:phrase",
                "Supplier RFQ workflow",
                "Current quote workflow.",
                authority=60,
                source_date=now - timedelta(days=30),
            ),
        ])
        db.commit()

        results = search_memory(db, query="supplier RFQ")

        assert [item.source_id for item in results] == ["chatgpt:phrase", "chatgpt:terms"]


def test_source_authority_and_limit_filters_are_applied() -> None:
    with _session() as db:
        db.add_all([
            _memory(
                "canonical:supplier",
                "Supplier decision",
                "Supplier selection rules.",
                authority=95,
                source_kind="management_decision",
            ),
            _memory(
                "chatgpt:supplier-high",
                "Supplier quote review",
                "Supplier quote comparison.",
                authority=80,
            ),
            _memory(
                "chatgpt:supplier-low",
                "Supplier note",
                "Supplier response details.",
                authority=50,
            ),
        ])
        db.commit()

        results = search_memory(
            db,
            query="supplier",
            source_kind="chatgpt_conversation",
            min_authority=60,
            limit=1,
        )

        assert [item.source_id for item in results] == ["chatgpt:supplier-high"]


def test_empty_query_returns_authority_ordered_records() -> None:
    with _session() as db:
        db.add_all([
            _memory("chatgpt:low", "Low", "Record", authority=60),
            _memory("canonical:high", "High", "Record", authority=95, source_kind="management_decision"),
        ])
        db.commit()

        results = search_memory(db, limit=2)

        assert [item.source_id for item in results] == ["canonical:high", "chatgpt:low"]
