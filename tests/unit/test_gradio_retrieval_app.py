from __future__ import annotations

import json
from pathlib import Path

from frontend.gradio_retrieval_app import build_retrieval_app, run_retrieval, show_cleaned_article


def test_retrieval_gradio_static_mode_hides_clean_preview(tmp_path):
    index_path = _index_path(tmp_path)
    outputs = run_retrieval(
        "Does duloxetine reduce catheter-related bladder discomfort?",
        "",
        "static",
        3,
        str(index_path),
        False,
        True,
        True,
    )
    assert len(outputs) == 8
    flow_html = outputs[0]
    stats_html = outputs[2]
    assert "检索流程" in flow_html
    assert "retrieved_total" in stats_html
    assert "question_expansion_ms" in stats_html
    assert "total_ms" in stats_html
    assert "online_backfill_used" not in stats_html
    cleaned_choice_update = outputs[4]
    preview_button_update = outputs[5]
    preview_html = outputs[6]
    assert cleaned_choice_update.get("visible") is False
    assert preview_button_update.get("visible") is False
    assert "静态模式不显示清洗预览" in preview_html


def test_retrieval_gradio_dynamic_mode_shows_clean_preview_controls(tmp_path):
    index_path = _index_path(tmp_path)
    outputs = run_retrieval(
        "Does duloxetine reduce catheter-related bladder discomfort?",
        "",
        "dynamic",
        3,
        str(index_path),
        True,
        True,
        True,
    )
    assert len(outputs) == 8
    stats_html = outputs[2]
    assert "retrieved_total" in stats_html
    assert "online_backfill_used" in stats_html
    assert "question_expansion_ms" in stats_html
    assert "total_ms" in stats_html
    cleaned_choice_update = outputs[4]
    preview_button_update = outputs[5]
    assert cleaned_choice_update.get("visible") is True
    assert preview_button_update.get("visible") is True


def test_retrieval_gradio_app_builds():
    app = build_retrieval_app()
    assert app.blocks


def test_show_cleaned_article_renders_cleaned_body_text(tmp_path: Path):
    article_path = tmp_path / "cleaned.json"
    article_path.write_text(
        json.dumps(
            {
                "study_id": "pmid:999",
                "metadata": {"title": "A cleaned RCT article", "pmid": "999", "pmc_id": "PMC999"},
                "derived": {},
                "xml_content": {
                    "sections": [
                        {"section": "abstract", "text": "This is cleaned abstract text."},
                        {"section": "results", "text": "This is cleaned results text."},
                    ],
                    "tables": [],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    html = show_cleaned_article(str(article_path), "dynamic")
    assert "清洗后正文全文预览" in html
    assert "This is cleaned abstract text." in html


def test_show_cleaned_article_handles_no_sections(tmp_path: Path):
    article_path = tmp_path / "cleaned_blocks.json"
    article_path.write_text(
        json.dumps(
            {
                "study_id": "pmid:100",
                "metadata": {"title": "Block style cleaned article", "pmid": "100", "pmc_id": "PMC100"},
                "derived": {},
                "xml_content": {"sections": [], "tables": []},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    html = show_cleaned_article(str(article_path), "dynamic")
    assert "暂无可展示的清洗正文段落" in html


def test_show_cleaned_article_rejects_legacy_blocks_schema(tmp_path: Path):
    article_path = tmp_path / "legacy_blocks.json"
    article_path.write_text(
        json.dumps(
            {
                "study_id": "pmid:100",
                "metadata": {"title": "Legacy", "pmid": "100", "pmc_id": "PMC100"},
                "derived": {},
                "xml_content": {
                    "sections": [{"section": "Results", "blocks": [{"text": "legacy"}]}],
                    "tables": [],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    html = show_cleaned_article(str(article_path), "dynamic")
    assert "读取失败" in html
    assert "legacy cleaned schema is not supported" in html


def _index_path(tmp_path: Path) -> Path:
    path = tmp_path / "local_rct_index.jsonl"
    doc = {
        "study_id": "pmid:37877838",
        "pmid": "37877838",
        "pmcid": "PMC1",
        "title": "Duloxetine catheter-related bladder discomfort trial",
        "abstract": "Adults with catheter related bladder discomfort received duloxetine or placebo.",
        "population": "catheter-related bladder discomfort",
        "intervention": "duloxetine",
        "source": "PMC",
        "article_path": None,
    }
    path.write_text(json.dumps(doc, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
