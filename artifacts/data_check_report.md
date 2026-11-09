# Data check report

Generated: 2026-11-09 14:28 UTC

**60 checks · 54 passed · 0 errors · 6 warnings**

- postgres: /tmp:5544/postgres

## Needs attention

| Result | Check | File | Detail | Items |
|---|---|---|---|---|
| WARN | url_not_retrieved | `research/sources_directory.csv` | 1 sources without a retrieved link | DS-05 |
| WARN | date_format | `research/sources_directory.csv` | 1 dates in an unrecognised shape | DS-06: '2019–2024 coverage (per listing)' |
| WARN | datasets_without_link | `research/data/dataset_inventory.csv` | 3 datasets have no verified link | DS-04; DS-10; DS-11 |
| WARN | licence_confirmed | `research/data/dataset_inventory.csv` | 9 datasets need licence confirmation | DS-02; DS-03; DS-04; DS-05; DS-07; DS-08 |
| WARN | record_count_known | `research/data/dataset_inventory.csv` | 8 datasets with unconfirmed record counts | DS-03; DS-04; DS-05; DS-06; DS-07; DS-08 |
| WARN | group_loadable_into_schema | `research/data/data_dictionary.csv` | 7 group values do not match the schema's field_group list ['after_treatment', 'engine', 'fleet', 'maintenance', 'market', 'vehicle'] | After-treatment / Compliance; Engine / AT; Engine / EV; Engine / Fleet; Maintenance / Fleet; Vehicle / Engine |

## All checks

