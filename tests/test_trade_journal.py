from __future__ import annotations

import pytest

from paper_trading.trade_journal import (
    add_journal_entry,
    build_trade_journal_dataframe,
    build_trade_journal_summary,
    create_trade_journal_entry,
    get_journal_entries_by_label,
    get_journal_entries_by_tag,
    get_journal_entries_by_ticker,
    get_journal_entries_by_trade_id,
    normalize_tags,
    normalize_ticker,
    validate_review_label,
)


def build_sample_journal_entries() -> list[dict[str, object]]:
    entry_1 = create_trade_journal_entry(
        account_id="acct-1",
        ticker="aapl",
        note="Entry followed the plan.",
        linked_trade_id="trade-1",
        review_label="Plan",
        tags=["Breakout", " Risk ", "breakout"],
    )

    entry_2 = create_trade_journal_entry(
        account_id="acct-1",
        ticker="MSFT",
        note="Good discipline on exit.",
        linked_trade_id="trade-2",
        review_label="Good Trade",
        tags=["discipline", "exit"],
    )

    entry_3 = create_trade_journal_entry(
        account_id="acct-1",
        ticker="AAPL",
        note="Need to review position size next time.",
        review_label="Lesson",
        tags=["review", "position-size"],
    )

    return [entry_1, entry_2, entry_3]


def test_normalize_ticker() -> None:
    assert normalize_ticker(" aapl ") == "AAPL"


def test_normalize_ticker_rejects_empty() -> None:
    with pytest.raises(ValueError, match="ticker"):
        normalize_ticker(" ")


def test_normalize_tags() -> None:
    tags = normalize_tags([" Breakout ", "risk", "breakout", "", "Risk"])

    assert tags == ["breakout", "risk"]


def test_normalize_tags_none() -> None:
    assert normalize_tags(None) == []


def test_validate_review_label_accepts_valid_label() -> None:
    validate_review_label("Good Trade")


def test_validate_review_label_rejects_invalid_label() -> None:
    with pytest.raises(ValueError, match="review_label"):
        validate_review_label("Random")


def test_create_trade_journal_entry() -> None:
    entry = create_trade_journal_entry(
        account_id="acct-1",
        ticker="aapl",
        note="Followed my setup.",
        linked_trade_id="trade-1",
        review_label="Plan",
        tags=["setup", "risk"],
    )

    assert entry["journal_id"]
    assert entry["ticker"] == "AAPL"
    assert entry["note"] == "Followed my setup."
    assert entry["linked_trade_id"] == "trade-1"
    assert entry["review_label"] == "Plan"
    assert entry["tags"] == ["setup", "risk"]


def test_create_trade_journal_entry_rejects_empty_note() -> None:
    with pytest.raises(ValueError, match="note"):
        create_trade_journal_entry(
            account_id="acct-1",
            ticker="AAPL",
            note=" ",
        )


def test_add_journal_entry() -> None:
    entries = build_sample_journal_entries()
    new_entry = create_trade_journal_entry(
        account_id="acct-1",
        ticker="NVDA",
        note="Follow up on volatility.",
        review_label="Follow Up",
    )

    result = add_journal_entry(entries, new_entry)

    assert len(result) == 4
    assert {entry["ticker"] for entry in result} == {"AAPL", "MSFT", "NVDA"}


def test_get_journal_entries_by_ticker() -> None:
    entries = build_sample_journal_entries()

    result = get_journal_entries_by_ticker(entries, "aapl")

    assert len(result) == 2
    assert all(entry["ticker"] == "AAPL" for entry in result)


def test_get_journal_entries_by_trade_id() -> None:
    entries = build_sample_journal_entries()

    result = get_journal_entries_by_trade_id(entries, "trade-1")

    assert len(result) == 1
    assert result[0]["ticker"] == "AAPL"


def test_get_journal_entries_by_trade_id_rejects_empty() -> None:
    with pytest.raises(ValueError, match="linked_trade_id"):
        get_journal_entries_by_trade_id([], "")


def test_get_journal_entries_by_label() -> None:
    entries = build_sample_journal_entries()

    result = get_journal_entries_by_label(entries, "Lesson")

    assert len(result) == 1
    assert result[0]["review_label"] == "Lesson"


def test_get_journal_entries_by_tag() -> None:
    entries = build_sample_journal_entries()

    result = get_journal_entries_by_tag(entries, "breakout")

    assert len(result) == 1
    assert result[0]["ticker"] == "AAPL"


def test_get_journal_entries_by_tag_rejects_empty() -> None:
    with pytest.raises(ValueError, match="tag"):
        get_journal_entries_by_tag([], " ")


def test_build_trade_journal_dataframe() -> None:
    entries = build_sample_journal_entries()

    df = build_trade_journal_dataframe(entries)

    expected_columns = [
        "journal_id",
        "account_id",
        "ticker",
        "linked_trade_id",
        "review_label",
        "tags",
        "note",
        "created_at",
    ]

    assert list(df.columns) == expected_columns
    assert len(df) == 3
    assert set(df["ticker"]) == {"AAPL", "MSFT"}


def test_build_trade_journal_summary() -> None:
    entries = build_sample_journal_entries()

    summary = build_trade_journal_summary(entries)

    assert summary["journal_entry_count"] == 3
    assert summary["unique_ticker_count"] == 2
    assert summary["linked_trade_note_count"] == 2
    assert summary["unlinked_note_count"] == 1
    assert summary["plan_count"] == 1
    assert summary["good_trade_count"] == 1
    assert summary["lesson_count"] == 1
    assert summary["most_common_ticker"] == "AAPL"


def test_build_trade_journal_summary_empty() -> None:
    summary = build_trade_journal_summary([])

    assert summary["journal_entry_count"] == 0
    assert summary["most_common_ticker"] is None
