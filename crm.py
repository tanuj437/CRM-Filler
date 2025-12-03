import json
import os
import time
from json_repair import repair_json
from rapidfuzz import fuzz
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def normalize_records(records, id_field):
    """
    Converts dict-of-dicts → list-of-dicts.
    Leaves list-of-dicts unchanged.
    """
    if isinstance(records, dict):
        fixed = []
        for key, val in records.items():
            if id_field not in val:
                # Generate ID from key if missing
                val[id_field] = key
            fixed.append(val)
        return fixed

    if isinstance(records, list):
        return records

    return []

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def load_companies(path="existing_companies.json"):
    data = load_json(path)
    return normalize_records(data, "company_id")

def load_contacts(path="existing_contacts.json"):
    data = load_json(path)
    return normalize_records(data, "contact_id")

def load_deals(path="previous_deals.json"):
    data = load_json(path)
    return normalize_records(data, "deal_id")

def load_meetings(path="previous_meetings.json"):
    data = load_json(path)
    return normalize_records(data, "meeting_id")
def extract_json(raw_text: str):
    if not raw_text:
        return {}

    try:
        return json.loads(raw_text)
    except:
        pass

    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start != -1 and end != -1:
        candidate = raw_text[start:end+1]
    else:
        candidate = raw_text

    try:
        fixed = repair_json(candidate)
        return json.loads(fixed)
    except:
        print("JSON extraction failed.")
        return {}
def generate_crm_update(prompt_text: str) -> str:
    system_msg = (
        "You are an enterprise CRM assistant. "
        "Return ONLY a valid JSON object. No explanation. No markdown."
    )

    response_text = ""

    with client.responses.stream(
        model="gpt-5.1",
        input=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt_text}
        ],
        temperature=0.0,
        max_output_tokens=20000
    ) as stream:

        for event in stream:
            if event.type == "response.output_text.delta":
                response_text += event.delta

    return response_text
def generate_with_retries(prompt_text, retries=3):
    for attempt in range(1, retries+1):
        print(f"[CRM] Attempt {attempt}")
        raw = generate_crm_update(prompt_text)
        data = extract_json(raw)

        if isinstance(data, dict) and "actions" in data:
            print("[CRM] Success")
            return data

        print("[CRM] Invalid JSON, retrying…")
        time.sleep(1)

    return {"contacts": [], "companies": [], "deals": [], "actions": []}
def find_company(companies, company_name):
    target = company_name.lower().strip()
    best = None
    best_score = 0

    for comp in companies:
        score = fuzz.token_set_ratio(target, comp["name"].lower())
        if score > best_score:
            best_score = score
            best = comp

    return best if best_score >= 80 else None
def find_contacts(contacts, contact_name, company_id=None):
    target = contact_name.lower()
    results = []

    for c in contacts:
        if company_id and c.get("company_id") == company_id:
            results.append(c)
        if fuzz.token_set_ratio(target, c["name"].lower()) > 80:
            results.append(c)

    unique = {c["contact_id"]: c for c in results}.values()
    return list(unique)[:3]

def find_recent_deals(existing_deals, company_name):
    deals = [d for d in existing_deals if d.get("company_name") == company_name]
    return deals[-3:]
def find_previous_meetings(existing_meetings, company_name):
    meets = [m for m in existing_meetings if m.get("company_name") == company_name]
    return meets[-3:]
def get_crm_context(meeting_company_name,
                    meeting_contact_name,
                    CRM_COMPANIES,
                    CRM_CONTACTS,
                    CRM_DEALS,
                    CRM_MEETINGS):

    company = find_company(CRM_COMPANIES, meeting_company_name)
    company_name = company.get("name") if company else None

    contacts = find_contacts(CRM_CONTACTS, meeting_contact_name,
                             company.get("company_id") if company else None)

    deals = find_recent_deals(CRM_DEALS, company_name) if company_name else []
    meetings = find_previous_meetings(CRM_MEETINGS, company_name) if company_name else []

    return company, contacts, deals, meetings
