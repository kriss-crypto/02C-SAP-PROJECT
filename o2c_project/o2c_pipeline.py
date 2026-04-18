"""
o2c_pipeline.py — TechNova Electronics
Implements all 6 O2C steps as Python functions mirroring SAP SD transactions.
"""
import sqlite3, uuid, datetime
from database import get_conn, DB_PATH

def _gen_id(prefix):
    return f"{prefix}-{str(uuid.uuid4())[:8].upper()}"

def _today(offset_days=0):
    d = datetime.date.today() + datetime.timedelta(days=offset_days)
    return d.strftime("%Y-%m-%d")

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — INQUIRY  (SAP T-Code: VA11)
# ═══════════════════════════════════════════════════════════════════════════════
def create_inquiry(customer_id, material_id, quantity, req_del_date=None):
    """
    Create a Pre-Sales Inquiry document.
    Mirrors SAP VA11 — checks customer and material existence.
    """
    conn = get_conn()
    c = conn.cursor()

    # Validate customer
    c.execute("SELECT name, credit_limit FROM customers WHERE customer_id=?", (customer_id,))
    cust = c.fetchone()
    if not cust:
        conn.close()
        raise ValueError(f"❌  Customer {customer_id} not found.")

    # Validate material & ATP check
    c.execute("SELECT description, stock_qty FROM materials WHERE material_id=?", (material_id,))
    mat = c.fetchone()
    if not mat:
        conn.close()
        raise ValueError(f"❌  Material {material_id} not found.")

    atp_status = "✅ AVAILABLE" if mat[1] >= quantity else "⚠️  PARTIAL STOCK"

    inquiry_id  = _gen_id("INQ")
    del_date    = req_del_date or _today(10)

    c.execute("""INSERT INTO inquiries
                 (inquiry_id, customer_id, material_id, quantity, req_del_date)
                 VALUES (?,?,?,?,?)""",
              (inquiry_id, customer_id, material_id, quantity, del_date))
    conn.commit()
    conn.close()

    print(f"\n{'='*55}")
    print(f"  STEP 1 — INQUIRY CREATED  [VA11]")
    print(f"{'='*55}")
    print(f"  Inquiry ID    : {inquiry_id}")
    print(f"  Customer      : {customer_id} — {cust[0]}")
    print(f"  Material      : {material_id} — {mat[0]}")
    print(f"  Quantity      : {quantity} EA")
    print(f"  Req. Del. Date: {del_date}")
    print(f"  ATP Check     : {atp_status} (Stock: {mat[1]} EA)")
    print(f"{'='*55}")
    return inquiry_id


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — QUOTATION  (SAP T-Code: VA21)
# ═══════════════════════════════════════════════════════════════════════════════
def create_quotation(inquiry_id, valid_days=7):
    """
    Create a Quotation from an Inquiry.
    Applies pricing procedure RVAA01: Base Price → Discount (5%) → GST (18%).
    Mirrors SAP VA21.
    """
    conn = get_conn()
    c = conn.cursor()

    c.execute("""SELECT i.*, m.unit_price, m.description, cu.name
                 FROM inquiries i
                 JOIN materials m  ON i.material_id  = m.material_id
                 JOIN customers cu ON i.customer_id  = cu.customer_id
                 WHERE i.inquiry_id=? AND i.status='OPEN'""", (inquiry_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"❌  Inquiry {inquiry_id} not found or not OPEN.")

    _, cust_id, mat_id, qty, del_date, created, _, unit_price, mat_desc, cust_name = row

    # Pricing calculation (RVAA01)
    base_amount    = unit_price * qty
    discount_amt   = base_amount * 0.05          # K007 — 5% discount
    after_discount = base_amount - discount_amt
    gst_amt        = after_discount * 0.18        # MWST — 18% GST
    gross_amount   = after_discount + gst_amt

    quotation_id = _gen_id("QT")
    valid_from   = _today()
    valid_to     = _today(valid_days)

    c.execute("""INSERT INTO quotations
                 (quotation_id, inquiry_id, customer_id, material_id, quantity,
                  unit_price, discount_pct, gst_pct, net_amount, gross_amount,
                  valid_from, valid_to)
                 VALUES (?,?,?,?,?,?,5.0,18.0,?,?,?,?)""",
              (quotation_id, inquiry_id, cust_id, mat_id, qty,
               unit_price, after_discount, gross_amount, valid_from, valid_to))

    c.execute("UPDATE inquiries SET status='QUOTED' WHERE inquiry_id=?", (inquiry_id,))
    conn.commit()
    conn.close()

    print(f"\n{'='*55}")
    print(f"  STEP 2 — QUOTATION CREATED  [VA21]")
    print(f"{'='*55}")
    print(f"  Quotation ID  : {quotation_id}")
    print(f"  Customer      : {cust_id} — {cust_name}")
    print(f"  Material      : {mat_id} — {mat_desc}")
    print(f"  Quantity      : {qty} EA")
    print(f"  Unit Price    : ₹{unit_price:,.2f}  (PR00)")
    print(f"  Discount (5%) : -₹{discount_amt:,.2f}  (K007)")
    print(f"  Net Amount    : ₹{after_discount:,.2f}")
    print(f"  GST (18%)     : +₹{gst_amt:,.2f}  (MWST)")
    print(f"  Gross Amount  : ₹{gross_amount:,.2f}")
    print(f"  Validity      : {valid_from} to {valid_to}")
    print(f"{'='*55}")
    return quotation_id


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — SALES ORDER  (SAP T-Code: VA01)
# ═══════════════════════════════════════════════════════════════════════════════
def create_sales_order(quotation_id):
    """
    Create a Sales Order from accepted Quotation.
    Runs credit check and ATP confirmation.
    Mirrors SAP VA01.
    """
    conn = get_conn()
    c = conn.cursor()

    c.execute("""SELECT q.*, cu.credit_limit, cu.name, m.stock_qty, m.description
                 FROM quotations q
                 JOIN customers cu ON q.customer_id = cu.customer_id
                 JOIN materials  m  ON q.material_id  = m.material_id
                 WHERE q.quotation_id=? AND q.status='SENT'""", (quotation_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"❌  Quotation {quotation_id} not found or already processed.")

    (qt_id, inq_id, cust_id, mat_id, qty, unit_price,
     disc_pct, gst_pct, net_amt, gross_amt,
     vf, vt, created, _, credit_limit, cust_name, stock_qty, mat_desc) = row

    # Credit check (CC01)
    credit_status = "APPROVED" if gross_amt <= credit_limit else "BLOCKED"

    # ATP check
    atp_ok = stock_qty >= qty

    order_id = _gen_id("SO")
    del_date = _today(7)

    c.execute("""INSERT INTO sales_orders
                 (order_id, quotation_id, customer_id, material_id, quantity,
                  unit_price, discount_pct, gst_pct, net_amount, gross_amount,
                  req_del_date, credit_status)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
              (order_id, quotation_id, cust_id, mat_id, qty,
               unit_price, disc_pct, gst_pct, net_amt, gross_amt,
               del_date, credit_status))

    c.execute("UPDATE quotations SET status='ORDERED' WHERE quotation_id=?", (quotation_id,))
    conn.commit()
    conn.close()

    print(f"\n{'='*55}")
    print(f"  STEP 3 — SALES ORDER CREATED  [VA01]")
    print(f"{'='*55}")
    print(f"  Sales Order ID : {order_id}")
    print(f"  Customer       : {cust_id} — {cust_name}")
    print(f"  Material       : {mat_id} — {mat_desc}")
    print(f"  Quantity       : {qty} EA")
    print(f"  Gross Amount   : ₹{gross_amt:,.2f}")
    print(f"  Credit Check   : {'✅ ' + credit_status if credit_status=='APPROVED' else '❌ ' + credit_status}")
    print(f"  ATP Check      : {'✅ CONFIRMED' if atp_ok else '⚠️  BACKORDER'} (Stock: {stock_qty})")
    print(f"  Req. Del. Date : {del_date}")
    print(f"{'='*55}")

    if credit_status == "BLOCKED":
        raise Exception(f"🚫  Sales Order {order_id} BLOCKED — credit limit exceeded.")

    return order_id


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4 — OUTBOUND DELIVERY + GOODS ISSUE  (SAP T-Code: VL01N / VL02N)
# ═══════════════════════════════════════════════════════════════════════════════
def create_delivery(order_id):
    """
    Create Delivery and Post Goods Issue (PGI).
    Reduces stock in Materials table (MM movement type 601).
    Mirrors SAP VL01N + VL02N (PGI).
    """
    conn = get_conn()
    c = conn.cursor()

    c.execute("""SELECT so.*, m.stock_qty, m.description
                 FROM sales_orders so
                 JOIN materials m ON so.material_id = m.material_id
                 WHERE so.order_id=? AND so.status='OPEN'""", (order_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"❌  Sales Order {order_id} not found or not OPEN.")

    (ord_id, qt_id, cust_id, mat_id, qty, unit_price,
     disc_pct, gst_pct, net_amt, gross_amt,
     del_date, created, credit_st, _, stock_qty, mat_desc) = row

    if stock_qty < qty:
        conn.close()
        raise Exception(f"❌  Insufficient stock. Available: {stock_qty}, Required: {qty}")

    delivery_id = _gen_id("DL")
    actual_gi   = _today()

    c.execute("""INSERT INTO deliveries
                 (delivery_id, order_id, customer_id, material_id, quantity,
                  planned_gi, actual_gi, status)
                 VALUES (?,?,?,?,?,?,?,'GOODS_ISSUED')""",
              (delivery_id, ord_id, cust_id, mat_id, qty, del_date, actual_gi))

    # PGI — reduce stock (MM movement 601)
    c.execute("UPDATE materials SET stock_qty = stock_qty - ? WHERE material_id=?",
              (qty, mat_id))
    c.execute("UPDATE sales_orders SET status='DELIVERED' WHERE order_id=?", (ord_id,))
    conn.commit()

    # Check new stock level
    c.execute("SELECT stock_qty FROM materials WHERE material_id=?", (mat_id,))
    new_stock = c.fetchone()[0]
    conn.close()

    print(f"\n{'='*55}")
    print(f"  STEP 4 — DELIVERY + GOODS ISSUE  [VL01N/VL02N]")
    print(f"{'='*55}")
    print(f"  Delivery ID    : {delivery_id}")
    print(f"  Sales Order    : {ord_id}")
    print(f"  Material       : {mat_id} — {mat_desc}")
    print(f"  Quantity Issued: {qty} EA")
    print(f"  Shipping Point : SP01 — Main Dispatch Hub")
    print(f"  GI Date        : {actual_gi}")
    print(f"  MM Movement    : 601 (Goods Issue to Customer)")
    print(f"  Stock Before   : {stock_qty} EA  →  After: {new_stock} EA")
    print(f"  FI Entry       : COGS Dr / Inventory Cr  ✅")
    print(f"{'='*55}")
    return delivery_id


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5 — BILLING / INVOICE  (SAP T-Code: VF01)
# ═══════════════════════════════════════════════════════════════════════════════
def create_invoice(delivery_id):
    """
    Create Billing Document (Invoice F2) from Delivery.
    Auto-generates FI accounting entry (AR Dr / Revenue Cr).
    Mirrors SAP VF01.
    """
    conn = get_conn()
    c = conn.cursor()

    c.execute("""SELECT d.*, so.net_amount, so.gross_amount, so.gst_pct, m.description
                 FROM deliveries d
                 JOIN sales_orders so ON d.order_id   = so.order_id
                 JOIN materials    m  ON d.material_id = m.material_id
                 WHERE d.delivery_id=? AND d.status='GOODS_ISSUED'""", (delivery_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"❌  Delivery {delivery_id} not found or goods not issued.")

    (dl_id, ord_id, cust_id, mat_id, qty,
     ship_pt, planned_gi, actual_gi, _, created,
     net_amt, gross_amt, gst_pct, mat_desc) = row

    gst_amount   = net_amt * (gst_pct / 100)
    invoice_id   = _gen_id("INV")
    billing_date = _today()
    due_date     = _today(30)

    c.execute("""INSERT INTO invoices
                 (invoice_id, delivery_id, order_id, customer_id, material_id,
                  quantity, net_amount, gst_amount, gross_amount,
                  billing_date, due_date)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
              (invoice_id, dl_id, ord_id, cust_id, mat_id,
               qty, net_amt, gst_amount, gross_amt, billing_date, due_date))

    c.execute("UPDATE deliveries SET status='INVOICED' WHERE delivery_id=?", (dl_id,))
    conn.commit()
    conn.close()

    print(f"\n{'='*55}")
    print(f"  STEP 5 — BILLING / INVOICE  [VF01]")
    print(f"{'='*55}")
    print(f"  Invoice ID     : {invoice_id}")
    print(f"  Delivery       : {dl_id}")
    print(f"  Customer       : {cust_id}")
    print(f"  Material       : {mat_id} — {mat_desc}")
    print(f"  Quantity       : {qty} EA")
    print(f"  Net Amount     : ₹{net_amt:,.2f}")
    print(f"  GST (18%)      : ₹{gst_amount:,.2f}")
    print(f"  Gross Amount   : ₹{gross_amt:,.2f}")
    print(f"  Billing Date   : {billing_date}")
    print(f"  Due Date       : {due_date}")
    print(f"  FI Entry       : AR Dr ₹{gross_amt:,.2f} / Revenue Cr ₹{net_amt:,.2f} / GST Cr ₹{gst_amount:,.2f}  ✅")
    print(f"{'='*55}")
    return invoice_id


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 6 — PAYMENT RECEIPT  (SAP T-Code: F-28 / F-32)
# ═══════════════════════════════════════════════════════════════════════════════
def post_payment(invoice_id, amount_paid=None):
    """
    Post incoming payment and clear the open item in FI-AR.
    Mirrors SAP F-28 (Post Payment) + F-32 (Clear Open Items).
    """
    conn = get_conn()
    c = conn.cursor()

    c.execute("""SELECT i.*, cu.name
                 FROM invoices i
                 JOIN customers cu ON i.customer_id = cu.customer_id
                 WHERE i.invoice_id=? AND i.status='OPEN'""", (invoice_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"❌  Invoice {invoice_id} not found or already paid.")

    (inv_id, dl_id, ord_id, cust_id, mat_id, qty,
     net_amt, gst_amt, gross_amt, bill_date, due_date, created, _, cust_name) = row

    payment_amount = amount_paid or gross_amt
    payment_id     = _gen_id("PAY")
    payment_date   = _today()

    c.execute("""INSERT INTO payments
                 (payment_id, invoice_id, customer_id, amount_paid, payment_date)
                 VALUES (?,?,?,?,?)""",
              (payment_id, inv_id, cust_id, payment_amount, payment_date))

    c.execute("UPDATE invoices SET status='CLEARED' WHERE invoice_id=?", (inv_id,))
    conn.commit()
    conn.close()

    print(f"\n{'='*55}")
    print(f"  STEP 6 — PAYMENT RECEIPT  [F-28 / F-32]")
    print(f"{'='*55}")
    print(f"  Payment ID     : {payment_id}")
    print(f"  Invoice        : {inv_id}")
    print(f"  Customer       : {cust_id} — {cust_name}")
    print(f"  Amount Paid    : ₹{payment_amount:,.2f}")
    print(f"  Payment Date   : {payment_date}")
    print(f"  Bank Account   : TN01-MAIN-BANK")
    print(f"  AR Cleared     : ✅  Open item cleared")
    print(f"  FI Entry       : Bank Dr ₹{payment_amount:,.2f} / AR Cr ₹{payment_amount:,.2f}  ✅")
    print(f"{'═'*55}")
    print(f"  🎉  O2C CYCLE COMPLETE — Payment received & cleared!")
    print(f"{'═'*55}")
    return payment_id
