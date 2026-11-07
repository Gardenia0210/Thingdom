# Refinement Notes

- Backend origin: `Code/kids_language_2-main/kids_language_2-main`; duplicate backend under the YOLO directory is not merged.
- Python apps, migrations and persona Markdown resources are preserved. Source SHA-256 hashes are recorded in `source_manifest.json`; private environment files, databases, caches, editor configuration, deployment machine paths and duplicate third-party documentation are excluded.
- Non-English Python comments are removed and docstrings are normalized to English. Runtime prompts, bilingual character resources, field labels and API messages are preserved because they are functional data.
- Fixed image inputs and implicit model paths are replaced with required caller arguments. A reusable detector exposes structured detections, summary counts and the highest-confidence class. Training and export entry points are newly added because project-specific ones were absent.
- Fake first-turn child greetings are replaced with clearly marked object detection events containing the detected name and selected chapter. Empty user input and empty model output now fail explicitly. An unselected chapter is no longer silently replaced with `fruit`.
- New v2 conversations use the naming agent rather than the historical preset identity lookup. Its schema/admin remain for migration compatibility; existing real conversation identities and persona templates remain valid.
- Reply/stop lookups require an active conversation for the sending device. Mastery evaluation restricts words to that user's active, unlocked plans and unfrozen, unmastered candidates.
- MQTT startup is opt-in. A dedicated `runmqtt` command separates device workers from migrations and HTTP processes. Dead startup code in the disabled legacy app is removed.
- Settings read the backend-local `.env`; no fallback secret or database password is embedded. PostgreSQL checkpoint connections reuse Django database parameters without interpolating credentials into a URI.
- Fixed the inherited streaming parser's loss of split JSON keys and its incorrect decoding of Unicode escapes. Fragmented strings, escaped quotes and surrogate-pair emoji have regression coverage.
- Fixed index/field removal order in the copied `user_system` migration `0003` for fresh database initialization, without changing its resulting model state.
- Pinned compatible LangGraph prebuilt/checkpoint subpackages after dependency resolution exposed an import mismatch. The full agent now assembles in an offline regression test.

This package preserves the existing application's broader behavior. The legacy agent directory contains models and callable helpers but no implemented HTTP views; its route prefix is retained. Real PostgreSQL, broker, model credentials, curriculum content and trained model artifacts remain deployment prerequisites. The parent mobile UI was not present in the supplied source.

## Raspberry Pi — 2026-11-07

Added the supplied Raspberry Pi drivers, image assets and local checkpoints. Replaced demo entry points and v1 MQTT with a real capture, transcription and v2 dialogue workflow. Board configuration uses local paths and environment variables.
