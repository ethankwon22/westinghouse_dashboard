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
DIESEL_EFFICIENCY = 0.35
NATGAS_EFFICIENCY = 0.30

# ─────────────────────────────────────────
# Constants — Market WTP Framework
# ─────────────────────────────────────────
PQ_MULT = {"Low": 1.00, "Med": 1.15, "High": 1.35}
EO_MULT = {"Low": 1.00, "Med": 1.25, "High": 1.60}
CU_MULT = {"Low": 1.00, "Med": 1.10, "High": 1.25}

RESTART_COST_PER_KW = {
    "Residential": 1.0,
    "Commercial":  3.0,
    "Industrial":  10.0,
}

# ─────────────────────────────────────────
# Load Real EIA Data
# ─────────────────────────────────────────
@st.cache_data
def load_fuel_prices():
    path = "Backup_Generator_Fuel_Prices_Forecasted.xlsx"
    if not os.path.exists(path):
        path = "/mnt/user-data/uploads/Backup_Generator_Fuel_Prices_Forecasted.xlsx"
    sheets = {}
    for sector in ["Residential", "Commercial", "Industrial"]:
        sheets[sector] = pd.read_excel(path, sheet_name=sector)
    return sheets

@st.cache_data
def load_reliability():
    path = "Reliability_2024.xlsx"
    if not os.path.exists(path):
        path = "/mnt/user-data/uploads/Reliability_2024.xlsx"
    df = pd.read_excel(path, sheet_name="State Totals", header=None)

    raw = df.iloc[3:].copy()
    raw = raw.dropna(subset=[1])

    result = pd.DataFrame({
        "state":             raw.iloc[:, 1].astype(str).str.strip(),
        "saidi_with_med":    pd.to_numeric(raw.iloc[:, 3], errors="coerce"),
        "saidi_without_med": pd.to_numeric(raw.iloc[:, 6], errors="coerce"),
        "saifi_with_med":    pd.to_numeric(raw.iloc[:, 4], errors="coerce"),
        "saifi_without_med": pd.to_numeric(raw.iloc[:, 7], errors="coerce"),
    })
    result["saidi_hours_with_med"]    = result["saidi_with_med"] / 60
    result["saidi_hours_without_med"] = result["saidi_without_med"] / 60
    return result[["state",
                    "saidi_hours_with_med", "saidi_hours_without_med",
                    "saifi_with_med",       "saifi_without_med"]].reset_index(drop=True)

fuel_sheets = load_fuel_prices()
reliability = load_reliability()

def get_price(sector, state, fuel, year):
    df = fuel_sheets[sector]
    row = df[(df["State"] == state) & (df["Fuel Type"].str.contains(fuel, case=False))]
    if row.empty:
        return None
    col = str(year)
    return float(row[col].values[0]) if col in row.columns else None


def get_avg_price_over_years(sector, state, fuel, years):
    prices = [get_price(sector, state, fuel, y) for y in years]
    prices = [p for p in prices if p is not None]
    return float(np.mean(prices)) if prices else None

def get_state_full_names():
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
industry = st.sidebar.selectbox("Industry Type", ["Government", "Market"])
required_mw = st.sidebar.number_input(
    "Required Capacity (MW)", 1, 15, 5, step=1,
    help="Default = 5 MW. eVinci range: 1–15 MW."
)

if industry == "Government":
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🪖 Government Parameters**")
    mission_type = st.sidebar.selectbox(
        "Mission Type", list(FBCF_PER_CONVOY_FIXED.keys()), index=1,
        help="Default = Forward Operating. Remote FOB: $500K/convoy | Forward: $150K/convoy | Domestic: $30K/convoy"
    )
    deployment_region = st.sidebar.selectbox(
        "Deployment Region", list(REGION_DISTANCE_KM.keys()), index=0,
        help="Default = Middle East. Geographic context only — does not directly affect cost."
    )
    force_size = st.sidebar.slider("Force Size (personnel)", 100, 5000, 500, step=100)
    convoys_per_year = st.sidebar.slider(
        "Convoys per Year", 4, 200, 24, step=4,
        help="Default = 24. Interpreted as monthly resupply + surge."
    )
    security_level = st.sidebar.slider("Security Level (%)", 0, 100, 30)
    risk_tolerance = st.sidebar.slider("Risk Tolerance (%)", 0, 100, 50)
    operation_years = st.sidebar.slider("Operation Duration (years)", 3, 20, 10)
    deployment_start_year = st.sidebar.slider(
        "Deployment Start Year", 2024, 2038, 2025,
        help="Used to average forecast diesel prices over the selected operating window."
    )
    contract_type = st.sidebar.selectbox(
        "Contract Type (LCOE Stage)",
        list(CAPEX_PER_MW.keys()), index=1,
        help="Default = BOAK. FOAK=$20M/MW | BOAK=$12M/MW | NOAK=$7M/MW"
    )

else:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**⚡ Market Parameters**")

    selected_state_name = st.sidebar.selectbox(
        "State", STATE_NAMES,
        index=STATE_NAMES.index("California") if "California" in STATE_NAMES else 0
    )
    selected_state_abbr = {v: k for k, v in STATE_MAP.items()}[selected_state_name]

    sector = st.sidebar.selectbox(
        "Sector", ["Commercial", "Industrial", "Residential"],
        index=0,
        help="Default = Commercial. Determines energy price tier from EIA SEDS data."
    )
    forecast_year = st.sidebar.slider(
        "Forecast Year", 2024, 2038, 2025,
        help="Default = 2025. 2024 = historical. 2025–2038 = forecast."
    )
    saidi_variant = st.sidebar.selectbox(
        "SAIDI Variant",
        ["With Major Event Days", "Without Major Event Days"],
        help="Default = With Major Event Days."
    )
    facility_kw = st.sidebar.number_input(
        "Facility Demand (kW)", 100, 50000, 1000, step=100,
        help="Default = 1,000 kW."
    )
    revenue_per_hr = st.sidebar.number_input(
        "Revenue Lost per Outage Hour ($)", 0, 5_000_000, 50_000, step=5_000,
        help=(
            "Default = $50,000/hr. This is a user-adjustable placeholder, "
            "not a model-predicted value."
        )
    )
    risk_tolerance = st.sidebar.slider(
        "Risk Tolerance (%)", 0, 100, 50,
        help="Default = 50%."
    )

    with st.sidebar.expander("⚙️ Advanced Risk Scenarios", expanded=False):
        st.caption(
            "Defaults are preloaded for convenience. If unchanged, Low is used as the default scenario. "
            "Multipliers are conservative scenario calibrations anchored in public literature "
            "(EPRI, NREL, LBNL, DOE) — not direct published coefficients."
        )
        pq_level = st.selectbox(
            "Power Quality Sensitivity",
            ["Low", "Med", "High"], index=0
        )
        eo_level = st.selectbox(
            "Extended Outage Exposure",
            ["Low", "Med", "High"], index=0
        )
        cu_level = st.selectbox(
            "Capacity Urgency",
            ["Low", "Med", "High"], index=0
        )

