"""Standalone Gradio app for Module1+2 retrieval joint debugging."""

from __future__ import annotations

import argparse
import json
import os
import sys
from html import escape
from pathlib import Path
from typing import Any

import gradio as gr
import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from ebm_backend.online_pipeline.application.question_study import DEFAULT_LOCAL_INDEX_PATH, DEFAULT_V2_INDEX_PATH
from ebm_backend.online_pipeline.application.question_study.cleaned_article_schema import validate_cleaned_article_payload
from ebm_backend.online_pipeline.application.run_pipeline import DEMO_1000_QUESTION_PRESETS


BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
DEFAULT_INDEX_PATH = str(PROJECT_ROOT / DEFAULT_LOCAL_INDEX_PATH)
DEFAULT_QUESTION = DEMO_1000_QUESTION_PRESETS[0]
DEFAULT_STATIC_INDEX_PATH = str(PROJECT_ROOT / DEFAULT_LOCAL_INDEX_PATH)
DEFAULT_DYNAMIC_INDEX_PATH = str(PROJECT_ROOT / DEFAULT_V2_INDEX_PATH)


def run_retrieval(
    question: str,
    preset_question: str,
    mode: str,
    top_k: int,
    index_path: str,
    enable_v2_backfill: bool,
    use_mock_llm: bool,
    rct_only: bool = True,
):
    question = (question or preset_question or "").strip()
    if not question:
        return _empty_outputs("请输入临床问题，或选择一个预置问题。")

    resolved_mode = "dynamic" if str(mode).strip() == "dynamic" else "static"
    payload = {
        "question": question,
        "mode": resolved_mode,
        "top_k": int(top_k),
        "index_path": (
            (index_path or DEFAULT_DYNAMIC_INDEX_PATH).strip()
            if resolved_mode == "dynamic"
            else (index_path or DEFAULT_STATIC_INDEX_PATH).strip()
        ),
        "enable_v2_backfill": bool(enable_v2_backfill),
        "use_mock_llm": bool(use_mock_llm),
        "rct_only": bool(rct_only),
    }
    try:
        data = _run_retrieval_via_api(payload, use_mock_llm=bool(use_mock_llm))
    except Exception as exc:
        return _empty_outputs(f"检索调用失败: {exc}")

    expansion = data.get("expansion") or {}
    pi = data.get("pi") or {}
    query = data.get("query") or {}
    search = data.get("search") or {}
    stats = data.get("stats") or {}
    studies = search.get("studies") or []
    choices = data.get("cleaned_article_choices") or []

    return (
        _flow_html(mode=resolved_mode),
        _expansion_panel(expansion=expansion, pi=pi, query=query),
        _stats_panel(stats=stats, mode=resolved_mode),
        _table_html(
            ["study_id", "title", "pmid", "pmcid", "score", "source"],
            [
                [
                    item.get("study_id"),
                    item.get("title"),
                    item.get("pmid"),
                    item.get("pmcid"),
                    _fmt(item.get("relevance_score")),
                    item.get("source"),
                ]
                for item in studies
            ],
            "暂无检索结果。",
        ),
        gr.update(choices=choices, value=(choices[0] if choices else None), visible=resolved_mode == "dynamic"),
        gr.update(visible=resolved_mode == "dynamic"),
        _preview_placeholder(resolved_mode),
        data,
    )


def run_static_retrieval(
    question: str,
    preset_question: str,
    top_k: int,
    index_path: str,
    use_mock_llm: bool,
    rct_only: bool,
):
    outputs = run_retrieval(
        question=question,
        preset_question=preset_question,
        mode="static",
        top_k=top_k,
        index_path=index_path,
        enable_v2_backfill=False,
        use_mock_llm=use_mock_llm,
        rct_only=rct_only,
    )
    return (outputs[0], outputs[1], outputs[2], outputs[3], outputs[7])


def run_dynamic_retrieval(
    question: str,
    preset_question: str,
    top_k: int,
    index_path: str,
    enable_v2_backfill: bool,
    use_mock_llm: bool,
    rct_only: bool,
):
    return run_retrieval(
        question=question,
        preset_question=preset_question,
        mode="dynamic",
        top_k=top_k,
        index_path=index_path,
        enable_v2_backfill=enable_v2_backfill,
        use_mock_llm=use_mock_llm,
        rct_only=rct_only,
    )


