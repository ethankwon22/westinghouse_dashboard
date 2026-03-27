import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="Microreactor Economic Decision Simulator", layout="wide")

# ─────────────────────────────────────────
# Constants
# ─────────────────────────────────────────
VSL = 10_000_000               # Value of Statistical Life (EPA, $10M)
CASUALTY_RATE = 1 / 24        # 1 casualty per 24 convoys (RAND MG-662)
MAX_CASUALTIES_PER_YEAR = 1   # Realistic annual cap — even active theater ~1/yr
SOLDIER_ANNUAL_COST = 120_000 # Fully-loaded annual cost per soldier
LOGISTICS_RATIO_MIN = 0.10    # Baseline: 10% of force on logistics
LOGISTICS_RATIO_MAX = 0.20    # Cap: 20% max (RAND estimate)

# Fixed cost per convoy by mission type (GAO-01-734, RAND MG-662)
# Region is contextual display only — cost driven by mission type
FBCF_PER_CONVOY_FIXED = {
    "Remote FOB":        500_000,  # $/convoy — air+ground, extreme remote ops
    "Forward Operating": 150_000,  # $/convoy — active theater, RAND midpoint
    "Domestic/Training":  30_000,  # $/convoy — CONUS training base
}

REGION_DISTANCE_KM = {
    "Middle East":    1000,
    "Pacific Island": 1500,
    "Europe":         450,
    "Domestic":       200,
}

# CAPEX per MW by contract type — DOE GAIN / AP1000 / INL reports
CAPEX_PER_MW = {
    "FOAK (1st unit)":    20_000_000,
    "BOAK (early batch)": 12_000_000,
    "NOAK (mature)":       7_000_000,
}
OPEX_PER_MW_YEAR = 500_000    # $/MW/year
DECOM_PER_MW     = 1_000_000  # $/MW

SECURITY_COST_RANGE = {  # $/MW/year
    "low":  50_000,   # 0–30%: NRC standard industrial
    "mid":  275_000,  # 30–70%: DOE facility level
    "high": 600_000,  # 70–100%: military-grade hardening
}

# ─────────────────────────────────────────
# State Dataset (Market)
# ─────────────────────────────────────────
def build_state_dataframe() -> pd.DataFrame:
    states = [
        "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA",
        "HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
        "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
        "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
        "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY",
    ]
    rows = []
    for i, state in enumerate(states):
        rows.append({
            "state": state,
            "grid_price": round(0.07 + (i % 12) * 0.01, 3),
            "saidi_hours": round(1 + (i % 10) * 0.5, 2),
            "volatility_index": round(0.1 + (i % 8) * 0.1, 2),
        })
    return pd.DataFrame(rows)

df = build_state_dataframe()

# ─────────────────────────────────────────
# Custom Items State Init
# ─────────────────────────────────────────
if "custom_items" not in st.session_state:
    st.session_state.custom_items = []

# ─────────────────────────────────────────
# Title
# ─────────────────────────────────────────
st.title("Microreactor Economic Decision Simulator")
st.caption("eVinci Pricing Framework — Government (FBCF-based) & Market (EIA-based)")

# ─────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────
st.sidebar.header("Scenario Inputs")

industry = st.sidebar.selectbox("Industry Type", ["Government", "Market"])
required_mw = st.sidebar.number_input(
    "Required Capacity (MW)", 1, 15, 5, step=1,
    help="eVinci range: 1–15 MW"
)

