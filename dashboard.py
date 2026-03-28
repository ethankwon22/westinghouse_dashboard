import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os

st.set_page_config(page_title="Microreactor Economic Decision Simulator", layout="wide")

# ─────────────────────────────────────────
# Constants — Government Model
# ─────────────────────────────────────────
VSL = 10_000_000
CASUALTY_RATE = 1 / 24
MAX_CASUALTIES_PER_YEAR = 1
SOLDIER_ANNUAL_COST = 120_000
LOGISTICS_RATIO_MIN = 0.10
LOGISTICS_RATIO_MAX = 0.20

FBCF_PER_CONVOY_FIXED = {
    "Remote FOB":        500_000,
    "Forward Operating": 150_000,
    "Domestic/Training":  30_000,
}
REGION_DISTANCE_KM = {
    "Middle East": 1000, "Pacific Island": 1500,
    "Europe": 450, "Domestic": 200,
}
CAPEX_PER_MW = {
    "FOAK (1st unit)":    20_000_000,
    "BOAK (early batch)": 12_000_000,
    "NOAK (mature)":       7_000_000,
}
OPEX_PER_MW_YEAR = 500_000
DECOM_PER_MW     = 1_000_000
SECURITY_COST_RANGE = {"low": 50_000, "mid": 275_000, "high": 600_000}

# Generator efficiency (fuel $/kWh-thermal → $/kWh-electric)
DIESEL_EFFICIENCY   = 0.35
NATGAS_EFFICIENCY   = 0.30

# ─────────────────────────────────────────
# Load Real EIA Data
# ─────────────────────────────────────────
@st.cache_data
def load_fuel_prices():
    """Load EIA SEDS forecasted fuel prices (1970–2038) by sector."""
    path = "Backup_Generator_Fuel_Prices_Forecasted.xlsx"
    if not os.path.exists(path):
        path = "/mnt/user-data/uploads/Backup_Generator_Fuel_Prices_Forecasted.xlsx"
    sheets = {}
    for sector in ["Residential", "Commercial", "Industrial"]:
        sheets[sector] = pd.read_excel(path, sheet_name=sector)
    return sheets

@st.cache_data
def load_reliability():
    """Load EIA-861 SAIDI reliability data by state (2024)."""
    path = "Reliability_2024.xlsx"
    if not os.path.exists(path):
        path = "/mnt/user-data/uploads/Reliability_2024.xlsx"
    df = pd.read_excel(path, sheet_name="State Totals", header=None)
    # Rows 0-2 = multi-row header, rows 3+ = data
    # Use iloc to extract columns directly — avoids duplicate column name issues
    # Col 1 = State abbr, Col 3 = SAIDI With MED (min/yr), Col 6 = SAIDI Without MED (min/yr)
    raw = df.iloc[3:].copy()
    raw = raw.dropna(subset=[1])  # drop footer rows

    result = pd.DataFrame({
        "state":               raw.iloc[:, 1].astype(str).str.strip(),
        "saidi_with_med":      pd.to_numeric(raw.iloc[:, 3], errors="coerce"),
        "saidi_without_med":   pd.to_numeric(raw.iloc[:, 6], errors="coerce"),
    })
    result["saidi_hours_with_med"]    = result["saidi_with_med"] / 60
    result["saidi_hours_without_med"] = result["saidi_without_med"] / 60
    return result[["state", "saidi_hours_with_med", "saidi_hours_without_med"]].reset_index(drop=True)

fuel_sheets   = load_fuel_prices()
reliability   = load_reliability()

def get_price(sector, state, fuel, year):
    """Get $/kWh price for a given sector/state/fuel/year."""
    df = fuel_sheets[sector]
    row = df[(df["State"] == state) & (df["Fuel Type"].str.contains(fuel, case=False))]
    if row.empty:
        return None
    col = str(year)
    return float(row[col].values[0]) if col in row.columns else None

