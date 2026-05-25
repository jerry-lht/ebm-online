# Batch Risk of Bias Eval Report

This report contains an audit trace: explicit extracted evidence, model-provided rationales, and label comparisons. It does not include hidden chain-of-thought.

- Studies: 20
- Domains: 100
- Accuracy: 61/100 (61.0%)
- Article-only scorable accuracy: 18/28 (64.3%)
- Article-observable accuracy: 18/28 (64.3%)
- Non-observable/article-missing GT accuracy: 37/57 (64.9%)
- External/review-context GT domains: 0/1 matched
- Unknown or non-text GT domains: 15
- Timeout retries recovered: 0

Interpretation note: `Article-only scorable` is the fairest metric for the current direct input contract (`sr_pico + xml_content + domain`). External/review-context rows often require author emails, protocols, registries, tables/figures, or review notes that are not present in the XML excerpts.

## Summary

| PMID | Study | Correct | Accuracy | Seconds | Retry |
|---|---|---:|---:|---:|---|
| 14647140 | Clayton 2007 | 1/5 | 20.0% | 47.30 |  |
| 17389922 | Cobo 2007 | 4/5 | 80.0% | 40.18 |  |
| 18398460 | Menéndez 2008 | 5/5 | 100.0% | 43.22 |  |
| 18779465 | Grant 2008 | 4/5 | 80.0% | 47.20 |  |
| 19209172 | Vodermaier 2009 | 2/5 | 40.0% | 48.15 |  |
| 19291323 | Middleton 2011 | 2/5 | 40.0% | 46.34 |  |
| 19319218 | Chien 2008a | 4/5 | 80.0% | 44.32 |  |
| 19487623 | King 2009 | 2/5 | 40.0% | 48.01 |  |
| 19798037 | Nidich 2009 | 1/5 | 20.0% | 45.29 |  |
| 20044929 | Hegarty 2013 | 4/5 | 80.0% | 41.62 |  |
| 20395225 | Alvarez 2010 | 5/5 | 100.0% | 43.49 |  |
| 20655662 | Litt 2010 | 4/5 | 80.0% | 42.30 |  |
| 20740213 | Jo 2010 | 3/5 | 60.0% | 43.33 |  |
| 20830695 | Deblinger 2011 | 3/5 | 60.0% | 43.03 |  |
| 21342490 | Freeman 2011 | 1/5 | 20.0% | 43.45 |  |
| 21543987 | Van der Ploeg 2010 | 2/5 | 40.0% | 41.62 |  |
| 21680092 | Turner 2011 | 4/5 | 80.0% | 43.66 |  |
| 21723049 | Brewer 2011 | 4/5 | 80.0% | 44.37 |  |
| 21775755 | Ziegler 2011 | 3/5 | 60.0% | 45.73 |  |
| 21933436 | Dorresteijn 2016 | 3/5 | 60.0% | 47.44 |  |

## Error Types

- gt_support_not_found_in_article_text: 19
- over-inferred_from_sparse_reporting: 8
- under-called_due_to_missing_or_underused_evidence: 5
- figure_table_or_supplement_needed: 3
- blinding_outcome_type_or_role_confusion: 2
- allocation_concealment_detail_threshold: 1
- external_or_review_context_needed: 1

## 14647140 - Clayton 2007

- Mode: audited
- Review context: none (0 chars)
- Article chars: 24130
- Extraction context chars: n/a
- Total seconds: 47.3
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

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
- Model rationale: The supplied excerpts contain no description of the method used to generate the allocation sequence (random number table, computer generator, coin toss, or any non-random rule). Because the necessary detail about sequence generation is missing, the risk is Unclear.
- Model support: Quote: "Whether this was a result of seeing the doctor or the use of the QPL is unclear from the design of the study" Comment: The report does not describe how participants were allocated to groups or any method of sequence generation, so risk of biased sequence generation cannot be assessed.
- Model support context: [{"source": "article", "quote": "Whether this was a result of seeing the doctor or the use of the QPL is unclear from the design of the study", "relevance": "Explicitly states study design details are unclear; no description of randomization method is provided."}, {"source": "not_reported", "quote": "No text describing random sequence generation (e.g., computer, random numbers, coin toss) is present in excerpts", "relevance": "Absence of any sequence-generation method prevents judgment as Low or High risk."}]
- GT support: Individually randomised and stratified by physician – random permuted blocks of 10 constructed using random number table (by research assistant not involved in recruitment)
- Evidence row: {}
- Source context preview: ## Data collection and analysis The focus groups and telephone interviews were audiotaped and fully transcribed. Data analysis was informed by qualitative methodology (Pope and Mays, 2000). Individual questions or information needs were identified from the transcripts using the participants' own language where possible. These were discussed by both facilitators to ensure consistency of interpretation and were organised into categories to facilitate comprehension, as suggested by Ley (1988). Further focus groups and/or telephone interviews were conducted until no additional topics were raised. A draft QPL was developed using the categories and questions identified in the transcripts. The...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The excerpts do not describe any method of allocation concealment (central randomization, sealed opaque envelopes, numbered containers, etc.). Because concealment procedures are not reported, there is insufficient information to judge and the appropriate label is Unclear risk.
- Model support: Quote: "We thank the research nurses, Debbie Malcolm, Jenny Bunn and Margaret McJannett, who assisted with patient recruitment and data collection in the pilot study." Comment: The report does not describe how the allocation sequence was concealed from those enrolling participants (no mention of central randomization, sealed envelopes, or other safeguards).
- Model support context: [{"source": "article", "quote": "We thank the research nurses... who assisted with patient recruitment and data collection in the pilot study.", "relevance": "Indicates personnel responsible for recruitment but gives no information about allocation concealment procedures."}, {"source": "article", "quote": "In all, 19 patients and 24 carers were recruited from hospitals, PC units and the community in three PC services in Sydney.", "relevance": "Reports numbers recruited but does not describe any method for concealing allocation prior to assignment."}]
- GT support: Allocations were concealed using sequentially numbered opaque sealed envelopes
- Evidence row: {}
- Source context preview: ## Results of focus groups and individual interviews General questions included how and when to contact the PC team, and the connection between the PC team and other health professionals involved in the patients' care. In addition, some patients wanted advice about how to choose another doctor. A second opinion was valued regarding disease-specific treatment from an independent source. Others wanted to discuss the option of stopping anticancer treatment or not starting it at all. --- ## Results of pilot study Patients' views about the QPL are outlined in Table 2Table 2Patient and carer feedback about QPL from pilot study Post consultation questionnaire refers to consultation immediately...

#### Blinding of participants and personnel: All outcomes

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The excerpts show an intervention delivered and patient-reported questionnaires were used (outcomes likely subjective), but the report gives no information whether participants or personnel were blinded; lacking that detail, risk of performance bias cannot be judged and is Unclear.
- Model support: Quote: "We piloted the final draft QPL in 23 patients seeing one of three PC doctors from three services in Sydney... Of the 23 participants, 20 completed their post consultation questionnaires... 11 patients completed the 3-week follow-up questionnaires..." Comment: The report describes a pilot of a question prompt list given to patients but does not state whether participants or personnel were blinded to allocation or whether any blinding was attempted, nor whether outcomes (patient-reported anxiety, satisfaction, knowledge) were collected blinded.
- Model support context: [{"source": "article", "quote": "We piloted the final draft QPL in 23 patients seeing one of three PC doctors from three services in Sydney", "relevance": "Indicates an intervention (QPL) was given to patients but does not describe blinding of participants or personnel."}, {"source": "article", "quote": "20 completed their post consultation questionnaires... 11 patients completed the 3-week follow-up questionnaires", "relevance": "Shows patient-reported outcomes were collected, implying outcomes could be influenced by knowledge of intervention; blinding status not reported."}]
- GT support: Physicians were unblinded; authors note that prior research has indicated that QPL require professional endorsement in consultations to be effective Unclear whether or not patients and carers were blinded to intervention and/or what effect this may have had on the outcomes
- Evidence row: {}
- Source context preview: ## Participants Three groups felt to have important input were sampled: (a) PC patients, (b) carers of PC patients, and (c) health professionals working in PC. Patients and carers were eligible to take part if they were: (1) over 18 years of age, (2) English speaking, (3) well enough to participate, (4) able to give informed consent, and (5) referred to a specialist PC service and diagnosed with an incurable and progressive illness, or the carer of such a patient. In all, 19 patients and 24 carers were recruited from hospitals, PC units and the community in three PC services in Sydney. Their demographic characteristics are shown in Table 1Table 1Demographic and disease characteristics of...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The outcome is self-reported anxiety measured by patients after consultation; the excerpts do not report whether patients or assessors were blinded. Because lack of blinding of self-reported outcomes is likely to influence results but blinding status is not reported, there is insufficient information to judge risk of detection bias.
- Model support: Quote: "After each consultation, clinicians were asked whether the QPL interfered with the flow of the consultation (Yes/No/Not sure)... After the consultation, patients also completed a questionnaire measuring anxiety and responses to the QPL using standard items." Comment: The report describes patient self-reported anxiety questionnaires (Spielberger State Anxiety Inventory) collected after consultation but does not state whether outcome assessors or patients were blinded to allocation.
- Model support context: [{"source": "article", "quote": "Patient anxiety was measured by the Spielberger State Anxiety Inventory (Spielberger, 1983) (20 items)...", "relevance": "Identifies the review-relevant outcome as a self-reported anxiety questionnaire."}, {"source": "article", "quote": "After the consultation, patients also completed a questionnaire measuring anxiety and responses to the QPL using standard items.", "relevance": "Shows outcomes were self-reported after knowing intervention; no information on blinding of patients or outcome assessors is provided."}]
- GT support: Authors indicate that consultations were audiotaped, transcribed and analysed by blinded coders "Two coders were trained and blinded to group allocation. One coder coded all transcripts and recoded a random 10% to determine intrarater reliability. The second coder coded a random 10% of transcripts to determine inter‐rater reliability" (page 716)
- Evidence row: {}
- Source context preview: ## Data collection and analysis Prior to the consultation, patients completed a questionnaire regarding their information and involvement (decisional control) preferences, and anxiety levels. General preferences for information were assessed using a question from the Cassileth Information Styles Questionnaire measuring the type of information preferred (Cassileth et al, 1980). Preferences for decisional control were assessed using a validated and reliable question from previous studies in cancer patients (Sutherland et al, 1989; Degner et al, 1997b). Patients were classified as wanting an ‘active’, ‘passive’ or ‘collaborative’ role when making decisions about treatment. Patient anxiety was...

#### Incomplete outcome data: All outcomes

- Prediction: High risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: Substantial overall missingness at the key 3-week outcome (≈52%) with outcome-related reasons (illness, death) and no description of handling or group denominators creates a high risk of attrition bias. Audited override: evidence map identifies substantial missingness without protective handling.
- Model support: Quote: 'Of the 23 participants, 20 completed their post consultation questionnaires, the remaining three became acutely unwell but gave verbal feedback... In all, 11 patients completed the 3-week follow-up questionnaires (five patients were too unwell, four died, two did not respond... and one patient's carer requested no further involvement).' Comment: Large and outcome-related missing data (illness/death), high overall attrition at 3 weeks (52%), no handling or arm-level denominators reported, so risk of attrition bias is high. Comment: Audited override: evidence map identifies substantial missingness without protective handling.
- Model support context: [{"source": "article", "quote": "Of the 23 participants, 20 completed their post consultation questionnaires, the remaining three became acutely unwell but gave verbal feedback", "relevance": "Shows missing at immediate post-consult and that non-response related to acute illness."}, {"source": "article", "quote": "In all, 11 patients completed the 3-week follow-up questionnaires (five patients were too unwell, four died, two did not respond...)", "relevance": "Demonstrates high (12/23) loss at 3 weeks with reasons likely related to the outcome (illness, death) and no handling described."}]
- GT support: Low levels of loss to follow‐up 4/174; balanced across groups (n = 2 each), with comparable reasons
- Evidence row: {}
- Source context preview: ## Results of pilot study Of the 23 participants, 20 completed their post consultation questionnaires, the remaining three became acutely unwell but gave verbal feedback to the research nurse following the consultation. In all, 11 patients completed the 3-week follow-up questionnaires (five patients were too unwell, four died, two did not respond to a reminder and one patient's carer requested no further involvement). --- ## Results of pilot study Patients' views about the QPL are outlined in Table 2Table 2Patient and carer feedback about QPL from pilot study Post consultation questionnaire refers to consultation immediately after receiving QPL (n=20)3-week follow-up refers to use of QPL...


## 17389922 - Cobo 2007

- Mode: audited
- Review context: none (0 chars)
- Article chars: 22398
- Extraction context chars: n/a
- Total seconds: 40.18
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Low risk | yes | article_text_match |  |
| Allocation concealment | Unclear risk | Unclear risk | yes | article_absence_or_unclear |  |
| Blinding of participants and personnel: All outcomes | Low risk | Unclear risk | no | article_absence_or_unclear | over-inferred_from_sparse_reporting |
| Blinding of outcome assessment: All outcomes | Unclear risk | Unclear risk | yes | article_absence_or_unclear |  |
| Incomplete outcome data: All outcomes | Low risk | Low risk | yes | article_absence_or_unclear |  |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: we randomly allocated the manuscripts accepted for review into four groups defined by the interventions
- Model rationale: The report states allocation was done with a computer program and minimization (which is considered equivalent to random), meeting the Low risk criteria for random sequence generation.
- Model support: Quote: "manuscripts were randomly allocated (by AS) using a computer program that first stratifies by study type, and second allocates to intervention groups while minimizing differences in initial quality." Comment: A computer program and minimization with stratification describe a random component in sequence generation.
- Model support context: [{"source": "article", "quote": "manuscripts were randomly allocated (by AS) using a computer program that first stratifies by study type, and second allocates to intervention groups while minimizing differences in initial quality.", "relevance": "Describes a computer program random allocation and use of minimization, both acceptable random sequence methods."}, {"source": "article", "quote": "We randomly allocated the manuscripts accepted for review into four groups defined by the interventions", "relevance": "Confirms manuscripts were allocated randomly to intervention groups."}]
- GT support: Quote: "We randomly allocated the manuscripts accepted for review into four groups defined by the interventions"; "Then, manuscripts were randomly allocated (by AS) using a computer program that first stratifies by study type, and second allocates to intervention groups while minimizing differences in initial quality. Then, the manuscripts followed the proper editorial procedure, according to their assigned group."
- Evidence row: {}
- Source context preview: ## Enrolment and Randomization Of the 327 originals received between May 2004 and March 2005, 196 (59.9%) were directly rejected by the editorial team. The remaining 131 (40.1%) were selected by the editorial committee as possible publications and therefore randomized. Of these, 2 were excluded either as a result of an administrative error (n = 1) or because the authors refused to participate (n = 1). From the 129 randomized manuscripts, 14 were lost of follow up because authors missed the deadline and the masked allocation was revealed; 21 (18.3%) of the 115 included papers were “interventions”, but only 3 were randomized clinical trials, 46 (40.0%) were longitudinal designs, 28 (24.3%)...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The report describes computer-based random allocation but provides no details on allocation concealment (central control, sealed envelopes, or other safeguards). Because concealment methods are not described, risk of selection bias cannot be judged and is Unclear.
- Model support: Quote: "manuscripts were randomly allocated (by AS) using a computer program that first stratifies by study type, and second allocates to intervention groups while minimizing differences in initial quality." Comment: Random sequence generation is described, but there is no information about how allocation was concealed from those enrolling manuscripts or whether recruiters could foresee assignments.
- Model support context: [{"source": "article", "quote": "manuscripts were randomly allocated (by AS) using a computer program that first stratifies by study type, and second allocates to intervention groups", "relevance": "Describes method of allocation generation but does not state how assignments were concealed from enrolment staff."}, {"source": "article", "quote": "Papers were randomized once the two clinical peers had been chosen.", "relevance": "Timing of randomization relative to selection is given, but concealment procedure (central allocation, sealed envelopes, etc.) is not reported."}]
- GT support: Insufficient reporting of the allocation procedure.
- Evidence row: {}
- Source context preview: ## Assessment and Procedure Two evaluators (EC, RD) independently rated the reporting quality of manuscripts at initial submission and following peer review and revision, according to the MQAI. Both knew the initial and final status but were blinded to the intervention group. The final score awarded to each scale item was reached by averaging the two evaluators' item scores after allowing each one to modify his or her score once the reasons for the other evaluator's score was made known. Primary outcome was defined as the difference in the quality of papers between the initial and final submission, expressed as the sum of the 36 specific MQAI items, resulting in a minimum of 36 (lowest...

#### Blinding of participants and personnel: All outcomes

- Prediction: Low risk
- Ground truth: Unclear risk
- Match: False
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The review-relevant outcome (MQAI score change) was assessed by evaluators explicitly blinded to group allocation, and the outcome is an assessor-rated quality score; therefore lack of blinding of other parties is unlikely to have influenced the outcome.
- Model support: Quote: "Both knew the initial and final status but were blinded to the intervention group." Comment: Outcome (change in manuscript quality score) was assessed by two blinded evaluators, so personnel assessing and influencing the outcome were masked and lack of participant blinding (authors/reviewers) is unlikely to have influenced this measured, largely objective outcome.
- Model support context: [{"source": "article", "quote": "Two evaluators (EC, RD) independently rated the reporting quality... Both knew the initial and final status but were blinded to the intervention group.", "relevance": "Shows outcome assessors were blinded to allocation, reducing risk of performance bias for the quality score outcome."}, {"source": "article", "quote": "Primary outcome was defined as the difference in the quality of papers between the initial and final submission, expressed as the sum of the 36 specific MQAI items.", "relevance": "Specifies the review-relevant outcome is an objective scoring instrument rated by the blinded evaluators."}]
- GT support: Unclear if the editorial team was blinded. Apart from half of them receiving the intervention, the clinical reviewers seem to be unaware of the study objective and randomization. Unclear whether it is possible for a reviewer to be in multiple intervention groups, based on randomization of manuscripts and the possibility for receiving several manuscripts over the trial period.
- Evidence row: {}
- Source context preview: ## Enrolment and Randomization Of the 327 originals received between May 2004 and March 2005, 196 (59.9%) were directly rejected by the editorial team. The remaining 131 (40.1%) were selected by the editorial committee as possible publications and therefore randomized. Of these, 2 were excluded either as a result of an administrative error (n = 1) or because the authors refused to participate (n = 1). From the 129 randomized manuscripts, 14 were lost of follow up because authors missed the deadline and the masked allocation was revealed; 21 (18.3%) of the 115 included papers were “interventions”, but only 3 were randomized clinical trials, 46 (40.0%) were longitudinal designs, 28 (24.3%)...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The outcome is the MQAI score (assessor-rated reporting quality) and the two evaluators were explicitly blinded to intervention group while rating, so blinding of outcome assessment was ensured and unlikely to be broken, supporting Low risk. Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support: Quote: "Two evaluators (EC, RD) independently rated the reporting quality of manuscripts at initial submission and following peer review and revision... Both knew the initial and final status but were blinded to the intervention group." Comment: Outcome assessors (two evaluators) were explicitly blinded to intervention group when rating the MQAI, so detection bias is unlikely. Comment: Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support context: [{"source": "article", "quote": "## Assessment and Procedure Two evaluators (EC, RD) independently rated the reporting quality of manuscripts at initial submission and following peer review and revision, according to the MQAI. Both knew the initial and final status but...", "relevance": "Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported."}, {"source": "article", "quote": "Two evaluators (EC, RD) independently rated the reporting quality... Both knew the initial and final status but were blinded to the intervention group.", "relevance": "States that the outcome assessors were blinded to intervention allocation when rating the primary outcome."}]
- GT support: Quote: "Two evaluators (EC, RD) independently rated the reporting quality of manuscripts at initial submission and following peer review and revision, according to the MQAI. Both knew the initial and final status but were blinded to the intervention group."; "On the use of a checklist, the evaluators were able to guess the intervention group in 65.3% (95% CI from 53.5 to 76.0%) of the 75 over 99 (75.8%) cases analyzed." According to the authors the overall conclusion the main effects remained the same after stratifying by response to both of the blinding questions. However, the data are not provided.
- Evidence row: {}
- Source context preview: ## Assessment and Procedure Two evaluators (EC, RD) independently rated the reporting quality of manuscripts at initial submission and following peer review and revision, according to the MQAI. Both knew the initial and final status but were blinded to the intervention group. The final score awarded to each scale item was reached by averaging the two evaluators' item scores after allowing each one to modify his or her score once the reasons for the other evaluator's score was made known. Primary outcome was defined as the difference in the quality of papers between the initial and final submission, expressed as the sum of the 36 specific MQAI items, resulting in a minimum of 36 (lowest...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The report gives randomized denominator (129), number lost to follow-up (14) with reasons, states those lost did not differ at baseline from retained manuscripts, and sensitivity analyses with imputed values yielded similar results; therefore missing outcome data are unlikely to be related to true outcomes and unlikely to bias results.
- Model support: Quote: "From the 129 randomized manuscripts, 14 were lost of follow up because authors missed the deadline and the masked allocation was revealed;... The 14 papers lost to follow-up did not differ, in terms of baseline quality, from the originals in the complete population. We performed several sensitivity analyses including those papers with different imputed values for the final version that produced very similar conclusions." Comment: Attrition (14/129) is reported, losses assessed as similar at baseline to retained manuscripts, and sensitivity analyses with imputation produced similar results, indicating missing data unlikely to bias the effect.
- Model support context: [{"source": "article", "quote": "From the 129 randomized manuscripts, 14 were lost of follow up because authors missed the deadline and the masked allocation was revealed;", "relevance": "States number and reason for missing randomized manuscripts and that allocation was revealed after loss."}, {"source": "article", "quote": "The 14 papers lost to follow-up did not differ, in terms of baseline quality, from the originals in the complete population. We performed several sensitivity analyses including those papers... produced very similar conclusions.", "relevance": "Indicates missing manuscripts similar at baseline and sensitivity analyses/imputation did not change conclusions, reducing risk of bias from attrition."}]
- GT support: 5 manuscripts in the control group and 4 in the intervention group were lost to follow-up. However, this was before the intervention was delivered and was due to the authors not responding within the deadline. It is unlikely this would have affected the outcome in any meaningful way. After the reviews, 5 manuscripts were rejected in each group. It is unclear if the editors rejecting were blinded or not. However, it is unlikely that this would have had an effect on the result as the rejected manuscripts were of low quality.
- Evidence row: {}
- Source context preview: ## Study populations Three different populations were considered: “complete” which included all randomized manuscripts not lost to follow-up, which was the population for the main analysis. Two other populations were defined for the sensitive analyses: one taking into consideration all “randomized” manuscripts and one including only those manuscripts accepted for publication. Those manuscripts rejected due to reviewers' comments and those lost to follow-up were analyzed considering two different values for their final quality: 1) the initial overall quality was imputed as the final overall quality interpreted as no change in quality during the editorial process), or 2) the final overall...


## 18398460 - Menéndez 2008

