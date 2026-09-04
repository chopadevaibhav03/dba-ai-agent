"""
Streamlit dashboard for the OS monitoring agent.

Run with:
    streamlit run app.py

Requires collector.py to be running separately (or in the background)
to populate metrics.db with data to display.
"""

import json
import sqlite3

import pandas as pd
import streamlit as st

import config
from analyzer import analyze
from automation import WHITELIST, execute
from report import generate_and_save
from chat_agent import parse_intent
from service_control import perform_action, list_services, service_exists

st.set_page_config(page_title="OS Monitoring Agent", layout="wide")


# ---------- data loaders ----------

def load_metrics() -> pd.DataFrame:
    conn = sqlite3.connect(config.DB_PATH)
    try:
        df = pd.read_sql_query("SELECT * FROM metrics ORDER BY ts DESC LIMIT 500", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    if not df.empty:
        df["ts"] = pd.to_datetime(df["ts"])
        df = df.sort_values("ts")
    return df


def load_report_history() -> pd.DataFrame:
    conn = sqlite3.connect(config.DB_PATH)
    try:
        df = pd.read_sql_query(
            "SELECT ts, severity, issue, markdown_path FROM reports ORDER BY ts DESC LIMIT 20",
            conn,
        )
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


# ---------- monitoring tab ----------

def render_monitoring_tab():
    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button("Analyze now", type="primary"):
            with st.spinner("Asking the local model to review recent metrics..."):
                result = analyze()
                path = generate_and_save(result)
            st.session_state["last_result"] = result
            st.success(f"Report saved: {path}")

    df = load_metrics()

    if df.empty:
        st.info("No metrics yet. Start the collector in another terminal: `python3 collector.py`")
    else:
        latest = df.iloc[-1]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("CPU %", f"{latest['cpu_percent']:.1f}")
        m2.metric("Memory %", f"{latest['mem_percent']:.1f}")
        m3.metric("Swap %", f"{latest['swap_percent']:.1f}")
        disk = json.loads(latest["disk_json"]) if latest["disk_json"] else {}
        root_pct = disk.get("/", {}).get("percent", 0)
        m4.metric("Disk / %", f"{root_pct:.1f}")

        st.subheader("Trends")
        chart_df = df.set_index("ts")[["cpu_percent", "mem_percent", "swap_percent"]]
        st.line_chart(chart_df)

    st.divider()
    st.subheader("Latest analysis")
    result = st.session_state.get("last_result")
    if result:
        severity = result.get("severity", "info")
        badge = {"critical": "🔴", "warning": "🟠", "info": "🟢"}.get(severity, "🟢")
        st.markdown(f"**{badge} {severity.upper()}** — {result.get('issue', '')}")
        st.write(result.get("root_cause", ""))

        actions = result.get("recommended_actions", [])
        if actions:
            st.markdown("**Recommended actions** (review before applying):")
            for key in actions:
                if key not in WHITELIST:
                    st.write(f"- {key} (not whitelisted, skipped)")
                    continue
                desc, cmd = WHITELIST[key]
                c1, c2 = st.columns([4, 1])
                c1.write(f"`{key}` — {desc}  \n`$ {cmd}`")
                if c2.button("Apply fix", key=f"apply_{key}"):
                    res = execute(key, confirm=True)
                    if res.get("ok"):
                        st.success(f"Executed: {key}")
                    else:
                        st.error(res.get("error") or res.get("stderr"))
        else:
            st.write("No action recommended.")
    else:
        st.write("Click **Analyze now** to get a diagnosis from the local model.")

    st.divider()
    st.subheader("Report history")
    hist = load_report_history()
    if hist.empty:
        st.write("No reports yet.")
    else:
        st.dataframe(hist, use_container_width=True)


# ---------- chat control tab ----------

def render_chat_tab():
    st.caption(
        "Type things like \"stop splunkd\", \"is nginx running?\", \"restart sshd\", "
        "\"list running services\". State-changing actions ask for confirmation before running."
    )

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "pending_action" not in st.session_state:
        st.session_state.pending_action = None

    # replay history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # if a state-changing action is awaiting confirmation, show it here
    if st.session_state.pending_action:
        pa = st.session_state.pending_action
        with st.chat_message("assistant"):
            st.warning(f"Confirm: **{pa['action']}** service **{pa['service']}**?")
            c1, c2 = st.columns(2)
            if c1.button("Yes, do it", key="confirm_yes"):
                res = perform_action(pa["service"], pa["action"], confirm=True)
                st.session_state.pending_action = None
                if res.get("ok"):
                    reply = f"Done. `{res['service']}` is now **{res.get('new_state', 'unknown')}**."
                else:
                    reply = f"Failed: {res.get('error') or res.get('stderr')}"
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
                st.rerun()
            if c2.button("Cancel", key="confirm_no"):
                st.session_state.pending_action = None
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": "Cancelled, no changes made."}
                )
                st.rerun()

    prompt = st.chat_input("e.g. stop splunkd")
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        with st.spinner("Thinking..."):
            intent = parse_intent(prompt)

        reply_text = intent.get("reply", "")
        service = intent.get("service")
        action = intent.get("action")

        if intent["intent"] == "list_services":
            services = list_services(active_only=True)
            names = ", ".join(s["unit"] for s in services[:25]) or "none found"
            reply_text = f"Running services: {names}"

        elif intent["intent"] == "service_action" and service and action:
            if not service_exists(service):
                reply_text = f"I don't see a service called '{service}' on this system."
            elif action == "status":
                res = perform_action(service, "status")
                reply_text = (
                    f"`{res['service']}` is **{res['state']}**."
                    if res.get("ok") else f"Couldn't check status: {res.get('error')}"
                )
            else:
                # start/stop/restart -- queue for confirmation, don't execute yet
                st.session_state.pending_action = {"service": service, "action": action}
                reply_text = reply_text or f"About to {action} {service} -- please confirm below."

        elif intent["intent"] == "unclear":
            reply_text = reply_text or "Which service did you mean?"

        elif intent["intent"] == "chitchat":
            reply_text = reply_text or "I mainly handle service start/stop/status requests here."

        st.session_state.chat_history.append({"role": "assistant", "content": reply_text})
        st.rerun()


# ---------- page ----------

st.title("OS monitoring agent")
st.caption("Local RHEL 9 host · metrics via psutil · diagnosis via local Ollama (llama3.2)")

tab_monitor, tab_chat = st.tabs(["Monitoring", "Chat control"])

with tab_monitor:
    render_monitoring_tab()

with tab_chat:
    render_chat_tab()