def _run_retrieval_via_api(payload: dict[str, Any], *, use_mock_llm: bool) -> dict[str, Any]:
    if use_mock_llm:
        return _run_retrieval_with_local_test_client(payload)
    with httpx.Client(base_url=BACKEND_BASE_URL, timeout=300.0) as client:
        response = client.post("/retrieval/run", json=payload)
        response.raise_for_status()
        return response.json()


def _run_retrieval_with_local_test_client(payload: dict[str, Any]) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from ebm_backend.online_pipeline.interfaces.api.main import create_app

    client = TestClient(create_app())
    response = client.post("/retrieval/run", json=payload)
    response.raise_for_status()
    return response.json()


def show_cleaned_article(path: str, mode: str) -> str:
    resolved_mode = "dynamic" if str(mode).strip() == "dynamic" else "static"
    if resolved_mode != "dynamic":
        return _panel_html("清洗文献预览", '<div class="ebm-empty">静态模式不显示清洗预览。</div>')
    value = str(path or "").strip()
    if not value:
        return _panel_html("清洗文献预览", '<div class="ebm-empty">请选择一篇文献。</div>')
    target = Path(value)
    if not target.exists():
        return _panel_html("清洗文献预览", f'<div class="ebm-error">文件不存在: {escape(value)}</div>')
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        validate_cleaned_article_payload(payload)
    except Exception as exc:
        return _panel_html("清洗文献预览", f'<div class="ebm-error">读取失败: {escape(str(exc))}</div>')
    metadata = payload.get("metadata") or {}
    xml_content = payload.get("xml_content") or {}
    sections = xml_content.get("sections") or []
    rendered_sections: list[str] = []
    for section in sections:
        title = str(section.get("section") or "section")
        text = str(section.get("text") or "").strip()
        if not text:
            continue
        rendered_sections.append(f"## {title}\n{text}")

    body = [
        ("study_id", payload.get("study_id")),
        ("title", metadata.get("title")),
        ("pmid", metadata.get("pmid")),
        ("pmcid", metadata.get("pmc_id")),
        ("sections_count", len(sections)),
        ("tables_count", len(xml_content.get("tables") or [])),
        ("path", str(target)),
    ]
    rendered = _kv_html(body)
    if rendered_sections:
        preview_text = "\n\n".join(rendered_sections)
        rendered += '<div class="ebm-subtitle">清洗后正文全文预览</div>'
        rendered += f'<pre class="ebm-text-preview">{escape(preview_text)}</pre>'
    else:
        rendered += '<div class="ebm-empty">该文献暂无可展示的清洗正文段落。</div>'
    return _panel_html("清洗文献预览", rendered)


def on_mode_change(mode: str):
    resolved_mode = "dynamic" if str(mode).strip() == "dynamic" else "static"
    visible = resolved_mode == "dynamic"
    return (
        gr.update(visible=visible),
        gr.update(visible=visible),
        _preview_placeholder(resolved_mode),
        _flow_html(mode=resolved_mode),
    )


def _empty_outputs(message: str):
    empty = _panel_html("状态", f'<div class="ebm-empty">{escape(message)}</div>')
    return (
        _flow_html(mode="dynamic"),
        empty,
        empty,
        _table_html([], [], message),
        gr.update(choices=[], value=None, visible=False),
        gr.update(visible=False),
        _preview_placeholder("static"),
        {"status": "error", "message": message},
    )


def _preview_placeholder(mode: str) -> str:
    if mode == "dynamic":
        return _panel_html("清洗文献预览", '<div class="ebm-empty">动态模式：选择文献后可查看清洗后的正文片段。</div>')
    return _panel_html("清洗文献预览", '<div class="ebm-empty">静态模式不显示清洗预览。</div>')


