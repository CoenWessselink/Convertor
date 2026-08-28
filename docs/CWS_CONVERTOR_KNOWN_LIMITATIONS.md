# CWS Convertor known limitations

- Physical machine/controller qualification is `BLOCKED_EXTERNAL_EVIDENCE` until machine, firmware, tooling, formal specification or golden sample, measurement report and owner approval exist.
- Direct machine transfer, deployment transport, remote control and machine polling remain disabled.
- Code signing is not claimed because no production signing certificate was supplied to this local build.
- Remote CI is not claimed for the local uncommitted worktree. Local artifacts are bound to a deterministic source-tree SHA-256 and carry the revision tag `uncommitted`.
- Confidential real-file fixtures are hashed and tested locally but are not embedded in the release or source ZIP.
- IFC viewer proxies and untrusted PDFs never become exact production geometry without separate canonical proof and confirmation.
- The CLI executable requires the complete one-folder/portable/installed runtime; only the final root GUI EXE is self-contained.
