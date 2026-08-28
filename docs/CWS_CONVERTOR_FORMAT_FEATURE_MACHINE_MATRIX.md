# Format, feature and machine matrix

| Area | Proven software scope | Fail-closed boundary |
| --- | --- | --- |
| IFC | Semantic hierarchy, identities, properties and exact-on-demand/proxy distinction | Per-part production exactness requires geometry proof |
| STEP/STP | Product/solid identity, canonical exact BREP where resolved | Ambiguous or fused structure remains review-required |
| NC1/DSTV | Deterministic supported-profile parsing and serialization with re-import compare | Unsupported blocks and machine/controller specifics are not guessed |
| Trusted PDF | Vector drawing plus canonical payload/hash verification | External/untrusted PDF remains reviewed canonical until confirmed |
| Workbench | Plate and proven profile/features through commands, rebuild, validation and rollback | Unsupported geometry stays visible and blocks release |
| Profile nesting | Material balance, stock/remnants, miter/common-cut, scenarios, locks and validation | No optimality claim without solver proof/bound |
| Plate nesting | Canonical 2D placement, kerf, margins, grain/rotation constraints and overlap validation | No proprietary machine output |
| Manufacturing | Faces, contacts, marks, hole references, identity, reachability, sequence and neutral job | Machine transfer and deployment are disabled |
| Quality | Plans, tolerances, measurements, NCR, rework, reinspection, certificates and approval | Final quality release blocks on missing/failed/stale evidence |