def _flow_html(*, mode: str) -> str:
    mode_label = "动态检索" if mode == "dynamic" else "静态检索"
    steps = [
        "1. 输入问题",
        "2. 问题扩写",
        "3. PI + Query",
        "4. 本地检索(v2缓存优先)" if mode == "dynamic" else "4. 本地检索(demo1000)",
        "5. 在线补全/清洗" if mode == "dynamic" else "5. 返回Top-K",
    ]
    chips = "".join(f'<div class="ebm-flow-step">{escape(step)}</div>' for step in steps)
    return (
        _style_html()
        + '<section class="ebm-flow">'
        + f'<div class="ebm-flow-title">检索流程（{escape(mode_label)}）</div>'
        + f'<div class="ebm-flow-grid">{chips}</div>'
        + "</section>"
    )


def _expansion_panel(*, expansion: dict[str, Any], pi: dict[str, Any], query: dict[str, Any]) -> str:
    pico = expansion.get("pico") or {}
    rows = [
        ("Expanded question", expansion.get("expanded_question") or "n/a"),
        ("P", _join(pico.get("population"))),
        ("I", _join(pico.get("intervention"))),
        ("C", _join(pico.get("comparison"))),
        ("O", _join(pico.get("outcome"))),
        ("PI population", _join(pi.get("population"))),
        ("PI intervention", _join(pi.get("intervention"))),
        ("Query", query.get("boolean_query") or "n/a"),
    ]
    return _panel_html("扩写结果", rows)


def _stats_panel(*, stats: dict[str, Any], mode: str) -> str:
    rows: list[tuple[str, Any]] = [
        ("retrieved_total", stats.get("retrieved_total", 0)),
        ("returned_top_k", stats.get("returned_top_k", 0)),
    ]
    if mode == "dynamic":
        rows.extend(
            [
                ("online_backfill_used", bool(stats.get("online_backfill_used"))),
                ("pubmed_requested", stats.get("pubmed_requested", 0)),
                ("rct_gate_excluded", stats.get("rct_gate_excluded", 0)),
                ("download_success", stats.get("download_success", 0)),
                ("clean_success", stats.get("clean_success", 0)),
                ("ingested_success", stats.get("ingested_success", 0)),
            ]
        )
    timings = stats.get("timings_ms") if isinstance(stats.get("timings_ms"), dict) else {}
    rows.extend(
        [
            ("question_expansion_ms", timings.get("question_expansion_ms", 0)),
            ("question_pi_extraction_ms", timings.get("question_pi_extraction_ms", 0)),
            ("query_generation_ms", timings.get("query_generation_ms", 0)),
            ("local_search_ms", timings.get("local_search_ms", 0)),
            ("total_ms", timings.get("total_ms", 0)),
        ]
    )
    return _panel_html("检索统计", rows)


def _table_html(headers: list[str], rows: list[list[Any]], empty_text: str) -> str:
    if not rows:
        return f'{_style_html()}<div class="ebm-empty">{escape(empty_text)}</div>'
    header_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{escape(_fmt(cell))}</td>" for cell in row)
        body_rows.append(f"<tr>{cells}</tr>")
    return (
        f'{_style_html()}<div class="ebm-table-wrap"><table class="ebm-table">'
        f"<thead><tr>{header_html}</tr></thead><tbody>{''.join(body_rows)}</tbody>"
        "</table></div>"
    )


def _panel_html(title: str, content: Any) -> str:
    body = _kv_html(content) if isinstance(content, list) else str(content)
    return f'{_style_html()}<section class="ebm-panel"><h3>{escape(title)}</h3>{body}</section>'


def _kv_html(rows: list[tuple[str, Any]]) -> str:
    parts = ['<dl class="ebm-kv">']
    for key, value in rows:
        parts.append(f"<dt>{escape(str(key))}</dt><dd>{escape(_fmt(value))}</dd>")
    parts.append("</dl>")
    return "".join(parts)


