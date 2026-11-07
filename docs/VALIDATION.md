# Verification Evidence

Verified on 2026-10-17 (Asia/Shanghai), using Python 3.12.14 in an isolated local environment.

| Check | Result |
| --- | --- |
| Offline pipeline tests | 6 passed |
| Django database and agent assembly tests | 6 passed |
| Django system check | Exit 0; five inherited `models.W035` warnings |
| Migration/model consistency | `makemigrations --check --dry-run`: no changes detected |
| Backend dependency consistency | `pip check`: no broken requirements |
| Python syntax and English comment scan | All delivered Python files parsed; no non-English comments |
| Original backend hashes | All 83 copied source/resource hashes unchanged at origin |
| Core code map | 19 entries; AST-derived method ranges; titles <=10 words and descriptions <100 words |

The six offline tests cover actual detection/chapter event data, missing inputs, missing weights, model-derived counts and top category, no detections, missing datasets, and arbitrarily fragmented JSON with escaped quotes, Chinese characters and emoji. Model inference outputs are mocked; no model accuracy is claimed.

The six Django tests cover foreign-device reply/stop rejection, real detection event forwarding, missing-chapter rejection, foreign-user vocabulary rejection, timed vocabulary thawing, and assembly of the full LangChain pipeline without network calls. Test databases are temporary SQLite databases. The original migration chain is executed for the active database during these tests.

## Repairs discovered during verification

The inherited `user_system` migration `0003` removed indexed foreign keys before their indexes and removed fields from a model that was about to be dropped. This failed on a fresh SQLite migration. The delivered copy now removes explicit indexes first and drops the obsolete model directly; final migration state still matches the models. Existing source migrations were not modified.

Unconstrained LangGraph subpackages resolved to versions incompatible with the original pinned framework. Pinning `langgraph-prebuilt==1.0.7` and `langgraph-checkpoint==3.0.1` restored imports and full agent assembly. Backend requirements were installed successfully from PyPI and passed dependency consistency checks. The optional Windows backend dependency snapshot records the exact verification environment.

## Remaining integration prerequisites

The five `models.W035` warnings identify matching table names in legacy and v2 apps. Their database router sends legacy tables to `legacy` and current tables to `default`; table names were retained for compatibility. Keep these databases separate.

Real PostgreSQL migrations/checkpoint persistence, MQTT delivery/reconnection, cloud model behavior, real image inference, model training/export, and physical hardware behavior have not been exercised. They require actual service credentials, a broker, curriculum data, model weights/datasets and a configured Raspberry Pi. No successful end-to-end hardware result is claimed.

## Reproduce

From `Thingdom_Code`, run `python -m unittest discover -s tests -v`. From `kids_language_2-main`, run `python manage.py check --settings kids_language_2.test_settings`, `python manage.py test --settings kids_language_2.test_settings`, and `python manage.py makemigrations --check --dry-run --settings kids_language_2.test_settings`. Use an installed Python 3.11/3.12 environment with the backend requirements. Run `python -m pip check` in that environment.

## Raspberry Pi — 2026-11-07

Five offline Raspberry Pi tests passed: capture retries, v2 message routing and conversation IDs, malformed/retained/partial reply rejection, transcript and vocabulary payloads, and text-only flashcards. All board Python files parsed. Physical peripherals, YOLO inference and live broker/ASR/TTS services were not exercised.
