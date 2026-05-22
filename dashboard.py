import os
import requests
import streamlit as st

API_BASE = os.getenv("AI_API_BASE", "http://127.0.0.1:8001")
API_KEY = os.getenv("AI_API_KEY", "")

headers = {"X-API-Key": API_KEY} if API_KEY else {}

st.set_page_config(page_title="AI Investing Ops Dashboard", layout="wide")
st.title("AI Investing Operations Dashboard")

col1, col2, col3 = st.columns(3)

health = {}
try:
    health = requests.get(f"{API_BASE}/health", timeout=5).json()
except Exception as e:
    st.error(f"Health endpoint unavailable: {e}")

col1.metric("Service Status", health.get("status", "unknown"))
col1.caption(health.get("time", ""))

summary = None
try:
    response = requests.get(f"{API_BASE}/dashboard/summary", headers=headers, timeout=5)
    response.raise_for_status()
    summary = response.json()
    col2.metric("Manual Approval", "Required" if summary["manual_approval_required"] else "Off")
    col3.metric("Autonomous", "On" if summary["autonomous_execution"] else "Off")
except Exception as e:
    col2.metric("Manual Approval", "Unknown")
    col3.metric("Autonomous", "Unknown")
    st.warning(f"Summary unavailable: {e}")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("System Summary")
    if summary:
        st.json(summary)
    else:
        st.info("Summary will appear after the API key is configured.")

with right:
    st.subheader("Day-0 Tick")
    cash = st.number_input("Cash", min_value=0.0, value=100.0, step=10.0)
    equity = st.number_input("Equity", min_value=0.0, value=100.0, step=10.0)
    peak_equity = st.number_input("Peak equity", min_value=0.0, value=100.0, step=10.0)
    daily_pnl = st.number_input("Daily PnL", value=0.0, step=1.0)
    if st.button("Run Shadow Tick"):
        payload = {
            "cash": cash,
            "equity": equity,
            "peak_equity": peak_equity,
            "daily_pnl": daily_pnl,
        }
        try:
            result = requests.post(
                f"{API_BASE}/simulate_tick",
                headers={**headers, "Content-Type": "application/json"},
                json=payload,
                timeout=5,
            )
            result.raise_for_status()
            st.json(result.json())
        except Exception as e:
            st.error(f"Simulation endpoint error: {e}")

st.divider()
st.subheader("Broker Status")
try:
    response = requests.get(f"{API_BASE}/broker/status", headers=headers, timeout=5)
    response.raise_for_status()
    st.json(response.json())
except Exception as e:
    st.error(f"Broker status endpoint error: {e}")

st.divider()
st.subheader("Recent Audit")
try:
    response = requests.get(f"{API_BASE}/audit", headers=headers, timeout=5)
    response.raise_for_status()
    audit = response.json()
    st.json(audit)
except Exception as e:
    st.error(f"Audit endpoint error: {e}")
