---
doc-type: explanation
---

# Generated asset kind taxonomy

`generated_assets[].kind` uses a small closed vocabulary: `agent_instructions`, `skill`, `documentation`, `template_config`, `project_plan`, `metadata`, `dependency_manifest`, `dependency_lock`, `source_code`, `test_code`, and `data_fixture`. This distinguishes runtime agent assets, docs, generator configuration, planning artifacts, dependency state, executable seeds, tests, fixtures, and generator-owned metadata without using free-form labels.

The Python-first expansion was accepted on 2026-08-10. Selection groups such as `python` and `application` remain broader than kinds; kinds describe lifecycle-relevant file roles rather than command bundles.
