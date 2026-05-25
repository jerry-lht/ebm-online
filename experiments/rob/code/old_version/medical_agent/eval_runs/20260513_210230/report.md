# Batch Risk of Bias Eval Report

This report contains an audit trace: explicit extracted evidence, model-provided rationales, and label comparisons. It does not include hidden chain-of-thought.

- Studies: 2
- Domains: 10
- Accuracy: 5/10 (50.0%)
- Article-observable accuracy: 3/4 (75.0%)
- External/review-context GT domains: 0
- Unknown or non-text GT domains: 1

## Summary

| PMID | Study | Correct | Accuracy | Seconds |
|---|---|---:|---:|---:|
| 14647140 | Clayton 2007 | 1/5 | 20.0% | 47.83 |
| 15249261 | Ross 2004 | 4/5 | 80.0% | 54.63 |

## Error Types

- gt_support_not_found_in_article_text: 3
- attrition_balance_or_missing_data_handling: 1
- figure_table_or_supplement_needed: 1

## 14647140 - Clayton 2007

- Mode: hybrid
- Review context: none (0 chars)
- Article chars: 24130
- Extraction context chars: 12005
- Total seconds: 47.83

### Methodology Extraction

- `randomization_method`: Not reported
- `allocation_concealment_method`: Not reported
- `blinding_participants`: Not reported
- `blinding_personnel`: Not reported
- `blinding_outcome_assessors`: Not reported
- `attrition_details`: Of the 23 participants, 20 completed their post consultation questionnaires, the remaining three became acutely unwell but gave verbal feedback to the research nurse following the consultation. In all, 11 patients completed the 3-week follow-up questionnaires (five patients were too unwell, four died, two did not respond to a reminder and one patient's carer requested no further involvement).
- `study_design`: Insufficient information
- `additional_notes`: Participants: 23 patients in pilot study; earlier qualitative work involved 19 patients and 24 carers. Outcomes collected: questionnaires pre-consultation, post-consultation, and 3-week follow-up including Spielberger State Anxiety Inventory; clinicians completed questionnaires. No explicit statements about randomisation, allocation, or blinding are reported in the provided text.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Unclear risk | Low risk | no | figure_table_or_supplement_reference | figure_table_or_supplement_needed |
| Allocation concealment | Unclear risk | Low risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |
| Blinding of participants and personnel: All outcomes | Unclear risk | Unclear risk | yes | article_absence_or_unclear |  |
| Blinding of outcome assessment: All outcomes | Unclear risk | Low risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |
| Incomplete outcome data: All outcomes | High risk | Low risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |

### Audit Details

#### Random sequence generation

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: figure_table_or_supplement_reference (article observable: None)
- GT support phrase hits: 
- Model rationale: No description of a random component (computer/random number table/coin toss/etc.) is provided and the report explicitly lacks randomization details, so there is insufficient information to judge risk of bias for sequence generation.
- Model support: Comment: The report provides no information about how the allocation sequence was generated; randomization method is not reported, so adequacy of sequence generation cannot be judged.
- Model support context: [{"source": "methodology", "quote": "randomization_method: \"Not reported\"", "relevance": "Explicit statement that the study report did not describe sequence generation."}, {"source": "article", "quote": "Whether this was a result of seeing the doctor or the use of the QPL is unclear from the design of the study", "relevance": "Indicates design limitations and lack of detail about allocation/randomisation in the article."}]
- GT support: Individually randomised and stratified by physician – random permuted blocks of 10 constructed using random number table (by research assistant not involved in recruitment)
- Evidence row: {}
- Source context preview: ## Data collection and analysis The focus groups and telephone interviews were audiotaped and fully transcribed. Data analysis was informed by qualitative methodology (Pope and Mays, 2000). Individual questions or information needs were identified from the transcripts using the participants' own language where possible. These were discussed by both facilitators to ensure consistency of interpretation and were organised into categories to facilitate comprehension, as suggested by Ley (1988). Further focus groups and/or telephone interviews were conducted until no additional topics were raised. A draft QPL was developed using the categories and questions identified in the transcripts. The...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report provides no description of how allocations were concealed (or whether randomisation occurred), so there is insufficient information to determine if recruiters could foresee assignments; per Cochrane guidance this warrants 'Unclear risk'.
- Model support: Comment: No information about randomisation or allocation concealment is reported in the article excerpts or extracted methods; insufficient detail to judge whether assignments could be foreseen.
- Model support context: [{"source": "methodology", "quote": "allocation_concealment_method: \"Not reported\"", "relevance": "Explicit statement that concealment method was not reported, indicating missing information for judgment."}, {"source": "article", "quote": "No explicit statements about randomisation, allocation, or blinding are reported in the provided text.", "relevance": "Confirms article excerpts lack details on allocation procedures relevant to concealment."}]
- GT support: Allocations were concealed using sequentially numbered opaque sealed envelopes
- Evidence row: {}
- Source context preview: ## Results of focus groups and individual interviews General questions included how and when to contact the PC team, and the connection between the PC team and other health professionals involved in the patients' care. In addition, some patients wanted advice about how to choose another doctor. A second opinion was valued regarding disease-specific treatment from an independent source. Others wanted to discuss the option of stopping anticancer treatment or not starting it at all. --- ## Results of pilot study Patients' views about the QPL are outlined in Table 2Table 2Patient and carer feedback about QPL from pilot study Post consultation questionnaire refers to consultation immediately...

#### Blinding of participants and personnel: All outcomes

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: Because blinding of participants and personnel is not reported and the primary outcomes are self-reported and therefore potentially influenced by knowledge of allocation, there is insufficient information to judge risk; this warrants an 'Unclear risk' judgment.
- Model support: Comment: The report does not state whether participants or personnel were blinded. Outcomes included patient self-report questionnaires (anxiety, post-consultation and 3-week follow-up) which could be influenced by knowledge of allocation, but no information is provided about masking or use of placebo/attention control.
- Model support context: [{"source": "methodology", "quote": "blinding_participants: \"Not reported\"; blinding_personnel: \"Not reported\"; blinding_outcome_assessors: \"Not reported\"", "relevance": "Directly indicates absence of reported information about blinding."}, {"source": "article", "quote": "Outcomes collected: questionnaires pre-consultation, post-consultation, and 3-week follow-up including Spielberger State Anxiety Inventory; clinicians completed questionnaires.", "relevance": "Shows outcomes were patient self-report measures susceptible to performance bias if unblinded."}]
- GT support: Physicians were unblinded; authors note that prior research has indicated that QPL require professional endorsement in consultations to be effective Unclear whether or not patients and carers were blinded to intervention and/or what effect this may have had on the outcomes
- Evidence row: {}
- Source context preview: ## Participants Three groups felt to have important input were sampled: (a) PC patients, (b) carers of PC patients, and (c) health professionals working in PC. Patients and carers were eligible to take part if they were: (1) over 18 years of age, (2) English speaking, (3) well enough to participate, (4) able to give informed consent, and (5) referred to a specialist PC service and diagnosed with an incurable and progressive illness, or the carer of such a patient. In all, 19 patients and 24 carers were recruited from hospitals, PC units and the community in three PC services in Sydney. Their demographic characteristics are shown in Table 1Table 1Demographic and disease characteristics of...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: Because the paper does not report whether outcome assessment was blinded and outcomes are largely self-reported (susceptible to bias), there is insufficient information to judge low or high risk; thus risk is unclear.
- Model support: Comment: The report does not state whether outcome assessors were blinded. Outcomes include self-reported questionnaires (anxiety, responses to QPL) and clinician questionnaires, which could be influenced by knowledge of allocation, but blinding status is not reported.
- Model support context: [{"source": "methodology", "quote": "Comment: The report does not state whether outcome assessors were blinded. Outcomes include self-reported questionnaires (anxiety, responses to QPL) and clinician questionnaires, which could be influenced by knowledge of allocation, but...", "relevance": "Recovered from malformed JSON; inspect raw output if this judgement matters."}]
- GT support: Authors indicate that consultations were audiotaped, transcribed and analysed by blinded coders "Two coders were trained and blinded to group allocation. One coder coded all transcripts and recoded a random 10% to determine intrarater reliability. The second coder coded a random 10% of transcripts to determine inter‐rater reliability" (page 716)
- Evidence row: {}
- Source context preview: ## Data collection and analysis Prior to the consultation, patients completed a questionnaire regarding their information and involvement (decisional control) preferences, and anxiety levels. General preferences for information were assessed using a question from the Cassileth Information Styles Questionnaire measuring the type of information preferred (Cassileth et al, 1980). Preferences for decisional control were assessed using a validated and reliable question from previous studies in cancer patients (Sutherland et al, 1989; Degner et al, 1997b). Patients were classified as wanting an ‘active’, ‘passive’ or ‘collaborative’ role when making decisions about treatment. Patient anxiety was...

#### Incomplete outcome data: All outcomes

- Prediction: High risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: Twelve of 23 participants (≈52%) had missing 3-week outcomes with reasons directly related to health status (too unwell, died), which are likely related to true outcomes and can induce substantial bias; no appropriate methods to address missing data were reported.
- Model support: Quote: "Of the 23 participants, 20 completed their post consultation questionnaires, the remaining three became acutely unwell but gave verbal feedback to the research nurse following the consultation. In all, 11 patients completed the 3-week follow-up questionnaires (five patients were too unwell, four died, two did not respond to a reminder and one patient's carer requested no further involvement)." Comment: Substantial attrition by 3-week follow-up (12/23 missing) with reasons plausibly related to outcomes (illness, death) and no imputation/handling reported; this is likely to bias results.
- Model support context: [{"source": "article", "quote": "Of the 23 participants, 20 completed their post consultation questionnaires... In all, 11 patients completed the 3-week follow-up questionnaires (five patients were too unwell, four died...).", "relevance": "Shows amount and reasons for missing outcome data, many related to illness/death."}, {"source": "methodology", "quote": "Participants: 23 patients in pilot study... Outcomes collected: questionnaires pre-consultation, post-consultation, and 3-week follow-up... No explicit statements about randomisation, allocation, or blinding are reported.", "relevance": "Confirms lack of reporting on handling/imputation of missing data and small pilot sample."}]
- GT support: Low levels of loss to follow‐up 4/174; balanced across groups (n = 2 each), with comparable reasons
- Evidence row: {}
- Source context preview: ## Results of pilot study Of the 23 participants, 20 completed their post consultation questionnaires, the remaining three became acutely unwell but gave verbal feedback to the research nurse following the consultation. In all, 11 patients completed the 3-week follow-up questionnaires (five patients were too unwell, four died, two did not respond to a reminder and one patient's carer requested no further involvement). --- ## Results of pilot study Patients' views about the QPL are outlined in Table 2Table 2Patient and carer feedback about QPL from pilot study Post consultation questionnaire refers to consultation immediately after receiving QPL (n=20)3-week follow-up refers to use of QPL...


## 15249261 - Ross 2004

- Mode: hybrid
- Review context: none (0 chars)
- Article chars: 28431
- Extraction context chars: 12003
- Total seconds: 54.63

### Methodology Extraction

- `randomization_method`: "patients were consecutively assigned identification numbers that were linked to either the intervention group or the control group according to a predefined computer-generated randomization scheme developed by a statistical consultant. Randomization was restricted so that equal numbers of patients were assigned to the intervention and the control groups in blocks of 10."
- `allocation_concealment_method`: Not reported
- `blinding_participants`: "When patients completed the initial questionnaire they were blinded to their enrollment status."
- `blinding_personnel`: Not reported
- `blinding_outcome_assessors`: Not reported
- `attrition_details`: Insufficient information. The article states that participants completed questionnaires at baseline, 6 months, and 12 months and that information on mortality came from chart review, nursing staff, and telephone/mail contact. It also states: "we used a repeated measures analysis for incomplete data... The repeated measures model for incomplete data used observations prior to dropout to adjust the 6-month and 12-month means for each outcome measure, under the assumption that data were missing at...
- `study_design`: Randomized controlled trial (individual randomization), parallel groups
- `additional_notes`: Intervention group received user ID/password and written user guide; control group received usual care and was offered SPPARO after study. Randomization used computer-generated scheme with block size 10. Sample size target 100 per group. Statistical analysis used mixed model repeated measures for incomplete data (PROC MIXED, SAS v8.1) assuming missing at random.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Low risk | yes | article_text_match |  |
| Allocation concealment | Unclear risk | Unclear risk | yes | article_absence_or_unclear |  |
| Blinding of participants and personnel: All outcomes | High risk | High risk / Low risk | yes | no_support_phrase_match |  |
| Blinding of outcome assessment: All outcomes | Low risk | High risk / Low risk | yes | no_support_phrase_match |  |
| Incomplete outcome data: All outcomes | Low risk | High risk / Unclear risk | no | article_absence_or_unclear | attrition_balance_or_missing_data_handling |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: were consecutively assigned identification numbers that | consecutively assigned identification numbers that were | assigned identification numbers that were linked
- Model rationale: The trial used a predefined computer-generated randomization scheme (block randomization), which is an explicitly random method for sequence generation and satisfies the Cochrane criteria for Low risk of bias in this domain.
- Model support: Quote: "patients were consecutively assigned identification numbers that were linked to either the intervention group or the control group according to a predefined computer-generated randomization scheme developed by a statistical consultant. Randomization was restricted so that equal numbers of patients were assigned to the intervention and the control groups in blocks of 10." Comment: Probably done — a predefined computer-generated randomization scheme with block randomization is a random method meeting Low risk criteria.
- Model support context: [{"source": "article", "quote": "patients were consecutively assigned identification numbers ... according to a predefined computer-generated randomization scheme ... Randomization was restricted ... in blocks of 10.", "relevance": "Describes use of a computer random number scheme and block randomization, showing a random sequence generation method."}, {"source": "methodology", "quote": "\"randomization_method\": \"...linked to either the intervention group or the control group according to a predefined computer-generated randomization scheme... blocks of 10.\"", "relevance": "Extraction confirms the computer-generated, block-randomized sequence generation."}]
- GT support: "As the questionnaires were received, patients were consecutively assigned identification numbers that were linked to either the intervention group or the control group according to a predefined computer‐generated randomisation scheme developed by a statistical consultant” (p. 2)
- Evidence row: {}
- Source context preview: ## Randomization As the questionnaires were received, patients were consecutively assigned identification numbers that were linked to either the intervention group or the control group according to a predefined computer-generated randomization scheme developed by a statistical consultant. Randomization was restricted so that equal numbers of patients were assigned to the intervention and the control groups in blocks of 10. --- ## Randomization After completing the informed consent, patients who were interested in enrolling in the primary study were provided with an enrollment form and the initial questionnaire. When patients completed the initial questionnaire they were blinded to their...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The trial reports a computer-generated, blocked randomization sequence but gives no details that allocation was concealed (central system, opaque sealed envelopes, or other safeguards). Without information that recruiters could not foresee assignments, risk of selection bias cannot be judged as low.
- Model support: Quote: "patients were consecutively assigned identification numbers that were linked to either the intervention group or the control group according to a predefined computer-generated randomization scheme developed by a statistical consultant. Randomization was restricted so that equal numbers of patients were assigned to the intervention and the control groups in blocks of 10." Comment: Allocation concealment method not reported. Although a computer-generated scheme was used, there is no information that assignment was implemented centrally or that recruiters/enrollers could not foresee allocations (e.g. sealed envelopes or central phone/web system). Probably not assured.
- Model support context: [{"source": "article", "quote": "patients were consecutively assigned identification numbers that were linked to either the intervention group or the control group according to a predefined computer-generated randomization scheme", "relevance": "Describes random sequence generation but does not state how assignments were concealed from recruiters."}, {"source": "methodology", "quote": "allocation_concealment_method: Not reported", "relevance": "Explicitly notes absence of information about concealment, leaving risk unclear."}]
- GT support: Not reported
- Evidence row: {}
- Source context preview: ## Introduction With the advent of electronically stored medical records and of the Internet, it has become technically feasible to provide patients access to their records online. In comparison to a written medical record kept in centralized storage, an Internet-accessible medical record may be particularly helpful for patients. Patients can review an online medical record repeatedly at their convenience, in the context of other resources that may assist them in comprehending it. Demonstration projects have shown that patients can be provided access to online medical records without compromising privacy and security. Furthermore, access to these records is appreciated by patients and...

#### Blinding of participants and personnel: All outcomes

- Prediction: High risk
- Ground truth: High risk / Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: Blinding was not maintained: participants had to use a web system (obvious allocation) and personnel could learn status, so lack of blinding was likely to influence subjective outcomes (satisfaction, adherence), creating a material risk of performance bias.
- Model support: Quote: "When patients completed the initial questionnaire they were blinded to their enrollment status." Comment: Participants were only blinded at the time of initial questionnaire completion; the intervention required login/password access and staff/physicians could become aware if patients mentioned or used the system. Personnel blinding not maintained and participants could readily infer allocation, making performance bias likely for subjective outcomes.
- Model support context: [{"source": "article", "quote": "When patients completed the initial questionnaire they were blinded to their enrollment status.", "relevance": "Shows only temporary/initial participant blinding; does not indicate ongoing masking during follow-up."}, {"source": "article", "quote": "The physicians and practice staff were not told which patients were enrolled into the study. They could become aware ... if a patient directly mentioned using it, or if a patient sent an electronic message using SPPARO.", "relevance": "Indicates personnel could become aware of allocation during the study, risking differential care or behavior."}]
- GT support: Objective outcomes Mortality, hospitalisation, emergency room visits No blinding, but we assume that possible performance bias will not cause differences in mortality, hospitalisation, and emergency room visits | Patient‐reported outcomes Self‐efficacy, self‐reported medication adherence, patient satisfaction: no blinding
- Evidence row: {}
- Source context preview: ## Randomization After completing the informed consent, patients who were interested in enrolling in the primary study were provided with an enrollment form and the initial questionnaire. When patients completed the initial questionnaire they were blinded to their enrollment status. --- ## Randomization As the questionnaires were received, patients were consecutively assigned identification numbers that were linked to either the intervention group or the control group according to a predefined computer-generated randomization scheme developed by a statistical consultant. Randomization was restricted so that equal numbers of patients were assigned to the intervention and the control groups...

#### Blinding of outcome assessment: All outcomes

- Prediction: Low risk
- Ground truth: High risk / Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: Outcome measures were primarily subjective patient-reported questionnaires and chart-derived events; participants and staff could become aware of allocation and no explicit blinded outcome assessment was reported, so lack of blinding likely biased measurement. Calibration: source indicates blinded trial-team assessment or objective automated/device measurement unlikely to be influenced by allocation knowledge.
- Model support: Quote: "The physicians and practice staff were not told which patients were enrolled into the study. They could become aware of a patient's enrollment status, however, if a patient directly mentioned using it, or if a patient sent an electronic message using SPPARO." Comment: Probably not done — outcome assessment relied largely on self-reported questionnaires (patient-reported health status, satisfaction, adherence) and chart review; participants were blinded at enrollment but could become aware of allocation and outcomes were subjective, so lack of assessor/participant blinding is likely to have influenced measurement. Comment: Calibration: source indicates blinded trial-team assessment or objective automated/device measurement unlikely to be influenced by allocation knowledge.
- Model support context: [{"source": "article", "quote": "## Randomization After completing the informed consent, patients who were interested in enrolling in the primary study were provided with an enrollment form and the initial questionnaire. When patients completed the initial questionnaire...", "relevance": "Calibration: source indicates blinded trial-team assessment or objective automated/device measurement unlikely to be influenced by allocation knowledge."}, {"source": "article", "quote": "They could become aware of a patient's enrollment status, however, if a patient directly mentioned using it, or if a patient sent an electronic message using SPPARO.", "relevance": "Shows clinicians/staff could learn allocation, risking biased assessments from staff or patients."}]
- GT support: Objective outcomes Mortality, hospitalisation, emergency room visits: no blinding reported | Patient‐reported outcomes Self‐efficacy, self‐reported medication adherence, patient satisfaction: no blinding reported
- Evidence row: {}
- Source context preview: ## Randomization After completing the informed consent, patients who were interested in enrolling in the primary study were provided with an enrollment form and the initial questionnaire. When patients completed the initial questionnaire they were blinded to their enrollment status. --- ## Randomization As the questionnaires were received, patients were consecutively assigned identification numbers that were linked to either the intervention group or the control group according to a predefined computer-generated randomization scheme developed by a statistical consultant. Randomization was restricted so that equal numbers of patients were assigned to the intervention and the control groups...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: High risk / Unclear risk
- Match: False
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: Although individual reasons for loss are not detailed, attrition was moderate and fairly balanced over time, and the investigators used mixed-model repeated measures (valid under missing at random) to adjust estimates — meeting criteria for low risk of bias from incomplete outcome data.
- Model support: Quote: "Of the patients enrolled, 78.5% remained at 6 months and 76% remained at 12 months." Comment: Attrition was moderate (~22–24%) but balanced reporting indicates repeated-measures mixed models were used to handle incomplete data under a missing-at-random assumption; reasons for loss are not reported but the authors used appropriate modern methods to reduce bias. Probably done: appropriate handling of incomplete outcome data with mixed-models.
- Model support context: [{"source": "article", "quote": "Of the patients enrolled, 78.5% remained at 6 months and 76% remained at 12 months.", "relevance": "Shows amount of attrition (moderate, similar at both follow-ups)."}, {"source": "methodology", "quote": "\"The repeated measures model for incomplete data used observations prior to dropout... under the assumption that data were missing at random.\"", "relevance": "Indicates appropriate statistical handling (mixed model) of missing data."}]
- GT support: Objective outcomes Loss to follow‐up for outcome variables of resource use were not reported. Data were taken from chart review, but no indication whether these data were complete; number of analysed participants was not reported as outcome‐specific. Mortality data were obtained for all persons and for those who did not respond | Patient‐reported outcomes Great loss to follow‐up for patient‐reported outcomes from questionnaires. Greater loss to follow‐up in intervention group (30% vs 19%) but no indication of link to intervention; number of analysed participants was not reported as outcome‐specific
- Evidence row: {}
- Source context preview: ## Enrollment, Retention, and Demographics Figure 1 illustrates the flow of participants through the study. The pool of eligible patients was derived from the practice census at the beginning of the study and subsequent records of patients who had appointments during the enrollment period. Two interested patients were excluded because they were health professionals (one physician's assistant and one nurse practitioner). Approximately 10 patients were not approached for enrollment because they did not speak English. Of the patients enrolled, 78.5% remained at 6 months and 76% remained at 12 months. --- ## Statistical Analysis For scored questionnaire items, we used a repeated measures...

## Workflow Evolution Notes

- Inspect mismatches where prediction is `Unclear risk` but GT is `Low risk`: these usually mean retrieval or Stage 1 extraction missed a concrete methodological phrase.
- Inspect mismatches where prediction is `Low risk` or `High risk` but GT is `Unclear risk`: these usually mean the prompt is allowing too much inference from generic trial language.
- For blinding mismatches, add outcome-type cues to the prompt: self-report outcomes, objective outcomes, assessor-administered outcomes, and whether lack of blinding can materially affect the outcome.
- For allocation concealment mismatches, require the model to distinguish sequence generation from concealment before assignment.