def _style_html() -> str:
    return """
    <style>
    .ebm-panel { border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px 16px; background: #fff; color: #111827; }
    .ebm-panel h3 { margin: 0 0 10px; font-size: 1rem; line-height: 1.25; font-weight: 700; color: #111827; }
    .ebm-subtitle { margin: 12px 0 8px; font-weight: 700; color: #111827; }
    .ebm-kv { display: grid; grid-template-columns: minmax(140px, 200px) 1fr; gap: 8px 14px; margin: 0; }
    .ebm-kv dt { color: #6b7280; font-size: 0.82rem; font-weight: 650; }
    .ebm-kv dd { margin: 0; color: #111827; overflow-wrap: anywhere; }
    .ebm-table-wrap { overflow-x: auto; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; }
    table.ebm-table { border-collapse: collapse; width: 100%; min-width: 720px; font-size: 0.9rem; }
    .ebm-table th { background: #f8fafc; color: #111827; text-align: left; font-weight: 650; }
    .ebm-table th, .ebm-table td { border-bottom: 1px solid #e5e7eb; padding: 8px 10px; vertical-align: top; }
    .ebm-table tr:last-child td { border-bottom: 0; }
    .ebm-empty { color: #6b7280; padding: 6px 0; }
    .ebm-error { color: #991b1b; white-space: pre-wrap; }
    .ebm-flow { border: 1px solid #cbd5e1; border-radius: 10px; padding: 12px; background: linear-gradient(90deg, #f8fafc 0%, #ffffff 100%); }
    .ebm-flow-title { font-weight: 700; color: #0f172a; margin-bottom: 8px; }
    .ebm-flow-grid { display: grid; grid-template-columns: repeat(5, minmax(120px, 1fr)); gap: 8px; }
    .ebm-flow-step { border: 1px solid #93c5fd; background: #eff6ff; border-radius: 8px; padding: 8px 10px; font-size: 0.85rem; color: #1e3a8a; font-weight: 650; text-align: center; }
    .ebm-text-preview { border: 1px solid #e5e7eb; border-radius: 8px; background: #fafafa; padding: 12px; max-height: 420px; overflow: auto; white-space: pre-wrap; line-height: 1.45; }
    @media (max-width: 960px) {
      .ebm-flow-grid { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
    }
    </style>
    """


def _join(values: Any) -> str:
    if values is None:
        return "n/a"
    if isinstance(values, str):
        return values or "n/a"
    text = "; ".join(str(value) for value in values if value is not None and str(value) != "")
    return text or "n/a"


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3g}"
    return str(value)


def _section_text(section: dict[str, Any]) -> str:
    direct = str(section.get("text") or "").strip()
    if direct:
        return direct
    blocks = section.get("blocks") or []
    if not isinstance(blocks, list):
        return ""
    chunks: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        value = str(block.get("text") or "").strip()
        if value:
            chunks.append(value)
    return "\n".join(chunks).strip()


