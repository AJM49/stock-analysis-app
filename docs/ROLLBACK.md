# Rollback Runbook

## Purpose

This document explains how to recover the Stock Analysis Dashboard if a production deployment fails.

## Current Stable Release

- App: Stock Analysis Dashboard
- Stable version: v0.50.0
- Stable branch: main
- Stable tag: v0.50.0
- Main file path: stock_app.py

## When to Roll Back

- App fails to boot
- Missing Python package error
- Database connection failure
- Streamlit secrets failure
- Major UI sections missing
- Market data workflow broken
- Diagnostics page unavailable
- Production branch points to the wrong commit

## Roll Back Streamlit Cloud

1. Open Streamlit Cloud.
2. Open the deployed app.
3. Go to Manage app.
4. Open Settings.
5. Set Branch to a known stable branch.
6. Keep Main file path as stock_app.py.
7. Save.
8. Reboot or redeploy.
9. Confirm the app loads.

## Roll Back GitHub main to Stable Tag

Run this only if main must be restored to the stable release:

git checkout main
git fetch origin
git reset --hard v0.50.0
git push origin main --force-with-lease

## Verification After Rollback

- Stock Analysis Dashboard v0.50.0
- Sprint 50: Stabilization Release
- Release Notes visible
- Developer Status visible
- Diagnostics Page loads
- Admin Safety Guard visible
- Migration Status healthy
- Cache-only mode checked by default

## Database Verification

Run:

python3 scripts/run_database_migrations.py

Expected:

Database migrations completed.
