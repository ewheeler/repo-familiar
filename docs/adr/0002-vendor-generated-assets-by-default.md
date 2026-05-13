# Vendor generated assets by default

Generated downstream repositories will receive vendored copies of selected `repo-familiar` templates, skills, instructions, and documentation assets, plus bootstrap metadata recording the source and version used. We considered live references back to the reference source, but vendoring keeps bootstraps stable and self-contained; live sync can be introduced later as an explicit upgrade command rather than an ambient dependency.
