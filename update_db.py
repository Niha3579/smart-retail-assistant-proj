import sqlite3
import os

db_path = os.path.join('instance', 'retail.db')
if not os.path.exists(db_path):
    print("DB not found at", db_path)
else:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE sales_records ADD COLUMN order_id VARCHAR(50);")
        c.execute("ALTER TABLE sales_records ADD COLUMN customer_name VARCHAR(150);")
        c.execute("ALTER TABLE sales_records ADD COLUMN customer_email VARCHAR(200);")
        c.execute("ALTER TABLE sales_records ADD COLUMN status VARCHAR(50) DEFAULT 'Completed';")
        conn.commit()
        print("Columns added to sales_records")
    except Exception as e:
        print("Error adding columns:", e)

    try:
        c.execute('''CREATE TABLE documents (
            id INTEGER PRIMARY KEY,
            filename VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            created_at DATETIME
        )''')
        conn.commit()
        print("documents table created")
    except Exception as e:
        print("Error creating documents table:", e)
        
    conn.close()
