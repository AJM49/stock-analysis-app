# Production Deployment Checklist

## Purpose

This checklist defines the minimum checks before and after deploying the Stock Analysis Dashboard.

## Current Production Target

- Repository: AJM49/stock-analysis-app
- Branch: main
- Main file path: stock_app.py
- Stable release: v0.50.0
- Database: Neon Postgres
- Hosting: Streamlit Cloud

## Pre-Deployment Checks

Run:

git branch --show-current
git status -sb
git log --oneline -5

Confirm:

- You are on main or a release-ready branch
- Working tree is clean
- Latest commit is expected
- No secrets are tracked

## Dependency Check

Confirm requirements.txt includes:

- streamlit
- pandas
- plotly
- sqlalchemy
- psycopg2-binary
- requests
- python-dotenv

## Secrets Check

Required Streamlit Cloud secrets:

- DATABASE_URL
- ALPHA_VANTAGE_API_KEY

Confirm local secrets are ignored:

git ls-files .streamlit/secrets.toml
git check-ignore -v .streamlit/secrets.toml

## Migration Check

python3 scripts/run_database_migrations.py

Expected:

Database migrations completed.

## Compile Check

python3 -m py_compile stock_app.py
python3 -m py_compile database.py
python3 -m py_compile market_data.py
python3 -m py_compile ui_components.py
python3 -m py_compile ui/diagnostics_page.py
python3 -m py_compile scripts/run_database_migrations.py

Expected: no output.

## Local Launch Check

python3 -m streamlit run stock_app.py

Confirm:

- App loads
- Cache-only mode is checked by default
- Refresh Market Data is disabled while cache-only is checked
- Release Notes are visible
- Developer Status is visible
- Diagnostics Page loads
- Admin Safety Guard appears

## Streamlit Cloud Settings

- Repository: AJM49/stock-analysis-app
- Branch: main
- Main file path: stock_app.py

## Post-Deployment Checks

- Stock Analysis Dashboard v0.50.0
- Sprint 50: Stabilization Release
- Database shows Cloud Postgres
- Migration Status is healthy
- Release Notes visible
- Developer Status visible
- Diagnostics Page loads
- Admin Safety Guard visible
