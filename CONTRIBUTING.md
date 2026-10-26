# Contributing

Run `python -m unittest discover -s tests -v` from the repository root. These tests exercise the geometry algorithms without Autodesk Fusion or third-party Python packages.

Changes to commands also need manual testing inside Fusion. See [the native test checklist](docs/TESTING.md). Include the Fusion build, OS, selection type, error text, and a small shareable mesh when reporting a bug. Do not include private models, credentials, or machine-specific editor files.

Keep distance calculations in centimeters internally and display explicit units in the UI. Preserve existing geometry on failure. Keep algorithm code separate from Fusion event handlers. Record limitations accurately; sampled curve checks are not certified continuous error bounds.