def get_state_full_names():
    """Map state abbreviations to full names for display."""
    STATE_MAP = {
        "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California",
        "CO":"Colorado","CT":"Connecticut","DC":"District of Columbia","DE":"Delaware",
        "FL":"Florida","GA":"Georgia","HI":"Hawaii","IA":"Iowa","ID":"Idaho",
        "IL":"Illinois","IN":"Indiana","KS":"Kansas","KY":"Kentucky","LA":"Louisiana",
        "MA":"Massachusetts","MD":"Maryland","ME":"Maine","MI":"Michigan","MN":"Minnesota",
        "MO":"Missouri","MS":"Mississippi","MT":"Montana","NC":"North Carolina",
        "ND":"North Dakota","NE":"Nebraska","NH":"New Hampshire","NJ":"New Jersey",
        "NM":"New Mexico","NV":"Nevada","NY":"New York","OH":"Ohio","OK":"Oklahoma",
        "OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina",
        "SD":"South Dakota","TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont",
        "VA":"Virginia","WA":"Washington","WI":"Wisconsin","WV":"West Virginia","WY":"Wyoming",
    }
    avail = reliability["state"].tolist()
    return {abbr: name for abbr, name in STATE_MAP.items() if abbr in avail}

STATE_MAP = get_state_full_names()
STATE_NAMES = sorted(STATE_MAP.values())

# ─────────────────────────────────────────
# Custom Items Session State
# ─────────────────────────────────────────
if "custom_items" not in st.session_state:
    st.session_state.custom_items = []

# ─────────────────────────────────────────
# Title
# ─────────────────────────────────────────
st.title("Microreactor Economic Decision Simulator")
st.caption("eVinci Pricing Framework — Government (FBCF-based) & Market (EIA Real Data)")

# ─────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────
st.sidebar.header("Scenario Inputs")
industry    = st.sidebar.selectbox("Industry Type", ["Government", "Market"])
required_mw = st.sidebar.number_input("Required Capacity (MW)", 1, 15, 5, step=1,
                                       help="eVinci range: 1–15 MW")

# ── Government Parameters ─────────────────
if industry == "Government":
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🪖 Government Parameters**")
    mission_type = st.sidebar.selectbox(
        "Mission Type", list(FBCF_PER_CONVOY_FIXED.keys()), index=1,
        help="Remote FOB: $500K/convoy | Forward: $150K/convoy | Domestic: $30K/convoy")
    deployment_region = st.sidebar.selectbox(
        "Deployment Region", list(REGION_DISTANCE_KM.keys()), index=0,
        help="Geographic context — does not directly affect cost")
    force_size = st.sidebar.slider("Force Size (personnel)", 100, 5000, 500, step=100)
    convoys_per_year = st.sidebar.slider("Convoys per Year", 4, 200, 24, step=4,
        help="Default 24 = monthly resupply + surge (RAND MG-662 baseline)")
    security_level   = st.sidebar.slider("Security Level (%)", 0, 100, 30)
    risk_tolerance   = st.sidebar.slider("Risk Tolerance (%)", 0, 100, 50)
    operation_years  = st.sidebar.slider("Operation Duration (years)", 3, 20, 10)
    contract_type    = st.sidebar.selectbox("Contract Type (LCOE Stage)",
        list(CAPEX_PER_MW.keys()), index=1,
        help="FOAK=$20M/MW | BOAK=$12M/MW | NOAK=$7M/MW")

# ── Market Parameters ─────────────────────
else:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**⚡ Market Parameters**")

    selected_state_name = st.sidebar.selectbox("State", STATE_NAMES,
        index=STATE_NAMES.index("California") if "California" in STATE_NAMES else 0)
    selected_state_abbr = {v: k for k, v in STATE_MAP.items()}[selected_state_name]

    sector       = st.sidebar.selectbox("Sector", ["Commercial", "Industrial", "Residential"],
                                        help="Determines energy price tier from EIA SEDS data")
    forecast_year = st.sidebar.slider("Forecast Year", 2024, 2038, 2025,
                                      help="2024 = historical. 2025–2038 = Prophet forecast.")
    saidi_variant = st.sidebar.selectbox("SAIDI Variant",
        ["With Major Event Days", "Without Major Event Days"],
        help="With MED includes hurricanes/storms. Without MED = typical baseline.")
    facility_kw  = st.sidebar.number_input("Facility Demand (kW)", 100, 50000, 1000, step=100,
                                            help="Average electrical power draw of the facility")
    revenue_per_hr = st.sidebar.number_input("Revenue Lost per Outage Hour ($)", 0, 5_000_000,
                                              50_000, step=5_000,
                                              help="Gross productivity/revenue loss per hour of outage")
    risk_tolerance = st.sidebar.slider("Risk Tolerance (%)", 0, 100, 50)

