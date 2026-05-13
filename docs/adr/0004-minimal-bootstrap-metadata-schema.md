# Minimal bootstrap metadata schema

`.repo-familiar/bootstrap.yml` will start with a small schema containing `schema_version`, `reference_source`, `generated_at`, `generator`, `selected_options`, and `generated_assets`. This captures enough provenance for debugging and future explicit upgrades without treating bootstrap metadata as a full dependency lockfile.
