from __future__ import annotations

import asyncio
import json
import sqlite3

import pytest

from ebm_backend.shared.llm.gateway import LLMGateway
from ebm_backend.online_pipeline.application.question_study import Module2LLMRunner, QuestionExpander, QuestionPIExtractor, QueryGenerator
from ebm_backend.shared.persistence.db import init_db


class _FakeLLMResponse:
    def __init__(self, content: dict):
        self.output_text = json.dumps(content, ensure_ascii=False)
        self._content = content

    def model_dump(self):
        return {
            "usage": {
                "prompt_tokens": 20,
                "completion_tokens": 30,
                "total_tokens": 50,
            }
        }


class _FakeResponses:
    def __init__(self, content: dict):
        self.content = content
        self.calls = 0

    async def create(self, **kwargs):
        self.calls += 1
        return _FakeLLMResponse(self.content)


class _FakeClient:
    def __init__(self, content: dict):
        self.responses = _FakeResponses(content)


class _SequentialResponses:
    def __init__(self, contents: list[dict]):
        self.contents = contents
        self.calls = 0

    async def create(self, **kwargs):
        content = self.contents[self.calls]
        self.calls += 1
        return _FakeLLMResponse(content)


class _SequentialClient:
    def __init__(self, contents: list[dict]):
        self.responses = _SequentialResponses(contents)


@pytest.fixture
def gateway_factory(tmp_path):
    def _make(content: dict) -> tuple[LLMGateway, _FakeClient]:
        db_path = tmp_path / "m2llm.db"
        init_db(f"sqlite:///{db_path}")
        conn = sqlite3.connect(db_path)
        client = _FakeClient(content)
        return LLMGateway(conn=conn, client=client, model="gpt-test"), client

    return _make


def _expansion_fixture() -> dict:
    return {
        "is_medical_question": True,
        "expanded_question": "In adults with type 2 diabetes, does metformin improve glycemic control?",
        "pico": {
            "population": ["adults with type 2 diabetes mellitus"],
            "intervention": ["metformin"],
            "comparison": ["placebo or usual care"],
            "outcome": ["HbA1c", "adverse events"],
        },
        "eligibility_criteria": {
            "inclusion": ["diagnosis of type 2 diabetes"],
            "exclusion": ["type 1 diabetes"],
            "confidence": "medium",
        },
        "preliminary_analysis_plan": {
            "primary_outcome": "change in HbA1c",
            "secondary_outcomes": ["fasting glucose"],
            "timepoints": ["12 weeks", "24 weeks"],
            "effect_measures": {"continuous": "MD or SMD", "binary": "RR or OR"},
            "subgroups_of_interest": [],
            "confidence": "low",
        },
        "needs_user_confirmation": ["preliminary_analysis_plan.confidence"],
    }


def test_expand_with_llm_maps_payload(gateway_factory):
    gateway, client = gateway_factory(_expansion_fixture())
    expander = QuestionExpander()
    result = asyncio.run(expander.expand_with_llm(gateway, "metformin for diabetes?"))
    assert client.responses.calls == 1
    assert result.is_medical_question is True
    assert "metformin" in " ".join(result.pico.intervention).lower()
    assert result.pico.population
    assert result.needs_user_confirmation
    assert result.preliminary_analysis_plan.effect_measures.get("continuous")


def test_generate_with_llm_merges_extra_terms(gateway_factory):
    gateway, client = gateway_factory(
        {
            "population_extra_terms": ["T2DM"],
            "intervention_extra_terms": ["Dimethylbiguanidine"],
            "notes": "test",
        }
    )
    gen = QueryGenerator()
    out = asyncio.run(
        gen.generate_with_llm(
            gateway,
            population=["type 2 diabetes mellitus"],
            intervention=["metformin"],
        )
    )
    assert client.responses.calls == 1
    assert "T2DM" in out.boolean_query or "t2dm" in out.boolean_query.lower()
    assert "Dimethylbiguanidine" in out.boolean_query or "dimethylbiguanidine" in out.boolean_query.lower()


def test_question_pi_extractor_with_llm_uses_no_sql_gateway():
    gateway = LLMGateway(
        conn=None,
        client=_FakeClient(
            {
                "population": ["adults with type 2 diabetes mellitus"],
                "intervention": ["metformin"],
                "notes": "test",
            }
        ),
        model="gpt-test",
    )
    expansion = asyncio.run(QuestionExpander().expand_with_llm(gateway, "metformin for diabetes?"))
    # The fake client above returns PI payload, so build a deterministic expansion for PI extraction.
    expansion = QuestionExpander().expand(
        "metformin for diabetes?",
        pico=type(expansion.pico)(
            population=["adults with type 2 diabetes mellitus"],
            intervention=["metformin"],
        ),
    )
    pi = asyncio.run(QuestionPIExtractor().extract_with_llm(gateway, expansion))
    assert pi.population == ["adults with type 2 diabetes mellitus"]
    assert pi.intervention == ["metformin"]


def test_module2_llm_runner_returns_downstream_payload(tmp_path):
    gateway = LLMGateway(
        conn=None,
        client=_SequentialClient(
            [
                _expansion_fixture(),
                {
                    "population": ["adults with type 2 diabetes mellitus"],
                    "intervention": ["metformin"],
                    "notes": "pi",
                },
                {
                    "population_mappings": [
                        {
                            "original": "adults with type 2 diabetes mellitus",
                            "mesh_preferred": ["Diabetes Mellitus, Type 2"],
                            "entry_terms": ["T2DM"],
                        }
                    ],
                    "intervention_mappings": [
                        {
                            "original": "metformin",
                            "mesh_preferred": ["Metformin"],
                            "entry_terms": ["Dimethylbiguanidine"],
                        }
                    ],
                    "population_extra_terms": [],
                    "intervention_extra_terms": [],
                    "notes": "mesh",
                },
            ]
        ),
        model="gpt-test",
    )
    index_path = tmp_path / "index.jsonl"
    index_path.write_text(
        '{"study_id":"s1","pmid":"1","pmcid":"PMC1","title":"Metformin trial",'
        '"abstract":"Adults with type 2 diabetes received metformin.",'
        '"population":"Diabetes Mellitus, Type 2","intervention":"Metformin",'
        '"source":"PMC","article_path":"demo.json"}\n',
        encoding="utf-8",
    )
    result = asyncio.run(Module2LLMRunner(gateway, index_path=index_path).run("metformin?", top_k=3))
    assert result.pi.population
    assert "metformin" in result.query.boolean_query.lower()
    assert result.search.returned_count == 1
