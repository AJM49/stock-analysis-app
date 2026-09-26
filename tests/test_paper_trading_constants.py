from core.paper_trading_constants import FLOAT_TOLERANCE
from core.paper_trading_constants import MONEY_PRECISION
from core.paper_trading_constants import QUANTITY_PRECISION


def test_paper_trading_numeric_constants():
    assert FLOAT_TOLERANCE == 1e-9
    assert MONEY_PRECISION == 2
    assert QUANTITY_PRECISION == 6
