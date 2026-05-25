# Batch Risk of Bias Eval Report

This report contains an audit trace: explicit extracted evidence, model-provided rationales, and label comparisons. It does not include hidden chain-of-thought.

- Studies: 20
- Domains: 100
- Accuracy: 56/100 (56.0%)
- Article-only scorable accuracy: 15/28 (53.6%)
- Article-observable accuracy: 15/28 (53.6%)
- Non-observable/article-missing GT accuracy: 33/57 (57.9%)
- External/review-context GT domains: 0/1 matched
- Unknown or non-text GT domains: 15
- Timeout retries recovered: 0

Interpretation note: `Article-only scorable` is the fairest metric for the current direct input contract (`sr_pico + xml_content + domain`). External/review-context rows often require author emails, protocols, registries, tables/figures, or review notes that are not present in the XML excerpts.

## Summary

| PMID | Study | Correct | Accuracy | Seconds | Retry |
|---|---|---:|---:|---:|---|
| 14647140 | Clayton 2007 | 1/5 | 20.0% | 27.05 |  |
| 17389922 | Cobo 2007 | 4/5 | 80.0% | 27.17 |  |
| 18398460 | Menéndez 2008 | 5/5 | 100.0% | 32.85 |  |
| 18779465 | Grant 2008 | 3/5 | 60.0% | 28.75 |  |
| 19209172 | Vodermaier 2009 | 1/5 | 20.0% | 25.47 |  |
| 19291323 | Middleton 2011 | 2/5 | 40.0% | 29.89 |  |
| 19319218 | Chien 2008a | 3/5 | 60.0% | 24.17 |  |
| 19487623 | King 2009 | 3/5 | 60.0% | 28.09 |  |
| 19798037 | Nidich 2009 | 1/5 | 20.0% | 24.56 |  |
| 20044929 | Hegarty 2013 | 3/5 | 60.0% | 24.68 |  |
| 20395225 | Alvarez 2010 | 3/5 | 60.0% | 24.03 |  |
| 20655662 | Litt 2010 | 4/5 | 80.0% | 25.95 |  |
| 20740213 | Jo 2010 | 4/5 | 80.0% | 24.34 |  |
| 20830695 | Deblinger 2011 | 2/5 | 40.0% | 25.04 |  |
| 21342490 | Freeman 2011 | 2/5 | 40.0% | 26.07 |  |
| 21543987 | Van der Ploeg 2010 | 2/5 | 40.0% | 22.55 |  |
| 21680092 | Turner 2011 | 4/5 | 80.0% | 27.07 |  |
| 21723049 | Brewer 2011 | 3/5 | 60.0% | 26.00 |  |
| 21775755 | Ziegler 2011 | 3/5 | 60.0% | 24.73 |  |
| 21933436 | Dorresteijn 2016 | 3/5 | 60.0% | 24.60 |  |

## Error Types

- gt_support_not_found_in_article_text: 23
- over-inferred_from_sparse_reporting: 10
- under-called_due_to_missing_or_underused_evidence: 4
- figure_table_or_supplement_needed: 3
- allocation_concealment_detail_threshold: 1
- attrition_balance_or_missing_data_handling: 1
- blinding_outcome_type_or_role_confusion: 1
- external_or_review_context_needed: 1

## 14647140 - Clayton 2007

- Mode: direct
- Review context: none (0 chars)
- Article chars: 24130
- Extraction context chars: n/a
- Total seconds: 27.05
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
| Incomplete outcome data: All outcomes | Unclear risk | Low risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |

### Audit Details

#### Random sequence generation

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: figure_table_or_supplement_reference (article observable: None)
- GT support phrase hits: 
- Model rationale: The supplied excerpts contain no description of how participants were allocated or any random component (random number table, computer generator, coin toss, minimization, etc.). Because the method of sequence generation is not reported in the excerpts, risk of bias for sequence generation is unclear.
- Model support: Quote: "Whether this was a result of seeing the doctor or the use of the QPL is unclear from the design of the study..." Comment: The report gives no description of allocation or how any sequence was generated; the necessary randomization method is not reported.
- Model support context: [{"source": "article", "quote": "Whether this was a result of seeing the doctor or the use of the QPL is unclear from the design of the study", "relevance": "Indicates study design details about intervention effects are unclear; no description of sequence generation is provided in the excerpts."}, {"source": "not_reported", "quote": "No text describing random sequence generation (computer/coin/table, random number, minimization) is included in supplied excerpts", "relevance": "Specifies the missing information needed to judge random sequence generation as Low or High risk."}]
- GT support: Individually randomised and stratified by physician – random permuted blocks of 10 constructed using random number table (by research assistant not involved in recruitment)
- Evidence row: {}
- Source context preview: ## Data collection and analysis The focus groups and telephone interviews were audiotaped and fully transcribed. Data analysis was informed by qualitative methodology (Pope and Mays, 2000). Individual questions or information needs were identified from the transcripts using the participants' own language where possible. These were discussed by both facilitators to ensure consistency of interpretation and were organised into categories to facilitate comprehension, as suggested by Ley (1988). Further focus groups and/or telephone interviews were conducted until no additional topics were raised. A draft QPL was developed using the categories and questions identified in the transcripts. The...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The excerpts do not describe any allocation procedure or safeguards (central randomization, sealed opaque envelopes, etc.). Necessary details about how assignments were concealed prior to enrollment are missing, so risk is unclear.
- Model support: Quote: "We thank the research nurses... who assisted with patient recruitment and data collection in the pilot study." Comment: The report does not describe the method used to conceal allocation (no mention of envelopes, central randomization, or other safeguards), so concealment cannot be judged.
- Model support context: [{"source": "article", "quote": "We thank the research nurses... who assisted with patient recruitment and data collection in the pilot study.", "relevance": "Identifies recruiters but gives no information on allocation concealment procedures."}, {"source": "article", "quote": "Whether this was a result of seeing the doctor or the use of the QPL is unclear from the design of the study", "relevance": "States study design limitations but does not report any concealment method for allocation."}]
- GT support: Allocations were concealed using sequentially numbered opaque sealed envelopes
- Evidence row: {}
- Source context preview: ## Results of focus groups and individual interviews General questions included how and when to contact the PC team, and the connection between the PC team and other health professionals involved in the patients' care. In addition, some patients wanted advice about how to choose another doctor. A second opinion was valued regarding disease-specific treatment from an independent source. Others wanted to discuss the option of stopping anticancer treatment or not starting it at all. --- ## Results of pilot study Patients' views about the QPL are outlined in Table 2Table 2Patient and carer feedback about QPL from pilot study Post consultation questionnaire refers to consultation immediately...

#### Blinding of participants and personnel: All outcomes

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The excerpts show a pilot of a question prompt list with patient questionnaires (self-reported outcomes) but provide no information on whether participants or clinical staff were blinded. Because blinding status and its potential influence on subjective outcomes are not reported, the risk is unclear.
- Model support: Quote: "We piloted the final draft QPL in 23 patients seeing one of three PC doctors from three services in Sydney... Of the 23 participants, 20 completed their post consultation questionnaires... 11 patients completed the 3-week follow-up questionnaires" Comment: The report does not state whether participants or clinical staff were blinded to allocation (QPL vs usual care) or whether the intervention was delivered open-label, so risk due to performance bias cannot be judged.
- Model support context: [{"source": "article", "quote": "We piloted the final draft QPL in 23 patients seeing one of three PC doctors", "relevance": "Describes the intervention delivery setting but gives no information on blinding of participants or personnel."}, {"source": "article", "quote": "Of the 23 participants, 20 completed their post consultation questionnaires ... 11 patients completed the 3-week follow-up questionnaires", "relevance": "Shows outcomes were patient-reported (questionnaires) but does not report whether participants or staff were blinded."}]
- GT support: Physicians were unblinded; authors note that prior research has indicated that QPL require professional endorsement in consultations to be effective Unclear whether or not patients and carers were blinded to intervention and/or what effect this may have had on the outcomes
- Evidence row: {}
- Source context preview: ## Participants Three groups felt to have important input were sampled: (a) PC patients, (b) carers of PC patients, and (c) health professionals working in PC. Patients and carers were eligible to take part if they were: (1) over 18 years of age, (2) English speaking, (3) well enough to participate, (4) able to give informed consent, and (5) referred to a specialist PC service and diagnosed with an incurable and progressive illness, or the carer of such a patient. In all, 19 patients and 24 carers were recruited from hospitals, PC units and the community in three PC services in Sydney. Their demographic characteristics are shown in Table 1Table 1Demographic and disease characteristics of...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The outcome assessed is self-reported anxiety (Spielberger inventory) collected by patients; the excerpts do not state whether patients or any outcome assessors were blinded to allocation. Because blinding status is not reported and self-reported outcomes are susceptible to detection bias, there is insufficient information to judge Low or High risk.
- Model support: Quote: "patients completed a questionnaire regarding their information and involvement (decisional control) preferences, and anxiety levels... Patient anxiety was measured by the Spielberger State Anxiety Inventory (Spielberger, 1983) (20 items)" Comment: Outcome is self-reported anxiety measured by patients, but the report does not state whether outcome assessors or patients were blinded to allocation.
- Model support context: [{"source": "article", "quote": "Prior to the consultation, patients completed a questionnaire... Patient anxiety was measured by the Spielberger State Anxiety Inventory", "relevance": "Shows the review-relevant outcome (patient-reported anxiety) and that patients themselves assessed it."}, {"source": "article", "quote": "After each consultation... patients also completed a questionnaire measuring anxiety and responses to the QPL using standard items.", "relevance": "Indicates timing of outcome collection but gives no information about blinding of patients or outcome assessors."}]
- GT support: Authors indicate that consultations were audiotaped, transcribed and analysed by blinded coders "Two coders were trained and blinded to group allocation. One coder coded all transcripts and recoded a random 10% to determine intrarater reliability. The second coder coded a random 10% of transcripts to determine inter‐rater reliability" (page 716)
- Evidence row: {}
- Source context preview: ## Data collection and analysis Prior to the consultation, patients completed a questionnaire regarding their information and involvement (decisional control) preferences, and anxiety levels. General preferences for information were assessed using a question from the Cassileth Information Styles Questionnaire measuring the type of information preferred (Cassileth et al, 1980). Preferences for decisional control were assessed using a validated and reliable question from previous studies in cancer patients (Sutherland et al, 1989; Degner et al, 1997b). Patients were classified as wanting an ‘active’, ‘passive’ or ‘collaborative’ role when making decisions about treatment. Patient anxiety was...

#### Incomplete outcome data: All outcomes

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report gives overall attrition counts and reasons but does not present randomized/analyzed denominators or missing outcome counts by arm nor describe imputation/analysis methods; these missing details prevent judging risk, so Unclear risk is appropriate.
- Model support: Quote: "Of the 23 participants, 20 completed their post consultation questionnaires, the remaining three became acutely unwell but gave verbal feedback to the research nurse following the consultation. In all, 11 patients completed the 3-week follow-up questionnaires (five patients were too unwell, four died, two did not respond to a reminder and one patient's carer requested no further involvement)." Comment: Attrition numbers are reported overall but not by trial arm (no randomization/allocation details or analysis denominators by group), and handling/imputation of missing outcomes is not described.
- Model support context: [{"source": "methodology", "quote": "Quote: \"Of the 23 participants, 20 completed their post consultation questionnaires, the remaining three became acutely unwell but gave verbal feedback to the research nurse following the consultation. In all, 11 patients completed the...", "relevance": "Recovered from malformed JSON; inspect raw output if this judgement matters."}]
- GT support: Low levels of loss to follow‐up 4/174; balanced across groups (n = 2 each), with comparable reasons
- Evidence row: {}
- Source context preview: ## Results of pilot study Of the 23 participants, 20 completed their post consultation questionnaires, the remaining three became acutely unwell but gave verbal feedback to the research nurse following the consultation. In all, 11 patients completed the 3-week follow-up questionnaires (five patients were too unwell, four died, two did not respond to a reminder and one patient's carer requested no further involvement). --- ## Results of pilot study Patients' views about the QPL are outlined in Table 2Table 2Patient and carer feedback about QPL from pilot study Post consultation questionnaire refers to consultation immediately after receiving QPL (n=20)3-week follow-up refers to use of QPL...


## 17389922 - Cobo 2007

- Mode: direct
- Review context: none (0 chars)
- Article chars: 22398
- Extraction context chars: n/a
- Total seconds: 27.17
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
- Model rationale: The report states a computer program performed random allocation with stratification and minimization. Minimization is accepted as equivalent to random sequence generation, and a computer-based method indicates a random component, meeting the Low risk criteria.
- Model support: Quote: "manuscripts were randomly allocated (by AS) using a computer program that first stratifies by study type, and second allocates to intervention groups while minimizing differences in initial quality." Comment: The use of a computer program and minimization describes a random component in sequence generation.
- Model support context: [{"source": "article", "quote": "manuscripts were randomly allocated (by AS) using a computer program that first stratifies by study type, and second allocates to intervention groups while minimizing differences in initial quality.", "relevance": "Describes sequence generation using a computer program and minimization, which constitutes a random component."}, {"source": "article", "quote": "We randomly allocated the manuscripts accepted for review into four groups defined by the interventions", "relevance": "Confirms that allocation was randomized into intervention groups."}]
- GT support: Quote: "We randomly allocated the manuscripts accepted for review into four groups defined by the interventions"; "Then, manuscripts were randomly allocated (by AS) using a computer program that first stratifies by study type, and second allocates to intervention groups while minimizing differences in initial quality. Then, the manuscripts followed the proper editorial procedure, according to their assigned group."
- Evidence row: {}
- Source context preview: ## Enrolment and Randomization Of the 327 originals received between May 2004 and March 2005, 196 (59.9%) were directly rejected by the editorial team. The remaining 131 (40.1%) were selected by the editorial committee as possible publications and therefore randomized. Of these, 2 were excluded either as a result of an administrative error (n = 1) or because the authors refused to participate (n = 1). From the 129 randomized manuscripts, 14 were lost of follow up because authors missed the deadline and the masked allocation was revealed; 21 (18.3%) of the 115 included papers were “interventions”, but only 3 were randomized clinical trials, 46 (40.0%) were longitudinal designs, 28 (24.3%)...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The excerpts describe computer-based random allocation and timing but do not report any method to prevent investigators/enrollers from foreseeing assignments (no central system, sealed envelopes, or other concealment details). Therefore allocation concealment cannot be judged from the supplied text.
- Model support: Quote: "manuscripts were randomly allocated (by AS) using a computer program that first stratifies by study type, and second allocates to intervention groups while minimizing differences in initial quality." Comment: Random allocation method is described, but the report does not state how the allocation sequence was concealed from those enrolling manuscripts (e.g. central assignment, sealed envelopes, or other safeguards).
- Model support context: [{"source": "article", "quote": "manuscripts were randomly allocated (by AS) using a computer program that first stratifies by study type, and second allocates to intervention groups while minimizing differences in initial quality.", "relevance": "Describes sequence generation method but gives no information on concealment or who had access to the allocation list."}, {"source": "article", "quote": "Papers were randomized once the two clinical peers had been chosen.", "relevance": "Timing of randomization relative to reviewer selection is given, but no details on measures preventing foreseeability of assignments are reported."}]
- GT support: Insufficient reporting of the allocation procedure.
- Evidence row: {}
- Source context preview: ## Assessment and Procedure Two evaluators (EC, RD) independently rated the reporting quality of manuscripts at initial submission and following peer review and revision, according to the MQAI. Both knew the initial and final status but were blinded to the intervention group. The final score awarded to each scale item was reached by averaging the two evaluators' item scores after allowing each one to modify his or her score once the reasons for the other evaluator's score was made known. Primary outcome was defined as the difference in the quality of papers between the initial and final submission, expressed as the sum of the 36 specific MQAI items, resulting in a minimum of 36 (lowest...

#### Blinding of participants and personnel: All outcomes

- Prediction: Low risk
- Ground truth: Unclear risk
- Match: False
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: Outcome is an assessor-rated MQAI score collected by two evaluators who were blinded to intervention allocation, and the checklist-based measurement is unlikely to be influenced by lack of blinding of other trial personnel; therefore performance bias risk is low.
- Model support: Quote: "Both knew the initial and final status but were blinded to the intervention group." Comment: The two evaluators who rated the primary outcome were blinded to group allocation, and the outcome (change in manuscript quality scored via MQAI) is an assessor-rated objective checklist-based score, making it unlikely that lack of blinding of other personnel would influence this outcome.
- Model support context: [{"source": "article", "quote": "Both knew the initial and final status but were blinded to the intervention group.", "relevance": "Shows outcome assessors (the two evaluators) were masked to allocation when rating the primary outcome."}, {"source": "article", "quote": "Primary outcome was defined as the difference in the quality of papers... expressed as the sum of the 36 specific MQAI items.", "relevance": "Identifies the outcome as an assessor-rated MQAI score (structured checklist), less likely to be biased by participants/personnel knowledge."}]
- GT support: Unclear if the editorial team was blinded. Apart from half of them receiving the intervention, the clinical reviewers seem to be unaware of the study objective and randomization. Unclear whether it is possible for a reviewer to be in multiple intervention groups, based on randomization of manuscripts and the possibility for receiving several manuscripts over the trial period.
- Evidence row: {}
- Source context preview: ## Enrolment and Randomization Of the 327 originals received between May 2004 and March 2005, 196 (59.9%) were directly rejected by the editorial team. The remaining 131 (40.1%) were selected by the editorial committee as possible publications and therefore randomized. Of these, 2 were excluded either as a result of an administrative error (n = 1) or because the authors refused to participate (n = 1). From the 129 randomized manuscripts, 14 were lost of follow up because authors missed the deadline and the masked allocation was revealed; 21 (18.3%) of the 115 included papers were “interventions”, but only 3 were randomized clinical trials, 46 (40.0%) were longitudinal designs, 28 (24.3%)...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The outcome is manuscript quality assessed by two evaluators (assessors) who were explicitly blinded to intervention allocation; blinding was assessed and appears maintained, so detection bias is unlikely. Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support: Quote: "Two evaluators (EC, RD) independently rated the reporting quality of manuscripts at initial submission and following peer review and revision...Both knew the initial and final status but were blinded to the intervention group." Comment: Outcome assessors (two evaluators) were explicitly blinded to intervention allocation, making detection bias unlikely. Comment: Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support context: [{"source": "article", "quote": "## Assessment and Procedure Two evaluators (EC, RD) independently rated the reporting quality of manuscripts at initial submission and following peer review and revision, according to the MQAI. Both knew the initial and final status but...", "relevance": "Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported."}, {"source": "article", "quote": "Two evaluators (EC, RD) independently rated...Both knew the initial and final status but were blinded to the intervention group.", "relevance": "States that the outcome assessors were blinded to allocation, directly addressing detection bias."}]
- GT support: Quote: "Two evaluators (EC, RD) independently rated the reporting quality of manuscripts at initial submission and following peer review and revision, according to the MQAI. Both knew the initial and final status but were blinded to the intervention group."; "On the use of a checklist, the evaluators were able to guess the intervention group in 65.3% (95% CI from 53.5 to 76.0%) of the 75 over 99 (75.8%) cases analyzed." According to the authors the overall conclusion the main effects remained the same after stratifying by response to both of the blinding questions. However, the data are not provided.
- Evidence row: {}
- Source context preview: ## Assessment and Procedure Two evaluators (EC, RD) independently rated the reporting quality of manuscripts at initial submission and following peer review and revision, according to the MQAI. Both knew the initial and final status but were blinded to the intervention group. The final score awarded to each scale item was reached by averaging the two evaluators' item scores after allowing each one to modify his or her score once the reasons for the other evaluator's score was made known. Primary outcome was defined as the difference in the quality of papers between the initial and final submission, expressed as the sum of the 36 specific MQAI items, resulting in a minimum of 36 (lowest...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The report gives randomized (129) and missing (14) counts with reasons, shows missing papers had similar baseline quality to retained papers, and sensitivity analyses with imputed values produced similar conclusions; these factors meet criteria that reasons for missing outcome data are unlikely to be related to true outcome, supporting Low risk.
- Model support: Quote: "From the 129 randomized manuscripts, 14 were lost of follow up because authors missed the deadline and the masked allocation was revealed;... In the sensitive-analyses populations, we reached the same conclusions about those effects. Referring to the impact of non-complete data, the 14 papers lost to follow-up had a heterogeneous distribution among the randomized groups ... but did not differ, in terms of baseline quality, from the originals in the accepted manuscripts population. We performed several sensitivity analyses including those papers with different imputed values for the final version that produced very similar conclusions." Comment: Reasons for missingness are reported, baseline quality of missing papers was similar to retained papers, missing papers were examined in sensitivity analyses with imputation and conclusions were robust, supporting low risk of attrition...
- Model support context: [{"source": "article", "quote": "From the 129 randomized manuscripts, 14 were lost of follow up because authors missed the deadline and the masked allocation was revealed", "relevance": "Reports number randomized (129) and number lost to follow-up (14) plus reason for missingness."}, {"source": "article", "quote": "The 14 papers lost to follow-up did not differ, in terms of baseline quality, from the originals in the complete population. ... We performed several sensitivity analyses including those papers with different imputed values... produced...", "relevance": "States missing were similar at baseline and sensitivity analyses with imputation gave similar results, suggesting missingness unlikely to bias outcomes."}]
- GT support: 5 manuscripts in the control group and 4 in the intervention group were lost to follow-up. However, this was before the intervention was delivered and was due to the authors not responding within the deadline. It is unlikely this would have affected the outcome in any meaningful way. After the reviews, 5 manuscripts were rejected in each group. It is unclear if the editors rejecting were blinded or not. However, it is unlikely that this would have had an effect on the result as the rejected manuscripts were of low quality.
- Evidence row: {}
- Source context preview: ## Study populations Three different populations were considered: “complete” which included all randomized manuscripts not lost to follow-up, which was the population for the main analysis. Two other populations were defined for the sensitive analyses: one taking into consideration all “randomized” manuscripts and one including only those manuscripts accepted for publication. Those manuscripts rejected due to reviewers' comments and those lost to follow-up were analyzed considering two different values for their final quality: 1) the initial overall quality was imputed as the final overall quality interpreted as no change in quality during the editorial process), or 2) the final overall...


## 18398460 - Menéndez 2008

- Mode: direct
- Review context: none (0 chars)
- Article chars: 20345
- Extraction context chars: n/a
- Total seconds: 32.85
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
- Model rationale: The report explicitly states a computer-generated sequential list with random ordering was used to link study numbers to treatment, satisfying the Low risk criteria for random sequence generation.
- Model support: Quote: "A computer-generated sequential list contained the study numbers linked to treatment identification letters, randomly ordered in blocks of 10." Comment: The sequence was produced by a computer-generated random list, which is an adequate random component.
- Model support context: [{"source": "article", "quote": "After written informed consent was obtained, the lowest available study number was assigned. A computer-generated sequential list contained the study numbers linked to treatment identification letters, randomly ordered in blocks of 10.", "relevance": "Describes computer-generated random list linking study numbers to treatments, indicating adequate random sequence generation."}]
- GT support: A computer-generated sequential list contained the study numbers linked to treatment identification letters, randomly ordered in blocks of 10. After written informed consent was obtained, the lowest available study number was assigned.
- Evidence row: {}
- Source context preview: ## Enrolment and interventions From August 2003 to April 2005 pregnant women were enrolled at the MDH ANC if their gestational age was ≤ 28 weeks, they did not report allergies to sulpha drugs, and they were permanent residents of the CISM study area. After written informed consent was obtained, the lowest available study number was assigned. A computer-generated sequential list contained the study numbers linked to treatment identification letters, randomly ordered in blocks of 10. Tablets of SP or placebo, identical in shape and colour, were stored in 10 bottles labelled only with a single treatment identification letter. Women were randomised to receive 3 tablets of SP (1500 mg...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: A computer-generated sequential list linked study numbers to treatment letters and participants were assigned the lowest available study number at enrolment; combined with identical packaging, recruiters could not foresee allocations, meeting Low risk criteria. Calibration: source describes sequence/list/envelope mechanics but not enough safeguards or access control to show recruiters could not foresee assignments.
- Model support: Quote: "After written informed consent was obtained, the lowest available study number was assigned. A computer-generated sequential list contained the study numbers linked to treatment identification letters, randomly ordered in blocks of 10. Tablets of SP or placebo, identical in shape and colour, were stored in 10 bottles labelled only with a single treatment identification letter." Comment: Computer-generated sequential list linking study numbers to treatment letters and identical treatment packaging with numbered study assignment administered by assigning lowest available study number indicates allocation could not be foreseen by recruiters. Comment: Calibration: source describes sequence/list/envelope mechanics but not enough safeguards or access control to show recruiters could not foresee assignments.
- Model support context: [{"source": "article", "quote": "of the CISM study area. After written informed consent was obtained, the lowest available study number was assigned. A computer-generated sequential list contained the study numbers linked to treatment identification letters, randomly...", "relevance": "Calibration: source describes sequence/list/envelope mechanics but not enough safeguards or access control to show recruiters could not foresee assignments."}, {"source": "article", "quote": "After written informed consent was obtained, the lowest available study number was assigned.", "relevance": "Shows enrolment used assignment by lowest available study number, preventing recruiter choice at point of allocation."}]
- GT support: Allocation was stored in a computer-generated list, but there is no information about where this list was kept or who had access to it.
- Evidence row: {}
- Source context preview: ## Methods The protocol for this trial and supporting CONSORT checklist are available as supporting information; see Checklist S1 and Protocol S1. --- ## Enrolment and interventions From August 2003 to April 2005 pregnant women were enrolled at the MDH ANC if their gestational age was ≤ 28 weeks, they did not report allergies to sulpha drugs, and they were permanent residents of the CISM study area. After written informed consent was obtained, the lowest available study number was assigned. A computer-generated sequential list contained the study numbers linked to treatment identification letters, randomly ordered in blocks of 10. Tablets of SP or placebo, identical in shape and colour,...