# ─────────────────────────────────────────
# Government Model Calculation
# ─────────────────────────────────────────
def calc_government(required_mw, mission_type, deployment_region,
                    force_size, convoys_per_year, security_level,
                    risk_tolerance, operation_years, deployment_start_year,
                    contract_type, custom_items):

    fallback_flags = []
    end_year = min(deployment_start_year + operation_years - 1, 2038)
    operating_years = list(range(deployment_start_year, end_year + 1))
    actual_years_used = len(operating_years)

    # Use forecasted diesel prices to adjust the fuel-related portion of the FBCF.
    # We keep the military logistics burden concept intact and scale it by relative fuel price movement.
    region_to_state = {
        "Middle East": "Texas",
        "Pacific Island": "Hawaii",
        "Europe": "Virginia",
        "Domestic": "Pennsylvania",
    }
    diesel_reference_state = region_to_state.get(deployment_region, "Texas")
    base_year = 2025
    base_diesel_price = get_price("Commercial", diesel_reference_state, "Diesel", base_year)
    avg_diesel_price = get_avg_price_over_years("Commercial", diesel_reference_state, "Diesel", operating_years)

    if base_diesel_price is None or base_diesel_price <= 0:
        base_diesel_price = 0.07
        fallback_flags.append("Government diesel base price fallback applied ($0.07/kWh-th in 2025 equivalent).")
    if avg_diesel_price is None or avg_diesel_price <= 0:
        avg_diesel_price = base_diesel_price
        fallback_flags.append("Government diesel forecast fallback applied; using base-year diesel price.")

    diesel_escalation_factor = avg_diesel_price / base_diesel_price if base_diesel_price > 0 else 1.0
    adjusted_fbcf_per_convoy = FBCF_PER_CONVOY_FIXED[mission_type] * diesel_escalation_factor
    fbcf_annual = convoys_per_year * adjusted_fbcf_per_convoy

    expected_casualties = min(convoys_per_year * CASUALTY_RATE, MAX_CASUALTIES_PER_YEAR)
    blood_cost_annual   = expected_casualties * VSL
    base_disruption     = 2_000_000 * required_mw
    mission_assurance   = base_disruption * (1 - risk_tolerance / 100)
    logistics_ratio     = LOGISTICS_RATIO_MIN + (LOGISTICS_RATIO_MAX - LOGISTICS_RATIO_MIN) * (1 - risk_tolerance / 100)
    force_realloc       = force_size * logistics_ratio * SOLDIER_ANNUAL_COST

    if security_level <= 30:
        sec_rate = SECURITY_COST_RANGE["low"]
    elif security_level <= 70:
        sec_rate = SECURITY_COST_RANGE["mid"]
    else:
        sec_rate = SECURITY_COST_RANGE["high"]

    security_cost_annual = sec_rate * required_mw

    capex       = CAPEX_PER_MW[contract_type] * required_mw
    opex_annual = OPEX_PER_MW_YEAR * required_mw
    decom       = DECOM_PER_MW * required_mw
    smr_annual  = (capex + decom) / operation_years + opex_annual + security_cost_annual

    custom_total      = sum(i["value"] for i in custom_items)
    diesel_annual     = fbcf_annual + blood_cost_annual + mission_assurance + force_realloc
    diesel_lifecycle  = (diesel_annual + custom_total) * actual_years_used
    smr_lifecycle     = smr_annual * actual_years_used
    net_advantage     = (diesel_annual + custom_total) - smr_annual
    lifecycle_adv     = diesel_lifecycle - smr_lifecycle
    annual_kwh        = required_mw * 1_000 * 8_760
    max_price_kwh     = (diesel_annual + custom_total) / annual_kwh if annual_kwh > 0 else 0

    return {
        "diesel_annual": diesel_annual,
        "diesel_lifecycle": diesel_lifecycle,
        "smr_annual": smr_annual,
        "smr_lifecycle": smr_lifecycle,
        "net_advantage": net_advantage,
        "lifecycle_advantage": lifecycle_adv,
        "max_smr_price_kwh": max_price_kwh,
        "deployment_start_year": deployment_start_year,
        "deployment_end_year": end_year,
        "years_used": actual_years_used,
        "diesel_reference_state": diesel_reference_state,
        "base_diesel_price": base_diesel_price,
        "avg_diesel_price": avg_diesel_price,
        "diesel_escalation_factor": diesel_escalation_factor,
        "fallback_flags": fallback_flags,
        "breakdown": {
            "FBCF (Fuel Logistics, adj.)": adjusted_fbcf_per_convoy * convoys_per_year,
            "Casualty Avoidance":          blood_cost_annual,
            "Mission Assurance Premium":   mission_assurance,
            "Force Reallocation":          force_realloc,
            "Custom Items":                custom_total,
        },
        "smr_breakdown": {
            "CAPEX (annualized)":           capex / operation_years,
            "OPEX":                         opex_annual,
            "Security Hardening":           security_cost_annual,
            "Decommissioning (annualized)": decom / operation_years,
        },
    }

