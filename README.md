
---

# 📌 CRM Intelligence Project — README

## 📖 Overview

This project implements a lightweight *CRM (Customer Relationship Management) dataset system* using structured JSON files and a notebook (main.ipynb). The data represents companies, business contacts, sales meetings, and deal pipelines, allowing analytical workflows for:

* Lead prioritization
* Deal tracking
* Meeting intelligence
* Contact qualification
* Competitor mapping

The primary objective is to provide a *single source of truth* for business-to-business (B2B) revenue operations.

---

## 🗂 Project Structure

### ✔ Data Files

| File                      | Purpose                                                                               |
| ------------------------- | ------------------------------------------------------------------------------------- |
| existing_companies.json | Master list of companies with industry, size, and location.                           |
| existing_contacts.json  | Contact directory including job roles, communication details, and decision authority. |
| previous_deals.json     | Deal pipeline with value, stage, competitor landscape, and next steps.                |
| previous_meetings.json  | Meeting intelligence history linked to deals, summaries, and outcomes.                |
| main.ipynb              | Notebook to process, analyze, and visualize CRM data.                                 |

---

## 🧾 Data Model Summary

### 🏢 Companies

Stored in existing_companies.json, each company entry includes:

* Name
* Industry
* Size
* Location
* Company ID

Example entry:

* Mercury Consulting, Energy sector, SMB, Berlin, Germany 

---

### 👤 Contacts

Stored in existing_contacts.json, each contact entry includes:

* Name
* Job Title
* Company Name
* Email / Phone
* Decision Power Score (yes, maybe, no, unknown)

Example insight:

* Many recurring names across companies (e.g., *Liu Wei, **Maya Patel, **Omar Khalid*).
* Key decision-makers typically have titles like CTO, VP Product, Head of Sales. 

---

### 💼 Deals

Stored in previous_deals.json, each record includes:

* Deal Name
* Deal Value & Currency
* Stage (Discovery, Proposal, Negotiation, ClosedWon, etc.)
* Competitors
* Next Steps

Example deal properties:

* Deal *D-3005* (Mercury Consulting — Engineering Manager) valued at *EUR 1,803,301, stage: **Demo, competitor: **Marketo*. 

---

### 🤝 Meeting History

Stored in previous_meetings.json, each meeting entry contains:

* Timestamp
* Summary narrative
* Outcome
* Linked deal ID

Analysis characteristics:

* Each summary includes budget, competitor, timeline, and contact influence.
* Example: Meeting with Liu Wei (Mercury Consulting) — evaluating Freshworks, timeline next quarter, follow-up needed. 

---

## 💡 Potential Use Cases

### ✔ CRM Automation

* Track deal pipelines by stage
* Automate follow-ups based on next_steps fields
* Score prospects by decision power

### ✔ NLP & Generative AI

* Meeting summary extraction
* Competitor heat-map creation
* Automatic proposal recommendations

### ✔ Business Intelligence

* Deal win rate vs competitor
* Sales timelines forecast
* Industry segmentation analysis

---

## 🧠 Suggested Notebook Features (main.ipynb)

A well-designed notebook could include:

* 📍 *Top decision-makers* across industries
* 🔥 *Hot leads ranking* (budget × decision power × timeline)
* ⚔ *Number of deals lost vs competitors* (Salesforce, Freshworks, HubSpot, etc.)
* 📊 *Visualization:*

  * Deal value distribution
  * Timeline vs stage flow
  * Company segmentation (by size/location/industry)

---

## 🏗 Tech Setup

### Dependencies (likely required)

* Python 3
* Pandas
* NumPy
* Matplotlib / Plotly

### Recommended Folder Structure


project/
│
├── data/
│   ├── existing_companies.json
│   ├── existing_contacts.json
│   ├── previous_deals.json
│   └── previous_meetings.json
│
├── notebooks/
│   └── main.ipynb
│
└── README.md


---

## 🔥 Key Insights from Dataset (Quick Highlights)

* Many *decision-making roles* include CTO, VP Product, Head of Sales.
* Common *competitors*: Salesforce, Freshworks, HubSpot, Oracle, Zoho, Marketo.
* Currency variety points to *multi-country, multi-currency deal handling* (INR, EUR, GBP, USD, AUD).
* Recurring contacts indicate *multi-deal, multi-meeting pipelines* (Maya Patel, Liu Wei, Omar Khalid appear across several companies and deals).

---

## 🚀 Next Steps

* Implement function to *identify the highest-value active deal* per company.

* Build a *lead scoring algorithm* using:

  * Decision power
  * Budget
  * Competitor pressure
  * Stage urgency

* Convert meeting summaries to structured data using *NLTK or spaCy*.

---