def build_crm_prompt(
    meeting_notes,
    existing_contacts,
    existing_company,
    previous_deals,
    previous_meetings
):
    return f"""
You are an intelligent CRM extraction assistant.
Return ONLY valid JSON. No explanations.

EXISTING CONTACTS:
{json.dumps(existing_contacts, indent=2)}

EXISTING COMPANY:
{json.dumps(existing_company, indent=2)}

PREVIOUS DEALS:
{json.dumps(previous_deals, indent=2)}

PREVIOUS MEETINGS:
{json.dumps(previous_meetings, indent=2)}

NEW MEETING:
{meeting_notes}

JSON SCHEMA:
{{
  "contacts":[{{"temp_id":"c1","existing_id":null,"name":"string","job_title":"string",
    "email":"string","phone":"string","decision_power":"yes/no/maybe/Unknown"}}],

  "companies":[{{"temp_id":"co1","existing_id":null,"name":"string","industry":"string",
    "size":"string","location":"string"}}],

  "deals":[{{"temp_id":"d1","existing_id":null,"name":"string","value":"number or Unknown",
    "currency":"string","stage":"string","timeline":"string","next_steps":"string",
    "competitors":["string"]}}],

  "actions":[{{"entity":"contact/company/deal","operation":"create/update",
    "target_temp_id":"c1/co1/d1","reason":"string"}}]
}}
"""
def process_meeting(
    meeting_summary,
    meeting_company_name,
    meeting_contact_name,
    CRM_COMPANIES,
    CRM_CONTACTS,
    CRM_DEALS,
    CRM_MEETINGS
):
    company, contacts, deals, meetings = get_crm_context(
        meeting_company_name,
        meeting_contact_name,
        CRM_COMPANIES,
        CRM_CONTACTS,
        CRM_DEALS,
        CRM_MEETINGS
    )

    prompt = build_crm_prompt(
        meeting_summary,
        contacts,
        company,
        deals,
        meetings
    )

    return generate_with_retries(prompt)
def next_id(prefix, existing_list, id_field):
    nums = []
    for item in existing_list:
        if id_field in item:
            try:
                nums.append(int(item[id_field].split("-")[1]))
            except:
                pass
    new_number = max(nums or [2000]) + 1
    return f"{prefix}-{new_number}"
def apply_actions(gpt_json,
                  companies_path="existing_companies.json",
                  contacts_path="existing_contacts.json",
                  deals_path="previous_deals.json"):

    companies = load_companies(companies_path)
    contacts  = load_contacts(contacts_path)
    deals     = load_deals(deals_path)

    temp_map = {}

    # ---------- COMPANIES ----------
    for co in gpt_json["companies"]:
        temp = co["temp_id"]
        if co["existing_id"] is None:
            new_id = next_id("CO", companies, "company_id")
            new_co = {
                "company_id": new_id,
                "name": co["name"],
                "industry": co["industry"],
                "size": co["size"],
                "location": co["location"]
            }
            companies.append(new_co)
            temp_map[temp] = new_id
        else:
            for c in companies:
                if c["company_id"] == co["existing_id"]:
                    c.update({
                        "name": co["name"],
                        "industry": co["industry"],
                        "size": co["size"],
                        "location": co["location"]
                    })
                    temp_map[temp] = co["existing_id"]

    # ---------- CONTACTS ----------
    for ct in gpt_json["contacts"]:
        temp = ct["temp_id"]
        if ct["existing_id"] is None:
            new_id = next_id("C", contacts, "contact_id")
            new_contact = {
                "contact_id": new_id,
                "name": ct["name"],
                "job_title": ct["job_title"],
                "email": ct["email"],
                "phone": ct["phone"],
                "decision_power": ct["decision_power"],
                "company_id": temp_map.get("co1")
            }
            contacts.append(new_contact)
            temp_map[temp] = new_id
        else:
            for c in contacts:
                if c["contact_id"] == ct["existing_id"]:
                    c.update({
                        "name": ct["name"],
                        "job_title": ct["job_title"],
                        "email": ct["email"],
                        "phone": ct["phone"],
                        "decision_power": ct["decision_power"]
                    })
                    temp_map[temp] = ct["existing_id"]

    # ---------- DEALS ----------
    for dl in gpt_json["deals"]:
        temp = dl["temp_id"]
        if dl["existing_id"] is None:
            new_id = next_id("D", deals, "deal_id")
            new_deal = {
                "deal_id": new_id,
                "company_name": gpt_json["companies"][0]["name"],
                "deal_name": dl["name"],
                "value": dl["value"],
                "currency": dl["currency"],
                "stage": dl["stage"],
                "timeline": dl["timeline"],
                "next_steps": dl["next_steps"],
                "competitors": dl["competitors"]
            }
            deals.append(new_deal)
            temp_map[temp] = new_id
        else:
            for d in deals:
                if d["deal_id"] == dl["existing_id"]:
                    d.update({
                        "deal_name": dl["name"],
                        "value": dl["value"],
                        "currency": dl["currency"],
                        "stage": dl["stage"],
                        "timeline": dl["timeline"],
                        "next_steps": dl["next_steps"],
                        "competitors": dl["competitors"]
                    })
                    temp_map[temp] = dl["existing_id"]

    # SAVE FIXED BACK
    save_json(companies_path, companies)
    save_json(contacts_path, contacts)
    save_json(deals_path, deals)

    return temp_map
