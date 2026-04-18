"""
main.py — TechNova Electronics O2C System
Entry point: menu-driven CLI to run the full O2C cycle.

Run:
    python main.py
"""
from database       import init_db
from o2c_pipeline   import (create_inquiry, create_quotation,
                             create_sales_order, create_delivery,
                             create_invoice, post_payment)
from reports        import (document_flow, ar_aging_report,
                             sales_summary, stock_report)
import sqlite3
from database import get_conn

BANNER = """
╔══════════════════════════════════════════════════════╗
║    TechNova Electronics Pvt. Ltd.                    ║
║    Order-to-Cash (O2C) System  —  SAP SD Simulation  ║
║    Capstone Project | Krissh Kumar Singh | 2329124   ║
╚══════════════════════════════════════════════════════╝
"""

MENU = """
  ── O2C TRANSACTIONS ──────────────────────────────────
  1.  Create Inquiry           (VA11)
  2.  Create Quotation         (VA21)
  3.  Create Sales Order       (VA01)
  4.  Create Delivery + PGI    (VL01N / VL02N)
  5.  Create Invoice           (VF01)
  6.  Post Payment             (F-28 / F-32)

  ── RUN FULL DEMO CYCLE ───────────────────────────────
  7.  Run Complete O2C Demo    (All 6 steps auto)

  ── REPORTS ───────────────────────────────────────────
  8.  Document Flow Report
  9.  AR Aging Report
  10. Sales Summary Report
  11. Stock Overview Report

  ── OTHER ─────────────────────────────────────────────
  12. Show Master Data
  0.  Exit
  ──────────────────────────────────────────────────────
"""

def show_master_data():
    conn = get_conn()
    c = conn.cursor()
    print("\n  ── CUSTOMERS ──────────────────────────────────────")
    for row in c.execute("SELECT * FROM customers"):
        print(f"  {row[0]} | {row[1]:<25} | {row[2]:<12} | Credit: ₹{row[3]:,.0f}")
    print("\n  ── MATERIALS ──────────────────────────────────────")
    for row in c.execute("SELECT * FROM materials"):
        print(f"  {row[0]} | {row[1]:<30} | ₹{row[2]:>10,.2f} | Stock: {row[3]}")
    print("\n  ── ORG STRUCTURE ──────────────────────────────────")
    for row in c.execute("SELECT * FROM org_structure"):
        print(f"  {row[0]:<25} : {row[1]}")
    conn.close()

def pick_from(table, id_col, label):
    conn = get_conn()
    c = conn.cursor()
    c.execute(f"SELECT {id_col} FROM {table} ORDER BY rowid DESC LIMIT 10")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    if not rows:
        print(f"  ❌  No {label} found. Please create one first.")
        return None
    print(f"\n  Recent {label}s:")
    for i, r in enumerate(rows, 1):
        print(f"    {i}. {r}")
    try:
        choice = int(input(f"  Select {label} (number): ")) - 1
        return rows[choice]
    except (ValueError, IndexError):
        print("  Invalid selection.")
        return None

def run_demo():
    """Runs a complete O2C cycle automatically for demo purposes."""
    print("\n  🚀  Running full O2C demo cycle for TechNova Electronics...")
    print("  Customer: CUST001 (Reliance Digital) | Material: MAT001 (Laptop Pro X1)")
    print("  Quantity: 10 units\n")

    try:
        inq_id = create_inquiry("CUST001", "MAT001", 10)
        qt_id  = create_quotation(inq_id)
        so_id  = create_sales_order(qt_id)
        dl_id  = create_delivery(so_id)
        inv_id = create_invoice(dl_id)
        pay_id = post_payment(inv_id)
        print(f"\n  ✅  Full O2C cycle completed successfully!")
        print(f"  INQ: {inq_id} → QT: {qt_id} → SO: {so_id}")
        print(f"  DL: {dl_id} → INV: {inv_id} → PAY: {pay_id}")
    except Exception as e:
        print(f"\n  ❌  Error: {e}")

def main():
    init_db()
    print(BANNER)

    while True:
        print(MENU)
        choice = input("  Enter option: ").strip()

        if choice == "1":
            show_master_data()
            cust = input("\n  Customer ID (e.g. CUST001): ").strip().upper()
            mat  = input("  Material ID (e.g. MAT001) : ").strip().upper()
            try:
                qty  = int(input("  Quantity               : ").strip())
                create_inquiry(cust, mat, qty)
            except Exception as e:
                print(f"  ❌  {e}")

        elif choice == "2":
            inq_id = pick_from("inquiries", "inquiry_id", "Inquiry")
            if inq_id:
                try:
                    create_quotation(inq_id)
                except Exception as e:
                    print(f"  ❌  {e}")

        elif choice == "3":
            qt_id = pick_from("quotations", "quotation_id", "Quotation")
            if qt_id:
                try:
                    create_sales_order(qt_id)
                except Exception as e:
                    print(f"  ❌  {e}")

        elif choice == "4":
            so_id = pick_from("sales_orders", "order_id", "Sales Order")
            if so_id:
                try:
                    create_delivery(so_id)
                except Exception as e:
                    print(f"  ❌  {e}")

        elif choice == "5":
            dl_id = pick_from("deliveries", "delivery_id", "Delivery")
            if dl_id:
                try:
                    create_invoice(dl_id)
                except Exception as e:
                    print(f"  ❌  {e}")

        elif choice == "6":
            inv_id = pick_from("invoices", "invoice_id", "Invoice")
            if inv_id:
                try:
                    post_payment(inv_id)
                except Exception as e:
                    print(f"  ❌  {e}")

        elif choice == "7":
            run_demo()

        elif choice == "8":
            document_flow()

        elif choice == "9":
            ar_aging_report()

        elif choice == "10":
            sales_summary()

        elif choice == "11":
            stock_report()

        elif choice == "12":
            show_master_data()

        elif choice == "0":
            print("\n  👋  Goodbye! — TechNova Electronics O2C System\n")
            break
        else:
            print("  ⚠️   Invalid option. Please try again.")

if __name__ == "__main__":
    main()
