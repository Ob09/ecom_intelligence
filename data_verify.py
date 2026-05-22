from dotenv import dotenv_values
from sqlalchemy import create_engine, text

config = dotenv_values('.env')
engine = create_engine(config['DATABASE_URL'])

tables = [
    'raw_orders', 'raw_customers', 'raw_products',
    'raw_sellers', 'raw_payments', 'raw_reviews',
    'raw_order_items', 'raw_geolocation', 'raw_category_translation'
]

with engine.connect() as conn:
    for table in tables:
        result = conn.execute(text(f'SELECT COUNT(*) FROM {table}'))
        count = result.fetchone()[0]
        print(f'{table}: {count:,} rows')