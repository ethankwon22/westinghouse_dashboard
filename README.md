# westinghouse_dashboard
# eVinci Microreactor Economic Decision Simulator
**Westinghouse 2 Capstone Project — Tepper School of Business, CMU | Spring 2025**

> An interactive pricing decision tool that estimates the optimal price range for the Westinghouse eVinci microreactor across Government and Market deployment scenarios.

---

## Overview

This dashboard supports Westinghouse's pricing and sales strategy by modeling two distinct customer segments:

- **Government** — Off-grid military/federal deployments. Pricing is benchmarked against the Fully Burdened Cost of Fuel (FBCF), not grid electricity. Methodology mirrors the U.S. DoD Project Pele framework.
- **Market** — Grid-connected civilian/commercial deployments. Pricing is benchmarked against EIA state-level electricity rates and outage costs (SAIDI-based).

The tool is designed as a **dynamic sales and strategy instrument** — not a static report. Users can adjust scenario parameters in real time and immediately see how the eVinci's justifiable price range shifts.

---

## Key Output

| Metric | Description |
|---|---|
| **Diesel Total (Annual)** | Total annual cost of maintaining diesel fuel logistics under given scenario |
| **SMR Total (Annual)** | Annualized lifecycle cost of eVinci deployment |
| **SMR Net Advantage** | Diesel Total minus SMR Total — positive means SMR is economically justified |
| **Max Acceptable SMR Price** | Maximum $/kWh Westinghouse can charge while remaining competitive vs. diesel |

---

## Government Model Parameters

| Parameter | Range | Default | Source |
|---|---|---|---|
| Capacity (MW) | 1–15 MW | 5 MW | Westinghouse eVinci specs |
| Mission Type | Remote FOB / Forward Operating / Domestic | Forward Operating | GAO-01-734, RAND MG-662 |
| Deployment Region | Middle East / Pacific Island / Europe / Domestic | Middle East | Contextual only |
| Force Size | 100–5,000 personnel | 500 | RAND estimate |
| Convoys per Year | 4–200 | 24 | RAND MG-662 (monthly + surge) |
| Security Level | 0–100% | 30% | NRC / DOE / Project Pele |
| Risk Tolerance | 0–100% | 50% | DoD Mission Assurance Policy |
| Operation Duration | 3–20 years | 10 years | eVinci fuel cycle specs |
| Contract Type | FOAK / BOAK / NOAK | BOAK | DOE GAIN / INL AP1000 reports |

**Note:** The Government model does not use electricity grid prices. The relevant comparison is diesel logistics cost (FBCF), not market electricity rates.

---

## Government Model — Cost Formula

### Diesel Side (annual)
```
FBCF               = Convoys/year × Fixed cost per convoy (by Mission Type)
Casualty Avoidance = min(Convoys/24, 1) × VSL ($10M)
Mission Assurance  = Capacity(MW) × $2M × (1 − Risk Tolerance)
Force Reallocation = Force Size × Logistics Ratio × $120K/soldier

Diesel Total = FBCF + Casualty + Mission Assurance + Force Reallocation
```

### SMR Side (annual)
```
CAPEX (annualized) = Capacity(MW) × CAPEX/MW ÷ Operation Years
OPEX               = Capacity(MW) × $500K
Security           = Capacity(MW) × Security Cost/MW
Decommissioning    = Capacity(MW) × $1M ÷ Operation Years

SMR Total = CAPEX + OPEX + Security + Decommissioning
```

### Max Acceptable Price
```
Max SMR Price ($/kWh) = Diesel Total ÷ Annual Generation (kWh)
Annual Generation     = Capacity(MW) × 1,000 × 8,760 hrs
```

---

## Market Model Parameters

| Parameter | Description |
|---|---|
| State | Pulls EIA grid price and SAIDI outage hours |
| Load Factor (%) | Actual utilization rate of the reactor |
| Risk Tolerance (%) | Willingness to accept outage risk |
| Usage Type | Primary (full-time) or Backup |

### Market Model — Breakeven Formula
```
Annual Outage Loss  = Outage Hours × $300K × Criticality Factor × Scale Factor
Resilience Premium  = Annual Loss ÷ Annual Energy Consumption
Breakeven Price     = Grid Price + Adjusted Premium
```

---

## Custom Cost Items

The **+ Add** button allows users to manually inject additional cost or benefit factors not captured in the base model:

- **Positive value** → adds to diesel burden (makes SMR look more favorable)
- **Negative value** → treated as a SMR-side benefit (e.g., Combined Heat & Power savings, CHP)

Example use cases: Regulatory compliance costs, CHP thermal value, grid interconnection fees, deferred maintenance savings.

---

## Differentiation from Project Pele

| | Project Pele (DoD, 2020) | This Dashboard |
|---|---|---|
| Purpose | Single-scenario DoD policy report | Dynamic Westinghouse sales/strategy tool |
| Scenarios | Fixed conditions | Infinite parameter combinations |
| Scope | Government only | Government + Market integrated |
| Output | Static cost estimate | Interactive break-even analysis |
| User | DoD analysts | Westinghouse sales, strategy, and clients |

---

## Data Sources

| Data | Source |
|---|---|
| FBCF unit costs | GAO-01-734; RAND MG-662 |
| Value of Statistical Life (VSL) | U.S. EPA ($10M) |
| Casualty rate per convoy | RAND MG-662 (1 per 24 convoys) |
| SMR CAPEX estimates | DOE GAIN Program; INL AP1000 Report (2025) |
| Grid electricity prices | EIA State Energy Data (dummy values in prototype) |
| Outage hours (SAIDI) | EIA Reliability Data (IEEE standards) |
| Security cost tiers | NRC Regulatory Guide 5.59; DOE O 473.3 |

---

## Deployment

### Option 1 — Run Locally

**Requirements:**
```
Python 3.9+
streamlit
pandas
plotly
numpy
```

**Install dependencies:**
```bash
pip install streamlit pandas plotly numpy
```

**Run:**
```bash
streamlit run dashboard.py
```

Then open `http://localhost:8501` in your browser.

---

### Option 2 — Deploy via Streamlit Cloud (Recommended for sharing)

This is the fastest way to share a live link with sponsors or stakeholders — free, no server setup required.

**Step 1.** Push your code to a GitHub repository:
```
your-repo/
├── dashboard.py
├── requirements.txt
└── README.md
```

**Step 2.** Create `requirements.txt`:
```
streamlit
pandas
plotly
numpy
```

**Step 3.** Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.

**Step 4.** Click **"New app"** → select your repo → set main file to `dashboard.py` → click **Deploy**.

**Step 5.** Streamlit will generate a public URL like:
```
https://your-app-name.streamlit.app
```

Share this link directly with Westinghouse or any stakeholder. No installation needed on their end.

---

## Project Team

| Name | Program |
|---|---|
| Bodong Chen | MSBA, Tepper School of Business |
| Diaa Emam | MSBA, Tepper School of Business |
| Ethan Kwon | MSBA, Tepper School of Business |
| Steven Shen | MSBA, Tepper School of Business |

**Sponsor:** Westinghouse Electric Company
**Course:** Capstone Project, Spring 2025