- Mode: audited
- Review context: none (0 chars)
- Article chars: 20345
- Extraction context chars: n/a
- Total seconds: 43.22
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Low risk | yes | no_support_phrase_match |  |
| Allocation concealment | Unclear risk | Unclear risk | yes | no_support_phrase_match |  |
| Blinding of participants and personnel: All outcomes | Low risk | Low risk | yes | no_support_phrase_match |  |
| Blinding of outcome assessment: All outcomes | Low risk | Low risk | yes | no_support_phrase_match |  |
| Incomplete outcome data: All outcomes | Unclear risk | Unclear risk | yes | no_support_phrase_match |  |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report states a computer-generated sequential list randomly ordered in blocks of 10 was used to link study numbers to treatments, which is a described random component fulfilling the Low risk criteria.
- Model support: Quote: "A computer-generated sequential list contained the study numbers linked to treatment identification letters, randomly ordered in blocks of 10." Comment: This explicitly describes a computer-generated random sequence (with blocking), meeting Low risk criteria.
- Model support context: [{"source": "article", "quote": "A computer-generated sequential list contained the study numbers linked to treatment identification letters, randomly ordered in blocks of 10.", "relevance": "Direct description of a computer-generated random sequence for allocation."}, {"source": "article", "quote": "After written informed consent was obtained, the lowest available study number was assigned.", "relevance": "Shows application of the generated sequence via study numbers to assign participants."}]
- GT support: A computer-generated sequential list contained the study numbers linked to treatment identification letters, randomly ordered in blocks of 10. After written informed consent was obtained, the lowest available study number was assigned.
- Evidence row: {}
- Source context preview: ## Enrolment and interventions From August 2003 to April 2005 pregnant women were enrolled at the MDH ANC if their gestational age was ≤ 28 weeks, they did not report allergies to sulpha drugs, and they were permanent residents of the CISM study area. After written informed consent was obtained, the lowest available study number was assigned. A computer-generated sequential list contained the study numbers linked to treatment identification letters, randomly ordered in blocks of 10. Tablets of SP or placebo, identical in shape and colour, were stored in 10 bottles labelled only with a single treatment identification letter. Women were randomised to receive 3 tablets of SP (1500 mg...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: Participants were assigned the lowest available study number at enrolment and treatments were linked via a computer-generated sequential list with identical labelled bottles, which would prevent recruiters from foreseeing assignments and meets criteria for central/secure concealment. Calibration: source describes sequence/list/envelope mechanics but not enough safeguards or access control to show recruiters could not foresee assignments.
- Model support: Quote: "After written informed consent was obtained, the lowest available study number was assigned. A computer-generated sequential list contained the study numbers linked to treatment identification letters, randomly ordered in blocks of 10. Tablets of SP or placebo, identical in shape and colour, were stored in 10 bottles labelled only with a single treatment identification letter." Comment: Allocation used a computer-generated sequential list linking study numbers to treatment codes and identical labelled bottles, preventing recruiters from foreseeing assignments. Comment: Calibration: source describes sequence/list/envelope mechanics but not enough safeguards or access control to show recruiters could not foresee assignments.
- Model support context: [{"source": "article", "quote": "of the CISM study area. After written informed consent was obtained, the lowest available study number was assigned. A computer-generated sequential list contained the study numbers linked to treatment identification letters, randomly...", "relevance": "Calibration: source describes sequence/list/envelope mechanics but not enough safeguards or access control to show recruiters could not foresee assignments."}, {"source": "article", "quote": "After written informed consent was obtained, the lowest available study number was assigned.", "relevance": "Shows allocation proceeded by assigning study numbers at enrolment, consistent with concealed assignment."}]
- GT support: Allocation was stored in a computer-generated list, but there is no information about where this list was kept or who had access to it.
- Evidence row: {}
- Source context preview: ## Methods The protocol for this trial and supporting CONSORT checklist are available as supporting information; see Checklist S1 and Protocol S1. --- ## Enrolment and interventions From August 2003 to April 2005 pregnant women were enrolled at the MDH ANC if their gestational age was ≤ 28 weeks, they did not report allergies to sulpha drugs, and they were permanent residents of the CISM study area. After written informed consent was obtained, the lowest available study number was assigned. A computer-generated sequential list contained the study numbers linked to treatment identification letters, randomly ordered in blocks of 10. Tablets of SP or placebo, identical in shape and colour,...

#### Blinding of participants and personnel: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly states the study was double-blind and describes identical placebo and active tablets; therefore participants and key personnel were blinded and it is unlikely that lack of blinding would have influenced the objective and subjective outcomes assessed.
- Model support: Quote: "This double blind, individually randomised, placebo controlled trial" Comment: The trial is explicitly described as double-blind with identical SP and placebo tablets, indicating participants and personnel were blinded and unlikely to have had knowledge that would influence the listed outcomes.
- Model support context: [{"source": "article", "quote": "This double blind, individually randomised, placebo controlled trial", "relevance": "Explicit statement that the trial was double-blind, relevant to blinding of participants and personnel."}, {"source": "article", "quote": "Tablets of SP or placebo, identical in shape and colour, were stored in 10 bottles labelled only with a single treatment identification letter.", "relevance": "Describes identical appearance of active and placebo tablets, supporting maintenance of blinding for participants and administering personnel."}]
- GT support: This study was a double-blind, placebo-controlled trial. Tablets of SP or placebo, identical in shape and colour, were stored in 10 bottles labelled only with a single treatment identification letter. Women were randomized to receive 3 tablets of SP (1500 mg sulphadoxine/75 mg pyrimetamine) or placebo.
- Evidence row: {}
- Source context preview: ## Study design This double blind, individually randomised, placebo controlled trial had the primary objective of estimating the additive protective effect of two-dose IPTp with SP to that of ITNs on LBW prevalence. Based on previous estimates in the area, a LBW prevalence of 20% and an estimated 25% reduction to 15% in the presence of ITNs [14], 411 women per group were needed to show a lack of difference between the two groups with a confidence interval of 7 (8% to 22%), at the 5% level of significance with a 80% statistical power. The study protocol was approved by the National Mozambican Ethics Review Committee, and the Hospital Clinic of Barcelona Ethics Review Committee. --- ##...

#### Blinding of outcome assessment: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly states the trial was double-blind with identical placebo, and the review-relevant outcomes (parasitemia, PCV/anaemia, placental infection) were measured by laboratory/device methods by readers using standard procedures; these objective assessments are unlikely to be influenced by knowledge of allocation, so detection bias is low.
- Model support: Quote: "Tablets of SP or placebo, identical in shape and colour... This double blind, individually randomised, placebo controlled trial" Comment: Trial was double-blind with identical placebo, and laboratory outcome measurements (blood films, PCV, placental histology) are objective and unlikely influenced by assessor knowledge.
- Model support context: [{"source": "article", "quote": "Tablets of SP or placebo, identical in shape and colour.", "relevance": "Supports that allocation was masked to participants and staff, reducing chance assessors knew allocation."}, {"source": "article", "quote": "Thick and thin blood films were stained and read according to standard, quality-controlled procedures. PCV was measured in a microcapillary tube after centrifugation.", "relevance": "Outcome measurement was laboratory/device based and objective, reducing detection bias even if blinding failed."}]
- GT support: As nurses and doctors were blinded, and the principal outcome of the study was low birth weight, we judged the study to have a low risk of detection bias.
- Evidence row: {}
- Source context preview: ## Enrolment and interventions From August 2003 to April 2005 pregnant women were enrolled at the MDH ANC if their gestational age was ≤ 28 weeks, they did not report allergies to sulpha drugs, and they were permanent residents of the CISM study area. After written informed consent was obtained, the lowest available study number was assigned. A computer-generated sequential list contained the study numbers linked to treatment identification letters, randomly ordered in blocks of 10. Tablets of SP or placebo, identical in shape and colour, were stored in 10 bottles labelled only with a single treatment identification letter. Women were randomised to receive 3 tablets of SP (1500 mg...

#### Incomplete outcome data: All outcomes

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report asserts ITT analysis and references a trial profile, but the provided excerpts lack counts of randomized versus analyzed participants, missing outcome numbers by arm, reasons for loss, or imputation methods; therefore insufficient information to judge incomplete outcome data risk. Audited override: Low risk is not established because actual missing outcome data are not reported.
- Model support: Quote: 'Data were analysed by intention-to-treat (ITT) analysis whereby all randomised women were included regardless of whether or not they had received the intervention and the number of doses.' Comment: Trial report provides an ITT statement but the excerpts do not give randomized/enrolled counts, numbers analyzed, or missing outcomes by arm or reasons, so risk from incomplete outcome data cannot be judged. Comment: Audited override: Low risk is not established because actual missing outcome data are not reported.
- Model support context: [{"source": "article", "quote": "Data were analysed by intention-to-treat (ITT) analysis whereby all randomised women were included regardless of whether or not they had received the intervention and the number of doses.", "relevance": "States analysis approach but gives no attrition or missing-data counts or handling details."}, {"source": "article", "quote": "Figure 1 shows the trial profile and table 1 shows the baseline characteristics of participants.", "relevance": "Indicates participant flow exists in full paper but the supplied excerpts do not include the flow numbers needed to assess attrition bias."}]
- GT support: The paper does not explain why a few children did not have data on weight, or whether baseline characteristics were balanced among those who were weighed and those who were not.
- Evidence row: {}
- Source context preview: ## Enrolment and interventions From August 2003 to April 2005 pregnant women were enrolled at the MDH ANC if their gestational age was ≤ 28 weeks, they did not report allergies to sulpha drugs, and they were permanent residents of the CISM study area. After written informed consent was obtained, the lowest available study number was assigned. A computer-generated sequential list contained the study numbers linked to treatment identification letters, randomly ordered in blocks of 10. Tablets of SP or placebo, identical in shape and colour, were stored in 10 bottles labelled only with a single treatment identification letter. Women were randomised to receive 3 tablets of SP (1500 mg...


## 18779465 - Grant 2008

- Mode: audited
- Review context: none (0 chars)
- Article chars: 23878
- Extraction context chars: n/a
- Total seconds: 47.2
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Unclear risk | Unclear risk | yes | article_absence_or_unclear |  |
| Allocation concealment | Unclear risk | Unclear risk | yes | article_absence_or_unclear |  |
| Blinding of participants and personnel: All outcomes | Unclear risk | Unclear risk | yes | article_absence_or_unclear |  |
| Blinding of outcome assessment: All outcomes | Low risk | Low risk | yes | article_absence_or_unclear |  |
| Incomplete outcome data: All outcomes | Unclear risk | Low risk | no | figure_table_or_supplement_reference | figure_table_or_supplement_needed |

### Audit Details

#### Random sequence generation

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The text reports stratified random assignment of practices but provides no description of the random component or method (computer, random number table, minimization, etc.). According to the criteria, lack of details about how the sequence was generated requires an 'Unclear risk' judgement.
- Model support: Quote: "practices within each independent stratum were randomly assigned to 1 of 2 study arms (for 16 possible randomization combinations)." Comment: The report states practices were 'randomly assigned' within strata but does not describe the method used to generate the random sequence (eg, computer, random number table, coin toss).
- Model support context: [{"source": "article", "quote": "practices within each independent stratum were randomly assigned to 1 of 2 study arms", "relevance": "Describes that random assignment occurred but gives no details of the random sequence generation method."}, {"source": "article", "quote": "Practices were grouped in 4 mutually exclusive strata...and practices within each independent stratum were randomly assigned", "relevance": "Confirms stratified cluster randomization but does not report the random component or mechanism used to generate the sequence."}]
- GT support: Cluster‐randomisation, stratified block randomisation. It was not described how the random sequence was generated. “Practices were grouped in 4 mutually exclusive strata (women’s health practices, low‐income urban practices, large suburban practices, and smaller suburban practices), and practices within each independent stratum were randomly assigned to 1 of 2 study arms (for 16 possible randomisation combinations)” (p. 1778)
- Evidence row: {}
- Source context preview: ## Randomization Because this was a system-level intervention that involved patients, their physicians, and the clinical support staff at each practice, we randomized at the practice level. Practices were grouped in 4 mutually exclusive strata (women's health practices, low-income urban practices, large suburban practices, and smaller suburban practices), and practices within each independent stratum were randomly assigned to 1 of 2 study arms (for 16 possible randomization combinations). All primary and other clinical outcomes were collected directly from the electronic clinical data repository, and these data were obtained solely as part of usual clinical care. --- ## Intervention After...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The article states cluster randomization and that patients consented before notification, but it does not report methods of allocation concealment (central randomization, sealed envelopes, etc.), so insufficient detail prevents a Low or High risk judgment.
- Model support: Quote: "practices within each independent stratum were randomly assigned to 1 of 2 study arms (for 16 possible randomization combinations)." Comment: The report describes cluster randomization by practice and stratification, but gives no details on how the allocation sequence was concealed from those enrolling practices.
- Model support context: [{"source": "article", "quote": "practices within each independent stratum were randomly assigned to 1 of 2 study arms", "relevance": "Shows random assignment at practice level but does not describe concealment procedures."}, {"source": "article", "quote": "Informed consent was obtained from eligible patients prior to notification of practice randomization status.", "relevance": "Indicates patients consented before being told practice allocation but does not state how allocation was concealed from recruiters or practices."}]
- GT support: It was not reported whether allocation of treatment to clusters was concealed, but it seems that patients had been recruited before randomisation
- Evidence row: {}
- Source context preview: ## Randomization Because this was a system-level intervention that involved patients, their physicians, and the clinical support staff at each practice, we randomized at the practice level. Practices were grouped in 4 mutually exclusive strata (women's health practices, low-income urban practices, large suburban practices, and smaller suburban practices), and practices within each independent stratum were randomly assigned to 1 of 2 study arms (for 16 possible randomization combinations). All primary and other clinical outcomes were collected directly from the electronic clinical data repository, and these data were obtained solely as part of usual clinical care. --- ## Intervention After...

#### Blinding of participants and personnel: All outcomes

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The interventions were distinct PHR modules and participants would know which content they used; outcomes (patient satisfaction, compliance, knowledge) are subjective and likely influenced by lack of blinding, so risk of performance bias is high. Calibration: lack of blinding is plausible for this behavioral/lifestyle intervention, but the supplied evidence does not clearly show a material influence on the review-relevant outcomes.
- Model support: Quote: "Patients were unaware of their PHR assignment when consenting to enroll in the study." Comment: Participants were unaware at consent but then intervention involved clearly different PHR content (DM-specific vs family history PHR) so participants and personnel would know allocation when using the systems; outcomes like patient satisfaction, compliance and knowledge are subjective and likely influenced by lack of blinding. Comment: Calibration: lack of blinding is plausible for this behavioral/lifestyle intervention, but the supplied evidence does not clearly show a material influence on the review-relevant outcomes.
- Model support context: [{"source": "article", "quote": "f primary care practices randomized and the flow of patients with DM in each study arm. Use of the parent PG secure Web portal by patients with DM ranged from 7% to 14% of each practice population. Among patients with active PG accounts,...", "relevance": "Calibration: lack of blinding is plausible for this behavioral/lifestyle intervention, but the supplied evidence does not clearly show a material influence on..."}, {"source": "article", "quote": "Patients were unaware of their PHR assignment when consenting to enroll in the study.", "relevance": "Shows participants were initially blinded but does not indicate masking during intervention delivery."}]
- GT support: Objective outcomes Blinding of physicians not possible, patients were blinded, as the control group also gained access to new components of the patient portal “Patients were unaware of their PHR assignment when consenting to enrol in the study. Because both intervention and control groups used PG and received additional PHR modules, the primary distinction between the 2 study arms was the content of the modules“ (p. 1777) Unclear whether different performance influences HbA1c No further outcomes were reported
- Evidence row: {}
- Source context preview: ## Randomization Because this was a system-level intervention that involved patients, their physicians, and the clinical support staff at each practice, we randomized at the practice level. Practices were grouped in 4 mutually exclusive strata (women's health practices, low-income urban practices, large suburban practices, and smaller suburban practices), and practices within each independent stratum were randomly assigned to 1 of 2 study arms (for 16 possible randomization combinations). All primary and other clinical outcomes were collected directly from the electronic clinical data repository, and these data were obtained solely as part of usual clinical care. --- ## Intervention After...

#### Blinding of outcome assessment: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The review-relevant outcomes (HbA1c, blood pressure, LDL-C) are objective measurements extracted from electronic records; because these are unlikely to be influenced by knowledge of allocation, detection bias is judged low.
- Model support: Quote: "All primary and other clinical outcomes were collected directly from the electronic clinical data repository, and these data were obtained solely as part of usual clinical care." Comment: Outcomes (HbA1c, BP, LDL-C) were objective laboratory/physiologic measures retrieved from electronic records, unlikely to be influenced by assessor knowledge.
- Model support context: [{"source": "article", "quote": "All primary and other clinical outcomes were collected directly from the electronic clinical data repository, and these data were obtained solely as part of usual clinical care.", "relevance": "Shows outcome data source is objective EMR/lab measurements rather than subjective assessor ratings."}, {"source": "article", "quote": "The primary outcomes... HbA1c, blood pressure, and LDL-C", "relevance": "Identifies the review-relevant outcomes as objective lab/physiologic measures."}]
- GT support: Objective outcomes It was not reported whether personnel in the lab were blinded, but this routine lab test has probably a small risk for detection bias. No further outcomes were reported
- Evidence row: {}
- Source context preview: ## Comment Effective translation of new innovations into improved DM care remains a difficult challenge for current research efforts.28 The results of our study underscore a number of critical points for future work in this area. First, evaluating the impact of new technologies and new strategies for care requires a rigorous study design. Our use of an active control study design provided the advantage of allowing us to compare 2 groups of patients who were equally inclined to enroll in a clinical trial of Web-based PHR interventions. Thus, the comparison of primary outcomes between “active account” study arms reflects the impact of the DM PHR on clinical care among patients equally...

#### Incomplete outcome data: All outcomes

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: figure_table_or_supplement_reference (article observable: None)
- GT support phrase hits: 
- Model rationale: The excerpts indicate outcomes were EMR-derived and analyzed ITT, but do not report numbers randomized versus analyzed, missing outcome counts by arm, reasons for missing data, or how missing data were handled; therefore reporting is insufficient to assess attrition bias.
- Model support: Quote: "The primary outcomes for this study were changes from baseline in 3 key measures of DM management: HbA1c, blood pressure, and LDL-C, comparing all eligible patients with DM in the 2 study arms in an intention-to-treat analysis." Comment: Outcomes were collected from the EMR and analyzed by intention-to-treat, but the report excerpts do not give numbers randomized vs analyzed, nor missing outcome counts or reasons by arm, so attrition and handling cannot be judged.
- Model support context: [{"source": "article", "quote": "The primary outcomes... comparing all eligible patients with DM in the 2 study arms in an intention-to-treat analysis.", "relevance": "States outcome type and that ITT analysis was used but gives no missing-by-arm counts or handling details."}, {"source": "article", "quote": "Figure 1 illustrates the number of primary care practices randomized and the flow of patients with DM in each study arm.", "relevance": "Refers to participant flow figure, but that figure and numeric patient-level attrition details are not included in the supplied excerpts."}]
- GT support: Objective outcomes All patients were analysed, but no data show whether follow‐up was equally distributed over the different clusters (p. 1779, Table)
- Evidence row: {}
- Source context preview: ## Participant Flow Figure 1 illustrates the number of primary care practices randomized and the flow of patients with DM in each study arm. Use of the parent PG secure Web portal by patients with DM ranged from 7% to 14% of each practice population. Among patients with active PG accounts, the rate of consent to enroll in the advanced patient portal clinical trial was 39% in the DM PHR intervention arm and 35% in the family history and health maintenance PHR active control arm. Practices were enrolled beginning September 30, 2005, and follow-up ascertainment was completed when the study was formally closed March 22, 2007. --- ## Outcomes The primary outcomes for this study were changes from...


## 19209172 - Vodermaier 2009

- Mode: audited
- Review context: none (0 chars)
- Article chars: 35445
- Extraction context chars: n/a
- Total seconds: 48.15
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Unclear risk | Unclear risk | yes | no_support_phrase_match |  |
| Allocation concealment | Unclear risk | Low risk | no | unknown | under-called_due_to_missing_or_underused_evidence |
| Blinding of participants and personnel: All outcomes | High risk | Unclear risk | no | article_absence_or_unclear | over-inferred_from_sparse_reporting |
| Blinding of outcome assessment: All outcomes | High risk | Low risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |
| Incomplete outcome data: All outcomes | Unclear risk | Unclear risk | yes | no_support_phrase_match |  |

### Audit Details

#### Random sequence generation

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report states allocation used numbered cards in envelopes but does not specify a random component (computer, random table, drawing lots, etc.) or how the numbered list was produced; therefore information is insufficient to judge as low or high risk.
- Model support: Quote: "Random assignment was performed by means of numbered cards in envelopes for the intervention and the control group, and was stratified by age group (<, ⩾60 years)." Comment: numbered cards in envelopes are described but the method used to generate the sequence of those cards (eg, random number table, computer generator, or other) is not reported.
- Model support context: [{"source": "article", "quote": "Random assignment was performed by means of numbered cards in envelopes for the intervention and the control group, and was stratified by age group (<, ⩾60 years).", "relevance": "Describes the allocation implementation but does not state how the sequence/list of numbered cards was generated (random method unspecified)."}, {"source": "article", "quote": "Randomisation was conducted after the patient gave written informed consent to participate in the trial.", "relevance": "Confirms timing of randomisation but gives no detail on the random sequence generation process."}]
- GT support: “Randomisation after the patient gave written informed consent”; “Random assignment was performed by means of numbered cards in envelopes”; “stratified by age group” (p. 2)
- Evidence row: {}
- Source context preview: ## Procedure Staff doctors informed the two research psychologists (CC, JK) who recruited the patients about new patients who had entered the ward and who were eligible for the trial. Randomisation was conducted after the patient gave written informed consent to participate in the trial through the research staff. Random assignment was performed by means of numbered cards in envelopes for the intervention and the control group, and was stratified by age group (<, ⩾60 years). For participants of the intervention arm, the decision board intervention was provided by research psychologists who had previously recruited the patients. The intervention was conducted on the day the patients arrived...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: The report states allocation used numbered cards in envelopes but does not specify whether envelopes were opaque, sealed, sequentially numbered, or held independently; therefore there is insufficient information to determine whether recruiters could foresee assignments.
- Model support: Quote: "Random assignment was performed by means of numbered cards in envelopes for the intervention and the control group, and was stratified by age group (<, ⩾60 years)." Comment: Numbered cards in envelopes are described but no details on whether envelopes were opaque, sealed, sequentially numbered, or held independently, so concealment cannot be confirmed.
- Model support context: [{"source": "article", "quote": "Random assignment was performed by means of numbered cards in envelopes for the intervention and the control group, and was stratified by age group.", "relevance": "Describes the method used for allocation but lacks details about envelope safeguards needed to judge concealment."}, {"source": "article", "quote": "Randomisation was conducted after the patient gave written informed consent to participate in the trial through the research staff.", "relevance": "Indicates timing of randomisation (post-consent) but does not state who prepared or controlled the envelopes or whether recruiters could foresee allocations."}]
- GT support: “[N]umbered cards in envelopes” (p. 2)
- Evidence row: {}
- Source context preview: ## Procedure Staff doctors informed the two research psychologists (CC, JK) who recruited the patients about new patients who had entered the ward and who were eligible for the trial. Randomisation was conducted after the patient gave written informed consent to participate in the trial through the research staff. Random assignment was performed by means of numbered cards in envelopes for the intervention and the control group, and was stratified by age group (<, ⩾60 years). For participants of the intervention arm, the decision board intervention was provided by research psychologists who had previously recruited the patients. The intervention was conducted on the day the patients arrived...

#### Blinding of participants and personnel: All outcomes

- Prediction: High risk
- Ground truth: Unclear risk
- Match: False
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The trial explicitly states blinding was not possible and the intervention was an obvious decision aid (participant-visible); the review-relevant outcomes are patient-reported decision-making measures, so lack of blinding was likely to influence outcomes, supporting High risk.
- Model support: Quote: "Blinding was not possible within the hospital procedures. Nonetheless, in most cases physicians did not know in which arm patients had been randomised." Comment: Participants received a visible 20-min decision aid and brochure vs standard care, and personnel recruiting/intervening (research psychologists) delivered the intervention, so participants and some staff were unblinded and outcomes are patient-reported (decision making, decisional conflict), likely influenced by lack of blinding.
- Model support context: [{"source": "article", "quote": "Blinding was not possible within the hospital procedures.", "relevance": "Explicitly states that blinding could not be done for participants/personnel."}, {"source": "article", "quote": "the intervention group received a 20-min decision aid intervention and additional written information, whereas the control group received standard care.", "relevance": "Intervention was visibly different and outcomes are patient-reported decision-making measures likely influenced by knowledge of allocation."}]
- GT support: Not blinded ‐ unclear if this would introduce bias to outcome assessed
- Evidence row: {}
- Source context preview: ## Study design A two-arm, randomised controlled trial with decision aids vs standard treatment was conducted. Randomisation was conducted after the patient gave written informed consent to participate in the trial. Blinding was not possible within the hospital procedures. Nonetheless, in most cases physicians did not know in which arm patients had been randomised. Patients were assessed pre-randomisation (baseline) and at 1 week follow-up. The baseline questionnaire was filled out shortly after hospital admission and prior to randomisation. A few hours later, the intervention group received a 20-min decision aid intervention and additional written information, whereas the control group...

#### Blinding of outcome assessment: All outcomes

- Prediction: High risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The review-relevant outcomes include patient-reported satisfaction (subjective). The article states ratings were performed by research psychologists who were not blind and who delivered the intervention, so lack of blinding could have biased these subjective outcome assessments.
- Model support: Quote: "...ratings were not blind to the research psychologists who performed the intervention. This may have lead to social desirability with regard to the evaluation of the decision aid intervention..." Comment: Outcome assessment for patient-reported satisfaction was not blinded and assessors (research psychologists) knew allocation, likely influencing subjective outcomes.
- Model support context: [{"source": "article", "quote": "ratings were not blind to the research psychologists who performed the intervention.", "relevance": "States that outcome ratings were done by unblinded research psychologists involved in the intervention."}, {"source": "article", "quote": "Satisfaction with the decision making process and general patient satisfaction with care was high and did not differ between groups.", "relevance": "Identifies the outcome as patient satisfaction, a subjective measure likely influenced by unblinded assessment."}]
- GT support: Not blinded but outcomes were objectively measured and not subjective to interpretation
- Evidence row: {}
- Source context preview: ## Discussion Satisfaction with the decision making process and general patient satisfaction with care was high and did not differ between groups. Though physicians involved in the patients' treatment did not see patients' assessment of treatment satisfaction, ratings were not blind to the research psychologists who performed the intervention. This may have lead to social desirability with regard to the evaluation of the decision aid intervention but may have had little impact on ratings of satisfaction with treatment. Variance constriction because of a ceiling effect may have contributed to the lack of a group difference. Results are in line with other studies, which reported null effects...

