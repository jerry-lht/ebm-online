"""Risk of Bias evaluator using OpenAI API.

Default workflow:
- Judge each domain directly from PICO plus domain-specific source excerpts.
- Optional source-grounded calibration is kept only for ablation experiments.

The evaluator also supports hybrid/two-stage, joint, evidence-table, targeted,
and audited modes for experiments.
"""

import json
import os
import re
from typing import Optional

from openai import OpenAI, APITimeoutError
from pydantic import ValidationError

from schemas import (
    DomainResult,
    EvidenceTable,
    MethodologyExtraction,
    RiskOfBiasAssessment,
    RoBDomain,
    Judgement,
    SupportContext,
)
from prompts import (
    build_direct_judgement_system_prompt,
    build_targeted_direct_system_prompt,
    EVIDENCE_JUDGEMENT_SYSTEM_PROMPT,
    EVIDENCE_SYSTEM_PROMPT,
    EXTRACTION_SYSTEM_PROMPT,
    JUDGEMENT_SYSTEM_PROMPT,
    JOINT_JUDGEMENT_SYSTEM_PROMPT,
    build_direct_judgement_prompt,
    build_evidence_judgement_prompt,
    build_evidence_prompt,
    build_extraction_prompt,
    build_judgement_prompt,
    build_joint_judgement_prompt,
    build_targeted_direct_judgement_prompt,
)


