"""Gradio demo for the Phase 5 EBM pipeline."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

import gradio as gr
import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_DOTENV_OPENAI_API_KEY = None
_DOTENV_OPENAI_BASE_URL = None
_DOTENV_LLM_MODEL = None
for raw_line in (PROJECT_ROOT / ".env").read_text(encoding="utf-8").splitlines() if (PROJECT_ROOT / ".env").exists() else []:
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    value = value.strip().strip("'\"")
    if key == "OPENAI_API_KEY":
        _DOTENV_OPENAI_API_KEY = value
    elif key == "OPENAI_BASE_URL":
        _DOTENV_OPENAI_BASE_URL = value
    elif key == "LLM_MODEL":
        _DOTENV_LLM_MODEL = value

_REAL_API_KEY_AVAILABLE = bool(os.getenv("OPENAI_API_KEY") or _DOTENV_OPENAI_API_KEY)
os.environ.setdefault("OPENAI_API_KEY", _DOTENV_OPENAI_API_KEY or "mock-key-for-gradio-demo")
if _DOTENV_OPENAI_BASE_URL:
    os.environ.setdefault("OPENAI_BASE_URL", _DOTENV_OPENAI_BASE_URL)
if _DOTENV_LLM_MODEL:
    os.environ.setdefault("LLM_MODEL", _DOTENV_LLM_MODEL)

BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from ebm_backend.online_pipeline.application.question_study import DEFAULT_LOCAL_INDEX_PATH
from ebm_backend.online_pipeline.application.run_pipeline import DEMO_1000_QUESTION_PRESETS


DEFAULT_QUESTION = DEMO_1000_QUESTION_PRESETS[0]
DEFAULT_INDEX_PATH = str(PROJECT_ROOT / DEFAULT_LOCAL_INDEX_PATH)
LOG_PATH = PROJECT_ROOT / "logs" / "gradio_pipeline.log"
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TIMELINE_STEPS = [
    ("question_expansion", "Question expansion"),
    ("question_pi_extraction", "PI extraction"),
    ("query_generation", "Boolean query"),
    ("local_search", "Local retrieval"),
    ("module3_analysis", "Evidence analysis"),
]


@dataclass(frozen=True)
class _StepView:
    name: str
    status: str
    summary: str = ""
    payload: dict[str, Any] | None = None
    error: str | None = None


@dataclass(frozen=True)
class _RunView:
    run_id: str
    status: str
    question: str
    top_k: int
    use_mock: bool
    index_path: str | None
    steps: list[_StepView]
    result: dict[str, Any] | None
    error: str | None = None


def run_pipeline(
    question: str,
    preset_question: str,
    top_k: int,
    use_mock: bool,
    index_path: str,
):
    """Run the synchronous Gradio callback around the async orchestrator."""
    question = (question or preset_question or "").strip()
    if not question:
        yield _empty_outputs("Enter a clinical question or choose a demo question.")
        return
    if not use_mock and not _REAL_API_KEY_AVAILABLE:
        yield _empty_outputs("Real LLM mode requires OPENAI_API_KEY. Turn on mock mode or set the key.")
        return

    resolved_index_path = (index_path or DEFAULT_INDEX_PATH).strip()
    mode = "mock" if use_mock else "real LLM"
    _log_event(f"start mode={mode} top_k={int(top_k)} index={resolved_index_path} question={question!r}")
    yield _running_outputs(question=question, top_k=int(top_k), use_mock=bool(use_mock), index_path=resolved_index_path)

    start = time.perf_counter()
    try:
        trace = _run_pipeline_via_backend(
            question=question,
            top_k=int(top_k),
            use_mock=bool(use_mock),
            index_path=resolved_index_path,
        )
    except Exception as exc:
        elapsed = time.perf_counter() - start
        _log_event(f"finish status=failed elapsed={elapsed:.2f}s error={exc!r}")
        yield _error_outputs(str(exc))
        return

    elapsed = time.perf_counter() - start
    trace["elapsed_seconds"] = round(elapsed, 3)
    run = _run_view_from_trace(trace)
    trace_path = _write_trace_file(trace)
    _log_event(
        f"finish status={_status_value(run.status)} elapsed={elapsed:.2f}s "
        f"run_id={run.run_id} trace={trace_path} error={run.error!r}"
    )
    yield _outputs_from_run(run, elapsed, trace_path=trace_path)


def _run_pipeline_via_backend(*, question: str, top_k: int, use_mock: bool, index_path: str) -> dict[str, Any]:
    payload = {
        "question": question,
        "top_k": top_k,
        "use_mock": use_mock,
        "index_path": index_path,
    }
    try:
        with httpx.Client(base_url=BACKEND_BASE_URL, timeout=300.0) as client:
            created = client.post("/pipeline/runs", json=payload)
            created.raise_for_status()
            run_id = created.json()["run_id"]
            trace = client.get(f"/pipeline/runs/{run_id}/trace")
            trace.raise_for_status()
            return _trace_payload_from_api(trace.json())
    except Exception:
        if not use_mock:
            raise
        return _run_pipeline_with_local_test_client(payload)


def _run_pipeline_with_local_test_client(payload: dict[str, Any]) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from ebm_backend.online_pipeline.infrastructure.pipeline_repository import DEFAULT_PIPELINE_STORE
    from ebm_backend.online_pipeline.interfaces.api.main import create_app

    DEFAULT_PIPELINE_STORE._runs.clear()
    client = TestClient(create_app())
    created = client.post("/pipeline/runs", json=payload)
    created.raise_for_status()
    run_id = created.json()["run_id"]
    trace = client.get(f"/pipeline/runs/{run_id}/trace")
    trace.raise_for_status()
    return _trace_payload_from_api(trace.json())


def _trace_payload_from_api(api_trace: dict[str, Any]) -> dict[str, Any]:
    run = api_trace.get("run") or {}
    return {
        **run,
        "steps": api_trace.get("steps") or [],
        "result": api_trace.get("result"),
    }


def _run_view_from_trace(trace: dict[str, Any]) -> _RunView:
    return _RunView(
        run_id=str(trace.get("run_id") or ""),
        status=str(trace.get("status") or "unknown"),
        question=str(trace.get("question") or ""),
        top_k=int(trace.get("top_k") or 0),
        use_mock=bool(trace.get("use_mock")),
        index_path=trace.get("index_path"),
        steps=[
            _StepView(
                name=str(step.get("name") or ""),
                status=str(step.get("status") or "pending"),
                summary=str(step.get("summary") or ""),
                payload=step.get("payload") or {},
                error=step.get("error"),
            )
            for step in trace.get("steps") or []
        ],
        result=trace.get("result") or None,
        error=trace.get("error"),
    )


def _outputs_from_run(run: Any, elapsed: float, trace_path: str | None):
    trace = _run_to_dict(run, elapsed)
    result = run.result or {}
    expansion = result.get("question_expansion") or _step_payload(run, "question_expansion")
    pi = result.get("pi") or _step_payload(run, "question_pi_extraction")
    query = result.get("query") or _step_payload(run, "query_generation")
    search = result.get("search") or _step_payload(run, "local_search")
    candidates = result.get("candidates") or search.get("studies") or []
    module3 = _module3_payload(run)
    screening = result.get("screening") or module3.get("screening") or {}
    planning = result.get("planning") or module3.get("planning") or {}
    extraction = result.get("extraction") or module3.get("extraction") or {}
    rob = result.get("risk_of_bias") or module3.get("risk_of_bias") or {}
    aggregation = result.get("aggregation") or module3.get("aggregation") or {}
    grade = result.get("grade") or module3.get("grade") or {}

    return (
        _answer_markdown(run, elapsed, expansion, screening, aggregation, grade),
        _summary_markdown(run, elapsed, candidates),
        _timeline_markdown(run),
        _pico_markdown(expansion),
        _eligibility_markdown(expansion),
        _plan_markdown(expansion, planning),
        _pi_markdown(pi),
        _query_markdown(query, search),
        _table_html(
            ["study_id", "title", "pmid", "pmcid", "score", "matched_fields", "source"],
            _candidate_rows(candidates),
            "Waiting for local search results.",
        ),
        _table_html(
            ["study_id", "title", "decision", "rationale", "exclusion_reason"],
            _screening_rows(screening),
            "Waiting for screening decisions.",
        ),
        _table_html(
            [
                "study_id",
                "analysis_id",
                "outcome_type",
                "effect_measure",
                "status",
                "exp_events",
                "exp_n",
                "ctrl_events",
                "ctrl_n",
                "exp_mean",
                "ctrl_mean",
                "notes",
            ],
            _extraction_rows(extraction),
            "Waiting for extraction rows.",
        ),
        _table_html(
            ["study_id", "domain", "judgement", "rationale", "overall"],
            _rob_rows(rob),
            "Waiting for Risk of Bias assessments.",
        ),
        _table_html(
            ["analysis_id", "outcome", "effect_measure", "effect", "ci_low", "ci_high", "i2", "studies", "warnings"],
            _aggregation_rows(aggregation),
            "Waiting for aggregation results.",
        ),
        _table_html(
            ["analysis_id", "certainty", "downgrade_reasons", "rationale", "warnings"],
            _grade_rows(grade),
            "Waiting for GRADE assessments.",
        ),
        trace,
        trace_path,
        gr.update(visible=run.error is not None, value=_error_html(run.error or "")),
    )


def _run_signature(run: Any) -> str:
    step_bits = [
        f"{step.name}:{_status_value(step.status)}:{step.summary}:{step.error or ''}"
        for step in run.steps
    ]
    return "|".join(
        [
            _status_value(run.status),
            str(len(run.steps)),
            *step_bits,
            str(bool(run.result)),
            str(run.error or ""),
        ]
    )


def _step_status_summary(run: Any) -> str:
    parts = [f"run_id={run.run_id}", f"status={_status_value(run.status)}"]
    for step in run.steps:
        parts.append(f"{step.name}={_status_value(step.status)}")
    return " ".join(parts)


def _log_event(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().isoformat(timespec="seconds")
    LOG_PATH.write_text("", encoding="utf-8") if not LOG_PATH.exists() else None
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} {message}\n")


def _running_outputs(*, question: str, top_k: int, use_mock: bool, index_path: str):
    empty_table = _table_html([], [], "Pipeline is running. Results will appear when the run completes.")
    trace = {
        "status": "running",
        "question": question,
        "top_k": top_k,
        "use_mock": use_mock,
        "index_path": index_path,
        "message": "Pipeline started. Waiting for orchestrator to finish.",
        "log_path": str(LOG_PATH),
    }
    return (
        _panel_html(
            "Running",
            [
                ("Question", question),
                ("Status", "Pipeline started. Results will refresh step by step."),
                ("Mode", "mock" if use_mock else "real LLM"),
            ],
            tone="active",
        ),
        _panel_html(
            "Run Summary",
            [
                ("Status", "running"),
                ("Top K", top_k),
                ("Index", index_path),
                ("Log", str(LOG_PATH)),
            ],
            tone="active",
        ),
        _timeline_html(None),
        _empty_panel("PICO", "Waiting for question expansion."),
        _empty_panel("Eligibility", "Waiting for eligibility criteria."),
        _empty_panel("Analysis Plan", "Waiting for analysis plan."),
        _empty_panel("PI Extraction", "Waiting for PI extraction."),
        _empty_panel("Query", "Waiting for query generation and local search."),
        empty_table,
        empty_table,
        empty_table,
        empty_table,
        empty_table,
        empty_table,
        trace,
        None,
        gr.update(visible=False, value=""),
    )


def _empty_outputs(message: str):
    empty_trace = {"status": "not_started", "message": message}
    empty_table = _table_html([], [], message)
    return (
        _empty_panel("Not Started", message),
        _empty_panel("Run Summary", message),
        _timeline_html(None),
        _empty_panel("PICO", message),
        _empty_panel("Eligibility", message),
        _empty_panel("Analysis Plan", message),
        _empty_panel("PI Extraction", message),
        _empty_panel("Query", message),
        empty_table,
        empty_table,
        empty_table,
        empty_table,
        empty_table,
        empty_table,
        empty_trace,
        None,
        gr.update(visible=False, value=""),
    )


def _error_outputs(message: str):
    empty_trace = {"status": "failed", "error": message}
    empty_table = _table_html([], [], message)
    return (
        _error_html(message),
        _error_html(message),
        _timeline_html(None),
        _empty_panel("PICO", message),
        _empty_panel("Eligibility", message),
        _empty_panel("Analysis Plan", message),
        _empty_panel("PI Extraction", message),
        _empty_panel("Query", message),
        empty_table,
        empty_table,
        empty_table,
        empty_table,
        empty_table,
        empty_table,
        empty_trace,
        None,
        gr.update(visible=True, value=_error_html(message)),
    )


def _run_to_dict(run: Any, elapsed_seconds: float) -> dict[str, Any]:
    payload = _jsonable(run)
    payload["elapsed_seconds"] = round(elapsed_seconds, 3)
    return payload


def _write_trace_file(trace: dict[str, Any]) -> str:
    run_id = str(trace.get("run_id") or "pipeline")
    safe_run_id = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in run_id)
    path = Path(tempfile.gettempdir()) / f"ebm_pipeline_trace_{safe_run_id}.json"
    path.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {name: _jsonable(getattr(value, name)) for name in value.__dataclass_fields__}
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


def _step_payload(run: Any, name: str) -> dict[str, Any]:
    for step in run.steps:
        if step.name == name:
            return step.payload or {}
    return {}


def _module3_payload(run: Any) -> dict[str, Any]:
    return _step_payload(run, "module3_analysis")


def _answer_markdown(
    run: Any,
    elapsed: float,
    expansion: dict[str, Any],
    screening: dict[str, Any],
    aggregation: dict[str, Any],
    grade: dict[str, Any],
) -> str:
    included = len(screening.get("included") or [])
    excluded = len(screening.get("excluded") or [])
    analyses = aggregation.get("analyses") or []
    certainty = ", ".join(
        str(item.get("certainty")) for item in grade.get("assessments") or [] if item.get("certainty")
    )
    pico = expansion.get("pico") or {}
    primary = (expansion.get("preliminary_analysis_plan") or {}).get("primary_outcome")
    status = _status_value(run.status)
    rows: list[tuple[str, Any]] = [
        ("Question", run.question),
        ("Status", status),
        ("Elapsed", f"{elapsed:.1f}s"),
        ("Studies", f"{included} included, {excluded} excluded"),
    ]
    if primary:
        rows.append(("Primary outcome", primary))
    if certainty:
        rows.append(("GRADE certainty", certainty))
    if pico:
        rows.append(("PICO", _pico_inline(pico)))

    body = _kv_html(rows)
    if analyses:
        body += '<div class="ebm-subtitle">Analysis summary</div><ul class="ebm-list">'
        for analysis in analyses:
            pooled = analysis.get("pooled_result") or {}
            effect = _fmt(pooled.get("effect")) if pooled else "not pooled"
            ci = _ci_text(pooled)
            body += (
                "<li>"
                f"{escape(str(analysis.get('outcome') or analysis.get('analysis_id')))}: "
                f"{escape(str(analysis.get('effect_measure') or 'effect'))} {escape(effect)}{escape(ci)}"
                "</li>"
            )
        body += "</ul>"
    if run.error:
        body += _error_html(run.error)
    return _panel_html(status.title(), body, tone="success" if status == "completed" else "active")


def _summary_markdown(run: Any, elapsed: float, candidates: list[dict[str, Any]]) -> str:
    return _panel_html(
        "Run Summary",
        [
            ("Run status", _status_value(run.status)),
            ("Run ID", run.run_id),
            ("Elapsed", f"{elapsed:.2f}s"),
            ("Candidates", len(candidates)),
            ("Mode", "mock" if run.use_mock else "real LLM"),
            ("Index", run.index_path),
        ],
        tone="active" if _status_value(run.status) == "running" else "neutral",
    )


def _timeline_markdown(run: Any) -> str:
    return _timeline_html(run)


def _timeline_html(run: Any | None) -> str:
    by_name = {step.name: step for step in run.steps} if run is not None else {}
    items = []
    run_status = _status_value(run.status) if run is not None else "running"
    for name, label in TIMELINE_STEPS:
        step = by_name.get(name)
        if step is None:
            status = "pending"
            summary = ""
            error = ""
        else:
            status = _status_value(step.status)
            summary = step.summary or ""
            error = step.error or ""
        cls = "done" if status == "completed" else "failed" if status == "failed" else "active" if status == "running" else "pending"
        items.append(
            '<div class="ebm-step {cls}">'
            '<div class="ebm-step-dot"></div>'
            '<div class="ebm-step-body">'
            '<div class="ebm-step-title">{label}<span>{status}</span></div>'
            '<div class="ebm-step-summary">{summary}</div>'
            '{error}'
            '</div></div>'.format(
                cls=cls,
                label=escape(label),
                status=escape(status),
                summary=escape(summary or "Waiting" if status == "pending" else summary),
                error=f'<div class="ebm-step-error">{escape(error)}</div>' if error else "",
            )
        )
    return _style_html() + f'<div class="ebm-timeline" data-status="{escape(run_status)}">{"".join(items)}</div>'


def _legacy_timeline_markdown(run: Any) -> str:
    by_name = {step.name: step for step in run.steps}
    rows = []
    for name, label in TIMELINE_STEPS:
        step = by_name.get(name)
        if not step:
            rows.append(f"- pending - **{label}**")
            continue
        status = _status_value(step.status)
        summary = f" - {step.summary}" if step.summary else ""
        rows.append(f"- {status} - **{label}**{summary}")
        if step.error:
            rows.append(f"  - Error: `{step.error}`")
    return "\n".join(rows)


def _pico_markdown(expansion: dict[str, Any]) -> str:
    pico = expansion.get("pico") or {}
    if not pico:
        return _empty_panel("PICO", "Waiting for question expansion.")
    return _panel_html(
        "PICO",
        [
            ("Population", _join(pico.get("population"))),
            ("Intervention", _join(pico.get("intervention"))),
            ("Comparison", _join(pico.get("comparison"))),
            ("Outcome", _join(pico.get("outcome"))),
            ("Expanded question", expansion.get("expanded_question") or "n/a"),
        ],
    )


def _eligibility_markdown(expansion: dict[str, Any]) -> str:
    eligibility = expansion.get("eligibility_criteria") or {}
    if not eligibility:
        return _empty_panel("Eligibility", "Waiting for eligibility criteria.")
    return _panel_html(
        "Eligibility",
        [
            ("Inclusion", _join(eligibility.get("inclusion"))),
            ("Exclusion", _join(eligibility.get("exclusion"))),
            ("Confidence", eligibility.get("confidence") or "n/a"),
            ("Needs confirmation", _join(expansion.get("needs_user_confirmation"))),
        ],
    )


def _plan_markdown(expansion: dict[str, Any], planning: dict[str, Any]) -> str:
    preliminary = expansion.get("preliminary_analysis_plan") or {}
    analyses = planning.get("analyses") or []
    if not preliminary and not analyses:
        return _empty_panel("Analysis Plan", "Waiting for analysis plan.")
    rows = [
        ("Primary outcome", preliminary.get("primary_outcome") or "n/a"),
        ("Secondary outcomes", _join(preliminary.get("secondary_outcomes"))),
        ("Timepoints", _join(preliminary.get("timepoints"))),
        ("Effect measures", json.dumps(preliminary.get("effect_measures") or {}, ensure_ascii=False)),
        ("Preliminary confidence", preliminary.get("confidence") or "n/a"),
    ]
    body = _kv_html(rows)
    if analyses:
        body += '<div class="ebm-subtitle">Module 3 analyses</div><ul class="ebm-list">'
        for item in analyses:
            body += (
                "<li>"
                f"{escape(str(item.get('analysis_id')))} - {escape(str(item.get('outcome')))} "
                f"({escape(str(item.get('outcome_type')))}, {escape(str(item.get('effect_measure')))})"
                "</li>"
            )
        body += "</ul>"
    return _panel_html("Analysis Plan", body)


def _pi_markdown(pi: dict[str, Any]) -> str:
    if not pi:
        return _empty_panel("PI Extraction", "Waiting for PI extraction.")
    return _panel_html(
        "PI Extraction",
        [
            ("Population terms", _join(pi.get("population"))),
            ("Intervention terms", _join(pi.get("intervention"))),
            ("Notes", pi.get("notes") or "n/a"),
        ],
    )


def _query_markdown(query: dict[str, Any], search: dict[str, Any]) -> str:
    if not query and not search:
        return _empty_panel("Query", "Waiting for query generation and local search.")
    fallback = search.get("fallback_search") or {}
    rows = [
        ("Boolean query", query.get("boolean_query") or search.get("query_used") or "n/a"),
        ("Local query_text", fallback.get("query_text") or search.get("query_text") or "n/a"),
        ("Returned", f"{search.get('returned_count', 0)} / total {search.get('total_hits', 0)}"),
    ]
    if fallback:
        rows.append(("Fallback", json.dumps(fallback, ensure_ascii=False)))
    return _panel_html("Query", rows)


def _candidate_rows(candidates: list[dict[str, Any]]) -> list[list[Any]]:
    return [
        [
            item.get("study_id"),
            item.get("title"),
            item.get("pmid"),
            item.get("pmcid"),
            _fmt(item.get("relevance_score")),
            _join(item.get("matched_fields")),
            item.get("source"),
        ]
        for item in candidates
    ]


def _screening_rows(screening: dict[str, Any]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for item in screening.get("decisions") or []:
        rows.append(
            [
                item.get("study_id"),
                item.get("title"),
                "included" if item.get("included") else "excluded",
                item.get("rationale"),
                item.get("exclusion_reason"),
            ]
        )
    if rows:
        return rows
    for item in screening.get("included") or []:
        rows.append([item.get("study_id"), item.get("title"), "included", "", ""])
    for item in screening.get("excluded") or []:
        rows.append([item.get("study_id"), item.get("title"), "excluded", item.get("rationale"), item.get("exclusion_reason")])
    return rows


def _extraction_rows(extraction: dict[str, Any]) -> list[list[Any]]:
    return [
        [
            item.get("study_id"),
            item.get("analysis_id"),
            item.get("outcome_type"),
            item.get("effect_measure"),
            item.get("extraction_status"),
            item.get("exp_events"),
            item.get("exp_n"),
            item.get("ctrl_events"),
            item.get("ctrl_n"),
            item.get("exp_mean"),
            item.get("ctrl_mean"),
            item.get("notes"),
        ]
        for item in extraction.get("rows") or []
    ]


def _rob_rows(rob: dict[str, Any]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for assessment in rob.get("assessments") or []:
        domains = assessment.get("domains") or []
        if not domains:
            rows.append([assessment.get("study_id"), "", assessment.get("overall"), "", ""])
        for domain in domains:
            rows.append(
                [
                    assessment.get("study_id"),
                    domain.get("domain"),
                    domain.get("judgement"),
                    domain.get("rationale"),
                    assessment.get("overall"),
                ]
            )
    return rows


def _aggregation_rows(aggregation: dict[str, Any]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for analysis in aggregation.get("analyses") or []:
        pooled = analysis.get("pooled_result") or {}
        heterogeneity = analysis.get("heterogeneity") or {}
        rows.append(
            [
                analysis.get("analysis_id"),
                analysis.get("outcome"),
                analysis.get("effect_measure"),
                _fmt(pooled.get("effect")),
                _fmt(pooled.get("ci_low")),
                _fmt(pooled.get("ci_high")),
                _fmt(heterogeneity.get("i2")),
                len(analysis.get("study_effects") or []),
                _join(analysis.get("warnings")),
            ]
        )
    return rows


def _grade_rows(grade: dict[str, Any]) -> list[list[Any]]:
    return [
        [
            item.get("analysis_id"),
            item.get("certainty"),
            _join(item.get("downgrade_reasons")),
            item.get("rationale"),
            _join(item.get("warnings")),
        ]
        for item in grade.get("assessments") or []
    ]


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


def _panel_html(title: str, content: Any, *, tone: str = "neutral") -> str:
    body = _kv_html(content) if isinstance(content, list) else str(content)
    return f'{_style_html()}<section class="ebm-panel {escape(tone)}"><h3>{escape(title)}</h3>{body}</section>'


def _empty_panel(title: str, message: str) -> str:
    return _panel_html(title, f'<div class="ebm-empty">{escape(message)}</div>')


def _error_html(message: str) -> str:
    return _panel_html("Error", f'<div class="ebm-error">{escape(message)}</div>', tone="failed")


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
    .ebm-panel.active { border-color: #93c5fd; background: #f8fbff; }
    .ebm-panel.success { border-color: #86efac; background: #f8fff9; }
    .ebm-panel.failed { border-color: #fecaca; background: #fff8f8; }
    .ebm-kv { display: grid; grid-template-columns: minmax(120px, 180px) 1fr; gap: 8px 14px; margin: 0; }
    .ebm-kv dt { color: #6b7280; font-size: 0.82rem; font-weight: 650; }
    .ebm-kv dd { margin: 0; color: #111827; overflow-wrap: anywhere; }
    .ebm-subtitle { margin-top: 14px; margin-bottom: 6px; font-weight: 700; color: #111827; }
    .ebm-list { margin: 0; padding-left: 18px; }
    .ebm-table-wrap { overflow-x: auto; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; }
    table.ebm-table { border-collapse: collapse; width: 100%; min-width: 760px; font-size: 0.9rem; }
    .ebm-table th { background: #f8fafc; color: #111827; text-align: left; font-weight: 650; }
    .ebm-table th, .ebm-table td { border-bottom: 1px solid #e5e7eb; padding: 8px 10px; vertical-align: top; }
    .ebm-table tr:last-child td { border-bottom: 0; }
    .ebm-empty { color: #6b7280; padding: 6px 0; }
    .ebm-error { color: #991b1b; white-space: pre-wrap; }
    .ebm-timeline { display: grid; gap: 8px; }
    .ebm-step { display: grid; grid-template-columns: 18px 1fr; gap: 10px; padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; }
    .ebm-step-dot { width: 10px; height: 10px; border-radius: 50%; margin-top: 4px; background: #d1d5db; }
    .ebm-step.done .ebm-step-dot { background: #16a34a; }
    .ebm-step.active .ebm-step-dot { background: #2563eb; box-shadow: 0 0 0 4px #dbeafe; }
    .ebm-step.failed .ebm-step-dot { background: #dc2626; }
    .ebm-step-title { display: flex; justify-content: space-between; gap: 12px; font-weight: 700; color: #111827; }
    .ebm-step-title span { color: #6b7280; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0; }
    .ebm-step-summary { margin-top: 4px; color: #4b5563; overflow-wrap: anywhere; }
    .ebm-step-error { margin-top: 4px; color: #991b1b; }
    </style>
    """


