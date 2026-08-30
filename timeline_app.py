"""Local, no-key review surface for the DayQuest evidence timeline MVP."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from dayquest.timeline_mvp import readable_case_summary


PROJECT_ROOT = Path(__file__).resolve().parent
ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "evaluation" / "top1" / "mvp"
REPORT_ROOT = ARTIFACT_ROOT / "reports"


@st.cache_data
def load_review_data() -> tuple[dict, list[dict]]:
    aggregate = json.loads((ARTIFACT_ROOT / "aggregate.json").read_text("utf-8"))
    reports = [
        json.loads((REPORT_ROOT / f"{case_id}.json").read_text("utf-8"))
        for case_id in aggregate["case_ids"]
    ]
    return aggregate, reports


def pointer_label(pointer: dict) -> str:
    return (
        f"{pointer['evidence_id']} · {pointer['source']} · "
        f"{pointer['field']} · {pointer['safe_record_id'][:16]}…"
    )


st.set_page_config(page_title="DayQuest Evidence Review", layout="wide")
st.title("DayQuest Evidence Review")
st.caption("本地、无密钥、synthetic-safe（合成安全）证据审核面；不会读取 .env 或外部账户。")

try:
    aggregate, reports = load_review_data()
except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
    st.error(f"审核产物不可用：{exc}")
    st.stop()

counts = aggregate["counts"]
metrics = st.columns(5)
metrics[0].metric("案例", counts["total"])
metrics[1].metric("Supported（已支持）", counts["claim_supported"])
metrics[2].metric("Unknown（证据不足）", counts["claim_unknown"])
metrics[3].metric("Conflict（证据冲突）", counts["claim_conflict"])
metrics[4].metric("False Supported", counts["false_supported"])
st.info(
    "证据链范围：8 个案例执行真实 localhost MCP acquisition；其中 5 个案例的最终场景证据直接来自未修改的 MCP response，"
    "3 个案例在 MCP acquisition 后执行明确的受控 missing/conflict 变换；另有 4 个受控 tool-fault fixtures。"
)

summary_rows = []
for report in reports:
    view = readable_case_summary(report)
    summary_rows.append(
        {
            "案例": view["case_id"],
            "类型": view["family"],
            "Claim 状态": view["status"],
            "Policy": view["policy_status"],
            "任务判定": view["task_verdict"],
            "Tool fault": view["tool_fault"] or "—",
        }
    )

st.subheader("12-case 产品评测矩阵")
st.dataframe(summary_rows, use_container_width=True, hide_index=True)

selected_id = st.selectbox(
    "选择一个案例查看证据",
    options=[report["case_id"] for report in reports],
    index=4,
)
selected_report = next(report for report in reports if report["case_id"] == selected_id)
selected = readable_case_summary(selected_report)

st.subheader(f"案例审核 · {selected_id}")
left, right = st.columns([3, 2])
with left:
    st.markdown(f"**待核验陈述：** {selected['statement']}")
    st.markdown(f"**Claim 状态：** `{selected['status']}`")
    st.write(selected["status_explanation"])

    st.markdown("**支持证据指针**")
    if selected["supporting"]:
        for pointer in selected["supporting"]:
            st.write(f"- {pointer_label(pointer)}")
    else:
        st.write("- 无")

    st.markdown("**冲突证据指针**")
    if selected["contradicting"]:
        for pointer in selected["contradicting"]:
            st.write(f"- {pointer_label(pointer)}")
    else:
        st.write("- 无")

    st.markdown("**缺失的必要证据**")
    st.write(", ".join(selected["missing"]) if selected["missing"] else "无")

with right:
    st.markdown("**Policy（策略合规）与 Claim 分开判定**")
    st.write(f"Policy：`{selected['policy_status']}`")
    if selected["policy_violations"]:
        for violation in selected["policy_violations"]:
            st.error(violation)
    else:
        st.success("没有观察到策略违规。")
    st.write(f"任务判定：`{selected['task_verdict']}`")
    st.write(f"Tool fault：`{selected['tool_fault'] or 'none'}`")
    if selected["story_eligible"]:
        st.markdown("**Story 可用的事实输入**")
        for fact in selected["story_facts"]:
            st.write(f"- {fact}")
    else:
        st.info("Story 不得消费此案例：仅 Supported 且 policy compliant 的 claim 可进入叙事。")

st.divider()
st.caption(
    "Claim boundary：这是 12-case 本地开发与产品验收切片，不代表生产可靠性、"
    "私有数据适用性、通用 secret 扫描、跨平台路径检测、统计泛化、安全认证或对成熟评测框架的全面优越性。"
)
