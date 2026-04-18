# TechNova Electronics — Order-to-Cash (O2C) System
### SAP SD Capstone Project | Krissh Kumar Singh | Roll: 2329124

---

## 📌 Project Overview
A Python + SQLite simulation of the complete SAP SD Order-to-Cash cycle
for a fictitious company **TechNova Electronics Pvt. Ltd.**

---

## 🗂️ Project Structure
```
o2c_project/
├── main.py           # Entry point — menu-driven CLI
├── database.py       # DB setup + master data seeding
├── o2c_pipeline.py   # All 6 O2C steps (mirrors SAP transactions)
├── reports.py        # Business reports (Doc Flow, AR Aging, Sales)
├── technova_o2c.db   # SQLite database (auto-created on first run)
└── README.md
```

---

## ⚙️ How to Run
```bash
python main.py
```
No external libraries needed — uses only Python standard library + SQLite.

---

## 🔄 O2C Process Flow

| Step | Description         | SAP T-Code     |
|------|---------------------|----------------|
| 1    | Inquiry             | VA11           |
| 2    | Quotation           | VA21           |
| 3    | Sales Order         | VA01           |
| 4    | Delivery + PGI      | VL01N / VL02N  |
| 5    | Billing / Invoice   | VF01           |
| 6    | Payment Receipt     | F-28 / F-32    |

---

## 📊 Reports Available
- Document Flow (VF03)
- AR Aging Report (FBL5N)
- Sales Summary (VA05)
- Stock Overview (MMBE)

---

## 🏢 Company Setup
- **Company:** TechNova Electronics Pvt. Ltd.
- **Company Code:** TN01
- **Sales Org:** SL01 | **Dist. Channel:** DI | **Division:** EL
- **Plant:** PL01 | **Shipping Point:** SP01
- **Pricing Procedure:** RVAA01 (Base + 5% Discount + 18% GST)