#### Incomplete outcome data: All outcomes

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report provides total randomized (152) and analysed per arm (55,56) with specified exclusions (13,16) but lacks detailed information on other withdrawals, missing outcome counts at follow-up, reasons for non-response, and how missing data were handled (ITT/imputation). These missing details prevent judgment against Low or High risk.
- Model support: Quote: "152 participants were randomised to either the intervention or the control condition. The final sample was 111 patients, of whom 55 were randomly assigned to the intervention group and 56 to the control group. Here, 13 and 16 patients respectively were excluded from the analyses because of post hoc ascertainment of not having met the inclusion criteria (benign diagnosis, carcinoma in situ, Stage IV-tumour)." Comment: Although randomised/enrolled and analysed numbers by arm are reported and post-randomisation exclusions are described, the report does not give full details on all withdrawals, reasons by arm for other losses, or whether analyses used ITT or handling of missing outcome data, so risk of attrition bias cannot be judged.
- Model support context: [{"source": "article", "quote": "152 participants were randomised... The final sample was 111 patients, of whom 55... intervention and 56... control. 13 and 16 patients respectively were excluded from the analyses", "relevance": "Gives randomized and analysed counts by arm and numbers excluded post-randomisation."}, {"source": "article", "quote": "Patients were assessed pre-randomisation (baseline) and at 1 week follow-up... For completion of the follow-up, patients received a pre-paid envelope to send back the questionnaire.", "relevance": "Describes timing/method of outcome collection but does not report missing outcome counts, reasons for other losses, or analysis approach."}]
- GT support: Flow diagram, p. 5; baseline characteristics not included
- Evidence row: {}
- Source context preview: ## Trial retention Between May 2003 and October 2004 we invited 246 patients to participate, of whom 94 declined (uptake rate of 62.6%). Patient accrual according to the Consort guidelines is presented in Figure 1. The major reasons for declining study participation were preoperative distress associated with filling out a questionnaire shortly after admission (70%), general refusal to fill out questionnaires (10%), involvement in another study therefore not wanting to participate in an additional study (2%), first agreed to participate, but refused after reviewing the questionnaire (4%) or were ineligible because of missing diagnostic findings, outstanding examinations, or preoperative...


## 19291323 - Middleton 2011

- Mode: audited
- Review context: none (0 chars)
- Article chars: 29453
- Extraction context chars: n/a
- Total seconds: 46.34
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Low risk | yes | no_support_phrase_match |  |
| Allocation concealment | Low risk | Low risk | yes | no_support_phrase_match |  |
| Blinding of participants and personnel: All outcomes | Low risk | High risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |
| Blinding of outcome assessment: All outcomes | Unclear risk | Low risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |
| Incomplete outcome data: All outcomes | Unclear risk | Low risk | no | figure_table_or_supplement_reference | figure_table_or_supplement_needed |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report states allocation was generated using random number generating software by an independent statistician, which describes a random component (computer-generated sequence) meeting Low risk criteria.
- Model support: Quote: "stratification details... will be provided in a de-identified form to an independent statistician located offshore and not otherwise involved in the study for randomisation within strata, this will be generated using random number generating software[29]." Comment: Sequence generation used random number generating software by an independent statistician.
- Model support context: [{"source": "article", "quote": "this will be generated using random number generating software", "relevance": "Explicit random component (computer random number generator) for sequence generation"}, {"source": "article", "quote": "stratification details... provided to an independent statistician located offshore... for randomisation within strata", "relevance": "Independent statistician performed the randomisation, supporting proper sequence generation"}]
- GT support: "ASUs were stratified by category (category A or B) and then by absolute numbers of pre-intervention cohort patients recruited (high or low recruiters). High recruiters had consented more than two patients per month; low recruiters two or fewer per month. De-identified stratification details were provided to an independent statistician who used random number generating software to randomise withinstrata with allocation concealed until provided to the Project Officer who assigned ASUs to their groups."
- Evidence row: {}
- Source context preview: ## Hypotheses Once the baseline patient cohort 90-day outcome data have been collected, participating ASUs will be stratified and randomised. The project officer (SD) will first stratify ASUs according to their category classification (A or B) and then, by referring to absolute numbers of patients recruited at baseline, describe each as a 'high recruiter' or 'low recruiter'. Recruitment numbers will be included as a randomisation strata to maximise the chance of similar sample size in the intervention and control groups. Stratification details will be provided in a de-identified form to an independent statistician located offshore and not otherwise involved in the study for randomisation...

#### Allocation concealment

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: An independent offshore statistician both generated and assigned allocations using random number software, a centralised process that prevents investigators enrolling clusters from foreseeing upcoming allocations and meets criteria for adequate concealment.
- Model support: Quote: "Stratification details will be provided in a de-identified form to an independent statistician located offshore and not otherwise involved in the study for randomisation within strata, this will be generated using random number generating software. ... generation of the allocation sequence and assigning of ASUs to either intervention or control group will be undertaken by the offshore independent statistician." Comment: An independent offshore statistician generated the sequence and undertook assignment, preventing recruiters from foreseeing allocations.
- Model support context: [{"source": "article", "quote": "stratification details will be provided in a de-identified form to an independent statistician located offshore ... generated using random number generating software", "relevance": "Shows sequence generation by an independent external statistician using random software."}, {"source": "article", "quote": "generation of the allocation sequence and assigning of ASUs to either intervention or control group will be undertaken by the offshore independent statistician", "relevance": "Indicates assignment was performed remotely by an independent party, preventing foreknowledge by recruiters."}]
- GT support: "De-identified stratification details were provided to an independent statistician who used random number generating software to randomise within strata with allocation concealed until provided to the Project Officer who assigned ASUs to their groups."
- Evidence row: {}
- Source context preview: ## Hypotheses Once the baseline patient cohort 90-day outcome data have been collected, participating ASUs will be stratified and randomised. The project officer (SD) will first stratify ASUs according to their category classification (A or B) and then, by referring to absolute numbers of patients recruited at baseline, describe each as a 'high recruiter' or 'low recruiter'. Recruitment numbers will be included as a randomisation strata to maximise the chance of similar sample size in the intervention and control groups. Stratification details will be provided in a de-identified form to an independent statistician located offshore and not otherwise involved in the study for randomisation...

#### Blinding of participants and personnel: All outcomes

- Prediction: Low risk
- Ground truth: High risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The protocol explicitly states that patients and CATI research interviewers (who collect the 90-day patient-level outcomes) will be blind to allocation, so lack of blinding is unlikely to have influenced the review-relevant healthcare quality assessment outcomes.
- Model support: Quote: "Patients will be blinded to group allocation. Data entry will be undertaken by the CATI research assistants blind to group allocation." Comment: Patients (outcome reporters for CATI-based 90-day healthcare quality outcomes) and CATI interviewers are stated as blinded, making performance bias unlikely.
- Model support context: [{"source": "article", "quote": "Patients will be blinded to group allocation.", "relevance": "Participant blinding for patient-reported 90-day outcomes reduces risk that knowledge of allocation influenced responses."}, {"source": "article", "quote": "All CATIs will be undertaken by research interviewers blind to the study design and also to ASU group allocation", "relevance": "Outcome assessors (CATI interviewers/data entry) were blinded, lowering the chance of performance bias in outcome collection."}]
- GT support: "Clinical research assistants [personnel] masked to trial design enrolled patients. Patients were masked to ASU group allocation but clinicians delivering our intervention were not."
- Evidence row: {}
- Source context preview: ## Hypotheses Once the baseline patient cohort 90-day outcome data have been collected, participating ASUs will be stratified and randomised. The project officer (SD) will first stratify ASUs according to their category classification (A or B) and then, by referring to absolute numbers of patients recruited at baseline, describe each as a 'high recruiter' or 'low recruiter'. Recruitment numbers will be included as a randomisation strata to maximise the chance of similar sample size in the intervention and control groups. Stratification details will be provided in a de-identified form to an independent statistician located offshore and not otherwise involved in the study for randomisation...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly states that outcome assessment is blinded for all primary and secondary measures and that CATI interviewers (assessors of patient-reported outcomes like SF-36 and mRS by telephone) are blind to allocation, making detection bias unlikely. Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support: Quote: "Blinded outcome assessment will be undertaken for all analyses of primary and secondary outcome measures." Comment: Outcome assessment was explicitly planned to be blinded for all primary and secondary outcomes. Comment: Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support context: [{"source": "article", "quote": "measures 4. Health status 90 days post-hospital admission using the Medical Outcomes Study Short Form 36 Health Survey Questionnaire (SF-36) [45]. The SF-36 includes a single 'health transition rating' and scores eight health domains which...", "relevance": "Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported."}, {"source": "article", "quote": "Blinded outcome assessment will be undertaken for all analyses of primary and secondary outcome measures.", "relevance": "States that outcome assessment will be blinded for all primary and secondary outcomes, supporting low detection bias."}]
- GT support: "Research assistants who undertook the computer-assisted telephone interviews and the medical record audits were masked to trial aims, design, and group allocation; the trial statistician was masked to group allocation [outcome assessors]."
- Evidence row: {}
- Source context preview: ## Hypotheses Once the baseline patient cohort 90-day outcome data have been collected, participating ASUs will be stratified and randomised. The project officer (SD) will first stratify ASUs according to their category classification (A or B) and then, by referring to absolute numbers of patients recruited at baseline, describe each as a 'high recruiter' or 'low recruiter'. Recruitment numbers will be included as a randomisation strata to maximise the chance of similar sample size in the intervention and control groups. Stratification details will be provided in a de-identified form to an independent statistician located offshore and not otherwise involved in the study for randomisation...

#### Incomplete outcome data: All outcomes

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: figure_table_or_supplement_reference (article observable: None)
- GT support phrase hits: 
- Model rationale: The provided excerpts are from the study protocol and describe expected loss and plans to retrieve missing data, but they do not report actual numbers randomized, analyzed, missing by arm, reasons for missingness, or handling of observed missing outcome data; therefore there is insufficient information to judge risk of attrition bias.
- Model support: Quote: "Assuming a loss to follow-up of 10%, an effective sample size of 280 participants per group is required to be recruited." Comment: The protocol anticipates and plans for loss to follow-up but does not report actual numbers randomized, analyzed, missing by arm, reasons for missingness, or how missing outcome data were handled in the results.
- Model support context: [{"source": "article", "quote": "Assuming a loss to follow-up of 10%, an effective sample size of 280 participants per group is required to be recruited.", "relevance": "States assumed attrition in sample size calculation but gives no observed missing data counts or reasons."}, {"source": "article", "quote": "For missing data, patient clinical data will be obtained from the TASC database.", "relevance": "Describes a plan to obtain missing clinical data but does not report whether this succeeded or provide missingness by arm."}]
- GT support: "Of the 1861 eligible QASC consenting patients across the entire study period, medical records were unavailable for 57 patients (3·6%) [17 (2·4%) from the preintervention cohort and 40 (3·7%) from the postintervention cohort] resulting in collection of data for 1804 patients. No data missing, pre-determined outcomes were assessed." Participant drop out explained in figure 2. Less than 20% drop out rate in each intervention is low risk of bias.
- Evidence row: {}
- Source context preview: ## Background In our study, we will develop, implement, and rigorously evaluate a multidisciplinary team-building intervention in ASUs. Our intervention is designed to improve outcomes for patients admitted with acute stroke by better management of fever, hyperglycaemia, and swallowing dysfunction as recommended by evidence-based guidelines. This intervention will comprise replicable steps to identify local barriers and enablers, unit-based education, feedback, and ongoing proactive support. As we are focussing on fever, hyperglycaemia ('sugar'), and swallowing dysfunction, our intervention is known as the 'FeSS' intervention. Because the team-building intervention can only be delivered at...


## 19319218 - Chien 2008a

- Mode: audited
- Review context: none (0 chars)
- Article chars: 46815
- Extraction context chars: n/a
- Total seconds: 44.32
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Low risk | yes | no_support_phrase_match |  |
| Allocation concealment | Low risk | Low risk | yes | article_text_match |  |
| Blinding of participants and personnel: All outcomes | High risk | High risk | yes | no_support_phrase_match |  |
| Blinding of outcome assessment: All outcomes | High risk | Low risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |
| Incomplete outcome data: All outcomes | Low risk | Low risk | yes | no_support_phrase_match |  |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly states use of a computer-generated random numbers table for selection/allocation, which is a valid random method per the Low risk criteria.
- Model support: Quote: "They were then selected randomly from the patient list, using a computer-generated random numbers table." Comment: This describes a random component (computer-generated random numbers table) meeting Low risk criteria.
- Model support context: [{"source": "article", "quote": "They were then selected randomly from the patient list, using a computer-generated random numbers table.", "relevance": "Explicit description of a computer-generated random numbers table for sequence generation."}, {"source": "article", "quote": "64 families signed an informed written consent and voluntarily participated in the study. They were then randomly assigned to one of the two groups in this study", "relevance": "Confirms participants were randomly assigned; supports that random selection/allocation occurred."}]
- GT support: Quote: "the participants were then asked by the principal researcher to draw a sealed opaque envelope, in which a number card indicated to which group they had been allocated (1 = psycho-education group and 2 = routine care group)." Comment: simple randomisation
- Evidence row: {}
- Source context preview: ## Sample & Study Settings Exclusion criteria included those who cared for more than one family member with mental illness, who themselves had mental illness, and who were the primary carers for less than three months. Those eligible were listed in alphabetical order by surname. They were then selected randomly from the patient list, using a computer-generated random numbers table. --- ## METHODS A repeated measures design was used to compare two groups of family caregivers of patients with schizophrenia: a psycho-education and support group and a standard care (conventional psychiatric outpatient care) group. This study was undertaken between January 2005 and September 2006. Analysis of...

#### Allocation concealment

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: the participants were then asked by the principal researcher to draw a sealed opaque envelope
- Model rationale: The report states participants drew sealed opaque envelopes indicating group assignment, which is an accepted method (sequentially numbered, opaque, sealed envelopes) preventing foreknowledge by recruiters; therefore allocation concealment is Low risk.
- Model support: Quote: "the participants were then asked by the principal researcher to draw a sealed opaque envelope, in which a number card indicated to which group they had been allocated (1 = psycho-education group and 2 = routine care group)." Comment: Use of sealed opaque envelopes drawn by participants prevents recruiters from foreseeing assignments.
- Model support context: [{"source": "article", "quote": "the participants were then asked by the principal researcher to draw a sealed opaque envelope, in which a number card indicated to which group they had been allocated", "relevance": "Describes allocation via sealed opaque envelopes, an adequate concealment method per criteria."}, {"source": "article", "quote": "Except for the principal researcher and the group instructor, all other clinic staffs were blinded to treatment allocation.", "relevance": "Indicates personnel enrolling participants were not generally aware of assignments, supporting concealment."}]
- GT support: Quote: "the participants were then asked by the principal researcher to draw a sealed opaque envelope"
- Evidence row: {}
- Source context preview: ## Data Collection Enrolment, allocation, treatments, measures, and analyses of data from the study subjects are summarized in a flow diagram (Fig. 1), according to the revised version of CONSORT statements [39]. A trained psychiatric nurse (group instructor) approached the patients in person during follow-up appointment to seek written consent for voluntary participation in this study and permission to approach their family members. With the patient’s permission, one family member who was the primary caregiver of the patient was contacted by telephone to explain the purpose and procedure of the study and to invite his/her participation in the study. Written consent was obtained in a...

#### Blinding of participants and personnel: All outcomes

- Prediction: High risk
- Ground truth: High risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: Participants and the key interventionist were unblinded and the interventions are visibly different; several review outcomes (quality of life, relapse, stress, patient compliance) are subjective and likely influenced by lack of blinding, so performance bias is high.
- Model support: Quote: "the participants were then asked by the principal researcher to draw a sealed opaque envelope, in which a number card indicated to which group they had been allocated (1 = psycho-education group and 2 = routine care group). Except for the principal researcher and the group instructor, all other clinic staffs were blinded to treatment allocation." Comment: Participants and the group instructor (key personnel delivering the intervention) were aware of allocation, and interventions (psycho-education group vs routine care) are visibly different, so lack of blinding was likely to influence review-relevant subjective outcomes such as quality of life, relapse reporting, stress and patient compliance.
- Model support context: [{"source": "article", "quote": "the participants were then asked by the principal researcher to draw a sealed opaque envelope, in which a number card indicated to which group they had been allocated", "relevance": "Shows allocation was revealed to participants at enrolment and that participants knew their group."}, {"source": "article", "quote": "Except for the principal researcher and the group instructor, all other clinic staffs were blinded to treatment allocation.", "relevance": "Indicates the group instructor (key personnel) was not blinded, so personnel delivering the intervention knew allocation."}]
- GT support: Quote: "Except for the principal researcher and the group instructor, all other clinic staffs were blinded to treatment allocation."
- Evidence row: {}
- Source context preview: ## METHODS A repeated measures design was used to compare two groups of family caregivers of patients with schizophrenia: a psycho-education and support group and a standard care (conventional psychiatric outpatient care) group. This study was undertaken between January 2005 and September 2006. Analysis of data was on an intention-to-treat basis [35]. All subjects, who completed the intervention or not, were followed up over a 12-month post-intervention period. They were selected randomly from two regional outpatient clinics in Hong Kong, consisting of about 1,800 patients with schizophrenia or its subtypes, representing 12% of this type of patients in Hong Kong [36]. --- ## Models of...

#### Blinding of outcome assessment: All outcomes

- Prediction: High risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: Subjective caregiver-reported outcomes were central and participants likely knew allocation; assessor blinding at outcome collection is not clearly reported, so knowledge of allocation could have influenced measurement, leading to High risk. Audited override: self-reported outcome with clearly unmasked participants and material influence on measurement.
- Model support: Quote: 'Except for the principal researcher and the group instructor, all other clinic staffs were blinded to treatment allocation. An independent assessor (a research assistant) was trained to undertake measurements at Time 1, 2 and 3.' Comment: Caregiver-reported subjective scales were used and caregivers likely knew group allocation (they drew envelopes/participated in intervention), and it is not stated that the independent assessor was blinded during collection or that self-reports were collected blind, so detection bias is likely. Comment: Audited override: self-reported outcome with clearly unmasked participants and material influence on measurement.
- Model support context: [{"source": "article", "quote": "participants were then asked by the principal researcher to draw a sealed opaque envelope, in which a number card indicated to which group they had been allocated", "relevance": "Shows participants likely became aware of allocation, relevant because many outcomes are self-reported."}, {"source": "article", "quote": "An independent assessor (a research assistant) was trained to undertake measurements at Time 1, 2 and 3", "relevance": "States an assessor collected measurements but does not state they were blinded, leaving risk of biased outcome assessment."}]
- GT support: Quote: "An independent assessor (a research assistant) was trained to undertake measurements at Time 1, 2 and 3 using a set of questionnaires."
- Evidence row: {}
- Source context preview: ## Study Rationale This study sought to test and compare the effectiveness between two modes of community-based interventions, namely: (i) a family psychoeducation and mutual support group and (ii) the conventional psychiatric outpatient care (routine care group) for family caregivers of people with schizophrenia in a Chinese population. The two groups were compared prior to (Time 1), one month later (Time 2) and 12 months after the intervention (Time 3), and multiple outcome measures for families and patients were used to assess treatment effects. The main hypothesis was that the psychoeducation and support group intervention would significantly reduce schizophrenic patients’ psychosocial...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: Reported attrition was small (3 vs 2), reasons for dropout were provided and similar, and analysis was intention-to-treat, meeting criteria for low risk due to balanced, unlikely-to-bias missing outcome data.
- Model support: Quote: "Thirty-one subjects (91.2%) from the mutual psychoeducation and support group completed the program. These subjects, together with those who dropped out or absented in more than four group sessions - psycho-education group (n = 3) and routine care group (n = 2), were evaluated at three times of outcome measurements." Comment: Attrition was very low and similar across groups with reasons reported and analysis was by intention-to-treat.
- Model support context: [{"source": "article", "quote": "Thirty-one subjects (91.2%) from the mutual psychoeducation and support group completed the program... psycho-education group (n = 3) and routine care group (n = 2), were evaluated at three times of outcome measurements.", "relevance": "Reports numbers completing and dropouts by arm and indicates low, balanced attrition."}, {"source": "article", "quote": "Analysis of data was on an intention-to-treat basis.", "relevance": "States that analyses included all randomized subjects, addressing handling of missing data."}]
- GT support: Comment: study attrition reported, with similar number and reasons for dropouts shown in the flow chart
- Evidence row: {}
- Source context preview: ## Sample Characteristics Thirty-one subjects (91.2%) from the mutual psychoeducation and support group completed the program. These subjects, together with those who dropped out or absented in more than four group sessions - psycho-education group (n = 3) and routine care group (n = 2), were evaluated at three times of outcome measurements. Reasons for dropout or discontinuation from the group interventions were mainly: insufficient time to attend (n = 2), patient’s mental state worsened (n = 3), not interested (n = 2), and the only person taking care of patient (n = 2). --- ## Strengths and Limitations of the Study Strengths in the design of the study include: (a) randomized treatment...


## 19487623 - King 2009

- Mode: audited
- Review context: none (0 chars)
- Article chars: 24566
- Extraction context chars: n/a
- Total seconds: 48.01
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Unclear risk | no | article_text_match | over-inferred_from_sparse_reporting |
| Allocation concealment | Unclear risk | Unclear risk | yes | article_absence_or_unclear |  |
| Blinding of participants and personnel: All outcomes | Low risk | Low risk | yes | article_text_match |  |
| Blinding of outcome assessment: All outcomes | High risk | Low risk | no | article_text_match | blinding_outcome_type_or_role_confusion |
| Incomplete outcome data: All outcomes | Low risk | Unclear risk | no | external_or_review_context | external_or_review_context_needed |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Unclear risk
- Match: False
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: placebo using permuted blocks with randomly | using permuted blocks with randomly varying | permuted blocks with randomly varying block | blocks with randomly varying block sizes | with randomly varying block sizes stratified
- Model rationale: The report explicitly states use of permuted blocks with randomly varying block sizes, which is a valid random sequence generation method (random component), therefore Low risk for selection bias from sequence generation.
- Model support: Quote: "Participants were randomly assigned to citalopram or placebo using permuted blocks with randomly varying block sizes stratified by site and by age (5-11 vs 12-17 years)." Comment: The sequence generation describes a random component (permuted blocks with randomly varying block sizes), meeting Low risk criteria.
- Model support context: [{"source": "article", "quote": "Participants were randomly assigned to citalopram or placebo using permuted blocks with randomly varying block sizes stratified by site and by age (5-11 vs 12-17 years).", "relevance": "Describes a random component (permuted blocks with randomly varying block sizes), indicating adequate random sequence generation."}, {"source": "article", "quote": "Two hundred forty-four of 331 participants screened... Consent was obtained for 175 subjects, and 149 were randomized to receive citalopram (n=73) or placebo (n=76).", "relevance": "Shows numbers randomized by arm, consistent with a randomized allocation process."}]
- GT support: Participants were randomly assigned to citalopram or placebo using permuted blocks with randomly varying block sizes stratified by site and by age (5-11 vs 12-17 years)
- Evidence row: {}
- Source context preview: ## Randomization and Blinding Participants were randomly assigned to citalopram or placebo using permuted blocks with randomly varying block sizes stratified by site and by age (5-11 vs 12-17 years). Two masked clinicians met with participants during each scheduled evaluation. The evaluating clinician monitored efficacy and was blinded to adverse events. The treating clinician reviewed efficacy ratings, monitored and recorded adverse events, and subsequently adjusted the medication dosage as clinically indicated. --- ## Methods The trial, NCT00086645, was registered at clinicaltrials.gov before initiation and was conducted at the following 6 academic medical centers: Mount Sinai School of...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The report gives details on sequence generation (permuted blocks) but omits any description of allocation concealment (central randomization, sealed envelopes, or pharmacy control of assignment). Because concealment details are not reported, risk is Unclear.
- Model support: Quote: "Participants were randomly assigned to citalopram or placebo using permuted blocks with randomly varying block sizes stratified by site and by age (5-11 vs 12-17 years)." Comment: The method of sequence generation is described, but the report does not state how the allocation sequence was concealed from recruiters (eg, central randomization, sealed opaque envelopes, or pharmacy control).
- Model support context: [{"source": "article", "quote": "Participants were randomly assigned to citalopram or placebo using permuted blocks with randomly varying block sizes stratified by site and by age (5-11 vs 12-17 years).", "relevance": "Describes randomization method but gives no information about concealment or who held/implemented the allocation."}, {"source": "article", "quote": "Placebo matched for smell, taste, and viscosity was prepared at each site's pharmacy according to study specifications.", "relevance": "Indicates site pharmacies prepared placebo but does not state whether pharmacy-controlled or central allocation concealed assignments."}]
- GT support: Details not provided
- Evidence row: {}
- Source context preview: ## Methods The trial, NCT00086645, was registered at clinicaltrials.gov before initiation and was conducted at the following 6 academic medical centers: Mount Sinai School of Medicine, New York, New York; North Shore–Long Island Jewish Health System, New York; University of North Carolina at Chapel Hill; University of California at Los Angeles; Yale University, New Haven, Connecticut; and Dartmouth Medical School, Hanover, New Hampshire. Each site's institutional review board approved the study. At least 1 parent or guardian for each participant provided written informed consent, and subjects who were capable provided assent. The National Institute of Mental Health convened a Data and...

