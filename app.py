"""Streamlit interface for the DayQuest local MVP."""

from __future__ import annotations

import html

import streamlit as st

from dayquest.agent import run_agent


st.set_page_config(page_title="DayQuest", page_icon="🧭", layout="wide")
st.markdown(
    """
    <style>
    .stApp {background: linear-gradient(180deg, #0d1722 0%, #152536 100%);}
    .quest-card {background:#1e3245; border:1px solid #49677e; border-radius:14px;
      padding:1.1rem; margin:.65rem 0; transition:transform .18s ease, border-color .18s ease;}
    .quest-card:hover {transform:translateY(-2px); border-color:#d8ad63;}
    .quest-kicker {color:#d8ad63; font-size:.78rem; letter-spacing:.08em; text-transform:uppercase;}
    .quest-title {font-size:1.22rem; font-weight:700; margin:.2rem 0 .45rem;}
    .badge {display:inline-block; padding:.2rem .55rem; border-radius:20px; background:#2c4b61; margin-right:.3rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🧭 DayQuest")
st.caption("A privacy-first local agent that reconstructs a fragmented day as a safe fantasy adventure log.")
st.info("Synthetic demo data only — no personal accounts, sponsor APIs, or external models are connected.")

run_clicked = st.button("Run DayQuest Agent", type="primary", use_container_width=True)
if run_clicked:
    with st.spinner("The agent is observing, deciding, and building the chronicle…"):
        st.session_state.dayquest_state = run_agent()

state = st.session_state.get("dayquest_state")
if state is None:
    st.subheader("Agent Status")
    st.write("Ready. Run the agent to begin the local five-iteration loop.")
else:
    status_col, iteration_col, sources_col, scenes_col = st.columns(4)
    status_col.metric("Agent Status", "Finished" if state.finished else "Running")
    iteration_col.metric("Iterations", f"{state.iteration} / {state.max_iterations}")
    sources_col.metric("Sources Queried", len(state.queried_sources))
    scenes_col.metric("Scenes", len(state.scenes))

    if state.errors:
        st.warning("One or more sources had problems; available sources were still processed.")
        for error in state.errors:
            st.error(error)

    st.subheader("Reconstructed Timeline")
    if state.events:
        st.dataframe(
            [
                {
                    "Start": event.start_time,
                    "End": event.end_time,
                    "Type": event.event_type,
                    "Summary": event.summary,
                    "Source": event.source,
                    "Confidence": event.confidence,
                    "Sensitivity": event.sensitivity,
                    "Redacted": event.redacted,
                }
                for event in state.events
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.caption("Evidence payloads are intentionally withheld from the rendered timeline and story.")
        if state.missing_time_ranges:
            st.write("Remaining time gaps: " + ", ".join(state.missing_time_ranges))
    else:
        st.warning("No events could be reconstructed. Check the source errors above.")

    st.subheader("Privacy Gate")
    gate_columns = st.columns(3)
    for column, bucket in zip(gate_columns, ("Detected", "Removed", "Generalized")):
        values = state.privacy_risks[bucket]
        with column:
            st.metric(bucket, len(values))
            if values:
                for value in values:
                    st.write(f"• {value}")
            else:
                st.caption("None")

    st.subheader("Agent Loop Trace")
    if state.trace:
        for entry in state.trace:
            with st.expander(f"Iteration {entry.iteration} · {entry.action}", expanded=True):
                st.markdown(f"**Observation:** {entry.observation}")
                st.markdown(f"**Decision:** {entry.decision}")
                st.markdown(f"**Reason:** {entry.reason}")

    st.subheader("Fantasy Story Log")
    if state.scenes:
        for scene in state.scenes:
            st.markdown(
                f"""
                <div class="quest-card">
                  <div class="quest-kicker">Scene {scene.scene_number} · {html.escape(scene.approximate_time)}</div>
                  <div class="quest-title">{html.escape(scene.title)}</div>
                  <span class="badge">{html.escape(scene.fictional_event)}</span>
                  <p>{html.escape(scene.narration)}</p>
                  <small><b>Based on:</b> {html.escape(', '.join(scene.based_on_event_ids))}<br>
                  <b>Fictional embellishment:</b> {html.escape(scene.fictional_embellishment)}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.warning("No story was generated because the safety or minimum-event condition was not met.")

    st.subheader("Stop Reason")
    if state.stop_reason.startswith("Success"):
        st.success(state.stop_reason)
    else:
        st.warning(state.stop_reason)
    if state.evaluation:
        st.json(state.evaluation)

st.subheader("Sponsor Integration Status")
sponsor_columns = st.columns(3)
for column, sponsor in zip(sponsor_columns, ("Akash", "Nexla", "Pomerium")):
    column.warning(f"{sponsor}: Not connected")