# ── Government Parameters ─────────────────
if industry == "Government":
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🪖 Government Parameters**")

    mission_type = st.sidebar.selectbox(
        "Mission Type",
        list(FBCF_PER_CONVOY_FIXED.keys()),
        index=1,
        help="Remote FOB: $500K/convoy | Forward: $150K/convoy | Domestic: $30K/convoy"
    )
    deployment_region = st.sidebar.selectbox(
        "Deployment Region",
        list(REGION_DISTANCE_KM.keys()),
        index=0,
        help="Geographic context only — does not directly affect cost"
    )
    force_size = st.sidebar.slider(
        "Force Size (personnel)", 100, 5000, 500, step=100,
        help="Total base personnel; drives Force Reallocation cost"
    )
    convoys_per_year = st.sidebar.slider(
        "Convoys per Year", 4, 200, 24, step=4,
        help="Default 24 = monthly resupply + surge (typical FOB). RAND MG-662 baseline."
    )
    security_level = st.sidebar.slider(
        "Security Level (%)", 0, 100, 30,
        help="0%=industrial | 50%=govt facility | 100%=military hardening"
    )
    risk_tolerance = st.sidebar.slider(
        "Risk Tolerance (%)", 0, 100, 50,
        help="0%=zero downtime allowed | 100%=backup usage OK"
    )
    operation_years = st.sidebar.slider(
        "Operation Duration (years)", 3, 20, 10,
        help="Deployment period for amortizing CAPEX"
    )
    contract_type = st.sidebar.selectbox(
        "Contract Type (LCOE Stage)",
        list(CAPEX_PER_MW.keys()),
        index=1,
        help="FOAK=$20M/MW | BOAK=$12M/MW | NOAK=$7M/MW (DOE GAIN / INL)"
    )

# ── Market Parameters ─────────────────────
else:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**⚡ Market Parameters**")
    load_factor    = st.sidebar.slider("Load Factor (%)", 1, 100, 70)
    risk_tolerance = st.sidebar.slider("Risk Tolerance (%)", 0, 100, 50)
    usage_type     = st.sidebar.selectbox("Usage Type", ["Primary", "Backup"])

# ─────────────────────────────────────────
# Government Model Calculation
# ─────────────────────────────────────────
def calc_government(
    required_mw, mission_type, deployment_region,
    force_size, convoys_per_year, security_level,
    risk_tolerance, operation_years, contract_type,
    custom_items
):
    # FBCF: fixed $/convoy by mission type (GAO-01-734, RAND MG-662)
    fbcf_annual = convoys_per_year * FBCF_PER_CONVOY_FIXED[mission_type]

    # Blood Cost: expected casualties capped at MAX_CASUALTIES_PER_YEAR
    expected_casualties = min(convoys_per_year * CASUALTY_RATE, MAX_CASUALTIES_PER_YEAR)
    blood_cost_annual   = expected_casualties * VSL

    # Mission Assurance Premium (scales with risk intolerance)
    base_disruption   = 2_000_000 * required_mw
    mission_assurance = base_disruption * (1 - risk_tolerance / 100)

    # Force Reallocation: ratio bounded between 10–20%
    logistics_ratio = LOGISTICS_RATIO_MIN + (LOGISTICS_RATIO_MAX - LOGISTICS_RATIO_MIN) * (1 - risk_tolerance / 100)
    force_realloc   = force_size * logistics_ratio * SOLDIER_ANNUAL_COST

    # Security Cost ($/MW/year by tier)
    if security_level <= 30:
        sec_rate = SECURITY_COST_RANGE["low"]
    elif security_level <= 70:
        sec_rate = SECURITY_COST_RANGE["mid"]
    else:
        sec_rate = SECURITY_COST_RANGE["high"]
    security_cost_annual = sec_rate * required_mw

    # SMR Lifecycle Cost (annualized)
    capex       = CAPEX_PER_MW[contract_type] * required_mw
    opex_annual = OPEX_PER_MW_YEAR * required_mw
    decom       = DECOM_PER_MW * required_mw
    smr_annual  = (capex + decom) / operation_years + opex_annual + security_cost_annual

    # Custom items
    custom_total  = sum(item["value"] for item in custom_items)
    diesel_annual = fbcf_annual + blood_cost_annual + mission_assurance + force_realloc
    net_advantage = (diesel_annual + custom_total) - smr_annual

    annual_kwh        = required_mw * 1_000 * 8_760
    max_smr_price_kwh = (diesel_annual + custom_total) / annual_kwh if annual_kwh > 0 else 0
    smr_lcoe_kwh      = smr_annual / annual_kwh if annual_kwh > 0 else 0

    breakdown = {
        "FBCF (Fuel Logistics)":     fbcf_annual,
        "Casualty Avoidance":        blood_cost_annual,
        "Mission Assurance Premium": mission_assurance,
        "Force Reallocation":        force_realloc,
        "Custom Items":              custom_total,
    }
    smr_breakdown = {
        "CAPEX (annualized)":           capex / operation_years,
        "OPEX":                         opex_annual,
        "Security Hardening":           security_cost_annual,
        "Decommissioning (annualized)": decom / operation_years,
    }

    return {
        "diesel_annual":      diesel_annual,
        "smr_annual":         smr_annual,
        "net_advantage":      net_advantage,
        "max_smr_price_kwh":  max_smr_price_kwh,
        "smr_lcoe_kwh":       smr_lcoe_kwh,
        "breakdown":          breakdown,
        "smr_breakdown":      smr_breakdown,
        "custom_total":       custom_total,
    }

