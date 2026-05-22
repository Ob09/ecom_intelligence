# Week 1: Environment Setup and Project Foundations

## What I Built This Week
- Set up a professional Python development environment using Anaconda (ecom-bi conda env, Python 3.11)
- Created the full project folder structure
- Set up GitHub repository with version control
- Created and connected a free PostgreSQL database on Supabase (West EU - Ireland)
- Downloaded the Olist Brazilian E-commerce dataset (100,000 orders, 9 CSV files)
- Wrote a Python ingestion script that loaded all 9 CSV files into Supabase
- Verified all 9 tables are live in the database

## Tools Set Up This Week
| Tool | Purpose |
|------|---------|
| Anaconda (ecom-bi env) | Isolated Python 3.11 environment |
| Git + GitHub | Version control and code hosting |
| Supabase | Free hosted PostgreSQL database |
| Pandas | Reading CSV files |
| SQLAlchemy | Connecting Python to PostgreSQL |
| python-dotenv | Managing secret credentials |

## Key Concepts Learned
- Virtual environments — why isolation matters per project
- .env files — keeping secrets out of GitHub
- .gitignore — controlling what Git tracks
- Git workflow — add, commit, push
- Database connection strings — how Python talks to PostgreSQL
- Chunked data loading — handling large files without timeout errors

## Database Tables Created
| Table | Rows |
|-------|------|
| raw_orders | 99,441 |
| raw_customers | 99,441 |
| raw_products | 32,951 |
| raw_sellers | 3,095 |
| raw_payments | 103,886 |
| raw_reviews | 100,000 |
| raw_order_items | 112,650 |
| raw_geolocation | 1,000,163 |
| raw_category_translation | 71 |

## Next Steps
Week 2 — Data modelling with dbt: transform raw tables into clean analytical models