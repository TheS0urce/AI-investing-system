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

with broker_left:
    st.subheader("Paper Ops Snapshot")
    if st.button("Run Paper Ops Snapshot"):
        try:
            response = requests.get(
                f"{API_BASE}/broker/paper/ops_snapshot",
                headers=headers,
                params={"watch_limit": 500},
                timeout=20,
            )
            response.raise_for_status()
            st.json(response.json())
        except Exception as e:
            st.error(f"Paper ops snapshot error: {e}")

with broker_right:
    st.subheader("Paper Readiness")
    if st.button("Run Paper Readiness"):
        try:
            response = requests.get(
                f"{API_BASE}/broker/paper/readiness",
                headers=headers,
                params={"watch_limit": 500},
                timeout=15,
            )
            response.raise_for_status()
            st.json(response.json())
        except Exception as e:
            st.error(f"Paper readiness error: {e}")

with broker_right:
    st.subheader("Dry-Run Paper Drill")
    if st.button("Run Dry-Run Paper Drill"):
        try:
            response = requests.post(
                f"{API_BASE}/broker/paper/order_drill",
                headers={**headers, "Content-Type": "application/json"},
                json={"symbol": "QQQ", "side": "BUY", "quantity": 0.001, "limit_price": 1.00},
                timeout=15,
            )
            response.raise_for_status()
            st.json(response.json())
        except Exception as e:
            st.error(f"Paper drill error: {e}")

with broker_left:
    st.subheader("Strategy Quality")
    if st.button("Run Strategy Quality"):
        try:
            response = requests.get(
                f"{API_BASE}/broker/paper/strategy_quality",
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            st.json(response.json())
        except Exception as e:
            st.error(f"Strategy quality error: {e}")

with broker_left:
    st.subheader("Strategy Scenarios")
    if st.button("Run Strategy Scenarios"):
        try:
            response = requests.get(
                f"{API_BASE}/broker/paper/strategy_scenarios",
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            st.json(response.json())
        except Exception as e:
            st.error(f"Strategy scenario error: {e}")

with broker_right:
    st.subheader("GO/NO-GO Checklist")
    if st.button("Show GO/NO-GO Checklist"):
        try:
            response = requests.get(
                f"{API_BASE}/broker/paper/go_no_go_checklist",
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            st.json(response.json())
        except Exception as e:
            st.error(f"GO/NO-GO checklist error: {e}")

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
st.subheader("Real-Time Paper Preview")
market_left, market_right = st.columns(2)

with market_left:
    market_symbol = st.text_input("Market symbol", value="QQQ").upper()
    market_feed = st.selectbox("Market data feed", ["iex", "delayed_sip", "sip"], index=0)
    if st.button("Fetch Market Snapshot"):
        try:
            response = requests.get(
                f"{API_BASE}/broker/paper/market_snapshot",
                headers=headers,
                params={"symbol": market_symbol, "feed": market_feed},
                timeout=15,
            )
            response.raise_for_status()
            st.json(response.json())
        except Exception as e:
            st.error(f"Market snapshot error: {e}")

with market_right:
    preview_cash = st.number_input("Preview cash", min_value=0.0, value=100.0, step=10.0)
    preview_equity = st.number_input("Preview equity", min_value=0.0, value=100.0, step=10.0)
    use_paper_account = st.checkbox("Use paper account state", value=True)
    if st.button("Fetch Paper Account"):
        try:
            response = requests.get(
                f"{API_BASE}/broker/paper/account",
                headers=headers,
                timeout=15,
            )
            response.raise_for_status()
            st.json(response.json())
        except Exception as e:
            st.error(f"Paper account error: {e}")
    if st.button("Fetch Paper Market Clock"):
        try:
            response = requests.get(
                f"{API_BASE}/broker/paper/clock",
                headers=headers,
                timeout=15,
            )
            response.raise_for_status()
            st.json(response.json())
        except Exception as e:
            st.error(f"Paper clock error: {e}")
    if st.button("Run Paper Strategy Preview"):
        try:
            response = requests.get(
                f"{API_BASE}/broker/paper/strategy_preview",
                headers=headers,
                params={
                    "symbol": market_symbol,
                    "feed": market_feed,
                    "cash": preview_cash,
                    "equity": preview_equity,
                    "peak_equity": preview_equity,
                    "daily_pnl": 0,
                    "consecutive_losses": 0,
                    "use_paper_account": use_paper_account,
                },
                timeout=15,
            )
            response.raise_for_status()
            st.json(response.json())
        except Exception as e:
            st.error(f"Strategy preview error: {e}")

st.divider()
st.subheader("Paper Watch Mode")
watch_symbol = st.text_input("Watch symbol", value="QQQ").upper()
watch_feed = st.selectbox("Watch feed", ["iex", "delayed_sip", "sip"], index=0)
allow_closed_market = st.checkbox("Allow closed-market watch evaluation", value=False)
watch_left, watch_right = st.columns(2)

with watch_left:
    if st.button("Record Watch Tick"):
        try:
            response = requests.post(
                f"{API_BASE}/broker/paper/watch_tick",
                headers={**headers, "Content-Type": "application/json"},
                json={
                    "symbol": watch_symbol,
                    "feed": watch_feed,
                    "use_paper_account": True,
                    "allow_closed_market": allow_closed_market,
                },
                timeout=15,
            )
            response.raise_for_status()
            st.json(response.json())
        except Exception as e:
            st.error(f"Watch tick error: {e}")

with watch_right:
    if st.button("Refresh Watch History"):
        try:
            response = requests.get(
                f"{API_BASE}/broker/paper/watch_history",
                headers=headers,
                params={"limit": 20},
                timeout=10,
            )
            response.raise_for_status()
            st.json(response.json())
        except Exception as e:
            st.error(f"Watch history error: {e}")

summary_left, export_left, export_right = st.columns(3)
with summary_left:
    if st.button("Summarize Watch History"):
        try:
            response = requests.get(
                f"{API_BASE}/broker/paper/watch_summary",
                headers=headers,
                params={"limit": 500},
                timeout=10,
            )
            response.raise_for_status()
            st.json(response.json())
        except Exception as e:
            st.error(f"Watch summary error: {e}")

with export_left:
    if st.button("Export Watch CSV"):
        try:
            response = requests.get(
                f"{API_BASE}/broker/paper/watch_export",
                headers=headers,
                params={"format": "csv", "limit": 500},
                timeout=10,
            )
            response.raise_for_status()
            st.download_button(
                "Download Watch CSV",
                data=response.text,
                file_name="paper_watch_history.csv",
                mime="text/csv",
            )
        except Exception as e:
            st.error(f"Watch CSV export error: {e}")

with export_right:
    if st.button("Export Watch JSONL"):
        try:
            response = requests.get(
                f"{API_BASE}/broker/paper/watch_export",
                headers=headers,
                params={"format": "jsonl", "limit": 500},
                timeout=10,
            )
            response.raise_for_status()
            st.download_button(
                "Download Watch JSONL",
                data=response.text,
                file_name="paper_watch_history.jsonl",
                mime="application/x-ndjson",
            )
        except Exception as e:
            st.error(f"Watch JSONL export error: {e}")

st.divider()
st.subheader("Recent Audit")
try:
    response = requests.get(f"{API_BASE}/audit", headers=headers, timeout=5)
    response.raise_for_status()
    audit = response.json()
    st.json(audit)
except Exception as e:
    st.error(f"Audit endpoint error: {e}")