# ─────────────────────────────────────────
# Government Model Calculation
# ─────────────────────────────────────────
def calc_government(required_mw, mission_type, deployment_region,
                    force_size, convoys_per_year, security_level,
                    risk_tolerance, operation_years, contract_type, custom_items):

    fbcf_annual         = convoys_per_year * FBCF_PER_CONVOY_FIXED[mission_type]
    expected_casualties = min(convoys_per_year * CASUALTY_RATE, MAX_CASUALTIES_PER_YEAR)
    blood_cost_annual   = expected_casualties * VSL
    base_disruption     = 2_000_000 * required_mw
    mission_assurance   = base_disruption * (1 - risk_tolerance / 100)
    logistics_ratio     = LOGISTICS_RATIO_MIN + (LOGISTICS_RATIO_MAX - LOGISTICS_RATIO_MIN) * (1 - risk_tolerance / 100)
    force_realloc       = force_size * logistics_ratio * SOLDIER_ANNUAL_COST

    if security_level <= 30:   sec_rate = SECURITY_COST_RANGE["low"]
    elif security_level <= 70: sec_rate = SECURITY_COST_RANGE["mid"]
    else:                      sec_rate = SECURITY_COST_RANGE["high"]
    security_cost_annual = sec_rate * required_mw

    capex       = CAPEX_PER_MW[contract_type] * required_mw
    opex_annual = OPEX_PER_MW_YEAR * required_mw
    decom       = DECOM_PER_MW * required_mw
    smr_annual  = (capex + decom) / operation_years + opex_annual + security_cost_annual

    custom_total  = sum(i["value"] for i in custom_items)
    diesel_annual = fbcf_annual + blood_cost_annual + mission_assurance + force_realloc
    net_advantage = (diesel_annual + custom_total) - smr_annual
    annual_kwh    = required_mw * 1_000 * 8_760
    max_price_kwh = (diesel_annual + custom_total) / annual_kwh if annual_kwh > 0 else 0

    return {
        "diesel_annual": diesel_annual, "smr_annual": smr_annual,
        "net_advantage": net_advantage, "max_smr_price_kwh": max_price_kwh,
        "breakdown": {
            "FBCF (Fuel Logistics)":     fbcf_annual,
            "Casualty Avoidance":        blood_cost_annual,
            "Mission Assurance Premium": mission_assurance,
            "Force Reallocation":        force_realloc,
            "Custom Items":              custom_total,
        },
        "smr_breakdown": {
            "CAPEX (annualized)":           capex / operation_years,
            "OPEX":                         opex_annual,
            "Security Hardening":           security_cost_annual,
            "Decommissioning (annualized)": decom / operation_years,
        },
    }