#### Blinding of participants and personnel: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly states a double-blind, placebo-controlled design and describes identical tablets and masked packaging; therefore participants and key personnel were blinded and lack of knowledge of allocation is unlikely to have influenced the measured outcomes (e.g., LBW, parasitemia, anemia).
- Model support: Quote: "This double blind, individually randomised, placebo controlled trial" Comment: Trial explicitly describes double-blind design with identical placebo tablets and computer-generated allocation, so participants and personnel were blinded and outcomes are unlikely to be influenced by knowledge of allocation.
- Model support context: [{"source": "article", "quote": "This double blind, individually randomised, placebo controlled trial", "relevance": "Explicit statement that the trial was double blind, indicating participants and personnel were intended to be blinded."}, {"source": "article", "quote": "Tablets of SP or placebo, identical in shape and colour, were stored in 10 bottles labelled only with a single treatment identification letter.", "relevance": "Describes matching placebo and masking procedures for study medication, supporting effective blinding of participants and administering personnel."}]
- GT support: This study was a double-blind, placebo-controlled trial. Tablets of SP or placebo, identical in shape and colour, were stored in 10 bottles labelled only with a single treatment identification letter. Women were randomized to receive 3 tablets of SP (1500 mg sulphadoxine/75 mg pyrimetamine) or placebo.
- Evidence row: {}
- Source context preview: ## Study design This double blind, individually randomised, placebo controlled trial had the primary objective of estimating the additive protective effect of two-dose IPTp with SP to that of ITNs on LBW prevalence. Based on previous estimates in the area, a LBW prevalence of 20% and an estimated 25% reduction to 15% in the presence of ITNs [14], 411 women per group were needed to show a lack of difference between the two groups with a confidence interval of 7 (8% to 22%), at the 5% level of significance with a 80% statistical power. The study protocol was approved by the National Mozambican Ethics Review Committee, and the Hospital Clinic of Barcelona Ethics Review Committee. --- ##...

#### Blinding of outcome assessment: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report specifies a double-blind design with identical placebo and describes objective, laboratory-measured outcomes (parasitemia, PCV, placental histology) read by standard procedures; thus detection bias is unlikely.
- Model support: Quote: "This double blind, individually randomised, placebo controlled trial" Comment: Trial was double-blind with identical placebo tablets, and laboratory outcomes (blood films, PCV, placental histology) were objective measurements unlikely to be influenced by assessor knowledge.
- Model support context: [{"source": "article", "quote": "This double blind, individually randomised, placebo controlled trial", "relevance": "States that the study was double-blind, indicating outcome assessors were intended to be blinded."}, {"source": "article", "quote": "Thick and thin blood films were stained and read according to standard, quality-controlled procedures. PCV was measured in a microcapillary tube after centrifugation.", "relevance": "Describes objective laboratory outcome measurements (parasitemia, PCV) that are unlikely to be influenced by assessor knowledge."}]
- GT support: As nurses and doctors were blinded, and the principal outcome of the study was low birth weight, we judged the study to have a low risk of detection bias.
- Evidence row: {}
- Source context preview: ## Enrolment and interventions From August 2003 to April 2005 pregnant women were enrolled at the MDH ANC if their gestational age was ≤ 28 weeks, they did not report allergies to sulpha drugs, and they were permanent residents of the CISM study area. After written informed consent was obtained, the lowest available study number was assigned. A computer-generated sequential list contained the study numbers linked to treatment identification letters, randomly ordered in blocks of 10. Tablets of SP or placebo, identical in shape and colour, were stored in 10 bottles labelled only with a single treatment identification letter. Women were randomised to receive 3 tablets of SP (1500 mg...

#### Incomplete outcome data: All outcomes

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The text reports an ITT analysis and refers to a trial profile (Figure 1) but the provided excerpts do not include randomized/enrolled counts by arm, analyzed outcome counts, missing data amounts, or reasons; therefore there is insufficient reporting to assess attrition bias.
- Model support: Quote: "Data were analysed by intention-to-treat (ITT) analysis whereby all randomised women were included regardless of whether or not they had received the intervention and the number of doses." Comment: ITT is stated but the report excerpts do not give numbers randomized vs analyzed, missing outcome counts by arm, reasons for loss to follow-up or withdrawal, or handling of missing outcome data, so risk of bias from incomplete data cannot be judged.
- Model support context: [{"source": "article", "quote": "Data were analysed by intention-to-treat (ITT) analysis whereby all randomised women were included regardless of whether or not they had received the intervention and the number of doses.", "relevance": "States analytic approach (ITT) but does not provide counts of randomized/analyzed or details on missing outcome data or reasons."}, {"source": "article", "quote": "Figure 1 shows the trial profile and table 1 shows the baseline characteristics of participants.", "relevance": "Refers to a trial profile with attrition details but the actual figure/table with numbers and reasons is not included in the supplied excerpts."}]
- GT support: The paper does not explain why a few children did not have data on weight, or whether baseline characteristics were balanced among those who were weighed and those who were not.
- Evidence row: {}
- Source context preview: ## Enrolment and interventions From August 2003 to April 2005 pregnant women were enrolled at the MDH ANC if their gestational age was ≤ 28 weeks, they did not report allergies to sulpha drugs, and they were permanent residents of the CISM study area. After written informed consent was obtained, the lowest available study number was assigned. A computer-generated sequential list contained the study numbers linked to treatment identification letters, randomly ordered in blocks of 10. Tablets of SP or placebo, identical in shape and colour, were stored in 10 bottles labelled only with a single treatment identification letter. Women were randomised to receive 3 tablets of SP (1500 mg...


## 18779465 - Grant 2008

- Mode: direct
- Review context: none (0 chars)
- Article chars: 23878
- Extraction context chars: n/a
- Total seconds: 28.75
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Unclear risk | Unclear risk | yes | article_absence_or_unclear |  |
| Allocation concealment | Unclear risk | Unclear risk | yes | article_absence_or_unclear |  |
| Blinding of participants and personnel: All outcomes | High risk | Unclear risk | no | article_absence_or_unclear | over-inferred_from_sparse_reporting |
| Blinding of outcome assessment: All outcomes | Low risk | Low risk | yes | article_absence_or_unclear |  |
| Incomplete outcome data: All outcomes | Unclear risk | Low risk | no | figure_table_or_supplement_reference | figure_table_or_supplement_needed |

### Audit Details

#### Random sequence generation

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The article reports that practices were 'randomly assigned' within strata but provides no details about the random component (computer, random number table, drawing lots, etc.). According to the criteria, insufficient information about the generation process requires an Unclear risk judgement.
- Model support: Quote: "practices were grouped in 4 mutually exclusive strata ... and practices within each independent stratum were randomly assigned to 1 of 2 study arms (for 16 possible randomization combinations)." Comment: The report states practices were "randomly assigned" but does not describe the random component or method used to generate the allocation sequence.
- Model support context: [{"source": "article", "quote": "practices were grouped in 4 mutually exclusive strata ... and practices within each independent stratum were randomly assigned to 1 of 2 study arms", "relevance": "States that assignment was random but gives no description of the random sequence generation method."}, {"source": "article", "quote": "We randomized at the practice level.", "relevance": "Confirms cluster (practice-level) randomization but does not specify how the random sequence was generated."}]
- GT support: Cluster‐randomisation, stratified block randomisation. It was not described how the random sequence was generated. “Practices were grouped in 4 mutually exclusive strata (women’s health practices, low‐income urban practices, large suburban practices, and smaller suburban practices), and practices within each independent stratum were randomly assigned to 1 of 2 study arms (for 16 possible randomisation combinations)” (p. 1778)
- Evidence row: {}
- Source context preview: ## Randomization Because this was a system-level intervention that involved patients, their physicians, and the clinical support staff at each practice, we randomized at the practice level. Practices were grouped in 4 mutually exclusive strata (women's health practices, low-income urban practices, large suburban practices, and smaller suburban practices), and practices within each independent stratum were randomly assigned to 1 of 2 study arms (for 16 possible randomization combinations). All primary and other clinical outcomes were collected directly from the electronic clinical data repository, and these data were obtained solely as part of usual clinical care. --- ## Intervention After...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The article states cluster randomization and that patients were consented before notification of practice assignment, but it does not describe the allocation concealment mechanism (central randomization, sealed opaque envelopes, or similar). Missing details on how practices/enrollers were prevented from foreseeing assignments require an Unclear risk judgement.
- Model support: Quote: "we randomized at the practice level. Practices were grouped in 4 mutually exclusive strata... and practices within each independent stratum were randomly assigned to 1 of 2 study arms (for 16 possible randomization combinations)." Comment: The report describes cluster randomization and stratification but does not state how the allocation sequence was concealed from those enrolling practices or whether central/web/telephone allocation or sealed envelopes were used.
- Model support context: [{"source": "article", "quote": "we randomized at the practice level. Practices were grouped in 4 mutually exclusive strata... and practices within each independent stratum were randomly assigned", "relevance": "Describes unit randomized and that practices were randomly assigned, but gives no details on concealment procedures."}, {"source": "article", "quote": "Informed consent was obtained from eligible patients prior to notification of practice randomization status.", "relevance": "Shows timing of patient consent relative to notification, but does not describe who generated or controlled allocation or the method used to prevent..."}]
- GT support: It was not reported whether allocation of treatment to clusters was concealed, but it seems that patients had been recruited before randomisation
- Evidence row: {}
- Source context preview: ## Randomization Because this was a system-level intervention that involved patients, their physicians, and the clinical support staff at each practice, we randomized at the practice level. Practices were grouped in 4 mutually exclusive strata (women's health practices, low-income urban practices, large suburban practices, and smaller suburban practices), and practices within each independent stratum were randomly assigned to 1 of 2 study arms (for 16 possible randomization combinations). All primary and other clinical outcomes were collected directly from the electronic clinical data repository, and these data were obtained solely as part of usual clinical care. --- ## Intervention After...

#### Blinding of participants and personnel: All outcomes

- Prediction: High risk
- Ground truth: Unclear risk
- Match: False
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The report states participants were unaware at consent but describes different, content-distinct PHR modules that participants used, and gives no clear information whether participants or staff remained blinded or whether lack of blinding could influence the review outcomes (patient satisfaction, compliance, knowledge, adverse events). Required details on ongoing blinding of participants/personnel and its potential impact are missing. Calibration: visibly different active interventions with subjective patient-reported outcomes make participant/personnel blinding unlikely and material.
- Model support: Quote: "Patients were unaware of their PHR assignment when consenting to enroll in the study." Comment: Participants initially blinded to allocation at consent, but later they used different PHR modules (DM-specific vs family history) so participants and personnel likely became aware; the report does not state whether participants or staff remained blinded or whether knowledge could influence patient-reported outcomes. Comment: Calibration: visibly different active interventions with subjective patient-reported outcomes make participant/personnel blinding unlikely and material.
- Model support context: [{"source": "article", "quote": "## Randomization Because this was a system-level intervention that involved patients, their physicians, and the clinical support staff at each practice, we randomized at the practice level. Practices were grouped in 4 mutually exclusive...", "relevance": "Calibration: visibly different active interventions with subjective patient-reported outcomes make participant/personnel blinding unlikely and material."}, {"source": "article", "quote": "Patients were unaware of their PHR assignment when consenting to enroll in the study.", "relevance": "Shows initial concealment at consent but does not confirm ongoing blinding during intervention delivery or of personnel."}]
- GT support: Objective outcomes Blinding of physicians not possible, patients were blinded, as the control group also gained access to new components of the patient portal “Patients were unaware of their PHR assignment when consenting to enrol in the study. Because both intervention and control groups used PG and received additional PHR modules, the primary distinction between the 2 study arms was the content of the modules“ (p. 1777) Unclear whether different performance influences HbA1c No further outcomes were reported
- Evidence row: {}
- Source context preview: ## Randomization Because this was a system-level intervention that involved patients, their physicians, and the clinical support staff at each practice, we randomized at the practice level. Practices were grouped in 4 mutually exclusive strata (women's health practices, low-income urban practices, large suburban practices, and smaller suburban practices), and practices within each independent stratum were randomly assigned to 1 of 2 study arms (for 16 possible randomization combinations). All primary and other clinical outcomes were collected directly from the electronic clinical data repository, and these data were obtained solely as part of usual clinical care. --- ## Intervention After...

#### Blinding of outcome assessment: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The review-relevant outcomes are objective measures (HbA1c, blood pressure, LDL-C) obtained from the electronic clinical data repository; objective device/lab/EMR-derived outcomes are unlikely to be affected by assessor knowledge, meeting Low risk criteria.
- Model support: Quote: "All primary and other clinical outcomes were collected directly from the electronic clinical data repository, and these data were obtained solely as part of usual clinical care." Comment: Outcomes (HbA1c, blood pressure, LDL-C) were objective lab/device/EMR-measured data extracted from the EMR, so assessor knowledge of allocation is unlikely to influence measurement.
- Model support context: [{"source": "article", "quote": "All primary and other clinical outcomes were collected directly from the electronic clinical data repository", "relevance": "Indicates outcomes were obtained from EMR/data repository rather than subjective assessment."}, {"source": "article", "quote": "The primary outcomes... HbA1c, blood pressure, and LDL-C", "relevance": "Specifies objective laboratory and physiological measures that are unlikely to be influenced by assessor knowledge."}]
- GT support: Objective outcomes It was not reported whether personnel in the lab were blinded, but this routine lab test has probably a small risk for detection bias. No further outcomes were reported
- Evidence row: {}
- Source context preview: ## Comment Effective translation of new innovations into improved DM care remains a difficult challenge for current research efforts.28 The results of our study underscore a number of critical points for future work in this area. First, evaluating the impact of new technologies and new strategies for care requires a rigorous study design. Our use of an active control study design provided the advantage of allowing us to compare 2 groups of patients who were equally inclined to enroll in a clinical trial of Web-based PHR interventions. Thus, the comparison of primary outcomes between “active account” study arms reflects the impact of the DM PHR on clinical care among patients equally...

#### Incomplete outcome data: All outcomes

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: figure_table_or_supplement_reference (article observable: None)
- GT support phrase hits: 
- Model rationale: The report states an intention-to-treat analysis and describes outcomes, but the excerpts do not provide randomized and analyzed participant counts by arm, numbers or percentages of missing outcome data, reasons for missingness, or methods used to handle missing data, so risk of attrition bias cannot be judged.
- Model support: Quote: "The primary outcomes for this study were changes from baseline in 3 key measures of DM management: HbA1c, blood pressure, and LDL-C, comparing all eligible patients with DM in the 2 study arms in an intention-to-treat analysis." Comment: Numbers randomized, analyzed, and missing outcome data by arm, plus reasons for missingness and how missing data were handled, are not reported in the supplied excerpts.
- Model support context: [{"source": "article", "quote": "Figure 1 illustrates the number of primary care practices randomized and the flow of patients with DM in each study arm.", "relevance": "Mentions flow diagram but actual randomized/analyzed/missing patient counts by arm are not provided in the excerpts."}, {"source": "article", "quote": "All primary and other clinical outcomes were collected directly from the electronic clinical data repository, and these data were obtained solely as part of usual clinical care.", "relevance": "Indicates outcome data source but does not report completeness, missing counts, reasons, or handling of missing data."}]
- GT support: Objective outcomes All patients were analysed, but no data show whether follow‐up was equally distributed over the different clusters (p. 1779, Table)
- Evidence row: {}
- Source context preview: ## Participant Flow Figure 1 illustrates the number of primary care practices randomized and the flow of patients with DM in each study arm. Use of the parent PG secure Web portal by patients with DM ranged from 7% to 14% of each practice population. Among patients with active PG accounts, the rate of consent to enroll in the advanced patient portal clinical trial was 39% in the DM PHR intervention arm and 35% in the family history and health maintenance PHR active control arm. Practices were enrolled beginning September 30, 2005, and follow-up ascertainment was completed when the study was formally closed March 22, 2007. --- ## Outcomes The primary outcomes for this study were changes from...


## 19209172 - Vodermaier 2009

- Mode: direct
- Review context: none (0 chars)
- Article chars: 35445
- Extraction context chars: n/a
- Total seconds: 25.47
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
| Incomplete outcome data: All outcomes | High risk | Unclear risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |

### Audit Details

#### Random sequence generation

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report states allocation used numbered cards in envelopes and stratification by age, but it does not describe a random component (computer, random number table, coin toss, minimization with random element). Because the mechanism for generating the sequence is not specified, the risk of bias for sequence generation is unclear.
- Model support: Quote: "Random assignment was performed by means of numbered cards in envelopes for the intervention and the control group, and was stratified by age group (<, ⩾60 years)." Comment: Method mentions numbered cards in envelopes but does not describe how the sequence/list of numbers/cards was generated (random number table, computer, coin, etc.), so risk is unclear.
- Model support context: [{"source": "article", "quote": "Random assignment was performed by means of numbered cards in envelopes for the intervention and the control group, and was stratified by age group (<, ⩾60 years).", "relevance": "Describes the physical allocation mechanism but does not state how the sequence of cards was generated (random component not specified)."}, {"source": "article", "quote": "Randomisation was conducted after the patient gave written informed consent to participate in the trial.", "relevance": "Indicates timing of randomisation but gives no information on the method used to generate the random sequence."}]
- GT support: “Randomisation after the patient gave written informed consent”; “Random assignment was performed by means of numbered cards in envelopes”; “stratified by age group” (p. 2)
- Evidence row: {}
- Source context preview: ## Procedure Staff doctors informed the two research psychologists (CC, JK) who recruited the patients about new patients who had entered the ward and who were eligible for the trial. Randomisation was conducted after the patient gave written informed consent to participate in the trial through the research staff. Random assignment was performed by means of numbered cards in envelopes for the intervention and the control group, and was stratified by age group (<, ⩾60 years). For participants of the intervention arm, the decision board intervention was provided by research psychologists who had previously recruited the patients. The intervention was conducted on the day the patients arrived...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: The trial used numbered cards in envelopes to allocate participants, but the report does not state whether envelopes were opaque, sealed, sequentially numbered, or held independently, so there is insufficient information to judge allocation concealment.
- Model support: Quote: "Random assignment was performed by means of numbered cards in envelopes for the intervention and the control group, and was stratified by age group (<, ⩾60 years)." Comment: Numbered envelopes are reported but no details on whether envelopes were opaque, sealed, sequentially numbered, or held independently, so concealment is unclear.
- Model support context: [{"source": "article", "quote": "Random assignment was performed by means of numbered cards in envelopes for the intervention and the control group, and was stratified by age group.", "relevance": "Describes the allocation mechanism (envelopes) but omits safeguards required to judge concealment (opacity, sealing, independence)."}, {"source": "article", "quote": "Randomisation was conducted after the patient gave written informed consent to participate in the trial through the research staff.", "relevance": "Indicates timing of randomisation but does not indicate who controlled envelopes or whether recruiters could foresee assignments."}]
- GT support: “[N]umbered cards in envelopes” (p. 2)
- Evidence row: {}
- Source context preview: ## Procedure Staff doctors informed the two research psychologists (CC, JK) who recruited the patients about new patients who had entered the ward and who were eligible for the trial. Randomisation was conducted after the patient gave written informed consent to participate in the trial through the research staff. Random assignment was performed by means of numbered cards in envelopes for the intervention and the control group, and was stratified by age group (<, ⩾60 years). For participants of the intervention arm, the decision board intervention was provided by research psychologists who had previously recruited the patients. The intervention was conducted on the day the patients arrived...

#### Blinding of participants and personnel: All outcomes

- Prediction: High risk
- Ground truth: Unclear risk
- Match: False
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The intervention was a visible decision aid plus brochure versus standard care and blinding was not possible; primary outcomes are patient-reported decision-making measures, so lack of blinding likely influenced outcomes, meeting High risk criteria.
- Model support: Quote: "Blinding was not possible within the hospital procedures. Nonetheless, in most cases physicians did not know in which arm patients had been randomised." Comment: Participants received a visible 20-min decision aid plus brochure versus standard care, so participants and personnel were not fully blinded and the outcomes are patient-reported (decision making, decisional conflict), likely influenced by knowledge of allocation.
- Model support context: [{"source": "article", "quote": "Blinding was not possible within the hospital procedures. Nonetheless, in most cases physicians did not know in which arm patients had been randomised.", "relevance": "States blinding was not possible and physicians were often unaware, implying participants and some personnel were unblinded."}, {"source": "article", "quote": "the intervention group received a 20-min decision aid intervention and additional written information ... control group received standard care", "relevance": "Describes clearly different, visible interventions; outcomes are patient-reported decision-making measures likely affected by knowing allocation."}]
- GT support: Not blinded ‐ unclear if this would introduce bias to outcome assessed
- Evidence row: {}
- Source context preview: ## Study design A two-arm, randomised controlled trial with decision aids vs standard treatment was conducted. Randomisation was conducted after the patient gave written informed consent to participate in the trial. Blinding was not possible within the hospital procedures. Nonetheless, in most cases physicians did not know in which arm patients had been randomised. Patients were assessed pre-randomisation (baseline) and at 1 week follow-up. The baseline questionnaire was filled out shortly after hospital admission and prior to randomisation. A few hours later, the intervention group received a 20-min decision aid intervention and additional written information, whereas the control group...

#### Blinding of outcome assessment: All outcomes

- Prediction: High risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The review-relevant outcomes include patient-reported satisfaction/decision measures (self-report) and the research psychologists who performed the intervention were not blind to these ratings, creating a likely influence of lack of blinding on outcome assessment (detection bias).
- Model support: Quote: "ratings were not blind to the research psychologists who performed the intervention. This may have lead to social desirability with regard to the evaluation of the decision aid intervention" Comment: Outcome assessment (patient-reported satisfaction and decision measures) was influenced by assessors who were unblinded and involved in delivering the intervention, risking detection bias.
- Model support context: [{"source": "article", "quote": "ratings were not blind to the research psychologists who performed the intervention.", "relevance": "Explicit statement that assessors (research psychologists) were unblinded and involved in the intervention."}, {"source": "article", "quote": "Satisfaction with the decision making process and general patient satisfaction... ratings were not blind to the research psychologists", "relevance": "Identifies patient-reported satisfaction outcomes and that those ratings were available to unblinded intervention staff."}]
- GT support: Not blinded but outcomes were objectively measured and not subjective to interpretation
- Evidence row: {}
- Source context preview: ## Discussion Satisfaction with the decision making process and general patient satisfaction with care was high and did not differ between groups. Though physicians involved in the patients' treatment did not see patients' assessment of treatment satisfaction, ratings were not blind to the research psychologists who performed the intervention. This may have lead to social desirability with regard to the evaluation of the decision aid intervention but may have had little impact on ratings of satisfaction with treatment. Variance constriction because of a ceiling effect may have contributed to the lack of a group difference. Results are in line with other studies, which reported null effects...

#### Incomplete outcome data: All outcomes