#### Blinding of participants and personnel: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: during each scheduled evaluation
- Model rationale: A placebo-controlled design with masked evaluating clinicians assessing efficacy (CGI-I and other scales) and separation from treating clinicians indicates blinding of participants/personnel relevant to outcome measurement, making bias unlikely.
- Model support: Quote: "Participants were randomly assigned to citalopram or placebo... Two masked clinicians met with participants during each scheduled evaluation. The evaluating clinician monitored efficacy and was blinded to adverse events." Comment: Trial used placebo control and masked clinicians for evaluations, so participants and key personnel involved in outcome assessment were blinded and outcomes (CGI-I, CYBOCS-PDD, ABC irritability) were unlikely to be influenced by lack of blinding.
- Model support context: [{"source": "article", "quote": "Participants were randomly assigned to citalopram or placebo... Two masked clinicians met with participants during each scheduled evaluation.", "relevance": "Indicates placebo control and that clinicians evaluating outcomes were masked, supporting participant/personnel blinding for outcome assessment."}, {"source": "article", "quote": "The evaluating clinician monitored efficacy and was blinded to adverse events. The treating clinician reviewed efficacy ratings, monitored and recorded adverse events, and subsequently adjusted the medication dosage.", "relevance": "Shows separation of blinded outcome evaluation from treating clinician, reducing risk that knowledge of allocation influenced measured outcomes."}]
- GT support: Two masked clinicians met with participants during each scheduled evaluation
- Evidence row: {}
- Source context preview: ## Randomization and Blinding Participants were randomly assigned to citalopram or placebo using permuted blocks with randomly varying block sizes stratified by site and by age (5-11 vs 12-17 years). Two masked clinicians met with participants during each scheduled evaluation. The evaluating clinician monitored efficacy and was blinded to adverse events. The treating clinician reviewed efficacy ratings, monitored and recorded adverse events, and subsequently adjusted the medication dosage as clinically indicated. --- ## Methods The trial, NCT00086645, was registered at clinicaltrials.gov before initiation and was conducted at the following 6 academic medical centers: Mount Sinai School of...

#### Blinding of outcome assessment: All outcomes

- Prediction: High risk
- Ground truth: Low risk
- Match: False
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: evaluating clinician monitored efficacy
- Model rationale: Primary outcomes (CGI-I, CYBOCS-PDD) were clinician-rated and the report states the evaluating clinician was masked, indicating blinding of outcome assessment and making it unlikely that assessment was influenced by knowledge of allocation. Calibration: the outcome appears self-reported/subjective and participants could know allocation, so participants were unmasked outcome assessors.
- Model support: Quote: "Two masked clinicians met with participants during each scheduled evaluation. The evaluating clinician monitored efficacy and was blinded to adverse events." Comment: The primary and key secondary outcomes (CGI-I and CYBOCS-PDD) were clinician-rated and the evaluating clinician was explicitly masked, so outcome assessment was blinded. Comment: Calibration: the outcome appears self-reported/subjective and participants could know allocation, so participants were unmasked outcome assessors.
- Model support context: [{"source": "article", "quote": "el and clinical response. The mean maximum dosage achieved, 16.5 mg/d, is similar to dosages identified as effective in open-label studies of ASDs.18,19 In the open-label study of escitalopram by Owley et al,32 40% of responders were...", "relevance": "Calibration: the outcome appears self-reported/subjective and participants could know allocation, so participants were unmasked outcome assessors."}, {"source": "article", "quote": "The primary outcome measure was the CGI-I rated by the evaluating clinician.", "relevance": "Identifies the review-relevant outcomes as clinician-rated (not self-report)."}]
- GT support: The evaluating clinician monitored efficacy and was blinded to AEs
- Evidence row: {}
- Source context preview: ## Efficacy Measures The primary outcome measure was the CGI-I rated by the evaluating clinician. The CGI-I is a subscale scored from 1 (very much improved) to 7 (very much worse).23 A score of 4 reflects no change. Positive response was defined by a score of 2 (much improved) or (very much improved) at week 12. The following 8 secondary outcomes were evaluated: the CYBOCS-PDD, a composite measure of the CGI-I and the CYBOCS-PDD (CGI-I score of 1 or 2 and a 25% reduction on the CYBOCS-PDD), and 6 subscales of the Repetitive Behavior Scale. The CYBOCS-PDD, which was rated by the evaluating clinician, is designed to measure the severity of repetitive behavior in children with ASDs.22 The 5...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Unclear risk
- Match: False
- GT observability: external_or_review_context (article observable: False)
- GT support phrase hits: 
- Model rationale: Randomized counts and per-arm attrition are reported (73 vs 76; completion 82.6%). Missingness is moderate, balanced in numbers and reasons across arms, and analyses used LOCF with consistent complete-case results, making bias from incomplete outcome data unlikely.
- Model support: Quote: "149 were randomized to receive citalopram (n=73) or placebo (n=76). Most participants (82.6%) completed the 12-week trial. In the citalopram-treated group, 12.3% stopped early due to adverse events and another 2.7% withdrew consent; in the placebo group, 9.2% left early owing to adverse events and another 6.6% withdrew consent... For subjects who failed to complete all postrandomization assessments, the last observation was carried forward." Comment: Attrition was moderate (about 17.4% overall), balanced across arms with similar reasons, and handled with LOCF plus complete-case analyses that gave consistent results.
- Model support context: [{"source": "article", "quote": "149 were randomized to receive citalopram (n=73) or placebo (n=76). Most participants (82.6%) completed the 12-week trial.", "relevance": "Provides randomized numbers by arm and overall completion rate, showing modest attrition."}, {"source": "article", "quote": "In the citalopram-treated group, 12.3% stopped early due to adverse events and another 2.7% withdrew consent; in the placebo group, 9.2% left early owing to adverse events and another 6.6% withdrew consent... last observation was carried...", "relevance": "Gives per-arm missingness, reasons (adverse events/withdrawal) that are similar across groups and describes imputation method."}]
- GT support: LTFU citalopram: 13 withdrew, 1 due to serious AE; 8 AEs; 2 protocol violations; 2 consent withdrawn LTFU placebo: 13 withdrawn, 7 AEs; 1 protocol violation; 5 consent withdrawn
- Evidence row: {}
- Source context preview: ## Results Two hundred forty-four of 331 participants screened by telephone were presumed eligible and were invited for a screening visit. Consent was obtained for 175 subjects, and 149 were randomized to receive citalopram (n=73) or placebo (n=76). Most participants (82.6%) completed the 12-week trial. In the citalopram-treated group, 12.3% stopped early due to adverse events and another 2.7% withdrew consent; in the placebo group, 9.2% left early owing to adverse events and another 6.6% withdrew consent (Figure 1). The citalopram-treated and placebo groups were balanced in terms of demographic and baseline characteristics, including age, sex, race/ethnicity, nonverbal IQ, Tanner stage,...


## 19798037 - Nidich 2009

- Mode: audited
- Review context: none (0 chars)
- Article chars: 21001
- Extraction context chars: n/a
- Total seconds: 45.29
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Unclear risk | Low risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |
| Allocation concealment | Low risk | Unclear risk | no | article_text_match | over-inferred_from_sparse_reporting |
| Blinding of participants and personnel: All outcomes | High risk | Unclear risk | no | article_absence_or_unclear | over-inferred_from_sparse_reporting |
| Blinding of outcome assessment: All outcomes | Low risk | Low risk | yes | no_support_phrase_match |  |
| Incomplete outcome data: All outcomes | Unclear risk | High risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |

### Audit Details

#### Random sequence generation

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report states 'random blocks method' with stratification, but does not describe the random component (e.g., computer generator, random number table). Because the mechanism used to generate the sequence is not specified, there is insufficient information to judge Low risk.
- Model support: Quote: "Students were then randomized to experimental or control groups, using the random blocks method21 stratifying on gender (male/female) and self-reported attention deficit hyperactivity disorder status (yes, no)..." Comment: Random blocks and stratification are mentioned but the report does not state how the random blocks were generated (computer, random number table, etc.), so sequence generation method is not sufficiently described to be judged Low risk.
- Model support context: [{"source": "article", "quote": "Students were then randomized to experimental or control groups, using the random blocks method21 stratifying on gender...and self-reported attention deficit hyperactivity disorder status...", "relevance": "Describes use of block randomization and stratification but does not specify the random component or method used to generate the sequence."}, {"source": "article", "quote": "The treatment group allocations were concealed by the study statistician, with individual treatment group assignments revealed to the project manager only when study participants completed baseline testing.", "relevance": "Describes allocation concealment process but does not clarify how the random sequence itself was generated."}]
- GT support: Students were randomised to experimental or control groups, using the random blocks method, stratifying on gender.
- Evidence row: {}
- Source context preview: ## Study protocol Students were then randomized to experimental or control groups, using the random blocks method21 stratifying on gender (male/female) and self-reported attention deficit hyperactivity disorder status (yes, no), to either (a) immediate instruction in the TM program or (b) wait list/delayed start condition. (The attention deficit hyperactivity disorder stratification was for the purpose of a separate substudy.) --- ## Statistical methods Differences between the treatment groups on demographic and baseline variables was examined using t-tests for continuous variables and χ2-tests for categorical variables, and by multivariate analysis of variance to assess multivariate...

#### Allocation concealment

- Prediction: Low risk
- Ground truth: Unclear risk
- Match: False
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: with individual treatment group assignments revealed
- Model rationale: A central concealment process was used: the statistician held allocations and only revealed assignments after baseline testing, fitting the criterion for Low risk because enrolling investigators could not foresee or influence assignments.
- Model support: Quote: "The treatment group allocations were concealed by the study statistician, with individual treatment group assignments revealed to the project manager only when study participants completed baseline testing." Comment: Allocation was kept by the statistician and assignments were only revealed after baseline, preventing recruiters from foreseeing allocations.
- Model support context: [{"source": "article", "quote": "The treatment group allocations were concealed by the study statistician, with individual treatment group assignments revealed to the project manager only when study participants completed baseline testing.", "relevance": "States that allocations were concealed centrally by the statistician and revealed only after baseline, preventing foreseeability by enrolling staff."}, {"source": "article", "quote": "Students were then randomized to experimental or control groups, using the random blocks method stratifying on gender...", "relevance": "Describes randomization method (blocked, stratified), supporting that a formal allocation list existed and was managed centrally."}]
- GT support: The treatment group allocations were concealed by the study statistician, with individual treatment group assignments revealed to the project manager only when study participants completed baseline testing.
- Evidence row: {}
- Source context preview: ## Study protocol The treatment group allocations were concealed by the study statistician, with individual treatment group assignments revealed to the project manager only when study participants completed baseline testing. Subjects were post-tested after ~3 months. All assessments were administered by research staff who were masked to treatment condition. Thus, this was a single-blind design. After post-test evaluation, wait-list participants were offered TM instruction. --- ## Statistical methods Differences between the treatment groups on demographic and baseline variables was examined using t-tests for continuous variables and χ2-tests for categorical variables, and by multivariate...

#### Blinding of participants and personnel: All outcomes

- Prediction: High risk
- Ground truth: Unclear risk
- Match: False
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The report explicitly states a single-blind design with assessors masked but participants received obvious different interventions (immediate TM training vs wait-list). Review-relevant outcomes include subjective measures (psychological distress, coping, quality of life) and blood pressure which can be influenced by participant/personnel expectations; therefore risk of performance bias is high.
- Model support: Quote: "Thus, this was a single-blind design." Comment: Participants and intervention instructors were not blinded (wait-list vs immediate TM instruction), and several review-relevant outcomes (blood pressure, psychological distress, coping, quality of life) are susceptible to influence by participants/personnel knowledge of allocation.
- Model support context: [{"source": "article", "quote": "Thus, this was a single-blind design.", "relevance": "States only a single-blind design; implies participants/personnel were not blinded."}, {"source": "article", "quote": "All assessments were administered by research staff who were masked to treatment condition.", "relevance": "Assessor masking reported, but participants and instructors were unblinded which can influence subjective and some physiologic outcomes."}]
- GT support: Single-blind. We have left as unclear risk as it is difficult, if not impossible, to blind participants and personnel to lifestyle interventions.
- Evidence row: {}
- Source context preview: ## Study protocol The treatment group allocations were concealed by the study statistician, with individual treatment group assignments revealed to the project manager only when study participants completed baseline testing. Subjects were post-tested after ~3 months. All assessments were administered by research staff who were masked to treatment condition. Thus, this was a single-blind design. After post-test evaluation, wait-list participants were offered TM instruction. --- ## Study design This was a single-blind RCT comparing stress reduction with the TM program to wait-list controls on change in BP, psychological distress, and coping in young adults. The present study reports on both...

#### Blinding of outcome assessment: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly states that research staff who administered all assessments were masked to treatment condition; therefore outcome assessment was blinded and unlikely to be influenced by knowledge of allocation for both objective (BP) and subjective (psychological/coping) outcomes.
- Model support: Quote: "All assessments were administered by research staff who were masked to treatment condition." Comment: Research staff (outcome assessors) were explicitly masked, making detection bias unlikely for measured outcomes like casual blood pressure and psychological scales.
- Model support context: [{"source": "article", "quote": "All assessments were administered by research staff who were masked to treatment condition.", "relevance": "States that outcome assessors (research staff) were masked to allocation, directly addressing detection bias."}, {"source": "article", "quote": "The primary outcome for the study was casual BP. Secondary outcomes were psychological distress... and coping ability.", "relevance": "Identifies the review-relevant outcomes (blood pressure, psychological scales) that were measured by masked assessors."}]
- GT support: All assessments were administered by research staff who were masked to treatment condition.
- Evidence row: {}
- Source context preview: ## Study protocol Students were then randomized to experimental or control groups, using the random blocks method21 stratifying on gender (male/female) and self-reported attention deficit hyperactivity disorder status (yes, no), to either (a) immediate instruction in the TM program or (b) wait list/delayed start condition. (The attention deficit hyperactivity disorder stratification was for the purpose of a separate substudy.) --- ## Study protocol The treatment group allocations were concealed by the study statistician, with individual treatment group assignments revealed to the project manager only when study participants completed baseline testing. Subjects were post-tested after ~3...

#### Incomplete outcome data: All outcomes

- Prediction: Unclear risk
- Ground truth: High risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: About 30% missing outcomes with no per-arm missingness, reasons, or imputation methods reported in the excerpts; although baseline comparison between completers and non-completers is provided, this is insufficient to conclude low risk, so overall judgement is Unclear. Audited override: Low risk is not established because actual missing outcome data are not reported.
- Model support: Quote: '207 students who completed both BP baseline and post-testing' and 'Across groups, there were no significant differences between subjects who completed post-testing (n = 207) and those who did not complete post-testing (n = 91) on any of the primary or secondary outcome variables at baseline.' Comment: Overall attrition is substantial (~30%) but the excerpts do not report missingness by arm, reasons, or imputation methods, so risk of bias due to incomplete outcome data cannot be judged confidently. Comment: Audited override: Low risk is not established because actual missing outcome data are not reported.
- Model support context: [{"source": "article", "quote": "'The subjects were 298 students...'; '207 students who completed both BP baseline and post-testing by group.'", "relevance": "Shows total randomized and number with outcome data; implies ~91 missing but no arm-specific counts."}, {"source": "article", "quote": "'Across groups, there were no significant differences between subjects who completed post-testing (n = 207) and those who did not complete post-testing (n = 91)...'", "relevance": "Authors compare completers vs attriters at baseline, but do not provide reasons or per-arm missingness or imputation details."}]
- GT support: For relevant subgroup, 159 students were randomised and 112 completed 3-month follow-up (41.9% loss to follow-up).
- Evidence row: {}
- Source context preview: ## Front To further investigate the effectiveness of the TM program on BP, psychological distress, and coping, we conducted a randomized controlled trial (RCT) in college students. To our knowledge, this is the first RCT to evaluate the efficacy of a mind–body intervention on BP and psychological factors in young adults. --- ## Study protocol Students were then randomized to experimental or control groups, using the random blocks method21 stratifying on gender (male/female) and self-reported attention deficit hyperactivity disorder status (yes, no), to either (a) immediate instruction in the TM program or (b) wait list/delayed start condition. (The attention deficit hyperactivity disorder...


## 20044929 - Hegarty 2013

- Mode: audited
- Review context: none (0 chars)
- Article chars: 38512
- Extraction context chars: n/a
- Total seconds: 41.62
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Low risk | yes | no_support_phrase_match |  |
| Allocation concealment | Unclear risk | Unclear risk | yes | article_absence_or_unclear |  |
| Blinding of participants and personnel: All outcomes | High risk | High risk | yes | no_support_phrase_match |  |
| Blinding of outcome assessment: All outcomes | Low risk | Low risk | yes | article_absence_or_unclear |  |
| Incomplete outcome data: All outcomes | Unclear risk | Low risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly states block randomisation with random block sizes and that a statistician performed the randomisation, meeting the Low risk criteria for a random component in sequence generation.
- Model support: Quote: "block randomisation with random block sizes will be used within each stratum. The randomisation will be performed by a statistician not directly involved in the study and who is blinded to the identity of the practitioners." Comment: Describes use of random (random block sizes) method and independent statistician performing randomisation.
- Model support context: [{"source": "article", "quote": "block randomisation with random block sizes will be used within each stratum.", "relevance": "Specifies a random component in sequence generation (random block sizes)."}, {"source": "article", "quote": "The randomisation will be performed by a statistician not directly involved in the study", "relevance": "Independent statistician generating sequence supports appropriate random sequence generation."}]
- GT support: Quote:"A statistician who was otherwise not involved in the study follow‐up, generated a random allocation sequence in Stata, stratified by location of each doctor’s practice (urban vs rural), with random permuted block sizes of two and four within each stratum" (p 252)
- Evidence row: {}
- Source context preview: ## Methods/Design The study conforms to the guidelines contained in the CONSORT statement for cluster randomised controlled trials [50]. Individual GPs (cluster) will be the unit of randomisation. The study includes one GP only per practice to circumvent the threat of contamination due to cross-over effects. Interventions and analyses will target two levels - the cluster (GP) level and individual (woman) level. The trial will include 40 GPs and consist of two arms - intervention and comparison. Figure 1 presents the anticipated flow of clusters and individual patients over the course of the trial. The study has received ethics approval from the Human Research Ethics Committee of The...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The excerpts state cluster randomisation by wave and timing of randomisation but do not describe any concealment mechanism (central randomisation, opaque sealed envelopes, etc.), so there is insufficient information to judge whether recruiters could foresee assignments.
- Model support: Quote: "Sequence generation and allocation concealment Allocation to intervention or comparison will be based on clusters rather than individuals. The trial will be run in four consecutive over..." Comment: The report states cluster allocation and that randomisation occurs by wave, but does not describe the method used to conceal allocations (central randomisation, sealed envelopes, etc.).
- Model support context: [{"source": "article", "quote": "Individual GPs (cluster) will be the unit of randomisation... All GPs (and their female patients) in a given wave... are randomised to intervention or comparison once the cut-off for the return of the baseline survey... has been reached.", "relevance": "Describes timing and unit of randomisation but gives no details on how allocations are concealed from those enrolling clusters."}, {"source": "article", "quote": "Sequence generation and allocation concealment Allocation to intervention or comparison will be based on clusters... The trial will be run in four consecutive over...", "relevance": "Section heading indicates allocation concealment should be addressed, but the excerpt does not report the concealment method; necessary details are missing."}]
- GT support: Comment:Unclear if concealment of randomisation was done adequately after randomisation was carried out. (The unit of randomisation is the unit of analysis for this review and hence for the purpose of risk of bias, it is considered an individual RCT, not a cluster RCT)
- Evidence row: {}
- Source context preview: ## Patient recruitment Patient recruitment will be done through methods validated in a recent primary care cohort study that screened for probable depression via postal survey, and included a screen for abuse [51]. In weave, for each participating GP, a list of female patients, aged 16 to 50 years who consulted the GP at least once in the previous 12 months will be randomly generated (maximum 600 patients per list). The GP will review the list and exclude those women who meet exclusion criteria. The remaining women will be mailed the screening questionnaire together with a letter from their GP endorsing the project, an information sheet, a resource card listing contact numbers for various...

#### Blinding of participants and personnel: All outcomes

- Prediction: High risk
- Ground truth: High risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly states both GPs and women were not blinded. The review-relevant outcomes include self-reported attitudes, counseling uptake and readiness, which are likely affected by knowledge of allocation, so performance bias is likely (High risk).
- Model support: Quote: "Due to the nature of the intervention (professional training plus patient counselling) it is not possible to blind the GPs to their status as intervention or control. Similarly, the immediate project team is not blind... women are not blinded" Comment: Participants (women) and key personnel (GPs) were not blinded and outcomes (attitude, counselling delivery, readiness, referrals — many self-reported or clinician-delivered) are likely influenced by knowledge of allocation.
- Model support context: [{"source": "article", "quote": "Due to the nature of the intervention... it is not possible to blind the GPs to their status as intervention or control.", "relevance": "Shows GPs (key personnel) were unblinded, which can influence delivery of counseling and clinician-reported outcomes."}, {"source": "article", "quote": "women are not blinded in that they need to be aware that they may (intervention group) or may not (comparison group) be invited by the GP", "relevance": "Shows participants were unblinded; many review outcomes are self-reported attitudes/readiness and could be biased by awareness of allocation."}]
- GT support: Comment:High risk of performance bias as outcomes were self‐reported and participants were aware of which group they were allocated to Quote:"Because of the nature of the intervention, neither doctors nor patients could be masked to intervention." (p 252)
- Evidence row: {}
- Source context preview: ## Methods/Design The study conforms to the guidelines contained in the CONSORT statement for cluster randomised controlled trials [50]. Individual GPs (cluster) will be the unit of randomisation. The study includes one GP only per practice to circumvent the threat of contamination due to cross-over effects. Interventions and analyses will target two levels - the cluster (GP) level and individual (woman) level. The trial will include 40 GPs and consist of two arms - intervention and comparison. Figure 1 presents the anticipated flow of clusters and individual patients over the course of the trial. The study has received ethics approval from the Human Research Ethics Committee of The...

#### Blinding of outcome assessment: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: Outcomes include self-reported measures (quality of life, mental health, readiness, comfort, GP inquiry) assessed by women and GPs who were not blinded; subjective outcomes collected unblinded are likely influenced by knowledge of allocation, so risk of detection bias is high. Calibration: outcome measurement was objective/device/lab-based or centrally interpreted, so assessor knowledge is unlikely to materially bias measurement.
- Model support: Quote: "There is no blinding as regards data collection based on the CONSORT guidelines [50], as the women and GPs themselves complete the surveys (i.e. data were not collected by a research assistant blinded to the allocation)." Comment: Outcome assessment (self-reported surveys and GP-reported behaviours) was not blinded and these are subjective measures likely influenced by knowledge of allocation. Comment: Calibration: outcome measurement was objective/device/lab-based or centrally interpreted, so assessor knowledge is unlikely to materially bias measurement.
- Model support context: [{"source": "article", "quote": "audio-record consultations. We anticipate that only a small proportion of GPs and women will agree to have the sessions recorded. We will conduct semi-structured interviews with a sample of up to 20 women from...", "relevance": "Calibration: outcome measurement was objective/device/lab-based or centrally interpreted, so assessor knowledge is unlikely to materially bias measurement."}, {"source": "article", "quote": "data were not collected by a research assistant blinded to the allocation. However the wider investigator team (and the statistician) remain blinded", "relevance": "States explicitly that outcome data collection was unblinded, indicating assessors (women and GPs) knew allocation."}]
- GT support: Comment:unclear about blinding of assessors but outcomes were not subjective to assessor interpretation as the included outcomes from this study were self‐reported Quote:"...but study investigators and researchers following‐up patients and entering and analysing data were masked to allocation." (p 252)
- Evidence row: {}
- Source context preview: ## Data collection The primary outcomes (Table 1) include quality of life, measured across four dimensions (physical, psychological, environmental, social) using the WHOQoL-Bref [58], and mental health status, using the mental component of the SF-12 [59]. The third primary outcome is safety and is measured based on the existence of a safety plan (yes/no) and the number of safety behaviours enacted (Safety-Promoting Behaviour Checklist [60]). The secondary outcomes include open ended questions about readiness for change, based on the Domestic Violence Survivor Assessment [61], comfort to discuss abuse with GP (5-point likert scale), GPs' inquiry about the safety of women and their children...

