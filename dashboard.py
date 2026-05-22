import os
import requests
import streamlit as st

API_BASE = os.getenv("AI_API_BASE", "http://127.0.0.1:8001")
API_KEY = os.getenv("AI_API_KEY", "")

headers = {"X-API-Key": API_KEY} if API_KEY else {}


def order_payload(prefix: str, include_confirm: bool = False) -> dict[str, object]:
    payload: dict[str, object] = {
        "symbol": st.text_input("Symbol", value="QQQ", key=f"{prefix}_symbol").upper(),
        "side": st.segmented_control("Side", ["BUY", "SELL"], default="BUY", key=f"{prefix}_side"),
        "quantity": st.number_input("Quantity", min_value=0.0, value=0.01, step=0.01, format="%.8f", key=f"{prefix}_qty"),
        "limit_price": st.number_input("Limit price", min_value=0.0, value=430.0, step=0.01, format="%.2f", key=f"{prefix}_price"),
        "reason": "dashboard manual paper order",
    }
    if include_confirm:
        payload["confirm"] = st.text_input("Confirmation", value="", key=f"{prefix}_confirm")
    return payload

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
    broker_status = response.json()
    st.json(broker_status)
except Exception as e:
    broker_status = None
    st.error(f"Broker status endpoint error: {e}")

st.divider()
st.subheader("Paper Broker Controls")
broker_left, broker_right = st.columns(2)

with broker_left:
    st.subheader("Order Preview")
    preview_payload = order_payload("preview")
    if st.button("Preview Paper Order"):
        try:
            response = requests.post(
                f"{API_BASE}/broker/paper/order_preview",
                headers={**headers, "Content-Type": "application/json"},
                json=preview_payload,
                timeout=10,
            )
            response.raise_for_status()
            st.json(response.json())
        except Exception as e:
            st.error(f"Paper preview error: {e}")

with broker_right:
    st.subheader("Recent Paper Orders")
    if st.button("Refresh Paper Orders"):
        try:
            response = requests.get(
                f"{API_BASE}/broker/paper/orders",
                headers=headers,
                params={"status": "all", "limit": 20},
                timeout=10,
            )
            response.raise_for_status()
            st.json(response.json())
        except Exception as e:
            st.error(f"Paper orders error: {e}")

with st.expander("Submit Paper Order"):
    submit_payload = order_payload("submit", include_confirm=True)
    if st.button("Submit Confirmed Paper Order", type="primary"):
        if submit_payload.get("confirm") != "SUBMIT_PAPER_ORDER":
            st.error("Type SUBMIT_PAPER_ORDER to enable paper submission.")
        else:
            try:
                response = requests.post(
                    f"{API_BASE}/broker/paper/submit_order",
                    headers={**headers, "Content-Type": "application/json"},
                    json=submit_payload,
                    timeout=15,
                )
                response.raise_for_status()
                st.json(response.json())
            except Exception as e:
                st.error(f"Paper submit error: {e}")

with st.expander("Cancel Open Paper Orders"):
    cancel_confirm = st.text_input("Cancel confirmation", value="", key="cancel_paper_confirm")
    if st.button("Cancel Open Paper Orders", type="secondary"):
        if cancel_confirm != "CANCEL_PAPER_ORDERS":
            st.error("Type CANCEL_PAPER_ORDERS to request paper-order cancellation.")
        else:
            try:
                response = requests.post(
                    f"{API_BASE}/broker/paper/cancel_orders",
                    headers={**headers, "Content-Type": "application/json"},
                    json={"confirm": cancel_confirm},
                    timeout=15,
                )
                response.raise_for_status()
                st.json(response.json())
            except Exception as e:
                st.error(f"Paper cancel error: {e}")

st.divider()
st.subheader("Recent Audit")
try:
    response = requests.get(f"{API_BASE}/audit", headers=headers, timeout=5)
    response.raise_for_status()
    audit = response.json()
    st.json(audit)
except Exception as e:
    st.error(f"Audit endpoint error: {e}")
