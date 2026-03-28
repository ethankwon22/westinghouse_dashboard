eVinci Microreactor Economic Decision Simulator

Westinghouse 2 Capstone Project — Tepper School of Business, CMU | Spring 2025

An interactive pricing decision tool that estimates the economically justifiable price range for the Westinghouse eVinci microreactor across Government and Market deployment scenarios.

Overview

This dashboard supports Westinghouse’s pricing and sales strategy by modeling two distinct customer segments:

Government — Off-grid military/federal deployments. Pricing is benchmarked against the Fully Burdened Cost of Fuel (FBCF) rather than grid electricity. The methodology mirrors the logic of the U.S. DoD Project Pele framework.
Market — Grid-connected commercial/civilian deployments. Pricing is benchmarked against real EIA state-level electricity and backup fuel prices together with state-level outage reliability data (SAIDI/SAIFI), user-provided outage-loss assumptions, and scenario-based resilience adders.

The dashboard is designed as a dynamic sales and strategy tool, not a static report. Users can adjust assumptions in real time and immediately observe how the eVinci’s economically defensible price range changes across use cases.

Key Outputs
Metric	Model	Description
Diesel Total (Annual)	Government	Total annual cost burden of diesel-based logistics and mission support
SMR Total (Annual)	Government	Annualized lifecycle cost of eVinci deployment
SMR Net Advantage	Government	Diesel Total minus SMR Total — positive values support SMR adoption
Max Acceptable SMR Price	Government	Maximum $/kWh Westinghouse can charge relative to diesel burden
SMR Breakeven Price	Market	$/kWh at which eVinci becomes economically justifiable relative to grid power
Justifiable Premium	Market	% above grid electricity price the customer can rationally absorb
WTP Breakdown	Market	Annual resilience value split into duration, frequency, power quality, extended outage, and capacity urgency components
Backup Scenario Comparison	Market	No Backup / Diesel Generator / Natural Gas Generator / SMR comparison
Model Philosophy
Government Model

The Government model asks:

Why can eVinci command a premium in military/off-grid environments?

Because government customers are not primarily purchasing low-cost electricity — they are reducing:

fuel logistics burden,
casualty exposure,
mission disruption risk,
and force allocation inefficiency.
Market Model

The Market model asks:

Where does that premium become economically viable in commercial settings?

Because market customers are not valuing only average electricity price — they are valuing:

outage duration risk,
outage frequency risk,
power quality sensitivity,
prolonged outage exposure,
and urgency of capacity access.
Government Model
Parameters
Parameter	Range	Default	Source
Capacity (MW)	1–15 MW	5 MW	Westinghouse eVinci specs
Mission Type	Remote FOB / Forward Operating / Domestic/Training	Forward Operating	GAO-01-734; RAND MG-662
Deployment Region	Middle East / Pacific Island / Europe / Domestic	Middle East	Contextual only
Force Size	100–5,000 personnel	500	RAND estimate
Convoys per Year	4–200	24	RAND MG-662 baseline
Security Level	0–100%	30%	NRC / DOE / Project Pele
Risk Tolerance	0–100%	50%	DoD Mission Assurance logic
Operation Duration	3–20 years	10 years	eVinci fuel cycle assumptions
Contract Type	FOAK / BOAK / NOAK	BOAK	DOE GAIN / INL AP1000-based estimates

Note: The Government model intentionally excludes electricity grid prices. The relevant comparison baseline is diesel logistics cost (FBCF), not market electricity rates. This mirrors Project Pele-style analysis.

Cost Formula

Diesel Side (Annual)

FBCF               = Convoys/year × Fixed cost per convoy (by Mission Type)
                     Remote FOB: $500K | Forward: $150K | Domestic: $30K

Casualty Avoidance = min(Convoys/24, 1 casualty) × VSL ($10M)

Mission Assurance  = Capacity(MW) × $2M × (1 − Risk Tolerance)

Force Reallocation = Force Size × Logistics Ratio (10–20%) × $120K/soldier

Diesel Total = FBCF + Casualty Avoidance + Mission Assurance + Force Reallocation + Custom Items