- Prediction: High risk
- Ground truth: Unclear risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: A large proportion of randomized participants (41/152, ~27%) were excluded post-randomisation for reasons discovered after allocation, with unequal exclusions by arm and reasons plausibly related to outcomes; this meets the criteria for High risk due to attrition likely related to true outcome and potential bias.
- Model support: Quote: "152 participants were randomised to either the intervention or the control condition. The final sample was 111 patients, of whom 55 were randomly assigned to the intervention group and 56 to the control group. Here, 13 and 16 patients respectively were excluded from the analyses because of post hoc ascertainment of not having met the inclusion criteria (benign diagnosis, carcinoma in situ, Stage IV-tumour)." Comment: Large post-randomisation exclusions (41/152, ~27%) and exclusions differed by arm (13 vs 16) and were related to diagnosis discovered after randomisation, likely related to outcomes and introducing attrition bias.
- Model support context: [{"source": "article", "quote": "152 participants were randomised... The final sample was 111 patients, of whom 55 were randomly assigned to the intervention group and 56 to the control group.", "relevance": "Shows numbers randomized and numbers analysed by arm; indicates substantial loss from randomisation (152 -> 111)."}, {"source": "article", "quote": "13 and 16 patients respectively were excluded from the analyses because of post hoc ascertainment of not having met the inclusion criteria (benign diagnosis, carcinoma in situ, Stage IV-tumour).", "relevance": "Explains reasons for post-randomisation exclusions that are related to diagnosis and hence plausibly related to outcomes."}]
- GT support: Flow diagram, p. 5; baseline characteristics not included
- Evidence row: {}
- Source context preview: ## Trial retention Between May 2003 and October 2004 we invited 246 patients to participate, of whom 94 declined (uptake rate of 62.6%). Patient accrual according to the Consort guidelines is presented in Figure 1. The major reasons for declining study participation were preoperative distress associated with filling out a questionnaire shortly after admission (70%), general refusal to fill out questionnaires (10%), involvement in another study therefore not wanting to participate in an additional study (2%), first agreed to participate, but refused after reviewing the questionnaire (4%) or were ineligible because of missing diagnostic findings, outstanding examinations, or preoperative...


## 19291323 - Middleton 2011

- Mode: direct
- Review context: none (0 chars)
- Article chars: 29453
- Extraction context chars: n/a
- Total seconds: 29.89
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
- Model rationale: The report explicitly states an independent statistician will generate the allocation using random number generating software, meeting the 'random component' criteria for Low risk.
- Model support: Quote: "this will be generated using random number generating software[29]." Comment: An independent offshore statistician will generate the allocation using random number generating software, which describes a random component for sequence generation.
- Model support context: [{"source": "article", "quote": "this will be generated using random number generating software[29].", "relevance": "Explicit statement that a random number generator will be used to create the allocation sequence."}, {"source": "article", "quote": "generation of the allocation sequence and assigning of ASUs to either intervention or control group will be undertaken by the offshore independent statistician.", "relevance": "Shows an independent statistician will produce the randomized sequence, supporting appropriate random sequence generation."}]
- GT support: "ASUs were stratified by category (category A or B) and then by absolute numbers of pre-intervention cohort patients recruited (high or low recruiters). High recruiters had consented more than two patients per month; low recruiters two or fewer per month. De-identified stratification details were provided to an independent statistician who used random number generating software to randomise withinstrata with allocation concealed until provided to the Project Officer who assigned ASUs to their groups."
- Evidence row: {}
- Source context preview: ## Hypotheses Once the baseline patient cohort 90-day outcome data have been collected, participating ASUs will be stratified and randomised. The project officer (SD) will first stratify ASUs according to their category classification (A or B) and then, by referring to absolute numbers of patients recruited at baseline, describe each as a 'high recruiter' or 'low recruiter'. Recruitment numbers will be included as a randomisation strata to maximise the chance of similar sample size in the intervention and control groups. Stratification details will be provided in a de-identified form to an independent statistician located offshore and not otherwise involved in the study for randomisation...

#### Allocation concealment

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: Allocation was centrally generated and assignments were performed by an independent offshore statistician using random-number software, which meets criteria for central allocation and prevents foreseeability by enrolling investigators.
- Model support: Quote: "Stratification details will be provided in a de-identified form to an independent statistician located offshore and not otherwise involved in the study for randomisation within strata, this will be generated using random number generating software[29]. ... generation of the allocation sequence and assigning of ASUs to either intervention or control group will be undertaken by the offshore independent statistician." Comment: An independent offshore statistician generated the allocation using random-number software and both sequence generation and assignment were performed by that independent party, preventing recruiters from foreseeing allocations.
- Model support context: [{"source": "article", "quote": "\"stratification details will be provided in a de-identified form to an independent statistician located offshore... generated using random number generating software\"", "relevance": "Indicates centralised external generation of the allocation sequence using random software."}, {"source": "article", "quote": "\"generation of the allocation sequence and assigning of ASUs to either intervention or control group will be undertaken by the offshore independent statistician.\"", "relevance": "Shows assignment was undertaken by an independent offshore statistician, preventing recruiters from foreseeing allocations."}]
- GT support: "De-identified stratification details were provided to an independent statistician who used random number generating software to randomise within strata with allocation concealed until provided to the Project Officer who assigned ASUs to their groups."
- Evidence row: {}
- Source context preview: ## Hypotheses Once the baseline patient cohort 90-day outcome data have been collected, participating ASUs will be stratified and randomised. The project officer (SD) will first stratify ASUs according to their category classification (A or B) and then, by referring to absolute numbers of patients recruited at baseline, describe each as a 'high recruiter' or 'low recruiter'. Recruitment numbers will be included as a randomisation strata to maximise the chance of similar sample size in the intervention and control groups. Stratification details will be provided in a de-identified form to an independent statistician located offshore and not otherwise involved in the study for randomisation...

#### Blinding of participants and personnel: All outcomes

- Prediction: Low risk
- Ground truth: High risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The protocol explicitly states that patients are blinded and that outcome CATI interviewers are blind to allocation; because outcomes are patient-level and collected by blinded interviewers, lack of personnel blinding is unlikely to have influenced the measured outcomes, supporting Low risk.
- Model support: Quote: "Patients will be blinded to group allocation. Data entry will be undertaken by the CATI research assistants blind to group allocation." Comment: Participants and key outcome data collectors (CATI interviewers) are stated as blinded, and outcomes are patient-level assessments collected by blinded interviewers, making performance bias unlikely.
- Model support context: [{"source": "article", "quote": "Patients will be blinded to group allocation. Data entry will be undertaken by the CATI research assistants blind to group allocation.", "relevance": "States that patients and CATI research assistants (who collect outcomes) are blinded, reducing risk that knowledge of allocation influenced care or outcome..."}, {"source": "article", "quote": "CRAs recruiting patients will be blind at baseline to ASU group allocation.", "relevance": "Recruiters being blind at baseline reduces differential enrolment or baseline influence by personnel."}]
- GT support: "Clinical research assistants [personnel] masked to trial design enrolled patients. Patients were masked to ASU group allocation but clinicians delivering our intervention were not."
- Evidence row: {}
- Source context preview: ## Hypotheses Once the baseline patient cohort 90-day outcome data have been collected, participating ASUs will be stratified and randomised. The project officer (SD) will first stratify ASUs according to their category classification (A or B) and then, by referring to absolute numbers of patients recruited at baseline, describe each as a 'high recruiter' or 'low recruiter'. Recruitment numbers will be included as a randomisation strata to maximise the chance of similar sample size in the intervention and control groups. Stratification details will be provided in a de-identified form to an independent statistician located offshore and not otherwise involved in the study for randomisation...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly states that outcome assessment is blinded for all primary and secondary outcomes and that CATI interviewers (assessing patient-reported outcomes such as SF-36) are blind to group allocation, making it unlikely that detection bias affected outcome measurement. Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support: Quote: "Blinded outcome assessment will be undertaken for all analyses of primary and secondary outcome measures." Comment: Outcome assessment is explicitly described as blinded for primary and secondary outcomes, indicating assessors were masked. Comment: Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support context: [{"source": "article", "quote": "measures 4. Health status 90 days post-hospital admission using the Medical Outcomes Study Short Form 36 Health Survey Questionnaire (SF-36) [45]. The SF-36 includes a single 'health transition rating' and scores eight health domains which...", "relevance": "Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported."}, {"source": "article", "quote": "Blinded outcome assessment will be undertaken for all analyses of primary and secondary outcome measures.", "relevance": "Direct statement that outcome assessment will be blinded for all primary and secondary outcomes."}]
- GT support: "Research assistants who undertook the computer-assisted telephone interviews and the medical record audits were masked to trial aims, design, and group allocation; the trial statistician was masked to group allocation [outcome assessors]."
- Evidence row: {}
- Source context preview: ## Hypotheses Once the baseline patient cohort 90-day outcome data have been collected, participating ASUs will be stratified and randomised. The project officer (SD) will first stratify ASUs according to their category classification (A or B) and then, by referring to absolute numbers of patients recruited at baseline, describe each as a 'high recruiter' or 'low recruiter'. Recruitment numbers will be included as a randomisation strata to maximise the chance of similar sample size in the intervention and control groups. Stratification details will be provided in a de-identified form to an independent statistician located offshore and not otherwise involved in the study for randomisation...

#### Incomplete outcome data: All outcomes

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: figure_table_or_supplement_reference (article observable: None)
- GT support phrase hits: 
- Model rationale: The supplied excerpts are from the trial protocol and describe expected loss to follow-up and planned ITT analysis, but do not present randomized or analyzed participant counts, actual missing outcome numbers, reasons for missingness, balance across arms, or imputation methods. Because critical post-randomization attrition details are not reported, risk of bias due to incomplete outcome data cannot be judged.
- Model support: Quote: "Assuming a loss to follow-up of 10%, an effective sample size of 280 participants per group is required to be recruited." Comment: Protocol states an anticipated 10% loss and that intention-to-treat analysis will be applied, but the report provides no actual numbers randomized, analyzed, or missing by arm, nor reasons for missing data.
- Model support context: [{"source": "article", "quote": "Assuming a loss to follow-up of 10%, an effective sample size of 280 participants per group is required to be recruited.", "relevance": "Reports an anticipated attrition rate but not observed missing outcome data."}, {"source": "article", "quote": "Intention-to-treat analysis will applied.", "relevance": "States planned analysis approach but does not report how missing data were handled or actual missing counts by arm."}]
- GT support: "Of the 1861 eligible QASC consenting patients across the entire study period, medical records were unavailable for 57 patients (3·6%) [17 (2·4%) from the preintervention cohort and 40 (3·7%) from the postintervention cohort] resulting in collection of data for 1804 patients. No data missing, pre-determined outcomes were assessed." Participant drop out explained in figure 2. Less than 20% drop out rate in each intervention is low risk of bias.
- Evidence row: {}
- Source context preview: ## Background In our study, we will develop, implement, and rigorously evaluate a multidisciplinary team-building intervention in ASUs. Our intervention is designed to improve outcomes for patients admitted with acute stroke by better management of fever, hyperglycaemia, and swallowing dysfunction as recommended by evidence-based guidelines. This intervention will comprise replicable steps to identify local barriers and enablers, unit-based education, feedback, and ongoing proactive support. As we are focussing on fever, hyperglycaemia ('sugar'), and swallowing dysfunction, our intervention is known as the 'FeSS' intervention. Because the team-building intervention can only be delivered at...


## 19319218 - Chien 2008a

- Mode: direct
- Review context: none (0 chars)
- Article chars: 46815
- Extraction context chars: n/a
- Total seconds: 24.17
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Low risk | yes | no_support_phrase_match |  |
| Allocation concealment | Unclear risk | Low risk | no | article_text_match | under-called_due_to_missing_or_underused_evidence |
| Blinding of participants and personnel: All outcomes | Unclear risk | High risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |
| Blinding of outcome assessment: All outcomes | Low risk | Low risk | yes | no_support_phrase_match |  |
| Incomplete outcome data: All outcomes | Low risk | Low risk | yes | no_support_phrase_match |  |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly states a computer-generated random numbers table was used to select participants, meeting the criteria for a random component and thus Low risk for sequence generation.
- Model support: Quote: "They were then selected randomly from the patient list, using a computer-generated random numbers table." Comment: The sequence generation used a computer-generated random numbers table, which is an adequate random component.
- Model support context: [{"source": "article", "quote": "They were then selected randomly from the patient list, using a computer-generated random numbers table.", "relevance": "Describes a computer-generated random numbers table used to select participants, indicating an appropriate random sequence generation method."}, {"source": "article", "quote": "Sixty-eight of 300 eligible subjects were selected randomly from a list of family members", "relevance": "Confirms that selection was random from an eligible list, supporting the use of a random method."}]
- GT support: Quote: "the participants were then asked by the principal researcher to draw a sealed opaque envelope, in which a number card indicated to which group they had been allocated (1 = psycho-education group and 2 = routine care group)." Comment: simple randomisation
- Evidence row: {}
- Source context preview: ## Sample & Study Settings Exclusion criteria included those who cared for more than one family member with mental illness, who themselves had mental illness, and who were the primary carers for less than three months. Those eligible were listed in alphabetical order by surname. They were then selected randomly from the patient list, using a computer-generated random numbers table. --- ## METHODS A repeated measures design was used to compare two groups of family caregivers of patients with schizophrenia: a psycho-education and support group and a standard care (conventional psychiatric outpatient care) group. This study was undertaken between January 2005 and September 2006. Analysis of...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: the participants were then asked by the principal researcher to draw a sealed opaque envelope
- Model rationale: The report states participants drew a sealed opaque envelope, but does not specify whether envelopes were sequentially numbered, prepared and held independently, or otherwise safeguarded; therefore insufficient detail to judge concealment as adequate.
- Model support: Quote: "the participants were then asked by the principal researcher to draw a sealed opaque envelope, in which a number card indicated to which group they had been allocated (1 = psycho-education group and 2 = routine care group)." Comment: Envelope method is described but details necessary to judge adequate concealment (who prepared envelopes, whether envelopes were sequentially numbered, opaque and sealed with safeguards) are not reported.
- Model support context: [{"source": "article", "quote": "participants were then asked by the principal researcher to draw a sealed opaque envelope, in which a number card indicated to which group they had been allocated", "relevance": "Describes use of envelopes for allocation but lacks details on safeguards (sequencing, independent preparation)."}, {"source": "article", "quote": "Except for the principal researcher and the group instructor, all other clinic staffs were blinded to treatment allocation.", "relevance": "Indicates some blinding after allocation but does not address who could foresee or control assignments before allocation."}]
- GT support: Quote: "the participants were then asked by the principal researcher to draw a sealed opaque envelope"
- Evidence row: {}
- Source context preview: ## Data Collection Enrolment, allocation, treatments, measures, and analyses of data from the study subjects are summarized in a flow diagram (Fig. 1), according to the revised version of CONSORT statements [39]. A trained psychiatric nurse (group instructor) approached the patients in person during follow-up appointment to seek written consent for voluntary participation in this study and permission to approach their family members. With the patient’s permission, one family member who was the primary caregiver of the patient was contacted by telephone to explain the purpose and procedure of the study and to invite his/her participation in the study. Written consent was obtained in a...

#### Blinding of participants and personnel: All outcomes

- Prediction: Unclear risk
- Ground truth: High risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report shows that the group instructor and principal researcher were not blinded and that participants drew allocation envelopes, suggesting participants likely became aware of allocation; insufficient information on whether lack of blinding plausibly influenced the listed outcomes (some subjective outcomes present), so risk of performance bias is unclear.
- Model support: Quote: "Except for the principal researcher and the group instructor, all other clinic staffs were blinded to treatment allocation." Comment: Staff (some) were blinded but participants and group instructor were not; report does not state whether participants knew allocation or whether personnel delivering interventions were blinded, so effect on outcomes is uncertain.
- Model support context: [{"source": "article", "quote": "Except for the principal researcher and the group instructor, all other clinic staffs were blinded to treatment allocation.", "relevance": "Indicates partial blinding of staff but implies key personnel (group instructor) were unblinded; does not state participant blinding."}, {"source": "article", "quote": "participants were then asked by the principal researcher to draw a sealed opaque envelope ... indicated to which group they had been allocated", "relevance": "Describes open allocation reveal to participant at assignment, implying participants became aware of group allocation."}]
- GT support: Quote: "Except for the principal researcher and the group instructor, all other clinic staffs were blinded to treatment allocation."
- Evidence row: {}
- Source context preview: ## METHODS A repeated measures design was used to compare two groups of family caregivers of patients with schizophrenia: a psycho-education and support group and a standard care (conventional psychiatric outpatient care) group. This study was undertaken between January 2005 and September 2006. Analysis of data was on an intention-to-treat basis [35]. All subjects, who completed the intervention or not, were followed up over a 12-month post-intervention period. They were selected randomly from two regional outpatient clinics in Hong Kong, consisting of about 1,800 patients with schizophrenia or its subtypes, representing 12% of this type of patients in Hong Kong [36]. --- ## Models of...

#### Blinding of outcome assessment: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: Outcome type: questionnaire-based self-report and assessor-administered scales; assessor role: independent research assistant. The report does not state explicitly whether this assessor was blinded, and given self-report/questionnaire outcomes, lack of clear information prevents a Low or High risk judgment. Calibration: outcome measurement was objective/device/lab-based or centrally interpreted, so assessor knowledge is unlikely to materially bias measurement.
- Model support: Quote: "Except for the principal researcher and the group instructor, all other clinic staffs were blinded to treatment allocation. An independent assessor (a research assistant) was trained to undertake measurements at Time 1, 2 and 3 using a set of questionnaires." Comment: It is unclear whether the independent assessor remained blinded to group allocation when administering or scoring the largely self-report/questionnaire outcomes. Comment: Calibration: outcome measurement was objective/device/lab-based or centrally interpreted, so assessor knowledge is unlikely to materially bias measurement.
- Model support context: [{"source": "article", "quote": "## Study Rationale This study sought to test and compare the effectiveness between two modes of community-based interventions, namely: (i) a family psychoeducation and mutual support group and (ii) the conventional psychiatric outpatient...", "relevance": "Calibration: outcome measurement was objective/device/lab-based or centrally interpreted, so assessor knowledge is unlikely to materially bias measurement."}, {"source": "article", "quote": "Except for the principal researcher and the group instructor, all other clinic staffs were blinded to treatment allocation.", "relevance": "Reports some staff blinding but does not specify whether the independent assessor was blinded."}]
- GT support: Quote: "An independent assessor (a research assistant) was trained to undertake measurements at Time 1, 2 and 3 using a set of questionnaires."
- Evidence row: {}
- Source context preview: ## Study Rationale This study sought to test and compare the effectiveness between two modes of community-based interventions, namely: (i) a family psychoeducation and mutual support group and (ii) the conventional psychiatric outpatient care (routine care group) for family caregivers of people with schizophrenia in a Chinese population. The two groups were compared prior to (Time 1), one month later (Time 2) and 12 months after the intervention (Time 3), and multiple outcome measures for families and patients were used to assess treatment effects. The main hypothesis was that the psychoeducation and support group intervention would significantly reduce schizophrenic patients’ psychosocial...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: Attrition was very low (3 vs 2 dropouts), balanced across groups, and the report states intention-to-treat analysis with follow-up of all subjects, so reasons/handling make bias unlikely, meeting Low risk criteria.
- Model support: Quote: "Thirty-one subjects (91.2%) from the mutual psychoeducation and support group completed the program. These subjects, together with those who dropped out or absented in more than four group sessions - psycho-education group (n = 3) and routine care group (n = 2), were evaluated at three times of outcome measurements." Comment: Attrition was very low and balanced (3 vs 2) and all participants, completers and dropouts, were evaluated at all three outcome time points with intention-to-treat analysis.
- Model support context: [{"source": "methodology", "quote": "Quote: \"Thirty-one subjects (91.2%) from the mutual psychoeducation and support group completed the program. These subjects, together with those who dropped out or absented in more than four group sessions - psycho-education group (n = 3)...", "relevance": "Recovered from malformed JSON; inspect raw output if this judgement matters."}]
- GT support: Comment: study attrition reported, with similar number and reasons for dropouts shown in the flow chart
- Evidence row: {}
- Source context preview: ## Sample Characteristics Thirty-one subjects (91.2%) from the mutual psychoeducation and support group completed the program. These subjects, together with those who dropped out or absented in more than four group sessions - psycho-education group (n = 3) and routine care group (n = 2), were evaluated at three times of outcome measurements. Reasons for dropout or discontinuation from the group interventions were mainly: insufficient time to attend (n = 2), patient’s mental state worsened (n = 3), not interested (n = 2), and the only person taking care of patient (n = 2). --- ## Strengths and Limitations of the Study Strengths in the design of the study include: (a) randomized treatment...


## 19487623 - King 2009

- Mode: direct
- Review context: none (0 chars)
- Article chars: 24566
- Extraction context chars: n/a
- Total seconds: 28.09
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Unclear risk | no | article_text_match | over-inferred_from_sparse_reporting |
| Allocation concealment | Unclear risk | Unclear risk | yes | article_absence_or_unclear |  |
| Blinding of participants and personnel: All outcomes | Low risk | Low risk | yes | article_text_match |  |
| Blinding of outcome assessment: All outcomes | Low risk | Low risk | yes | article_text_match |  |
| Incomplete outcome data: All outcomes | Low risk | Unclear risk | no | external_or_review_context | external_or_review_context_needed |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Unclear risk
- Match: False
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: placebo using permuted blocks with randomly | using permuted blocks with randomly varying | permuted blocks with randomly varying block | blocks with randomly varying block sizes | with randomly varying block sizes stratified
- Model rationale: The report explicitly states use of permuted blocks with randomly varying block sizes (a described random component), which satisfies the Low risk criterion for adequate random sequence generation.
- Model support: Quote: "Participants were randomly assigned to citalopram or placebo using permuted blocks with randomly varying block sizes stratified by site and by age (5-11 vs 12-17 years)." Comment: The sequence generation used permuted blocks with randomly varying block sizes, which describes a random component.
- Model support context: [{"source": "article", "quote": "Participants were randomly assigned to citalopram or placebo using permuted blocks with randomly varying block sizes stratified by site and by age (5-11 vs 12-17 years).", "relevance": "Explicit description of a random component (permuted blocks with randomly varying block sizes) meets Low risk criteria for sequence generation."}, {"source": "article", "quote": "The trial, NCT00086645, was registered at clinicaltrials.gov before initiation and was conducted at the following 6 academic medical centers.", "relevance": "Registration and multicenter conduct support trial governance but primary relevance is confirmation of trial context."}]
- GT support: Participants were randomly assigned to citalopram or placebo using permuted blocks with randomly varying block sizes stratified by site and by age (5-11 vs 12-17 years)
- Evidence row: {}
- Source context preview: ## Randomization and Blinding Participants were randomly assigned to citalopram or placebo using permuted blocks with randomly varying block sizes stratified by site and by age (5-11 vs 12-17 years). Two masked clinicians met with participants during each scheduled evaluation. The evaluating clinician monitored efficacy and was blinded to adverse events. The treating clinician reviewed efficacy ratings, monitored and recorded adverse events, and subsequently adjusted the medication dosage as clinically indicated. --- ## Methods The trial, NCT00086645, was registered at clinicaltrials.gov before initiation and was conducted at the following 6 academic medical centers: Mount Sinai School of...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The report describes a permuted-block randomization method but provides no details on allocation concealment (central randomization, opaque sealed envelopes, pharmacy-controlled assignment, or similar). Because the mechanism preventing foreknowledge of assignments is not reported, the risk of bias is unclear.
- Model support: Quote: "Participants were randomly assigned to citalopram or placebo using permuted blocks with randomly varying block sizes stratified by site and by age (5-11 vs 12-17 years)." Comment: Random sequence generation is described, but no information is provided about the method used to conceal allocations from those enrolling participants.
- Model support context: [{"source": "article", "quote": "Participants were randomly assigned to citalopram or placebo using permuted blocks with randomly varying block sizes stratified by site and by age (5-11 vs 12-17 years).", "relevance": "Describes sequence generation but does not state how allocation was concealed from recruiters or sites."}, {"source": "article", "quote": "Placebo matched for smell, taste, and viscosity was prepared at each site's pharmacy according to study specifications.", "relevance": "Shows matching placebo preparation at site pharmacy but gives no information on central randomization, sealed envelopes, or other concealment procedures."}]
- GT support: Details not provided
- Evidence row: {}
- Source context preview: ## Methods The trial, NCT00086645, was registered at clinicaltrials.gov before initiation and was conducted at the following 6 academic medical centers: Mount Sinai School of Medicine, New York, New York; North Shore–Long Island Jewish Health System, New York; University of North Carolina at Chapel Hill; University of California at Los Angeles; Yale University, New Haven, Connecticut; and Dartmouth Medical School, Hanover, New Hampshire. Each site's institutional review board approved the study. At least 1 parent or guardian for each participant provided written informed consent, and subjects who were capable provided assent. The National Institute of Mental Health convened a Data and...

