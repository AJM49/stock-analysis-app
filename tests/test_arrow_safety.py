import pandas as pd

from ui.charts import make_arrow_safe


def test_make_arrow_safe_converts_object_values_to_strings() -> None:
    dataframe = pd.DataFrame(
        {
            "Ticker": ["AAPL", "MSFT"],
            "Metadata": [{"source": "cache"}, {"source": "live"}],
            "Price": [100.0, 200.0],
        }
    )

    result = make_arrow_safe(dataframe)

    assert result["Ticker"].tolist() == ["AAPL", "MSFT"]
    assert result["Metadata"].tolist() == [
        "{'source': 'cache'}",
        "{'source': 'live'}",
    ]
    assert result["Price"].tolist() == [100.0, 200.0]


def test_make_arrow_safe_does_not_mutate_input_dataframe() -> None:
    dataframe = pd.DataFrame(
        {
            "Metadata": [{"source": "cache"}],
        }
    )

    result = make_arrow_safe(dataframe)

    assert result is not dataframe
    assert dataframe["Metadata"].iloc[0] == {"source": "cache"}
    assert result["Metadata"].iloc[0] == "{'source': 'cache'}"


def test_make_arrow_safe_returns_empty_dataframe_for_none() -> None:
    result = make_arrow_safe(None)

    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_stock_views_uses_canonical_arrow_safe_helper() -> None:
    import ui.stock_views as stock_views

    from ui.charts import make_arrow_safe

    assert stock_views.make_arrow_safe is make_arrow_safe
