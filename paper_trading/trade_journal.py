from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pandas as pd

from paper_trading.models import TradeJournalEntry


VALID_REVIEW_LABELS = {
    "Plan",
    "Good Trade",
    "Bad Trade",
    "Mistake",
    "Lesson",
    "Follow Up",
}


def normalize_ticker(ticker: str) -> str:
    """Normalize ticker symbols for journal lookup."""
    if not ticker or not ticker.strip():
        raise ValueError("ticker cannot be empty")

    return ticker.strip().upper()


def normalize_tags(tags: list[str] | None) -> list[str]:
    """Normalize journal tags."""
    if tags is None:
        return []

    clean_tags = []

    for tag in tags:
        clean_tag = str(tag).strip().lower()

        if clean_tag and clean_tag not in clean_tags:
            clean_tags.append(clean_tag)

    return clean_tags


def validate_review_label(review_label: str) -> None:
    """Validate review label."""
    if review_label not in VALID_REVIEW_LABELS:
        valid_labels = ", ".join(sorted(VALID_REVIEW_LABELS))
        raise ValueError(f"review_label must be one of: {valid_labels}")


def create_trade_journal_entry(
    account_id: str,
    ticker: str,
    note: str,
    linked_trade_id: str | None = None,
    review_label: str = "Plan",
    tags: list[str] | None = None,
) -> dict[str, object]:
    """Create a journal entry dictionary with metadata."""
    if not account_id:
        raise ValueError("account_id cannot be empty")

    clean_ticker = normalize_ticker(ticker)

    if not note or not note.strip():
        raise ValueError("note cannot be empty")

    validate_review_label(review_label)

    journal_entry = TradeJournalEntry(
        journal_id=str(uuid4()),
        account_id=account_id,
        ticker=clean_ticker,
        note=note.strip(),
        linked_trade_id=linked_trade_id,
        created_at=datetime.now(UTC),
    )

    return {
        "journal_entry": journal_entry,
        "journal_id": journal_entry.journal_id,
        "account_id": journal_entry.account_id,
        "ticker": journal_entry.ticker,
        "note": journal_entry.note,
        "linked_trade_id": journal_entry.linked_trade_id,
        "review_label": review_label,
        "tags": normalize_tags(tags),
        "created_at": journal_entry.created_at,
    }


def add_journal_entry(
    journal_entries: list[dict[str, object]],
    journal_entry: dict[str, object],
) -> list[dict[str, object]]:
    """Add a journal entry to the journal ledger."""
    return sorted(
        [*journal_entries, journal_entry],
        key=lambda entry: (entry["created_at"], entry["ticker"]),
    )


def get_journal_entries_by_ticker(
    journal_entries: list[dict[str, object]],
    ticker: str,
) -> list[dict[str, object]]:
    """Get journal entries for one ticker."""
    clean_ticker = normalize_ticker(ticker)

    return [
        entry
        for entry in journal_entries
        if entry["ticker"] == clean_ticker
    ]


def get_journal_entries_by_trade_id(
    journal_entries: list[dict[str, object]],
    linked_trade_id: str,
) -> list[dict[str, object]]:
    """Get journal entries linked to a specific trade ID."""
    if not linked_trade_id:
        raise ValueError("linked_trade_id cannot be empty")

    return [
        entry
        for entry in journal_entries
        if entry["linked_trade_id"] == linked_trade_id
    ]


def get_journal_entries_by_label(
    journal_entries: list[dict[str, object]],
    review_label: str,
) -> list[dict[str, object]]:
    """Get journal entries by review label."""
    validate_review_label(review_label)

    return [
        entry
        for entry in journal_entries
        if entry["review_label"] == review_label
    ]


def get_journal_entries_by_tag(
    journal_entries: list[dict[str, object]],
    tag: str,
) -> list[dict[str, object]]:
    """Get journal entries by tag."""
    clean_tag = str(tag).strip().lower()

    if not clean_tag:
        raise ValueError("tag cannot be empty")

    return [
        entry
        for entry in journal_entries
        if clean_tag in entry["tags"]
    ]


def build_trade_journal_dataframe(
    journal_entries: list[dict[str, object]],
) -> pd.DataFrame:
    """Build table-ready trade journal DataFrame."""
    rows = []

    for entry in journal_entries:
        rows.append(
            {
                "journal_id": entry["journal_id"],
                "account_id": entry["account_id"],
                "ticker": entry["ticker"],
                "linked_trade_id": entry["linked_trade_id"],
                "review_label": entry["review_label"],
                "tags": ", ".join(entry["tags"]),
                "note": entry["note"],
                "created_at": entry["created_at"],
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "journal_id",
            "account_id",
            "ticker",
            "linked_trade_id",
            "review_label",
            "tags",
            "note",
            "created_at",
        ],
    )


def build_trade_journal_summary(
    journal_entries: list[dict[str, object]],
) -> dict[str, object]:
    """Build summary metrics for trade journal entries."""
    if not journal_entries:
        return {
            "journal_entry_count": 0,
            "unique_ticker_count": 0,
            "linked_trade_note_count": 0,
            "unlinked_note_count": 0,
            "plan_count": 0,
            "good_trade_count": 0,
            "bad_trade_count": 0,
            "mistake_count": 0,
            "lesson_count": 0,
            "follow_up_count": 0,
            "most_common_ticker": None,
        }

    journal_df = build_trade_journal_dataframe(journal_entries)

    ticker_counts = journal_df["ticker"].value_counts()
    most_common_ticker = str(ticker_counts.index[0])

    return {
        "journal_entry_count": len(journal_df),
        "unique_ticker_count": int(journal_df["ticker"].nunique()),
        "linked_trade_note_count": int(journal_df["linked_trade_id"].notna().sum()),
        "unlinked_note_count": int(journal_df["linked_trade_id"].isna().sum()),
        "plan_count": int((journal_df["review_label"] == "Plan").sum()),
        "good_trade_count": int((journal_df["review_label"] == "Good Trade").sum()),
        "bad_trade_count": int((journal_df["review_label"] == "Bad Trade").sum()),
        "mistake_count": int((journal_df["review_label"] == "Mistake").sum()),
        "lesson_count": int((journal_df["review_label"] == "Lesson").sum()),
        "follow_up_count": int((journal_df["review_label"] == "Follow Up").sum()),
        "most_common_ticker": most_common_ticker,
    }