#### Blinding of participants and personnel: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: during each scheduled evaluation
- Model rationale: The trial used placebo control and explicitly reports masked clinicians evaluating efficacy; for drug versus placebo with blinded evaluators, lack of participant awareness is implied and key personnel involved in outcome assessment were blinded, so outcomes were unlikely to be influenced by lack of blinding.
- Model support: Quote: "Two masked clinicians met with participants during each scheduled evaluation. The evaluating clinician monitored efficacy and was blinded to adverse events. The treating clinician reviewed efficacy ratings, monitored and recorded adverse events, and subsequently adjusted the medication dosage as clinically indicated." Comment: Participants were randomized to citalopram or placebo and clinicians were masked; interventions were drug versus placebo, and blinded clinicians assessed efficacy, reducing risk that knowledge of allocation influenced outcomes.
- Model support context: [{"source": "article", "quote": "Participants were randomly assigned to citalopram or placebo using permuted blocks... Two masked clinicians met with participants during each scheduled evaluation.", "relevance": "Shows placebo control and use of masked clinicians for evaluations, supporting blinding of study personnel."}, {"source": "article", "quote": "The evaluating clinician monitored efficacy and was blinded to adverse events. The treating clinician... adjusted the medication dosage as clinically indicated.", "relevance": "Indicates separation of roles with a blinded evaluator assessing outcomes, reducing performance bias for the review outcomes."}]
- GT support: Two masked clinicians met with participants during each scheduled evaluation
- Evidence row: {}
- Source context preview: ## Randomization and Blinding Participants were randomly assigned to citalopram or placebo using permuted blocks with randomly varying block sizes stratified by site and by age (5-11 vs 12-17 years). Two masked clinicians met with participants during each scheduled evaluation. The evaluating clinician monitored efficacy and was blinded to adverse events. The treating clinician reviewed efficacy ratings, monitored and recorded adverse events, and subsequently adjusted the medication dosage as clinically indicated. --- ## Methods The trial, NCT00086645, was registered at clinicaltrials.gov before initiation and was conducted at the following 6 academic medical centers: Mount Sinai School of...

#### Blinding of outcome assessment: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: evaluating clinician monitored efficacy
- Model rationale: The review-relevant outcomes (CGI-I and CYBOCS-PDD) were clinician-rated and the report explicitly states evaluating clinicians were masked; therefore outcome assessment was blinded and unlikely to be influenced by knowledge of allocation.
- Model support: Quote: "Two masked clinicians met with participants during each scheduled evaluation. The evaluating clinician monitored efficacy and was blinded to adverse events." Comment: The primary and key secondary outcomes (CGI-I and CYBOCS-PDD) were clinician-rated by an evaluating clinician who was explicitly masked.
- Model support context: [{"source": "article", "quote": "The primary outcome measure was the CGI-I rated by the evaluating clinician.", "relevance": "Identifies the review-relevant outcomes as clinician-rated (not self-report)."}, {"source": "article", "quote": "Two masked clinicians met with participants during each scheduled evaluation. The evaluating clinician...was blinded to adverse events.", "relevance": "States that outcome assessors (evaluating clinicians) were masked, supporting low detection bias."}]
- GT support: The evaluating clinician monitored efficacy and was blinded to AEs
- Evidence row: {}
- Source context preview: ## Efficacy Measures The primary outcome measure was the CGI-I rated by the evaluating clinician. The CGI-I is a subscale scored from 1 (very much improved) to 7 (very much worse).23 A score of 4 reflects no change. Positive response was defined by a score of 2 (much improved) or (very much improved) at week 12. The following 8 secondary outcomes were evaluated: the CYBOCS-PDD, a composite measure of the CGI-I and the CYBOCS-PDD (CGI-I score of 1 or 2 and a 25% reduction on the CYBOCS-PDD), and 6 subscales of the Repetitive Behavior Scale. The CYBOCS-PDD, which was rated by the evaluating clinician, is designed to measure the severity of repetitive behavior in children with ASDs.22 The 5...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Unclear risk
- Match: False
- GT observability: external_or_review_context (article observable: False)
- GT support phrase hits: 
- Model rationale: Randomized numbers and completion rates are reported (73 vs 76; 82.6% completed). Missingness was modest and similar across groups with comparable reasons (adverse events and withdrawn consent), and analyses used LOCF plus consistent complete-case analyses, meeting criteria for low risk.
- Model support: Quote: "149 were randomized to receive citalopram (n=73) or placebo (n=76). Most participants (82.6%) completed the 12-week trial. In the citalopram-treated group, 12.3% stopped early due to adverse events and another 2.7% withdrew consent; in the placebo group, 9.2% left early owing to adverse events and another 6.6% withdrew consent... For subjects who failed to complete all postrandomization assessments, the last observation was carried forward." Comment: Attrition was modest (≈17.4% overall), balanced across arms with similar reasons, and handled with LOCF plus consistent complete-case analyses showing similar results.
- Model support context: [{"source": "article", "quote": "149 were randomized to receive citalopram (n=73) or placebo (n=76). Most participants (82.6%) completed the 12-week trial.", "relevance": "Shows randomized numbers by arm and that 82.6% completed the trial (quantifies attrition)."}, {"source": "article", "quote": "In the citalopram-treated group, 12.3% stopped early due to adverse events and another 2.7% withdrew consent; in the placebo group, 9.2% left early owing to adverse events and another 6.6% withdrew consent... For subjects who failed to...", "relevance": "Provides reasons for missingness by arm and states the imputation method used (LOCF)."}]
- GT support: LTFU citalopram: 13 withdrew, 1 due to serious AE; 8 AEs; 2 protocol violations; 2 consent withdrawn LTFU placebo: 13 withdrawn, 7 AEs; 1 protocol violation; 5 consent withdrawn
- Evidence row: {}
- Source context preview: ## Results Two hundred forty-four of 331 participants screened by telephone were presumed eligible and were invited for a screening visit. Consent was obtained for 175 subjects, and 149 were randomized to receive citalopram (n=73) or placebo (n=76). Most participants (82.6%) completed the 12-week trial. In the citalopram-treated group, 12.3% stopped early due to adverse events and another 2.7% withdrew consent; in the placebo group, 9.2% left early owing to adverse events and another 6.6% withdrew consent (Figure 1). The citalopram-treated and placebo groups were balanced in terms of demographic and baseline characteristics, including age, sex, race/ethnicity, nonverbal IQ, Tanner stage,...


## 19798037 - Nidich 2009

- Mode: direct
- Review context: none (0 chars)
- Article chars: 21001
- Extraction context chars: n/a
- Total seconds: 24.56
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
| Incomplete outcome data: All outcomes | Low risk | High risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |

### Audit Details

#### Random sequence generation

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The paper reports 'random blocks method' and stratification, which implies randomization but fails to describe the random component (e.g., computer generator, random number table). Per criteria, insufficient detail about how the random sequence was generated warrants Unclear risk.
- Model support: Quote: "Students were then randomized to experimental or control groups, using the random blocks method21 stratifying on gender (male/female) and self-reported attention deficit hyperactivity disorder status (yes, no)..." Comment: The report states use of a 'random blocks method' with stratification but does not describe the random component (e.g., computer generator, random number table) or how the random blocks were generated.
- Model support context: [{"source": "article", "quote": "Students were then randomized to experimental or control groups, using the random blocks method21 stratifying on gender (male/female) and ...", "relevance": "Describes blocked randomization and stratification but does not specify how the random sequence was generated."}, {"source": "article", "quote": "The treatment group allocations were concealed by the study statistician, with individual treatment group assignments revealed to the project manager only when study participants completed baseline testing.", "relevance": "Speaks to allocation concealment process but does not provide detail on the sequence generation mechanism."}]
- GT support: Students were randomised to experimental or control groups, using the random blocks method, stratifying on gender.
- Evidence row: {}
- Source context preview: ## Study protocol Students were then randomized to experimental or control groups, using the random blocks method21 stratifying on gender (male/female) and self-reported attention deficit hyperactivity disorder status (yes, no), to either (a) immediate instruction in the TM program or (b) wait list/delayed start condition. (The attention deficit hyperactivity disorder stratification was for the purpose of a separate substudy.) --- ## Statistical methods Differences between the treatment groups on demographic and baseline variables was examined using t-tests for continuous variables and χ2-tests for categorical variables, and by multivariate analysis of variance to assess multivariate...

#### Allocation concealment

- Prediction: Low risk
- Ground truth: Unclear risk
- Match: False
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: with individual treatment group assignments revealed
- Model rationale: An independent study statistician held allocations and assignments were revealed only after baseline testing to the project manager, consistent with central concealment and preventing recruiters from foreseeing assignments, meeting Low risk criteria.
- Model support: Quote: "The treatment group allocations were concealed by the study statistician, with individual treatment group assignments revealed to the project manager only when study participants completed baseline testing." Comment: Allocation was held by an independent statistician and only revealed after baseline, preventing recruiters from foreseeing assignments.
- Model support context: [{"source": "article", "quote": "The treatment group allocations were concealed by the study statistician, with individual treatment group assignments revealed to the project manager only when study participants completed baseline testing.", "relevance": "Describes that allocation was concealed centrally by a statistician and revealed only after baseline testing, preventing foreknowledge by enrolment staff."}, {"source": "article", "quote": "Students were then randomized to experimental or control groups, using the random blocks method21 stratifying on gender ...", "relevance": "Confirms randomization procedure occurred but allocation concealment detail shows independent control of assignments."}]
- GT support: The treatment group allocations were concealed by the study statistician, with individual treatment group assignments revealed to the project manager only when study participants completed baseline testing.
- Evidence row: {}
- Source context preview: ## Study protocol The treatment group allocations were concealed by the study statistician, with individual treatment group assignments revealed to the project manager only when study participants completed baseline testing. Subjects were post-tested after ~3 months. All assessments were administered by research staff who were masked to treatment condition. Thus, this was a single-blind design. After post-test evaluation, wait-list participants were offered TM instruction. --- ## Statistical methods Differences between the treatment groups on demographic and baseline variables was examined using t-tests for continuous variables and χ2-tests for categorical variables, and by multivariate...

#### Blinding of participants and personnel: All outcomes

- Prediction: High risk
- Ground truth: Unclear risk
- Match: False
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The report explicitly states a single-blind design with masked assessors but gives no information that participants or intervention personnel were blinded. Because many review outcomes are subjective (coping, psychological distress) and the effect of lack of participant blinding is not addressed, there is insufficient information to judge Low or High risk. Calibration: visibly different intervention routes or wait-list control with subjective/clinical outcomes makes lack of participant/personnel blinding likely to be material.
- Model support: Quote: "All assessments were administered by research staff who were masked to treatment condition. Thus, this was a single-blind design." Comment: Assessors were masked, but participants and intervention personnel were not described as blinded; for patient-reported outcomes (e.g. coping, psychological distress) lack of participant blinding could influence results and the report does not state whether participants were blinded or the likely impact. Comment: Calibration: visibly different intervention routes or wait-list control with subjective/clinical outcomes makes lack of participant/personnel blinding likely to be material.
- Model support context: [{"source": "article", "quote": "esearch staff who were masked to treatment condition. Thus, this was a single-blind design. After post-test evaluation, wait-list participants were offered TM instruction. --- ## Study design This was a single-blind RCT comparing stress...", "relevance": "Calibration: visibly different intervention routes or wait-list control with subjective/clinical outcomes makes lack of participant/personnel blinding likely..."}, {"source": "article", "quote": "All assessments were administered by research staff who were masked to treatment condition. Thus, this was a single-blind design.", "relevance": "States that assessors were masked and labels the trial single-blind, relevant to who was blinded."}]
- GT support: Single-blind. We have left as unclear risk as it is difficult, if not impossible, to blind participants and personnel to lifestyle interventions.
- Evidence row: {}
- Source context preview: ## Study protocol The treatment group allocations were concealed by the study statistician, with individual treatment group assignments revealed to the project manager only when study participants completed baseline testing. Subjects were post-tested after ~3 months. All assessments were administered by research staff who were masked to treatment condition. Thus, this was a single-blind design. After post-test evaluation, wait-list participants were offered TM instruction. --- ## Study design This was a single-blind RCT comparing stress reduction with the TM program to wait-list controls on change in BP, psychological distress, and coping in young adults. The present study reports on both...

#### Blinding of outcome assessment: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly states that research staff who administered all assessments were masked to treatment condition. Because outcome assessment (casual blood pressure measured by staff and psychological questionnaires administered by masked staff) was performed by blinded assessors, detection bias is unlikely (Low risk).
- Model support: Quote: "All assessments were administered by research staff who were masked to treatment condition." Comment: Outcome assessment was performed by masked research staff, making detection bias unlikely for measured outcomes such as casual blood pressure and psychological questionnaires.
- Model support context: [{"source": "article", "quote": "All assessments were administered by research staff who were masked to treatment condition.", "relevance": "Explicit statement that outcome assessors (research staff) were masked to allocation, reducing detection bias."}, {"source": "article", "quote": "The primary outcome for the study was casual BP. Secondary outcomes were psychological distress and coping ability.", "relevance": "Identifies review-relevant outcomes (BP and self-report measures) and who assessed them is relevant to judge blinding impact."}]
- GT support: All assessments were administered by research staff who were masked to treatment condition.
- Evidence row: {}
- Source context preview: ## Study protocol Students were then randomized to experimental or control groups, using the random blocks method21 stratifying on gender (male/female) and self-reported attention deficit hyperactivity disorder status (yes, no), to either (a) immediate instruction in the TM program or (b) wait list/delayed start condition. (The attention deficit hyperactivity disorder stratification was for the purpose of a separate substudy.) --- ## Study protocol The treatment group allocations were concealed by the study statistician, with individual treatment group assignments revealed to the project manager only when study participants completed baseline testing. Subjects were post-tested after ~3...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: High risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The article reports 298 randomized, 207 completers and 91 non-completers, and explicitly states no baseline differences between completers and non-completers nor between groups among non-completers, so missing outcome data appear balanced and unlikely to be related to true outcomes, meeting Low risk criteria.
- Model support: Quote: "Table 1 shows baseline data for the 207 students who completed both BP baseline and post-testing by group." Comment: The report gives numbers for completers (207) and non-completers (91), states no baseline differences between completers and attriters and no differences between groups among non-completers, indicating missing data balanced and unlikely related to outcome.
- Model support context: [{"source": "article", "quote": "Table 1 shows baseline data for the 207 students who completed both BP baseline and post-testing by group.", "relevance": "Provides number of completers and indicates outcome data available for 207 participants."}, {"source": "article", "quote": "there were no significant differences between subjects who completed post-testing (n = 207) and those who did not complete post-testing (n = 91) on any of the primary or secondary outcome variables at baseline", "relevance": "States attriters and completers did not differ at baseline, suggesting missingness unlikely related to outcomes and balanced across groups."}]
- GT support: For relevant subgroup, 159 students were randomised and 112 completed 3-month follow-up (41.9% loss to follow-up).
- Evidence row: {}
- Source context preview: ## Front To further investigate the effectiveness of the TM program on BP, psychological distress, and coping, we conducted a randomized controlled trial (RCT) in college students. To our knowledge, this is the first RCT to evaluate the efficacy of a mind–body intervention on BP and psychological factors in young adults. --- ## Study protocol Students were then randomized to experimental or control groups, using the random blocks method21 stratifying on gender (male/female) and self-reported attention deficit hyperactivity disorder status (yes, no), to either (a) immediate instruction in the TM program or (b) wait list/delayed start condition. (The attention deficit hyperactivity disorder...


## 20044929 - Hegarty 2013

- Mode: direct
- Review context: none (0 chars)
- Article chars: 38512
- Extraction context chars: n/a
- Total seconds: 24.68
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Low risk | yes | no_support_phrase_match |  |
| Allocation concealment | Low risk | Unclear risk | no | article_absence_or_unclear | over-inferred_from_sparse_reporting |
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
- Model rationale: The report explicitly states block randomisation with random block sizes and that an independent statistician performed the randomisation, indicating an adequately random sequence generation process (Low risk).
- Model support: Quote: "block randomisation with random block sizes will be used within each stratum. The randomisation will be performed by a statistician not directly involved in the study and who is blinded to the identity of the practitioners." Comment: Describes use of random (block) allocation generated by an independent statistician, meeting criteria for a random component.
- Model support context: [{"source": "article", "quote": "block randomisation with random block sizes will be used within each stratum.", "relevance": "Specifies a random component to sequence generation (random block sizes)."}, {"source": "article", "quote": "The randomisation will be performed by a statistician not directly involved in the study and who is blinded to the identity of the practitioners.", "relevance": "Independent statistician performed randomisation, supporting appropriate sequence generation."}]
- GT support: Quote:"A statistician who was otherwise not involved in the study follow‐up, generated a random allocation sequence in Stata, stratified by location of each doctor’s practice (urban vs rural), with random permuted block sizes of two and four within each stratum" (p 252)
- Evidence row: {}
- Source context preview: ## Methods/Design The study conforms to the guidelines contained in the CONSORT statement for cluster randomised controlled trials [50]. Individual GPs (cluster) will be the unit of randomisation. The study includes one GP only per practice to circumvent the threat of contamination due to cross-over effects. Interventions and analyses will target two levels - the cluster (GP) level and individual (woman) level. The trial will include 40 GPs and consist of two arms - intervention and comparison. Figure 1 presents the anticipated flow of clusters and individual patients over the course of the trial. The study has received ethics approval from the Human Research Ethics Committee of The...

#### Allocation concealment

- Prediction: Low risk
- Ground truth: Unclear risk
- Match: False
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: An independent statistician performed randomisation and allocation occurred only after baseline data collection so recruiters and participants could not foresee or influence assignments, meeting criteria for adequate concealment (central allocation).
- Model support: Quote: "The randomisation will be performed by a statistician not directly involved in the study and who is blinded to the identity of the practitioners. Allocation of clusters to intervention or comparison will done following collection of baseline data. In other words, at the time of screening and recruitment of women, the allocation of GPs (and therefore, of women) will be unknown." Comment: Allocation was performed centrally by an independent statistician after baseline data collection, preventing recruiters from foreseeing assignments.
- Model support context: [{"source": "article", "quote": "The randomisation will be performed by a statistician not directly involved in the study and who is blinded to the identity of the practitioners.", "relevance": "Independent central generation of the sequence supports concealment from recruiters."}, {"source": "article", "quote": "Allocation of clusters to intervention or comparison will done following collection of baseline data...the allocation of GPs...will be unknown.", "relevance": "Allocation assigned after baseline ensures recruiters/enrollers could not foresee assignments."}]
- GT support: Comment:Unclear if concealment of randomisation was done adequately after randomisation was carried out. (The unit of randomisation is the unit of analysis for this review and hence for the purpose of risk of bias, it is considered an individual RCT, not a cluster RCT)
- Evidence row: {}
- Source context preview: ## Patient recruitment Patient recruitment will be done through methods validated in a recent primary care cohort study that screened for probable depression via postal survey, and included a screen for abuse [51]. In weave, for each participating GP, a list of female patients, aged 16 to 50 years who consulted the GP at least once in the previous 12 months will be randomly generated (maximum 600 patients per list). The GP will review the list and exclude those women who meet exclusion criteria. The remaining women will be mailed the screening questionnaire together with a letter from their GP endorsing the project, an information sheet, a resource card listing contact numbers for various...

#### Blinding of participants and personnel: All outcomes

- Prediction: High risk
- Ground truth: High risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly states both GPs and women were not blinded. The review-relevant outcomes (attitude, counseling, readiness, referral, knowledge) are subjective or behaviorally influenced and thus likely affected by lack of blinding, meeting criteria for High risk.
- Model support: Quote: "Due to the nature of the intervention (professional training plus patient counselling) it is not possible to blind the GPs to their status as intervention or control. ... women are not blinded in that they need to be aware that they may (intervention group) or may not (comparison group) be invited by the GP to discuss relationship issues" Comment: Participants and personnel were not blinded and outcomes (attitudes, counseling, readiness, referral) are subjective and likely influenced by knowledge of allocation.
- Model support context: [{"source": "article", "quote": "Due to the nature of the intervention ... it is not possible to blind the GPs to their status as intervention or control.", "relevance": "Shows GPs (personnel) were unblinded, relevant to performance bias."}, {"source": "article", "quote": "women are not blinded in that they need to be aware that they may or may not be invited by the GP to discuss relationship issues", "relevance": "Shows participants were unblinded; outcomes are patient-reported and likely influenced."}]
- GT support: Comment:High risk of performance bias as outcomes were self‐reported and participants were aware of which group they were allocated to Quote:"Because of the nature of the intervention, neither doctors nor patients could be masked to intervention." (p 252)
- Evidence row: {}
- Source context preview: ## Methods/Design The study conforms to the guidelines contained in the CONSORT statement for cluster randomised controlled trials [50]. Individual GPs (cluster) will be the unit of randomisation. The study includes one GP only per practice to circumvent the threat of contamination due to cross-over effects. Interventions and analyses will target two levels - the cluster (GP) level and individual (woman) level. The trial will include 40 GPs and consist of two arms - intervention and comparison. Figure 1 presents the anticipated flow of clusters and individual patients over the course of the trial. The study has received ethics approval from the Human Research Ethics Committee of The...

#### Blinding of outcome assessment: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: Outcome measurement was self-reported (women) and GP-reported for subjective outcomes (attitude, readiness, anxiety/depression), and the report explicitly states data collection was unblinded; thus lack of blinding was likely to influence these outcomes (High risk). Calibration: outcome measurement was objective/device/lab-based or centrally interpreted, so assessor knowledge is unlikely to materially bias measurement.
- Model support: Quote: "There is no blinding as regards data collection based on the CONSORT guidelines [50], as the women and GPs themselves complete the surveys (i.e. data were not collected by a research assistant blinded to the allocation)." Comment: Outcome assessment was done by unblinded participants (women) and unblinded GPs using self-completed surveys for subjective outcomes (attitudes, readiness, anxiety/depression), so measurement likely influenced by knowledge of allocation. Comment: Calibration: outcome measurement was objective/device/lab-based or centrally interpreted, so assessor knowledge is unlikely to materially bias measurement.
- Model support context: [{"source": "article", "quote": "audio-record consultations. We anticipate that only a small proportion of GPs and women will agree to have the sessions recorded. We will conduct semi-structured interviews with a sample of up to 20 women from each arm of the trial after...", "relevance": "Calibration: outcome measurement was objective/device/lab-based or centrally interpreted, so assessor knowledge is unlikely to materially bias measurement."}, {"source": "article", "quote": "There is no blinding as regards data collection... the women and GPs themselves complete the surveys", "relevance": "States outcome assessors (women and GPs) were not blinded and they self-completed subjective measures."}]
- GT support: Comment:unclear about blinding of assessors but outcomes were not subjective to assessor interpretation as the included outcomes from this study were self‐reported Quote:"...but study investigators and researchers following‐up patients and entering and analysing data were masked to allocation." (p 252)
- Evidence row: {}
- Source context preview: ## Data collection The primary outcomes (Table 1) include quality of life, measured across four dimensions (physical, psychological, environmental, social) using the WHOQoL-Bref [58], and mental health status, using the mental component of the SF-12 [59]. The third primary outcome is safety and is measured based on the existence of a safety plan (yes/no) and the number of safety behaviours enacted (Safety-Promoting Behaviour Checklist [60]). The secondary outcomes include open ended questions about readiness for change, based on the Domestic Violence Survivor Assessment [61], comfort to discuss abuse with GP (5-point likert scale), GPs' inquiry about the safety of women and their children...

