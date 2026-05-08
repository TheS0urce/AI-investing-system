import os
import requests
import streamlit as st

API_BASE = os.getenv("AI_API_BASE", "http://127.0.0.1:8000")
API_KEY = os.getenv("AI_API_KEY", "")

headers = {"X-API-Key": API_KEY} if API_KEY else {}

st.set_page_config(page_title="AI Investing Ops Dashboard", layout="wide")
st.title("AI Investing Operations Dashboard")

col1, col2, col3 = st.columns(3)

# Health
health = requests.get(f"{API_BASE}/health", timeout=5).json()
col1.metric("Service Status", health.get("status", "unknown"))
col1.caption(health.get("time", ""))

# Summary
try:
    summary = requests.get(f"{API_BASE}/dashboard/summary", headers=headers, timeout=5).json()
    col2.metric("Equity", f"{summary['risk']['equity']:.2f}")
    col3.metric("30D Drawdown", f"{summary['risk']['rolling_30d_drawdown_pct']*100:.2f}%")
except Exception as e:
    st.warning(f"Summary unavailable: {e}")
    summary = None

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Risk Snapshot")
    try:
        risk = requests.get(f"{API_BASE}/dashboard/risk", headers=headers, timeout=5).json()
        st.json(risk)
    except Exception as e:
        st.error(f"Risk endpoint error: {e}")

with right:
    st.subheader("Scaling Window Decision")
    try:
        scaling = requests.get(f"{API_BASE}/dashboard/scaling-window", headers=headers, timeout=5).json()
        st.json(scaling)
    except Exception as e:
        st.error(f"Scaling endpoint error: {e}")

st.divider()
st.subheader("Governance")
try:
    governance = requests.get(f"{API_BASE}/dashboard/governance", headers=headers, timeout=5).json()
    st.json(governance)
except Exception as e:
    st.error(f"Governance endpoint error: {e}")

st.divider()
st.subheader("Recent Audit")
try:
    audit = requests.get(f"{API_BASE}/dashboard/audit", headers=headers, timeout=5).json()
    st.json(audit)
except Exception as e:
    st.error(f"Audit endpoint error: {e}")
