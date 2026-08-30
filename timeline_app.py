"""No-key product and evaluation surface for the DayQuest flagship candidate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import streamlit as st

from dayquest.product_timeline import PRODUCT_DEMO_ID, build_product_demo
from dayquest.product_v2 import PRODUCT_V2_ARTIFACT_ID, build_product_v2, product_v2_identity
from dayquest.timeline_mvp import readable_case_summary


PROJECT_ROOT = Path(__file__).resolve().parent
ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "evaluation" / "top1" / "mvp"
REPORT_ROOT = ARTIFACT_ROOT / "reports"
COMPARISON_OUTPUT = PROJECT_ROOT / "artifacts" / "evaluation" / "comparison" / "benchmark.json"
STATUS_COLORS = {"Supported": "#1f9d68", "Unknown": "#d28b19", "Conflict": "#d45d5d"}
TIME_LABELS = {"morning": "上午", "afternoon": "下午", "evening": "晚上", "unknown": "时间未知"}


@st.cache_data
def load_review_data() -> tuple[dict, list[dict], dict]:
    aggregate = json.loads((ARTIFACT_ROOT / "aggregate.json").read_text("utf-8"))
    reports = [json.loads((REPORT_ROOT / f"{case_id}.json").read_text("utf-8")) for case_id in aggregate["case_ids"]]
    comparison = json.loads(COMPARISON_OUTPUT.read_text("utf-8"))
    return aggregate, reports, comparison


@st.cache_data
def load_product_demo() -> dict:
    return build_product_demo(PROJECT_ROOT)


@st.cache_data
def load_product_v2() -> dict:
    return build_product_v2(PROJECT_ROOT)


def pointer_label(pointer: dict) -> str:
    return f"{pointer['evidence_id']} · {pointer['source']} · {pointer['field']} · {pointer['safe_record_id'][:16]}…"


def render_pointer_group(title: str, pointers: list[dict]) -> None:
    st.markdown(f"**{title}**")
    if not pointers:
        st.caption("无")
        return
    for pointer in pointers:
        st.write(f"- {pointer_label(pointer)}")


st.set_page_config(page_title="DayQuest", page_icon="🧭", layout="wide")
st.markdown(
    """
    <style>
      .block-container {max-width: 1180px; padding-top: 2rem;}
      .hero {padding: 1.4rem 1.6rem; border: 1px solid #36546b; border-radius: 18px;
        background: linear-gradient(125deg, #102333 0%, #1a3547 100%); margin-bottom: 1rem;}
      .hero h1 {margin: 0 0 .4rem 0; font-size: 2.4rem;}
      .hero p {margin: 0; color: #d6e3ec; font-size: 1.05rem;}
      .status-badge {display:inline-block; color:white; border-radius:999px; padding:.18rem .65rem;
        font-size:.82rem; font-weight:700; margin-left:.35rem;}
      .timeline-card {border-left: 4px solid #789; padding:.5rem 1rem .8rem 1rem; margin:.6rem 0 1rem;}
      .timeline-card h3 {margin:.15rem 0 .35rem;}
      .muted {color:#9fb1bf;}
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="hero"><h1>🧭 DayQuest · Evidence Replay</h1>
    <p>个人活动证据的 epistemic timeline debugger（认知状态时间线调试器）：不仅解释当前判断，还能安全预演证据变化会如何传播。</p></div>
    """,
    unsafe_allow_html=True,
)
st.caption("本地 · 无 API key · synthetic-safe 数据。Supported / Unknown / Conflict 不会被摘要悄悄改写。")

try:
    aggregate, reports, comparison = load_review_data()
    product_demo = load_product_demo()
    product_v2 = load_product_v2()
except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
    st.error(f"本地证据产物不可用：{exc}")
    st.stop()

product_tab, review_tab, boundary_tab = st.tabs(["我的一天 · V2", "Evaluation / Review", "工程与边界"])

with product_tab:
    control_left, control_right = st.columns([3, 1])
    with control_left:
        st.selectbox("选择本地演示日", [product_demo["fixture_label"]], key="product_fixture")
    with control_right:
        st.write("")
        st.write("")
        reload_clicked = st.button("重新载入并重建", type="primary", use_container_width=True)
    if reload_clicked:
        st.cache_data.clear()
        product_demo = load_product_demo()
        st.success("已从本地、版本化证据产物重新构建。")

    st.subheader("我的一天")
    metrics = st.columns(4)
    metrics[0].metric("时间线项目", product_demo["counts"]["items"])
    metrics[1].metric("Supported", product_demo["counts"]["supported"])
    metrics[2].metric("Unknown", product_demo["counts"]["unknown"])
    metrics[3].metric("Conflict", product_demo["counts"]["conflict"])

    for item in product_demo["timeline"]:
        color = STATUS_COLORS[item["status"]]
        time_label = TIME_LABELS.get(item["time_range"], item["time_range"])
        st.markdown(
            f"""
            <div class="timeline-card" style="border-left-color:{color}">
              <span class="muted">{time_label}</span>
              <span class="status-badge" style="background:{color}">{item['status']} · {item['status_label']}</span>
              <h3>{item['title']}</h3><div>{item['statement']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander("为什么系统这样判断？", expanded=item["status"] != "Supported"):
            render_pointer_group("支持证据", item["supporting_pointers"])
            render_pointer_group("冲突证据", item["contradicting_pointers"])
            st.markdown("**缺失的必要证据**")
            st.write(", ".join(item["missing_requirements"]) or "无")
            st.markdown("**Policy（独立于 Claim 状态）**")
            st.write(item["policy_status"])
            if item["policy_violations"]:
                st.error("；".join(item["policy_violations"]))

    st.subheader("受约束摘要")
    st.success(product_demo["constrained_summary"]["text"])
    st.caption(
        "摘要规则：只使用 Supported 且 policy-compliant 的事实。"
        f"本次纳入 {product_demo['counts']['summary_facts']} 条；Unknown / Conflict 保留在时间线中但不事实化。"
    )

    st.divider()
    st.subheader("Evidence Replay Lab（证据回放实验室）")
    st.write(
        "选择一次可逆干预，观察同一条 claim（主张）如何改变状态，以及这个变化是否能进入预览摘要。"
        "所有操作只发生在内存中的 preview（预览）；上方事实基线与 canonical summary（规范摘要）不会被改写。"
    )
    replay_by_label = {item["label"]: item for item in product_v2["replays"]}
    selected_label = st.selectbox("选择证据干预", list(replay_by_label), key="v2_replay")
    replay = replay_by_label[selected_label]
    st.caption(replay["description"])

    before_col, arrow_col, after_col = st.columns([4, 1, 4])
    with before_col:
        st.markdown("#### Before · 当前证据")
        st.markdown(
            f"<span class='status-badge' style='background:{STATUS_COLORS[replay['before']['status']]}'>{replay['before']['status']}</span>",
            unsafe_allow_html=True,
        )
        render_pointer_group("证据指针", replay["before"]["pointers"])
        st.markdown("**缺失的必要证据**")
        st.write(", ".join(replay["before"]["missing"]) or "无")
    with arrow_col:
        st.markdown("<div style='text-align:center;font-size:2rem;padding-top:4rem'>→</div>", unsafe_allow_html=True)
    with after_col:
        st.markdown("#### After · 预览结果")
        st.markdown(
            f"<span class='status-badge' style='background:{STATUS_COLORS[replay['after_preview']['status']]}'>{replay['after_preview']['status']}</span>",
            unsafe_allow_html=True,
        )
        render_pointer_group("证据指针", replay["after_preview"]["pointers"])
        st.markdown("**缺失的必要证据**")
        st.write(", ".join(replay["after_preview"]["missing"]) or "无")

    if replay["after_preview"]["contains_hypothetical_evidence"]:
        st.warning("此预览包含 hypothetical evidence（假设证据）。它没有被观察到，也绝不会自动晋升为事实证据。")
    st.info(f"下一项证据动作：{replay['next_evidence_action']}")

    summary_left, summary_right = st.columns(2)
    with summary_left:
        st.markdown("**Canonical summary · 不变**")
        st.success(product_v2["canonical_summary"]["text"])
    with summary_right:
        st.markdown("**Preview summary · 只用于比较**")
        if replay["summary_delta"]["preview_included"]:
            st.success(replay["summary_delta"]["preview_fact"])
        else:
            st.warning("该主张不会进入预览摘要。")

    receipt_text = json.dumps(replay["receipt"], ensure_ascii=False, indent=2, sort_keys=True)
    with st.expander("查看 canonical intervention receipt（规范干预回执）"):
        st.json(replay["receipt"])
        st.download_button(
            "下载此回执 JSON",
            data=receipt_text + "\n",
            file_name=f"{replay['receipt']['receipt_id']}.json",
            mime="application/json",
        )

with review_tab:
    st.subheader("Product V2 状态迁移门")
    transition_metrics = st.columns(3)
    transition_metrics[0].metric("Supported → Unknown", product_v2["transition_counts"]["Supported->Unknown"])
    transition_metrics[1].metric("Unknown → Supported", product_v2["transition_counts"]["Unknown->Supported"])
    transition_metrics[2].metric("Conflict → Unknown", product_v2["transition_counts"]["Conflict->Unknown"])
    st.caption(
        "每次迁移都绑定原始 V1 report identity 与规范回执；这些是三条确定性 synthetic-safe 回放，"
        "不是用户行为统计、产品可靠率或成熟项目性能对比。"
    )

    st.subheader("12-case 产品评测矩阵")
    counts = aggregate["counts"]
    metrics = st.columns(5)
    metrics[0].metric("案例", counts["total"])
    metrics[1].metric("Supported", counts["claim_supported"])
    metrics[2].metric("Unknown", counts["claim_unknown"])
    metrics[3].metric("Conflict", counts["claim_conflict"])
    metrics[4].metric("False Supported", counts["false_supported"])
    st.info(
        "8 个案例执行真实 localhost MCP acquisition；5 个最终场景证据直接来自未修改 MCP response，"
        "3 个执行明确的 post-MCP 受控变换；另有 4 个受控 tool-fault fixtures。"
    )
    summary_rows = []
    for report in reports:
        view = readable_case_summary(report)
        summary_rows.append({"案例": view["case_id"], "类型": view["family"], "Claim 状态": view["status"], "Policy": view["policy_status"], "任务判定": view["task_verdict"], "Tool fault": view["tool_fault"] or "—"})
    st.dataframe(summary_rows, use_container_width=True, hide_index=True)
    selected_id = st.selectbox("选择评测案例查看证据", options=[report["case_id"] for report in reports], index=4)
    selected_report = next(report for report in reports if report["case_id"] == selected_id)
    selected = readable_case_summary(selected_report)
    st.markdown(f"**待核验陈述：** {selected['statement']}")
    st.markdown(f"**Claim 状态：** `{selected['status']}` — {selected['status_explanation']}")
    evidence_left, evidence_right = st.columns(2)
    with evidence_left:
        render_pointer_group("支持证据指针", selected["supporting"])
        render_pointer_group("冲突证据指针", selected["contradicting"])
        st.markdown("**缺失的必要证据**")
        st.write(", ".join(selected["missing"]) or "无")
    with evidence_right:
        st.markdown("**Policy 与 Claim 分开判定**")
        st.write(f"Policy：`{selected['policy_status']}`")
        st.write(f"任务判定：`{selected['task_verdict']}`")
        st.write(f"Tool fault：`{selected['tool_fault'] or 'none'}`")
        if selected["policy_violations"]:
            for violation in selected["policy_violations"]:
                st.error(violation)
        if selected["story_eligible"]:
            st.success("可进入摘要 / Story 的事实层。")
        else:
            st.warning("不得进入摘要 / Story 的事实层。")

    st.subheader("透明对照评测")
    comparison_rows = []
    for strategy in comparison["strategies"]:
        metrics = strategy["metrics"]
        comparison_rows.append(
            {
                "策略": strategy["strategy_id"],
                "类型": strategy["kind"],
                "误判 Supported": metrics["false_supported"]["count"],
                "保留 Conflict": f"{metrics['conflict_preservation']['count']}/{metrics['conflict_preservation']['total']}",
                "不当摘要泄漏": metrics["unsupported_summary_leakage"]["count"],
                "安全处理工具故障": f"{metrics['safe_tool_failure_handling']['count']}/{metrics['safe_tool_failure_handling']['total']}",
            }
        )
    st.dataframe(comparison_rows, use_container_width=True, hide_index=True)
    st.caption("三个对照是公开规则的简单 ablation（消融策略），不是成熟竞品实现；结果只适用于当前 12 个 synthetic-safe cases。")

    st.subheader("成熟项目工作流差距")
    for item in product_v2["mature_workflow_comparison"]:
        with st.expander(f"{item['project']} · fixed commit {item['commit'][:10]}"):
            st.markdown(f"**成熟工作流：** {item['mature_workflow']}")
            st.markdown(f"**DayQuest V2 聚焦差距：** {item['dayquest_v2_gap']}")
            st.caption("比较层级：documentation / architecture / public workflow only")
    st.warning(
        "本表只比较公开 documentation / architecture / workflow（文档、架构与工作流），"
        "未运行这些第三方项目，也不声称 DayQuest 的性能、成熟度或通用能力优于它们。"
    )

with boundary_tab:
    st.subheader("工程证据与明确边界")
    aggregate_hash = hashlib.sha256((ARTIFACT_ROOT / "aggregate.json").read_bytes()).hexdigest().upper()
    st.code(f"MVP aggregate SHA-256\n{aggregate_hash}")
    st.write(f"Product demo identity：`{PRODUCT_DEMO_ID}`")
    st.write(f"Product V2 identity：`{PRODUCT_V2_ARTIFACT_ID}`")
    st.write(f"Product V2 canonical SHA-256：`{product_v2_identity(product_v2)}`")
    st.write(f"Report schema：`{reports[0]['schema_version']}`")
    st.write(f"Aggregate schema：`{aggregate['schema_version']}`")
    st.markdown(
        """
        - 当前只使用 committed synthetic-safe fixtures。
        - 隐私检测只覆盖冻结的 Windows drive-letter path、email-shaped text 与 Bearer/sk-like token 模式。
        - 不代表真实私人数据适用性、通用 secret scanning、跨平台路径检测或安全认证。
        - 12 cases 是确定性开发/验收矩阵，不是生产统计或泛化结论。
        - 三条 V2 回放只改变 preview；baseline reports 与 canonical summary 保持不可变。
        - 成熟项目比较只到公开文档、架构和工作流层级；未执行第三方代码或性能测试。
        - CI 可配置，但在 push 前不能声称 GitHub Actions 已实际通过。
        """
    )