#### Incomplete outcome data: All outcomes

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The excerpts give planned sample sizes and anticipated losses but do not report actual randomized/enrolled/analyzed numbers by arm, observed missing outcome counts, reasons for dropout, or how missing data will be handled; this insufficient reporting prevents judgment under the domain criteria.
- Model support: Quote: "Once the baseline survey and consent form have been returned, women are officially enrolled in the trial." Comment: The report describes planned recruitment, follow-up schedule and that analysis will be intention-to-treat, but provides no randomized/enrolled counts by arm, numbers analyzed at 12 months, attrition by arm, reasons for loss to follow-up, or handling of missing outcome data.
- Model support context: [{"source": "methodology", "quote": "Quote: \"Once the baseline survey and consent form have been returned, women are officially enrolled in the trial.\" Comment: The report describes planned recruitment, follow-up schedule and that analysis will be intention-to-treat, but...", "relevance": "Recovered from malformed JSON; inspect raw output if this judgement matters."}]
- GT support: Comment:no missing primary outcome data. All secondary outcomes apart from Readiness to Change were reported Quote:" We have not yet analysed the open‐ended questions (at 6 months and 12 months) about readiness for change." (p 252)
- Evidence row: {}
- Source context preview: ## Data analysis and reporting Characteristics of GPs and women will be summarised using frequencies and percentages for categorical data, and means and standard deviations or percentiles for continuous data, for the two study arms. GP and women's characteristics will be compared between the two arms at recruitment to ensure that randomisation was effective. Intra-cluster correlations will be calculated for key outcome variables and patient variables at baseline. Appropriate modelling techniques will be used to account for the complexity of the study design, its hierarchical structure (women clustered within practices), stratification of practices at randomisation and repeated measures over...


## 20395225 - Alvarez 2010

- Mode: audited
- Review context: none (0 chars)
- Article chars: 32026
- Extraction context chars: n/a
- Total seconds: 43.49
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Unclear risk | Unclear risk | yes | no_support_phrase_match |  |
| Allocation concealment | Unclear risk | Unclear risk | yes | article_absence_or_unclear |  |
| Blinding of participants and personnel: All outcomes | High risk | High risk | yes | no_support_phrase_match |  |
| Blinding of outcome assessment: All outcomes | High risk | High risk | yes | no_support_phrase_match |  |
| Incomplete outcome data: All outcomes | Unclear risk | Unclear risk | yes | no_support_phrase_match |  |

### Audit Details

#### Random sequence generation

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The article asserts participants were 'randomly assigned' but fails to describe the random component or method used to generate the allocation sequence; therefore there is insufficient information to judge Low or High risk.
- Model support: Quote: "On completion of the baseline measures, participants were randomly assigned to one of two workshops (i.e., suspected child maltreatment reporting and ethnic cultural sensitivity)." Comment: The report states participants were 'randomly assigned' but gives no description of the random sequence generation method.
- Model support context: [{"source": "article", "quote": "On completion of the baseline measures, participants were randomly assigned to one of two workshops", "relevance": "States that random assignment occurred but does not describe how the sequence was generated."}, {"source": "article", "quote": "random assignment of participants to the child abuse reporting workshop or a workshop designed to enhance ethnic cultural sensitivity", "relevance": "Reiterates use of random assignment but provides no details of the randomization method (e.g., computer, random table, coin)."}]
- GT support: Comment:inadequate description of the generation of the randomised sequence Quote:"on completion of baseline measures, participants were randomly assigned to one of two workshops" (Alvarez 2010, p 215)
- Evidence row: {}
- Source context preview: ## Procedure On arriving for the workshops, participants were instructed to complete informed consent and baseline outcome measures. Measures were presented to each participant in random order to minimize order effects. On completion of the baseline measures, participants were randomly assigned to one of two workshops (i.e., suspected child maltreatment reporting and ethnic cultural sensitivity). Workshops were facilitated by nonlicensed graduate students at the master’s level, who were enrolled in a clinical psychology doctoral program. These facilitators used standardized agendas and protocol checklists depicting relevant content areas to be reviewed during the workshop. After completion...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The article states participants were randomly assigned but provides no information on the mechanism used to prevent recruiters or participants from foreseeing allocations; therefore details necessary to judge allocation concealment (e.g. central randomization or sealed envelopes) are missing.
- Model support: Quote: "On completion of the baseline measures, participants were randomly assigned to one of two workshops (i.e., suspected child maltreatment reporting and ethnic cultural sensitivity)." Comment: The report states that participants were "randomly assigned" but gives no details on the method of allocation concealment (central allocation, sealed envelopes, etc.).
- Model support context: [{"source": "article", "quote": "On completion of the baseline measures, participants were randomly assigned to one of two workshops", "relevance": "Shows random assignment occurred but does not describe how allocation was concealed from recruiters or participants."}, {"source": "article", "quote": "participants were instructed to complete informed consent and baseline outcome measures. ... On completion of the baseline measures, participants were randomly assigned", "relevance": "Indicates timing of assignment (after consent/baseline) but lacks description of concealment procedures (central randomization, opaque sealed envelopes, etc.)."}]
- GT support: Comment:method of concealment not reported by study authors
- Evidence row: {}
- Source context preview: ## Rationale for Current Study To assist in determining the application of this training program to students and professionals of diverse backgrounds, a between-groups experimental methodology was used, including standardized training protocols, assessment of the integrity of training, and random assignment of participants to the child abuse reporting workshop or a workshop designed to enhance ethnic cultural sensitivity. Although not a focus in the current study, ethnic cultural sensitivity is an important skill set involved in the provision of therapy (Sue & Lam, 2002). Ethnic cultural sensitivity was chosen as the comparison workshop in this study because it has been shown to enhance...

#### Blinding of participants and personnel: All outcomes

- Prediction: High risk
- Ground truth: High risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The interventions were distinct training workshops delivered openly to participants and facilitators; the review-relevant outcomes (identification accuracy and reporting behavior) are subjective and behaviorally influenced, so lack of blinding likely affected outcomes, meeting High risk criteria.
- Model support: Quote: "participants were randomly assigned to one of two workshops (i.e., suspected child maltreatment reporting and ethnic cultural sensitivity)." Comment: Participants and facilitators attended different active workshops with no sham/placebo or masking described; outcomes (accuracy in identification and reporting behavior) are participant/clinician-influenced and likely affected by knowledge of allocation.
- Model support context: [{"source": "article", "quote": "participants were randomly assigned to one of two workshops (i.e., suspected child maltreatment reporting and ethnic cultural sensitivity).", "relevance": "Shows participants knew they attended a specific workshop condition rather than being blinded."}, {"source": "article", "quote": "facilitators used standardized agendas and protocol checklists... workshops were facilitated by nonlicensed graduate students", "relevance": "Indicates personnel delivering interventions were aware of workshop content and thus not blinded."}]
- GT support: Comment:performance bias due to lack of blinding, and therefore likely knowledge of the allocated intervention by participants and personnel during the study, which may have influenced subjective study outcomes (i.e. self‐report measures)
- Evidence row: {}
- Source context preview: ## Procedure On arriving for the workshops, participants were instructed to complete informed consent and baseline outcome measures. Measures were presented to each participant in random order to minimize order effects. On completion of the baseline measures, participants were randomly assigned to one of two workshops (i.e., suspected child maltreatment reporting and ethnic cultural sensitivity). Workshops were facilitated by nonlicensed graduate students at the master’s level, who were enrolled in a clinical psychology doctoral program. These facilitators used standardized agendas and protocol checklists depicting relevant content areas to be reviewed during the workshop. After completion...

#### Blinding of outcome assessment: All outcomes

- Prediction: High risk
- Ground truth: High risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: Primary outcomes were self-reported by participants after attending different workshops and there is no information that participants or outcome assessors were blinded; knowledge of allocation could plausibly influence subjective responses, so risk is high. Audited override: self-reported outcome with clearly unmasked participants and material influence on measurement.
- Model support: Quote: 'On completion of the baseline measures, participants were randomly assigned to one of two workshops... After completion of the workshops, participants were readministered the outcome measures in random order.' Comment: Outcomes are participant self-reports and knowledge tests with no statement of participant or assessor blinding, so allocation knowledge likely influenced measurement. Comment: Audited override: self-reported outcome with clearly unmasked participants and material influence on measurement.
- Model support context: [{"source": "article", "quote": "On completion of the baseline measures, participants were randomly assigned to one of two workshops... After completion of the workshops, participants were readministered the outcome measures in random order.", "relevance": "Shows participants completed outcome measures pre/post workshop but gives no blinding information; participants knew which workshop they attended."}, {"source": "article", "quote": "Respondents indicated their likelihood of reporting suspected child maltreatment... on a 7-point Likert-type scale", "relevance": "Primary outcome is self-reported likelihood to report, which can be influenced by participants' knowledge of their training condition."}]
- GT support: Comment:detection bias due to knowledge of the allocated intervention by outcome assessors, and outcome measurement is likely to be influenced by lack of blinding (pre‐post self‐report measures tied closely to intervention purpose)
- Evidence row: {}
- Source context preview: ## Procedure On arriving for the workshops, participants were instructed to complete informed consent and baseline outcome measures. Measures were presented to each participant in random order to minimize order effects. On completion of the baseline measures, participants were randomly assigned to one of two workshops (i.e., suspected child maltreatment reporting and ethnic cultural sensitivity). Workshops were facilitated by nonlicensed graduate students at the master’s level, who were enrolled in a clinical psychology doctoral program. These facilitators used standardized agendas and protocol checklists depicting relevant content areas to be reviewed during the workshop. After completion...

#### Incomplete outcome data: All outcomes

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report mentions a single excluded participant for not completing postworkshop assessment but does not provide randomized counts by arm, numbers analyzed, reasons by group, or missing-data handling; therefore reporting is insufficient to judge attrition bias.
- Model support: Quote: "One participant was excluded from the study because this individual was unable to complete the postworkshop assessment." Comment: Report notes one exclusion but provides no randomized group counts, no by-arm numbers for analyzed participants, no reasons by group, and no handling of missing data.
- Model support context: [{"source": "article", "quote": "One participant was excluded from the study because this individual was unable to complete the postworkshop assessment.", "relevance": "Shows there was at least one missing outcome but does not report which arm, total randomized, or how missing data were handled."}, {"source": "not_reported", "quote": "No information on randomized numbers by arm, analyzed sample sizes, reasons for missingness by group, or imputation methods provided in excerpts.", "relevance": "Absence of key attrition details prevents judgement whether missing data were balanced or related to outcomes."}]
- GT support: Comment:1 participant was excluded from analyses due to inability to complete the postintervention measure; however, authors do not report the participant's allocation condition (Alvarez 2010, p 212)
- Evidence row: {}
- Source context preview: ## Front The current article reports the development of a training program to assist professionals in effectively reporting suspected child maltreatment. Along these lines, we first underscore child maltreatment reporting practices and techniques that have been promoted based on clinical lore or results found in uncontrolled trials (i.e., did not involve random assignment of participants to experimental conditions or case trials involving multiple baseline or withdrawal experimental designs). We then review a training program that is specific to child maltreatment reporting and found to be efficacious in a single-case multiple baseline trial. This program incorporates many of the practices...


## 20655662 - Litt 2010

- Mode: audited
- Review context: none (0 chars)
- Article chars: 30746
- Extraction context chars: n/a
- Total seconds: 42.3
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Low risk | yes | no_support_phrase_match |  |
| Allocation concealment | Low risk | High risk | no | unknown | allocation_concealment_detail_threshold |
| Blinding of participants and personnel: All outcomes | High risk | High risk | yes | no_support_phrase_match |  |
| Blinding of outcome assessment: All outcomes | High risk | High risk | yes | no_support_phrase_match |  |
| Incomplete outcome data: All outcomes | Low risk | Low risk | yes | no_support_phrase_match |  |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly states a computerized urn randomization procedure was used, which constitutes a random component (computer-based random/urn method) meeting the Low risk criteria for sequence generation.
- Model support: Quote: "Those who agreed to participate were randomized to either the Standard Treatment group (STD; n=49) or to the Standard Treatment + Cognitive-Behavioral Treatment group (STD+CBT; n=52) using a computerized urn randomization procedure [28]." Comment: A computerized urn randomization procedure is a random component fulfilling sequence generation criteria for low risk.
- Model support context: [{"source": "article", "quote": "randomized... using a computerized urn randomization procedure", "relevance": "Describes a computerized random component (urn randomization) used to generate allocation sequence."}, {"source": "article", "quote": "The two conditions were balanced on gender, age, ethnic background, pain level recorded at baseline, and RDC axis I diagnoses.", "relevance": "Indicates stratified/balanced randomization consistent with an algorithmic random sequence generation."}]
- GT support: Stratified randomisation (computerised urn method) generated by an independent study co‐ordinator
- Evidence row: {}
- Source context preview: ## Procedure Those who agreed to participate were randomized to either the Standard Treatment group (STD; n=49) or to the Standard Treatment + Cognitive-Behavioral Treatment group (STD+CBT; n=52) using a computerized urn randomization procedure [28]. The two conditions were balanced on gender, age, ethnic background, pain level recorded at baseline, and RDC axis I diagnoses. The Project Coordinator entered the urn data during the intake session and informed the participants of their treatment assignments. The first treatment appointment was then scheduled for one to two weeks later, coinciding with the delivery of the splint. --- ## Procedure Analysis of main effects of treatment on each of...

#### Allocation concealment

- Prediction: Low risk
- Ground truth: High risk
- Match: False
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: A computerized urn randomization procedure implies central/random assignment that recruiters could not foresee, meeting criteria for adequate concealment (central allocation).
- Model support: Quote: "Those who agreed to participate were randomized to either the Standard Treatment group (STD; n=49) or to the Standard Treatment + Cognitive-Behavioral Treatment group (STD+CBT; n=52) using a computerized urn randomization procedure [28]. The two conditions were balanced on gender, age, ethnic background, pain level recorded at baseline, and RDC axis I diagnoses. The Project Coordinator entered the urn data during the intake session and informed the participants of their treatment assignments." Comment: Allocation was implemented via a computerized urn randomization procedure, with assignments generated centrally and entered during intake, making it unlikely that recruiters could foresee allocations.
- Model support context: [{"source": "article", "quote": "randomized ... using a computerized urn randomization procedure", "relevance": "Describes a centralized computerized randomization method which prevents foreknowledge of upcoming allocations."}, {"source": "article", "quote": "The Project Coordinator entered the urn data during the intake session and informed the participants of their treatment assignments.", "relevance": "Shows assignment was determined via the urn system at intake rather than by an open schedule accessible to recruiters."}]
- GT support: Not discussed
- Evidence row: {}
- Source context preview: ## Procedure Those who agreed to participate were randomized to either the Standard Treatment group (STD; n=49) or to the Standard Treatment + Cognitive-Behavioral Treatment group (STD+CBT; n=52) using a computerized urn randomization procedure [28]. The two conditions were balanced on gender, age, ethnic background, pain level recorded at baseline, and RDC axis I diagnoses. The Project Coordinator entered the urn data during the intake session and informed the participants of their treatment assignments. The first treatment appointment was then scheduled for one to two weeks later, coinciding with the delivery of the splint. --- ## Procedure ### Assignment to treatment --- ## Procedure...

#### Blinding of participants and personnel: All outcomes

- Prediction: High risk
- Ground truth: High risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: Participants were explicitly informed of allocation and research staff were unblinded; the interventions differ (behavioral therapy addition) and outcomes include subjective measures (pain, disability), so lack of blinding was likely to influence these outcomes (High risk).
- Model support: Quote: "The Project Coordinator entered the urn data during the intake session and informed the participants of their treatment assignments." Comment: Participants were told their treatment; interventions (splint vs splint+CBT) are clearly different and personnel (therapists) delivered treatments unblinded, so performance bias likely affected subjective outcomes like pain and disability.
- Model support context: [{"source": "article", "quote": "The Project Coordinator...informed the participants of their treatment assignments.", "relevance": "Shows participants were aware of allocation, indicating no participant blinding."}, {"source": "article", "quote": "A trained M.A.-level research associate, who was not blinded to treatment condition, conducted the pretreatment and follow-up research assessments.", "relevance": "Indicates personnel assessing participants were unblinded, risking influence on outcomes."}]
- GT support: Not possible for participants to be blinded to treatment in this type of trial. Study personnel were not blinded.
- Evidence row: {}
- Source context preview: ## Procedure Those who agreed to participate were randomized to either the Standard Treatment group (STD; n=49) or to the Standard Treatment + Cognitive-Behavioral Treatment group (STD+CBT; n=52) using a computerized urn randomization procedure [28]. The two conditions were balanced on gender, age, ethnic background, pain level recorded at baseline, and RDC axis I diagnoses. The Project Coordinator entered the urn data during the intake session and informed the participants of their treatment assignments. The first treatment appointment was then scheduled for one to two weeks later, coinciding with the delivery of the splint. --- ## Procedure A trained M.A.-level research associate, who was...

#### Blinding of outcome assessment: All outcomes

- Prediction: High risk
- Ground truth: High risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The review-relevant outcomes (pain and interference) were self-reported questionnaire measures collected by an assessor explicitly described as not blinded; lack of blinding is likely to influence these subjective outcome assessments, so detection bias is high.
- Model support: Quote: "A trained M.A.-level research associate, who was not blinded to treatment condition, conducted the pretreatment and follow-up research assessments." Comment: Outcome assessment (pain, interference, self-efficacy via questionnaires) was conducted by an unblinded assessor and these are participant-reported/subjective measures likely influenced by assessor/participant knowledge.
- Model support context: [{"source": "article", "quote": "A trained M.A.-level research associate, who was not blinded to treatment condition, conducted the pretreatment and follow-up research assessments.", "relevance": "Identifies that the person collecting outcome data was not blinded."}, {"source": "article", "quote": "Ratings of pain experience... collected using the Multidimensional Pain Inventory... Interference with activities was measured using the interference scale from the MPI.", "relevance": "Specifies the review-relevant outcomes (pain, interference) were self-report/questionnaire measures collected by the unblinded assessor."}]
- GT support: Outcome assessors not blinded as participant self‐report
- Evidence row: {}
- Source context preview: ## Measures and Instruments Readiness to engage in self-management treatment for chronic pain was assessed using the Pain Stages of Change Questionnaire [PSOCQ; 11; 12]. The PSOCQ assesses readiness using 30 Likert-scaled items scored from 1 (strongly disagree) to 5 (strongly agree), and comprising four scales: Precontemplation (e.g., `All of this talk about how to cope better is a waste of my time'), Contemplation (e.g., `I have been thinking that the way I cope with my pain could improve'), Action (e.g., `I am developing new ways to cope with my pain') and Maintenance (e.g., `I use what I have learned to help keep my pain under control'). The internal reliabilities of these scales ranged...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report gives randomized sample size (101), follow-up rates (88% posttreatment, 73% at 52 weeks), and explicitly states losses were equivalent across treatment conditions; balanced and relatively moderate attrition meets criteria for Low risk.
- Model support: Quote: "Of 196 persons screened, 121 were deemed eligible for the study, and 101 were assigned to treatment. At posttreatment 88% of patients provided data, and 73% provided data at 52 weeks. Losses to follow-up were equivalent across treatment conditions." Comment: Attrition is reported, with overall follow-up rates and statement that losses were equivalent across treatment conditions, suggesting balanced missingness unlikely to bias results.
- Model support context: [{"source": "article", "quote": "Of 196 persons screened, 121 were deemed eligible for the study, and 101 were assigned to treatment. At posttreatment 88% of patients provided data, and 73% provided data at 52 weeks.", "relevance": "Reports numbers randomized (101) and overall follow-up percentages at posttreatment and 52 weeks, enabling assessment of amount of missing outcome data."}, {"source": "article", "quote": "Losses to follow-up were equivalent across treatment conditions.", "relevance": "States balance of attrition across arms, supporting that missingness was similar between groups and less likely to bias comparisons."}]
- GT support: "At posttreatment 88% of patients provided data, and 73% provided data at 52 weeks. Losses to follow‐up were equivalent across treatment conditions." "Analysis of main effects of treatment on each of the three major dependent variables was conducted using a mixed model regression procedure (Proc MIXED, SAS Institute [25]), and an intent‐to‐treat approach."
- Evidence row: {}
- Source context preview: ## Participants The mean age of the sample was 39.4 years (SD = 12.1). The majority of participants were white (79%), with 9% black, 9% of Hispanic origin, and 3% self-described as Other. Forty-one percent were married or cohabiting. The average years of education was 14.7 (SD = 2.5). The participants reported having chronic TMD pain for 6.7 years on average (SD = 6.6), with a mean pain intensity rating of 3.5 on a scale to 6 (SD = 1.3). Of 196 persons screened, 121 were deemed eligible for the study, and 101 were assigned to treatment. At posttreatment 88% of patients provided data, and 73% provided data at 52 weeks. Losses to follow-up were equivalent across treatment conditions. The...


## 20740213 - Jo 2010

- Mode: audited
- Review context: none (0 chars)
- Article chars: 16249
- Extraction context chars: n/a
- Total seconds: 43.33
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Unclear risk | Unclear risk | yes | unknown |  |
| Allocation concealment | Unclear risk | Unclear risk | yes | unknown |  |
| Blinding of participants and personnel: All outcomes | Low risk | Low risk | yes | unknown |  |
| Blinding of outcome assessment: All outcomes | Unclear risk | Low risk | no | unknown | under-called_due_to_missing_or_underused_evidence |
| Incomplete outcome data: All outcomes | Unclear risk | Low risk | no | unknown | under-called_due_to_missing_or_underused_evidence |

### Audit Details

#### Random sequence generation

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: The excerpts report treatment groups and blinding of personnel but provide no information on how the allocation sequence was generated (no mention of random number table, computer generator, coin toss, minimization, or a non-random rule), so there is insufficient information to judge risk of bias for sequence generation.
- Model support: Quote: "After performing sternotomy, patients received saline (n=20, controls) or milrinone (n=20, Sanofi, Korea) 0.5 µg/kg/min during coronary artery anastomosis." Comment: The report gives group sizes but does not describe how patients were allocated or any random sequence generation method.
- Model support context: [{"source": "article", "quote": "After performing sternotomy, patients received saline (n=20, controls) or milrinone (n=20...)", "relevance": "Shows group allocation and sizes but contains no description of randomization method."}, {"source": "article", "quote": "All procedures were performed by the same cardiac surgeon and anesthesiologist blinded to the treatment groups.", "relevance": "States personnel were blinded to groups but does not describe how the sequence was generated."}]
- GT support: No information provided
- Evidence row: {}
- Source context preview: ## Materials and Methods Exclusion criteria included left or right ventricular ejection fraction of less than 40% from the transthoracic echocardiogram before surgery, valvular heart disease, severe cerebral or renal dysfunction, or emergency surgery. Patients with stenosis at more than 3 coronary arteries were selected. An hour before arriving at the operating rooms, all patients received an intramuscular injection of morphine, 0.05-0.1 mg/kg, as preliminary anesthesia, and other drugs, except digoxin and diuretics, as normal. After arriving at the operating room, the induction of lead II and V5 was continuously monitored by 5-leads electrocardiography, and a catheter was inserted by...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: The article provides no description of the method used to conceal allocation (no central randomization, sealed envelopes, or equivalent). Necessary detail on how assignments were prevented from being foreseen by recruiters is missing, so risk is unclear.
- Model support: Quote: "All procedures were performed by the same cardiac surgeon and anesthesiologist blinded to the treatment groups." Comment: The report states personnel were blinded but gives no information on how the allocation sequence was concealed prior to assignment (no method of allocation concealment described).
- Model support context: [{"source": "methodology", "quote": "Quote: \"All procedures were performed by the same cardiac surgeon and anesthesiologist blinded to the treatment groups.\" Comment: The report states personnel were blinded but gives no information on how the allocation sequence was...", "relevance": "Recovered from malformed JSON; inspect raw output if this judgement matters."}]
- GT support: No information provided
- Evidence row: {}
- Source context preview: ## Materials and Methods For inducing anesthesia, endotracheal intubation was performed after giving intravenous injections of midazolam 2.5 mg, sufentanil 1.5-3.0 µg/kg, and rocuronium bromide 50 mg. To maintain anesthesia, sufentanil (0.5-1.5 µg/kg/h) and vecuronium were continuously administered intravenously with 50% oxygen and 50% medical air, as well as sevoflurane with an end-tidal concentration of 0.2-0.4 vol%, and controlled ventilation was conducted to set the end-tidal CO2 tension at 30-35 mmHg. After inducing anesthesia, isosorbide dinitrate (0.5 µg/kg/min) was administered to prevent myocardial ischemia and coronary vasospasm, and a transesophageal echocardiography probe was...

