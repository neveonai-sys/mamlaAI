Place plain-text legal source files here, one file per source body.

Current repository state:
- This folder now contains original starter knowledge-base summaries written for Mamla Brain.
- These files are safe seed material for retrieval testing and framework validation.
- They are not a substitute for authoritative bare-act text or licensed case-law databases.

Expected format:
- UTF-8 `.txt` files
- Prefer section-oriented text where each section begins with `Section <number>`

Seed files currently included:
- civil_procedure_foundations.txt
- criminal_procedure_foundations.txt
- evidence_foundations.txt
- contract_and_obligation_disputes.txt
- limitation_and_interim_relief.txt
- cpc_jurisdiction_injunction_execution_map.txt
- crpc_bail_investigation_trial_map.txt
- evidence_admissions_electronic_records_map.txt
- ipc_offence_analysis_map.txt
- negotiable_instruments_cheque_dishonour_map.txt
- specific_relief_contract_remedies_map.txt
- bail_and_personal_liberty_precedents.txt
- criminal_vs_civil_wrong_precedents.txt
- electronic_evidence_precedents.txt
- injunction_and_specific_relief_precedents.txt
- cheque_dishonour_presumption_precedents.txt
- property_title_and_possession_precedents.txt
- matrimonial_custody_and_maintenance_precedents.txt
- company_director_and_vicarious_liability_precedents.txt

Recommended next step for production-quality legal reasoning:
- Add curated primary-law source text and verified case-law summaries in separate files.

Important note:
- The statute-oriented files in this folder are original summaries and section maps.
- They reference acts and section numbers, but do not reproduce authoritative statute text verbatim.
- The precedent-oriented files are also original case notes written for retrieval, not copied headnotes or judgment extracts.

Use `python manage.py ingest_legal_kb` from `Legalv1/` after adding or changing files in this directory.