def _join(values: Any) -> str:
    if values is None:
        return "n/a"
    if isinstance(values, str):
        return values or "n/a"
    if isinstance(values, dict):
        return json.dumps(values, ensure_ascii=False)
    text = "; ".join(str(value) for value in values if value is not None and str(value) != "")
    return text or "n/a"


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3g}"
    return str(value)


def _ci_text(pooled: dict[str, Any]) -> str:
    low = pooled.get("ci_low")
    high = pooled.get("ci_high")
    if low is None or high is None:
        return ""
    return f" (95% CI {_fmt(low)} to {_fmt(high)})"


def _pico_inline(pico: dict[str, Any]) -> str:
    return (
        f"P: {_join(pico.get('population'))}; "
        f"I: {_join(pico.get('intervention'))}; "
        f"C: {_join(pico.get('comparison'))}; "
        f"O: {_join(pico.get('outcome'))}"
    )


def _status_value(status: Any) -> str:
    return str(getattr(status, "value", status))


def build_app() -> gr.Blocks:
    css = """
    .gradio-container { max-width: 1400px !important; }
    #app-title { margin-bottom: 6px; }
    #app-title h2 { margin-bottom: 4px; }
    .trace-panel textarea { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }
    """
    with gr.Blocks(title="EBM Online Pipeline Demo", css=css) as demo:
        gr.Markdown(
            "## EBM Online Pipeline Demo\n"
            "Ask a clinical evidence question and watch the pipeline update step by step.",
            elem_id="app-title",
        )
        with gr.Row():
            with gr.Column(scale=4, min_width=320):
                question = gr.Textbox(
                    label="Clinical question",
                    value=DEFAULT_QUESTION,
                    lines=4,
                    placeholder="In patients ..., does ... compared with ... improve ...?",
                )
                preset = gr.Dropdown(
                    label="Demo question",
                    choices=DEMO_1000_QUESTION_PRESETS,
                    value=DEFAULT_QUESTION,
                    interactive=True,
                )
                with gr.Row():
                    top_k = gr.Slider(label="Top K", minimum=1, maximum=20, step=1, value=5)
                    use_mock = gr.Checkbox(label="Use mock LLM", value=False)
                index_path = gr.Textbox(label="Local index path", value=DEFAULT_INDEX_PATH, lines=1)
                run_button = gr.Button("Run pipeline", variant="primary")
            with gr.Column(scale=7, min_width=420):
                answer = gr.HTML(label="Answer")
                summary = gr.HTML(label="Run summary")
                error = gr.HTML(visible=False)

        with gr.Accordion("Pipeline timeline", open=True):
            timeline = gr.HTML()

        with gr.Tabs():
            with gr.Tab("Question"):
                with gr.Row():
                    pico = gr.HTML(label="PICO")
                    eligibility = gr.HTML(label="Eligibility")
                plan = gr.HTML(label="Analysis plan")
                pi = gr.HTML(label="PI extraction")
            with gr.Tab("Search"):
                query = gr.HTML(label="Query")
                candidates = gr.HTML(label="Top candidate studies")
            with gr.Tab("Screening"):
                screening = gr.HTML(label="Screening decisions")
            with gr.Tab("Extraction"):
                extraction = gr.HTML(label="Extraction rows")
            with gr.Tab("Risk of Bias"):
                rob = gr.HTML(label="Risk of Bias")
            with gr.Tab("Aggregation / GRADE"):
                aggregation = gr.HTML(label="Aggregation")
                grade = gr.HTML(label="GRADE Summary of Findings")
            with gr.Tab("Trace JSON"):
                trace_json = gr.JSON(label="Full trace")
                trace_file = gr.File(label="Download full trace JSON")

        outputs = [
            answer,
            summary,
            timeline,
            pico,
            eligibility,
            plan,
            pi,
            query,
            candidates,
            screening,
            extraction,
            rob,
            aggregation,
            grade,
            trace_json,
            trace_file,
            error,
        ]
        run_button.click(
            fn=run_pipeline,
            inputs=[question, preset, top_k, use_mock, index_path],
            outputs=outputs,
        )
        preset.change(fn=lambda value: value, inputs=preset, outputs=question)
    return demo


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Gradio Phase 6 EBM demo.")
    parser.add_argument("--host", default=os.getenv("GRADIO_SERVER_NAME", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("GRADIO_SERVER_PORT", "7860")))
    parser.add_argument("--share", action="store_true", default=os.getenv("GRADIO_SHARE", "").lower() == "true")
    args = parser.parse_args()
    build_app().queue().launch(server_name=args.host, server_port=args.port, share=args.share)


if __name__ == "__main__":
    main()