#### Blinding of participants and personnel: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: Personnel directly involved in delivering the intervention (surgeon and anesthesiologist) are explicitly reported as blinded; the outcomes are objective clinical events, so lack of participant blinding (not reported) is unlikely to have materially influenced these outcomes.
- Model support: Quote: "All procedures were performed by the same cardiac surgeon and anesthesiologist blinded to the treatment groups." Comment: Key personnel delivering the intervention were blinded, so performance bias from personnel is unlikely to have influenced objective outcomes (death, MI, stroke, cardiogenic shock, arrhythmia, low cardiac output).
- Model support context: [{"source": "article", "quote": "All procedures were performed by the same cardiac surgeon and anesthesiologist blinded to the treatment groups.", "relevance": "States that key care personnel were blinded, reducing risk that care differed by allocation during surgery."}, {"source": "article", "quote": "After performing sternotomy, patients received saline (n=20, controls) or milrinone (n=20...) 0.5 µg/kg/min during coronary artery anastomosis.", "relevance": "Describes interventions that could be visibly different, but personnel blinding reported mitigates performance bias for the clinical outcomes."}]
- GT support: Double-blind study
- Evidence row: {}
- Source context preview: ## Materials and Methods For inducing anesthesia, endotracheal intubation was performed after giving intravenous injections of midazolam 2.5 mg, sufentanil 1.5-3.0 µg/kg, and rocuronium bromide 50 mg. To maintain anesthesia, sufentanil (0.5-1.5 µg/kg/h) and vecuronium were continuously administered intravenously with 50% oxygen and 50% medical air, as well as sevoflurane with an end-tidal concentration of 0.2-0.4 vol%, and controlled ventilation was conducted to set the end-tidal CO2 tension at 30-35 mmHg. After inducing anesthesia, isosorbide dinitrate (0.5 µg/kg/min) was administered to prevent myocardial ischemia and coronary vasospasm, and a transesophageal echocardiography probe was...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: Device-based hemodynamic and echocardiographic outcomes were measured and the operative/anesthesia staff were explicitly blinded; objective measurements are unlikely to be influenced by knowledge of allocation, meeting Low risk criteria. Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support: Quote: "All procedures were performed by the same cardiac surgeon and anesthesiologist blinded to the treatment groups." Comment: The key hemodynamic outcomes (cardiac output, RVEF, pressures) were measured by continuous transesophageal echocardiography and invasive monitoring, objective device-based measures and assessed by personnel who were blinded. Comment: Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support context: [{"source": "article", "quote": "## Materials and Methods For inducing anesthesia, endotracheal intubation was performed after giving intravenous injections of midazolam 2.5 mg, sufentanil 1.5-3.0 µg/kg, and rocuronium bromide 50 mg. To maintain anesthesia, sufentanil...", "relevance": "Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported."}, {"source": "article", "quote": "All procedures were performed by the same cardiac surgeon and anesthesiologist blinded to the treatment groups.", "relevance": "States that key clinical personnel performing surgery and anesthetic management were blinded to group allocation."}]
- GT support: Double-blind study
- Evidence row: {}
- Source context preview: ## Materials and Methods For inducing anesthesia, endotracheal intubation was performed after giving intravenous injections of midazolam 2.5 mg, sufentanil 1.5-3.0 µg/kg, and rocuronium bromide 50 mg. To maintain anesthesia, sufentanil (0.5-1.5 µg/kg/h) and vecuronium were continuously administered intravenously with 50% oxygen and 50% medical air, as well as sevoflurane with an end-tidal concentration of 0.2-0.4 vol%, and controlled ventilation was conducted to set the end-tidal CO2 tension at 30-35 mmHg. After inducing anesthesia, isosorbide dinitrate (0.5 µg/kg/min) was administered to prevent myocardial ischemia and coronary vasospasm, and a transesophageal echocardiography probe was...

#### Incomplete outcome data: All outcomes

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: Planned/enrolled numbers are reported and some outcomes stated as similar, but absence of per-arm analyzed counts, missing data amounts, reasons, or handling methods prevents assessment of attrition bias, so judgement is Unclear. Audited override: Low risk is not established because actual missing outcome data are not reported.
- Model support: Quote: '20 patients in each group, 40 in total.' Comment: The report gives planned/enrolled numbers and states 'there were no early deaths' and similar complication rates, but provides no per-arm analyzed counts, no missing outcome numbers or reasons, nor any description of how missing outcomes were handled, so risk of attrition bias is unclear. Comment: Audited override: Low risk is not established because actual missing outcome data are not reported.
- Model support context: [{"source": "article", "quote": "20 patients in each group, 40 in total.", "relevance": "Shows randomized/enrolled numbers but does not indicate analyzed or missing counts."}, {"source": "article", "quote": "there were no early deaths; both groups showed similar rates of myocardial infarction, cerebral infarction, renal failure, mechanical ventilation lasting more than 48 hours, re-operation, and infections (Table 6).", "relevance": "Provides outcome incidence statements but does not provide per-arm denominators or missing data details."}]
- GT support: No missing outcome data
- Evidence row: {}
- Source context preview: ## Results OPCAB was performed successfully without transition to emergency cardiopulmonary bypass. There were no significant statistical differences between the 2 groups for gender, age, medical history of diabetes and hypertension, drug administration, or left ventricle ejection rate (Table 1). The total operation time, coronary artery anastomosis, and total norepinephrine volume were similar for both groups (Table 2). Heart movement and stabilization for anastomosis did not require treatment of arrhythmia. --- ## Results Cardiac index decreased in controls during OM anastomosis, whereas milrinone treatment increased it (P < 0.05, Table 3). Milrinone also blocked the increase in pulmonary...


## 20830695 - Deblinger 2011

- Mode: audited
- Review context: none (0 chars)
- Article chars: 29800
- Extraction context chars: n/a
- Total seconds: 43.03
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Unclear risk | Unclear risk | yes | no_support_phrase_match |  |
| Allocation concealment | Unclear risk | Unclear risk | yes | no_support_phrase_match |  |
| Blinding of participants and personnel: All outcomes | High risk | High risk | yes | no_support_phrase_match |  |
| Blinding of outcome assessment: All outcomes | Unclear risk | High risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |
| Incomplete outcome data: All outcomes | Unclear risk | Low risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |

### Audit Details

#### Random sequence generation

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The excerpts repeatedly state participants were 'randomly assigned' but provide no description of the randomization procedure (random number table, computer generator, minimization, etc.). Because the method of sequence generation is not reported, risk of bias for sequence generation is unclear.
- Model support: Quote: "Following the initial assessment, each child was randomly assigned to one of the four treatment conditions." Comment: The report states participants were 'randomly assigned' but does not describe the method or any random component (e.g., computer, table, coin), so sequence generation is unclear.
- Model support context: [{"source": "article", "quote": "Following the initial assessment, each child was randomly assigned to one of the four treatment conditions.", "relevance": "States random assignment occurred but gives no details of the sequence generation method."}, {"source": "article", "quote": "Two hundred ten children... were randomly assigned to one of four treatment conditions", "relevance": "Confirms random assignment of sample size but lacks description of how the random sequence was generated."}]
- GT support: Comment: the authors only reported that participants were randomly allocated.
- Evidence row: {}
- Source context preview: ## Procedures Although detailed descriptions of TF-CBT can be found elsewhere, 4, 5 TF-CBT includes components that spell out the acronym PRACTICE: Psychoeducation and parenting, Relaxation, Affective modulation, Cognitive coping, TN, In vivo exposure, Conjoint parent child sessions and Enhancing safety and future development. TF-CBT, with all the components including the TN component, was only provided to those participants randomly assigned to the Yes TN conditions. In the Yes TN conditions, the TN component was covered in 3–4 sessions in the 8 session condition with at least double that number of TN sessions in the 16 session condition. For all participants, treatment typically began...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report states participants were randomly assigned and that the project coordinator was blind, but it does not describe the allocation concealment method (central system, sealed envelopes, etc.). Key details about how recruiters were prevented from foreseeing assignments are missing, so risk is unclear.
- Model support: Quote: "each child was randomly assigned to one of the four treatment conditions. ... Because the project coordinator was blind to treatment assignment, participants were told of the treatment assignment by the therapist during the first treatment session." Comment: Random assignment is reported but the method of concealment (central randomization, sealed envelopes, web/phone system) is not described, so concealment is unclear.
- Model support context: [{"source": "article", "quote": "each child was randomly assigned to one of the four treatment conditions", "relevance": "Shows random assignment occurred but does not describe how the allocation sequence was concealed."}, {"source": "article", "quote": "Because the project coordinator was blind to treatment assignment, participants were told of the treatment assignment by the therapist during the first treatment session", "relevance": "Indicates coordinator was blind but does not explain the allocation concealment mechanism prior to assignment."}]
- GT support: Comment: not mentioned and unlikely to have been done
- Evidence row: {}
- Source context preview: ## Procedures Following the initial assessment, each child was randomly assigned to one of the four treatment conditions. The families were told that they would be paid $25 for completing the initial evaluation, $25 for a 4 week evaluation, $50 for an 8 week evaluation, 16 week evaluation, and 6 and 12 month evaluations. Because the project coordinator was blind to treatment assignment, participants were told of the treatment assignment by the therapist during the first treatment session. All siblings participating in the study were assigned to the same condition. The therapists had graduate degrees in psychology, clinical social work, or a related field and had at least three years of...

#### Blinding of participants and personnel: All outcomes

- Prediction: High risk
- Ground truth: High risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly states therapists told participants their assignment and the interventions differed in obvious content; relevant outcomes are subjective (e.g., PTSD, anxiety, depression, behavior), so lack of blinding was likely to influence results, meeting High risk criteria.
- Model support: Quote: "Because the project coordinator was blind to treatment assignment, participants were told of the treatment assignment by the therapist during the first treatment session." Comment: Therapists informed participants of allocation at first session, so participants and treating personnel were aware of group assignment. Outcomes (anxiety, depression, PTSD, behavior, QoL, social functioning) are participant- or clinician-influenced and likely affected by lack of blinding.
- Model support context: [{"source": "article", "quote": "Because the project coordinator was blind to treatment assignment, participants were told of the treatment assignment by the therapist during the first treatment session.", "relevance": "States that therapists informed participants of their assigned treatment, indicating participants and therapists were unblinded."}, {"source": "article", "quote": "Therapists had graduate degrees... provided TF-CBT components... children were actively encouraged to develop a detailed narrative... No TN conditions were not encouraged to discuss or write about details.", "relevance": "Interventions were psychotherapy variants with visibly different content, making lack of blinding likely to influence subjective outcomes."}]
- GT support: Comment: not mentioned and unlikely to have been done
- Evidence row: {}
- Source context preview: ## Procedures Following the initial assessment, each child was randomly assigned to one of the four treatment conditions. The families were told that they would be paid $25 for completing the initial evaluation, $25 for a 4 week evaluation, $50 for an 8 week evaluation, 16 week evaluation, and 6 and 12 month evaluations. Because the project coordinator was blind to treatment assignment, participants were told of the treatment assignment by the therapist during the first treatment session. All siblings participating in the study were assigned to the same condition. The therapists had graduate degrees in psychology, clinical social work, or a related field and had at least three years of...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: High risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The reported review-relevant outcomes (anxiety, depression, PTSD, behavior, quality of life, social functioning) are measured with self-report instruments (parent and child questionnaires). The article excerpts do not state whether participants, parents, or outcome assessors were blinded, so there is insufficient information to judge whether detection bias was present.
- Model support: Quote: "Parent Emotional Reaction Questionnaire (PERQ) ... is a 15-item self-report instrument" Comment: Outcomes are largely self-reported (parents and children) but the report gives no information on whether outcome assessors or participants were blinded to allocation.
- Model support context: [{"source": "article", "quote": "Parent Emotional Reaction Questionnaire (PERQ) ... is a 15-item self-report instrument", "relevance": "Shows parent-reported outcome is self-report, which is susceptible to detection bias if unblinded."}, {"source": "article", "quote": "The Shame Questionnaire ... is an 8-item self-report instrument", "relevance": "Shows child-reported outcome is self-report; no blinding of assessors/participants is described."}]
- GT support: Comment: children's self-reports and parents’ reports
- Evidence row: {}
- Source context preview: ## Data analysis Two-factor, linear mixed-model repeated-measures ANOVAs were next performed with all of the 14 outcome measures. The main effects were for type of condition (8 No TN, 8 Yes TN, 16 No TN, and 16 Yes TN) and time (pre-treatment, 8 weeks, and 16 weeks) and the interaction was for type of condition by time. The identity of the children or parents was considered to represent a random effect in the repeated ANOVAs. All 14 outcome measures for the four groups significantly (ps < .05, two-tailed test) improved over time. However, none of the mean differences for the 14 outcome measures between the 8- and 16-week evaluations for the families that were treated in the 8 session groups...

#### Incomplete outcome data: All outcomes

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The excerpts report overall dropout numbers (31/210) and that analyses were based on completers (179) and that multiple imputation was performed with similar results, but they do not provide randomized/analyzed counts or missing outcome data by treatment arm, nor detailed reasons by arm. Therefore reporting is insufficient to judge whether missingness could bias results.
- Model support: Quote: "Two hundred ten children... were randomly assigned... Figure 1 shows the number of children who completed three or more sessions and a post-test K-SADS assessment in each of the treatment conditions." Comment: The report describes 31 dropouts (15%) and that analyses were based on 179 completers (>=3 sessions) but does not give randomized/analyzed counts or missing outcome numbers by arm in the supplied excerpts.
- Model support context: [{"source": "article", "quote": "16 (8%) children... never returned after being assigned; 15 (7%)... left after one or two sessions. These 31 (15%)... were defined as dropouts. Therefore, 179 (85%) children attended at least three TF-CBT sessions.", "relevance": "Gives overall dropout counts and that analyses used completers (>=3 sessions), relevant to attrition but not broken down by arm."}, {"source": "article", "quote": "A modified intent-to-treat approach... SAS Multiple Imputation... 10 maximum-likelihood pre- and post-treatment complete sets... All parameter estimates... were similar to those that had been found without imputing missing data.", "relevance": "States multiple imputation was used for sensitivity but does not report by-arm missingness, reasons by arm, or which participants were excluded from reported..."}]
- GT support: Comment: 31 children and their parents dropped out. Differences between completers and non-completers were not statistically significant. Authors analysed data on an intention-to-treat (ITT) basis.
- Evidence row: {}
- Source context preview: ## RESULTS Figure 1 shows the number of children who completed three or more sessions and a post-test K-SADS assessment in each of the treatment conditions. The mean number of TF-CBT sessions attended by the 87 children and their parents in the two 8 session conditions was 7.36 (SD = 1.33, median = 8, range = 3 – 8), whereas the mean number was 13.92 (SD = 3.34, median = 16, range 3 – 16) for the 92 children and their parents in the two 16 session conditions. Of the children/parents assigned to the 8 session conditions, 63 (72%) completed all eight treatment sessions, whereas only 50 (54%) of the children/parents assigned to the 16 session conditions completed all 16 sessions of treatment....


## 21342490 - Freeman 2011

- Mode: audited
- Review context: none (0 chars)
- Article chars: 20821
- Extraction context chars: n/a
- Total seconds: 43.45
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Unclear risk | Low risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |
| Allocation concealment | Unclear risk | Low risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |
| Blinding of participants and personnel: All outcomes | Low risk | Unclear risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |
| Blinding of outcome assessment: All outcomes | Unclear risk | Unclear risk | yes | article_absence_or_unclear |  |
| Incomplete outcome data: All outcomes | Unclear risk | Low risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |

### Audit Details

#### Random sequence generation

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The article states participants were randomized but provides no information on how the allocation sequence was generated (computer, random number table, minimization, etc.). Because the method of sequence generation is not reported in the supplied excerpts, risk of bias is unclear.
- Model support: Quote: "Men and women aged 70-82 (n = 5804) ... were randomized to placebo or pravastatin (40 mg per day) treatment." Comment: The report states participants were randomized but gives no description of the random sequence generation method.
- Model support context: [{"source": "article", "quote": "Men and women aged 70-82 (n = 5804) ... were randomized to placebo or pravastatin (40 mg per day) treatment.", "relevance": "Confirms randomization occurred but does not describe the method used to generate the sequence."}, {"source": "article", "quote": "The design and outcome of PROSPER is described elsewhere[15-17].", "relevance": "Points to external sources for methods; sequence generation detail is not provided in the supplied excerpt."}]
- GT support: Randomized, double-blind, placebo-controlled trial. "The randomization sequence was generated with a computerized random number generator and consisted of balanced blocks of size four." "Randomization was performed using the method of permuted blocks, stratified by site."
- Evidence row: {}
- Source context preview: ## Background Venous thromboembolism (VTE) has an incidence of 1-2 per 1000 individuals per year but is close to 1% per annum in those aged over 70 years[1]. VTE is a leading cause of death in hospital inpatients[2] and is a major cause of morbidity and mortality particularly in older people and among those with cancer[1,3]. Despite the fact that 70% of patients with VTE are aged over 60[1], there are few studies of risk factors in the elderly. Other studies have analyzed effects of pre-existing statin medication on incident VTE [4-6] or have compared statin use in case control studies of VTE[7-9]. A post hoc analysis of the Heart and Estrogen/progestin Replacement Study (HERS)[4] and...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The excerpts state randomization took place but contain no information on central allocation, sealed envelopes, pharmacy control, or other concealment methods. Because the method of allocation concealment is not described, judgement is Unclear and necessary details are missing.
- Model support: Quote: "Men and women aged 70-82 (n = 5804) ... were randomized to placebo or pravastatin (40 mg per day) treatment." Comment: The report states participants were randomized but gives no details on how the allocation sequence was concealed from those enrolling participants.
- Model support context: [{"source": "article", "quote": "Men and women aged 70-82 (n = 5804) ... were randomized to placebo or pravastatin (40 mg per day) treatment.", "relevance": "Shows randomization occurred but does not describe the method used to conceal allocation."}, {"source": "article", "quote": "The design and outcome of PROSPER is described elsewhere[15-17].", "relevance": "Refers to other sources for design details; no concealment procedure is reported here."}]
- GT support: Randomization was done by telephone call or through fax exchange with the study data center.
- Evidence row: {}
- Source context preview: ## Statistical analysis Data were analyzed using SAS vs9.1 (SAS Institute Inc, Cary NC). Where necessary continuous variables were transformed logarithmically to give a near-normal distribution of data for parametric analysis. Where data were available from the entire cohort, analyses were carried out using cases and non-cases (n = 5627) not using warfarin at baseline, including 2834 patients allocated to pravastatin and 2865 to placebo. The time to VTE was quantified by univariate hazard ratios and 95% confidence intervals calculated with Cox's proportional hazard model for each variable of interest. In the multivariate analyses, forward stepwise regression was undertaken, where all...

#### Blinding of participants and personnel: All outcomes

- Prediction: Low risk
- Ground truth: Unclear risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly describes the trial as double-blind and placebo-controlled and the review-relevant outcome (VTE) was objectively ascertained from imaging, anticoagulant records, or death certificates and adjudicated by clinicians, so performance bias from knowledge of allocation is unlikely.
- Model support: Quote: "The Prospective Study of Pravastatin in the Elderly at Risk (PROSPER) was a multi-centre, randomized, double-blind, placebo-controlled trial of pravastatin in the prevention of vascular disease in the elderly" Comment: Trial described as double-blind placebo-controlled, and the outcome VTE is objective (clinically adjudicated events using imaging, anticoagulant treatment, or death certificate), so lack of knowledge of allocation is unlikely to have materially influenced these objective outcomes.
- Model support context: [{"source": "article", "quote": "randomized, double-blind, placebo-controlled trial of pravastatin", "relevance": "States participants and personnel were intended to be blinded."}, {"source": "article", "quote": "Events were categorized as definite VTE if death from VTE was confirmed on the death certificate or if there was recorded evidence from investigations such as ultrasound venography ventilation perfusion lung scans or computed tomography...", "relevance": "Outcome (VTE) is objective and adjudicated from tests/records, reducing risk of bias from unblinded participants/personnel."}]
- GT support: Described as double-blind, but no details provided
- Evidence row: {}
- Source context preview: ## Background The Prospective Study of Pravastatin in the Elderly at Risk (PROSPER) was a multi-centre, randomized, double-blind, placebo-controlled trial of pravastatin in the prevention of vascular disease in the elderly[15]. The present study is an analysis of incident VTE in this population of men and women aged 70-82 using data from the PROSPER database. The aim was to determine whether pravastatin reduces VTE incidence in older people. In addition, we assessed the impact of clinical, hematological, lipid, inflammatory and vascular risk factors for incident VTE in older age. --- ## Subjects The design and outcome of PROSPER is described elsewhere[15-17]. Men and women aged 70-82 (n =...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The outcome is VTE events adjudicated from medical records by clinicians (assessors). Although the trial is described as double-blind, the report does not state whether the clinicians who examined records and made consensus categorizations were blinded to allocation, so there is insufficient information to judge detection bias.
- Model support: Quote: "The Prospective Study of Pravastatin in the Elderly at Risk (PROSPER) was a multi-centre, randomized, double-blind, placebo-controlled trial of pravastatin..." Comment: Trial described as double-blind but the article does not state who assessed VTE outcomes or whether outcome adjudicators were blinded when reviewing medical records.
- Model support context: [{"source": "article", "quote": "The Prospective Study of Pravastatin in the Elderly at Risk (PROSPER) was a multi-centre, randomized, double-blind, placebo-controlled trial of pravastatin in the prevention of vascular disease in the elderly.", "relevance": "States overall trial was double-blind but does not specify blinding of VTE outcome assessors or who performed adjudication."}, {"source": "article", "quote": "for the present study the full medical records were retrieved for all suspected VTE...examined by three clinicians in a pre-planned post hoc analysis. A consensus of two clinical opinions was required to confirm the event categorization.", "relevance": "Describes clinicians adjudicating VTE events but does not report whether these clinicians were blinded to treatment allocation."}]
- GT support: Unclear. No details were found.
- Evidence row: {}
- Source context preview: ## Subjects The design and outcome of PROSPER is described elsewhere[15-17]. Men and women aged 70-82 (n = 5804) with evidence of pre-existing vascular disease or at least one major risk factor for vascular disease were randomized to placebo or pravastatin (40 mg per day) treatment. Follow up was 3.2 years on average. For the present study the full medical records were retrieved for all suspected VTE in the PROSPER database and examined by three clinicians in a pre-planned post hoc analysis. Events were categorized as definite VTE if death from VTE was confirmed on the death certificate or if there was recorded evidence from investigations such as ultrasound venography ventilation perfusion...

#### Incomplete outcome data: All outcomes

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The excerpt reports total randomized N and event counts but does not provide numbers analyzed by arm, attrition or reasons for missing outcome data, nor handling/imputation methods; therefore insufficient reporting prevents judgement.
- Model support: Quote: "Men and women aged 70-82 (n = 5804) ... were randomized to placebo or pravastatin (40 mg per day) treatment. Follow up was 3.2 years on average." Comment: The report gives total randomized N and VTE event counts but does not report numbers analyzed by arm, numbers lost to follow-up, withdrawals by arm, or reasons for missing outcome data.
- Model support context: [{"source": "article", "quote": "Men and women aged 70-82 (n = 5804) ... were randomized to placebo or pravastatin (40 mg per day) treatment. Follow up was 3.2 years on average.", "relevance": "Provides total randomized sample but no per-arm analyzed or missing outcome counts."}, {"source": "article", "quote": "We matched each probable and definite case (n = 76) with 2 controls (n = 152) ... leaving 93 controls (Figure 1).", "relevance": "Mentions nested case-control selection and Figure 1 but missing details of withdrawals/missing outcomes by randomized arm are not reported in excerpts."}]
- GT support: The discontinued rates in each group were low. No participants lost to follow-up were reported.
- Evidence row: {}
- Source context preview: ## Subjects The design and outcome of PROSPER is described elsewhere[15-17]. Men and women aged 70-82 (n = 5804) with evidence of pre-existing vascular disease or at least one major risk factor for vascular disease were randomized to placebo or pravastatin (40 mg per day) treatment. Follow up was 3.2 years on average. For the present study the full medical records were retrieved for all suspected VTE in the PROSPER database and examined by three clinicians in a pre-planned post hoc analysis. Events were categorized as definite VTE if death from VTE was confirmed on the death certificate or if there was recorded evidence from investigations such as ultrasound venography ventilation perfusion...


## 21543987 - Van der Ploeg 2010

