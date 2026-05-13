# Structured generated asset records

`generated_assets` in `.repo-familiar/bootstrap.yml` will use structured records with `path`, `kind`, `source`, and optional `content_sha256` fields from schema v1. We considered a simple path list, but structured records make future upgrade behavior easier by preserving what each asset is, where it came from, and whether generated content has drifted; `.repo-familiar/bootstrap.yml` itself is not self-hashed.