# ─────────────────────────────────────────
# Market Model Calculation (Real EIA Data)
# ─────────────────────────────────────────
def calc_market(required_mw, state_abbr, sector, forecast_year,
                saidi_variant, facility_kw, revenue_per_hr,
                risk_tolerance, custom_items):

    # Real prices from EIA SEDS
    elec_price   = get_price(sector, STATE_MAP[state_abbr], "Electricity", forecast_year)
    diesel_price = get_price(sector, STATE_MAP[state_abbr], "Diesel",      forecast_year)
    natgas_price = get_price(sector, STATE_MAP[state_abbr], "Natural Gas",  forecast_year)

    # Real SAIDI from EIA-861
    rel_row = reliability[reliability["state"] == state_abbr]
    if rel_row.empty:
        saidi_hours = 2.0
    else:
        col = "saidi_hours_with_med" if "With Major" in saidi_variant else "saidi_hours_without_med"
        saidi_hours = float(rel_row[col].values[0])

    # Grid savings during outage (utility doesn't bill)
    grid_savings = facility_kw * saidi_hours * (elec_price or 0.10)

    # No backup scenario
    no_backup_cost = revenue_per_hr * saidi_hours - grid_savings

    # Diesel backup scenario
    diesel_fuel_per_kwh_elec = (diesel_price or 0.07) / DIESEL_EFFICIENCY
    diesel_fuel_cost = facility_kw * saidi_hours * diesel_fuel_per_kwh_elec
    diesel_backup_cost = diesel_fuel_cost - grid_savings

    # Natural gas backup scenario
    natgas_fuel_per_kwh_elec = (natgas_price or 0.04) / NATGAS_EFFICIENCY
    natgas_fuel_cost = facility_kw * saidi_hours * natgas_fuel_per_kwh_elec
    natgas_backup_cost = natgas_fuel_cost - grid_savings

    # SMR breakeven price ($/kWh)
    annual_energy = required_mw * 1_000 * 8_760
    # Resilience premium based on outage cost avoided
    outage_cost_avoided = max(no_backup_cost, 0)
    custom_total   = sum(i["value"] for i in custom_items)
    premium_adj    = outage_cost_avoided * (1 - risk_tolerance / 200)
    breakeven_kwh  = (elec_price or 0.10) + (premium_adj + custom_total) / annual_energy
    premium_pct    = ((breakeven_kwh - (elec_price or 0.10)) / (elec_price or 0.10)) * 100

    return {
        "elec_price":       elec_price,
        "diesel_price":     diesel_price,
        "natgas_price":     natgas_price,
        "saidi_hours":      saidi_hours,
        "no_backup_cost":   no_backup_cost,
        "diesel_backup":    diesel_backup_cost,
        "natgas_backup":    natgas_backup_cost,
        "breakeven_kwh":    breakeven_kwh,
        "premium_pct":      premium_pct,
        "custom_total":     custom_total,
        "grid_savings":     grid_savings,
    }

# ─────────────────────────────────────────
# Layout — Government header
# ─────────────────────────────────────────
if industry == "Government":
    st.subheader("🪖 Government Pricing Model — FBCF-Based Analysis")
    st.caption("Comparison baseline: Fully Burdened Cost of Fuel (FBCF). Grid electricity price excluded.")

# ── Market: State map ────────────────────
else:
    st.subheader("⚡ Market Pricing Model — EIA Real Data")
    st.caption(f"Electricity & fuel prices: EIA SEDS {forecast_year} ({sector}). Outage data: EIA-861 2024.")

    # Build choropleth from real EIA electricity prices for selected year
    map_data = []
    for abbr in reliability["state"].tolist():
        p = get_price(sector, STATE_MAP.get(abbr, ""), "Electricity", forecast_year)
        if p:
            map_data.append({"state": abbr, "elec_price": round(p, 4)})
    map_df = pd.DataFrame(map_data)

    left_col, right_col = st.columns([2, 1])
    with left_col:
        fig_map = px.choropleth(
            map_df, locations="state", locationmode="USA-states",
            color="elec_price", scope="usa",
            color_continuous_scale="Blues",
            labels={"elec_price": f"Electricity $/kWh ({forecast_year})"},
        )
        fig_map.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig_map, use_container_width=True)

    with right_col:
        st.markdown(f"**{selected_state_name} ({selected_state_abbr}) — {forecast_year}**")
        ep = get_price(sector, selected_state_name, "Electricity", forecast_year)
        dp = get_price(sector, selected_state_name, "Diesel",      forecast_year)
        np_ = get_price(sector, selected_state_name, "Natural Gas", forecast_year)
        rel_row = reliability[reliability["state"] == selected_state_abbr]
        saidi_val = float(rel_row["saidi_hours_with_med"].values[0]) if not rel_row.empty else None

        st.metric("Electricity Price", f"${ep:.4f}/kWh" if ep else "N/A")
        st.metric("Diesel Price",      f"${dp:.4f}/kWh" if dp else "N/A")
        st.metric("Natural Gas Price", f"${np_:.4f}/kWh" if np_ else "N/A")
        st.metric("SAIDI (outage hrs/yr)", f"{saidi_val:.1f} hrs" if saidi_val else "N/A")