# ─────────────────────────────────────────
# Market Model Calculation
# ─────────────────────────────────────────
def calc_market(required_mw, state_abbr, sector, forecast_year,
                saidi_variant, facility_kw, revenue_per_hr,
                risk_tolerance, pq_level, eo_level, cu_level, custom_items):

    fallback_flags = []

    # Real prices
    elec_price = get_price(sector, STATE_MAP[state_abbr], "Electricity", forecast_year)
    diesel_price = get_price(sector, STATE_MAP[state_abbr], "Diesel", forecast_year)
    natgas_price = get_price(sector, STATE_MAP[state_abbr], "Natural Gas", forecast_year)

    if elec_price is None:
        elec_price = 0.10
        fallback_flags.append("Electricity price fallback applied ($0.10/kWh).")
    if diesel_price is None:
        diesel_price = 0.07
        fallback_flags.append("Diesel backup price fallback applied ($0.07/kWh-th).")
    if natgas_price is None:
        natgas_price = 0.04
        fallback_flags.append("Natural gas backup price fallback applied ($0.04/kWh-th).")

    # Reliability
    rel_row = reliability[reliability["state"] == state_abbr]
    if rel_row.empty:
        saidi_hours = 2.0
        saifi = 1.5
        fallback_flags.append("Reliability fallback applied (SAIDI=2.0 hrs/yr, SAIFI=1.5 events/yr).")
    else:
        saidi_col = "saidi_hours_with_med" if "With Major" in saidi_variant else "saidi_hours_without_med"
        saifi_col = "saifi_with_med" if "With Major" in saidi_variant else "saifi_without_med"
        saidi_hours = float(rel_row[saidi_col].values[0])
        saifi = float(rel_row[saifi_col].values[0])

    base_duration_loss = revenue_per_hr * saidi_hours
    restart_cost = RESTART_COST_PER_KW[sector]
    v_freq = saifi * facility_kw * restart_cost

    pq_mult = PQ_MULT[pq_level]
    eo_mult = EO_MULT[eo_level]
    cu_mult = CU_MULT[cu_level]

    v_pq = base_duration_loss * (pq_mult - 1.0)
    v_ext = base_duration_loss * (eo_mult - 1.0)
    v_cap = base_duration_loss * (cu_mult - 1.0)

    total_resilience_value = base_duration_loss + v_freq + v_pq + v_ext + v_cap
    grid_savings = facility_kw * saidi_hours * elec_price

    no_backup_cost = base_duration_loss - grid_savings
    diesel_fuel_cost = facility_kw * saidi_hours * (diesel_price / DIESEL_EFFICIENCY)
    diesel_backup = diesel_fuel_cost - grid_savings
    natgas_fuel_cost = facility_kw * saidi_hours * (natgas_price / NATGAS_EFFICIENCY)
    natgas_backup = natgas_fuel_cost - grid_savings

    annual_energy = required_mw * 1_000 * 8_760
    custom_total = sum(i["value"] for i in custom_items)
    premium_adj = total_resilience_value * (1 - risk_tolerance / 200)
    breakeven_kwh = elec_price + (premium_adj + custom_total) / annual_energy
    premium_pct = ((breakeven_kwh - elec_price) / elec_price) * 100 if elec_price > 0 else 0

    return {
        "elec_price": elec_price,
        "diesel_price": diesel_price,
        "natgas_price": natgas_price,
        "saidi_hours": saidi_hours,
        "saifi": saifi,
        "no_backup_cost": no_backup_cost,
        "diesel_backup": diesel_backup,
        "natgas_backup": natgas_backup,
        "breakeven_kwh": breakeven_kwh,
        "premium_pct": premium_pct,
        "custom_total": custom_total,
        "grid_savings": grid_savings,
        "fallback_flags": fallback_flags,
        "wtp_breakdown": {
            "Base Duration Loss":       base_duration_loss,
            "Frequency Cost (V_freq)":  v_freq,
            "Power Quality (V_pq)":     v_pq,
            "Extended Outage (V_ext)":  v_ext,
            "Capacity Urgency (V_cap)": v_cap,
            "Custom Items":             custom_total,
        },
    }

# ─────────────────────────────────────────
# Header
# ─────────────────────────────────────────
if industry == "Government":
    st.subheader("🪖 Government Pricing Model — FBCF-Based Analysis")
    st.caption("Comparison baseline: Fully Burdened Cost of Fuel (FBCF). Grid electricity price excluded.")
else:
    st.subheader("⚡ Market Pricing Model — EIA Real Data")
    st.caption(
        f"Electricity & fuel prices: EIA SEDS {forecast_year} ({sector}). "
        f"Outage data: EIA-861 2024. Defaults are preloaded for convenience."
    )

# ─────────────────────────────────────────
# Custom Cost Items
# ─────────────────────────────────────────
st.markdown("---")
st.subheader("➕ Additional Cost Items")
st.caption("Positive = added burden. Negative = benefit/savings.")

c1, c2, c3 = st.columns([3, 2, 1])
with c1:
    new_label = st.text_input("Item Label", placeholder="e.g. CHP Value, Regulatory Compliance")
with c2:
    new_value = st.number_input("Annual Value ($)", value=0, step=10_000)
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
        with a:
            st.write(f"📌 {item['label']}")
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

