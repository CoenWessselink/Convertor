# CWS Viewer workspace schema 1.1

Schema 1.1 is backward compatible at application level with 1.0 and adds:

- `explode_offsets`;
- `measurements` including stable anchors, status and proof;
- `measurement_settings`;
- viewpoint explode state and visible measurement IDs.

The workspace remains viewer-only. It is bound to project ID and scene hash,
written atomically and accompanied by a SHA-256 sidecar. Loading against another
project is rejected; revision remapping is explicit and invalidates broken anchors.