# ─────────────────────────────────────────
# Market Model Calculation
# ─────────────────────────────────────────
def calc_market(required_mw, load_factor, risk_tolerance, usage_type, selected_row, custom_items):
    grid_price   = float(selected_row["grid_price"])
    outage_hours = float(selected_row["saidi_hours"])
    lf = load_factor / 100

    criticality_factor = 1 + 1.2 * lf
    scale_factor       = required_mw ** 0.9

    annual_loss    = outage_hours * 300_000 * criticality_factor * scale_factor
    annual_energy  = required_mw * 1000 * lf * 8760
    premium        = annual_loss / annual_energy if annual_energy > 0 else 0
    premium_adj    = premium * (1 - risk_tolerance / 200)

    custom_total   = sum(item["value"] for item in custom_items)
    custom_per_kwh = custom_total / annual_energy if annual_energy > 0 else 0

    breakeven_price = grid_price + premium_adj + custom_per_kwh
    premium_pct     = ((breakeven_price - grid_price) / grid_price) * 100 if grid_price > 0 else 0

    return {
        "grid_price":      grid_price,
        "breakeven_price": breakeven_price,
        "premium_pct":     premium_pct,
        "annual_loss":     annual_loss,
        "custom_total":    custom_total,
    }

# ─────────────────────────────────────────
# Map + State Selector (Market only)
# ─────────────────────────────────────────
if industry == "Market":
    left, right = st.columns([2, 1])
    with left:
        st.subheader("State-Level Grid Price Overview")
        fig_map = px.choropleth(
            df, locations="state", locationmode="USA-states",
            color="grid_price", scope="usa",
            hover_data=["saidi_hours", "volatility_index"],
            color_continuous_scale="Blues",
            labels={"grid_price": "Grid Price ($/kWh)"},
        )
        fig_map.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig_map, use_container_width=True)
    with right:
        st.subheader("Select State")
        selected_state = st.selectbox("State", sorted(df["state"]), index=4)
        selected_row   = df[df["state"] == selected_state].iloc[0]
        st.write("State Data:")
        st.dataframe(pd.DataFrame([selected_row]), use_container_width=True, hide_index=True)
else:
    st.subheader("🪖 Government Pricing Model — FBCF-Based Analysis")
    st.caption("Comparison baseline: Fully Burdened Cost of Fuel (FBCF), not grid electricity price.")
    selected_row = None

# ─────────────────────────────────────────
# Custom Cost Items (+ Button)
# ─────────────────────────────────────────
st.markdown("---")
st.subheader("➕ Additional Cost Items")
st.caption("Add custom annual cost/benefit factors. Use negative values for benefits (e.g. CHP savings).")

col_add1, col_add2, col_add3 = st.columns([3, 2, 1])
with col_add1:
    new_label = st.text_input("Item Label", placeholder="e.g. CHP Value, Regulatory Compliance")
with col_add2:
    new_value = st.number_input("Annual Value ($)", value=0, step=10_000,
                                help="Positive = extra cost. Negative = benefit/savings.")
with col_add3:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("＋ Add"):
        if new_label.strip():
            st.session_state.custom_items.append({"label": new_label.strip(), "value": float(new_value)})
            st.rerun()

