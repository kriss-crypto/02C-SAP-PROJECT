"""
database.py — TechNova Electronics O2C
Creates and seeds the SQLite database with master data.
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "technova_o2c.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    # ── Master Data Tables ────────────────────────────────────────────────────
    c.executescript("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id   TEXT PRIMARY KEY,
        name          TEXT NOT NULL,
        city          TEXT,
        credit_limit  REAL DEFAULT 5000000,
        payment_terms TEXT DEFAULT 'NET30'
    );

    CREATE TABLE IF NOT EXISTS materials (
        material_id   TEXT PRIMARY KEY,
        description   TEXT NOT NULL,
        unit_price    REAL NOT NULL,
        stock_qty     INTEGER DEFAULT 0,
        uom           TEXT DEFAULT 'EA'
    );

    CREATE TABLE IF NOT EXISTS org_structure (
        key   TEXT PRIMARY KEY,
        value TEXT
    );

    -- ── Transaction Tables ───────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS inquiries (
        inquiry_id     TEXT PRIMARY KEY,
        customer_id    TEXT,
        material_id    TEXT,
        quantity       INTEGER,
        req_del_date   TEXT,
        created_at     TEXT DEFAULT (datetime('now')),
        status         TEXT DEFAULT 'OPEN',
        FOREIGN KEY(customer_id) REFERENCES customers(customer_id),
        FOREIGN KEY(material_id) REFERENCES materials(material_id)
    );

    CREATE TABLE IF NOT EXISTS quotations (
        quotation_id   TEXT PRIMARY KEY,
        inquiry_id     TEXT,
        customer_id    TEXT,
        material_id    TEXT,
        quantity       INTEGER,
        unit_price     REAL,
        discount_pct   REAL DEFAULT 5.0,
        gst_pct        REAL DEFAULT 18.0,
        net_amount     REAL,
        gross_amount   REAL,
        valid_from     TEXT,
        valid_to       TEXT,
        created_at     TEXT DEFAULT (datetime('now')),
        status         TEXT DEFAULT 'SENT',
        FOREIGN KEY(inquiry_id) REFERENCES inquiries(inquiry_id)
    );

    CREATE TABLE IF NOT EXISTS sales_orders (
        order_id       TEXT PRIMARY KEY,
        quotation_id   TEXT,
        customer_id    TEXT,
        material_id    TEXT,
        quantity       INTEGER,
        unit_price     REAL,
        discount_pct   REAL,
        gst_pct        REAL,
        net_amount     REAL,
        gross_amount   REAL,
        req_del_date   TEXT,
        created_at     TEXT DEFAULT (datetime('now')),
        credit_status  TEXT DEFAULT 'APPROVED',
        status         TEXT DEFAULT 'OPEN',
        FOREIGN KEY(quotation_id) REFERENCES quotations(quotation_id)
    );

    CREATE TABLE IF NOT EXISTS deliveries (
        delivery_id    TEXT PRIMARY KEY,
        order_id       TEXT,
        customer_id    TEXT,
        material_id    TEXT,
        quantity       INTEGER,
        shipping_point TEXT DEFAULT 'SP01',
        planned_gi     TEXT,
        actual_gi      TEXT,
        status         TEXT DEFAULT 'PENDING',
        created_at     TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(order_id) REFERENCES sales_orders(order_id)
    );

    CREATE TABLE IF NOT EXISTS invoices (
        invoice_id     TEXT PRIMARY KEY,
        delivery_id    TEXT,
        order_id       TEXT,
        customer_id    TEXT,
        material_id    TEXT,
        quantity       INTEGER,
        net_amount     REAL,
        gst_amount     REAL,
        gross_amount   REAL,
        billing_date   TEXT,
        due_date       TEXT,
        created_at     TEXT DEFAULT (datetime('now')),
        status         TEXT DEFAULT 'OPEN',
        FOREIGN KEY(delivery_id) REFERENCES deliveries(delivery_id)
    );

    CREATE TABLE IF NOT EXISTS payments (
        payment_id     TEXT PRIMARY KEY,
        invoice_id     TEXT,
        customer_id    TEXT,
        amount_paid    REAL,
        payment_date   TEXT,
        bank_account   TEXT DEFAULT 'TN01-MAIN-BANK',
        created_at     TEXT DEFAULT (datetime('now')),
        status         TEXT DEFAULT 'CLEARED',
        FOREIGN KEY(invoice_id) REFERENCES invoices(invoice_id)
    );
    """)

    # ── Seed Master Data ─────────────────────────────────────────────────────
    c.executemany("INSERT OR IGNORE INTO customers VALUES (?,?,?,?,?)", [
        ("CUST001", "Reliance Digital",  "New Delhi", 10000000, "NET30"),
        ("CUST002", "Croma Stores",      "Mumbai",     8000000, "NET45"),
        ("CUST003", "Vijay Sales",       "Bangalore",  5000000, "NET30"),
    ])

    c.executemany("INSERT OR IGNORE INTO materials VALUES (?,?,?,?,?)", [
        ("MAT001", "Laptop Pro X1",    75000.0, 200, "EA"),
        ("MAT002", "Wireless Earbuds Z3", 3500.0, 500, "EA"),
        ("MAT003", 'Smart TV 55"',     55000.0, 100, "EA"),
    ])

    c.executemany("INSERT OR IGNORE INTO org_structure VALUES (?,?)", [
        ("COMPANY_CODE",        "TN01 — TechNova Electronics India"),
        ("SALES_ORG",           "SL01 — India Sales Organisation"),
        ("DIST_CHANNEL",        "DI — Direct Sales"),
        ("DIVISION",            "EL — Electronics"),
        ("PLANT",               "PL01 — Bhubaneswar Warehouse"),
        ("SHIPPING_POINT",      "SP01 — Main Dispatch Hub"),
        ("CREDIT_CTRL_AREA",    "CC01 — India Credit Control"),
        ("PRICING_PROCEDURE",   "RVAA01"),
    ])

    conn.commit()
    conn.close()
    print("✅  Database initialised — technova_o2c.db")

if __name__ == "__main__":
    init_db()
