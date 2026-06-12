from __future__ import annotations

# Compatibility facade.
# stock_app.py can keep importing from ui_components.py while the real UI
# implementation moves into smaller modules.

from ui.cache_panel import render_market_cache_panel
from ui.charts import render_comparison_chart
from ui.charts import render_price_chart

# Legacy functions still live in the backup during migration.
# We import them from the old module copy so product behavior remains unchanged.
from ui_components_legacy_backup import make_arrow_safe
from ui_components_legacy_backup import render_company_profile
from ui_components_legacy_backup import render_portfolio_dashboard
from ui_components_legacy_backup import render_portfolio_sidebar
from ui_components_legacy_backup import render_portfolio_table
from ui_components_legacy_backup import render_risk_dashboard
from ui_components_legacy_backup import render_stock_comparison
from ui_components_legacy_backup import render_stock_export
from ui_components_legacy_backup import render_stock_header
from ui_components_legacy_backup import render_stop_loss_calculator
from ui_components_legacy_backup import render_technical_indicators
from ui_components_legacy_backup import render_watchlist_sidebar