#### Incomplete outcome data: All outcomes

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The excerpts are from a protocol-style report: they report planned ITT analysis and anticipated attrition but do not give actual randomized/enrolled/analyzed numbers, missing outcome counts by arm, reasons for missingness, or imputation/handling methods, so there is insufficient information to judge attrition bias.
- Model support: Quote: "analysis will be intention-to-treat." Comment: The protocol states ITT analysis and anticipates loss to follow-up ("approximately a third (88) will be lost to follow-up at 12 months"), but the report does not provide actual randomized, analyzed or missing outcome counts, reasons by arm, or how missing data will be handled, so risk of bias due to incomplete outcome data cannot be judged.
- Model support context: [{"source": "article", "quote": "\"analysis will be intention-to-treat.\"", "relevance": "States planned analysis approach but gives no observed attrition or handling details."}, {"source": "article", "quote": "\"a third (88) will be lost to follow-up at 12 months based on data from the diamond cohort\"", "relevance": "Provides an anticipated attrition estimate rather than actual missing outcome counts or reasons by arm."}]
- GT support: Comment:no missing primary outcome data. All secondary outcomes apart from Readiness to Change were reported Quote:" We have not yet analysed the open‐ended questions (at 6 months and 12 months) about readiness for change." (p 252)
- Evidence row: {}
- Source context preview: ## Data analysis and reporting Characteristics of GPs and women will be summarised using frequencies and percentages for categorical data, and means and standard deviations or percentiles for continuous data, for the two study arms. GP and women's characteristics will be compared between the two arms at recruitment to ensure that randomisation was effective. Intra-cluster correlations will be calculated for key outcome variables and patient variables at baseline. Appropriate modelling techniques will be used to account for the complexity of the study design, its hierarchical structure (women clustered within practices), stratification of practices at randomisation and repeated measures over...


## 20395225 - Alvarez 2010

- Mode: direct
- Review context: none (0 chars)
- Article chars: 32026
- Extraction context chars: n/a
- Total seconds: 24.03
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Unclear risk | Unclear risk | yes | no_support_phrase_match |  |
| Allocation concealment | Unclear risk | Unclear risk | yes | article_absence_or_unclear |  |
| Blinding of participants and personnel: All outcomes | High risk | High risk | yes | no_support_phrase_match |  |
| Blinding of outcome assessment: All outcomes | Unclear risk | High risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |
| Incomplete outcome data: All outcomes | Low risk | Unclear risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |

### Audit Details

#### Random sequence generation

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The article explicitly states participants were "randomly assigned" but provides no description of the sequence generation process (random number table, computer generator, coin toss, minimization, etc.). According to the criteria, this insufficient detail requires an 'Unclear risk' judgement.
- Model support: Quote: "participants were randomly assigned to one of two workshops (i.e., suspected child maltreatment reporting and ethnic cultural sensitivity)." Comment: The report states random assignment but does not describe the method used to generate the sequence (for example computer, random number table, drawing lots).
- Model support context: [{"source": "article", "quote": "participants were randomly assigned to one of two workshops", "relevance": "States that random assignment occurred but gives no details of the sequence generation method."}, {"source": "article", "quote": "a between-groups experimental methodology was used... and random assignment of participants", "relevance": "Reiterates use of random assignment but does not describe the random component or procedure."}]
- GT support: Comment:inadequate description of the generation of the randomised sequence Quote:"on completion of baseline measures, participants were randomly assigned to one of two workshops" (Alvarez 2010, p 215)
- Evidence row: {}
- Source context preview: ## Procedure On arriving for the workshops, participants were instructed to complete informed consent and baseline outcome measures. Measures were presented to each participant in random order to minimize order effects. On completion of the baseline measures, participants were randomly assigned to one of two workshops (i.e., suspected child maltreatment reporting and ethnic cultural sensitivity). Workshops were facilitated by nonlicensed graduate students at the master’s level, who were enrolled in a clinical psychology doctoral program. These facilitators used standardized agendas and protocol checklists depicting relevant content areas to be reviewed during the workshop. After completion...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The article confirms random assignment but provides no information on the allocation concealment method (e.g., central randomization, opaque sealed envelopes). Because concealment procedures are not described, risk of selection bias is unclear.
- Model support: Quote: "On completion of the baseline measures, participants were randomly assigned to one of two workshops (i.e., suspected child maltreatment reporting and ethnic cultural sensitivity)." Comment: The report states participants were randomly assigned but gives no details on how the allocation sequence was concealed from recruiters/enrollers.
- Model support context: [{"source": "article", "quote": "On completion of the baseline measures, participants were randomly assigned to one of two workshops", "relevance": "Describes that random assignment occurred but does not explain the method of allocation concealment."}, {"source": "not_reported", "quote": "No description of central randomization, sealed envelopes, numbered containers, or other concealment procedures", "relevance": "Absence of any specific concealment method prevents judgement of whether recruiters could foresee assignments."}]
- GT support: Comment:method of concealment not reported by study authors
- Evidence row: {}
- Source context preview: ## Rationale for Current Study To assist in determining the application of this training program to students and professionals of diverse backgrounds, a between-groups experimental methodology was used, including standardized training protocols, assessment of the integrity of training, and random assignment of participants to the child abuse reporting workshop or a workshop designed to enhance ethnic cultural sensitivity. Although not a focus in the current study, ethnic cultural sensitivity is an important skill set involved in the provision of therapy (Sue & Lam, 2002). Ethnic cultural sensitivity was chosen as the comparison workshop in this study because it has been shown to enhance...

#### Blinding of participants and personnel: All outcomes

- Prediction: High risk
- Ground truth: High risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The trial compared two visibly different training workshops with facilitators and participants aware of allocation; the review-relevant outcomes are subjective/behavioral (recognition, intent, clinical expertise) and thus likely influenced by lack of blinding, meeting criteria for High risk.
- Model support: Quote: "participants were randomly assigned to one of two workshops (i.e., suspected child maltreatment reporting and ethnic cultural sensitivity). Workshops were facilitated by nonlicensed graduate students..." Comment: Participants and facilitators clearly knew which workshop they attended; outcomes (recognition/intent to report, clinical expertise) are participant- and performance-based and likely influenced by knowledge of allocation.
- Model support context: [{"source": "article", "quote": "participants were randomly assigned to one of two workshops (i.e., suspected child maltreatment reporting and ethnic cultural sensitivity).", "relevance": "Shows allocation to visibly different active training conditions; participants knew which workshop they attended."}, {"source": "article", "quote": "Measures were readministered...including recognition and intent to report suspected child maltreatment, and clinical expertise in reporting suspected child maltreatment.", "relevance": "Outcomes are participant-reported/skill performance measures likely influenced by awareness of receiving the reporting workshop."}]
- GT support: Comment:performance bias due to lack of blinding, and therefore likely knowledge of the allocated intervention by participants and personnel during the study, which may have influenced subjective study outcomes (i.e. self‐report measures)
- Evidence row: {}
- Source context preview: ## Procedure On arriving for the workshops, participants were instructed to complete informed consent and baseline outcome measures. Measures were presented to each participant in random order to minimize order effects. On completion of the baseline measures, participants were randomly assigned to one of two workshops (i.e., suspected child maltreatment reporting and ethnic cultural sensitivity). Workshops were facilitated by nonlicensed graduate students at the master’s level, who were enrolled in a clinical psychology doctoral program. These facilitators used standardized agendas and protocol checklists depicting relevant content areas to be reviewed during the workshop. After completion...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: High risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: For the observer-rated outcome (intervention integrity assessed by independent raters), assessors are explicitly described as blind; therefore detection bias for these outcomes is unlikely. Other outcomes (self-reported vignette responses) were participant-reported and not blinded, but the provided evidence includes blinded assessor measurement for the observer-rated outcome, supporting Low risk for those assessed by blinded raters. Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support: Quote: "Blind independent raters observed the workshops and indicated on separate protocol checklists whether the facilitators completed each task. Protocol checklists completed by the facilitators and independent raters were compared. The facilitators...and the blind raters agreed these steps were completed." Comment: Outcome assessment of intervention integrity (observer-rated checklist) was performed by blind independent raters, making detection bias unlikely for these observer-rated outcomes. Comment: Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support context: [{"source": "article", "quote": "ated interpersonal violence scenarios. A total of 120 physicians and 172 additional staff completed pre and postviewing questionnaires, the results of which indicated improvements in the identification of physical indicators of...", "relevance": "Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported."}, {"source": "article", "quote": "Blind independent raters observed the workshops and indicated on separate protocol checklists whether the facilitators completed each task.", "relevance": "States that independent raters assessing protocol adherence were blind, indicating masked observer assessment for that outcome."}]
- GT support: Comment:detection bias due to knowledge of the allocated intervention by outcome assessors, and outcome measurement is likely to be influenced by lack of blinding (pre‐post self‐report measures tied closely to intervention purpose)
- Evidence row: {}
- Source context preview: ## Procedure On arriving for the workshops, participants were instructed to complete informed consent and baseline outcome measures. Measures were presented to each participant in random order to minimize order effects. On completion of the baseline measures, participants were randomly assigned to one of two workshops (i.e., suspected child maltreatment reporting and ethnic cultural sensitivity). Workshops were facilitated by nonlicensed graduate students at the master’s level, who were enrolled in a clinical psychology doctoral program. These facilitators used standardized agendas and protocol checklists depicting relevant content areas to be reviewed during the workshop. After completion...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Unclear risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report specifies the randomized sample size (55) and that only one participant was excluded due to inability to complete the postworkshop assessment; this small, explained loss is unlikely to bias the intervention effect, meeting Low risk criteria.
- Model support: Quote: "One participant was excluded from the study because this individual was unable to complete the postworkshop assessment." Comment: Only 1 of 56 participants was excluded with a stated reason, suggesting minimal and unlikely outcome-related missing data.
- Model support context: [{"source": "article", "quote": "The participants were 55 mental health professionals... One participant was excluded from the study because this individual was unable to complete the postworkshop assessment.", "relevance": "Reports number randomized/enrolled and states the single exclusion with reason, indicating near-complete outcome data."}, {"source": "article", "quote": "After completion of the workshops, participants were readministered the outcome measures in random order.", "relevance": "Confirms postworkshop assessment was planned and administered; supports that missing data were limited to one noncompleter."}]
- GT support: Comment:1 participant was excluded from analyses due to inability to complete the postintervention measure; however, authors do not report the participant's allocation condition (Alvarez 2010, p 212)
- Evidence row: {}
- Source context preview: ## Front The current article reports the development of a training program to assist professionals in effectively reporting suspected child maltreatment. Along these lines, we first underscore child maltreatment reporting practices and techniques that have been promoted based on clinical lore or results found in uncontrolled trials (i.e., did not involve random assignment of participants to experimental conditions or case trials involving multiple baseline or withdrawal experimental designs). We then review a training program that is specific to child maltreatment reporting and found to be efficacious in a single-case multiple baseline trial. This program incorporates many of the practices...


## 20655662 - Litt 2010

- Mode: direct
- Review context: none (0 chars)
- Article chars: 30746
- Extraction context chars: n/a
- Total seconds: 25.95
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
- Model rationale: The report explicitly states a 'computerized urn randomization procedure,' which constitutes a random method (computer-generated/minimization-like urn algorithm) meeting the Low risk criteria for sequence generation.
- Model support: Quote: "Those who agreed to participate were randomized to either the Standard Treatment group (STD; n=49) or to the Standard Treatment + Cognitive-Behavioral Treatment group (STD+CBT; n=52) using a computerized urn randomization procedure." Comment: A computerized urn randomization procedure describes a random component in sequence generation.
- Model support context: [{"source": "article", "quote": "Those who agreed to participate were randomized ... using a computerized urn randomization procedure.", "relevance": "Specifies a computerized urn randomization method, which is a random sequence generation process."}, {"source": "article", "quote": "The two conditions were balanced on gender, age, ethnic background, pain level recorded at baseline, and RDC axis I diagnoses.", "relevance": "Indicates the urn procedure was used to achieve balance, consistent with a random allocation algorithm."}]
- GT support: Stratified randomisation (computerised urn method) generated by an independent study co‐ordinator
- Evidence row: {}
- Source context preview: ## Procedure Those who agreed to participate were randomized to either the Standard Treatment group (STD; n=49) or to the Standard Treatment + Cognitive-Behavioral Treatment group (STD+CBT; n=52) using a computerized urn randomization procedure [28]. The two conditions were balanced on gender, age, ethnic background, pain level recorded at baseline, and RDC axis I diagnoses. The Project Coordinator entered the urn data during the intake session and informed the participants of their treatment assignments. The first treatment appointment was then scheduled for one to two weeks later, coinciding with the delivery of the splint. --- ## Procedure Analysis of main effects of treatment on each of...

#### Allocation concealment

- Prediction: Low risk
- Ground truth: High risk
- Match: False
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: The report specifies use of a computerized urn randomization procedure to assign participants, indicating allocation was generated centrally by a computer system rather than via an open list or predictable method; this meets the criteria for adequate concealment (central allocation).
- Model support: Quote: "Those who agreed to participate were randomized to either the Standard Treatment group (STD; n=49) or to the Standard Treatment + Cognitive-Behavioral Treatment group (STD+CBT; n=52) using a computerized urn randomization procedure [28]. The Project Coordinator entered the urn data during the intake session and informed the participants of their treatment assignments." Comment: Computerized urn randomization implies a central/randomized procedure run via computer, and the sequence was generated and assigned through that system rather than an open schedule, meaning recruiters could not foresee upcoming allocations.
- Model support context: [{"source": "article", "quote": "Those who agreed to participate were randomized ... using a computerized urn randomization procedure.", "relevance": "Describes a computerized central/random process for generating allocations, supporting concealment."}, {"source": "article", "quote": "The Project Coordinator entered the urn data during the intake session and informed the participants of their treatment assignments.", "relevance": "Shows assignments were determined by the computerized urn system at intake, limiting recruiters' ability to foresee allocations."}]
- GT support: Not discussed
- Evidence row: {}
- Source context preview: ## Procedure Those who agreed to participate were randomized to either the Standard Treatment group (STD; n=49) or to the Standard Treatment + Cognitive-Behavioral Treatment group (STD+CBT; n=52) using a computerized urn randomization procedure [28]. The two conditions were balanced on gender, age, ethnic background, pain level recorded at baseline, and RDC axis I diagnoses. The Project Coordinator entered the urn data during the intake session and informed the participants of their treatment assignments. The first treatment appointment was then scheduled for one to two weeks later, coinciding with the delivery of the splint. --- ## Procedure ### Assignment to treatment --- ## Procedure...

#### Blinding of participants and personnel: All outcomes

- Prediction: High risk
- Ground truth: High risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: Participants were informed of allocation and research staff assessing outcomes were not blinded; review-relevant outcomes (pain, disability) are subjective and thus likely influenced by lack of blinding, meeting High risk criteria.
- Model support: Quote: "The Project Coordinator entered the urn data during the intake session and informed the participants of their treatment assignments." Comment: Participants were explicitly told their assigned treatment; interventions (splint ± CBT) are visibly different and include subjective outcomes (pain, disability), so lack of participant/personnel blinding was likely to influence outcomes.
- Model support context: [{"source": "article", "quote": "The Project Coordinator...informed the participants of their treatment assignments.", "relevance": "Shows participants were told their allocation, indicating no participant blinding."}, {"source": "article", "quote": "A trained M.A.-level research associate, who was not blinded to treatment condition, conducted the pretreatment and follow-up research assessments.", "relevance": "Assessor/personnel were unblinded and conducted outcome assessments, increasing risk of bias for subjective outcomes."}]
- GT support: Not possible for participants to be blinded to treatment in this type of trial. Study personnel were not blinded.
- Evidence row: {}
- Source context preview: ## Procedure Those who agreed to participate were randomized to either the Standard Treatment group (STD; n=49) or to the Standard Treatment + Cognitive-Behavioral Treatment group (STD+CBT; n=52) using a computerized urn randomization procedure [28]. The two conditions were balanced on gender, age, ethnic background, pain level recorded at baseline, and RDC axis I diagnoses. The Project Coordinator entered the urn data during the intake session and informed the participants of their treatment assignments. The first treatment appointment was then scheduled for one to two weeks later, coinciding with the delivery of the splint. --- ## Procedure A trained M.A.-level research associate, who was...

#### Blinding of outcome assessment: All outcomes

- Prediction: High risk
- Ground truth: High risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The assessor was explicitly unblinded and the review-relevant outcomes (pain and interference) were measured using self-report questionnaires (MPI), so lack of blinding is likely to have influenced outcome measurement, meeting the criteria for High risk.
- Model support: Quote: "A trained M.A.-level research associate, who was not blinded to treatment condition, conducted the pretreatment and follow-up research assessments." Comment: Outcome assessment was performed by an unblinded assessor and outcomes (pain, interference, self-efficacy) are self-reported and thus likely influenced by knowledge of allocation.
- Model support context: [{"source": "article", "quote": "A trained M.A.-level research associate, who was not blinded to treatment condition, conducted the pretreatment and follow-up research assessments.", "relevance": "States the outcome assessor was unblinded, directly relevant to detection bias."}, {"source": "article", "quote": "Ratings of pain experience... Multidimensional Pain Inventory; Interference with activities was measured using the interference scale from the MPI.", "relevance": "Outcomes (pain, interference) are self-reported questionnaire measures susceptible to assessor/participant expectation effects."}]
- GT support: Outcome assessors not blinded as participant self‐report
- Evidence row: {}
- Source context preview: ## Measures and Instruments Readiness to engage in self-management treatment for chronic pain was assessed using the Pain Stages of Change Questionnaire [PSOCQ; 11; 12]. The PSOCQ assesses readiness using 30 Likert-scaled items scored from 1 (strongly disagree) to 5 (strongly agree), and comprising four scales: Precontemplation (e.g., `All of this talk about how to cope better is a waste of my time'), Contemplation (e.g., `I have been thinking that the way I cope with my pain could improve'), Action (e.g., `I am developing new ways to cope with my pain') and Maintenance (e.g., `I use what I have learned to help keep my pain under control'). The internal reliabilities of these scales ranged...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report provides randomized sample size (101) and proportions with outcome data (88% posttreatment, 73% at 52 weeks) and explicitly states losses were equivalent across treatment conditions, meeting criteria for Low risk because missing outcome data are balanced with similar reasons across groups.
- Model support: Quote: "Of 196 persons screened, 121 were deemed eligible for the study, and 101 were assigned to treatment. At posttreatment 88% of patients provided data, and 73% provided data at 52 weeks. Losses to follow-up were equivalent across treatment conditions." Comment: Attrition percentages reported with statement that losses were equivalent across arms, suggesting balanced and unlikely to bias comparisons.
- Model support context: [{"source": "article", "quote": "Of 196 persons screened, 121 were deemed eligible for the study, and 101 were assigned to treatment.", "relevance": "Shows number randomized (N=101), needed to assess attrition."}, {"source": "article", "quote": "At posttreatment 88% of patients provided data, and 73% provided data at 52 weeks. Losses to follow-up were equivalent across treatment conditions.", "relevance": "Gives proportion with outcome data at follow-ups and explicitly states losses were equivalent across arms."}]
- GT support: "At posttreatment 88% of patients provided data, and 73% provided data at 52 weeks. Losses to follow‐up were equivalent across treatment conditions." "Analysis of main effects of treatment on each of the three major dependent variables was conducted using a mixed model regression procedure (Proc MIXED, SAS Institute [25]), and an intent‐to‐treat approach."
- Evidence row: {}
- Source context preview: ## Participants The mean age of the sample was 39.4 years (SD = 12.1). The majority of participants were white (79%), with 9% black, 9% of Hispanic origin, and 3% self-described as Other. Forty-one percent were married or cohabiting. The average years of education was 14.7 (SD = 2.5). The participants reported having chronic TMD pain for 6.7 years on average (SD = 6.6), with a mean pain intensity rating of 3.5 on a scale to 6 (SD = 1.3). Of 196 persons screened, 121 were deemed eligible for the study, and 101 were assigned to treatment. At posttreatment 88% of patients provided data, and 73% provided data at 52 weeks. Losses to follow-up were equivalent across treatment conditions. The...


## 20740213 - Jo 2010

- Mode: direct
- Review context: none (0 chars)
- Article chars: 16249
- Extraction context chars: n/a
- Total seconds: 24.34
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
| Incomplete outcome data: All outcomes | Low risk | Low risk | yes | unknown |  |

### Audit Details

#### Random sequence generation

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: The article reports allocated group sizes (20 per group) but provides no details on the method used to generate the allocation sequence; therefore there is insufficient information to judge whether the sequence was truly random.
- Model support: Quote: "After performing sternotomy, patients received saline (n=20, controls) or milrinone (n=20, Sanofi, Korea) 0.5 µg/kg/min during coronary artery anastomosis." Comment: The report gives group sizes but does not describe how patients were allocated/randomized or what random component was used.
- Model support context: [{"source": "article", "quote": "After performing sternotomy, patients received saline (n=20, controls) or milrinone (n=20...", "relevance": "Shows group allocation and numbers but does not describe sequence generation method."}, {"source": "not_reported", "quote": "No description of random number table, computer generator, coin toss, sealed envelopes, or other random method.", "relevance": "Absence of any described random component prevents judgment of Low or High risk."}]
- GT support: No information provided
- Evidence row: {}
- Source context preview: ## Materials and Methods Exclusion criteria included left or right ventricular ejection fraction of less than 40% from the transthoracic echocardiogram before surgery, valvular heart disease, severe cerebral or renal dysfunction, or emergency surgery. Patients with stenosis at more than 3 coronary arteries were selected. An hour before arriving at the operating rooms, all patients received an intramuscular injection of morphine, 0.05-0.1 mg/kg, as preliminary anesthesia, and other drugs, except digoxin and diuretics, as normal. After arriving at the operating room, the induction of lead II and V5 was continuously monitored by 5-leads electrocardiography, and a catheter was inserted by...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: The report provides group sizes and timing of consent but contains no information on how treatment assignments were concealed (no description of central allocation, opaque sealed envelopes, numbered containers, or equivalent). Therefore there is insufficient information to judge allocation concealment.
- Model support: Quote: "After performing sternotomy, patients received saline (n=20, controls) or milrinone (n=20, Sanofi, Korea) 0.5 µg/kg/min during coronary artery anastomosis." Comment: The report gives group sizes but does not describe how the allocation sequence was concealed before assignment (no mention of central randomization, sealed envelopes, or other safeguards).
- Model support context: [{"source": "article", "quote": "After performing sternotomy, patients received saline (n=20, controls) or milrinone (n=20, Sanofi, Korea) 0.5 µg/kg/min during coronary artery anastomosis.", "relevance": "Shows numbers randomized per group but does not describe the concealment method used prior to assignment."}, {"source": "article", "quote": "This study was authorized by the Institutional Review Board and was conducted with OPCAB patients after written consent, before giving them anesthetic.", "relevance": "States timing of consent but gives no detail on allocation concealment procedures (central randomization, envelopes, etc.)."}]
- GT support: No information provided
- Evidence row: {}
- Source context preview: ## Materials and Methods For inducing anesthesia, endotracheal intubation was performed after giving intravenous injections of midazolam 2.5 mg, sufentanil 1.5-3.0 µg/kg, and rocuronium bromide 50 mg. To maintain anesthesia, sufentanil (0.5-1.5 µg/kg/h) and vecuronium were continuously administered intravenously with 50% oxygen and 50% medical air, as well as sevoflurane with an end-tidal concentration of 0.2-0.4 vol%, and controlled ventilation was conducted to set the end-tidal CO2 tension at 30-35 mmHg. After inducing anesthesia, isosorbide dinitrate (0.5 µg/kg/min) was administered to prevent myocardial ischemia and coronary vasospasm, and a transesophageal echocardiography probe was...

