# HVPC Trimble Desktop Capture Attempt

Status: `BLOCKED_EXTERNAL_EVIDENCE`

- Exactly one `CWS Convertor 0.10.18-beta-dev` window and one `Trimble Connect` window were discovered on the same machine.
- First capture failed with `GetCursorPos failed: Toegang geweigerd. (0x80070005)`.
- A fresh reselection without activation failed with `IGraphicsCaptureItemInterop.CreateForMonitor ... (0x80070057)`.
- No stale coordinate, screenshot ID or window handle was reused.
- CWS independently proves 5,725/5,725 exact physical objects, 0 missing and 0 duplicate.
- Live synchronized-camera and object-by-object Trimble parity are not claimed.
