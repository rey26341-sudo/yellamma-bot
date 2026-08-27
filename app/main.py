import sqlite3
import datetime
import os
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from google import genai
from google.genai import types

app = FastAPI(title="Yellamma Multi-Tenant AI Booking Engine")

DB_PATH = "yellamma.dev.db"

class ChatRequest(BaseModel):
    business_id: Optional[str] = None
    tenant_slug: Optional[str] = None
    message: str
    session_id: Optional[str] = "default_user"

def get_tenant_info(slug: str):
    if not os.path.exists(DB_PATH):
        return None, []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    tenant = None
    services = []

    if "tenants" in tables:
        cursor.execute("SELECT id, name FROM tenants WHERE slug = ?", (slug,))
        tenant = cursor.fetchone()
        if not tenant:
            cursor.execute("SELECT id, name FROM tenants LIMIT 1")
            tenant = cursor.fetchone()

    if tenant and "services" in tables:
        tenant_id, tenant_name = tenant[0], tenant[1]
        cursor.execute("PRAGMA table_info(services);")
        columns = [col[1] for col in cursor.fetchall()]

        if "tenant_slug" in columns:
            cursor.execute("SELECT name, price, duration, description FROM services WHERE tenant_slug = ?", (slug,))
        elif "tenant_id" in columns:
            cursor.execute("SELECT name, price, duration, description FROM services WHERE tenant_id = ?", (tenant_id,))
        else:
            cursor.execute("SELECT name, price, duration, description FROM services")

        services = cursor.fetchall()

    conn.close()
    return tenant, services

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    slug = req.business_id or req.tenant_slug or "medical_clinic"
    tenant, services = get_tenant_info(slug)

    tenant_name = tenant[1] if tenant else slug.replace("_", " ").title()
    services_list_str = "\n".join([f"- {s[0]}: ${s[1]} ({s[2]} mins) - {s[3]}" for s in services]) if services else "General Consultation - $50 (30 mins)"

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    tomorrow_str = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    system_instruction = f"""
You are an AI booking assistant for '{tenant_name}'.
Today's date is: {today_str} (Tomorrow is {tomorrow_str}).

Available Services & Pricing:
{services_list_str}

Instructions:
1. Help the user schedule an appointment or answer questions about services.
2. If the user mentions symptoms (e.g., cold, fever, cough), recommend a General Consultation or suitable service.
3. Collect the following details to confirm a booking: Name, Phone Number, Service, Date, and Time.
4. Convert relative dates (e.g., "tomorrow") into exact dates (YYYY-MM-DD) relative to today ({today_str}).
5. Ask naturally for missing details.
"""

    raw_key = os.environ.get("GEMINI_API_KEY", "").strip().strip('"').strip("'")
    if not raw_key:
        print("[ERROR] GEMINI_API_KEY environment variable is empty!", file=sys.stderr)
        fallback_reply = "[API Key Missing] Please set GEMINI_API_KEY in your terminal environment."
        return {"reply": fallback_reply, "response": fallback_reply, "session_id": req.session_id}

    try:
        # Initialize Google GenAI client explicitly with key
        client = genai.Client(api_key=raw_key)
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=f"User Message: {req.message}",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2
            )
        )
        reply_text = response.text.strip()
        return {"reply": reply_text, "response": reply_text, "session_id": req.session_id}
    except Exception as e:
        print(f"[GEMINI API EXCEPTION] {e}", file=sys.stderr)
        fallback_reply = f"Error processing request: {str(e)}"
        return {"reply": fallback_reply, "response": fallback_reply, "session_id": req.session_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
