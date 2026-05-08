"""
Run once to initialize database, run migrations, and load CSV data.
Usage: python init_db.py
"""
import os
from app import create_app, db
from app.services.data_loader import load_products_from_csv, load_sales_from_csv

app = create_app("development")

with app.app_context():
    print("Creating all tables…")
    db.create_all()
    print("Tables created.")

    # Load products
    products_csv = os.path.join("data", "ecommerce_products_updated.csv")
    if os.path.exists(products_csv):
        count = load_products_from_csv(products_csv)
        print(f"Loaded {count} products.")
    else:
        print("Products CSV not found at data/ecommerce_products_updated.csv")

    # Load sales
    sales_csv = os.path.join("data", "simulated_sales_data_2022_2025.csv")
    if os.path.exists(sales_csv):
        count = load_sales_from_csv(sales_csv)
        print(f"Loaded {count} sales records.")
    else:
        print("Sales CSV not found at data/simulated_sales_data_2022_2025.csv")

    print("\nDatabase initialized successfully.")
    print("Run: flask run")
