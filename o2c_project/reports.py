"""
reports.py — TechNova Electronics O2C
Business reports: Document Flow, AR Aging, Sales Summary, Stock Report.
"""
import sqlite3
from database import get_conn

SEP = "─" * 70

def document_flow():
    """Full O2C document flow — mirrors SAP VF03 > Document Flow."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT
            i.inquiry_id,
            q.quotation_id,
            so.order_id,
            d.delivery_id,
            inv.invoice_id,
            p.payment_id,
            cu.name        AS customer,
            m.description  AS material,
            so.quantity,
            inv.gross_amount,
            inv.status     AS inv_status,
            p.payment_date
        FROM inquiries i
        LEFT JOIN quotations  q   ON i.inquiry_id   = q.inquiry_id
        LEFT JOIN sales_orders so ON q.quotation_id  = so.quotation_id
        LEFT JOIN deliveries   d  ON so.order_id     = d.order_id
        LEFT JOIN invoices     inv ON d.delivery_id   = inv.delivery_id
        LEFT JOIN payments     p  ON inv.invoice_id  = p.invoice_id
        LEFT JOIN customers    cu ON i.customer_id   = cu.customer_id
        LEFT JOIN materials    m  ON i.material_id   = m.material_id
        ORDER BY i.created_at DESC
    """)
    rows = c.fetchall()
    conn.close()

    print(f"\n{'='*70}")
    print(f"  📄  DOCUMENT FLOW REPORT  (SAP: VF03 > Environment > Doc Flow)")
    print(f"{'='*70}")
    if not rows:
        print("  No transactions found.")
        return

    for row in rows:
        (inq, qt, so, dl, inv, pay,
         cust, mat, qty, gross, inv_status, pay_date) = row
        print(f"\n  Customer  : {cust}")
        print(f"  Material  : {mat}  |  Qty: {qty}")
        print(f"  {SEP}")
        print(f"  Inquiry   : {inq or '—'}")
        print(f"     ↓")
        print(f"  Quotation : {qt  or '—'}")
        print(f"     ↓")
        print(f"  Sales Ord : {so  or '—'}")
        print(f"     ↓")
        print(f"  Delivery  : {dl  or '—'}")
        print(f"     ↓")
        print(f"  Invoice   : {inv or '—'}  |  ₹{gross:,.2f}  |  {inv_status}")
        print(f"     ↓")
        print(f"  Payment   : {pay or '—'}  |  {'Cleared ✅' if pay else 'Pending ⏳'}")
    print(f"\n{'='*70}\n")


def ar_aging_report():
    """Accounts Receivable Aging — mirrors SAP FBL5N."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT
            inv.invoice_id,
            cu.name,
            inv.gross_amount,
            inv.billing_date,
            inv.due_date,
            inv.status,
            CAST(julianday('now') - julianday(inv.due_date) AS INTEGER) AS overdue_days
        FROM invoices inv
        JOIN customers cu ON inv.customer_id = cu.customer_id
        ORDER BY overdue_days DESC
    """)
    rows = c.fetchall()
    conn.close()

    print(f"\n{'='*70}")
    print(f"  📊  ACCOUNTS RECEIVABLE AGING REPORT  (SAP: FBL5N)")
    print(f"{'='*70}")
    print(f"  {'Invoice':<20} {'Customer':<22} {'Amount':>12} {'Due Date':<12} {'Status':<10} {'Overdue'}")
    print(f"  {SEP}")
    total_open = 0
    for inv_id, cust, amt, bill_dt, due_dt, status, overdue in rows:
        flag = ""
        if status == "OPEN":
            total_open += amt
            flag = f"{'🔴 ' + str(overdue) + 'd' if overdue > 0 else '🟢 Current'}"
        else:
            flag = "✅ Cleared"
        print(f"  {inv_id:<20} {cust:<22} ₹{amt:>11,.2f} {due_dt:<12} {status:<10} {flag}")
    print(f"  {SEP}")
    print(f"  Total Open AR : ₹{total_open:,.2f}")
    print(f"{'='*70}\n")


def sales_summary():
    """Sales Summary by Customer — mirrors SAP VA05."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT
            cu.customer_id,
            cu.name,
            COUNT(so.order_id)     AS total_orders,
            SUM(so.quantity)       AS total_qty,
            SUM(so.gross_amount)   AS total_revenue
        FROM sales_orders so
        JOIN customers cu ON so.customer_id = cu.customer_id
        GROUP BY cu.customer_id
        ORDER BY total_revenue DESC
    """)
    rows = c.fetchall()
    conn.close()

    print(f"\n{'='*70}")
    print(f"  📈  SALES SUMMARY BY CUSTOMER  (SAP: VA05)")
    print(f"{'='*70}")
    print(f"  {'Customer ID':<12} {'Name':<24} {'Orders':>7} {'Qty':>8} {'Revenue':>14}")
    print(f"  {SEP}")
    total_rev = 0
    for cust_id, name, orders, qty, rev in rows:
        total_rev += rev or 0
        print(f"  {cust_id:<12} {name:<24} {orders:>7} {qty:>8} ₹{(rev or 0):>12,.2f}")
    print(f"  {SEP}")
    print(f"  {'TOTAL':>45} ₹{total_rev:>12,.2f}")
    print(f"{'='*70}\n")


def stock_report():
    """Current stock levels — mirrors SAP MMBE."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT material_id, description, stock_qty, uom FROM materials")
    rows = c.fetchall()
    conn.close()

    print(f"\n{'='*70}")
    print(f"  🏭  STOCK OVERVIEW  (SAP: MMBE — Plant PL01)")
    print(f"{'='*70}")
    print(f"  {'Material':<10} {'Description':<30} {'Stock':>8} {'UOM'}")
    print(f"  {SEP}")
    for mat_id, desc, qty, uom in rows:
        flag = "⚠️  LOW" if qty < 50 else "✅"
        print(f"  {mat_id:<10} {desc:<30} {qty:>8} {uom}  {flag}")
    print(f"{'='*70}\n")