| Result | Severity | Check | File | Detail |
|---|---|---|---|---|
| PASS | error | file_exists | `research/sources_directory.csv` | 93 data rows |
| PASS | error | expected_columns | `research/sources_directory.csv` | all expected columns present |
| PASS | error | consistent_column_count | `research/sources_directory.csv` | all rows have 10 columns |
| PASS | warn | no_blank_rows | `research/sources_directory.csv` | 0 blank rows |
| PASS | error | unique_key:id | `research/sources_directory.csv` | 0 duplicate, 0 empty keys |
| PASS | warn | no_padded_cells | `research/sources_directory.csv` | 0 cells with leading/trailing spaces |
| PASS | error | file_exists | `research/data/dataset_inventory.csv` | 11 data rows |
| PASS | error | expected_columns | `research/data/dataset_inventory.csv` | all expected columns present |
| PASS | error | consistent_column_count | `research/data/dataset_inventory.csv` | all rows have 13 columns |
| PASS | warn | no_blank_rows | `research/data/dataset_inventory.csv` | 0 blank rows |
| PASS | error | unique_key:dataset_id | `research/data/dataset_inventory.csv` | 0 duplicate, 0 empty keys |
| PASS | warn | no_padded_cells | `research/data/dataset_inventory.csv` | 0 cells with leading/trailing spaces |
| PASS | error | file_exists | `research/data/data_dictionary.csv` | 42 data rows |
| PASS | error | expected_columns | `research/data/data_dictionary.csv` | all expected columns present |
| PASS | error | consistent_column_count | `research/data/data_dictionary.csv` | all rows have 9 columns |
| PASS | warn | no_blank_rows | `research/data/data_dictionary.csv` | 0 blank rows |
| PASS | error | unique_key:field | `research/data/data_dictionary.csv` | 0 duplicate, 0 empty keys |
| PASS | warn | no_padded_cells | `research/data/data_dictionary.csv` | 0 cells with leading/trailing spaces |
| PASS | error | url_format | `research/sources_directory.csv` | 0 malformed URLs |
| WARN | warn | url_not_retrieved | `research/sources_directory.csv` | 1 sources without a retrieved link |
| PASS | warn | duplicate_urls | `research/sources_directory.csv` | 0 URLs listed more than once |
| WARN | warn | date_format | `research/sources_directory.csv` | 1 dates in an unrecognised shape |
| PASS | info | dated_sources | `research/sources_directory.csv` | 74 of 93 sources have a date; 19 are n/d |
| PASS | error | id_prefix_matches_company | `research/sources_directory.csv` | 0 mismatches |
| PASS | error | verification_status_present | `research/sources_directory.csv` | 0 rows without verification status |
| PASS | info | sources_per_company | `research/sources_directory.csv` | Tata Motors: 20, Mahindra: 16, VECV (Eicher): 15, Ashok Leyland: 15, Cummins: 16, UCI / public research: 2, NASA: 3, India Data Portal (mirror of VAHAN): 5, arXiv (research paper): 1 |
| PASS | error | dataset_id_format | `research/data/dataset_inventory.csv` | 0 ids not shaped DS-NN |
| PASS | error | access_link_format | `research/data/dataset_inventory.csv` | 0 malformed links |
| WARN | warn | datasets_without_link | `research/data/dataset_inventory.csv` | 3 datasets have no verified link |
| WARN | warn | licence_confirmed | `research/data/dataset_inventory.csv` | 9 datasets need licence confirmation |
| WARN | warn | record_count_known | `research/data/dataset_inventory.csv` | 8 datasets with unconfirmed record counts |
| PASS | error | availability_code_valid | `research/data/data_dictionary.csv` | 0 invalid codes |
| PASS | error | code_matches_meaning | `research/data/data_dictionary.csv` | 0 rows where code and meaning disagree |
| PASS | warn | field_name_snake_case | `research/data/data_dictionary.csv` | 0 field names not snake_case |
| WARN | warn | group_loadable_into_schema | `research/data/data_dictionary.csv` | 7 group values do not match the schema's field_group list ['after_treatment', 'engine', 'fleet', 'maintenance', 'market', 'vehicle'] |
| PASS | info | availability_distribution | `research/data/data_dictionary.csv` | A: 10, C: 3, D: 26, E: 3 |
| PASS | error | dataset_refs_resolve | `research/data/data_dictionary.csv` | 5 DS refs, 0 unknown |
| PASS | error | dataset_refs_resolve | `research/data/etl_and_data_quality_plan.md` | 4 DS refs, 0 unknown |
| PASS | error | dataset_refs_resolve | `research/projects_and_roadmap.md` | 6 DS refs, 0 unknown |
| PASS | error | markdown_links_wellformed | `research/README.md` | 0 links; 0 non-http link targets |
| PASS | error | markdown_links_wellformed | `research/companies/01_tata_motors.md` | 53 links; 0 non-http link targets |
| PASS | info | links_in_source_directory | `research/companies/01_tata_motors.md` | 18 of 38 unique links are not in sources_directory.csv |
| PASS | error | markdown_links_wellformed | `research/companies/02_mahindra.md` | 32 links; 0 non-http link targets |
| PASS | info | links_in_source_directory | `research/companies/02_mahindra.md` | 9 of 25 unique links are not in sources_directory.csv |
| PASS | error | markdown_links_wellformed | `research/companies/03_vecv_eicher.md` | 31 links; 0 non-http link targets |
| PASS | info | links_in_source_directory | `research/companies/03_vecv_eicher.md` | 11 of 26 unique links are not in sources_directory.csv |
| PASS | error | markdown_links_wellformed | `research/companies/04_ashok_leyland.md` | 24 links; 0 non-http link targets |
| PASS | info | links_in_source_directory | `research/companies/04_ashok_leyland.md` | 8 of 23 unique links are not in sources_directory.csv |
| PASS | error | markdown_links_wellformed | `research/companies/05_cummins.md` | 27 links; 0 non-http link targets |
| PASS | info | links_in_source_directory | `research/companies/05_cummins.md` | 3 of 20 unique links are not in sources_directory.csv |
| PASS | error | markdown_links_wellformed | `research/comparison_five_companies.md` | 0 links; 0 non-http link targets |
| PASS | info | links_in_source_directory | `research/comparison_five_companies.md` | 0 of 0 unique links are not in sources_directory.csv |
| PASS | error | markdown_links_wellformed | `research/data/etl_and_data_quality_plan.md` | 0 links; 0 non-http link targets |
| PASS | error | markdown_links_wellformed | `research/missing_data_requiring_permission.md` | 0 links; 0 non-http link targets |
| PASS | error | markdown_links_wellformed | `research/projects_and_roadmap.md` | 0 links; 0 non-http link targets |
| PASS | info | schema_objects | `research/data/schema_postgres.sql` | 16 tables, 2 views |
| PASS | error | no_duplicate_tables | `research/data/schema_postgres.sql` | 0 duplicates |
| PASS | error | balanced_parentheses | `research/data/schema_postgres.sql` | ( = 97, ) = 97 |
| PASS | error | foreign_keys_resolve | `research/data/schema_postgres.sql` | 6 referenced tables, 0 undefined |
| PASS | error | schema_loads_in_postgres | `research/data/schema_postgres.sql` | schema created and rolled back cleanly |
