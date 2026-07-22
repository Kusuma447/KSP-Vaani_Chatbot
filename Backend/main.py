import sqlite3
import os
import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DB_PATH = os.path.join(os.path.dirname(__file__), "police.db")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    text: str
    session_id: str = "default"

conversation_memory = {}


def text_to_sql(text: str, session_id: str = "default"):
    t = text.lower()

    fir_match = re.search(r"fir\s*-?\s*(\d+)", t)
    if fir_match:
        fir_number = f"FIR{fir_match.group(1)}"
        return (
            "SELECT * FROM complaints WHERE fir_number = ?",
            (fir_number,),
            f"Looking up status for {fir_number}"
        )

    stations = ["tadepalligudem", "vijayawada", "guntur", "bengaluru"]
    for station in stations:
        if station in t:
            conversation_memory[session_id] = station
            return (
                "SELECT * FROM complaints WHERE LOWER(station) LIKE ?",
                (f"%{station}%",),
                f"Complaints filed at {station.title()} station"
            )

    if "pending" in t:
        return (
            "SELECT * FROM complaints WHERE status = 'Pending'",
            (),
            "All pending complaints"
        )
    if "closed" in t or "resolved" in t:
        return (
            "SELECT * FROM complaints WHERE status = 'Closed'",
            (),
            "All closed complaints"
        )
    if "investigation" in t:
        return (
            "SELECT * FROM complaints WHERE status = 'Under Investigation'",
            (),
            "All complaints under investigation"
        )

    types = ["theft", "cyber fraud", "assault", "missing person", "domestic dispute"]
    for c_type in types:
        if c_type in t:
            conversation_memory[session_id] = c_type
            return (
                "SELECT * FROM complaints WHERE LOWER(complaint_type) LIKE ?",
                (f"%{c_type}%",),
                f"Complaints of type: {c_type.title()}"
            )

    if "how many" in t or "count" in t or "total" in t:
        return (
            "SELECT COUNT(*) as total FROM complaints",
            (),
            "Total number of complaints on record"
        )

    remembered = conversation_memory.get(session_id)
    if remembered:
        return (
            "SELECT * FROM complaints WHERE LOWER(station) LIKE ? OR LOWER(complaint_type) LIKE ?",
            (f"%{remembered}%", f"%{remembered}%"),
            f"Continuing from your last question about '{remembered}'"
        )

    return (
        "SELECT * FROM complaints LIMIT 5",
        (),
        "Showing recent complaints (try mentioning an FIR number, station, status, or complaint type)"
    )


@app.post("/query")
def run_query(req: QueryRequest):
    sql, params, explanation = text_to_sql(req.text, req.session_id)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()

    return {
        "input_text": req.text,
        "generated_sql": sql,
        "explanation": explanation,
        "results": rows,
        "result_count": len(rows)
    }


@app.get("/")
def root():
    return {"status": "KSP Chatbot backend running"}