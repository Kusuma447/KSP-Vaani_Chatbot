import sqlite3
import os
import re
import json
import requests

DB_PATH = os.path.join(os.path.dirname(__file__), "police.db")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"

conversation_memory = {}

SCHEMA_DESCRIPTION = """
Table: complaints
Columns:
  id (integer)
  fir_number (text, e.g. 'FIR1001')
  complainant_name (text)
  complaint_type (text, one of: Theft, Cyber Fraud, Assault, Missing Person, Domestic Dispute)
  status (text, one of: Pending, Under Investigation, Closed)
  station (text, e.g. 'Tadepalligudem PS', 'Vijayawada PS', 'Guntur PS', 'Bengaluru City PS')
  date_filed (text, format YYYY-MM-DD)
"""


def ask_gemini_for_sql(question: str, memory_hint: str = ""):
    prompt = f"""You are a text-to-SQL engine for a police complaints database.

{SCHEMA_DESCRIPTION}

The user may ask in English or Kannada. Convert their question into a single
valid SQLite SELECT query against the `complaints` table only.
Rules:
- Only generate SELECT statements. Never INSERT, UPDATE, DELETE, or DROP.
- If the question references dates like "last week" or "this month", use SQLite date functions relative to '2026-07-21' as today's date.
- If the question is a follow-up / vague and this context is available, use it: {memory_hint}
- Respond with ONLY the raw SQL query, no explanation, no markdown, no backticks.

User question: {question}
SQL query:"""

    try:
        resp = requests.post(
            GEMINI_URL,
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=15
        )
        result = resp.json()
        if "candidates" not in result:
            return f"-- GEMINI_ERROR: {json.dumps(result)}"
        sql = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        sql = sql.replace("```sql", "").replace("```", "").strip()
        return sql
    except Exception as e:
        return f"-- GEMINI_EXCEPTION: {str(e)}"


def is_safe_select(sql: str) -> bool:
    s = sql.strip().lower()
    if not s.startswith("select"):
        return False
    forbidden = ["insert", "update", "delete", "drop", "alter", "attach", ";--", "pragma"]
    return not any(word in s for word in forbidden)


def run_sql(sql: str, session_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql)
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def handler(context, basicio):
    query_text = basicio.get_argument("text") or ""
    session_id = basicio.get_argument("session_id") or "default"

    memory_hint = conversation_memory.get(session_id, "")

    sql = ask_gemini_for_sql(query_text, memory_hint)

    if sql and sql.startswith("-- GEMINI"):
        sql = "SELECT * FROM complaints LIMIT 5"

    if not sql or not is_safe_select(sql):
        explanation = f"Couldn't confidently interpret that question — showing recent complaints instead. DEBUG raw output was: {sql}"
        sql = "SELECT * FROM complaints LIMIT 5"
    else:
        explanation = "Interpreted your question and ran a matching database query."
        conversation_memory[session_id] = query_text

    try:
        rows = run_sql(sql, session_id)
    except Exception as e:
        rows = []
        explanation = f"Query failed to execute: {str(e)}"

    response = {
        "input_text": query_text,
        "generated_sql": sql,
        "explanation": explanation,
        "results": rows,
        "result_count": len(rows)
    }

    basicio.write(json.dumps(response, ensure_ascii=False))
    context.close()