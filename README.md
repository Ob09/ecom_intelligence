 # E-commerce Business Intelligence and Analytics Platform

A full-stack business intelligence platform built on the Olist Brazilian E-commerce dataset.

## What This Project Does
- Ingests 100,000 real e-commerce orders from Olist (Brazil, 2016–2018)
- Transforms raw data into clean analytical models using dbt
- Validates data quality with Great Expectations
- Runs RFM segmentation, cohort retention analysis, and KPI tracking
- Generates 30-day revenue forecasts using Prophet
- Exposes analytics through a FastAPI REST API
- Displays everything in an interactive Plotly Dash dashboard

## Tech Stack
| Layer | Tool |
|-------|------|
| Database | PostgreSQL via Supabase |
| Transformation | dbt Core |
| Data Quality | Great Expectations |
| Analytics | Python (Pandas, NumPy, scikit-learn) |
| Forecasting | Prophet |
| API | FastAPI |
| Dashboard | Plotly Dash |
| Pipeline | GitHub Actions |
| Hosting | Render + GitHub Pages |

## Project Status
Week 1 — Environment setup and project structure
