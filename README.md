# eVinci Microreactor Economic Decision Simulator
**Westinghouse 2 Capstone Project — Tepper School of Business, CMU | Spring 2025**

> An interactive pricing decision tool that estimates the optimal price range for the Westinghouse eVinci microreactor across Government and Market deployment scenarios.

---

## Overview

This dashboard supports Westinghouse's pricing and sales strategy by modeling two distinct customer segments:

- **Government** — Off-grid military/federal deployments. Pricing is benchmarked against the Fully Burdened Cost of Fuel (FBCF), not grid electricity. Methodology mirrors the U.S. DoD Project Pele framework.
- **Market** — Grid-connected civilian/commercial deployments. Pricing is benchmarked against real EIA state-level electricity rates (1970–2038 forecast) and IEEE-standard outage costs (SAIDI-based).

The tool is designed as a **dynamic sales and strategy instrument** — not a static report. Users can adjust scenario parameters in real time and immediately see how the eVinci's justifiable price range shifts.

---

## Key Outputs

| Metric | Model | Description |
|---|---|---|
| **Diesel Total (Annual)** | Government | Total annual cost of maintaining diesel fuel logistics |
| **SMR Total (Annual)** | Government | Annualized lifecycle cost of eVinci deployment |
| **SMR Net Advantage** | Government | Diesel Total minus SMR Total — positive = SMR justified |
| **Max Acceptable SMR Price** | Government | Maximum $/kWh Westinghouse can charge vs. diesel |
| **SMR Breakeven Price** | Market | $/kWh at which eVinci becomes cost-competitive vs. grid |
| **Justifiable Premium** | Market | % above grid price the customer can rationally absorb |
| **4-Scenario Comparison** | Market | No Backup / Diesel / Natural Gas / SMR side-by-side |

---

## Government Model

### Parameters

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

> **Note:** The Government model does not use electricity grid prices. The relevant comparison is diesel logistics cost (FBCF), not market electricity rates. This mirrors the Project Pele methodology.

### Cost Formula

**Diesel Side (annual)**
```
FBCF               = Convoys/year × Fixed cost per convoy (by Mission Type)
                     Remote FOB: $500K | Forward: $150K | Domestic: $30K
Casualty Avoidance = min(Convoys/24, 1 casualty) × VSL ($10M)
Mission Assurance  = Capacity(MW) × $2M × (1 − Risk Tolerance)
Force Reallocation = Force Size × Logistics Ratio (10–20%) × $120K/soldier

Diesel Total = FBCF + Casualty + Mission Assurance + Force Reallocation
```

**SMR Side (annual)**
```
CAPEX (annualized) = Capacity(MW) × CAPEX/MW ÷ Operation Years
                     FOAK: $20M/MW | BOAK: $12M/MW | NOAK: $7M/MW
OPEX               = Capacity(MW) × $500K
Security           = Capacity(MW) × Security Cost/MW (tier-based)
Decommissioning    = Capacity(MW) × $1M ÷ Operation Years

SMR Total = CAPEX + OPEX + Security + Decommissioning
```

**Max Acceptable Price**
```
Max SMR Price ($/kWh) = Diesel Total ÷ Annual Generation (kWh)
Annual Generation     = Capacity(MW) × 1,000 × 8,760 hrs
```

---

## Market Model

### Parameters

| Parameter | Range | Default | Source |
|---|---|---|---|
| State | All 51 states + DC | California | EIA SEDS |
| Sector | Residential / Commercial / Industrial | Commercial | EIA SEDS |
| Forecast Year | 2024–2038 | 2025 | Prophet forecast |
| SAIDI Variant | With / Without Major Event Days | With MED | EIA-861 |
| Facility Demand (kW) | 100–50,000 kW | 1,000 kW | User input |
| Revenue Lost per Outage Hour | $0–$5M | $50,000 | User input |
| Risk Tolerance | 0–100% | 50% | — |

### Cost Formula

```
Annual Outage Hours  = SAIDI (minutes) ÷ 60
Grid Savings         = Facility kW × Outage Hours × Grid Price

No Backup Cost       = Revenue Lost/hr × Outage Hours − Grid Savings

Diesel Backup Cost   = Facility kW × Outage Hours × (Diesel Price ÷ 0.35 efficiency)
                       + Annual Generator Cost − Grid Savings

Natural Gas Backup   = Facility kW × Outage Hours × (NG Price ÷ 0.30 efficiency)
                       + Annual Generator Cost − Grid Savings

SMR Breakeven ($/kWh) = Grid Price + (Outage Cost Avoided × Risk Adj.) ÷ Annual kWh
```

---

## Data Sources