- Mode: audited
- Review context: none (0 chars)
- Article chars: 22909
- Extraction context chars: n/a
- Total seconds: 41.62
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Low risk | yes | no_support_phrase_match |  |
| Allocation concealment | Unclear risk | Low risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |
| Blinding of participants and personnel: All outcomes | Low risk | Unclear risk | no | article_absence_or_unclear | over-inferred_from_sparse_reporting |
| Blinding of outcome assessment: All outcomes | Low risk | Unclear risk | no | article_absence_or_unclear | over-inferred_from_sparse_reporting |
| Incomplete outcome data: All outcomes | Low risk | Low risk | yes | unknown |  |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly states a minimization algorithm was used for randomization; per the criteria, minimization is considered equivalent to random sequence generation and therefore Low risk.
- Model support: Quote: "Ninety patients were randomized 2:1 to the treatment arm using a minimization algorithm in an effort to balance the groups for disease severity (29)." Comment: Minimization is considered an adequate random method for sequence generation.
- Model support context: [{"source": "article", "quote": "Ninety patients were randomized 2:1 to the treatment arm using a minimization algorithm", "relevance": "Describes the sequence generation method; minimization is listed in criteria as equivalent to random."}, {"source": "article", "quote": "Groups were stratified according to baseline six minute walk test ... and baseline upright forced vital capacity", "relevance": "Shows minimization was applied to balance important baseline factors, supporting use of a random-like allocation method."}]
- GT support: Quote: "Patients were randomized by study personnel entering baseline information into an Interactive Voice Response System. The Interactive Voice Response System was linked to a centralized computer that randomly assigned treatment via the minimization algorithm as implemented by proprietary and validated software developed by Covance, a contract research organization."
- Evidence row: {}
- Source context preview: ## Patient Population and Randomization Ninety patients were randomized 2:1 to the treatment arm using a minimization algorithm in an effort to balance the groups for disease severity (29). Groups were stratified according to baseline six minute walk test with a threshold of 300 meters and baseline upright forced vital capacity with a threshold of 55% of the predicted value. --- ## Study Design This study was a post-hoc analysis of cardiovascular parameters in a double-blind, multi-center, randomized controlled trial evaluating the efficacy and safety of acid alpha-glucosidase enzyme replacement therapy versus placebo in patients with late onset Pompe disease. The primary efficacy endpoints...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The excerpts report use of a minimization algorithm and that the trial was double-blind, but they do not describe any method of allocation concealment (central/random telephone/web system, opaque sealed envelopes with safeguards, or pharmacy control). Because the necessary detail on how assignments were concealed from recruiters is missing, the risk is Unclear.
- Model support: Quote: "Ninety patients were randomized 2:1 to the treatment arm using a minimization algorithm in an effort to balance the groups for disease severity (29)." Comment: The report states a minimization algorithm was used but gives no details on how allocations were concealed from enrolling investigators (central randomization, sealed envelopes, or other safeguards).
- Model support context: [{"source": "article", "quote": "Ninety patients were randomized 2:1 to the treatment arm using a minimization algorithm in an effort to balance the groups for disease severity (29).", "relevance": "States the randomization method (minimization) but does not describe the allocation concealment process."}, {"source": "article", "quote": "This study was a double-blind, multi-center, randomized controlled trial evaluating the efficacy and safety ...", "relevance": "Indicates study was double-blind but does not specify the mechanism preventing foreknowledge of upcoming allocations."}]
- GT support: Quote: "Patients were randomized by study personnel entering baseline information into an Interactive Voice Response System. The Interactive Voice Response System was linked to a centralized computer that randomly assigned treatment via the minimization algorithm as implemented by proprietary and validated software developed by Covance, a contract research organization. The Investigators, other study site personnel, the patients, and representatives of Genzyme Corporation, with the exception of Genzyme Clinical Pharmacy Research Services, remained blinded to treatment assignment for the duration of the study. Every effort was made to maintain the integrity of the blind".
- Evidence row: {}
- Source context preview: ## Study Interventions and Data Collection Echocardiographic evaluation of left ventricular size and function was performed at baseline, 52 and 78 weeks. All echocardiograms were interpreted at the central cardiology core lab by a cardiologist blinded to treatment allocation. Left ventricular ejection fraction was calculated from two dimensional images using the modified Simpson’s rule in all patients. Abnormal ejection fraction was defined as < 55% (31). Left ventricular mass was evaluated using two-dimensional (2D) echocardiography and the truncated ellipsoid method (31). If the two-dimensional image quality was not sufficient, M-mode assessment was performed and left ventricular mass was...

#### Blinding of participants and personnel: All outcomes

- Prediction: Low risk
- Ground truth: Unclear risk
- Match: False
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The report explicitly calls the study double-blind and notes a volume-matched placebo infusion; for infusion-delivered therapy and objective outcomes (6MWT, FEV, FVC, ECG/echocardiography) lack of knowledge of allocation was unlikely to influence performance, so risk of performance bias is low.
- Model support: Quote: "double-blind, multi-center, randomized controlled trial" Comment: The trial is described as double-blind and the control received a volume matched placebo infusion, making it unlikely that participants or infusion personnel knew allocations and therefore performance bias is unlikely for the listed outcomes.
- Model support context: [{"source": "article", "quote": "double-blind, multi-center, randomized controlled trial", "relevance": "States that the original trial was double-blind, indicating participants and personnel were intended to be blinded."}, {"source": "article", "quote": "the control group received a volume matched placebo infusion", "relevance": "Use of a volume-matched placebo supports effective masking of participants and infusion personnel for infusion-based outcomes."}]
- GT support: Quote: "The Investigators, other study site personnel, the patients, and representatives of Genzyme Corporation, with the exception of Genzyme Clinical Pharmacy Research Services, remained blinded to treatment assignment for the duration of the study. Every effort was made to maintain the integrity of the blind." Comment: method not described.
- Evidence row: {}
- Source context preview: ## Study Design This study was a post-hoc analysis of cardiovascular parameters in a double-blind, multi-center, randomized controlled trial evaluating the efficacy and safety of acid alpha-glucosidase enzyme replacement therapy versus placebo in patients with late onset Pompe disease. The primary efficacy endpoints of the original trial consisted of the six minute walk test and the percent-predicted forced vital capacity in the upright position (ClinicalTrial.Gov identifier #NCT00158600; Protocol No. AGLU02704). Results of the primary analysis have been recently published (28). The present analysis focuses on evaluation of cardiovascular endpoints. This study was approved by the...

#### Blinding of outcome assessment: All outcomes

- Prediction: Low risk
- Ground truth: Unclear risk
- Match: False
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The review-relevant outcomes (echocardiographic measures and ECG parameters) are objective device-based assessments and were interpreted centrally by cardiologists blinded to allocation, making it unlikely that lack of blinding influenced outcome measurement.
- Model support: Quote: "All echocardiograms were interpreted at the central cardiology core lab by a cardiologist blinded to treatment allocation." Comment: Central blinded reading of ECGs and echocardiograms indicates outcome assessors for these objective cardiovascular outcomes were masked.
- Model support context: [{"source": "article", "quote": "All echocardiograms were interpreted at the central cardiology core lab by a cardiologist blinded to treatment allocation.", "relevance": "States that the echocardiogram assessor was blinded, reducing detection bias for imaging outcomes."}, {"source": "article", "quote": "All ECG’s were interpreted at the central cardiology core lab by a cardiologist blinded to treatment arm.", "relevance": "States that ECG assessors were blinded, reducing detection bias for ECG outcomes."}]
- GT support: Quote: "The Investigators, other study site personnel, the patients, and representatives of Genzyme Corporation, with the exception of Genzyme Clinical Pharmacy Research Services, remained blinded to treatment assignment for the duration of the study." Comment: method not described.
- Evidence row: {}
- Source context preview: ## Study Interventions and Data Collection Echocardiographic evaluation of left ventricular size and function was performed at baseline, 52 and 78 weeks. All echocardiograms were interpreted at the central cardiology core lab by a cardiologist blinded to treatment allocation. Left ventricular ejection fraction was calculated from two dimensional images using the modified Simpson’s rule in all patients. Abnormal ejection fraction was defined as < 55% (31). Left ventricular mass was evaluated using two-dimensional (2D) echocardiography and the truncated ellipsoid method (31). If the two-dimensional image quality was not sufficient, M-mode assessment was performed and left ventricular mass was...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: The report gives randomized numbers (60 vs 30), missing outcome counts (5 [8%] vs 4 [14%]), and explicit reasons that are similar across groups and largely unrelated to cardiovascular outcomes; the amount and nature of missing data are unlikely to bias the cardiovascular endpoints.
- Model support: Quote: "Five (8%) patients in the enzyme replacement therapy group and four (14%) patients in the placebo group did not complete the study." Comment: Attrition was small, reasonably balanced between arms with similar reasons and not related to cardiovascular outcomes, and analysis focused on those with complete baseline and follow-up data.
- Model support context: [{"source": "article", "quote": "Of 108 patients screened, 90 were randomized: 60 to the treatment arm and 30 to the control arm.", "relevance": "Provides randomized denominators by arm needed to assess attrition rates."}, {"source": "article", "quote": "Five (8%) patients in the enzyme replacement therapy group and four (14%) patients in the placebo group did not complete the study. Reasons...hypersensitivity(2), death unrelated(1), switch to commercial therapy(2); control: adverse event...", "relevance": "Shows missing counts by arm, percentages, and reasons which appear balanced and unlikely related to cardiovascular outcomes."}]
- GT support: Comment: intention-to-treat analysis.
- Evidence row: {}
- Source context preview: ## Efficacy of Enzyme Replacement Therapy Table 3 displays ECG and echocardiographic data at baseline and 78 weeks in the treatment and placebo arms for those who completed the study. Of patients with baseline ECG data, 89% had follow-up ECG data. Of patients with baseline echocardiographic data, 80% had follow up echocardiographic data. No significant changes in ECG or echocardiographic parameters were seen in association with enzyme replacement therapy compared with placebo. --- ## Patient Characteristics Of 108 patients screened, 90 were randomized: 60 to the treatment arm and 30 to the control arm. We excluded three patients < 17 years of age from the analysis as the ECG and...


## 21680092 - Turner 2011

- Mode: audited
- Review context: none (0 chars)
- Article chars: 53160
- Extraction context chars: n/a
- Total seconds: 43.66
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Low risk | yes | no_support_phrase_match |  |
| Allocation concealment | Low risk | Low risk | yes | no_support_phrase_match |  |
| Blinding of participants and personnel: All outcomes | High risk | High risk | yes | no_support_phrase_match |  |
| Blinding of outcome assessment: All outcomes | Unclear risk | High risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |
| Incomplete outcome data: All outcomes | Low risk | Low risk | yes | no_support_phrase_match |  |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly states the allocation list was generated with the S-PLUS 'sample' function and that block sizes were chosen randomly, which constitutes a computer random number method and meets the Low risk criteria.
- Model support: Quote: "The randomization list was prepared using the 'sample' function of the S-PLUS® statistical software (Insightful Corporation, Seattle, WA)." Comment: Sequence generation used a computer random sampling function, meeting criteria for a random component.
- Model support context: [{"source": "article", "quote": "The randomization list was prepared using the 'sample' function of the S-PLUS statistical software.", "relevance": "Specifies a computer-based random number/sample function used to generate the allocation sequence."}, {"source": "article", "quote": "Block sizes were equal to 3 or 6, and were chosen randomly with 2/3 and 1/3 probability.", "relevance": "Indicates random selection of block sizes, supporting a randomized sequence generation process."}]
- GT support: Stratified block randomisation undertaken by study assistant not involved in screening using a computer programme
- Evidence row: {}
- Source context preview: ## 2.4. Randomization Randomization to the three treatment groups was stratified by participant’s baseline chronic pain grade and recruitment source (U.W. Orofacial Pain Clinic new patient, U.W. Orofacial Pain Clinic return patient, and non-U.W. sources), and with blocking to ensure that the groups would be (nearly) balanced across the study period and within each stratum. Block sizes were equal to 3 or 6, and were chosen randomly with 2/3 and 1/3 probability, respectively. In addition, the number of women randomized to the COCT group was increased by 25% to allow for some disqualification at the ARNP visit. The randomization list was prepared using the “sample” function of the S-PLUS®...

#### Allocation concealment

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report specifies that sealed, sequentially numbered envelopes were prepared by a study assistant not involved in screening, and that assignments were concealed from enrolling personnel until opening, meeting the criteria for low risk.
- Model support: Quote: "Treatment assignments were recorded on cards numbered consecutively within each stratum, and a study assistant not involved in the screening and randomization put the randomization assignments in sealed envelopes sequentially numbered by stratum. Randomization assignments were concealed to all study personnel with study participant contact until envelopes were opened by research staff at the time of randomization." Comment: Sequentially numbered, sealed envelopes prepared and placed by staff not involved in enrollment indicate adequate allocation concealment.
- Model support context: [{"source": "article", "quote": "Treatment assignments were recorded on cards numbered consecutively within each stratum... put the randomization assignments in sealed envelopes sequentially numbered by stratum.", "relevance": "Describes use of sequentially numbered sealed envelopes for allocation concealment."}, {"source": "article", "quote": "Randomization assignments were concealed to all study personnel with study participant contact until envelopes were opened by research staff at the time of randomization.", "relevance": "States that personnel who enrolled participants could not see assignments before envelope opening."}]
- GT support: Sequence put into opaque, sequentially numbered envelopes by an assistant not otherwise involved in the study
- Evidence row: {}
- Source context preview: ## 2.4. Randomization Randomization to the three treatment groups was stratified by participant’s baseline chronic pain grade and recruitment source (U.W. Orofacial Pain Clinic new patient, U.W. Orofacial Pain Clinic return patient, and non-U.W. sources), and with blocking to ensure that the groups would be (nearly) balanced across the study period and within each stratum. Block sizes were equal to 3 or 6, and were chosen randomly with 2/3 and 1/3 probability, respectively. In addition, the number of women randomized to the COCT group was increased by 25% to allow for some disqualification at the ARNP visit. The randomization list was prepared using the “sample” function of the S-PLUS®...

#### Blinding of participants and personnel: All outcomes

- Prediction: High risk
- Ground truth: High risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The excerpts indicate participants knew they might receive COCT (medication) or SMT (behavioral), implying no effective participant blinding for these visibly different interventions; however the report does not state whether personnel were blinded or whether lack of blinding likely influenced the review outcomes (pain, disability, adverse events), so information is insufficient to classify as Low or High risk. Calibration: visibly different active interventions with subjective patient-reported outcomes make participant/personnel blinding unlikely and material.
- Model support: Quote: "Potential participants were told that the study involved randomization to COCT or to one of two different versions of SMT. At no time before or during study participation were participants informed that one and only one version focused on menstrual cycle-related changes." Comment: Participants were aware they could receive medication (COCT) or self-management therapy (SMT/TSMT), suggesting no participant blinding; report does not state whether personnel delivering interventions were blinded nor whether lack of blinding likely influenced reported outcomes (pain, disability, adverse events). Comment: Calibration: visibly different active interventions with subjective patient-reported outcomes make participant/personnel blinding unlikely and material.
- Model support context: [{"source": "article", "quote": "## 2.5. Interventions At their clinic visit with the study ARNP, women who were randomized to, and met all eligibility criteria for, COCT received instructions on use of the medication, potential breakthrough bleeding problems, backup...", "relevance": "Calibration: visibly different active interventions with subjective patient-reported outcomes make participant/personnel blinding unlikely and material."}, {"source": "article", "quote": "Potential participants were told that the study involved randomization to COCT or to one of two different versions of SMT.", "relevance": "Shows participants were informed about treatment options and not fully blinded to receiving medication vs behavioral therapy."}]
- GT support: Not possible to blind participants to the intervention received in this type of trial. Study assistant was blinded. All study personnel remained blind to assignment until the point of randomisation.
- Evidence row: {}
- Source context preview: ## 2.5. Interventions At their clinic visit with the study ARNP, women who were randomized to, and met all eligibility criteria for, COCT received instructions on use of the medication, potential breakthrough bleeding problems, backup birth control methods in the event of missed doses (for participants who were also using the study medication for birth control), and contact information for any medication-related questions. A 4-month supply of the medication (20 mcg ethinyl estradiol and 100 mcg levonorgestrel) was dispensed. At a second visit three months later, they received additional medication, for a total of six months on the medication. Women returned for a final visit just prior to...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: High risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The review-relevant outcomes (pain intensity and activity interference) were collected as standardized patient-reported numeric measures at prespecified timepoints; although assessors/research staff opened envelopes at randomization, outcome measurement consisted of structured self-report scales unlikely to be materially influenced by assessor knowledge, supporting Low risk. Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support: Quote: "Randomization assignments were concealed to all study personnel with study participant contact until envelopes were opened by research staff at the time of randomization." Comment: Outcome measurement (pain intensity, activity interference) used standardized self-report instruments and scheduled assessments at baseline, 6 and 12 months; these are objective patient-reported scales collected by research staff after allocation but there is no indication that assessor knowledge could bias automated/scored questionnaires. Comment: Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support context: [{"source": "article", "quote": "focused on menstrual cycle-related changes. All potential study participants completed a comprehensive clinical history questionnaire and had a comprehensive clinical dental examination to ensure there were no conditions that would...", "relevance": "Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported."}, {"source": "article", "quote": "Participants completed the study measures at the time of study enrollment (baseline, prior to randomization) and at 6 and 12 months after randomization.", "relevance": "Shows timing and that outcomes (pain, interference) were collected at scheduled follow-ups relevant to detection bias."}]
- GT support: Not possible to blind for self‐report outcome questionnaires. Blinding of outcome assessors is not explicitly reported.
- Evidence row: {}
- Source context preview: ## 2.7. Statistical analysis We did not make a statistical adjustment (e.g., Bonferroni method, which inflates type II error and reduces statistical power) for multiple testing. We expected moderate correlations of the outcome and process measures; patterns of significant differences among the study groups on multiple related measures would support an interpretation that the treatment had an effect on the constructs assessed by those measures. We included multiple measures within the outcome and process variable domains because it would be of interest to patients, clinicians, and researchers to know whether the interventions had a different impact on, for example, activity interference...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report gives randomized (n=191), withdrawals (n=20) with reasons for many withdrawals (medical contraindications concentrated in COCT), reports similar follow-up completion rates across arms, compares analyzed (n=147) to excluded (n=24) with no significant differences, and used multiple imputation with sensitivity analyses that did not change conclusions, indicating missing data unlikely to bias outcomes.
- Model support: Quote: "Among the 191 women who were randomized, 20 were withdrawn from the study (15 of whom were randomized to the COCT group but then withdrawn due to medical contra-indications). In each of the three groups, 86% of participants completed at least one follow-up assessment." Comment: Missing data were investigated, compared between excluded and analyzed participants, and multiple imputation was used with sensitivity analyses showing primary conclusions unchanged.
- Model support context: [{"source": "article", "quote": "Among the 191 women who were randomized, 20 were withdrawn... In each of the three groups, 86% of participants completed at least one follow-up assessment.", "relevance": "Provides randomized count, withdrawals, and overall follow-up completion rate and balance across groups."}, {"source": "article", "quote": "In the sensitivity analyses using multiple imputation for missing values, the primary conclusions remained unchanged;", "relevance": "Shows appropriate handling (multiple imputation) and that results were robust to missing data."}]
- GT support: Missing data clearly described and sensitivity analysis carried out regarding imputation and intention‐to‐treat strategy.
- Evidence row: {}
- Source context preview: ## 2.7. Statistical analysis In addition, we performed multiple imputation analyses for the outcomes of characteristic pain intensity and activity inference to assess the effect of missing data due to participants who provided no follow-up data. Baseline and follow-up values of characteristic pain intensity or activity inference, as well as a variable indicating assigned treatment, were used in the imputation of the missing values, which used a Markov Chain Monte Carlo (MCMC) method assuming an arbitrary missing data pattern and multivariate normality and a single chain to create five imputations using 200 burn-in iterations before the first imputation and 100 iterations between...


## 21723049 - Brewer 2011

- Mode: audited
- Review context: none (0 chars)
- Article chars: 30867
- Extraction context chars: n/a
- Total seconds: 44.37
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Low risk | yes | no_support_phrase_match |  |
| Allocation concealment | Low risk | Unclear risk | no | unknown | over-inferred_from_sparse_reporting |
| Blinding of participants and personnel: All outcomes | Unclear risk | Unclear risk | yes | article_absence_or_unclear |  |
| Blinding of outcome assessment: All outcomes | Unclear risk | Unclear risk | yes | unknown |  |
| Incomplete outcome data: All outcomes | Unclear risk | Unclear risk | yes | no_support_phrase_match |  |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The article explicitly reports a computer-generated urn randomization program, which is a random sequence generation method (computer-generated/minimization-style urn), meeting the Low risk criteria.
- Model support: Quote: "A computer-generated urn randomization program assigned participants to MT or FFS based on age (> vs. ≤ 40 years old), sex, race (white vs. non-white), and cigarettes smoked/day (> vs. ≤ 20)." Comment: The use of a computer-generated urn randomization program describes a random component meeting Low risk criteria.
- Model support context: [{"source": "article", "quote": "A computer-generated urn randomization program assigned participants to MT or FFS based on age, sex, race, and cigarettes smoked/day.", "relevance": "Explicit statement that sequence was generated by a computer-generated urn randomization program, indicating a random method."}]
- GT support: A computer-generated urn randomisation program assigned participants to MT or FFS based on age, sex, race, and cigarettes smoked/day.
- Evidence row: {}
- Source context preview: ## 2.3. Interventions A computer-generated urn randomization program assigned participants to MT or FFS based on age (> vs. ≤ 40 years old), sex, race (white vs. non-white), and cigarettes smoked/day (> vs. ≤ 20). All participants received twice weekly group sessions (eight total) that were manualized and delivered by instructors experienced in MT (a single therapist with >13 years of training in MT) or certified in FFS respectively (2 therapists with masters (+) level of training in drug counseling/health psychology). FFS was chosen as an active ‘standard treatment’ comparison condition for several reasons: 1) It has demonstrated efficacy (Lando et al., 1990), 2) is manualized and...

#### Allocation concealment

- Prediction: Low risk
- Ground truth: Unclear risk
- Match: False
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: The report states allocation was via a computer-generated urn randomization program, an automated centralized method meeting criteria for adequate concealment because recruiters could not foresee assignments.
- Model support: Quote: "A computer-generated urn randomization program assigned participants to MT or FFS based on age (> vs. ≤ 40 years old), sex, race (white vs. non-white), and cigarettes smoked/day (> vs. ≤ 20)." Comment: Use of a computer-generated urn randomization program implies centralized, automated assignment that recruiters could not foresee.
- Model support context: [{"source": "article", "quote": "A computer-generated urn randomization program assigned participants to MT or FFS", "relevance": "Describes an automated, centralized randomization method that prevents foreknowledge of upcoming allocations."}, {"source": "article", "quote": "This study was a randomized, controlled pilot trial with a four-week treatment", "relevance": "Confirms randomized design context in which concealment method would operate."}]
- GT support: No information
- Evidence row: {}
- Source context preview: ## 4.1. Strengths and Limitations Strengths of this pilot trial include the random assignment from a diverse community sample, the presence of an active comparison group, and the use of intent-to-treat analysis of our sample using validated outcome measures. This study has several limitations as well. This study was performed at a single site, treatment was provided by only 1–2 therapists per condition, and treatment integrity was not formally assessed. Thus treatment effects may not be generalized beyond the specific therapists in this trial (Crits-Christoph and Mintz, 1991). Also, it was of moderate size, and used an active comparison group, which typically limits the ability to detect...