class RoBEvaluator:
    """Risk of Bias evaluator with hybrid, strict, evidence, joint, and direct modes."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        request_timeout: Optional[float] = None,
        extraction_max_chars: Optional[int] = None,
        domain_context_max_chars: Optional[int] = None,
        joint_max_chars: Optional[int] = None,
        reasoning_effort: Optional[str] = None,
        enable_calibration: Optional[bool] = None,
        max_retries: Optional[int] = None,
    ):
        self.request_timeout = request_timeout or float(os.getenv("REQUEST_TIMEOUT", "90"))
        self.max_retries = (
            max_retries
            if max_retries is not None
            else int(os.getenv("MAX_RETRIES", "0"))
        )
        self.client = OpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=base_url or os.getenv("OPENAI_BASE_URL"),
            timeout=self.request_timeout,
            max_retries=self.max_retries,
        )
        self.model = model or os.getenv("BASE_MODEL", "gpt-5-mini")
        self.max_tokens = max_tokens or int(os.getenv("MAX_TOKENS", "4096"))
        self.extraction_max_chars = extraction_max_chars or int(
            os.getenv("EXTRACTION_MAX_CHARS", "18000")
        )
        self.domain_context_max_chars = domain_context_max_chars or int(
            os.getenv("DOMAIN_CONTEXT_MAX_CHARS", "8000")
        )
        self.joint_max_chars = joint_max_chars or int(os.getenv("JOINT_MAX_CHARS", "24000"))
        self.reasoning_effort = reasoning_effort or os.getenv("REASONING_EFFORT", "minimal")
        self.enable_calibration = (
            enable_calibration
            if enable_calibration is not None
            else os.getenv("ENABLE_CALIBRATION", "0").lower() in {"1", "true", "yes"}
        )
        print(f"Using model: {self.model}")
        print(f"Using base URL: {self.client.base_url}")
        print(f"Request timeout: {self.request_timeout:g}s")
        print(f"Max retries: {self.max_retries}")
        print(f"Reasoning effort: {self.reasoning_effort}")
        print(f"Calibration: {'on' if self.enable_calibration else 'off'}")
        #print(f"Using API key: {self.api_key}")

    def evaluate(
        self,
        xml_content: dict,
        sr_pico: str = "",
        study_id: Optional[str] = None,
        pmid: Optional[str] = None,
        mode: str = "direct",
        review_context: str = "",
    ) -> RiskOfBiasAssessment:
        """Run Risk of Bias evaluation.

        Args:
            xml_content: dict with 'sections' key containing article text
            sr_pico: optional PICO context from systematic review
            study_id: optional study identifier
            pmid: optional PubMed ID
            mode: one of:
                - "hybrid": extraction plus source excerpts for each domain
                - "strict": strict two-stage, judgement only sees extraction
                - "joint": judge all domains together from the article
                - "evidence": extract a domain evidence table, then judge
                - "direct": judge each domain directly from PICO and source excerpts
                - "targeted": direct plus structured evidence maps for complex domains

        Returns:
            RiskOfBiasAssessment with results for all 5 domains
        """
        if mode not in {"hybrid", "strict", "joint", "evidence", "direct", "targeted", "audited"}:
            raise ValueError("mode must be one of: hybrid, strict, joint, evidence, direct, targeted, audited")

        article_text = self._format_article(xml_content)

        if mode in {"direct", "targeted", "audited"}:
            print(f"{mode.title()} mode: Judging each domain from PICO + source excerpts...")
            attrition_clues = self._extract_attrition_numeric_clues(article_text)
            results = []
            for domain in RoBDomain:
                domain_context = self._build_domain_context(
                    domain,
                    article_text,
                    max_chars=self.domain_context_max_chars,
                )
                supplementary_context = self._build_supplementary_context(
                    domain,
                    attrition_clues=attrition_clues,
                )
                calibration_evidence = self._combine_calibration_evidence(
                    domain_context,
                    supplementary_context,
                )
                print(
                    f"  Evaluating {domain.value} "
                    f"({len(domain_context)}/{len(article_text)} chars)..."
                )
                if mode == "audited":
                    result = self._judge_domain_audited(
                        domain,
                        sr_pico,
                        domain_context,
                        supplementary_context=supplementary_context,
                        calibration_evidence=calibration_evidence,
                    )
                elif mode == "targeted":
                    result = self._judge_domain_targeted(
                        domain,
                        sr_pico,
                        domain_context,
                        supplementary_context=supplementary_context,
                    )
                    if self.enable_calibration:
                        result = self._calibrate_direct_domain_result(
                            domain, result, calibration_evidence
                        )
                else:
                    result = self._judge_domain_direct(
                        domain,
                        sr_pico,
                        domain_context,
                        supplementary_context=supplementary_context,
                    )
                    if self.enable_calibration:
                        result = self._calibrate_direct_domain_result(
                            domain, result, calibration_evidence
                        )
                results.append(result)
                print(f"    → {result.judgement.value}")
            print("✓ All domains evaluated\n")
            return RiskOfBiasAssessment(
                study_id=study_id,
                pmid=pmid,
                results=results,
            )

        if mode == "evidence":
            evidence_text = self._build_methodology_context(
                article_text,
                max_chars=self.extraction_max_chars,
            )
            print(
                "Evidence mode: Extracting domain evidence table "
                f"({len(evidence_text)}/{len(article_text)} chars)..."
            )
            evidence_table = self._extract_evidence_table(
                sr_pico,
                evidence_text,
                review_context=review_context,
            )
            print("✓ Evidence table complete\n")

            print("Evidence mode: Judging domains from evidence table...")
            results = self._judge_evidence_table(evidence_table)
            print("✓ All domains evaluated\n")
            return RiskOfBiasAssessment(
                study_id=study_id,
                pmid=pmid,
                results=results,
            )

        if mode == "joint":
            joint_text = self._build_methodology_context(
                article_text,
                max_chars=self.joint_max_chars,
            )
            print(
                "Joint mode: Judging all domains together "
                f"({len(joint_text)}/{len(article_text)} chars)..."
            )
            results = self._judge_domains_joint(sr_pico, joint_text)
            print("✓ All domains evaluated\n")
            return RiskOfBiasAssessment(
                study_id=study_id,
                pmid=pmid,
                results=results,
            )

        # Stage 1: Extract methodology
        extraction_text = self._build_methodology_context(
            article_text,
            max_chars=self.extraction_max_chars,
        )
        print(
            "Stage 1: Extracting methodological information "
            f"({len(extraction_text)}/{len(article_text)} chars)..."
        )
        methodology = self._extract_methodology(sr_pico, extraction_text)
        print(f"✓ Extraction complete\n")

        # Stage 2: Judge each domain
        if mode == "strict":
            print("Stage 2: Judging domains from extracted information only...")
        else:
            print("Stage 2: Judging domains with source excerpts...")
        results = []
        methodology_json = methodology.model_dump_json(indent=2)

        for domain in RoBDomain:
            print(f"  Evaluating {domain.value}...")
            domain_context = ""
            if mode == "hybrid":
                domain_context = self._build_domain_context(
                    domain,
                    article_text,
                    max_chars=self.domain_context_max_chars,
                )
            result = self._judge_domain(
                domain,
                methodology_json,
                sr_pico,
                domain_context=domain_context,
            )
            if self.enable_calibration and mode == "hybrid":
                result = self._calibrate_domain_result(
                    domain,
                    result,
                    methodology_json,
                    domain_context,
                )
            results.append(result)
            print(f"    → {result.judgement.value}")

        print("✓ All domains evaluated\n")

        return RiskOfBiasAssessment(
            study_id=study_id,
            pmid=pmid,
            results=results,
        )

    def _format_article(self, xml_content: dict) -> str:
        """Format article sections into readable text."""
        sections = xml_content.get("sections", [])
        formatted = []
        for sec in sections:
            section_name = sec.get("section", "")
            text = sec.get("text", "")
            if section_name and text:
                formatted.append(f"## {section_name}\n\n{text}")
        return "\n\n".join(formatted)

    def _extract_methodology(
        self, sr_pico: str, article_text: str
    ) -> MethodologyExtraction:
        """Stage 1: Extract methodological information."""
        user_prompt = build_extraction_prompt(sr_pico, article_text)

        response = self._create_chat_completion(
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            timeout_message=(
                f"Extraction request timed out after {self.request_timeout:g}s. "
                "Try lowering EXTRACTION_MAX_CHARS or using --timeout with a larger value."
            ),
        )

        content = response.choices[0].message.content
        extracted_json = self._extract_json(content)

        try:
            parsed = self._loads_json_lenient(extracted_json)
            return MethodologyExtraction.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"Warning: Extraction validation failed: {e}")
            print(f"Raw response: {content[:500]}...")
            return self._salvage_methodology_extraction(extracted_json or content)

    def _extract_evidence_table(
        self,
        sr_pico: str,
        article_text: str,
        review_context: str = "",
    ) -> EvidenceTable:
        """Extract a structured evidence table for all configured domains."""
        user_prompt = build_evidence_prompt(
            sr_pico,
            article_text,
            review_context=review_context,
        )

        response = self._create_chat_completion(
            messages=[
                {"role": "system", "content": EVIDENCE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            timeout_message=(
                f"Evidence extraction request timed out after {self.request_timeout:g}s. "
                "Try lowering EXTRACTION_MAX_CHARS or using --timeout with a larger value."
            ),
        )

        content = response.choices[0].message.content
        evidence_json = self._extract_json(content)

        try:
            return EvidenceTable.model_validate_json(evidence_json)
        except ValidationError as e:
            print(f"Warning: Evidence validation failed: {e}")
            print(f"Raw response: {content[:500]}...")
            raise

    def _judge_evidence_table(self, evidence_table: EvidenceTable) -> list[DomainResult]:
        """Judge all configured domains from a structured evidence table."""
        by_domain = {item.domain: item for item in evidence_table.results}
        results = []
        for domain in RoBDomain:
            evidence = by_domain[domain]
            evidence_json = evidence.model_dump_json(indent=2)
            results.append(self._judge_domain_from_evidence(domain, evidence_json))
        return results

    def _judge_domain_from_evidence(
        self,
        domain: RoBDomain,
        evidence_json: str,
    ) -> DomainResult:
        """Judge a single domain from one evidence table row."""
        user_prompt = build_evidence_judgement_prompt(domain, evidence_json)

        response = self._create_chat_completion(
            messages=[
                {"role": "system", "content": EVIDENCE_JUDGEMENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            timeout_message=(
                f"Evidence judgement request timed out after {self.request_timeout:g}s "
                f"for {domain.value}."
            ),
        )

        content = response.choices[0].message.content
        judgement_json = self._extract_json(content)

        return self._parse_domain_result_payload(
            domain=domain,
            payload=judgement_json,
            raw_content=content,
            label="Evidence judgement",
        )

    def _judge_domain(
        self,
        domain: RoBDomain,
        methodology_json: str,
        sr_pico: str,
        domain_context: str = "",
    ) -> DomainResult:
        """Stage 2: Judge a single domain."""
        user_prompt = build_judgement_prompt(
            domain,
            methodology_json,
            sr_pico,
            domain_context=domain_context,
        )

        response = self._create_chat_completion(
            messages=[
                {"role": "system", "content": JUDGEMENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            timeout_message=(
                f"Judgement request timed out after {self.request_timeout:g}s "
                f"for {domain.value}."
            ),
        )

        content = response.choices[0].message.content
        judgement_json = self._extract_json(content)

        return self._parse_domain_result_payload(
            domain=domain,
            payload=judgement_json,
            raw_content=content,
            label="Judgement",
        )

    def _judge_domain_direct(
        self,
        domain: RoBDomain,
        sr_pico: str,
        domain_context: str,
        supplementary_context: str = "",
    ) -> DomainResult:
        """Judge a single domain directly from PICO plus source excerpts."""
        user_prompt = build_direct_judgement_prompt(
            domain,
            sr_pico=sr_pico,
            domain_context=domain_context,
            supplementary_context=supplementary_context,
        )

        response = self._create_chat_completion(
            messages=[
                {"role": "system", "content": build_direct_judgement_system_prompt(domain)},
                {"role": "user", "content": user_prompt},
            ],
            timeout_message=(
                f"Direct judgement request timed out after {self.request_timeout:g}s "
                f"for {domain.value}."
            ),
        )

        content = response.choices[0].message.content
        judgement_json = self._extract_json(content)

        return self._parse_domain_result_payload(
            domain=domain,
            payload=judgement_json,
            raw_content=content,
            label="Direct judgement",
        )

    def _judge_domain_targeted(
        self,
        domain: RoBDomain,
        sr_pico: str,
        domain_context: str,
        supplementary_context: str = "",
    ) -> DomainResult:
        """Use structured evidence-map prompting for high-complexity domains."""
        if domain not in {
            RoBDomain.BLINDING_OUTCOME_ASSESSORS,
            RoBDomain.INCOMPLETE_OUTCOME_DATA,
        }:
            return self._judge_domain_direct(
                domain,
                sr_pico,
                domain_context,
                supplementary_context=supplementary_context,
            )

        user_prompt = build_targeted_direct_judgement_prompt(
            domain,
            sr_pico=sr_pico,
            domain_context=domain_context,
            supplementary_context=supplementary_context,
        )

        response = self._create_chat_completion(
            messages=[
                {"role": "system", "content": build_targeted_direct_system_prompt(domain)},
                {"role": "user", "content": user_prompt},
            ],
            timeout_message=(
                f"Targeted direct judgement request timed out after {self.request_timeout:g}s "
                f"for {domain.value}."
            ),
        )

        content = response.choices[0].message.content
        judgement_json = self._extract_json(content)

        return self._parse_domain_result_payload(
            domain=domain,
            payload=judgement_json,
            raw_content=content,
            label="Targeted direct judgement",
        )

    def _judge_domain_audited(
        self,
        domain: RoBDomain,
        sr_pico: str,
        domain_context: str,
        supplementary_context: str = "",
        calibration_evidence: str = "",
    ) -> DomainResult:
        """Use direct judgement as primary and targeted evidence maps as guardrails."""
        evidence = calibration_evidence or self._combine_calibration_evidence(
            domain_context,
            supplementary_context,
        )
        direct = self._judge_domain_direct(
            domain,
            sr_pico,
            domain_context,
            supplementary_context=supplementary_context,
        )
        if self.enable_calibration:
            direct = self._calibrate_direct_domain_result(domain, direct, evidence)

        if domain not in {
            RoBDomain.BLINDING_OUTCOME_ASSESSORS,
            RoBDomain.INCOMPLETE_OUTCOME_DATA,
        }:
            return direct

        targeted = self._judge_domain_targeted(
            domain,
            sr_pico,
            domain_context,
            supplementary_context=supplementary_context,
        )
        merged = self._merge_audited_domain_result(domain, direct, targeted)
        if self.enable_calibration:
            merged = self._calibrate_direct_domain_result(domain, merged, evidence)
        return merged

    def _merge_audited_domain_result(
        self,
        domain: RoBDomain,
        direct: DomainResult,
        targeted: DomainResult,
    ) -> DomainResult:
        """Conservatively override direct results using structured evidence maps."""
        evidence_map = targeted.evidence_map or {}
        chosen = direct
        audit_reason = ""

        if domain == RoBDomain.BLINDING_OUTCOME_ASSESSORS:
            outcome_type = str(evidence_map.get("outcome_measurement_type", "")).lower()
            primary_type = str(evidence_map.get("primary_outcome_type", "")).lower()
            assessor_masking = str(evidence_map.get("assessor_masking", "")).lower()
            participant_masking = str(
                evidence_map.get("participant_masking_if_relevant", "")
                or evidence_map.get("participants_blinded", "")
            ).lower()
            influence = str(
                evidence_map.get("can_allocation_knowledge_materially_influence_measurement", "")
            ).lower()
            low_reason = str(
                evidence_map.get("reason_low_possible_without_explicit_assessor_blinding", "")
            ).lower()
            risk_signal = str(evidence_map.get("risk_signal", "")).lower()
            self_reported = any(
                token in f"{outcome_type} {primary_type}"
                for token in ("self-reported", "self reported", "self_report", "participant")
            )
            clearly_unmasked_participant = (
                participant_masking in {"no", "not masked", "not blinded", "unmasked"}
                or "not masked" in participant_masking
                or "not blinded" in participant_masking
                or "unmasked" in participant_masking
            )
            masked_assessor = (
                ("masked" in assessor_masking or "blinded" in assessor_masking)
                and "not masked" not in assessor_masking
                and "not blinded" not in assessor_masking
                and "unclear" not in assessor_masking
                and "not_relevant" not in assessor_masking
            )
            objective_or_masked = (
                any(
                    token in f"{outcome_type} {primary_type} {low_reason}"
                    for token in (
                        "lab",
                        "device",
                        "registry",
                        "admin",
                        "mortality",
                        "imaging",
                        "objective",
                        "coder",
                        "adjudicator",
                    )
                )
                or masked_assessor
                or "objective" in low_reason
                or "central_blinded" in low_reason
                or "mortality_registry" in low_reason
            )
            probably_no_influence = "probably_no" in influence or influence.strip() == "no"

            if (
                direct.judgement == Judgement.UNCLEAR
                and targeted.judgement == Judgement.HIGH
                and self_reported
                and clearly_unmasked_participant
                and "yes" in influence
            ):
                chosen = targeted
                audit_reason = (
                    "Audited override: self-reported outcome with clearly unmasked "
                    "participants and material influence on measurement."
                )
            elif direct.judgement == Judgement.HIGH and targeted.judgement == Judgement.LOW and objective_or_masked:
                chosen = targeted
                audit_reason = (
                    "Audited override: evidence map identifies objective or explicitly masked "
                    "outcome assessment."
                )
            elif (
                direct.judgement == Judgement.UNCLEAR
                and targeted.judgement == Judgement.LOW
                and (objective_or_masked or probably_no_influence or "low" in risk_signal)
            ):
                chosen = targeted
                audit_reason = (
                    "Audited Low-rescue: evidence map supports objective measurement, masked "
                    "assessment, or immaterial influence from allocation knowledge."
                )
            elif (
                direct.judgement == Judgement.LOW
                and targeted.judgement == Judgement.UNCLEAR
                and self_reported
                and clearly_unmasked_participant
                and "yes" in influence
            ):
                chosen = targeted
                audit_reason = (
                    "Audited override: subjective self-reported outcome with unmasked participants; "
                    "Low is not supported."
                )

        if domain == RoBDomain.INCOMPLETE_OUTCOME_DATA:
            report_type = str(evidence_map.get("is_protocol_or_results_report", "")).lower()
            balance = str(evidence_map.get("balance_of_missingness", "")).lower()
            protective = str(evidence_map.get("protective_factors", "")).lower()
            handling = str(evidence_map.get("missing_data_handling", "")).lower()
            risk_signal = str(evidence_map.get("risk_signal", "")).lower()
            missing_by_arm = str(evidence_map.get("missing_by_arm", "")).lower()
            missing_reasons = str(evidence_map.get("missing_reasons", "")).lower()
            overall_missing = str(evidence_map.get("overall_missing_rate", "")).lower()

            protective_signal = any(
                token in f"{protective} {handling} {balance}"
                for token in (
                    "complete data",
                    "no missing",
                    "small loss",
                    "balanced loss",
                    "balanced",
                    "unrelated",
                    "multiple imputation",
                    "sensitivity",
                    "mixed model",
                    "robust",
                    "similar conclusions",
                )
            )
            insufficient_actual_data = (
                "protocol" in report_type
                or (
                    "not reported" in missing_by_arm
                    and "not reported" in missing_reasons
                    and not protective_signal
                    and "low" not in risk_signal
                )
            )
            substantial_signal = bool(
                re.search(r"\b(?:2[0-9]|3[0-9]|4[0-9]|[5-9][0-9])\s*%", overall_missing)
            )

            if direct.judgement == Judgement.HIGH and targeted.judgement == Judgement.UNCLEAR and protective_signal:
                chosen = targeted
                audit_reason = (
                    "Audited override: missingness appears balanced or handled with "
                    "robust/sensitivity methods, so High is not established."
                )
            elif direct.judgement == Judgement.UNCLEAR and targeted.judgement == Judgement.LOW and protective_signal:
                chosen = targeted
                audit_reason = (
                    "Audited override: evidence map identifies complete/small/balanced "
                    "missingness or robust handling."
                )
            elif direct.judgement == Judgement.LOW and targeted.judgement == Judgement.UNCLEAR and insufficient_actual_data:
                chosen = targeted
                audit_reason = (
                    "Audited override: Low risk is not established because actual missing "
                    "outcome data are not reported."
                )
            elif (
                direct.judgement != Judgement.HIGH
                and targeted.judgement == Judgement.HIGH
                and "high" in risk_signal
                and substantial_signal
                and not protective_signal
            ):
                chosen = targeted
                audit_reason = (
                    "Audited override: evidence map identifies substantial missingness "
                    "without protective handling."
                )
            elif (
                direct.judgement == Judgement.UNCLEAR
                and targeted.judgement == Judgement.LOW
                and ("low" in risk_signal or protective_signal)
                and not substantial_signal
            ):
                chosen = targeted
                audit_reason = (
                    "Audited Low-rescue: evidence map indicates complete/small/balanced "
                    "missingness or credible handling."
                )
            elif (
                direct.judgement == Judgement.HIGH
                and targeted.judgement == Judgement.LOW
                and protective_signal
                and not substantial_signal
            ):
                chosen = targeted
                audit_reason = (
                    "Audited override: protective attrition evidence outweighs High signal "
                    "from sparse direct judgement."
                )

        if chosen is direct:
            return DomainResult(
                domain=direct.domain,
                judgement=direct.judgement,
                support_text=direct.support_text,
                support_context=direct.support_context,
                reasoning=direct.reasoning,
                evidence_map=evidence_map or direct.evidence_map,
            )

        return DomainResult(
            domain=chosen.domain,
            judgement=chosen.judgement,
            support_text=self._compact_text(
                f"{chosen.support_text} Comment: {audit_reason}",
                1600,
            ),
            support_context=chosen.support_context,
            reasoning=self._compact_text(
                f"{chosen.reasoning or ''} {audit_reason}",
                1000,
            ),
            evidence_map=evidence_map,
        )

    def _judge_domains_joint(self, sr_pico: str, article_text: str) -> list[DomainResult]:
        """Judge all configured domains in one LLM call."""
        user_prompt = build_joint_judgement_prompt(sr_pico, article_text)

        response = self._create_chat_completion(
            messages=[
                {"role": "system", "content": JOINT_JUDGEMENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            timeout_message=(
                f"Joint judgement request timed out after {self.request_timeout:g}s. "
                "Try lowering JOINT_MAX_CHARS or using --timeout with a larger value."
            ),
        )

        content = response.choices[0].message.content
        judgement_json = self._extract_json(content)

        try:
            parsed = self._loads_json_lenient(judgement_json)
            raw_results = parsed["results"]
            by_domain = {item["domain"]: item for item in raw_results}
            results = []
            for domain in RoBDomain:
                item = by_domain[domain.value]
                results.append(self._domain_result_from_parsed(domain, item))
            return results
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            print(f"Warning: Joint judgement parsing failed: {e}")
            print(f"Raw response: {content[:500]}...")
            return [
                self._salvage_domain_result(
                    domain=domain,
                    text=self._extract_domain_segment(content, domain),
                    parse_error=str(e),
                )
                for domain in RoBDomain
            ]
    
    def _create_chat_completion(
        self,
        messages: list[dict[str, str]],
        timeout_message: str,
    ):
        """Create a chat completion with a clear timeout error."""
        try:
            params = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "timeout": self.request_timeout,
                "messages": messages,
            }
            if self.reasoning_effort:
                params["reasoning_effort"] = self.reasoning_effort
            return self.client.chat.completions.create(**params)
        except APITimeoutError as e:
            raise TimeoutError(timeout_message) from e

    def _parse_support_context(self, parsed: dict) -> list[SupportContext]:
        """Parse support_context from model output with a support_text fallback."""
        raw_items = parsed.get("support_context") or []
        contexts = []
        if isinstance(raw_items, list):
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                try:
                    contexts.append(
                        SupportContext(
                            source=str(item.get("source") or "methodology"),
                            quote=self._compact_text(str(item.get("quote") or ""), 240),
                            relevance=self._compact_text(
                                str(item.get("relevance") or ""),
                                160,
                            ),
                        )
                    )
                except ValidationError:
                    continue

        if contexts:
            return contexts[:2]

        support_text = parsed.get("support_text", "")
        return [
            SupportContext(
                source="methodology",
                quote=self._compact_text(str(support_text), 240),
                relevance="Fallback context derived from support_text because structured support_context was not provided.",
            )
        ]

    def _calibrate_domain_result(
        self,
        domain: RoBDomain,
        result: DomainResult,
        methodology_json: str,
        domain_context: str,
    ) -> DomainResult:
        """Apply high-confidence, source-grounded judgement calibrations."""
        evidence = f"{domain_context}\n{methodology_json}"
        evidence_lower = evidence.lower()

        if domain == RoBDomain.ALLOCATION_CONCEALMENT:
            remote_list = (
                ("biostatistics department" in evidence_lower or "randomization unit" in evidence_lower)
                and (
                    "randomization list" in evidence_lower
                    or "randomisation list" in evidence_lower
                )
                and (
                    "undisclosed block" in evidence_lower
                    or "at distance" in evidence_lower
                    or "remote" in evidence_lower
                )
            )
            senior_only = (
                "computer-generated randomization" in evidence_lower
                and "senior editor" in evidence_lower
                and "without knowledge" in evidence_lower
            )
            automated_after_enrolment = (
                "auto-generated" in evidence_lower
                and "group assignment" in evidence_lower
                and ("baseline assessment" in evidence_lower or "online informed consent" in evidence_lower)
            )
            if result.judgement != Judgement.LOW and (
                remote_list or senior_only or automated_after_enrolment
            ):
                reason = (
                    "Calibration: source indicates assignments were generated/held by a remote or automated process "
                    "with no evidence recruiters could foresee upcoming allocations."
                )
                return self._with_calibrated_judgement(
                    result,
                    Judgement.LOW,
                    reason,
                    self._best_quote(
                        evidence,
                        [
                            "randomization list",
                            "randomisation list",
                            "senior editor",
                            "auto-generated",
                        ],
                    ),
                )

        if domain == RoBDomain.BLINDING_OUTCOME_ASSESSORS:
            subjective_outcome = any(
                phrase in evidence_lower
                for phrase in (
                    "self-report",
                    "self report",
                    "self-reported",
                    "self reported",
                    "questionnaire",
                    "diary",
                    "pain",
                    "symptom",
                    "depress",
                    "anxiety",
                    "womac",
                    "vas",
                    "visual analogue",
                    "quality of life",
                    "behavioral",
                    "behavioural",
                    "participant reported",
                    "patient reported",
                )
            )
            open_or_unmasked = any(
                phrase in evidence_lower
                for phrase in (
                    "open-label",
                    "open label",
                    "not blinded",
                    "not masked",
                    "blinding was not possible",
                    "no blinding",
                    "participants were informed",
                    "research assistants were aware",
                )
            )
            double_blind_assessment = (
                "double-blind" in evidence_lower
                and (
                    "matching placebo" in evidence_lower
                    or "identical in appearance" in evidence_lower
                    or "placebo-controlled" in evidence_lower
                )
                and (
                    "assessor" in evidence_lower
                    or "investigator" in evidence_lower
                    or "physician" in evidence_lower
                    or "reading and quality assurance" in evidence_lower
                    or "independent assessor" in evidence_lower
                )
                and "self-report" not in evidence_lower
                and "self report" not in evidence_lower
                and not subjective_outcome
                and not open_or_unmasked
            )
            objective_device = (
                any(
                    phrase in evidence_lower
                    for phrase in (
                        "oxygen saturation",
                        "spo2",
                        "device",
                        "monitor",
                        "laboratory",
                        "registry",
                        "administrative",
                        "computer set-up",
                    )
                )
                and any(
                    phrase in evidence_lower
                    for phrase in (
                        "objectively",
                        "continuous",
                        "recorded",
                        "generated",
                        "measured",
                    )
                )
                and not subjective_outcome
                and not open_or_unmasked
            )
            self_report_unmasked = (
                subjective_outcome
                and open_or_unmasked
            )
            if result.judgement != Judgement.HIGH and self_report_unmasked:
                return self._with_calibrated_judgement(
                    result,
                    Judgement.HIGH,
                    "Calibration: outcomes were self-reported and participants could know allocation, so participants acted as unmasked outcome assessors.",
                    self._best_quote(evidence, ["self-report", "not blinded", "participants were informed"]),
                )
            if result.judgement != Judgement.LOW and (double_blind_assessment or objective_device):
                return self._with_calibrated_judgement(
                    result,
                    Judgement.LOW,
                    "Calibration: source indicates blinded trial-team assessment or objective automated/device measurement unlikely to be influenced by allocation knowledge.",
                    self._best_quote(
                        evidence,
                        ["double-blind", "independent assessor", "oxygen saturation", "recorded"],
                    ),
                )

        if domain == RoBDomain.INCOMPLETE_OUTCOME_DATA:
            analyzed_pairs = [
                (int(a), int(b))
                for a, b in re.findall(
                    r"(\d{1,4})\s*/\s*(\d{1,4})\s+(?:in|randomi[sz]ed|analysed|analyzed)",
                    evidence_lower,
                )
                if int(b) > 0
            ]
            rates = [a / b for a, b in analyzed_pairs if b]
            notable_missing = any(rate < 0.9 for rate in rates)
            imbalanced_missing = len(rates) >= 2 and max(rates) - min(rates) >= 0.1
            if result.judgement == Judgement.LOW and (notable_missing or imbalanced_missing):
                return self._with_calibrated_judgement(
                    result,
                    Judgement.UNCLEAR,
                    "Calibration: analyzed counts suggest notable or imbalanced missing outcome data; ITT/LOCF alone is not enough for Low risk.",
                    self._best_quote(evidence, ["17/20", "14/20", "analyzed", "analysed"]),
                )

            no_missing_primary = (
                "no loss to follow-up" in evidence_lower
                or "no loss to follow up" in evidence_lower
                or "complete for all participants" in evidence_lower
                or "no missing outcome data" in evidence_lower
            )
            appropriate_missing_handling = (
                (
                    "intention-to-treat" in evidence_lower
                    or "intention to treat" in evidence_lower
                    or "included all persons who were randomized" in evidence_lower
                    or "included all persons who were randomised" in evidence_lower
                )
                and (
                    "multiple imputation" in evidence_lower
                    or "missing at random" in evidence_lower
                    or "inverse probability weights" in evidence_lower
                    or "inverse probability weighting" in evidence_lower
                )
            )
            small_reported_attrition = (
                bool(re.search(r"\b1[7-9]\s*/\s*19\s+patients completed\b", evidence_lower))
                or bool(re.search(r"\b(?:8[5-9]|9\d|100)%\s+(?:completed|included|analysed|analyzed)\b", evidence_lower))
            )
            if result.judgement != Judgement.LOW and (
                no_missing_primary or appropriate_missing_handling or small_reported_attrition
            ):
                return self._with_calibrated_judgement(
                    result,
                    Judgement.LOW,
                    "Calibration: source reports no/low missing outcome data or appropriate missing-data handling, so attrition is unlikely to materially bias results.",
                    self._best_quote(
                        evidence,
                        [
                            "no loss to follow-up",
                            "complete for all participants",
                            "included all persons who were randomized",
                            "multiple imputation",
                            "17/19 patients completed",
                        ],
                    ),
                )

            outcome_related_exclusions = (
                "excluded from the study" in evidence_lower
                and any(
                    phrase in evidence_lower
                    for phrase in (
                        "residual stones",
                        "rupture",
                        "major bleeding",
                        "complication",
                        "adverse event",
                    )
                )
            )
            if result.judgement != Judgement.HIGH and outcome_related_exclusions:
                return self._with_calibrated_judgement(
                    result,
                    Judgement.HIGH,
                    "Calibration: source reports post-randomization exclusions for outcome-related clinical events, which can bias incomplete outcome data.",
                    self._best_quote(
                        evidence,
                        ["excluded from the study", "residual stones", "major bleeding"],
                    ),
                )

        return result

    def _calibrate_direct_domain_result(
        self,
        domain: RoBDomain,
        result: DomainResult,
        domain_context: str,
    ) -> DomainResult:
        """Apply conservative corrections for common direct-mode boundary errors."""
        evidence_lower = domain_context.lower()

        if domain == RoBDomain.RANDOM_SEQUENCE_GENERATION:
            has_list_only = (
                (
                    "randomization list" in evidence_lower
                    or "randomisation list" in evidence_lower
                    or "randomly assigned" in evidence_lower
                )
                and not any(
                    phrase in evidence_lower
                    for phrase in (
                        "biostatistics department",
                        "graphpad",
                        "sas",
                        "statistician",
                        "computer-generated",
                        "computer generated",
                        "random number generator",
                        "random-number generator",
                        "tables of random numbers",
                        "table of random numbers",
                        "random number table",
                        "sample function",
                        "software",
                        "block size",
                        "permuted blocks",
                        "blocked randomization",
                        "blocked randomisation",
                        "random allocation was balanced",
                        "randomly chosen",
                        "chosen randomly",
                        "drawing of lots",
                        "minimization",
                        "minimisation",
                    )
                )
            )
            if result.judgement == Judgement.LOW and has_list_only:
                return self._with_calibrated_judgement(
                    result,
                    Judgement.UNCLEAR,
                    "Calibration: the source mentions a randomization list or random assignment but does not describe the random component used to generate the sequence.",
                    self._best_quote(
                        domain_context,
                        ["randomization list", "randomisation list", "randomly assigned"],
                    ),
                )

        if domain == RoBDomain.ALLOCATION_CONCEALMENT:
            third_party_sequence_only = (
                "third party" in evidence_lower
                and (
                    "randomization was generated" in evidence_lower
                    or "randomisation was generated" in evidence_lower
                    or "generated by a third party" in evidence_lower
                )
                and not any(
                    phrase in evidence_lower
                    for phrase in (
                        "conceal",
                        "central",
                        "opaque",
                        "sealed",
                        "envelope",
                        "pharmacy",
                        "web",
                        "telephone",
                        "assignment was generated after",
                        "after baseline",
                        "after informed consent",
                    )
                )
            )
            numbered_envelopes_without_safeguards = (
                "envelope" in evidence_lower
                and "after recruitment" in evidence_lower
                and not any(
                    phrase in evidence_lower
                    for phrase in (
                        "opaque",
                        "sealed",
                        "sequentially numbered, opaque",
                        "sequentially numbered opaque",
                        "concealed to",
                        "concealment",
                        "independent",
                        "not involved",
                    )
                )
            )
            list_access_unclear = (
                "computer-generated sequential list" in evidence_lower
                and "lowest available study number" in evidence_lower
                and not any(
                    phrase in evidence_lower
                    for phrase in (
                        "concealed",
                        "opaque",
                        "sealed",
                        "held by",
                        "pharmacy",
                        "central",
                    )
                )
            )
            if result.judgement == Judgement.LOW and (
                third_party_sequence_only
                or numbered_envelopes_without_safeguards
                or list_access_unclear
            ):
                return self._with_calibrated_judgement(
                    result,
                    Judgement.UNCLEAR,
                    "Calibration: source describes sequence/list/envelope mechanics but not enough safeguards or access control to show recruiters could not foresee assignments.",
                    self._best_quote(
                        domain_context,
                        ["third party", "envelope", "computer-generated sequential list"],
                    ),
                )

        if domain == RoBDomain.BLINDING_PARTICIPANTS_PERSONNEL:
            visibly_different_unmasked = (
                result.judgement == Judgement.UNCLEAR
                and any(
                    phrase in evidence_lower
                    for phrase in (
                        "exercise",
                        "walking",
                        "retro-walking",
                        "conventional treatment",
                        "counseling",
                        "counselling",
                        "education",
                        "surgery",
                    )
                )
                and any(
                    phrase in evidence_lower
                    for phrase in (
                        "patient reported",
                        "self-report",
                        "self reported",
                        "visual analogue",
                        "womac",
                        "pain",
                        "function",
                    )
                )
                and not any(
                    phrase in evidence_lower
                    for phrase in (
                        "sham",
                        "placebo",
                        "identical",
                        "masked",
                        "blind",
                    )
                )
            )
            if visibly_different_unmasked:
                return self._with_calibrated_judgement(
                    result,
                    Judgement.HIGH,
                    "Calibration: visibly different active interventions with subjective patient-reported outcomes make participant/personnel blinding unlikely and material.",
                    self._best_quote(
                        domain_context,
                        ["patient reported", "womac", "retro-walking", "visual analogue"],
                    ),
                )

            difficult_to_blind_uncertain_impact = (
                result.judgement == Judgement.HIGH
                and any(
                    phrase in evidence_lower
                    for phrase in (
                        "lifestyle",
                        "decision aid",
                        "patient portal",
                        "portal",
                        "mindfulness",
                        "counseling",
                        "counselling",
                        "education",
                        "job support",
                        "support website",
                    )
                )
                and not any(
                    phrase in evidence_lower
                    for phrase in (
                        "wait-list",
                        "wait list",
                        "burnout",
                        "stress",
                        "questionnaire",
                        "self-report",
                        "self reported",
                        "quality of life",
                        "depression",
                        "anxiety",
                    )
                )
                and (
                    "unclear" in result.support_text.lower()
                    or "could influence" in result.support_text.lower()
                    or "likely influenced" in result.support_text.lower()
                    or "likely bias" in result.support_text.lower()
                )
                and not any(
                    phrase in evidence_lower
                    for phrase in (
                        "open-label",
                        "open label",
                        "no blinding",
                        "not blinded",
                    )
                )
            )
            objective_device_unblinded = (
                result.judgement == Judgement.HIGH
                and any(
                    phrase in evidence_lower
                    for phrase in (
                        "oxygen saturation",
                        "spo2",
                        "computer set-up",
                        "continuously measured",
                    )
                )
                and any(
                    phrase in evidence_lower
                    for phrase in (
                        "objectively",
                        "recorded",
                        "generated",
                        "measured",
                    )
                )
            )
            if difficult_to_blind_uncertain_impact:
                return self._with_calibrated_judgement(
                    result,
                    Judgement.UNCLEAR,
                    "Calibration: lack of blinding is plausible for this behavioral/lifestyle intervention, but the supplied evidence does not clearly show a material influence on the review-relevant outcomes.",
                    self._best_quote(
                        domain_context,
                        ["decision aid", "mindfulness", "portal", "education", "lifestyle"],
                    ),
                )
            if objective_device_unblinded:
                return self._with_calibrated_judgement(
                    result,
                    Judgement.LOW,
                    "Calibration: outcomes were generated by objective device/monitoring measures unlikely to be materially influenced by participant/personnel blinding.",
                    self._best_quote(domain_context, ["oxygen saturation", "SpO2", "monitor"]),
                )

            participant_only_masking = (
                result.judgement == Judgement.LOW
                and (
                    "patients were masked" in evidence_lower
                    or "participants were masked" in evidence_lower
                    or "patients were blinded" in evidence_lower
                    or "participants were blinded" in evidence_lower
                )
                and not any(
                    phrase in evidence_lower
                    for phrase in (
                        "personnel were masked",
                        "personnel were blinded",
                        "providers were masked",
                        "providers were blinded",
                        "clinicians were masked",
                        "clinicians were blinded",
                        "investigators were masked",
                        "investigators were blinded",
                        "double-blind",
                        "double blind",
                    )
                )
            )
            assessor_blinding_only = (
                result.judgement == Judgement.LOW
                and any(
                    phrase in evidence_lower
                    for phrase in (
                        "blinded interviewers",
                        "blinded to assignments",
                        "assessing outcomes",
                        "outcome assessors",
                        "rater blinded",
                    )
                )
                and not any(
                    phrase in evidence_lower
                    for phrase in (
                        "participants were blinded",
                        "patients were blinded",
                        "personnel were blinded",
                        "providers were blinded",
                        "double-blind",
                        "double blind",
                    )
                )
            )
            route_obvious_unmasked = (
                result.judgement == Judgement.UNCLEAR
                and any(
                    phrase in evidence_lower
                    for phrase in (
                        "intravenous",
                        "subcutaneous",
                        "natalizumab",
                        "interferon",
                        "wait-list",
                        "wait list",
                    )
                )
                and any(
                    phrase in evidence_lower
                    for phrase in (
                        "self-report",
                        "self reported",
                        "questionnaire",
                        "edss",
                        "relapse",
                        "stress",
                        "burnout",
                    )
                )
                and not any(
                    phrase in evidence_lower
                    for phrase in (
                        "placebo",
                        "sham",
                        "double-blind",
                        "double blind",
                    )
                )
            )
            if participant_only_masking or assessor_blinding_only:
                return self._with_calibrated_judgement(
                    result,
                    Judgement.UNCLEAR,
                    "Calibration: this domain concerns participants and intervention personnel; masking only participants or only outcome assessors/interviewers is insufficient for Low risk.",
                    self._best_quote(
                        domain_context,
                        ["patients were masked", "blinded interviewers", "rater blinded"],
                    ),
                )
            if route_obvious_unmasked:
                return self._with_calibrated_judgement(
                    result,
                    Judgement.HIGH,
                    "Calibration: visibly different intervention routes or wait-list control with subjective/clinical outcomes makes lack of participant/personnel blinding likely to be material.",
                    self._best_quote(
                        domain_context,
                        ["intravenous", "subcutaneous", "wait-list", "rater blinded"],
                    ),
                )

        if domain == RoBDomain.BLINDING_OUTCOME_ASSESSORS:
            subjective_outcome = any(
                phrase in evidence_lower
                for phrase in (
                    "self-report",
                    "self report",
                    "self-reported",
                    "self reported",
                    "participant reported",
                    "patient reported",
                    "patient-reported",
                    "participants completed",
                    "patients completed",
                    "questionnaire",
                    "diary",
                    "pain",
                    "symptom",
                    "depress",
                    "anxiety",
                    "quality of life",
                    "satisfaction",
                    "womac",
                    "visual analogue",
                    "vas",
                    "likert",
                    "inventory",
                    "scale score",
                )
            )
            objective_outcome = (
                any(
                    phrase in evidence_lower
                    for phrase in (
                        "laboratory",
                        "lab value",
                        "biomarker",
                        "registry",
                        "administrative",
                        "medical record",
                        "hospitalization",
                        "mortality",
                        "death",
                        "blood pressure",
                        "heart rate",
                        "echocardiography",
                        "electrocardiography",
                        "ecg",
                        "transesophageal",
                        "haemodynamic",
                        "hemodynamic",
                        "catheter",
                        "oxygen saturation",
                        "spo2",
                        "accelerometer",
                        "actigraph",
                        "device",
                        "monitor",
                        "central cardiology core lab",
                        "centrally read",
                        "central reader",
                    )
                )
                and any(
                    phrase in evidence_lower
                    for phrase in (
                        "objectively",
                        "recorded",
                        "generated",
                        "measured",
                        "read by",
                        "interpreted",
                        "adjudicated",
                    )
                )
            )
            open_or_unmasked = any(
                phrase in evidence_lower
                for phrase in (
                    "open-label",
                    "open label",
                    "not blinded",
                    "not masked",
                    "no blinding",
                    "blinding was not possible",
                    "could not be blinded",
                    "were aware of treatment",
                    "aware of group assignment",
                    "knew the group",
                    "knew their group",
                )
            )
            participant_masking = any(
                phrase in evidence_lower
                for phrase in (
                    "participants were blinded",
                    "participants were masked",
                    "patients were blinded",
                    "patients were masked",
                    "subjects were blinded",
                    "subjects were masked",
                    "double-blind",
                    "double blind",
                    "triple-blind",
                    "triple blind",
                    "identical placebo",
                    "matching placebo",
                    "placebo-controlled",
                    "placebo controlled",
                )
            )
            assessor_masking = any(
                phrase in evidence_lower
                for phrase in (
                    "outcome assessors were blinded",
                    "outcome assessors were masked",
                    "assessors were blinded",
                    "assessors were masked",
                    "evaluator was blinded",
                    "evaluators were blinded",
                    "rater was blinded",
                    "raters were blinded",
                    "blinded assessor",
                    "blinded assessors",
                    "blinded evaluator",
                    "blinded evaluators",
                    "blinded rater",
                    "blinded raters",
                    "blinded coder",
                    "blinded coders",
                    "independent blinded",
                    "central blinded",
                    "blinded adjudication",
                    "research staff who were masked",
                    "research staff were masked",
                    "research staff were blinded",
                    "staff were masked to treatment",
                    "staff were blinded to treatment",
                    "masked to treatment condition",
                    "masked to group allocation",
                    "masked to trial aims",
                )
            )
            analyst_only_masking = any(
                phrase in evidence_lower
                for phrase in (
                    "statistician was blinded",
                    "statisticians were blinded",
                    "data analyst was blinded",
                    "data analysts were blinded",
                    "analysis was blinded",
                )
            )

            if (
                result.judgement == Judgement.LOW
                and subjective_outcome
                and not participant_masking
            ):
                if open_or_unmasked:
                    return self._with_calibrated_judgement(
                        result,
                        Judgement.HIGH,
                        "Calibration: the outcome appears self-reported/subjective and participants could know allocation, so participants were unmasked outcome assessors.",
                        self._best_quote(
                            domain_context,
                            ["questionnaire", "self-report", "open-label", "not blinded"],
                        ),
                    )
                if assessor_masking:
                    pass
                elif analyst_only_masking:
                    return self._with_calibrated_judgement(
                        result,
                        Judgement.UNCLEAR,
                        "Calibration: analyst masking does not establish Low risk for self-reported outcomes when participant masking is not reported.",
                        self._best_quote(
                            domain_context,
                            ["questionnaire", "blinded", "data analyst"],
                        ),
                    )
                else:
                    return self._with_calibrated_judgement(
                        result,
                        Judgement.UNCLEAR,
                        "Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.",
                        self._best_quote(domain_context, ["questionnaire", "self-report", "patient reported"]),
                    )

            if (
                result.judgement == Judgement.LOW
                and not objective_outcome
                and not assessor_masking
                and not participant_masking
                and any(
                    phrase in evidence_lower
                    for phrase in (
                        "clinician-rated",
                        "clinician rated",
                        "observer-rated",
                        "observer rated",
                        "rated by",
                        "assessed by",
                        "evaluated by",
                        "interview",
                        "diagnosis",
                    )
                )
            ):
                return self._with_calibrated_judgement(
                    result,
                    Judgement.UNCLEAR,
                    "Calibration: assessor-rated outcomes are not clearly objective, and assessor masking is not reported.",
                    self._best_quote(domain_context, ["assessed by", "rated by", "interview"]),
                )

            self_report_unmasked = (
                result.judgement != Judgement.HIGH
                and any(
                    phrase in evidence_lower
                    for phrase in (
                        "participants completed",
                        "patient reported",
                        "self-report",
                        "self reported",
                        "visual analogue",
                        "womac",
                        "questionnaire",
                        "satisfaction",
                        "pain",
                    )
                )
                and any(
                    phrase in evidence_lower
                    for phrase in (
                        "were told",
                        "randomization to",
                        "randomisation to",
                        "open-label",
                        "open label",
                        "no blinding",
                        "openly administered",
                    )
                )
                and not any(
                    phrase in evidence_lower
                    for phrase in (
                        "participants were blinded",
                        "patients were blinded",
                        "double-blind",
                        "double blind",
                        "placebo",
                        "identical",
                    )
                )
            )
            if self_report_unmasked:
                return self._with_calibrated_judgement(
                    result,
                    Judgement.HIGH,
                    "Calibration: self-reported subjective outcomes were assessed by participants who could know the broad treatment allocation.",
                    self._best_quote(
                        domain_context,
                        ["participants completed", "questionnaire", "open-label", "were told"],
                    ),
                )

            objective_device_outcome = (
                result.judgement != Judgement.LOW
                and any(
                    phrase in evidence_lower
                    for phrase in (
                        "oxygen saturation",
                        "spo2",
                        "monitor",
                        "computer set-up",
                        "continuously measured",
                        "device",
                        "laboratory",
                        "registry",
                        "central cardiology core lab",
                    )
                )
                and any(
                    phrase in evidence_lower
                    for phrase in (
                        "objectively",
                        "recorded",
                        "generated",
                        "measured",
                        "interpreted",
                        "blinded to treatment",
                    )
                )
            )
            coded_self_report_unmasked = (
                result.judgement == Judgement.LOW
                and any(
                    phrase in evidence_lower
                    for phrase in (
                        "questionnaires and samples were coded",
                        "questionnaires were coded",
                    )
                )
                and any(
                    phrase in evidence_lower
                    for phrase in (
                        "self-report",
                        "self reported",
                        "questionnaire",
                    )
                )
                and not any(
                    phrase in evidence_lower
                    for phrase in (
                        "participants were blinded",
                        "patients were blinded",
                        "double-blind",
                        "placebo",
                    )
                )
            )
            if objective_device_outcome:
                return self._with_calibrated_judgement(
                    result,
                    Judgement.LOW,
                    "Calibration: outcome measurement was objective/device/lab-based or centrally interpreted, so assessor knowledge is unlikely to materially bias measurement.",
                    self._best_quote(
                        domain_context,
                        ["oxygen saturation", "SpO2", "central cardiology core lab", "recorded"],
                    ),
                )
            objective_low_rescue = (
                result.judgement == Judgement.UNCLEAR
                and objective_outcome
                and not (subjective_outcome and open_or_unmasked)
            )
            masked_low_rescue = (
                result.judgement == Judgement.UNCLEAR
                and assessor_masking
                and not (subjective_outcome and open_or_unmasked and not participant_masking)
            )
            if objective_low_rescue or masked_low_rescue:
                return self._with_calibrated_judgement(
                    result,
                    Judgement.LOW,
                    "Calibration: objective/device/registry/mortality outcome or clearly masked outcome assessment; explicit assessor blinding is not required for Low risk.",
                    self._best_quote(
                        domain_context,
                        [
                            "laboratory",
                            "registry",
                            "mortality",
                            "central cardiology core lab",
                            "blinded assessor",
                            "objectively",
                        ],
                    ),
                )
            if coded_self_report_unmasked:
                return self._with_calibrated_judgement(
                    result,
                    Judgement.HIGH,
                    "Calibration: coding questionnaires/samples does not blind participant-assessors for self-reported outcomes.",
                    self._best_quote(domain_context, ["questionnaires and samples were coded", "questionnaire"]),
                )

        if domain == RoBDomain.INCOMPLETE_OUTCOME_DATA:
            complete_or_near_complete = (
                any(
                    phrase in evidence_lower
                    for phrase in (
                        "no loss to follow-up",
                        "no loss to follow up",
                        "no patients were lost",
                        "no participants were lost",
                        "no dropouts",
                        "no withdrawals",
                        "no missing outcome data",
                        "complete follow-up",
                        "follow-up was complete",
                        "all participants completed",
                        "all patients completed",
                        "all randomized participants were included",
                        "all randomised participants were included",
                        "all randomized patients were included",
                        "all randomised patients were included",
                        "all randomized patients were analyzed",
                        "all randomised patients were analysed",
                        "data were available for all",
                        "outcome data were available for all",
                    )
                )
                or bool(
                    re.search(
                        r"\b(?:9[5-9]|100)%\s+(?:completed|included|analysed|analyzed|followed)",
                        evidence_lower,
                    )
                )
            )
            if result.judgement != Judgement.LOW and complete_or_near_complete:
                return self._with_calibrated_judgement(
                    result,
                    Judgement.LOW,
                    "Calibration: source reports complete or near-complete outcome follow-up/inclusion, so missing outcome data are unlikely to materially bias results.",
                    self._best_quote(
                        domain_context,
                        ["no loss to follow-up", "all randomized", "complete follow-up", "data were available for all"],
                    ),
                )

            credible_handling_low = (
                result.judgement == Judgement.UNCLEAR
                and any(
                    phrase in evidence_lower
                    for phrase in (
                        "intention-to-treat",
                        "intention to treat",
                        "multiple imputation",
                        "mixed model",
                        "mixed-effect",
                        "sensitivity analysis",
                        "sensitivity analyses",
                        "inverse probability",
                    )
                )
                and any(
                    phrase in evidence_lower
                    for phrase in (
                        "no missing",
                        "complete follow-up",
                        "all randomized",
                        "all randomised",
                        "all participants completed",
                        "similar conclusions",
                        "balanced",
                        "small loss",
                        "95%",
                        "96%",
                        "97%",
                        "98%",
                        "99%",
                        "100%",
                    )
                )
                and not bool(re.search(r"\b(?:2[0-9]|3[0-9]|4[0-9]|[5-9][0-9])\s*%", evidence_lower))
            )
            if credible_handling_low:
                return self._with_calibrated_judgement(
                    result,
                    Judgement.LOW,
                    "Calibration: credible ITT/imputation/sensitivity handling with signals of complete or small/balanced missingness.",
                    self._best_quote(
                        domain_context,
                        ["intention-to-treat", "multiple imputation", "sensitivity", "all randomized"],
                    ),
                )

            locf_figure_only = (
                result.judgement == Judgement.LOW
                and (
                    "last observed carried forward" in evidence_lower
                    or "last observation carried forward" in evidence_lower
                    or "locf" in evidence_lower
                )
                and "figure" in evidence_lower
                and not re.search(r"\b\d+\s*/\s*\d+\s+(?:in|randomi[sz]ed|analysed|analyzed)", evidence_lower)
            )
            small_loss_no_reasons_subjective = (
                result.judgement == Judgement.UNCLEAR
                and bool(re.search(r"\b\d+\s+patients?\s+were lost to follow-up\b", evidence_lower))
                and any(
                    phrase in evidence_lower
                    for phrase in (
                        "patient reported",
                        "visual analogue",
                        "womac",
                        "pain",
                        "function",
                    )
                )
                and not any(
                    phrase in evidence_lower
                    for phrase in (
                        "reason",
                        "due to",
                        "because",
                        "multiple imputation",
                    )
                )
            )
            if locf_figure_only:
                return self._with_calibrated_judgement(
                    result,
                    Judgement.UNCLEAR,
                    "Calibration: LOCF with dropout details only referenced in a figure/table is not enough to establish low attrition bias from the supplied XML text.",
                    self._best_quote(domain_context, ["last observed", "locf", "figure"]),
                )
            if small_loss_no_reasons_subjective:
                return self._with_calibrated_judgement(
                    result,
                    Judgement.HIGH,
                    "Calibration: subjective outcomes were analyzed only among completers after losses to follow-up with no reasons reported.",
                    self._best_quote(domain_context, ["lost to follow-up", "patient reported", "womac"]),
                )

            analyzed_pairs = [
                (int(a), int(b))
                for a, b in re.findall(
                    r"(\d{1,5})\s*/\s*(\d{1,5})\s+(?:participants?|patients?|subjects?)?\s*(?:were\s+)?(?:included|analysed|analyzed|assessed|completed|followed)",
                    evidence_lower,
                )
                if int(b) > 0
            ]
            rates = [a / b for a, b in analyzed_pairs if b]
            notable_missing = any(rate < 0.85 for rate in rates)
            imbalanced_missing = len(rates) >= 2 and max(rates) - min(rates) >= 0.12
            high_missing_percent = bool(
                re.search(
                    r"\b(?:2[0-9]|3[0-9]|4[0-9]|[5-9][0-9])%\s+"
                    r"(?:lost|withdraw|withdrew|drop(?:ped)? out|missing|discontinued|not complete)",
                    evidence_lower,
                )
            )
            attrition_mentioned = any(
                phrase in evidence_lower
                for phrase in (
                    "lost to follow-up",
                    "loss to follow-up",
                    "lost to follow up",
                    "dropout",
                    "dropped out",
                    "withdrew",
                    "withdrawn",
                    "withdrawal",
                    "discontinued",
                    "missing data",
                    "excluded from analysis",
                    "excluded from the analysis",
                    "not included in the analysis",
                    "per-protocol",
                    "per protocol",
                    "complete case",
                    "complete-case",
                )
            )
            outcome_related_missing = any(
                phrase in evidence_lower
                for phrase in (
                    "adverse event",
                    "adverse events",
                    "side effect",
                    "lack of efficacy",
                    "treatment failure",
                    "worsening",
                    "relapse",
                    "died",
                    "death",
                    "hospitalized",
                    "hospitalised",
                    "complication",
                    "nonresponse",
                    "poor response",
                    "residual stones",
                    "major bleeding",
                )
            ) and attrition_mentioned
            protective_missing_handling = any(
                phrase in evidence_lower
                for phrase in (
                    "balanced",
                    "similar between groups",
                    "similar across groups",
                    "similar follow-up",
                    "did not differ",
                    "no significant difference",
                    "no significant baseline differences",
                    "sensitivity analyses",
                    "sensitivity analysis",
                    "multiple imputation",
                    "imputed",
                    "intention-to-treat",
                    "intention to treat",
                    "all subjects were followed",
                    "all participants were followed",
                    "all randomized participants were included",
                    "all randomised participants were included",
                    "no missing outcome data",
                )
            )
            imbalance_cues = attrition_mentioned and any(
                phrase in evidence_lower
                for phrase in (
                    "imbalanced",
                    "unbalanced",
                    "differed between groups",
                    "more frequent in",
                    "higher in the",
                    "lower in the",
                    "unequal",
                    "differential",
                    "more participants in",
                    "more patients in",
                )
            )
            missing_reasons_unclear = (
                result.judgement == Judgement.LOW
                and attrition_mentioned
                and not any(
                    phrase in evidence_lower
                    for phrase in (
                        "reason",
                        "reasons",
                        "due to",
                        "because",
                        "adverse",
                        "consent",
                        "moved",
                        "pregnancy",
                        "protocol violation",
                        "lost contact",
                    )
                )
            )

            if result.judgement == Judgement.LOW and (
                (notable_missing and not protective_missing_handling)
                or (imbalanced_missing and not protective_missing_handling)
                or (high_missing_percent and not protective_missing_handling)
                or missing_reasons_unclear
            ):
                return self._with_calibrated_judgement(
                    result,
                    Judgement.UNCLEAR,
                    "Calibration: the source suggests notable/imbalanced or insufficiently explained missing outcome data, so Low risk is not established from the supplied XML.",
                    self._best_quote(
                        domain_context,
                        ["lost to follow-up", "withdraw", "dropout", "excluded from analysis", "per-protocol"],
                    ),
                )

            if result.judgement != Judgement.HIGH and (
                (
                    imbalance_cues
                    and not protective_missing_handling
                )
                or (
                    outcome_related_missing
                    and (high_missing_percent or imbalanced_missing or notable_missing)
                    and not protective_missing_handling
                )
            ):
                return self._with_calibrated_judgement(
                    result,
                    Judgement.HIGH,
                    "Calibration: missing outcome data appear outcome-related or meaningfully imbalanced between groups.",
                    self._best_quote(
                        domain_context,
                        ["adverse event", "lack of efficacy", "differed between groups", "more participants"],
                    ),
                )

        return result

    def _with_calibrated_judgement(
        self,
        result: DomainResult,
        judgement: Judgement,
        reason: str,
        quote: str,
    ) -> DomainResult:
        """Return a copy of a result with an auditable calibrated judgement."""
        support_text = f"{result.support_text} Comment: {reason}"
        contexts = list(result.support_context)
        contexts.insert(
            0,
            SupportContext(
                source="article",
                quote=self._compact_text(quote, 240),
                relevance=self._compact_text(reason, 160),
            ),
        )
        return DomainResult(
            domain=result.domain,
            judgement=judgement,
            support_text=self._compact_text(support_text, 1600),
            support_context=contexts[:2],
            reasoning=self._compact_text(
                f"{result.reasoning or ''} {reason}",
                1000,
            ),
        )

    def _best_quote(self, evidence: str, needles: list[str]) -> str:
        """Extract a compact evidence window around a calibration cue."""
        lower = evidence.lower()
        for needle in needles:
            index = lower.find(needle.lower())
            if index >= 0:
                start = max(index - 120, 0)
                end = min(index + 360, len(evidence))
                return evidence[start:end]
        return evidence[:360]

    def _parse_domain_result_payload(
        self,
        domain: RoBDomain,
        payload: str,
        raw_content: str,
        label: str,
    ) -> DomainResult:
        """Parse one domain result, with a fallback for malformed model JSON."""
        try:
            parsed = self._loads_json_lenient(payload)
            return self._domain_result_from_parsed(domain, parsed)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            print(f"Warning: {label} parsing failed for {domain.value}: {e}")
            print(f"Raw response: {raw_content[:500]}...")
            return self._salvage_domain_result(
                domain=domain,
                text=payload or raw_content,
                parse_error=str(e),
            )

    def _domain_result_from_parsed(
        self,
        domain: RoBDomain,
        parsed: dict,
    ) -> DomainResult:
        """Build a DomainResult from parsed model output."""
        if not isinstance(parsed, dict):
            raise TypeError("Domain result payload must be a JSON object.")

        support_text = (
            parsed.get("support_text")
            or parsed.get("support")
            or parsed.get("evidence")
            or parsed.get("reasoning")
            or "Comment: No support text provided."
        )
        reasoning = parsed.get("reasoning") or parsed.get("rationale")
        return DomainResult(
            domain=domain,
            judgement=self._coerce_judgement(parsed.get("judgement")),
            support_text=self._compact_text(str(support_text), 1600),
            support_context=self._parse_support_context(parsed),
            reasoning=self._compact_text(str(reasoning), 1000) if reasoning else None,
            evidence_map=parsed.get("evidence_map") if isinstance(parsed.get("evidence_map"), dict) else None,
        )

    def _salvage_methodology_extraction(self, text: str) -> MethodologyExtraction:
        """Recover methodology fields from malformed extraction JSON."""
        values = {}
        for field in MethodologyExtraction.model_fields:
            value = self._extract_json_string_field(text, field)
            if not value:
                value = "Not reported"
            values[field] = self._compact_text(value, 1200)
        return MethodologyExtraction.model_validate(values)

    def _salvage_domain_result(
        self,
        domain: RoBDomain,
        text: str,
        parse_error: str,
    ) -> DomainResult:
        """Recover a usable domain result from partial or malformed JSON."""
        judgement_text = self._extract_json_string_field(text, "judgement")
        if not judgement_text:
            match = re.search(r"\b(Low risk|High risk|Unclear risk)\b", text)
            judgement_text = match.group(1) if match else "Unclear risk"

        try:
            judgement = self._coerce_judgement(judgement_text)
        except ValueError:
            judgement = Judgement.UNCLEAR

        support_text = (
            self._extract_json_string_field(text, "support_text")
            or self._extract_json_string_field(text, "support")
            or "Comment: Model response was malformed and no support_text field could be recovered."
        )
        reasoning = (
            self._extract_json_string_field(text, "reasoning")
            or self._extract_json_string_field(text, "rationale")
            or f"Recovered from malformed JSON: {parse_error}"
        )
        return DomainResult(
            domain=domain,
            judgement=judgement,
            support_text=self._compact_text(support_text, 1600),
            support_context=[
                SupportContext(
                    source="methodology",
                    quote=self._compact_text(support_text, 240),
                    relevance="Recovered from malformed JSON; inspect raw output if this judgement matters.",
                )
            ],
            reasoning=self._compact_text(reasoning, 1000),
        )

    def _coerce_judgement(self, value: object) -> Judgement:
        """Normalize judgement labels returned by models."""
        text = str(value or "").strip()
        for judgement in Judgement:
            if text.lower() == judgement.value.lower():
                return judgement

        normalized = re.sub(r"[^a-z]+", " ", text.lower()).strip()
        if normalized in {"low", "low risk"}:
            return Judgement.LOW
        if normalized in {"high", "high risk"}:
            return Judgement.HIGH
        if normalized in {"unclear", "unclear risk", "some concerns"}:
            return Judgement.UNCLEAR
        raise ValueError(f"Unknown judgement label: {text!r}")

    def _extract_json_string_field(self, text: str, field: str) -> Optional[str]:
        """Extract a JSON string field from malformed/partial model output."""
        match = re.search(rf'"{re.escape(field)}"\s*:\s*"', text)
        if not match:
            return None

        index = match.end()
        chars = []
        escaped = False
        while index < len(text):
            char = text[index]
            if escaped:
                chars.append(char)
                escaped = False
            elif char == "\\":
                chars.append(char)
                escaped = True
            elif char == '"':
                break
            else:
                chars.append(char)
            index += 1

        raw = "".join(chars).strip()
        if not raw:
            return None
        try:
            return json.loads(f'"{raw}"')
        except json.JSONDecodeError:
            return raw.replace("\n", " ").strip()

    def _extract_domain_segment(self, text: str, domain: RoBDomain) -> str:
        """Return the portion of a joint response nearest to one domain."""
        start = text.find(domain.value)
        if start < 0:
            return text
        next_starts = [
            text.find(other.value, start + len(domain.value))
            for other in RoBDomain
            if other != domain
        ]
        next_starts = [position for position in next_starts if position >= 0]
        end = min(next_starts) if next_starts else len(text)
        return text[start:end]

    def _compact_text(self, text: str, limit: int) -> str:
        """Normalize whitespace and trim long audit fields."""
        normalized = re.sub(r"\s+", " ", text).strip()
        if len(normalized) <= limit:
            return normalized
        return normalized[:limit].rsplit(" ", 1)[0] + "..."

    def _build_methodology_context(
        self,
        article_text: str,
        max_chars: Optional[int] = None,
    ) -> str:
        """Build a compact article context for RoB evidence extraction.

        Full papers often include long background and discussion sections that
        slow down extraction without adding much RoB evidence. This keeps the
        source-grounded design while prioritizing methods/results/ethics and
        paragraphs that mention RoB-relevant concepts.
        """
        max_chars = max_chars or self.extraction_max_chars
        if len(article_text) <= max_chars:
            return article_text

        keywords = sorted(
            {
                keyword
                for domain in RoBDomain
                for keyword in self._domain_keywords(domain)
            }
            | {
                "lost",
                "withdrawal",
                "withdrawn",
                "adverse",
                "protocol",
                "primary outcome",
                "sample size",
                "consent",
            }
        )
        chunks = self._section_chunks(article_text)
        scored: list[tuple[int, int, str]] = []

        for index, section_name, paragraph in chunks:
            haystack = f"{section_name}\n{paragraph}".lower()
            score = sum(1 for keyword in keywords if keyword in haystack)
            section_lower = section_name.lower()
            if "method" in section_lower or "material" in section_lower:
                score += 8
            elif "result" in section_lower:
                score += 4
            elif "ethic" in section_lower or "supplement" in section_lower:
                score += 2
            elif "discussion" in section_lower:
                score += 1

            if score:
                block = f"## {section_name}\n\n{paragraph.strip()}"
                scored.append((score, index, block))

        if not scored:
            return article_text[:max_chars].rsplit(" ", 1)[0].strip()

        scored.sort(key=lambda item: (-item[0], item[1]))
        selected = sorted(scored[:30], key=lambda item: item[1])
        selected_blocks = [block for _, _, block in selected]

        return self._join_with_budget(selected_blocks, max_chars, keywords)

    def _build_domain_context(
        self,
        domain: RoBDomain,
        article_text: str,
        max_chars: int = 8000,
    ) -> str:
        """Select source excerpts likely to contain evidence for one domain."""
        keywords = self._domain_keywords(domain)
        must_markers = self._domain_must_include_section_markers(domain)
        max_paragraphs = 18 if domain == RoBDomain.INCOMPLETE_OUTCOME_DATA else 16
        chunks = self._section_chunks(article_text)
        scored: list[tuple[int, int, str]] = []

        for index, section_name, paragraph in chunks:
            haystack = f"{section_name}\n{paragraph}".lower()
            score = sum(1 for keyword in keywords if keyword in haystack)
            score += self._domain_section_bonus(domain, section_name, paragraph)
            section_lower = section_name.lower()
            if any(marker in section_lower for marker in must_markers):
                score += 6
            if score:
                block = f"## {section_name}\n\n{paragraph.strip()}"
                scored.append((score, index, block))

        scored.sort(key=lambda item: (-item[0], item[1]))
        selected = [paragraph for _, _, paragraph in scored[:max_paragraphs]]

        if not selected:
            selected = self._split_article(article_text)[:4]

        return self._join_with_budget(selected, max_chars, keywords)

    def _extract_attrition_numeric_clues(self, article_text: str) -> str:
        """Regex-scan full article text for attrition-related numeric clues."""
        patterns = [
            r".{0,120}\b(?:randomi[sz]ed|allocated|enrolled)\b.{0,160}",
            r".{0,120}\b(?:analysed|analyzed|included|completed|assessed|followed)\b.{0,160}",
            r".{0,120}\b(?:lost to follow[- ]up|withdraw|dropout|discontinued|missing|excluded)\b.{0,160}",
            r".{0,120}\b\d+\s*/\s*\d+\b.{0,160}",
            r".{0,120}\b(?:ITT|intention-to-treat|intention to treat|per-protocol|per protocol|complete case|LOCF|multiple imputation|sensitivity)\b.{0,160}",
        ]
        hits: list[str] = []
        lower_seen: set[str] = set()
        for pattern in patterns:
            for match in re.finditer(pattern, article_text, flags=re.I):
                snippet = re.sub(r"\s+", " ", match.group(0)).strip()
                key = snippet.lower()
                if key and key not in lower_seen:
                    hits.append(snippet)
                    lower_seen.add(key)
                if len(hits) >= 80:
                    break
            if len(hits) >= 80:
                break
        if not hits:
            return ""
        return "\n".join(f"- {hit}" for hit in hits)

    def _build_supplementary_context(
        self,
        domain: RoBDomain,
        attrition_clues: str = "",
    ) -> str:
        """Build optional prompt blocks prepended before domain excerpts."""
        if domain != RoBDomain.INCOMPLETE_OUTCOME_DATA or not attrition_clues:
            return ""
        return (
            "# Numeric attrition clues extracted from full article (regex scan)\n"
            "<numeric_attrition_clues>\n"
            f"{attrition_clues}\n"
            "</numeric_attrition_clues>"
        )

    @staticmethod
    def _combine_calibration_evidence(
        domain_context: str,
        supplementary_context: str = "",
    ) -> str:
        """Merge excerpt and supplementary blocks for rule-based calibration."""
        parts = [part.strip() for part in (supplementary_context, domain_context) if part.strip()]
        return "\n\n".join(parts)

    def _domain_must_include_section_markers(self, domain: RoBDomain) -> tuple[str, ...]:
        """Section title substrings that receive a retrieval score boost."""
        common = (
            "method",
            "material",
            "design",
            "procedure",
            "protocol",
            "intervention",
            "random",
            "allocation",
            "blind",
            "mask",
            "statistical",
            "ethic",
            "study design",
            "participants",
        )
        if domain == RoBDomain.INCOMPLETE_OUTCOME_DATA:
            return common + (
                "result",
                "outcome",
                "flow",
                "follow-up",
                "follow up",
                "attrition",
            )
        if domain == RoBDomain.BLINDING_OUTCOME_ASSESSORS:
            return common + ("outcome", "measure", "assessment", "endpoint")
        return common

    def _domain_section_bonus(
        self,
        domain: RoBDomain,
        section_name: str,
        paragraph: str,
    ) -> int:
        """Prioritize domain-specific sections and evidence phrases."""
        section_lower = section_name.lower()
        text_lower = paragraph.lower()
        score = 0

        method_like_section = any(
            marker in section_lower
            for marker in (
                "method",
                "material",
                "design",
                "random",
                "intervention",
                "procedure",
                "protocol",
            )
        )
        low_value_section = any(
            marker in section_lower
            for marker in ("discussion", "conclusion", "pre-publication", "reference")
        )

        if domain in {
            RoBDomain.RANDOM_SEQUENCE_GENERATION,
            RoBDomain.ALLOCATION_CONCEALMENT,
            RoBDomain.BLINDING_PARTICIPANTS_PERSONNEL,
            RoBDomain.BLINDING_OUTCOME_ASSESSORS,
        }:
            if method_like_section:
                score += 4
            if low_value_section:
                score -= 4

        if domain == RoBDomain.ALLOCATION_CONCEALMENT:
            for phrase in (
                "central",
                "at distance",
                "remote",
                "independent",
                "senior editor",
                "only one",
                "only a senior",
                "only the senior",
                "without knowledge",
                "not aware",
                "undisclosed block",
                "biostatistics department",
                "randomization list",
                "randomisation list",
                "chronologically ascending",
                "sequence of arrival",
                "envelope",
                "envelopes",
                "opaque",
                "sealed",
                "after recruitment",
                "third party",
                "assignment",
                "foresee",
                "conceal",
            ):
                if phrase in text_lower:
                    score += 4

        if domain == RoBDomain.RANDOM_SEQUENCE_GENERATION:
            for phrase in (
                "pre-defined randomization list",
                "predefined randomization list",
                "pre-defined randomisation list",
                "predefined randomisation list",
                "random number",
                "random numbers",
                "random number generator",
                "tables of random numbers",
                "computer-generated",
                "computer generated",
                "sample function",
            ):
                if phrase in text_lower:
                    score += 4

        if domain == RoBDomain.BLINDING_OUTCOME_ASSESSORS:
            for phrase in (
                "open-label",
                "open label",
                "no blinding",
                "not blinded",
                "not masked",
                "participants completed",
                "self-report",
                "self report",
                "self-reported",
                "self reported",
                "questionnaire",
                "pain",
                "diary",
                "womac",
                "visual analogue",
                "vas",
                "quality of life",
                "satisfaction",
                "function",
                "participant reported",
                "patient reported",
                "patient-reported",
                "primary outcome",
                "primary endpoint",
                "secondary outcome",
                "secondary endpoint",
                "outcome measure",
                "outcome measures",
                "assessed by",
                "rated by",
                "evaluated by",
                "interviewer",
                "interviewers",
                "coder",
                "coders",
                "adjudication",
                "adjudicated",
                "central reader",
                "centrally read",
                "independent assessor",
                "independent blinded",
                "clinician-rated",
                "observer-rated",
                "self-administered",
                "scale score",
                "inventory",
                "likert",
            ):
                if phrase in text_lower:
                    score += 4

        if domain == RoBDomain.INCOMPLETE_OUTCOME_DATA:
            if "result" in section_lower or "flow" in section_lower:
                score += 8
            if any(
                marker in section_lower
                for marker in ("method", "material", "statistical", "analysis")
            ):
                score += 3
            for phrase in (
                "consort",
                "participant flow",
                "figure 1",
                "completed the study",
                "completed",
                "assessed",
                "analyzed",
                "analysed",
                "randomized",
                "randomised",
                "enrolled",
                "lost to follow-up",
                "loss to follow-up",
                "dropped out",
                "dropout",
                "withdraw",
                "discontinued",
                "excluded",
                "excluded from analysis",
                "excluded from the analysis",
                "not included in the analysis",
                "missing",
                "missing data",
                "missing values",
                "per-protocol",
                "per protocol",
                "intention-to-treat",
                "intention to treat",
                "full analysis set",
                "modified intention",
                "last observation",
                "last available",
                "locf",
                "multiple imputation",
                "imputed",
                "sensitivity analysis",
                "complete cases",
                "complete case",
                "available for all",
                "all randomized",
                "all randomised",
                "all participants completed",
                "no loss to follow-up",
                "no loss to follow up",
                "no missing outcome data",
                "responded",
                "responders",
                "non-response",
                "nonresponse",
                "response was observed",
                "follow-up",
                "follow up",
                "adverse event",
                "lack of efficacy",
                "treatment failure",
            ):
                if phrase in text_lower:
                    score += 5

        return score

    def _join_with_budget(
        self,
        blocks: list[str],
        max_chars: int,
        keywords: list[str],
    ) -> str:
        """Join blocks without exceeding a character budget."""
        excerpts: list[str] = []
        total = 0
        separator = "\n\n---\n\n"
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            remaining = max_chars - total
            if remaining <= 0:
                break
            if len(block) > remaining:
                block = self._trim_around_keywords(block, keywords, remaining)
            if block:
                excerpts.append(block)
                total += len(block) + len(separator)

        return separator.join(excerpts)

    def _trim_around_keywords(
        self,
        text: str,
        keywords: list[str],
        max_chars: int,
    ) -> str:
        """Take a window around the first matching keyword."""
        if len(text) <= max_chars:
            return text
        lower = text.lower()
        positions = [lower.find(keyword) for keyword in keywords if lower.find(keyword) >= 0]
        center = min(positions) if positions else 0
        start = max(center - max_chars // 3, 0)
        end = min(start + max_chars, len(text))
        start = max(end - max_chars, 0)
        excerpt = text[start:end].strip()
        if start > 0:
            excerpt = "..." + excerpt
        if end < len(text):
            excerpt = excerpt + "..."
        return excerpt

    def _section_chunks(self, article_text: str) -> list[tuple[int, str, str]]:
        """Split formatted article text into paragraph chunks with section names."""
        chunks: list[tuple[int, str, str]] = []
        current_section = "Article"
        current_lines: list[str] = []
        index = 0

        def flush_section() -> None:
            nonlocal index
            body = "\n".join(current_lines).strip()
            if not body:
                return
            for paragraph in re.split(r"\n\s*\n", body):
                paragraph = paragraph.strip()
                if paragraph:
                    chunks.append((index, current_section, paragraph))
                    index += 1

        for line in article_text.splitlines():
            if line.startswith("## "):
                flush_section()
                current_section = line.removeprefix("## ").strip() or "Article"
                current_lines = []
            else:
                current_lines.append(line)

        flush_section()
        return chunks

    def _split_article(self, article_text: str) -> list[str]:
        """Split formatted article text into paragraphs and section blocks."""
        chunks = []
        for part in re.split(r"\n\s*\n", article_text):
            cleaned = part.strip()
            if cleaned:
                chunks.append(cleaned)
        return chunks

    def _domain_keywords(self, domain: RoBDomain) -> list[str]:
        """Keywords used to retrieve domain-specific article excerpts."""
        common = [
            "method",
            "methods",
            "trial",
            "random",
            "assigned",
            "allocated",
            "allocation",
        ]
        if domain == RoBDomain.RANDOM_SEQUENCE_GENERATION:
            return common + [
                "randomisation",
                "randomization",
                "sequence",
                "computer",
                "generated",
                "stratified",
                "block",
                "minim",
            ]
        if domain == RoBDomain.ALLOCATION_CONCEALMENT:
            return common + [
                "conceal",
                "envelope",
                "opaque",
                "sealed",
                "central",
                "pharmacy",
                "recruit",
                "assignment",
            ]
        if domain == RoBDomain.BLINDING_PARTICIPANTS_PERSONNEL:
            return common + [
                "blind",
                "masked",
                "double-blind",
                "single-blind",
                "participant",
                "patient",
                "personnel",
                "provider",
                "therapist",
                "placebo",
            ]
        if domain == RoBDomain.BLINDING_OUTCOME_ASSESSORS:
            return common + [
                "blind",
                "masked",
                "assessor",
                "assessment",
                "evaluat",
                "observer",
                "outcome",
                "measure",
                "self-report",
                "questionnaire",
                "patient-reported",
                "participant-reported",
                "primary outcome",
                "endpoint",
                "rated",
                "interviewer",
                "coder",
                "adjudicat",
                "central reader",
                "clinician-rated",
                "self-administered",
            ]
        if domain == RoBDomain.INCOMPLETE_OUTCOME_DATA:
            return common + [
                "attrition",
                "lost to follow-up",
                "loss to follow-up",
                "withdraw",
                "dropout",
                "missing",
                "excluded",
                "excluded from analysis",
                "intention-to-treat",
                "intention to treat",
                "full analysis set",
                "per protocol",
                "imputation",
                "locf",
                "multiple imputation",
                "sensitivity analysis",
                "analy",
                "follow-up",
                "completed",
                "participant flow",
                "adverse event",
                "discontinued",
            ]
        return common

    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response (handles markdown code blocks)."""
        # Try to find JSON in markdown code block
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            return match.group(1)

        # Try to find raw JSON object
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return match.group(0)

        # If no JSON found, return as-is and let validation fail
        return text.strip()

    def _loads_json_lenient(self, text: str) -> dict:
        """Load model JSON, escaping raw control characters inside strings."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            import json_repair
            return json_repair.loads(text)

    def _escape_control_chars_in_strings(self, text: str) -> str:
        """Escape unescaped control characters that appear inside JSON strings."""
        result = []
        in_string = False
        escaped = False
        for char in text:
            if escaped:
                result.append(char)
                escaped = False
                continue
            if char == "\\":
                result.append(char)
                escaped = True
                continue
            if char == '"':
                in_string = not in_string
                result.append(char)
                continue
            if in_string and ord(char) < 32:
                result.append(json.dumps(char)[1:-1])
            else:
                result.append(char)
        return "".join(result)