### Fuel Price Data
| Item | Source |
|---|---|
| Historical prices (1970–2024) | EIA State Energy Data System (SEDS) — `pr_all_update.xlsx` |
| Forecast (2025–2038) | Facebook Prophet (linear, no seasonality) — validated via 2019–2024 holdout |
| Fuels covered | Electricity, Diesel (Distillate), Natural Gas |
| Sectors covered | Residential, Commercial, Industrial |
| Units | $/kWh (converted from $/mmBTU via ÷ 293.07107) |
| File | `Backup_Generator_Fuel_Prices_Forecasted.xlsx` |

### Reliability Data
| Item | Source |
|---|---|
| Outage metrics | EIA Form EIA-861 Annual Electric Power Industry Report |
| Standard | IEEE — SAIDI, SAIFI, CAIDI |
| Variants | With Major Event Days / Without Major Event Days |
| Coverage | 51 states + DC (2024 snapshot) |
| File | `Reliability_2024.xlsx` |

### Government Model Sources
| Item | Source |
|---|---|
| FBCF unit costs | GAO-01-734; RAND MG-662 |
| Value of Statistical Life (VSL) | U.S. EPA ($10M) |
| Casualty rate per convoy | RAND MG-662 (1 per 24 convoys) |
| SMR CAPEX estimates | DOE GAIN Program; INL AP1000 Report (2025) |
| Security cost tiers | NRC Regulatory Guide 5.59; DOE O 473.3 |

---

## Prophet Model Configuration

```
yearly_seasonality  = False
weekly_seasonality  = False
daily_seasonality   = False
n_changepoints      = 10
changepoint_range   = 0.9
changepoint_prior_scale = 0.1
interval_width      = 0.95
Transform           = None (raw $/kWh, additive linear trend)
Negative clamp      = $0.00 floor
```

**Backtest result (train 1970–2018, holdout 2019–2024):**
- Median MAPE: ~20% overall
- 6-year-out median APE: ~10%
- Direction accuracy: ~96%

---

## Custom Cost Items (+ Button)

Both models support manual injection of additional cost/benefit factors:

- **Positive value** → adds to the diesel/outage burden (makes SMR more favorable)
- **Negative value** → treated as an SMR-side benefit

Example use cases: CHP thermal value, regulatory compliance costs, grid interconnection fees, deferred maintenance savings.

---

## Differentiation from Project Pele

| | Project Pele (DoD, 2020) | This Dashboard |
|---|---|---|
| Purpose | Single-scenario DoD policy report | Dynamic Westinghouse sales/strategy tool |
| Scenarios | Fixed conditions | Infinite parameter combinations |
| Scope | Government only | Government + Market integrated |
| Price data | Engineering estimates | Real EIA SEDS + Prophet forecast |
| Outage data | N/A | EIA-861 IEEE standard (2024) |
| Output | Static cost estimate | Interactive 4-scenario comparison |
| User | DoD analysts | Westinghouse sales, strategy, and clients |

---

## Deployment

### Files Required

```
your-repo/
├── dashboard.py
├── Backup_Generator_Fuel_Prices_Forecasted.xlsx
├── Reliability_2024.xlsx
├── requirements.txt
└── README.md
```

### requirements.txt
```
streamlit
pandas
plotly
numpy
openpyxl
```

### Option 1 — Run Locally
```bash
pip install streamlit pandas plotly numpy openpyxl
streamlit run dashboard.py
```
Then open `http://localhost:8501`.

### Option 2 — Deploy via Streamlit Cloud (Recommended)

1. Push all files above to a GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io) → sign in with GitHub
3. Click **New app** → select repo → set main file to `dashboard.py` → **Deploy**
4. A public URL is generated instantly:
   ```
   https://your-app-name.streamlit.app
   ```
   Share this link directly with Westinghouse — no installation needed on their end.

---

## Updating Data in the Future

When new EIA data becomes available:

1. Download fresh `pr_all_update.xlsx` from [EIA SEDS](https://www.eia.gov/state/seds/seds-data-fuel.php?sid=US)
2. Rerun `SEDS_to_Backup_Generator.ipynb` to generate updated historical prices
3. Rerun `Energy_Price_Forecasting_Final.ipynb` to extend Prophet forecasts
4. Download fresh `Reliability_XXXX.xlsx` from [EIA-861](https://www.eia.gov/electricity/data/eia861/)
5. Replace both `.xlsx` files in the repo and redeploy

---

## Project Team

| Name | Program |
|---|---|
| Bodong Chen | MSBA, Tepper School of Business, CMU |
| Diaa Emam | MSBA, Tepper School of Business, CMU |
| Ethan Kwon | MSBA, Tepper School of Business, CMU |
| Steven Shen | MSBA, Tepper School of Business, CMU |

**Sponsor:** Westinghouse Electric Company
**Course:** Capstone Project, Spring 2025