#### Blinding of participants and personnel: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: The report explicitly states key personnel were blinded, and the review-relevant outcomes are objective physiological measurements and clinical events, so lack of participant knowledge (unclear) would be unlikely to bias these outcomes, meeting Low risk criteria.
- Model support: Quote: "All procedures were performed by the same cardiac surgeon and anesthesiologist blinded to the treatment groups." Comment: Key personnel (surgeon and anesthesiologist) were explicitly blinded during the intervention, and outcomes (death, MI, stroke, hemodynamic measures via pulmonary artery catheter) are objective physiological or hard clinical events unlikely to be materially influenced by participant expectation.
- Model support context: [{"source": "article", "quote": "All procedures were performed by the same cardiac surgeon and anesthesiologist blinded to the treatment groups.", "relevance": "Direct statement that key care personnel were blinded to treatment allocation."}, {"source": "article", "quote": "Variables included heart rate, mean arterial pressure... cardiac output... and we recorded permanent cerebral infarction for 30 days after the operation", "relevance": "Outcomes are objective physiological measurements and clinical events less likely biased by lack of participant blinding."}]
- GT support: Double-blind study
- Evidence row: {}
- Source context preview: ## Materials and Methods For inducing anesthesia, endotracheal intubation was performed after giving intravenous injections of midazolam 2.5 mg, sufentanil 1.5-3.0 µg/kg, and rocuronium bromide 50 mg. To maintain anesthesia, sufentanil (0.5-1.5 µg/kg/h) and vecuronium were continuously administered intravenously with 50% oxygen and 50% medical air, as well as sevoflurane with an end-tidal concentration of 0.2-0.4 vol%, and controlled ventilation was conducted to set the end-tidal CO2 tension at 30-35 mmHg. After inducing anesthesia, isosorbide dinitrate (0.5 µg/kg/min) was administered to prevent myocardial ischemia and coronary vasospasm, and a transesophageal echocardiography probe was...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: Outcome measurement (cardiac index, RVEF, pressures) was objective, device-based (pulmonary artery catheter, computerized monitoring), and clinicians were reported blinded; therefore detection bias is unlikely. Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support: Quote: "All procedures were performed by the same cardiac surgeon and anesthesiologist blinded to the treatment groups." Comment: The key hemodynamic outcomes (cardiac index, RVEF, pulmonary pressures) were measured by automated/continuous monitors and a pulmonary artery catheter (thermodilution) rather than subjective assessment, and clinicians performing procedures were blinded. Comment: Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support context: [{"source": "article", "quote": "## Materials and Methods For inducing anesthesia, endotracheal intubation was performed after giving intravenous injections of midazolam 2.5 mg, sufentanil 1.5-3.0 µg/kg, and rocuronium bromide 50 mg. To maintain anesthesia, sufentanil...", "relevance": "Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported."}, {"source": "article", "quote": "All procedures were performed by the same cardiac surgeon and anesthesiologist blinded to the treatment groups.", "relevance": "States that the clinicians involved in surgery were blinded to treatment allocation."}]
- GT support: Double-blind study
- Evidence row: {}
- Source context preview: ## Materials and Methods For inducing anesthesia, endotracheal intubation was performed after giving intravenous injections of midazolam 2.5 mg, sufentanil 1.5-3.0 µg/kg, and rocuronium bromide 50 mg. To maintain anesthesia, sufentanil (0.5-1.5 µg/kg/h) and vecuronium were continuously administered intravenously with 50% oxygen and 50% medical air, as well as sevoflurane with an end-tidal concentration of 0.2-0.4 vol%, and controlled ventilation was conducted to set the end-tidal CO2 tension at 30-35 mmHg. After inducing anesthesia, isosorbide dinitrate (0.5 µg/kg/min) was administered to prevent myocardial ischemia and coronary vasospasm, and a transesophageal echocardiography probe was...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: The report explicitly states no early deaths and similar reported event rates across groups and provides randomized counts (20 per group), satisfying criteria that there is no or balanced missing outcome data for the early clinical outcomes, supporting Low risk.
- Model support: Quote: "there were no early deaths; both groups showed similar rates of myocardial infarction, cerebral infarction, renal failure, mechanical ventilation lasting more than 48 hours, re-operation, and infections (Table 6)." Comment: Report states no early deaths and similar complication rates between groups, implying low and balanced missing outcome data for the early clinical endpoints.
- Model support context: [{"source": "methodology", "quote": "Quote: \"there were no early deaths; both groups showed similar rates of myocardial infarction, cerebral infarction, renal failure, mechanical ventilation lasting more than 48 hours, re-operation, and infections (Table 6).\" Comment: Report...", "relevance": "Recovered from malformed JSON; inspect raw output if this judgement matters."}]
- GT support: No missing outcome data
- Evidence row: {}
- Source context preview: ## Results OPCAB was performed successfully without transition to emergency cardiopulmonary bypass. There were no significant statistical differences between the 2 groups for gender, age, medical history of diabetes and hypertension, drug administration, or left ventricle ejection rate (Table 1). The total operation time, coronary artery anastomosis, and total norepinephrine volume were similar for both groups (Table 2). Heart movement and stabilization for anastomosis did not require treatment of arrhythmia. --- ## Results Cardiac index decreased in controls during OM anastomosis, whereas milrinone treatment increased it (P < 0.05, Table 3). Milrinone also blocked the increase in pulmonary...


## 20830695 - Deblinger 2011

- Mode: direct
- Review context: none (0 chars)
- Article chars: 29800
- Extraction context chars: n/a
- Total seconds: 25.04
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Unclear risk | Unclear risk | yes | no_support_phrase_match |  |
| Allocation concealment | Unclear risk | Unclear risk | yes | no_support_phrase_match |  |
| Blinding of participants and personnel: All outcomes | Unclear risk | High risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |
| Blinding of outcome assessment: All outcomes | Unclear risk | High risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |
| Incomplete outcome data: All outcomes | Unclear risk | Low risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |

### Audit Details

#### Random sequence generation

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The excerpts only state that children were 'randomly assigned' but provide no details about the sequence generation process (no description of random number generator, table, drawing lots, minimization, etc.), so there is insufficient information to judge low or high risk.
- Model support: Quote: "each child was randomly assigned to one of the four treatment conditions." Comment: The report states participants were 'randomly assigned' but gives no description of the method (e.g., computer, random number table, coin toss) or any random component, so sequence generation cannot be judged.
- Model support context: [{"source": "article", "quote": "Following the initial assessment, each child was randomly assigned to one of the four treatment conditions.", "relevance": "States that random assignment occurred but does not describe how the random sequence was generated."}, {"source": "article", "quote": "Two hundred ten children... were randomly assigned to one of four treatment conditions.", "relevance": "Confirms random assignment and sample size but lacks detail on the randomization method."}]
- GT support: Comment: the authors only reported that participants were randomly allocated.
- Evidence row: {}
- Source context preview: ## Procedures Although detailed descriptions of TF-CBT can be found elsewhere, 4, 5 TF-CBT includes components that spell out the acronym PRACTICE: Psychoeducation and parenting, Relaxation, Affective modulation, Cognitive coping, TN, In vivo exposure, Conjoint parent child sessions and Enhancing safety and future development. TF-CBT, with all the components including the TN component, was only provided to those participants randomly assigned to the Yes TN conditions. In the Yes TN conditions, the TN component was covered in 3–4 sessions in the 8 session condition with at least double that number of TN sessions in the 16 session condition. For all participants, treatment typically began...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The article confirms random assignment but provides no information on allocation concealment methods (central randomization, sealed envelopes, etc.). Necessary details about who generated/held the sequence or how assignments were concealed from recruiters are missing, so risk is unclear.
- Model support: Quote: "Following the initial assessment, each child was randomly assigned to one of the four treatment conditions." Comment: The report states random assignment but gives no details on how the allocation sequence was concealed from recruiters or who controlled assignment, so concealment method is unclear.
- Model support context: [{"source": "article", "quote": "Following the initial assessment, each child was randomly assigned to one of the four treatment conditions.", "relevance": "States random assignment occurred but does not describe the concealment mechanism."}, {"source": "article", "quote": "Because the project coordinator was blind to treatment assignment, participants were told of the treatment assignment by the therapist during the first treatment session.", "relevance": "Indicates coordinator was blind but does not explain how allocations were concealed prior to assignment or who held the allocation list."}]
- GT support: Comment: not mentioned and unlikely to have been done
- Evidence row: {}
- Source context preview: ## Procedures Following the initial assessment, each child was randomly assigned to one of the four treatment conditions. The families were told that they would be paid $25 for completing the initial evaluation, $25 for a 4 week evaluation, $50 for an 8 week evaluation, 16 week evaluation, and 6 and 12 month evaluations. Because the project coordinator was blind to treatment assignment, participants were told of the treatment assignment by the therapist during the first treatment session. All siblings participating in the study were assigned to the same condition. The therapists had graduate degrees in psychology, clinical social work, or a related field and had at least three years of...

#### Blinding of participants and personnel: All outcomes

- Prediction: Unclear risk
- Ground truth: High risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: Therapists informed participants of treatment and delivered visibly different psychotherapy components; given subjective psychosocial outcomes, lack of participant/personnel blinding is likely to have influenced outcomes, meeting High risk criteria. Calibration: lack of blinding is plausible for this behavioral/lifestyle intervention, but the supplied evidence does not clearly show a material influence on the review-relevant outcomes.
- Model support: Quote: "Because the project coordinator was blind to treatment assignment, participants were told of the treatment assignment by the therapist during the first treatment session." Comment: Participants and therapists were informed of allocation at first session, so both knew treatment; outcomes (anxiety, depression, PTSD, behavior, QoL, self-harm, social functioning) are largely subjective and likely influenced by lack of blinding. Comment: Calibration: lack of blinding is plausible for this behavioral/lifestyle intervention, but the supplied evidence does not clearly show a material influence on the review-relevant outcomes.
- Model support context: [{"source": "article", "quote": "scriptions of TF-CBT can be found elsewhere, 4, 5 TF-CBT includes components that spell out the acronym PRACTICE: Psychoeducation and parenting, Relaxation, Affective modulation, Cognitive coping, TN, In vivo exposure, Conjoint parent...", "relevance": "Calibration: lack of blinding is plausible for this behavioral/lifestyle intervention, but the supplied evidence does not clearly show a material influence on..."}, {"source": "article", "quote": "Because the project coordinator was blind to treatment assignment, participants were told of the treatment assignment by the therapist during the first treatment session.", "relevance": "Shows therapists informed participants of allocation, indicating no blinding of participants or personnel."}]
- GT support: Comment: not mentioned and unlikely to have been done
- Evidence row: {}
- Source context preview: ## Procedures Following the initial assessment, each child was randomly assigned to one of the four treatment conditions. The families were told that they would be paid $25 for completing the initial evaluation, $25 for a 4 week evaluation, $50 for an 8 week evaluation, 16 week evaluation, and 6 and 12 month evaluations. Because the project coordinator was blind to treatment assignment, participants were told of the treatment assignment by the therapist during the first treatment session. All siblings participating in the study were assigned to the same condition. The therapists had graduate degrees in psychology, clinical social work, or a related field and had at least three years of...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: High risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The outcomes relevant to the review (anxiety, depression, PTSD symptoms, behavior, QoL, social functioning) are measured by parent- and child self-report instruments; the excerpts do not report whether participants or outcome assessors were blinded or whether blinding could have been maintained, so there is insufficient information to judge detection bias.
- Model support: Quote: "Parent Emotional Reaction Questionnaire (PERQ) ... is a 15-item self-report instrument" Comment: Outcomes (parent- and child- reported measures of depression, shame, parenting practices, PTSD symptoms, etc.) are self-reported, but the report does not state whether outcome assessors or participants were blinded to allocation or whether masking was attempted.
- Model support context: [{"source": "article", "quote": "Parent Emotional Reaction Questionnaire (PERQ) ... is a 15-item self-report instrument", "relevance": "Shows parent-reported outcomes were used; self-report means assessor = participant and blinding matters."}, {"source": "article", "quote": "The Children’s Depression Inventory (CDI) ... is a 27-item self-report instrument", "relevance": "Shows child-reported outcomes were used; no information given about whether participants were blinded to treatment."}]
- GT support: Comment: children's self-reports and parents’ reports
- Evidence row: {}
- Source context preview: ## Data analysis Two-factor, linear mixed-model repeated-measures ANOVAs were next performed with all of the 14 outcome measures. The main effects were for type of condition (8 No TN, 8 Yes TN, 16 No TN, and 16 Yes TN) and time (pre-treatment, 8 weeks, and 16 weeks) and the interaction was for type of condition by time. The identity of the children or parents was considered to represent a random effect in the repeated ANOVAs. All 14 outcome measures for the four groups significantly (ps < .05, two-tailed test) improved over time. However, none of the mean differences for the 14 outcome measures between the 8- and 16-week evaluations for the families that were treated in the 8 session groups...

#### Incomplete outcome data: All outcomes

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report gives total randomized (210) and total dropouts (31, 15%) and notes completer analyses and multiple imputation were performed, but it does not report missing/outcome data by arm, reasons by arm, or analyzed counts for each outcome, so there is insufficient reporting to judge whether missing data could bias effect estimates.
- Model support: Quote: "Two hundred ten children... were randomly assigned to one of four treatment conditions..." "16 (8%) children and their parents never returned after being assigned to treatment, and 15 (7%)... left after attending only one or two sessions. These 31 (15%)... were defined as dropouts. Therefore, 179 (85%) children attended at least three TF-CBT sessions. This sample of completers was used for the subsequent analyses." Comment: The report describes 31 dropouts and that analyses were based on completers (>=3 sessions) but also states intent-to-treat analyses with multiple imputation were run and gave similar results; however the paper does not provide randomized/analyzed counts by arm, missing outcome counts by arm, or detailed reasons by arm to judge balance or potential bias.
- Model support context: [{"source": "article", "quote": "Two hundred ten children... were randomly assigned to one of four treatment conditions.", "relevance": "States number randomized (210) and four arms; needed for attrition assessment."}, {"source": "article", "quote": "16 (8%)... never returned... and 15 (7%)... left after attending only one or two sessions... 179 (85%) children attended at least three TF-CBT sessions. This sample of completers was used for the subsequent analyses.", "relevance": "Provides total dropouts (31, 15%) and that completer sample was analyzed, but lacks by-arm missing counts/reasons and primary outcome analyzed counts."}]
- GT support: Comment: 31 children and their parents dropped out. Differences between completers and non-completers were not statistically significant. Authors analysed data on an intention-to-treat (ITT) basis.
- Evidence row: {}
- Source context preview: ## RESULTS Figure 1 shows the number of children who completed three or more sessions and a post-test K-SADS assessment in each of the treatment conditions. The mean number of TF-CBT sessions attended by the 87 children and their parents in the two 8 session conditions was 7.36 (SD = 1.33, median = 8, range = 3 – 8), whereas the mean number was 13.92 (SD = 3.34, median = 16, range 3 – 16) for the 92 children and their parents in the two 16 session conditions. Of the children/parents assigned to the 8 session conditions, 63 (72%) completed all eight treatment sessions, whereas only 50 (54%) of the children/parents assigned to the 16 session conditions completed all 16 sessions of treatment....


## 21342490 - Freeman 2011

- Mode: direct
- Review context: none (0 chars)
- Article chars: 20821
- Extraction context chars: n/a
- Total seconds: 26.07
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
| Incomplete outcome data: All outcomes | Low risk | Low risk | yes | no_support_phrase_match |  |

### Audit Details

#### Random sequence generation

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The article excerpts only state that participants 'were randomized' without describing a random component (computer generator, random number table, minimization, etc.). Because the method of sequence generation is not reported in the supplied text, risk of bias is unclear.
- Model support: Quote: "Men and women aged 70-82 (n = 5804) ... were randomized to placebo or pravastatin (40 mg per day) treatment." Comment: The report states participants were randomized but gives no description of the method used to generate the allocation sequence.
- Model support context: [{"source": "article", "quote": "Men and women aged 70-82 (n = 5804) ... were randomized to placebo or pravastatin (40 mg per day) treatment.", "relevance": "States that randomization occurred but does not describe the random sequence generation method."}, {"source": "article", "quote": "The design and outcome of PROSPER is described elsewhere.", "relevance": "Refers to external protocol details but the provided excerpts do not report how the random sequence was generated."}]
- GT support: Randomized, double-blind, placebo-controlled trial. "The randomization sequence was generated with a computerized random number generator and consisted of balanced blocks of size four." "Randomization was performed using the method of permuted blocks, stratified by site."
- Evidence row: {}
- Source context preview: ## Background Venous thromboembolism (VTE) has an incidence of 1-2 per 1000 individuals per year but is close to 1% per annum in those aged over 70 years[1]. VTE is a leading cause of death in hospital inpatients[2] and is a major cause of morbidity and mortality particularly in older people and among those with cancer[1,3]. Despite the fact that 70% of patients with VTE are aged over 60[1], there are few studies of risk factors in the elderly. Other studies have analyzed effects of pre-existing statin medication on incident VTE [4-6] or have compared statin use in case control studies of VTE[7-9]. A post hoc analysis of the Heart and Estrogen/progestin Replacement Study (HERS)[4] and...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The excerpts confirm randomization occurred but contain no information on the method used to conceal allocation (central system, opaque sealed envelopes, numbered containers, or unsecured list). Because the necessary detail on concealment procedures is missing, risk of selection bias cannot be judged and is Unclear.
- Model support: Quote: "Men and women aged 70-82 (n = 5804) ... were randomized to placebo or pravastatin (40 mg per day) treatment." Comment: The report states participants were randomized but gives no details of the allocation concealment method (for example central randomization, sealed envelopes, or other safeguards).
- Model support context: [{"source": "article", "quote": "Men and women aged 70-82 (n = 5804) ... were randomized to placebo or pravastatin (40 mg per day) treatment.", "relevance": "Shows the trial was randomized but does not describe how allocations were concealed prior to assignment."}, {"source": "article", "quote": "The design and outcome of PROSPER is described elsewhere[15-17].", "relevance": "Referral to other sources suggests allocation details may be reported elsewhere but are not provided in the supplied excerpts."}]
- GT support: Randomization was done by telephone call or through fax exchange with the study data center.
- Evidence row: {}
- Source context preview: ## Statistical analysis Data were analyzed using SAS vs9.1 (SAS Institute Inc, Cary NC). Where necessary continuous variables were transformed logarithmically to give a near-normal distribution of data for parametric analysis. Where data were available from the entire cohort, analyses were carried out using cases and non-cases (n = 5627) not using warfarin at baseline, including 2834 patients allocated to pravastatin and 2865 to placebo. The time to VTE was quantified by univariate hazard ratios and 95% confidence intervals calculated with Cox's proportional hazard model for each variable of interest. In the multivariate analyses, forward stepwise regression was undertaken, where all...

#### Blinding of participants and personnel: All outcomes

- Prediction: Low risk
- Ground truth: Unclear risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly calls PROSPER 'double-blind, placebo-controlled', indicating blinding of participants and key personnel; the review-relevant outcome (VTE) was determined from objective diagnostic tests and records, so lack of blinding would be unlikely to influence outcome measurement.
- Model support: Quote: "The Prospective Study of Pravastatin in the Elderly at Risk (PROSPER) was a multi-centre, randomized, double-blind, placebo-controlled trial of pravastatin in the prevention of vascular disease in the elderly" Comment: Trial described as randomized, double-blind and placebo-controlled, so participants and personnel were blinded and outcomes (VTE events confirmed by records/tests) are objective and unlikely to be influenced by participant/personnel knowledge.
- Model support context: [{"source": "article", "quote": "PROSPER was a multi-centre, randomized, double-blind, placebo-controlled trial of pravastatin", "relevance": "States that the trial was double-blind and placebo-controlled, indicating blinding of participants and personnel."}, {"source": "article", "quote": "Events were categorized as definite VTE if death from VTE was confirmed on the death certificate or if there was recorded evidence from investigations such as ultrasound venography ventilation perfusion lung scans or computed tomography...", "relevance": "Primary outcomes (VTE) were based on objective diagnostic tests and records, making them unlikely to be influenced by lack of blinding."}]
- GT support: Described as double-blind, but no details provided
- Evidence row: {}
- Source context preview: ## Background The Prospective Study of Pravastatin in the Elderly at Risk (PROSPER) was a multi-centre, randomized, double-blind, placebo-controlled trial of pravastatin in the prevention of vascular disease in the elderly[15]. The present study is an analysis of incident VTE in this population of men and women aged 70-82 using data from the PROSPER database. The aim was to determine whether pravastatin reduces VTE incidence in older people. In addition, we assessed the impact of clinical, hematological, lipid, inflammatory and vascular risk factors for incident VTE in older age. --- ## Subjects The design and outcome of PROSPER is described elsewhere[15-17]. Men and women aged 70-82 (n =...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: Although the trial is described as double-blind, the VTE outcomes were adjudicated by clinicians reviewing medical records and the report does not state whether these outcome assessors were blinded to allocation; therefore there is insufficient information to judge detection bias.
- Model support: Quote: "The Prospective Study of Pravastatin in the Elderly at Risk (PROSPER) was a multi-centre, randomized, double-blind, placebo-controlled trial of pravastatin..." Comment: Trial is described as double-blind, but the report does not state who assessed VTE outcomes (clinicians reviewing records, treating clinicians, or blinded adjudicators) nor whether the outcome assessors were blinded, so insufficient information to judge detection bias.
- Model support context: [{"source": "article", "quote": "The Prospective Study of Pravastatin in the Elderly at Risk (PROSPER) was a multi-centre, randomized, double-blind, placebo-controlled trial of pravastatin in the prevention of vascular disease in the elderly.", "relevance": "States overall trial was double-blind but does not specify who performed outcome assessment for VTE or confirm they were blinded."}, {"source": "article", "quote": "For the present study the full medical records were retrieved for all suspected VTE in the PROSPER database and examined by three clinicians in a pre-planned post hoc analysis. A consensus of two clinical opinions was required to confirm...", "relevance": "Describes outcome ascertainment by clinicians reviewing records but does not state whether these reviewers were blind to treatment allocation."}]
- GT support: Unclear. No details were found.
- Evidence row: {}
- Source context preview: ## Subjects The design and outcome of PROSPER is described elsewhere[15-17]. Men and women aged 70-82 (n = 5804) with evidence of pre-existing vascular disease or at least one major risk factor for vascular disease were randomized to placebo or pravastatin (40 mg per day) treatment. Follow up was 3.2 years on average. For the present study the full medical records were retrieved for all suspected VTE in the PROSPER database and examined by three clinicians in a pre-planned post hoc analysis. Events were categorized as definite VTE if death from VTE was confirmed on the death certificate or if there was recorded evidence from investigations such as ultrasound venography ventilation perfusion...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report gives the number randomized/analyzed by arm (2834 vs 2865) and specific event counts with no mention of missing outcome data or differential loss; reasons for missingness are not described but outcome data appear complete for the cohort, meeting the 'no missing outcome data' / balanced criteria for Low risk.
- Model support: Quote: "including 2834 patients allocated to pravastatin and 2865 to placebo... There were 28 cases of definite VTE in 2834 non-warfarinised patients in the pravastatin group and 20 cases in 2865 allocated to placebo" Comment: Randomized denominators by arm and event counts are reported; outcome data appear available and balanced with small numbers of events and no indication of differential/missing outcome data.
- Model support context: [{"source": "article", "quote": "including 2834 patients allocated to pravastatin and 2865 to placebo.", "relevance": "Provides randomized denominators by arm for the cohort used in VTE analysis."}, {"source": "article", "quote": "There were 28 cases of definite VTE in 2834 non-warfarinised patients in the pravastatin group and 20 cases in 2865 allocated to placebo.", "relevance": "Gives event counts by arm showing missing outcome data are not reported and events are balanced in numbers."}]
- GT support: The discontinued rates in each group were low. No participants lost to follow-up were reported.
- Evidence row: {}
- Source context preview: ## Subjects The design and outcome of PROSPER is described elsewhere[15-17]. Men and women aged 70-82 (n = 5804) with evidence of pre-existing vascular disease or at least one major risk factor for vascular disease were randomized to placebo or pravastatin (40 mg per day) treatment. Follow up was 3.2 years on average. For the present study the full medical records were retrieved for all suspected VTE in the PROSPER database and examined by three clinicians in a pre-planned post hoc analysis. Events were categorized as definite VTE if death from VTE was confirmed on the death certificate or if there was recorded evidence from investigations such as ultrasound venography ventilation perfusion...


## 21543987 - Van der Ploeg 2010

