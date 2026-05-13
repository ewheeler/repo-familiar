# Bootstrap metadata path

Generated downstream repositories will store generator metadata at `.repo-familiar/bootstrap.yml`. We considered root-level metadata and placing this under `.agents/`, but chose a dedicated `.repo-familiar/` namespace to avoid root clutter, keep generator metadata separate from agent runtime instructions, and leave room for future files such as `.repo-familiar/manifest.yml` or `.repo-familiar/overrides.yml`.