#### Blinding of participants and personnel: All outcomes

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The excerpts describe clearly different behavioral group interventions delivered by identifiable therapists but do not report whether participants or personnel were blinded. Because blinding details are missing and the effect on subjective outcomes (e.g., mental distress, quality of life) cannot be judged from the text, risk of performance bias is unclear; necessary detail about who (if anyone) was blinded is not reported.
- Model support: Quote: "All participants received twice weekly group sessions (eight total) that were manualized and delivered by instructors experienced in MT (a single therapist with >13 years of training in MT) or certified in FFS respectively (2 therapists...)" Comment: The report describes different active group interventions delivered by different therapists, but does not state whether participants or personnel were blinded or whether any masking was attempted; insufficient information to judge influence of lack of blinding on outcomes.
- Model support context: [{"source": "article", "quote": "All participants received twice weekly group sessions... delivered by instructors experienced in MT (a single therapist...) or certified in FFS respectively (2 therapists...).", "relevance": "Shows interventions were distinct and delivered by different therapists, implying participants/personnel likely knew allocation but blinding is not reported."}, {"source": "article", "quote": "Strengths...the presence of an active comparison group...treatment was provided by only 1-2 therapists per condition, and treatment integrity was not formally assessed.", "relevance": "Confirms limited therapist pool and no assessment of masking; no explicit statement about participant or personnel blinding is provided."}]
- GT support: No information, but blinding unlikely. We have left as unclear risk as it is difficult, if not impossible, to blind participants and personnel to lifestyle interventions.
- Evidence row: {}
- Source context preview: ## 2.3. Interventions A computer-generated urn randomization program assigned participants to MT or FFS based on age (> vs. ≤ 40 years old), sex, race (white vs. non-white), and cigarettes smoked/day (> vs. ≤ 20). All participants received twice weekly group sessions (eight total) that were manualized and delivered by instructors experienced in MT (a single therapist with >13 years of training in MT) or certified in FFS respectively (2 therapists with masters (+) level of training in drug counseling/health psychology). FFS was chosen as an active ‘standard treatment’ comparison condition for several reasons: 1) It has demonstrated efficacy (Lando et al., 1990), 2) is manualized and...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: The review-relevant outcome 'one-week point prevalence abstinence' was verified by an objective CO measurement performed/recorded by a research assistant not involved in treatment; objective measurements by independent staff make detection bias unlikely, supporting Low risk. Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support: Quote: "Self-reported smoking was assessed at in-person weekly visits by a research assistant who was not involved in treatment delivery via the Timeline Follow Back method (TLFB)... Self-reported abstinence was assessed... and verified by an exhaled carbon monoxide (CO) measurement of ≤ 10 parts per million." Comment: The smoking outcome includes an objective CO measurement verified by research staff not involved in treatment delivery, reducing likelihood that assessor knowledge of allocation biased the primary outcome. Comment: Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support context: [{"source": "article", "quote": "## 2.4. Smoking Status Self-reported smoking was assessed at in-person weekly visits by a research assistant who was not involved in treatment delivery via the Timeline Follow Back method (TLFB) (Sobell and Sobell, 1992). Self-reported...", "relevance": "Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported."}, {"source": "article", "quote": "Self-reported smoking was assessed at in-person weekly visits by a research assistant who was not involved in treatment delivery via the Timeline Follow Back method (TLFB).", "relevance": "Identifies the assessor role (research assistant) and states they were not involved in treatment delivery, implying independence from intervention personnel."}]
- GT support: No information.
- Evidence row: {}
- Source context preview: ## 2.4. Smoking Status Self-reported smoking was assessed at in-person weekly visits by a research assistant who was not involved in treatment delivery via the Timeline Follow Back method (TLFB) (Sobell and Sobell, 1992). Self-reported abstinence was assessed using TLFB and verified by an exhaled carbon monoxide (CO) measurement of ≤ 10 parts per million at each of the twice-weekly treatment and at follow-up visits. Participants who dropped out of treatment were contacted to provide in-person assessments at follow-up time points (see CONSORT diagram) (Hollis and Campbell, 1999). All participants were financially compensated for assessment visits (10 USD per assessment visit during treatment...

#### Incomplete outcome data: All outcomes

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report mentions ITT mixed models and that one randomized person was excluded, and that incomplete data were handled via casewise deletion, but the supplied excerpts do not provide numbers randomized/analyzed/missing by arm, attrition counts, or balanced reasons for missingness; therefore reporting is insufficient to judge risk of bias from incomplete outcome data.
- Model support: Quote: "Longitudinal data were analyzed using intent-to-treat mixed effect regression models on the full sample of randomized subjects (minus one individual who was incarcerated after treatment and whose data were not allowed to be analyzed per Veteran’s Administration regulations) ... Incomplete data were handled using casewise deletion, using all available data for parameter estimates (Hedeker et al., 2007)." Comment: Study reports use of ITT mixed models but also casewise deletion and excludes one randomized participant; numbers randomized, analyzed and by-arm missing counts/reasons and balance are not presented in the supplied excerpts.
- Model support context: [{"source": "article", "quote": "Longitudinal data were analyzed using intent-to-treat mixed effect regression models on the full sample of randomized subjects (minus one individual who was incarcerated ...).", "relevance": "States ITT mixed models used but notes exclusion of one randomized participant; gives partial handling information."}, {"source": "article", "quote": "Incomplete data were handled using casewise deletion, using all available data for parameter estimates (Hedeker et al., 2007).", "relevance": "Describes approach to missing data (casewise deletion) but does not report randomized/analyzed/missing counts by arm or reasons and balance."}]
- GT support: Only 1 participant was excluded from ITT analysis because of incarceration. This participant was in the FFS group. In the FFS group, 8 participants were randomised but did not complete baseline assessment or start treatment and 32 completed treatment. In the MT group, 8 participants were randomised but did not complete baseline assessment or start treatment and 29 completed treatment. ITT analysis used for some but not all analyses.
- Evidence row: {}
- Source context preview: ## 3.2. Effects of Mindfulness Training on smoking Random effects regression analyses on the full intention to treat sample indicated participants in both groups reduced cigarette use from baseline through the 17-week follow-up (effect for time, F=480.79, df=1,1115, p<.0001). The rate of change during active treatment was significantly greater than the rate of change during post treatment (effect for phase, active versus follow-up, F=579.00, df=1,1115, p<.0001). During active treatment, individuals receiving MT demonstrated a greater reduction in cigarette use than those receiving FFS, and maintained these treatment gains during the follow-up period (treatment group × time, F=7.01,...


## 21775755 - Ziegler 2011

- Mode: audited
- Review context: none (0 chars)
- Article chars: 24371
- Extraction context chars: n/a
- Total seconds: 45.73
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Low risk | yes | no_support_phrase_match |  |
| Allocation concealment | Unclear risk | Low risk | no | article_text_match | under-called_due_to_missing_or_underused_evidence |
| Blinding of participants and personnel: All outcomes | Low risk | Low risk | yes | article_text_match |  |
| Blinding of outcome assessment: All outcomes | Low risk | Low risk | yes | no_support_phrase_match |  |
| Incomplete outcome data: All outcomes | Unclear risk | High risk | no | article_text_match | under-called_due_to_missing_or_underused_evidence |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly states a 'randomization list generated by the Biostatistics Department' and use of blocked randomization, which meets the criterion of a described random component for low risk.
- Model support: Quote: "Patients were assigned to the two treatment groups according to a randomization list generated by the Biostatistics Department of MEDA Pharma. The random allocation was balanced using an undisclosed block size of six." Comment: Describes a centrally generated randomization list with block randomization, indicating a random component.
- Model support context: [{"source": "article", "quote": "Patients were assigned... according to a randomization list generated by the Biostatistics Department of MEDA Pharma.", "relevance": "Specifies that the allocation list was generated by a biostatistics department, implying a random component to sequence generation."}, {"source": "article", "quote": "The random allocation was balanced using an undisclosed block size of six.", "relevance": "Indicates use of blocked randomization, supporting that sequence generation used a random method."}]
- GT support: Quote: "a randomization list was generated by the biostatistics department of the manufacturer of the study drug ..."
- Evidence row: {}
- Source context preview: ## Randomization Screened patients were assigned a unique five-digit number. Randomized patients were additionally assigned a four-digit randomization number at baseline. Patients were assigned to the two treatment groups according to a randomization list generated by the Biostatistics Department of MEDA Pharma. The random allocation was balanced using an undisclosed block size of six. The investigators and the monitor received sealed envelopes to enable decoding the individual blinded treatment in case of emergency. --- ## RESEARCH DESIGN AND METHODS The Neurological Assessment of Thioctic Acid in Diabetic Neuropathy (NATHAN) 1 trial was a multicenter (36 centers in the U.S., Canada, and...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: the random allocation was balanced using an undisclosed block size of six
- Model rationale: Although a central biostatistics department generated the randomization list, the article does not report the method used to conceal allocations at enrollment (e.g. central allocation, sealed opaque sequential envelopes with safeguards, or web/telephone system). The emergency sealed envelopes do not confirm allocation procedure, so information is insufficient to judge concealment.
- Model support: Quote: "Patients were assigned to the two treatment groups according to a randomization list generated by the Biostatistics Department of MEDA Pharma. The random allocation was balanced using an undisclosed block size of six. The investigators and the monitor received sealed envelopes to enable decoding the individual blinded treatment in case of emergency." Comment: A randomization list was generated centrally, but the report does not describe how assignments were implemented or whether the envelopes used for emergency decoding were the mechanism for allocation and whether they were opaque/sequential/secure, so concealment before assignment is unclear.
- Model support context: [{"source": "article", "quote": "Patients were assigned to the two treatment groups according to a randomization list generated by the Biostatistics Department of MEDA Pharma.", "relevance": "Shows a centrally generated randomization list but does not state how allocations were delivered to sites or whether recruiters were prevented from seeing..."}, {"source": "article", "quote": "The investigators and the monitor received sealed envelopes to enable decoding the individual blinded treatment in case of emergency.", "relevance": "Mentions sealed envelopes for emergency decoding only; does not describe use of sequentially numbered opaque sealed envelopes for allocation concealment."}]
- GT support: Quote: "a randomization list was generated by the biostatistics department of the manufacturer of the study drug, at distance of the centers the study took place"; "the random allocation was balanced using an undisclosed block size of six."
- Evidence row: {}
- Source context preview: ## Randomization Screened patients were assigned a unique five-digit number. Randomized patients were additionally assigned a four-digit randomization number at baseline. Patients were assigned to the two treatment groups according to a randomization list generated by the Biostatistics Department of MEDA Pharma. The random allocation was balanced using an undisclosed block size of six. The investigators and the monitor received sealed envelopes to enable decoding the individual blinded treatment in case of emergency. --- ## RESEARCH DESIGN AND METHODS The Neurological Assessment of Thioctic Acid in Diabetic Neuropathy (NATHAN) 1 trial was a multicenter (36 centers in the U.S., Canada, and...

#### Blinding of participants and personnel: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: matching placebo tablets with increased amounts of cellulose and lactose that were identical in appearance | matching placebo tablets with increased amounts
- Model rationale: The report explicitly describes a double-blind, placebo-controlled design with matching placebo tablets identical in appearance and emergency sealed envelopes for decoding, indicating blinding of participants and key personnel was implemented and unlikely to be broken, so risk of performance bias is Low.
- Model support: Quote: "randomized, double-blind, placebo-controlled... matching placebo tablets with increased amounts of cellulose and lactose that were identical in appearance" Comment: Participants and study personnel were blinded with visually identical placebo and active tablets, making performance bias unlikely for the trial outcomes.
- Model support context: [{"source": "article", "quote": "randomized, double-blind, placebo-controlled... matching placebo tablets with increased amounts of cellulose and lactose that were identical in appearance", "relevance": "Explicit statement that participants and personnel were blinded using identical placebo tablets."}, {"source": "article", "quote": "The investigators and the monitor received sealed envelopes to enable decoding the individual blinded treatment in case of emergency.", "relevance": "Indicates procedures to maintain the blind with emergency code-break envelopes."}]
- GT support: Quote: "... matching placebo tablets with increased amounts of cellulose and lactose that were identical in appearance." Comment: trial described as double-blind.
- Evidence row: {}
- Source context preview: ## RESEARCH DESIGN AND METHODS The Neurological Assessment of Thioctic Acid in Diabetic Neuropathy (NATHAN) 1 trial was a multicenter (36 centers in the U.S., Canada, and Europe [Supplementary Materials]), randomized, double-blind, placebo-controlled, two-arm, 1:1 allocation ratio, parallel-group clinical trial using film-coated tablets containing 600 mg ALA (Thioctacid HR; MEDA Pharma, Bad Homburg, Germany) that were administered once daily or matching placebo tablets with increased amounts of cellulose and lactose that were identical in appearance in diabetic patients with mild-to-moderate DSPN (18). The trial consisted of a 2-week screening phase, 6-week placebo run-in phase, 4-year...

#### Blinding of outcome assessment: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly describes a double-blind design with identical placebo and the review-relevant outcomes are largely objective electrophysiologic and device-measured tests; therefore detection bias is unlikely and risk is Low.
- Model support: Quote: "randomized, double-blind, placebo-controlled... matching placebo tablets with increased amounts of cellulose and lactose that were identical in appearance" Comment: Blinding was maintained and many key outcomes (nerve conduction measures, vibration detection thresholds, HRDB, lab-like electrophysiologic tests) are objective device/clinician-measured outcomes unlikely to be influenced by assessor knowledge of allocation.
- Model support context: [{"source": "article", "quote": "randomized, double-blind, placebo-controlled... matching placebo tablets with increased amounts of cellulose and lactose that were identical in appearance", "relevance": "States trial was double-blind with identical placebo, supporting that outcome assessors were unlikely to know allocation."}, {"source": "article", "quote": "primary outcome... NIS-LL+7 including vibration detection threshold, nerve conduction velocity, CMAP, sural sensory nerve action potential amplitude, and HRDB", "relevance": "Lists objective electrophysiologic and device-measured outcomes that are unlikely to be influenced by unblinded assessment."}]
- GT support: Quote: "The investigators and the monitor received sealed envelopes to enable decoding the individual blinded treatment in case of emergency."
- Evidence row: {}
- Source context preview: ## Outcomes Secondary outcome measures included the NIS, NIS-LL, Neuropathy Symptoms and Change (NSC) score, TSS, cooling detection threshold, heat pain response slope (0.5–5.0), tibial nerve CMAP and MNCV, sural sensory nerve action potential latency, and sensory nerve conduction velocity (SNCV). In a response/progression analysis after 2 and 4 years, a clinically meaningful response was defined as a decrease in NIS or NIS-LL by ≥2 points, respectively, while clinically meaningful progression was defined as an increase in NIS or NIS-LL by ≥2 points, respectively (16,17). --- ## RESEARCH DESIGN AND METHODS Exclusion criteria were neuropathies other than DSPN; myopathy and other neurologic...

#### Incomplete outcome data: All outcomes

- Prediction: Unclear risk
- Ground truth: High risk
- Match: False
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: mean of weeks 191 and 192 or last available value after randomization
- Model rationale: The excerpts mention planned sample size, ITT analysis, and a few treatment discontinuations, but do not report randomized counts, numbers analyzed for outcomes, total withdrawals/lost to follow-up by arm, or handling of missing data; therefore reporting is insufficient to judge attrition bias.
- Model support: Quote: "To account for a relatively high dropout rate expected in this long-term study, randomization of 250 patients per arm was proposed. Analysis of the intention-to-treat population was primary for all efficacy variables." Comment: Sample-size planning anticipated dropouts and ITT was primary, but the report excerpts do not provide randomized/enrolled numbers by arm, numbers analyzed, or actual missing outcome counts/reasons.
- Model support context: [{"source": "article", "quote": "randomization of 250 patients per arm was proposed. Analysis of the intention-to-treat population was primary for all efficacy variables.", "relevance": "Indicates anticipated dropout and planned ITT analysis but does not give actual attrition or numbers analyzed."}, {"source": "article", "quote": "Two (0.9%) patients on ALA and one (0.7%) patients on placebo discontinued study treatment as a result of lack of tolerability", "relevance": "Gives discontinuations due to tolerability but does not report total withdrawals, missing outcome data by arm, or reasons comprehensively."}]
- GT support: More than 40% of participants discontinued intervention in both groups during the 4-year study. We do not know how many participants were lost before the outcomes at 2 years (our outcome of interest), and how many after the first 2 years. Most participants (454/460) were included in the ITT analysis, but the study authors did not report for how many they managed to measure the outcome, and for how many they used the last observation carried forward ("mean of weeks 191 and 192 or last available value after randomization"). Apparently, the proportion of dropouts and the causes of dropout were equally distributed among the 2 groups.
- Evidence row: {}
- Source context preview: ## Statistical analysis We used a conservative approach to suggest that treatment with ALA may prevent worsening of DSPN but not necessarily cause improvement (16). A clinically meaningful treatment difference of 2.0 nds for the changes from baseline for NIS-LL+7 tests and statistical error probabilities α = 0.05 and β = 0.1 were assumed. Based on a two-sided t test, the following scenarios for SDs and sample size per group (n) were considered: SD 3.57, n = 68; SD 4, n = 86; SD 5, n = 133; SD 6, n = 191; SD 7, n = 211. To account for a relatively high dropout rate expected in this long-term study, randomization of 250 patients per arm was proposed. Analysis of the intention-to-treat...


## 21933436 - Dorresteijn 2016

- Mode: audited
- Review context: none (0 chars)
- Article chars: 27677
- Extraction context chars: n/a
- Total seconds: 47.44
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Low risk | yes | no_support_phrase_match |  |
| Allocation concealment | Low risk | Low risk | yes | unknown |  |
| Blinding of participants and personnel: All outcomes | Low risk | High risk | no | unknown | blinding_outcome_type_or_role_confusion |
| Blinding of outcome assessment: All outcomes | Unclear risk | Unclear risk | yes | no_support_phrase_match |  |
| Incomplete outcome data: All outcomes | Unclear risk | Low risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report states a computerised allocation conducted by an external agency and stratified block randomisation, which constitutes a random component (computer random generator) and meets the Low risk criteria for sequence generation.
- Model support: Quote: "Computerised alternative allocation was used in the randomisation process, which was performed by an external agency." Comment: A computerised/random component performed by an external agency indicates an appropriate random sequence generation method.
- Model support context: [{"source": "article", "quote": "Participants were assigned... using stratified randomisation. ... Computerised alternative allocation was used in the randomisation process, which was performed by an external agency.", "relevance": "Describes a computerised random allocation process performed externally, meeting criteria for a random number generator."}, {"source": "article", "quote": "This randomisation was performed in blocks of two on the basis of one prognostic factor: the level of concern about falls.", "relevance": "Specifies blocked stratified randomisation, supporting a structured random sequence generation."}]
- GT support: Randomisation conducted by an external agency blinded to participant characteristics.
- Evidence row: {}
- Source context preview: ## Randomisation Participants were assigned to the programme or the no-treatment control group directly after the baseline measurement using stratified randomisation. This randomisation was performed in blocks of two on the basis of one prognostic factor: the level of concern about falls (some, regular, often, and very often). Computerised alternative allocation was used in the randomisation process, which was performed by an external agency. --- ## Design The study concerns a two-group randomised controlled trial with a baseline measurement and follow-up measurements after 5 (directly after the programme) and 12 months (see Figure 1). The selection of potential participants was performed...

#### Allocation concealment

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: Allocation was generated by a computer and performed by an external agency, which constitutes centralised allocation and makes it unlikely that participants or investigators enrolling could foresee assignments.
- Model support: Quote: "Computerised alternative allocation was used in the randomisation process, which was performed by an external agency." Comment: Randomisation was computerised and performed by an external agency, indicating allocation was generated and handled away from recruiters, preventing foreseeability.
- Model support context: [{"source": "article", "quote": "Computerised alternative allocation was used in the randomisation process, which was performed by an external agency.", "relevance": "Indicates centralised, computerised randomisation by an external agency, supporting concealment from enrolling personnel."}, {"source": "article", "quote": "Participants were assigned ... directly after the baseline measurement using stratified randomisation.", "relevance": "Shows assignment occurred post-baseline and randomisation was external, reducing risk that recruiters could foresee allocations."}]
- GT support: Outcome assessors blinded to the allocation.
- Evidence row: {}
- Source context preview: ## Recruitment of participants Three communities, Maastricht, Sittard-Geleen, and Heerlen, situated in the southeast of The Netherlands have been selected for participation in the trial. The municipal registry offices selected 11,490 addresses of community-dwelling people of 70 years or over in their district, at random. To screen for eligibility, people received a short postal questionnaire with a freepost envelope, as well as information about the trial and an informed consent form. After a fortnight, reminder letters were sent. The questionnaire assessed socio-demographics and fall-related variables and inclusion and exclusion criteria. --- ## Randomisation Participants were assigned to...

#### Blinding of participants and personnel: All outcomes

- Prediction: Low risk
- Ground truth: High risk
- Match: False
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: Trained interviewers who collected effect data were explicitly blinded, and key outcomes include prospectively recorded falls (fall calendars) and a standardized disability scale; therefore lack of participant blinding is unlikely to have materially influenced the measured outcomes.
- Model support: Quote: "Data for the effect evaluation is gathered by means of telephone interviews which are conducted by trained interviewers, who are blinded for group allocation." Comment: Outcome data collection was performed by blinded interviewers and key outcomes (falls via calendar, disability via standard scale) are objective or collected by blinded staff, so lack of participant blinding is unlikely to have materially influenced these outcomes.
- Model support context: [{"source": "article", "quote": "Data for the effect evaluation is gathered by means of telephone interviews which are conducted by trained interviewers, who are blinded for group allocation.", "relevance": "Shows interviewers collecting effect outcomes were blinded, reducing performance bias from personnel."}, {"source": "article", "quote": "The number of falls is registered continuously during the course of the trial by a fall calendar.", "relevance": "Falls are recorded prospectively via calendars (objective event counts), less likely influenced by participant/ personnel knowledge."}]
- GT support: Blinding of participants not possible due to nature of intervention.
- Evidence row: {}
- Source context preview: ## Randomisation Participants were assigned to the programme or the no-treatment control group directly after the baseline measurement using stratified randomisation. This randomisation was performed in blocks of two on the basis of one prognostic factor: the level of concern about falls (some, regular, often, and very often). Computerised alternative allocation was used in the randomisation process, which was performed by an external agency. --- ## Design The study concerns a two-group randomised controlled trial with a baseline measurement and follow-up measurements after 5 (directly after the programme) and 12 months (see Figure 1). The selection of potential participants was performed...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report states that trained telephone interviewers assessing effect outcomes were blinded to allocation (assessor role) and falls were recorded via monthly calendars, so outcome measurement was unlikely to be influenced by knowledge of allocation; therefore Low risk. Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support: Quote: "Data for the effect evaluation is gathered by means of telephone interviews which are conducted by trained interviewers, who are blinded for group allocation." Comment: Outcome assessors (telephone interviewers) were explicitly blinded, reducing risk of detection bias for self-reported outcomes. Comment: Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support context: [{"source": "article", "quote": "ling people of 70 years or over in their district, at random. To screen for eligibility, people received a short postal questionnaire with a freepost envelope, as well as information about the trial and an informed consent form. After a...", "relevance": "Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported."}, {"source": "article", "quote": "Data for the effect evaluation is gathered by means of telephone interviews which are conducted by trained interviewers, who are blinded for group allocation.", "relevance": "Shows outcome assessment was performed by blinded interviewers, directly addressing detection bias."}]
- GT support: Assessors blinded, but outcomes were self-reported by participants who knew their group allocation.
- Evidence row: {}
- Source context preview: ## Outcomes ### Primary outcome measures --- ## Outcomes ### Secondary outcome measures --- ## Data collection Data for the effect evaluation is gathered by means of telephone interviews which are conducted by trained interviewers, who are blinded for group allocation. For the assessment of fall accidents, participants received a fall calendar after the baseline measurement. Every month, a sheet of the calendar has to be returned via a freepost envelope. People are reminded by telephone after one-and-half weeks if a sheet is not returned. --- ## Analysis Descriptive techniques will be used to describe the study groups. Baseline variables will be compared, to detect differences between the...

#### Incomplete outcome data: All outcomes

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The excerpts describe planned ITT analysis and follow-up procedures but do not report randomized or analyzed counts, attrition by arm, reasons for missing data, or actual imputation/handling; therefore reporting is insufficient to permit a judgement.
- Model support: Quote: "Data of the effect evaluation will be analysed according to both the intention-to-treat and per-protocol principles. In the first analyses all participants will be included according to their original assignment... Non-compliant participants of the programme group are approached for all follow-up measurements, and participants with missing data are contacted to ensure completion of data" Comment: The report describes intended handling (ITT, follow-up contacts) but does not provide randomized, analyzed, or missing outcome counts by arm, nor reasons for attrition, so risk of bias due to incomplete outcome data cannot be judged.
- Model support context: [{"source": "article", "quote": "Data of the effect evaluation will be analysed according to both the intention-to-treat and per-protocol principles. In the first analyses all participants will be included according to their original assignment", "relevance": "States planned ITT analysis but gives no actual numbers of randomized/analyzed or missing outcomes by arm."}, {"source": "article", "quote": "Non-compliant participants of the programme group are approached for all follow-up measurements, and participants with missing data are contacted to ensure completion of data", "relevance": "Describes efforts to reduce missing data but does not report amounts, balance, reasons, or how missingness was handled in analysis."}]
- GT support: Study authors conducted intention-to-treat analysis and imputed missing data.
- Evidence row: {}
- Source context preview: ## Analysis Descriptive techniques will be used to describe the study groups. Baseline variables will be compared, to detect differences between the participants of both groups at the start of the study. Data of the effect evaluation will be analysed according to both the intention-to-treat and per-protocol principles. In the first analyses all participants will be included according to their original assignment [52]. Participants of the intervention group who attended at least five of the seven programme sessions will be included in the per-protocol analysis. Based on prior work, five sessions of the programme are considered as sufficient programme exposure [15,18]. Mixed-effects...

## Workflow Evolution Notes

- Inspect mismatches where prediction is `Unclear risk` but GT is `Low risk`: these usually mean retrieval or Stage 1 extraction missed a concrete methodological phrase.
- Inspect mismatches where prediction is `Low risk` or `High risk` but GT is `Unclear risk`: these usually mean the prompt is allowing too much inference from generic trial language.
- For blinding mismatches, add outcome-type cues to the prompt: self-report outcomes, objective outcomes, assessor-administered outcomes, and whether lack of blinding can materially affect the outcome.
- For allocation concealment mismatches, require the model to distinguish sequence generation from concealment before assignment.