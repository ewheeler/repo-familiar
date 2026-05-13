# Model profiles location

Generated downstream repositories will store agent-facing model/provider profiles in `.agents/models.yml`, while `.repo-familiar/bootstrap.yml` records only the selected profile names under `selected_options.model_profiles`. This keeps runtime agent defaults with other agent assets, keeps generation provenance in generator metadata, and avoids putting provider secrets in either file.
