from __future__ import annotations

import json
from pathlib import Path

from ebm_backend.index_construction.application import build_module1_local_index_from_derived
from ebm_backend.online_pipeline.application.question_study import DEFAULT_LOCAL_INDEX_PATH, PICO, QueryGenerator, QuestionExpander, QuestionStudySearcher


def _ensure_local_index(tmp_path: Path) -> Path:
    default_index = Path(DEFAULT_LOCAL_INDEX_PATH)
    if default_index.exists():
        return default_index
    target = tmp_path / "local_rct_index.jsonl"
    result = build_module1_local_index_from_derived(
        data_root="data/data_for_test/data/data_for_test/data_demo_with_mesh",
        index_path=target,
        run_query_validation=False,
    )
    if result.indexed == 0:
        _write_fallback_local_index(target)
    return target


def _write_fallback_local_index(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    docs = [
        {
            "study_id": "pmid:37877838",
            "pmid": "37877838",
            "pmcid": "PMC10081038",
            "title": "Duloxetine in Reducing Catheter-Related Bladder Discomfort",
            "abstract": "Adults undergoing surgery with urinary catheterization received duloxetine or placebo for catheter-related bladder discomfort.",
            "population": "adults undergoing surgery with urinary catheterization catheter-related bladder discomfort",
            "intervention": "duloxetine",
            "population_original": "catheter-related bladder discomfort",
            "intervention_original": "duloxetine",
            "mesh_terms": [],
            "mesh_population": [],
            "mesh_intervention": [],
            "source": "unit",
            "article_path": None,
        },
        {
            "study_id": "pmid:36908720",
            "pmid": "36908720",
            "pmcid": "PMC-demo",
            "title": "Zinc-carbonate hydroxyapatite for postoperative sensitivity after composite restoration",
            "abstract": "Dental caries and hydroxyapatite trial in occlusal carious teeth.",
            "population": "dental caries carious teeth",
            "intervention": "hydroxyapatite zinc-carbonate hydroxyapatite",
            "population_original": "dental caries",
            "intervention_original": "hydroxyapatite",
            "mesh_terms": ["Dental Caries", "Hydroxyapatites"],
            "mesh_population": ["Dental Caries"],
            "mesh_intervention": ["Hydroxyapatites"],
            "source": "unit",
            "article_path": None,
        },
    ]
    path.write_text("\n".join(json.dumps(doc, ensure_ascii=False) for doc in docs) + "\n", encoding="utf-8")


def test_query_generator_builds_boolean_query_and_dedupes():
    generator = QueryGenerator()
    output = generator.generate(
        population=["dental caries", "Dental Caries"],
        intervention=["hydroxyapatite"],
    )

    assert "AND" in output.boolean_query
    assert '"dental caries"' in output.population_block.lower()
    assert "dental caries" in output.population_block.lower()
    assert "Tooth Decay" in output.population_block
    assert "Hydroxyapatites" in output.intervention_block
    assert output.search_filters["open_access"] is True
    assert output.search_filters["article_type"] == "primary_rct"


def test_question_expander_from_pico():
    expander = QuestionExpander()
    pico = PICO(
        population=["adults with type 2 diabetes mellitus"],
        intervention=["metformin"],
    )
    result = expander.from_pico("metformin 是否改善 2 型糖尿病?", pico)
    assert result.pico.population == ["adults with type 2 diabetes mellitus"]
    assert result.pico.intervention == ["metformin"]
    assert result.needs_user_confirmation


def test_question_to_study_local_search_returns_candidates(tmp_path: Path):
    index_path = _ensure_local_index(tmp_path)
    generator = QueryGenerator()
    searcher = QuestionStudySearcher(index_path=index_path)
    query_output = generator.generate(
        population=["dental caries"],
        intervention=["hydroxyapatite"],
    )
    result = searcher.search_from_query_output(query_output, top_k=5)
    assert result.returned_count > 0
    assert result.studies[0].study_id
    assert result.studies[0].title
    assert result.studies[0].matched_fields


def test_default_question_search_index_is_demo_1000():
    assert DEFAULT_LOCAL_INDEX_PATH == "data/data_for_test/data_demo_1000/index/local_rct_index.jsonl"
    assert Path(DEFAULT_LOCAL_INDEX_PATH).exists()


# 与 data/data_for_test/data/data_for_test/data_demo_with_mesh 100 篇索引中 pmid:37877838 全文高度一致；用于验证本地检索排序。
_DULOXETINE_CRBD_QUESTION = (
    "In adults undergoing surgery with a urinary catheter, does duloxetine reduce "
    "catheter-related bladder discomfort compared with placebo?"
)


def test_clinical_question_retrieval_ranks_duloxetine_catheter_trial_first(tmp_path: Path):
    index_path = _ensure_local_index(tmp_path)
    expansion = QuestionExpander().from_pico(
        _DULOXETINE_CRBD_QUESTION,
        PICO(
            population=[
                "adults undergoing surgery with urinary catheterization",
                "catheter-related bladder discomfort",
            ],
            intervention=["duloxetine"],
        ),
    )
    assert expansion.question == _DULOXETINE_CRBD_QUESTION

    query_out = QueryGenerator().generate(
        population=expansion.pico.population,
        intervention=expansion.pico.intervention,
    )
    result = QuestionStudySearcher(index_path=index_path).search_from_query_output(query_out, top_k=5)

    assert result.returned_count >= 1
    assert result.studies[0].study_id == "pmid:37877838"
    assert "duloxetine" in result.studies[0].title.lower()
    assert "catheter" in result.studies[0].title.lower()