if __name__ == "__main__":
    CRM_COMPANIES = load_companies("existing_companies.json")
    CRM_CONTACTS  = load_contacts("existing_contacts.json")
    CRM_DEALS     = load_deals("previous_deals.json")
    CRM_MEETINGS  = load_meetings("previous_meetings.json")


    meeting_text = '''
        Ravi (CIO):

“Thanks for joining. Before we finalize the new IT services budget, I want clarity on what flexibility we have for infrastructure upgrades—especially cloud expansion, cybersecurity, and the new automation initiatives. We can’t postpone them anymore.”

Anita (CFO):

“Understood. From a finance standpoint, we have a tentative allocation increase of 8–10% year-over-year, but we need stronger justification. Last year we overshot spending due to unexpected cloud consumption and vendor escalations. So, break down which items are mandatory vs optional.”

Sonal (Compliance Head):

“Mandatory increases will come from compliance needs alone.
We have:

New data residency requirements

Updated cyber audit mandates

Vendor risk management tightening

The upcoming Digital Personal Data Protection (DPDP) Act enforcement timelines

Non-compliance could cost more than upgrades. So cybersecurity and data governance tools can’t be classified as optional.”

Karan (Political Analyst):

“Adding context: The political landscape is shifting this year.

The government is pushing aggressive digital governance initiatives.

Expect stricter IT compliance rules, especially for companies handling customer data.

There’s also budget pressure on the central government, so policies may favor automation and cost-efficiency technologies.

This indirectly affects your IT budget—invest in automation early before regulations force the change at a higher cost.”

Ravi (CIO):

“Exactly my point. If regulations are tightening, we should invest proactively. Our IT services roadmap includes:

Zero-trust cybersecurity rollout

Migration of 40% remaining services to cloud

Internal AI-based monitoring tools

Compliance automation platforms

Disaster recovery site expansion

These aren’t luxury items—they’re risk mitigation.”

Anita (CFO):

“Ravi, those items total nearly a 22% budget increase, not 10%.
We can stretch to maybe 14–15%, but only if you justify ROI clearly. Why not phase the migration over two years?”

Ravi (CIO):

“Phasing increases long-term cost. Cloud vendors give better pricing with bundled commitments.
Plus, if cyber incidents rise—and they will—it’s cheaper to harden now.”

Sonal (Compliance Head):

“I’ll support that. Also:

The certification audits coming in Q3 will penalize outdated infra.

Manual audit work is not scalable; we need digital audit tools.

We’ll face regulatory disclosure pressure after June.

If we don’t modernize by then, our risk score worsens.”

Karan (Political Analyst):

“And don’t forget: Elections next year mean unpredictable shifts.
Two possibilities:

Pro-business, pro-digitization policies → incentives for cloud and automation

Protective, regulatory-heavy policies → mandatory tech upgrades

In both scenarios, under-investing in IT puts us behind competitors.”

Anita (CFO):

“Fair point. I need a revised document:

Separate ‘compliance-driven must-haves’

‘Operational efficiency improvements’

‘Innovation items’

If we package them strategically, I can negotiate for a higher internal budget allocation.”

Ravi (CIO):

“Done. I’ll also show how cloud and cybersecurity investments reduce long-term costs and avoid compliance penalties.”

Sonal (Compliance Head):

“And I’ll map each tech initiative to specific compliance clauses—DPDP, ISO 27001, SOC2—so the board understands the regulatory reasoning.”

Karan (Political Analyst):

“I’ll add a short political-risk note for the board package: how upcoming policy changes may impact IT cost structures and why planning ahead is smarter.”

Anita (CFO):

“Perfect. Let’s aim to finalize the revised IT budget by Monday.”
    '''
    
    result = process_meeting(
        meeting_text,
        "Mercury Consulting",
        "Liu Wei",
        CRM_COMPANIES,
        CRM_CONTACTS,
        CRM_DEALS,
        CRM_MEETINGS
    )

    print("GPT RESULT:")
    print(json.dumps(result, indent=2))

    temp_map = apply_actions(result)
    print("TEMP → REAL ID MAP:")
    print(temp_map)