# ─────────────────────────────────────────
# Custom Cost Items
# ─────────────────────────────────────────
st.markdown("---")
st.subheader("➕ Additional Cost Items")
st.caption("Manually add cost/benefit factors. Negative = benefit (e.g. CHP savings).")

c1, c2, c3 = st.columns([3, 2, 1])
with c1:
    new_label = st.text_input("Item Label", placeholder="e.g. CHP Value, Regulatory Compliance")
with c2:
    new_value = st.number_input("Annual Value ($)", value=0, step=10_000,
                                help="Positive=cost, Negative=benefit/savings")
with c3:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("＋ Add"):
        if new_label.strip():
            st.session_state.custom_items.append({"label": new_label.strip(), "value": float(new_value)})
            st.rerun()

if st.session_state.custom_items:
    st.markdown("**Current custom items:**")
    for idx, item in enumerate(st.session_state.custom_items):
        a, b, c = st.columns([3, 2, 1])
        with a: st.write(f"📌 {item['label']}")
        with b:
            sign = "+" if item["value"] >= 0 else ""
            st.write(f"{sign}${item['value']:,.0f} / year")
        with c:
            if st.button("🗑️ Remove", key=f"rm_{idx}"):
                st.session_state.custom_items.pop(idx)
                st.rerun()

# ─────────────────────────────────────────
# Results
# ─────────────────────────────────────────
st.markdown("---")
st.subheader("📊 Economic Outcome")