if st.session_state.custom_items:
    st.markdown("**Current custom items:**")
    for idx, item in enumerate(st.session_state.custom_items):
        c1, c2, c3 = st.columns([3, 2, 1])
        with c1:
            st.write(f"📌 {item['label']}")
        with c2:
            sign = "+" if item["value"] >= 0 else ""
            st.write(f"{sign}${item['value']:,.0f} / year")
        with c3:
            if st.button("🗑️ Remove", key=f"remove_{idx}"):
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
    left2, right2 = st.columns(2)

    with left2:
        st.markdown("**Diesel Cost Breakdown (Annual)**")
        bd = res["breakdown"]
        fig_diesel = go.Figure(go.Bar(
            x=list(bd.values()), y=list(bd.keys()), orientation="h",
            marker_color=["#E63946","#F4A261","#E9C46A","#2A9D8F","#457B9D"],
            text=[f"${v:,.0f}" for v in bd.values()], textposition="outside"
        ))
        fig_diesel.update_layout(xaxis_title="Annual Cost ($)",
                                  margin=dict(l=0, r=80, t=10, b=0), height=300)
        st.plotly_chart(fig_diesel, use_container_width=True)

    with right2:
        st.markdown("**SMR Cost Breakdown (Annual)**")
        sbd = res["smr_breakdown"]
        fig_smr = go.Figure(go.Bar(
            x=list(sbd.values()), y=list(sbd.keys()), orientation="h",
            marker_color=["#1D3557","#457B9D","#A8DADC","#F1FAEE"],
            text=[f"${v:,.0f}" for v in sbd.values()], textposition="outside"
        ))
        fig_smr.update_layout(xaxis_title="Annual Cost ($)",
                               margin=dict(l=0, r=80, t=10, b=0), height=300)
        st.plotly_chart(fig_smr, use_container_width=True)

    st.markdown("**Cost Comparison: Diesel vs SMR**")
    fig_compare = go.Figure(go.Bar(
        x=["Diesel (FBCF Total)", "SMR (Lifecycle Total)"],
        y=[res["diesel_annual"], res["smr_annual"]],
        marker_color=["#E63946", "#2A9D8F"],
        text=[f"${res['diesel_annual']:,.0f}", f"${res['smr_annual']:,.0f}"],
        textposition="outside"
    ))
    fig_compare.update_layout(yaxis_title="Annual Cost ($)",
                               margin=dict(l=0, r=0, t=10, b=0), height=350)
    st.plotly_chart(fig_compare, use_container_width=True)

    # Decision Summary — st.text() prevents $ from being parsed as LaTeX
    st.subheader("Decision Summary")
    status     = "✅ SMR IS ECONOMICALLY JUSTIFIED" if advantage > 0 else "⚠️ REQUIRES STRATEGIC JUSTIFICATION"
    diesel_fmt = "{:,.0f}".format(res["diesel_annual"])
    smr_fmt    = "{:,.0f}".format(res["smr_annual"])
    price_fmt  = "{:.3f}".format(res["max_smr_price_kwh"])

    st.text(
        f"Under {mission_type} conditions in the {deployment_region} region,\n"
        f"a {required_mw} MW eVinci deployment over {operation_years} years\n"
        f"shows an estimated annual diesel burden of ${diesel_fmt} vs. SMR annual cost of ${smr_fmt}."
    )
    st.text(f"The maximum price Westinghouse can charge while remaining competitive: ${price_fmt}/kWh.")
    st.markdown(f"### {status}")

else:
    res = calc_market(
        required_mw, load_factor, risk_tolerance,
        usage_type, selected_row,
        st.session_state.custom_items
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Grid Price ($/kWh)",      f"${res['grid_price']:.3f}")
    c2.metric("Breakeven Price ($/kWh)", f"${res['breakeven_price']:.3f}")
    c3.metric("Justifiable Premium (%)", f"{res['premium_pct']:.1f}%")
    c4.metric("Annual Outage Loss ($)",  f"${res['annual_loss']:,.0f}")

    result_df = pd.DataFrame({
        "Price Type":    ["Grid", "Breakeven"],
        "Value ($/kWh)": [res["grid_price"], res["breakeven_price"]],
    })
    fig_bar = px.bar(result_df, x="Price Type", y="Value ($/kWh)", text_auto=".3f",
                     color="Price Type", color_discrete_sequence=["#457B9D", "#2A9D8F"])
    fig_bar.update_layout(showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)

    is_viable = res["premium_pct"] <= 20
    status    = "✅ ECONOMICALLY DEFENSIBLE" if is_viable else "⚠️ REQUIRES STRATEGIC JUSTIFICATION"
    st.subheader("Decision Summary")
    st.text(
        f"For {selected_state}, a {industry} facility requiring {required_mw} MW\n"
        f"at {load_factor}% load factor experiences an estimated annual outage cost of ${res['annual_loss']:,.0f}.\n"
        f"Resilience premium: {res['premium_pct']:.1f}% above local grid price."
    )
    st.markdown(f"### {status}")