def build_retrieval_app() -> gr.Blocks:
    css = """
    .gradio-container { max-width: 1360px !important; }
    #app-title { margin-bottom: 6px; }
    """
    with gr.Blocks(title="Module1+2 Retrieval Debug", css=css) as demo:
        gr.Markdown("## Module1+2 统一检索联调页\n静态检索和动态检索已拆分为两个独立页面。", elem_id="app-title")

        with gr.Tabs():
            with gr.Tab("静态检索（本地1000索引）"):
                with gr.Row():
                    with gr.Column(scale=4, min_width=320):
                        static_question = gr.Textbox(
                            label="Clinical question",
                            value=DEFAULT_QUESTION,
                            lines=4,
                            placeholder="In patients ..., does ... compared with ... improve ...?",
                        )
                        static_preset = gr.Dropdown(
                            label="预置问题",
                            choices=DEMO_1000_QUESTION_PRESETS,
                            value=DEFAULT_QUESTION,
                            interactive=True,
                        )
                        static_top_k = gr.Slider(label="Top K", minimum=1, maximum=20, step=1, value=5)
                        static_use_mock_llm = gr.Checkbox(label="Use mock LLM", value=False)
                        static_rct_only = gr.Checkbox(label="RCT only", value=True)
                        static_index_path = gr.Textbox(label="Index path", value=DEFAULT_STATIC_INDEX_PATH, lines=1)
                        static_run_button = gr.Button("执行静态检索", variant="primary")
                    with gr.Column(scale=7, min_width=420):
                        static_flow_html = gr.HTML(label="流程")
                        static_expansion_html = gr.HTML(label="扩写结果")
                        static_stats_html = gr.HTML(label="检索统计")

                static_result_table = gr.HTML(label="Top-K 检索结果")
                static_response_json = gr.JSON(label="Raw retrieval response")

                static_run_button.click(
                    fn=run_static_retrieval,
                    inputs=[static_question, static_preset, static_top_k, static_index_path, static_use_mock_llm, static_rct_only],
                    outputs=[static_flow_html, static_expansion_html, static_stats_html, static_result_table, static_response_json],
                )
                static_preset.change(fn=lambda value: value, inputs=static_preset, outputs=static_question)

            with gr.Tab("动态检索（在线补全+清洗沉淀）"):
                with gr.Row():
                    with gr.Column(scale=4, min_width=320):
                        dynamic_question = gr.Textbox(
                            label="Clinical question",
                            value=DEFAULT_QUESTION,
                            lines=4,
                            placeholder="In patients ..., does ... compared with ... improve ...?",
                        )
                        dynamic_preset = gr.Dropdown(
                            label="预置问题",
                            choices=DEMO_1000_QUESTION_PRESETS,
                            value=DEFAULT_QUESTION,
                            interactive=True,
                        )
                        dynamic_top_k = gr.Slider(label="Top K", minimum=1, maximum=20, step=1, value=5)
                        dynamic_use_mock_llm = gr.Checkbox(label="Use mock LLM", value=False)
                        dynamic_rct_only = gr.Checkbox(label="RCT only", value=True)
                        dynamic_enable_v2_backfill = gr.Checkbox(label="Enable v2 backfill", value=True)
                        dynamic_index_path = gr.Textbox(label="Cache index path (v2)", value=DEFAULT_DYNAMIC_INDEX_PATH, lines=1)
                        dynamic_run_button = gr.Button("执行动态检索", variant="primary")
                    with gr.Column(scale=7, min_width=420):
                        dynamic_flow_html = gr.HTML(label="流程")
                        dynamic_expansion_html = gr.HTML(label="扩写结果")
                        dynamic_stats_html = gr.HTML(label="检索统计")

                dynamic_result_table = gr.HTML(label="Top-K 检索结果")
                with gr.Row():
                    dynamic_cleaned_choice = gr.Dropdown(label="清洗后文献路径", choices=[], interactive=True, visible=True)
                    dynamic_cleaned_preview_button = gr.Button("预览清洗文献", visible=True)
                dynamic_cleaned_preview = gr.HTML(label="清洗文献预览")
                dynamic_response_json = gr.JSON(label="Raw retrieval response")

                dynamic_run_button.click(
                    fn=run_dynamic_retrieval,
                    inputs=[
                        dynamic_question,
                        dynamic_preset,
                        dynamic_top_k,
                        dynamic_index_path,
                        dynamic_enable_v2_backfill,
                        dynamic_use_mock_llm,
                        dynamic_rct_only,
                    ],
                    outputs=[
                        dynamic_flow_html,
                        dynamic_expansion_html,
                        dynamic_stats_html,
                        dynamic_result_table,
                        dynamic_cleaned_choice,
                        dynamic_cleaned_preview_button,
                        dynamic_cleaned_preview,
                        dynamic_response_json,
                    ],
                )
                dynamic_cleaned_preview_button.click(
                    fn=lambda path: show_cleaned_article(path, "dynamic"),
                    inputs=[dynamic_cleaned_choice],
                    outputs=dynamic_cleaned_preview,
                )
                dynamic_preset.change(fn=lambda value: value, inputs=dynamic_preset, outputs=dynamic_question)
    return demo


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the standalone Module1+2 retrieval Gradio app.")
    parser.add_argument("--host", default=os.getenv("GRADIO_SERVER_NAME", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("GRADIO_SERVER_PORT", "7861")))
    parser.add_argument("--share", action="store_true", default=os.getenv("GRADIO_SHARE", "").lower() == "true")
    args = parser.parse_args()
    build_retrieval_app().queue().launch(server_name=args.host, server_port=args.port, share=args.share)


if __name__ == "__main__":
    main()