- Mode: direct
- Review context: none (0 chars)
- Article chars: 22909
- Extraction context chars: n/a
- Total seconds: 22.55
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
- Model rationale: The report explicitly states a minimization algorithm was used to allocate participants. Minimization is listed in the criteria as equivalent to a random method, so sequence generation is judged low risk.
- Model support: Quote: "Ninety patients were randomized 2:1 to the treatment arm using a minimization algorithm in an effort to balance the groups for disease severity (29)." Comment: Minimization is considered an adequate method with a random component and therefore indicates low risk for sequence generation.
- Model support context: [{"source": "article", "quote": "Ninety patients were randomized 2:1 to the treatment arm using a minimization algorithm", "relevance": "States the sequence generation method was minimization, which is acceptable as a random-equivalent method."}, {"source": "article", "quote": "Groups were stratified according to baseline six minute walk test... and baseline upright forced vital capacity...", "relevance": "Shows minimization was used to balance important baseline prognostic factors, supporting proper sequence generation."}]
- GT support: Quote: "Patients were randomized by study personnel entering baseline information into an Interactive Voice Response System. The Interactive Voice Response System was linked to a centralized computer that randomly assigned treatment via the minimization algorithm as implemented by proprietary and validated software developed by Covance, a contract research organization."
- Evidence row: {}
- Source context preview: ## Patient Population and Randomization Ninety patients were randomized 2:1 to the treatment arm using a minimization algorithm in an effort to balance the groups for disease severity (29). Groups were stratified according to baseline six minute walk test with a threshold of 300 meters and baseline upright forced vital capacity with a threshold of 55% of the predicted value. --- ## Study Design This study was a post-hoc analysis of cardiovascular parameters in a double-blind, multi-center, randomized controlled trial evaluating the efficacy and safety of acid alpha-glucosidase enzyme replacement therapy versus placebo in patients with late onset Pompe disease. The primary efficacy endpoints...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The article reports a minimization algorithm for randomization but gives no details on the process used to conceal allocations (for example central allocation, opaque sealed envelopes, or other safeguards). Because the concealment method is not described, risk of selection bias cannot be judged and is Unclear.
- Model support: Quote: "Ninety patients were randomized 2:1 to the treatment arm using a minimization algorithm in an effort to balance the groups for disease severity (29)." Comment: The report states minimization/randomization method but gives no information on how allocations were concealed from enrolling investigators (central randomization, sealed envelopes, or other).
- Model support context: [{"source": "article", "quote": "Ninety patients were randomized 2:1 to the treatment arm using a minimization algorithm in an effort to balance the groups for disease severity (29).", "relevance": "Describes randomization method (minimization) but does not describe the allocation concealment procedure."}, {"source": "article", "quote": "Patients ≥ 8 years of age...108 patients screened, 90 were randomized: 60 to the treatment arm and 30 to the control arm.", "relevance": "Shows numbers randomized but provides no details on who enrolled participants or how assignments were kept concealed prior to allocation."}]
- GT support: Quote: "Patients were randomized by study personnel entering baseline information into an Interactive Voice Response System. The Interactive Voice Response System was linked to a centralized computer that randomly assigned treatment via the minimization algorithm as implemented by proprietary and validated software developed by Covance, a contract research organization. The Investigators, other study site personnel, the patients, and representatives of Genzyme Corporation, with the exception of Genzyme Clinical Pharmacy Research Services, remained blinded to treatment assignment for the duration of the study. Every effort was made to maintain the integrity of the blind".
- Evidence row: {}
- Source context preview: ## Study Interventions and Data Collection Echocardiographic evaluation of left ventricular size and function was performed at baseline, 52 and 78 weeks. All echocardiograms were interpreted at the central cardiology core lab by a cardiologist blinded to treatment allocation. Left ventricular ejection fraction was calculated from two dimensional images using the modified Simpson’s rule in all patients. Abnormal ejection fraction was defined as < 55% (31). Left ventricular mass was evaluated using two-dimensional (2D) echocardiography and the truncated ellipsoid method (31). If the two-dimensional image quality was not sufficient, M-mode assessment was performed and left ventricular mass was...

#### Blinding of participants and personnel: All outcomes

- Prediction: Low risk
- Ground truth: Unclear risk
- Match: False
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The report explicitly describes the trial as double-blind and used volume-matched placebo infusions; key outcomes (ECG and echocardiography) were objectively measured, so lack of unblinding is unlikely to have influenced these outcomes.
- Model support: Quote: "This study was a post-hoc analysis of cardiovascular parameters in a double-blind, multi-center, randomized controlled trial..." Comment: The trial is described as double-blind and infusions were volume matched placebo, indicating participants and personnel were blinded and outcomes (ECG, echocardiography) are objective.
- Model support context: [{"source": "article", "quote": "double-blind, multi-center, randomized controlled trial", "relevance": "States that the trial was double-blind, bearing directly on participant/personnel blinding."}, {"source": "article", "quote": "the control group received a volume matched placebo infusion", "relevance": "Volume-matched placebo supports credible masking of participants and infusion personnel."}]
- GT support: Quote: "The Investigators, other study site personnel, the patients, and representatives of Genzyme Corporation, with the exception of Genzyme Clinical Pharmacy Research Services, remained blinded to treatment assignment for the duration of the study. Every effort was made to maintain the integrity of the blind." Comment: method not described.
- Evidence row: {}
- Source context preview: ## Study Design This study was a post-hoc analysis of cardiovascular parameters in a double-blind, multi-center, randomized controlled trial evaluating the efficacy and safety of acid alpha-glucosidase enzyme replacement therapy versus placebo in patients with late onset Pompe disease. The primary efficacy endpoints of the original trial consisted of the six minute walk test and the percent-predicted forced vital capacity in the upright position (ClinicalTrial.Gov identifier #NCT00158600; Protocol No. AGLU02704). Results of the primary analysis have been recently published (28). The present analysis focuses on evaluation of cardiovascular endpoints. This study was approved by the...

#### Blinding of outcome assessment: All outcomes

- Prediction: Low risk
- Ground truth: Unclear risk
- Match: False
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: For the review-relevant outcomes of echocardiography and ECG (objective clinician-interpreted measures), assessors were explicitly blinded and centrally blinded interpretation makes it unlikely that measurement was influenced by allocation, supporting Low risk.
- Model support: Quote: "All echocardiograms were interpreted at the central cardiology core lab by a cardiologist blinded to treatment allocation." Comment: Central blinded assessment of ECG and echocardiography means outcome measurement was unlikely to be influenced by knowledge of allocation.
- Model support context: [{"source": "article", "quote": "All echocardiograms were interpreted at the central cardiology core lab by a cardiologist blinded to treatment allocation.", "relevance": "States that echocardiographic outcomes were assessed centrally by a blinded cardiologist, reducing detection bias for imaging outcomes."}, {"source": "article", "quote": "All ECG's were interpreted at the central cardiology core lab by a cardiologist blinded to treatment arm.", "relevance": "States that ECG outcomes were centrally interpreted by a blinded cardiologist, indicating assessor blinding for electrophysiologic outcomes."}]
- GT support: Quote: "The Investigators, other study site personnel, the patients, and representatives of Genzyme Corporation, with the exception of Genzyme Clinical Pharmacy Research Services, remained blinded to treatment assignment for the duration of the study." Comment: method not described.
- Evidence row: {}
- Source context preview: ## Study Interventions and Data Collection Echocardiographic evaluation of left ventricular size and function was performed at baseline, 52 and 78 weeks. All echocardiograms were interpreted at the central cardiology core lab by a cardiologist blinded to treatment allocation. Left ventricular ejection fraction was calculated from two dimensional images using the modified Simpson’s rule in all patients. Abnormal ejection fraction was defined as < 55% (31). Left ventricular mass was evaluated using two-dimensional (2D) echocardiography and the truncated ellipsoid method (31). If the two-dimensional image quality was not sufficient, M-mode assessment was performed and left ventricular mass was...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: Attrition was low (5/60 and 4/30), reasons were reported and mostly unrelated to cardiovascular outcomes, and missingness was balanced across arms, meeting criteria for Low risk.
- Model support: Quote: "Five (8%) patients in the enzyme replacement therapy group and four (14%) patients in the placebo group did not complete the study." Comment: Missing outcome data were relatively small, balanced in numbers across groups with disclosed reasons (hypersensitivity, death, switch to commercial therapy, missed appointments) and unrelated to cardiovascular outcomes.
- Model support context: [{"source": "article", "quote": "Of 108 patients screened, 90 were randomized: 60 to the treatment arm and 30 to the control arm.", "relevance": "Provides randomized sample size and allocation ratio to contextualize attrition counts."}, {"source": "article", "quote": "Five (8%) patients in the enzyme replacement therapy group and four (14%) patients in the placebo group did not complete the study. Reasons... hypersensitivity (2), death unrelated to treatment (1), switch to commercial therapy (2);...", "relevance": "Gives missing counts by arm, percentages, and specific reasons showing balance and reasons unlikely related to cardiovascular outcomes."}]
- GT support: Comment: intention-to-treat analysis.
- Evidence row: {}
- Source context preview: ## Efficacy of Enzyme Replacement Therapy Table 3 displays ECG and echocardiographic data at baseline and 78 weeks in the treatment and placebo arms for those who completed the study. Of patients with baseline ECG data, 89% had follow-up ECG data. Of patients with baseline echocardiographic data, 80% had follow up echocardiographic data. No significant changes in ECG or echocardiographic parameters were seen in association with enzyme replacement therapy compared with placebo. --- ## Patient Characteristics Of 108 patients screened, 90 were randomized: 60 to the treatment arm and 30 to the control arm. We excluded three patients < 17 years of age from the analysis as the ECG and...


## 21680092 - Turner 2011

- Mode: direct
- Review context: none (0 chars)
- Article chars: 53160
- Extraction context chars: n/a
- Total seconds: 27.07
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
- Model rationale: The report explicitly states a randomization list was generated using the S-PLUS 'sample' function and random block sizes were used, which constitutes a random component per Low risk criteria.
- Model support: Quote: "The randomization list was prepared using the 'sample' function of the S-PLUS® statistical software... Block sizes were equal to 3 or 6, and were chosen randomly... Treatment assignments were recorded on cards numbered consecutively within each stratum, and a study assistant not involved in the screening and randomization put the randomization assignments in sealed envelopes sequentially numbered by stratum." Comment: Computer-based random number generation with random block sizes and sealed, sequential envelopes indicates an adequately random sequence generation.
- Model support context: [{"source": "article", "quote": "The randomization list was prepared using the 'sample' function of the S-PLUS statistical software.", "relevance": "Describes a computer random number-based method for sequence generation (meets Low risk criteria)."}, {"source": "article", "quote": "Block sizes were equal to 3 or 6, and were chosen randomly with 2/3 and 1/3 probability.", "relevance": "Specifies use of random block sizes, supporting that sequence had a random component."}]
- GT support: Stratified block randomisation undertaken by study assistant not involved in screening using a computer programme
- Evidence row: {}
- Source context preview: ## 2.4. Randomization Randomization to the three treatment groups was stratified by participant’s baseline chronic pain grade and recruitment source (U.W. Orofacial Pain Clinic new patient, U.W. Orofacial Pain Clinic return patient, and non-U.W. sources), and with blocking to ensure that the groups would be (nearly) balanced across the study period and within each stratum. Block sizes were equal to 3 or 6, and were chosen randomly with 2/3 and 1/3 probability, respectively. In addition, the number of women randomized to the COCT group was increased by 25% to allow for some disqualification at the ARNP visit. The randomization list was prepared using the “sample” function of the S-PLUS®...

#### Allocation concealment

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The sequence was generated by software and assignments were placed in sealed, sequentially numbered envelopes by a study assistant not involved in screening/randomization, and kept concealed until opening at randomization, meeting criteria for adequate allocation concealment.
- Model support: Quote: "The randomization list was prepared using the 'sample' function of the S-PLUS(R) statistical software... Treatment assignments were recorded on cards numbered consecutively within each stratum, and a study assistant not involved in the screening and randomization put the randomization assignments in sealed envelopes sequentially numbered by stratum. Randomization assignments were concealed to all study personnel with study participant contact until envelopes were opened by research staff at the time of randomization." Comment: Allocation was concealed using sequentially numbered, sealed envelopes prepared and held by staff not involved in enrollment, preventing recruiters from foreseeing assignments.
- Model support context: [{"source": "article", "quote": "The randomization list was prepared using the 'sample' function of the S-PLUS statistical software... Treatment assignments were recorded on cards numbered consecutively within each stratum", "relevance": "Shows a computer-generated random list and assignment cards were produced from it."}, {"source": "article", "quote": "a study assistant not involved in the screening and randomization put the randomization assignments in sealed envelopes sequentially numbered by stratum. Randomization assignments were concealed to all study personnel... until envelopes...", "relevance": "Describes sealed, sequentially numbered envelopes held/handled by staff not enrolling participants, indicating adequate concealment."}]
- GT support: Sequence put into opaque, sequentially numbered envelopes by an assistant not otherwise involved in the study
- Evidence row: {}
- Source context preview: ## 2.4. Randomization Randomization to the three treatment groups was stratified by participant’s baseline chronic pain grade and recruitment source (U.W. Orofacial Pain Clinic new patient, U.W. Orofacial Pain Clinic return patient, and non-U.W. sources), and with blocking to ensure that the groups would be (nearly) balanced across the study period and within each stratum. Block sizes were equal to 3 or 6, and were chosen randomly with 2/3 and 1/3 probability, respectively. In addition, the number of women randomized to the COCT group was increased by 25% to allow for some disqualification at the ARNP visit. The randomization list was prepared using the “sample” function of the S-PLUS®...

#### Blinding of participants and personnel: All outcomes

- Prediction: High risk
- Ground truth: High risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report indicates participants were informed about which broad interventions existed and allocation was revealed at randomization; there is no explicit statement that participants or caregivers were blinded, and the interventions are dissimilar (medication vs behavioral therapies). Necessary detail on whether participants or personnel were masked during treatment and whether lack of blinding could influence subjective outcomes (pain, disability) is missing, so risk is unclear. Calibration: visibly different active interventions with subjective patient-reported outcomes make participant/personnel blinding unlikely and material.
- Model support: Quote: "Potential participants were told that the study involved randomization to COCT or to one of two different versions of SMT. At no time before or during study participation were participants informed that one and only one version focused on menstrual cycle-related changes." Comment: Participants were aware of being randomized and of broad treatment types, but no clear statement that participants or treating personnel were blinded; interventions (COCT vs behavioral SMT/TSMT) are visibly different, so blinding is unlikely but not explicitly reported. Comment: Calibration: visibly different active interventions with subjective patient-reported outcomes make participant/personnel blinding unlikely and material.
- Model support context: [{"source": "article", "quote": "## 2.5. Interventions At their clinic visit with the study ARNP, women who were randomized to, and met all eligibility criteria for, COCT received instructions on use of the medication, potential breakthrough bleeding problems, backup...", "relevance": "Calibration: visibly different active interventions with subjective patient-reported outcomes make participant/personnel blinding unlikely and material."}, {"source": "article", "quote": "Potential participants were told that the study involved randomization to COCT or to one of two different versions of SMT.", "relevance": "Shows participants knew there were different treatment types but not whether they were blinded to allocation."}]
- GT support: Not possible to blind participants to the intervention received in this type of trial. Study assistant was blinded. All study personnel remained blind to assignment until the point of randomisation.
- Evidence row: {}
- Source context preview: ## 2.5. Interventions At their clinic visit with the study ARNP, women who were randomized to, and met all eligibility criteria for, COCT received instructions on use of the medication, potential breakthrough bleeding problems, backup birth control methods in the event of missed doses (for participants who were also using the study medication for birth control), and contact information for any medication-related questions. A 4-month supply of the medication (20 mcg ethinyl estradiol and 100 mcg levonorgestrel) was dispensed. At a second visit three months later, they received additional medication, for a total of six months on the medication. Women returned for a final visit just prior to...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: High risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The review-relevant outcomes (pain intensity and activity interference) were self-reported 0–10 scales (GCPS) completed by participants; these standardized numeric self-reports are unlikely to be biased by outcome assessor knowledge, supporting Low risk. (Assessor role: participant self-report.) Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support: Quote: "Randomization assignments were concealed to all study personnel with study participant contact until envelopes were opened by research staff at the time of randomization." Comment: Outcome measurement (pain intensity, activity interference) used standardized self-report scales (GCPS, 0-10 ratings) that are objective patient-reported measures unlikely to be influenced by assessor knowledge; outcome assessors not required for device/lab measures. Comment: Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support context: [{"source": "article", "quote": "focused on menstrual cycle-related changes. All potential study participants completed a comprehensive clinical history questionnaire and had a comprehensive clinical dental examination to ensure there were no conditions that would...", "relevance": "Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported."}, {"source": "article", "quote": "Participants completed the study measures at... baseline, and at 6 and 12 months after randomization.", "relevance": "Shows timing of outcome collection (self-report questionnaires at scheduled visits)."}]
- GT support: Not possible to blind for self‐report outcome questionnaires. Blinding of outcome assessors is not explicitly reported.
- Evidence row: {}
- Source context preview: ## 2.7. Statistical analysis We did not make a statistical adjustment (e.g., Bonferroni method, which inflates type II error and reduces statistical power) for multiple testing. We expected moderate correlations of the outcome and process measures; patterns of significant differences among the study groups on multiple related measures would support an interpretation that the treatment had an effect on the constructs assessed by those measures. We included multiple measures within the outcome and process variable domains because it would be of interest to patients, clinicians, and researchers to know whether the interventions had a different impact on, for example, activity interference...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report provides randomized (n=191), withdrawals with reasons (20 withdrawn, mostly COCT medical contraindications), follow-up completion rates by group (~86% with similar rates across groups), and conducted multiple imputation sensitivity analyses with unchanged conclusions, meeting criteria that reasons and handling make bias unlikely.
- Model support: Quote: "Among the 191 women who were randomized, 20 were withdrawn from the study (15 of whom were randomized to the COCT group but then withdrawn due to medical contra-indications). In each of the three groups, 86% of participants completed at least one follow-up assessment." Comment: Attrition was described, reasons given (medical contraindications, refusal, side effects), analysis was intent-to-treat for all randomized with follow-up data, and multiple imputation/sensitivity analyses were performed showing similar results, indicating missing data unlikely to bias outcomes materially.
- Model support context: [{"source": "article", "quote": "Among the 191 women who were randomized, 20 were withdrawn from the study (15 of whom were randomized to the COCT group but then withdrawn due to medical contra-indications).", "relevance": "Reports numbers randomized and reasons for many withdrawals, showing documented causes for missingness."}, {"source": "article", "quote": "The primary analyses... were intent-to-treat analyses, which included all randomized participants for whom follow-up data... were available. In sensitivity analyses using multiple imputation... the primary conclusions remained unchanged.", "relevance": "Describes handling of missing data (ITT with available follow-up, plus multiple imputation) and that results were robust to imputation."}]
- GT support: Missing data clearly described and sensitivity analysis carried out regarding imputation and intention‐to‐treat strategy.
- Evidence row: {}
- Source context preview: ## 2.7. Statistical analysis In addition, we performed multiple imputation analyses for the outcomes of characteristic pain intensity and activity inference to assess the effect of missing data due to participants who provided no follow-up data. Baseline and follow-up values of characteristic pain intensity or activity inference, as well as a variable indicating assigned treatment, were used in the imputation of the missing values, which used a Markov Chain Monte Carlo (MCMC) method assuming an arbitrary missing data pattern and multivariate normality and a single chain to create five imputations using 200 burn-in iterations before the first imputation and 100 iterations between...


## 21723049 - Brewer 2011

- Mode: direct
- Review context: none (0 chars)
- Article chars: 30867
- Extraction context chars: n/a
- Total seconds: 26.0
- Retry: no

### Methodology Extraction

- No separate extraction step for this mode.

### Domain Judgements

| Domain | Pred | GT | Match | GT Observability | Error Type |
|---|---|---|---|---|---|
| Random sequence generation | Low risk | Low risk | yes | no_support_phrase_match |  |
| Allocation concealment | Unclear risk | Unclear risk | yes | unknown |  |
| Blinding of participants and personnel: All outcomes | High risk | Unclear risk | no | article_absence_or_unclear | over-inferred_from_sparse_reporting |
| Blinding of outcome assessment: All outcomes | Unclear risk | Unclear risk | yes | unknown |  |
| Incomplete outcome data: All outcomes | Low risk | Unclear risk | no | no_support_phrase_match | gt_support_not_found_in_article_text |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report explicitly states a 'computer-generated urn randomization program' was used to assign participants, which is a random sequence generation method (computer random number/urn), meeting LOW RISK criteria.
- Model support: Quote: "A computer-generated urn randomization program assigned participants to MT or FFS based on age (> vs. ≤ 40 years old), sex, race (white vs. non-white), and cigarettes smoked/day (> vs. ≤ 20)." Comment: The sequence was generated by a computer-based urn randomization program, which describes a random component.
- Model support context: [{"source": "article", "quote": "A computer-generated urn randomization program assigned participants to MT or FFS based on age..., sex, race..., and cigarettes smoked/day...", "relevance": "Describes a computer-generated urn randomization method, indicating a random sequence generation process."}, {"source": "article", "quote": "Of the 103 eligible individuals, 88 were randomized (see CONSORT diagram, Fig. 1).", "relevance": "Confirms participants were randomized and that the computer-generated program was used for assignment."}]
- GT support: A computer-generated urn randomisation program assigned participants to MT or FFS based on age, sex, race, and cigarettes smoked/day.
- Evidence row: {}
- Source context preview: ## 2.3. Interventions A computer-generated urn randomization program assigned participants to MT or FFS based on age (> vs. ≤ 40 years old), sex, race (white vs. non-white), and cigarettes smoked/day (> vs. ≤ 20). All participants received twice weekly group sessions (eight total) that were manualized and delivered by instructors experienced in MT (a single therapist with >13 years of training in MT) or certified in FFS respectively (2 therapists with masters (+) level of training in drug counseling/health psychology). FFS was chosen as an active ‘standard treatment’ comparison condition for several reasons: 1) It has demonstrated efficacy (Lando et al., 1990), 2) is manualized and...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: The trial reports a computer-generated urn randomization (sequence generation) but does not describe any mechanism to prevent recruiters from foreseeing assignments (central allocation, sealed opaque envelopes, or similar). Because concealment procedures are not reported, risk of selection bias is unclear.
- Model support: Quote: "A computer-generated urn randomization program assigned participants to MT or FFS based on age ( > vs. ≤ 40 years old), sex, race (white vs. non-white), and cigarettes smoked/day ( > vs. ≤ 20)." Comment: Sequence generation is described (computer-generated urn) but the report gives no information on how allocations were concealed from recruiters/enrollers (central allocation, sealed envelopes, or other safeguards).
- Model support context: [{"source": "article", "quote": "A computer-generated urn randomization program assigned participants to MT or FFS based on age, sex, race, and cigarettes smoked/day.", "relevance": "Describes the randomization method but does not state how allocation was concealed from those enrolling participants."}, {"source": "article", "quote": "Of the 103 eligible individuals, 88 were randomized (see CONSORT diagram, Fig. 1).", "relevance": "Reports numbers randomized but provides no details on the allocation concealment process (e.g., central randomization or opaque sealed envelopes)."}]
- GT support: No information
- Evidence row: {}
- Source context preview: ## 4.1. Strengths and Limitations Strengths of this pilot trial include the random assignment from a diverse community sample, the presence of an active comparison group, and the use of intent-to-treat analysis of our sample using validated outcome measures. This study has several limitations as well. This study was performed at a single site, treatment was provided by only 1–2 therapists per condition, and treatment integrity was not formally assessed. Thus treatment effects may not be generalized beyond the specific therapists in this trial (Crits-Christoph and Mintz, 1991). Also, it was of moderate size, and used an active comparison group, which typically limits the ability to detect...

#### Blinding of participants and personnel: All outcomes