if industry == "Government":
    res = calc_government(
        required_mw, mission_type, deployment_region,
        force_size, convoys_per_year, security_level,
        risk_tolerance, operation_years, deployment_start_year,
        contract_type, st.session_state.custom_items
    )
    advantage = res["net_advantage"]
    lifecycle_advantage = res["lifecycle_advantage"]

    if res["fallback_flags"]:
        st.warning(
            "Some requested government fuel inputs were unavailable in the uploaded data, so fallback assumptions were used:\n\n- "
            + "\n- ".join(res["fallback_flags"])
        )
    else:
        st.info(
            f"Government diesel/FBCF adjustment uses forecast diesel prices averaged from {res['deployment_start_year']} to {res['deployment_end_year']} "
            f"({res['diesel_reference_state']} proxy state)."
        )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Diesel Total (Annual)", f"${res['diesel_annual']:,.0f}")
    c2.metric("Diesel Total (Lifecycle)", f"${res['diesel_lifecycle']:,.0f}")
    c3.metric("SMR Total (Annual)", f"${res['smr_annual']:,.0f}")
    c4.metric("SMR Total (Lifecycle)", f"${res['smr_lifecycle']:,.0f}")

    c5, c6, c7 = st.columns(3)
    c5.metric("SMR Net Advantage (Annual)", f"${advantage:,.0f}",
              delta="SMR Wins ✅" if advantage > 0 else "Diesel Wins ❌")
    c6.metric("SMR Net Advantage (Lifecycle)", f"${lifecycle_advantage:,.0f}",
              delta="SMR Wins ✅" if lifecycle_advantage > 0 else "Diesel Wins ❌")
    c7.metric("Max Acceptable SMR Price", f"${res['max_smr_price_kwh']:.3f}/kWh")

    st.caption(
        f"Lifecycle window: {res['deployment_start_year']}–{res['deployment_end_year']} ({res['years_used']} years used). "
        f"Avg diesel price proxy = ${res['avg_diesel_price']:.4f}/kWh-th vs. base ${res['base_diesel_price']:.4f}/kWh-th "
        f"(FBCF escalation factor {res['diesel_escalation_factor']:.2f}x)."
    )

else:
    res = calc_market(
        required_mw, selected_state_abbr, sector, forecast_year,
        saidi_variant, facility_kw, revenue_per_hr,
        risk_tolerance, pq_level, eo_level, cu_level,
        st.session_state.custom_items
    )

    if res["fallback_flags"]:
        st.warning(
            "Some requested inputs were unavailable in the uploaded data, so fallback assumptions were used:\n\n- "
            + "\n- ".join(res["fallback_flags"])
        )
    else:
        st.info("All core price and reliability inputs were pulled from the uploaded EIA-based datasets.")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Grid Electricity Price", f"${res['elec_price']:.4f}/kWh")
    c2.metric("SMR Breakeven Price", f"${res['breakeven_kwh']:.4f}/kWh")
    c3.metric("Justifiable Premium", f"{res['premium_pct']:.1f}%")
    c4.metric("SAIDI (hrs/yr)", f"{res['saidi_hours']:.1f} hrs")
    c5.metric("SAIFI (events/yr)", f"{res['saifi']:.2f}")

    st.markdown("**WTP Breakdown — Resilience Value Components**")
    st.caption(
        "Revenue loss per outage hour is a user-provided facility parameter. "
        "Defaults are placeholders for convenience; replace them with site-specific estimates when available. "
        "Advanced multipliers are conservative scenario calibrations anchored in public literature."
    )

    wtp = res["wtp_breakdown"]
    fig_wtp = go.Figure(go.Bar(
        x=list(wtp.values()), y=list(wtp.keys()), orientation="h",
        text=[f"${v:,.0f}" for v in wtp.values()], textposition="outside"
    ))
    fig_wtp.update_layout(xaxis_title="Annual Value ($)", margin=dict(l=0, r=80, t=10, b=0), height=320)
    st.plotly_chart(fig_wtp, use_container_width=True)

    st.subheader("Decision Summary")
    total_wtp = sum(res["wtp_breakdown"].values())
    st.text(
        f"In {selected_state_name} ({sector} sector, {forecast_year}),\n"
        f"grid electricity costs ${res['elec_price']:.4f}/kWh with {res['saidi_hours']:.1f} outage hrs/yr "
        f"and {res['saifi']:.2f} interruptions/yr.\n"
        f"Using a user-provided outage loss assumption of ${revenue_per_hr:,.0f}/hr,\n"
        f"total resilience value is estimated at ${total_wtp:,.0f}/yr.\n"
        f"SMR breakeven price: ${res['breakeven_kwh']:.4f}/kWh "
        f"({res['premium_pct']:.1f}% above grid rate)."
    )
