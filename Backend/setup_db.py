import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "police.db")

def setup():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fir_number TEXT,
            complainant_name TEXT,
            complaint_type TEXT,
            status TEXT,
            station TEXT,
            date_filed TEXT
        )
    """)

    sample_data = [
        ("FIR1001", "Ramesh Kumar", "Theft", "Pending", "Tadepalligudem PS", "2026-06-01"),
        ("FIR1002", "Sita Devi", "Cyber Fraud", "Under Investigation", "Vijayawada PS", "2026-06-03"),
        ("FIR1003", "Anil Reddy", "Assault", "Closed", "Tadepalligudem PS", "2026-06-05"),
        ("FIR1004", "Lakshmi N", "Missing Person", "Pending", "Guntur PS", "2026-06-07"),
        ("FIR1005", "Suresh Babu", "Theft", "Closed", "Vijayawada PS", "2026-06-10"),
        ("FIR1006", "Priya Sharma", "Cyber Fraud", "Pending", "Bengaluru City PS", "2026-06-12"),
        ("FIR1007", "Manoj Kumar", "Domestic Dispute", "Under Investigation", "Tadepalligudem PS", "2026-06-14"),
        ("FIR1008", "Kavya R", "Theft", "Pending", "Bengaluru City PS", "2026-06-16"),
        ("FIR1009", "Vijay Singh", "Assault", "Closed", "Guntur PS", "2026-06-18"),
        ("FIR1010", "Deepa M", "Missing Person", "Under Investigation", "Vijayawada PS", "2026-06-20"),
    ]

    cur.executemany("""
        INSERT INTO complaints (fir_number, complainant_name, complaint_type, status, station, date_filed)
        VALUES (?, ?, ?, ?, ?, ?)
    """, sample_data)

    conn.commit()
    conn.close()
    print(f"Database created at {DB_PATH} with {len(sample_data)} sample records.")

if __name__ == "__main__":
    setup()