SMR Side (Annual)

CAPEX (annualized) = Capacity(MW) × CAPEX/MW ÷ Operation Years
                     FOAK: $20M/MW | BOAK: $12M/MW | NOAK: $7M/MW

OPEX               = Capacity(MW) × $500K

Security           = Capacity(MW) × Security Cost/MW (tier-based)

Decommissioning    = Capacity(MW) × $1M ÷ Operation Years

SMR Total = CAPEX + OPEX + Security + Decommissioning

Max Acceptable SMR Price

Max SMR Price ($/kWh) = Diesel Total ÷ Annual Generation (kWh)

Annual Generation     = Capacity(MW) × 1,000 × 8,760 hrs
Market Model
Parameters
Parameter	Range	Default	Source
State	All states + DC with available data	California	EIA SEDS / EIA-861
Sector	Commercial / Industrial / Residential	Commercial	EIA SEDS
Forecast Year	2024–2038	2025	EIA + Prophet forecast
SAIDI Variant	With / Without Major Event Days	With MED	EIA-861
Facility Demand (kW)	100–50,000	1,000	User input
Revenue Lost per Outage Hour ($)	0–5,000,000	50,000	User input
Risk Tolerance (%)	0–100	50	User input
Power Quality Sensitivity	Low / Med / High	Low	Scenario calibration
Extended Outage Exposure	Low / Med / High	Low	Scenario calibration
Capacity Urgency	Low / Med / High	Low	Scenario calibration
Important Design Notes
Revenue Lost per Outage Hour is not model-predicted.
It is treated as a user-provided facility parameter, because outage loss is highly site-specific and depends on internal operations, process criticality, and business model.
Advanced Risk Scenario multipliers are not direct published coefficients.
They are conservative scenario calibrations anchored in public literature (EPRI, NREL, LBNL, DOE) and intended for decision support, not engineering certification.
Defaults are preloaded for convenience.
If users do not change certain inputs, the simulator applies conservative default assumptions.
Fallback assumptions are explicitly disclosed.
If requested state/year values are unavailable in the uploaded datasets, the app applies fallback assumptions and displays a warning in the UI.
Market WTP Logic

The Market model estimates the resilience-adjusted breakeven price of eVinci by combining real observed/forecasted energy prices with outage-related economic value.

Core Components
Base Duration Loss = Revenue Lost/hr × SAIDI hours

Frequency Cost     = SAIFI × Facility kW × Restart Cost per kW/event

Power Quality      = Base Duration Loss × (PQ Multiplier − 1)

Extended Outage    = Base Duration Loss × (EO Multiplier − 1)

Capacity Urgency   = Base Duration Loss × (CU Multiplier − 1)
Total Resilience Value
Total Resilience Value
= Base Duration Loss
+ Frequency Cost
+ Power Quality
+ Extended Outage
+ Capacity Urgency
+ Custom Items
SMR Breakeven Price
SMR Breakeven ($/kWh)
= Grid Price + (Risk-Adjusted Resilience Value ÷ Annual Generation)

where:

Risk-Adjusted Resilience Value
= Total Resilience Value × (1 − Risk Tolerance / 200)
Backup Scenario Comparison

The dashboard also compares four annual outage-cost cases:

No Backup
Diesel Generator
Natural Gas Generator
SMR (eVinci)

This gives users both:

a WTP-style breakeven price, and
a side-by-side operating scenario comparison.
Data Sources
Fuel Price Data
Item	Source
Historical prices (1970–2024)	EIA State Energy Data System (SEDS)
Forecast (2025–2038)	Prophet forecast using historical EIA price series
Fuels covered	Electricity, Diesel (Distillate), Natural Gas
Sectors covered	Residential, Commercial, Industrial
Units	$/kWh
File	Backup_Generator_Fuel_Prices_Forecasted.xlsx
Reliability Data
Item	Source
Outage metrics	EIA Form EIA-861 Annual Electric Power Industry Report
Standard	IEEE reliability metrics
Variables used	SAIDI, SAIFI
Variants	With Major Event Days / Without Major Event Days
Coverage	State-level 2024 snapshot
File	Reliability_2024.xlsx
Government Model Sources
Item	Source
FBCF unit costs	GAO-01-734; RAND MG-662
Value of Statistical Life (VSL)	U.S. EPA ($10M assumption)
Casualty rate per convoy	RAND MG-662
SMR CAPEX assumptions	DOE GAIN Program; INL/AP1000-style comparative estimates
Security cost tiers	NRC Regulatory Guide 5.59; DOE O 473.3
Literature Anchors for Market Risk Adders
Risk Component	Literature Basis
Power Quality Sensitivity	EPRI power quality and voltage sag studies
Frequency Cost / Restart Cost	LBNL / Sullivan customer damage function literature
Extended Outage Exposure	NREL resilience valuation literature
Capacity Urgency	DOE large-load / interconnection and data center power demand reports

These sources anchor the direction and relative magnitude of the scenario framework, but the specific multipliers in the dashboard should be interpreted as decision-support calibrations, not official published coefficients.

Prophet Model Configuration
yearly_seasonality        = False
weekly_seasonality        = False
daily_seasonality         = False
n_changepoints            = 10
changepoint_range         = 0.9
changepoint_prior_scale   = 0.1
interval_width            = 0.95
Transform                 = None
Negative clamp            = $0.00 floor

Backtest result (train 1970–2018, holdout 2019–2024):

Median MAPE: ~20% overall
6-year-out median APE: ~10%
Direction accuracy: ~96%
Custom Cost Items (+ Button)

Both models support manual injection of additional annual cost/benefit factors.

Positive value → increases diesel burden or resilience value
Negative value → treated as benefit/savings

Example use cases:

CHP thermal value
Regulatory compliance burden
Deferred maintenance savings
Grid interconnection fees
Process-specific strategic adders
Fallback Assumptions

If a requested Market input is unavailable in the uploaded data files, the simulator uses conservative fallback assumptions and explicitly notifies the user in the interface.

Fallback values currently used:

Electricity price fallback: $0.10/kWh
Diesel backup price fallback: $0.07/kWh-thermal
Natural gas backup price fallback: $0.04/kWh-thermal
Reliability fallback: SAIDI = 2.0 hrs/year, SAIFI = 1.5 events/year

These values are intended only to preserve model continuity and should be replaced by actual observed data whenever possible.

Differentiation from Project Pele
	Project Pele (DoD)	This Dashboard
Purpose	Single-scenario policy justification	Dynamic Westinghouse pricing/sales tool
Scope	Government only	Government + Market integrated
Government method	Engineering estimate	Engineering estimate
Market method	N/A	Real EIA prices + outage data + resilience valuation
User inputs	Fixed assumptions	Dynamic scenario inputs
Output	Static estimate	Interactive breakeven + WTP breakdown + scenario comparison
User	DoD analysts	Westinghouse sales, strategy, and clients
Deployment
Files Required
your-repo/
├── dashboard.py
├── Backup_Generator_Fuel_Prices_Forecasted.xlsx
├── Reliability_2024.xlsx
├── requirements.txt
└── README.md
requirements.txt
streamlit
pandas
plotly
numpy
openpyxl
Run Locally
pip install streamlit pandas plotly numpy openpyxl
streamlit run dashboard.py

Then open http://localhost:8501.

Deploy via Streamlit Cloud
Push all files above to a GitHub repository
Go to Streamlit Cloud
Create a new app
Set dashboard.py as the main file
Deploy and share the generated URL
Updating Data in the Future

When new EIA data becomes available:

Download updated SEDS fuel-price data
Regenerate the forecast workbook
Download updated EIA-861 reliability data
Replace the .xlsx files in the repository
Redeploy the app
Project Team
Name	Program
Bodong Chen	MSBA, Tepper School of Business, CMU
Diaa Emam	MSBA, Tepper School of Business, CMU
Ethan Kwon	MSBA, Tepper School of Business, CMU
Steven Shen	MSBA, Tepper School of Business, CMU

Sponsor: Westinghouse Electric Company
Course: Capstone Project, Spring 2025
