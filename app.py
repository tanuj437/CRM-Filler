import gradio as gr
import json

# Import all backend CRM logic from crm.py
from crm import (
    load_companies, load_contacts, load_deals, load_meetings,
    process_meeting, apply_actions
)


# ============================================================
# FUNCTION 1 — RUN GPT EXTRACTION
# ============================================================
def run_extraction(meeting_text, company_name, contact_name):

    # Load CRM databases
    CRM_COMPANIES = load_companies()
    CRM_CONTACTS  = load_contacts()
    CRM_DEALS     = load_deals()
    CRM_MEETINGS  = load_meetings()

    # Run extraction pipeline
    result = process_meeting(
        meeting_text,
        company_name,
        contact_name,
        CRM_COMPANIES,
        CRM_CONTACTS,
        CRM_DEALS,
        CRM_MEETINGS
    )

    return json.dumps(result, indent=2)


# ============================================================
# FUNCTION 2 — APPLY ACTIONS TO CRM JSON FILES
# ============================================================
def run_apply(gpt_json_text):

    # Gradio JSON component returns dict, not string
    if isinstance(gpt_json_text, dict):
        gpt_json = gpt_json_text
    else:
        # If it's text, attempt to parse
        try:
            gpt_json = json.loads(gpt_json_text)
        except:
            return "❌ Invalid JSON format", ""

    if not gpt_json:
        return "❌ No extraction JSON provided", ""

    # Apply CRM updates
    temp_map = apply_actions(gpt_json)

    updated_state = {
        "companies": load_companies(),
        "contacts":  load_contacts(),
        "deals":     load_deals(),
        "meetings":  load_meetings()
    }

    return (
        temp_map,                # ID mapping
        updated_state            # updated CRM database
    )



# ============================================================
# GRADIO UI
# ============================================================

with gr.Blocks(title="CRM Data Filler Agent") as demo:

    gr.Markdown("""
    # 💼 CRM Data Filler Agent  
    Paste your meeting notes, and the AI will extract **Contacts**, **Companies**, **Deals**  
    and automatically update your CRM JSON files.
    """)

    with gr.Row():
        meeting_text = gr.Textbox(label="Meeting Summary", lines=20, placeholder="Paste meeting text here...")
        with gr.Column():
            company_name = gr.Textbox(label="Company Mentioned in Meeting")
            contact_name = gr.Textbox(label="Primary Contact Name")

    btn_extract = gr.Button("🔍 Extract CRM Entities")
    extraction_output = gr.JSON(label="Extracted CRM JSON")

    btn_apply = gr.Button("💾 Apply to CRM (Update JSON Files)")
    id_mapping_output = gr.JSON(label="Temp → Real ID Mapping")
    updated_crm_output = gr.JSON(label="Updated CRM State")

    # BUTTON EVENTS
    btn_extract.click(
        run_extraction,
        inputs=[meeting_text, company_name, contact_name],
        outputs=[extraction_output]
    )

    btn_apply.click(
        run_apply,
        inputs=[extraction_output],
        outputs=[id_mapping_output, updated_crm_output]
    )


demo.launch()
