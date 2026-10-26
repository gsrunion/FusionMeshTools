# Publishing this prepared repository

The repository is local until you explicitly create a GitHub remote and push it. No GitHub repository or release is created by the build script.

## Before the first push

1. Review README, MIT license attribution, and the experimental/preview API notice.
2. Run `python3 -m unittest discover -s tests -v` and `python3 tools/build_release.py`.
3. Inspect the ZIP: it should contain one `FusionMeshTools` folder with the entry point and matching manifest, runtime helpers, license, and documentation.
4. Review the tracked files for private models, personal paths, caches, or secrets.
5. Create an empty GitHub repository named `FusionMeshTools` under your chosen account. Do not add another README or initial license on GitHub.
6. Add the remote and push the local `main` branch using your preferred Git client.

## First release

Create a **prerelease** named `v0.8.1 — Experimental`. Attach:

- `dist/FusionMeshTools-v0.8.1.zip`
- `dist/FusionMeshTools-v0.8.1.zip.sha256`

Use [CHANGELOG.md](../CHANGELOG.md) as the release notes, including the preview API dependency and macOS-only native validation. Prefer the installable ZIP over GitHub's generated source archive for end users.

## Later development

This standalone folder is a copy of the original local add-in. Until you switch installations, edits in the earlier `SplitFaceGroups` folder do not automatically update this repository. Stop and disable that earlier add-in before loading FusionMeshTools; both use the same manifest and command IDs.
