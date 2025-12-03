import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import traceback

# Import your CRM logic from crm.py
from crm import (
    load_companies, load_contacts, load_deals, load_meetings,
    process_meeting, apply_actions
)

# -------------------------------------------------------
# Logging Setup
# -------------------------------------------------------
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("crm-server")

app = FastAPI(title="Automated Data Filler Agent API")

# CORS – allow your HTML frontend to call FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Allow all (or specify your domain)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# -------------------------------------------------------
# Pydantic Models
# -------------------------------------------------------
class ExtractRequest(BaseModel):
    meeting_text: str
    company_name: Optional[str] = "Unknown"
    contact_name: Optional[str] = "Unknown"


class ApplyRequest(BaseModel):
    gpt_json: Dict[str, Any]   # contact/company/deal arrays


# -------------------------------------------------------
# HELPERS
# -------------------------------------------------------

def convert_frontend_payload_to_gpt(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert your frontend format:
      crmData = { contact: [...], company: [...], deal: [...] }
    into GPT-style schema used by apply_actions().
    """
    out = {"contacts": [], "companies": [], "deals": [], "actions": []}

    contacts = payload.get("contact", [])
    companies = payload.get("company", [])
    deals = payload.get("deal", [])

    # ---------------- COMPANIES ----------------
    for i, c in enumerate(companies, start=1):
        out["companies"].append({
            "temp_id": f"co{i}",
            "existing_id": None,
            "name": c.get("name", ""),
            "industry": c.get("industry", ""),
            "size": c.get("size", ""),
            "location": c.get("location", "")
        })

    # ---------------- CONTACTS ----------------
    for i, c in enumerate(contacts, start=1):
        out["contacts"].append({
            "temp_id": f"c{i}",
            "existing_id": None,
            "name": c.get("name", ""),
            "job_title": c.get("job_title", ""),
            "email": c.get("email", ""),
            "phone": c.get("phone", ""),
            "decision_power": c.get("decision_power", "Unknown")
        })

    # ---------------- DEALS ----------------
    for i, d in enumerate(deals, start=1):
        competitors = d.get("competitors", "")
        if isinstance(competitors, str):
            competitors = [x.strip() for x in competitors.split(",") if x.strip()]

        out["deals"].append({
            "temp_id": f"d{i}",
            "existing_id": None,
            "name": d.get("name", ""),
            "value": d.get("value", ""),
            "currency": d.get("currency", ""),
            "stage": d.get("stage", ""),
            "timeline": d.get("timeline", ""),
            "next_steps": d.get("next_steps", ""),
            "competitors": competitors
        })

    # Default "create" actions
    for c in out["contacts"]:
        out["actions"].append({
            "entity": "contact",
            "operation": "create",
            "target_temp_id": c["temp_id"],
            "reason": "Imported from frontend"
        })

    for co in out["companies"]:
        out["actions"].append({
            "entity": "company",
            "operation": "create",
            "target_temp_id": co["temp_id"],
            "reason": "Imported from frontend"
        })

    for d in out["deals"]:
        out["actions"].append({
            "entity": "deal",
            "operation": "create",
            "target_temp_id": d["temp_id"],
            "reason": "Imported from frontend"
        })

    return out


# -------------------------------------------------------
# EXTRACT ENDPOINT   (HTML → GPT extraction)
# -------------------------------------------------------
@app.post("/extract")
async def extract(req: ExtractRequest):

    meeting_text = req.meeting_text.strip()
    if not meeting_text:
        raise HTTPException(status_code=400, detail="Meeting summary is empty")

    log.info("Running extraction…")

    try:
        result = process_meeting(
            meeting_text,
            req.company_name or "Unknown",
            req.contact_name or "Unknown",
            load_companies(),
            load_contacts(),
            load_deals(),
            load_meetings()
        )
    except Exception as e:
        log.error("process_meeting failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail="LLM extraction failed")

    return {"extracted": result}


# -------------------------------------------------------
# APPLY ENDPOINT   (HTML → Apply to CRM JSON files)
# -------------------------------------------------------
@app.post("/apply")
async def apply(req: ApplyRequest):

    incoming = req.gpt_json

    # Convert HTML CRM table → GPT schema
    gpt_payload = convert_frontend_payload_to_gpt(incoming)

    try:
        temp_map = apply_actions(gpt_payload)
    except Exception as e:
        log.error("apply_actions failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail="CRM update failed")

    updated_state = {
        "companies": load_companies(),
        "contacts": load_contacts(),
        "deals": load_deals(),
        "meetings": load_meetings()
    }

    return {"mapping": temp_map, "crm_state": updated_state}


# -------------------------------------------------------
# CRM STATE ENDPOINT
# -------------------------------------------------------
@app.get("/crm-state")
async def crm_state():
    return {
        "companies": load_companies(),
        "contacts": load_contacts(),
        "deals": load_deals(),
        "meetings": load_meetings()
    }
