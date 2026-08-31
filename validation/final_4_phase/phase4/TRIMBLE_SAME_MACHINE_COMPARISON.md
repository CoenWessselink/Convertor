# Same-machine Trimble comparison

Status: `PASS` for the requested same-machine comparison evidence.

Model: `HVPC te Hengelo fasen totaal.ifc`

| Runtime | Scenario | Result |
|---|---|---:|
| Trimble Connect | Same-session open to refreshed complete model view | 3.551 s |
| CWS Convertor | Warm, 5,725-request large model, mean of 10 | 0.248 s |
| CWS Convertor | Cold, 5,725-request large model, mean of 5 | 71.041 s |

The Trimble screenshot is a real runtime capture from this workstation. The comparison closes the prior `NOT_TESTED` evidence gap, but it does not hide the separate cold-load failure: CWS does not yet prove the explicit 3-5 second cold target.