# ── Government Results ────────────────────
if industry == "Government":
    res = calc_government(
        required_mw, mission_type, deployment_region,
        force_size, convoys_per_year, security_level,
        risk_tolerance, operation_years, contract_type,
        st.session_state.custom_items
    )
    advantage = res["net_advantage"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Diesel Total (Annual)",    f"${res['diesel_annual']:,.0f}")
    c2.metric("SMR Total (Annual)",       f"${res['smr_annual']:,.0f}")
    c3.metric("SMR Net Advantage",        f"${advantage:,.0f}",
              delta="SMR Wins ✅" if advantage > 0 else "Diesel Wins ❌")
    c4.metric("Max Acceptable SMR Price", f"${res['max_smr_price_kwh']:.3f}/kWh")

    st.markdown("---")
    l2, r2 = st.columns(2)
    with l2:
        st.markdown("**Diesel Cost Breakdown (Annual)**")
        bd = res["breakdown"]
        fig_d = go.Figure(go.Bar(
            x=list(bd.values()), y=list(bd.keys()), orientation="h",
            marker_color=["#E63946","#F4A261","#E9C46A","#2A9D8F","#457B9D"],
            text=[f"${v:,.0f}" for v in bd.values()], textposition="outside"
        ))
        fig_d.update_layout(xaxis_title="Annual Cost ($)", margin=dict(l=0,r=80,t=10,b=0), height=300)
        st.plotly_chart(fig_d, use_container_width=True)

    with r2:
        st.markdown("**SMR Cost Breakdown (Annual)**")
        sbd = res["smr_breakdown"]
        fig_s = go.Figure(go.Bar(
            x=list(sbd.values()), y=list(sbd.keys()), orientation="h",
            marker_color=["#1D3557","#457B9D","#A8DADC","#F1FAEE"],
            text=[f"${v:,.0f}" for v in sbd.values()], textposition="outside"
        ))
        fig_s.update_layout(xaxis_title="Annual Cost ($)", margin=dict(l=0,r=80,t=10,b=0), height=300)
        st.plotly_chart(fig_s, use_container_width=True)

    st.markdown("**Cost Comparison: Diesel vs SMR**")
    fig_cmp = go.Figure(go.Bar(
        x=["Diesel (FBCF Total)", "SMR (Lifecycle Total)"],
        y=[res["diesel_annual"], res["smr_annual"]],
        marker_color=["#E63946", "#2A9D8F"],
        text=[f"${res['diesel_annual']:,.0f}", f"${res['smr_annual']:,.0f}"],
        textposition="outside"
    ))
    fig_cmp.update_layout(yaxis_title="Annual Cost ($)", margin=dict(l=0,r=0,t=10,b=0), height=350)
    st.plotly_chart(fig_cmp, use_container_width=True)

    st.subheader("Decision Summary")
    status = "✅ SMR IS ECONOMICALLY JUSTIFIED" if advantage > 0 else "⚠️ REQUIRES STRATEGIC JUSTIFICATION"
    st.text(
        f"Under {mission_type} conditions in the {deployment_region} region,\n"
        f"a {required_mw} MW eVinci deployment over {operation_years} years\n"
        f"shows an estimated annual diesel burden of ${res['diesel_annual']:,.0f} "
        f"vs. SMR annual cost of ${res['smr_annual']:,.0f}."
    )
    st.text(f"Max price Westinghouse can charge: ${res['max_smr_price_kwh']:.3f}/kWh.")
    st.markdown(f"### {status}")

# ── Market Results ────────────────────────
else:
    res = calc_market(
        required_mw, selected_state_abbr, sector, forecast_year,
        saidi_variant, facility_kw, revenue_per_hr,
        risk_tolerance, st.session_state.custom_items
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Grid Electricity Price",  f"${res['elec_price']:.4f}/kWh" if res['elec_price'] else "N/A")
    c2.metric("SMR Breakeven Price",     f"${res['breakeven_kwh']:.4f}/kWh")
    c3.metric("Justifiable Premium",     f"{res['premium_pct']:.1f}%")
    c4.metric("Annual Outage (hrs)",     f"{res['saidi_hours']:.1f} hrs")

    # 4-scenario comparison bar chart
    st.markdown("**Annual Outage Cost by Backup Scenario**")
    scenario_df = pd.DataFrame({
        "Scenario":     ["No Backup", "Diesel Generator", "Natural Gas Generator", "SMR (eVinci)"],
        "Annual Cost":  [
            max(res["no_backup_cost"], 0),
            max(res["diesel_backup"], 0),
            max(res["natgas_backup"], 0),
            0,   # SMR = 0 outage cost (continuous power)
        ],
        "Color": ["#E63946", "#F4A261", "#E9C46A", "#2A9D8F"]
    })
    fig_sc = go.Figure(go.Bar(
        x=scenario_df["Scenario"], y=scenario_df["Annual Cost"],
        marker_color=scenario_df["Color"],
        text=[f"${v:,.0f}" for v in scenario_df["Annual Cost"]],
        textposition="outside"
    ))
    fig_sc.update_layout(yaxis_title="Annual Outage Cost ($)",
                          margin=dict(l=0,r=0,t=10,b=0), height=350)
    st.plotly_chart(fig_sc, use_container_width=True)

    # Price trend chart (2024–2038)
    st.markdown("**Electricity Price Forecast: 2024–2038 (EIA + Prophet)**")
    years      = list(range(2024, 2039))
    price_hist = [get_price(sector, selected_state_name, "Electricity", y) for y in years]
    fig_trend  = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=years, y=price_hist, mode="lines+markers",
        name="Electricity Price", line=dict(color="#457B9D", width=2)
    ))
    fig_trend.add_vline(x=2024.5, line_dash="dash", line_color="gray",
                         annotation_text="Forecast →")
    fig_trend.update_layout(
        xaxis_title="Year", yaxis_title="$/kWh",
        margin=dict(l=0,r=0,t=10,b=0), height=300
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # Decision Summary
    st.subheader("Decision Summary")
    is_viable = res["premium_pct"] <= 20
    status    = "✅ ECONOMICALLY DEFENSIBLE" if is_viable else "⚠️ REQUIRES STRATEGIC JUSTIFICATION"
    st.text(
        f"In {selected_state_name} ({sector} sector, {forecast_year}),\n"
        f"grid electricity costs ${res['elec_price']:.4f}/kWh "
        f"with {res['saidi_hours']:.1f} annual outage hours (SAIDI).\n"
        f"Annual outage cost without backup: ${max(res['no_backup_cost'],0):,.0f}.\n"
        f"SMR breakeven price: ${res['breakeven_kwh']:.4f}/kWh "
        f"({res['premium_pct']:.1f}% above grid rate)."
    )
    st.markdown(f"### {status}")
