from __future__ import annotations

# Compatibility facade.
# stock_app.py keeps importing from ui_components.py.
# Real UI code is gradually moving into smaller ui/ modules.

from ui.cache_panel import render_market_cache_panel
from ui.charts import render_comparison_chart
from ui.charts import render_price_chart
from ui.charts import make_arrow_safe
from ui.charts import render_stock_comparison

from ui.stock_views import render_company_profile
from ui.portfolio_views import render_portfolio_dashboard
from ui.sidebar import render_portfolio_sidebar
from ui.portfolio_views import render_portfolio_table
from ui.portfolio_views import render_risk_dashboard
from ui.stock_views import render_stock_export
from ui.stock_views import render_stock_header
from ui.portfolio_views import render_stop_loss_calculator
from ui.stock_views import render_technical_indicators
from ui.sidebar import render_watchlist_sidebar
from ui.dev_status import render_developer_status_panel

from ui.release_notes_panel import render_release_notes_panel