- Prediction: High risk
- Ground truth: Unclear risk
- Match: False
- GT observability: article_absence_or_unclear (article observable: True)
- GT support phrase hits: 
- Model rationale: The trial compared two clearly different behavioral therapies delivered openly by therapists; no participant or personnel blinding or placebo/sham is reported. Outcomes include self-reported smoking and other subjective measures likely influenced by participants' and therapists' knowledge of allocation, meeting criteria for High risk.
- Model support: Quote: "All participants received twice weekly group sessions... delivered by instructors experienced in MT (a single therapist...) or certified in FFS respectively (2 therapists...)" Comment: Participants and therapists clearly received different active behavioral interventions with no masking or sham described, and outcomes (self-reported smoking, coping, mental distress, quality of life) could be influenced by knowledge of treatment.
- Model support context: [{"source": "article", "quote": "All participants received twice weekly group sessions... delivered by instructors experienced in MT (a single therapist...) or certified in FFS respectively (2 therapists...).", "relevance": "Shows active, different behavioral interventions delivered by identifiable therapists, implying participants/personnel were not blinded."}, {"source": "article", "quote": "Self-reported smoking was assessed at in-person weekly visits by a research assistant who was not involved in treatment delivery via the Timeline Follow Back method (TLFB).", "relevance": "Primary outcomes include self-reported smoking (participant-reported); participant knowledge of treatment could influence these subjective outcomes."}]
- GT support: No information, but blinding unlikely. We have left as unclear risk as it is difficult, if not impossible, to blind participants and personnel to lifestyle interventions.
- Evidence row: {}
- Source context preview: ## 2.3. Interventions A computer-generated urn randomization program assigned participants to MT or FFS based on age (> vs. ≤ 40 years old), sex, race (white vs. non-white), and cigarettes smoked/day (> vs. ≤ 20). All participants received twice weekly group sessions (eight total) that were manualized and delivered by instructors experienced in MT (a single therapist with >13 years of training in MT) or certified in FFS respectively (2 therapists with masters (+) level of training in drug counseling/health psychology). FFS was chosen as an active ‘standard treatment’ comparison condition for several reasons: 1) It has demonstrated efficacy (Lando et al., 1990), 2) is manualized and...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: The review-relevant outcome (smoking abstinence/BP etc.; here smoking outcomes) included an objective exhaled CO measurement assessed at visits; objective device/lab outcomes are unlikely to be influenced by assessor knowledge, so detection bias is low despite self-report components. Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support: Quote: "Self-reported smoking was assessed at in-person weekly visits by a research assistant who was not involved in treatment delivery via the Timeline Follow Back method (TLFB) ... Self-reported abstinence was assessed using TLFB and verified by an exhaled carbon monoxide (CO) measurement of ≤ 10 parts per million" Comment: Outcome assessment combined objective CO measurement (biochemical verification) with TLFB; CO is an objective lab/device measure unlikely to be influenced by assessor knowledge. Comment: Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support context: [{"source": "article", "quote": "## 2.4. Smoking Status Self-reported smoking was assessed at in-person weekly visits by a research assistant who was not involved in treatment delivery via the Timeline Follow Back method (TLFB) (Sobell and Sobell, 1992). Self-reported...", "relevance": "Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported."}, {"source": "article", "quote": "Self-reported smoking was assessed at in-person weekly visits by a research assistant who was not involved in treatment delivery via the Timeline Follow Back method (TLFB).", "relevance": "Identifies assessor as a research assistant not involved in treatment, relevant to potential blinding of assessment for self-report."}]
- GT support: No information.
- Evidence row: {}
- Source context preview: ## 2.4. Smoking Status Self-reported smoking was assessed at in-person weekly visits by a research assistant who was not involved in treatment delivery via the Timeline Follow Back method (TLFB) (Sobell and Sobell, 1992). Self-reported abstinence was assessed using TLFB and verified by an exhaled carbon monoxide (CO) measurement of ≤ 10 parts per million at each of the twice-weekly treatment and at follow-up visits. Participants who dropped out of treatment were contacted to provide in-person assessments at follow-up time points (see CONSORT diagram) (Hollis and Campbell, 1999). All participants were financially compensated for assessment visits (10 USD per assessment visit during treatment...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: Unclear risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The trial reports an ITT mixed-effects analysis, documents only one randomized participant excluded for an administrative/legal reason, and gives balanced follow-up completion rates (low attrition) by arm; reasons for missing data are reported and unlikely to be related to outcome, meeting Low risk criteria.
- Model support: Quote: "Longitudinal data were analyzed using intent-to-treat mixed effect regression models on the full sample of randomized subjects (minus one individual who was incarcerated after treatment and whose data were not allowed to be analyzed per Veteran’s Administration regulations)" Comment: ITT mixed-effects analyses used with casewise deletion for unavailable data; follow-up completion rates are reported and balanced across arms.
- Model support context: [{"source": "article", "quote": "intent-to-treat mixed effect regression models on the full sample of randomized subjects (minus one individual who was incarcerated...)", "relevance": "Indicates ITT analytic approach and explicit single excluded participant with reason."}, {"source": "article", "quote": "The six, 12, and 17-week follow-up completion rates were 27 (82%) and 33 (87%), 29 (88%) and 32 (84%), and 29 (88%) and 33 (87%) for MT and FFS respectively.", "relevance": "Provides by-arm follow-up completion rates showing low and balanced attrition across groups."}]
- GT support: Only 1 participant was excluded from ITT analysis because of incarceration. This participant was in the FFS group. In the FFS group, 8 participants were randomised but did not complete baseline assessment or start treatment and 32 completed treatment. In the MT group, 8 participants were randomised but did not complete baseline assessment or start treatment and 29 completed treatment. ITT analysis used for some but not all analyses.
- Evidence row: {}
- Source context preview: ## 3.2. Effects of Mindfulness Training on smoking Random effects regression analyses on the full intention to treat sample indicated participants in both groups reduced cigarette use from baseline through the 17-week follow-up (effect for time, F=480.79, df=1,1115, p<.0001). The rate of change during active treatment was significantly greater than the rate of change during post treatment (effect for phase, active versus follow-up, F=579.00, df=1,1115, p<.0001). During active treatment, individuals receiving MT demonstrated a greater reduction in cigarette use than those receiving FFS, and maintained these treatment gains during the follow-up period (treatment group × time, F=7.01,...


## 21775755 - Ziegler 2011

- Mode: direct
- Review context: none (0 chars)
- Article chars: 24371
- Extraction context chars: n/a
- Total seconds: 24.73
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
| Incomplete outcome data: All outcomes | Low risk | High risk | no | article_text_match | attrition_balance_or_missing_data_handling |

### Audit Details

#### Random sequence generation

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report describes a randomization list generated by a Biostatistics Department and balanced (blocked) random allocation, which meets the Low risk criterion of an explicit random component (computer/random list/minimization).
- Model support: Quote: "Patients were assigned to the two treatment groups according to a randomization list generated by the Biostatistics Department of MEDA Pharma. The random allocation was balanced using an undisclosed block size of six." Comment: Explicit randomization list generated by a Biostatistics Department and use of blocked randomization indicates a random component in sequence generation.
- Model support context: [{"source": "article", "quote": "Patients were assigned to the two treatment groups according to a randomization list generated by the Biostatistics Department of MEDA Pharma.", "relevance": "States the sequence was produced by a biostatistics department as a randomization list, indicating a random component."}, {"source": "article", "quote": "The random allocation was balanced using an undisclosed block size of six.", "relevance": "Specifies blocked randomization was used, supporting a randomized generation method."}]
- GT support: Quote: "a randomization list was generated by the biostatistics department of the manufacturer of the study drug ..."
- Evidence row: {}
- Source context preview: ## Randomization Screened patients were assigned a unique five-digit number. Randomized patients were additionally assigned a four-digit randomization number at baseline. Patients were assigned to the two treatment groups according to a randomization list generated by the Biostatistics Department of MEDA Pharma. The random allocation was balanced using an undisclosed block size of six. The investigators and the monitor received sealed envelopes to enable decoding the individual blinded treatment in case of emergency. --- ## RESEARCH DESIGN AND METHODS The Neurological Assessment of Thioctic Acid in Diabetic Neuropathy (NATHAN) 1 trial was a multicenter (36 centers in the U.S., Canada, and...

#### Allocation concealment

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: the random allocation was balanced using an undisclosed block size of six
- Model rationale: The report states a randomization list was generated and sealed envelopes existed for emergency decoding, but it lacks details on how allocation was delivered to sites or safeguards (central allocation, sequentially numbered opaque sealed envelopes, or other measures). Therefore there is insufficient information to judge allocation concealment.
- Model support: Quote: "Patients were assigned to the two treatment groups according to a randomization list generated by the Biostatistics Department of MEDA Pharma. The random allocation was balanced using an undisclosed block size of six. The investigators and the monitor received sealed envelopes to enable decoding the individual blinded treatment in case of emergency." Comment: Allocation generation is described but the method used to implement concealment (how the randomization list was accessed/used, who held it, and whether envelopes were sequentially numbered/opaque/sealed and held independently) is not reported, so concealment cannot be judged.
- Model support context: [{"source": "article", "quote": "Patients were assigned to the two treatment groups according to a randomization list generated by the Biostatistics Department of MEDA Pharma.", "relevance": "Describes who generated the allocation list but not how assignments were concealed from recruiters."}, {"source": "article", "quote": "The investigators and the monitor received sealed envelopes to enable decoding the individual blinded treatment in case of emergency.", "relevance": "Mentions sealed envelopes for emergency decoding but gives no details proving sequentially numbered, opaque, sealed envelopes or independent custody for..."}]
- GT support: Quote: "a randomization list was generated by the biostatistics department of the manufacturer of the study drug, at distance of the centers the study took place"; "the random allocation was balanced using an undisclosed block size of six."
- Evidence row: {}
- Source context preview: ## Randomization Screened patients were assigned a unique five-digit number. Randomized patients were additionally assigned a four-digit randomization number at baseline. Patients were assigned to the two treatment groups according to a randomization list generated by the Biostatistics Department of MEDA Pharma. The random allocation was balanced using an undisclosed block size of six. The investigators and the monitor received sealed envelopes to enable decoding the individual blinded treatment in case of emergency. --- ## RESEARCH DESIGN AND METHODS The Neurological Assessment of Thioctic Acid in Diabetic Neuropathy (NATHAN) 1 trial was a multicenter (36 centers in the U.S., Canada, and...

#### Blinding of participants and personnel: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: matching placebo tablets with increased amounts of cellulose and lactose that were identical in appearance | matching placebo tablets with increased amounts
- Model rationale: The report explicitly describes a double-blind, placebo-controlled design with matching identical-appearing tablets and emergency sealed decoding only, which supports that participants and key personnel were blinded and that blinding was unlikely to be broken; outcomes are clinical and some subjective but blinding was implemented.
- Model support: Quote: "randomized, double-blind, placebo-controlled... matching placebo tablets with increased amounts of cellulose and lactose that were identical in appearance" Comment: The trial explicitly states double-blind design with identical placebo, making it unlikely that participants or personnel knew allocation.
- Model support context: [{"source": "article", "quote": "randomized, double-blind, placebo-controlled... matching placebo tablets ... identical in appearance", "relevance": "Direct statement that participants and study personnel were blinded using identical placebo tablets."}, {"source": "article", "quote": "The investigators and the monitor received sealed envelopes to enable decoding the individual blinded treatment in case of emergency.", "relevance": "Indicates blinding was maintained with emergency unblinding procedures, supporting that routine allocation was concealed from personnel."}]
- GT support: Quote: "... matching placebo tablets with increased amounts of cellulose and lactose that were identical in appearance." Comment: trial described as double-blind.
- Evidence row: {}
- Source context preview: ## RESEARCH DESIGN AND METHODS The Neurological Assessment of Thioctic Acid in Diabetic Neuropathy (NATHAN) 1 trial was a multicenter (36 centers in the U.S., Canada, and Europe [Supplementary Materials]), randomized, double-blind, placebo-controlled, two-arm, 1:1 allocation ratio, parallel-group clinical trial using film-coated tablets containing 600 mg ALA (Thioctacid HR; MEDA Pharma, Bad Homburg, Germany) that were administered once daily or matching placebo tablets with increased amounts of cellulose and lactose that were identical in appearance in diabetic patients with mild-to-moderate DSPN (18). The trial consisted of a 2-week screening phase, 6-week placebo run-in phase, 4-year...

#### Blinding of outcome assessment: All outcomes

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The report specifies a double-blind design and that clinical and instrument-based outcomes were assessed by trained/certified personnel with central Reading and QA, making it unlikely that lack of assessor blinding influenced these primarily objective or centrally reviewed measures.
- Model support: Quote: "randomized, double-blind, placebo-controlled" Comment: Outcome assessments (NIS, NIS-LL, nerve conduction, QST, autonomic tests) were performed by trained, certified physicians and trained personnel with results "interactively evaluated by the Reading and Quality Assurance Centers", suggesting assessors were blinded and objective measurements were centrally reviewed.
- Model support context: [{"source": "article", "quote": "The NATHAN 1 trial was a ... randomized, double-blind, placebo-controlled ... trial", "relevance": "States trial was double-blind, supporting that outcome assessors were likely blinded."}, {"source": "article", "quote": "Experienced, trained, and certified physicians evaluated the NIS and NSC. The nerve conduction, quantitative sensory tests, and autonomic tests were performed by trained and certified personnel... All results were interactively evaluated...", "relevance": "Describes who measured outcomes (physicians, trained personnel) and that results underwent central reading/QA, reducing detection bias risk."}]
- GT support: Quote: "The investigators and the monitor received sealed envelopes to enable decoding the individual blinded treatment in case of emergency."
- Evidence row: {}
- Source context preview: ## Outcomes Secondary outcome measures included the NIS, NIS-LL, Neuropathy Symptoms and Change (NSC) score, TSS, cooling detection threshold, heat pain response slope (0.5–5.0), tibial nerve CMAP and MNCV, sural sensory nerve action potential latency, and sensory nerve conduction velocity (SNCV). In a response/progression analysis after 2 and 4 years, a clinically meaningful response was defined as a decrease in NIS or NIS-LL by ≥2 points, respectively, while clinically meaningful progression was defined as an increase in NIS or NIS-LL by ≥2 points, respectively (16,17). --- ## RESEARCH DESIGN AND METHODS Exclusion criteria were neuropathies other than DSPN; myopathy and other neurologic...

#### Incomplete outcome data: All outcomes

- Prediction: Low risk
- Ground truth: High risk
- Match: False
- GT observability: article_text_match (article observable: True)
- GT support phrase hits: mean of weeks 191 and 192 or last available value after randomization
- Model rationale: The report explicitly states good retention and provides small, balanced discontinuation counts (2 vs 1) with reasons, implying missing outcome data were minimal and unlikely to bias results, meeting Low risk criteria.
- Model support: Quote: "The clinical progression of DSPN in the placebo group within the setting of this randomized clinical trial with good retention of patients throughout a 4-year period was relatively slow." Comment: Trial reports "good retention of patients throughout a 4-year period" and gives numbers for AEs/SAEs and discontinuations (2 ALA, 1 placebo) suggesting low and balanced attrition.
- Model support context: [{"source": "article", "quote": "good retention of patients throughout a 4-year period", "relevance": "Direct statement indicating low overall attrition supporting low risk from amount of missing data."}, {"source": "article", "quote": "Two (0.9%) patients on ALA and one (0.7%) patient on placebo discontinued study treatment as a result of lack of tolerability", "relevance": "Reports discontinuations by arm and reason, showing very small and balanced numbers related to adverse events."}]
- GT support: More than 40% of participants discontinued intervention in both groups during the 4-year study. We do not know how many participants were lost before the outcomes at 2 years (our outcome of interest), and how many after the first 2 years. Most participants (454/460) were included in the ITT analysis, but the study authors did not report for how many they managed to measure the outcome, and for how many they used the last observation carried forward ("mean of weeks 191 and 192 or last available value after randomization"). Apparently, the proportion of dropouts and the causes of dropout were equally distributed among the 2 groups.
- Evidence row: {}
- Source context preview: ## Statistical analysis We used a conservative approach to suggest that treatment with ALA may prevent worsening of DSPN but not necessarily cause improvement (16). A clinically meaningful treatment difference of 2.0 nds for the changes from baseline for NIS-LL+7 tests and statistical error probabilities α = 0.05 and β = 0.1 were assumed. Based on a two-sided t test, the following scenarios for SDs and sample size per group (n) were considered: SD 3.57, n = 68; SD 4, n = 86; SD 5, n = 133; SD 6, n = 191; SD 7, n = 211. To account for a relatively high dropout rate expected in this long-term study, randomization of 250 patients per arm was proposed. Analysis of the intention-to-treat...


## 21933436 - Dorresteijn 2016

- Mode: direct
- Review context: none (0 chars)
- Article chars: 27677
- Extraction context chars: n/a
- Total seconds: 24.6
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
- Model rationale: The report explicitly states a computerised allocation process performed by an external agency, which constitutes a random component (computer random number generator) satisfying the Low risk criteria for sequence generation.
- Model support: Quote: "Computerised alternative allocation was used in the randomisation process, which was performed by an external agency." Comment: This describes a computer-based random component and use of an external agency to perform allocation, meeting Low risk criteria for random sequence generation.
- Model support context: [{"source": "article", "quote": "Participants were assigned... using stratified randomisation... Computerised alternative allocation was used in the randomisation process, which was performed by an external agency.", "relevance": "Describes a computerised random allocation process performed by an external agency, indicating a random sequence generation method."}]
- GT support: Randomisation conducted by an external agency blinded to participant characteristics.
- Evidence row: {}
- Source context preview: ## Randomisation Participants were assigned to the programme or the no-treatment control group directly after the baseline measurement using stratified randomisation. This randomisation was performed in blocks of two on the basis of one prognostic factor: the level of concern about falls (some, regular, often, and very often). Computerised alternative allocation was used in the randomisation process, which was performed by an external agency. --- ## Design The study concerns a two-group randomised controlled trial with a baseline measurement and follow-up measurements after 5 (directly after the programme) and 12 months (see Figure 1). The selection of potential participants was performed...

#### Allocation concealment

- Prediction: Low risk
- Ground truth: Low risk
- Match: True
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: Allocation was computerised and performed by an external agency after baseline measurement, which is consistent with central/remote allocation methods that prevent foreknowledge of assignments, meeting the Low risk criteria.
- Model support: Quote: "Computerised alternative allocation was used in the randomisation process, which was performed by an external agency." Comment: Randomisation was computerised and performed by an external agency, indicating allocation was generated and handled independently, preventing recruiters from foreseeing assignments.
- Model support context: [{"source": "article", "quote": "Computerised alternative allocation was used in the randomisation process, which was performed by an external agency.", "relevance": "Shows an independent external agency used a computerised allocation process, supporting concealment from enrolment staff."}, {"source": "article", "quote": "Participants were assigned ... directly after the baseline measurement using stratified randomisation... performed in blocks of two ... by an external agency.", "relevance": "Indicates assignment was handled externally after baseline, reducing the chance that recruiters could foresee allocations."}]
- GT support: Outcome assessors blinded to the allocation.
- Evidence row: {}
- Source context preview: ## Recruitment of participants Three communities, Maastricht, Sittard-Geleen, and Heerlen, situated in the southeast of The Netherlands have been selected for participation in the trial. The municipal registry offices selected 11,490 addresses of community-dwelling people of 70 years or over in their district, at random. To screen for eligibility, people received a short postal questionnaire with a freepost envelope, as well as information about the trial and an informed consent form. After a fortnight, reminder letters were sent. The questionnaire assessed socio-demographics and fall-related variables and inclusion and exclusion criteria. --- ## Randomisation Participants were assigned to...

#### Blinding of participants and personnel: All outcomes

- Prediction: Low risk
- Ground truth: High risk
- Match: False
- GT observability: unknown (article observable: None)
- GT support phrase hits: 
- Model rationale: Although participants and facilitators likely knew allocation (in-home programme vs no treatment) no evidence suggests this knowledge would materially bias the review outcomes because interviewers were blinded and key outcomes (falls via calendar, disability scales) were collected via structured instruments or objective records.
- Model support: Quote: "Data for the effect evaluation is gathered by means of telephone interviews which are conducted by trained interviewers, who are blinded for group allocation." Comment: Outcome data were collected by interviewers blinded to allocation, and many outcomes (falls via calendar, GARS disability) are objective/participant-recorded with blinded follow-up processes, so lack of participant/facilitator blinding is unlikely to have materially biased the measured outcomes.
- Model support context: [{"source": "article", "quote": "Data for the effect evaluation is gathered by means of telephone interviews which are conducted by trained interviewers, who are blinded for group allocation.", "relevance": "Shows outcome assessors/interviewers were blinded, reducing risk that personnel knowledge influenced outcome measurement."}, {"source": "article", "quote": "The number of falls is registered continuously during the course of the trial by a fall calendar.", "relevance": "Falls recorded prospectively by participants using calendars provide objective event data less likely to be biased by unblinded personnel."}]
- GT support: Blinding of participants not possible due to nature of intervention.
- Evidence row: {}
- Source context preview: ## Randomisation Participants were assigned to the programme or the no-treatment control group directly after the baseline measurement using stratified randomisation. This randomisation was performed in blocks of two on the basis of one prognostic factor: the level of concern about falls (some, regular, often, and very often). Computerised alternative allocation was used in the randomisation process, which was performed by an external agency. --- ## Design The study concerns a two-group randomised controlled trial with a baseline measurement and follow-up measurements after 5 (directly after the programme) and 12 months (see Figure 1). The selection of potential participants was performed...

#### Blinding of outcome assessment: All outcomes

- Prediction: Unclear risk
- Ground truth: Unclear risk
- Match: True
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The review-relevant outcomes (e.g. FES-I, HADS, falls) were collected by trained interviewers blinded to allocation (telephone interviews) and falls were captured by participant-completed calendars; thus blinding of outcome assessment was ensured and unlikely to be broken. Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support: Quote: "Data for the effect evaluation is gathered by means of telephone interviews which are conducted by trained interviewers, who are blinded for group allocation." Comment: Outcome assessment was performed by blinded interviewers, so detection bias is unlikely. Comment: Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported.
- Model support context: [{"source": "article", "quote": "ling people of 70 years or over in their district, at random. To screen for eligibility, people received a short postal questionnaire with a freepost envelope, as well as information about the trial and an informed consent form. After a...", "relevance": "Calibration: the outcome appears subjective or self-reported, but neither participant masking nor assessor masking is clearly reported."}, {"source": "article", "quote": "Data for the effect evaluation is gathered by means of telephone interviews which are conducted by trained interviewers, who are blinded for group allocation.", "relevance": "States that interviewers (assessors) were blinded, directly addressing blinding of outcome assessment."}]
- GT support: Assessors blinded, but outcomes were self-reported by participants who knew their group allocation.
- Evidence row: {}
- Source context preview: ## Outcomes ### Primary outcome measures --- ## Outcomes ### Secondary outcome measures --- ## Data collection Data for the effect evaluation is gathered by means of telephone interviews which are conducted by trained interviewers, who are blinded for group allocation. For the assessment of fall accidents, participants received a fall calendar after the baseline measurement. Every month, a sheet of the calendar has to be returned via a freepost envelope. People are reminded by telephone after one-and-half weeks if a sheet is not returned. --- ## Analysis Descriptive techniques will be used to describe the study groups. Baseline variables will be compared, to detect differences between the...

#### Incomplete outcome data: All outcomes

- Prediction: Unclear risk
- Ground truth: Low risk
- Match: False
- GT observability: no_support_phrase_match (article observable: False)
- GT support phrase hits: 
- Model rationale: The excerpts describe planned ITT analyses and attempts to contact participants, but do not report randomized/enrolled counts by arm, analyzed outcome numbers, percent missing, or reasons for loss; therefore there is insufficient reporting to judge attrition bias.
- Model support: Quote: "Data of the effect evaluation will be analysed according to both the intention-to-treat and per-protocol principles. In the first analyses all participants will be included according to their original assignment [52]." Comment: The report states ITT and attempts to contact participants with missing data, but does not provide numbers randomized, numbers analysed, or by-arm attrition and reasons.
- Model support context: [{"source": "article", "quote": "Data of the effect evaluation will be analysed according to both the intention-to-treat and per-protocol principles.", "relevance": "Indicates planned ITT analysis but gives no attrition counts or handling details."}, {"source": "article", "quote": "Non-compliant participants ... are approached for all follow-up measurements, and participants with missing data are contacted to ensure completion of data.", "relevance": "Describes efforts to reduce missing data but does not report actual missing outcome numbers, balance, or reasons by arm."}]
- GT support: Study authors conducted intention-to-treat analysis and imputed missing data.
- Evidence row: {}
- Source context preview: ## Analysis Descriptive techniques will be used to describe the study groups. Baseline variables will be compared, to detect differences between the participants of both groups at the start of the study. Data of the effect evaluation will be analysed according to both the intention-to-treat and per-protocol principles. In the first analyses all participants will be included according to their original assignment [52]. Participants of the intervention group who attended at least five of the seven programme sessions will be included in the per-protocol analysis. Based on prior work, five sessions of the programme are considered as sufficient programme exposure [15,18]. Mixed-effects...

## Workflow Evolution Notes

- Inspect mismatches where prediction is `Unclear risk` but GT is `Low risk`: these usually mean retrieval or Stage 1 extraction missed a concrete methodological phrase.
- Inspect mismatches where prediction is `Low risk` or `High risk` but GT is `Unclear risk`: these usually mean the prompt is allowing too much inference from generic trial language.
- For blinding mismatches, add outcome-type cues to the prompt: self-report outcomes, objective outcomes, assessor-administered outcomes, and whether lack of blinding can materially affect the outcome.
- For allocation concealment mismatches, require the model to distinguish sequence generation from concealment before assignment.