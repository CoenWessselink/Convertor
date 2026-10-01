# Native Tekla adapter: implementation and proof boundary

The adapter targets .NET Framework 4.8, Windows x64 and strongly typed official Trimble Open API NuGet packages. `2024.0.0` is the current developer **compile candidate**, not the user's detected Tekla version. It refuses connection if the exact configured installed version is absent or differs from `TeklaStructuresInfo.GetCurrentProgramVersion`, or if its major version differs from the loaded API assembly. No live licensed Tekla session has been tested. Windows compilation, disconnected UI startup and per-user script installation have separate CI evidence; they do not establish native Tekla runtime behavior.

| Capability | Implemented API path | Evidence and shipping status |
|---|---|---|
| Live model identity | `Model.GetInfo`; path/name identity binding, actual version, independently observed part-state revision | Implemented; actual installation unverified. Public `ModelInfo` exposes no model GUID; the path binding is explicitly labeled. |
| Part reads | Native beam endpoints/offsets; polybeam/plate contours/chamfers; profile/material/phase/mark/placement; native GUIDs; related object IDs; solid bbox | Implemented reads. Bbox/points are observations, not exact BRep equivalence. Shapes and other native types carry `UNSUPPORTED` status. |
| Model/catalog selection | Official model/UI selectors; exact native GUID resolution | Implemented. Unknown GUID blocks the whole requested selection. |
| Real catalogs | Official library profile/material/component/shape enumerators | Implemented. Parametric prefixes are returned separately and never treated as exact valid profile strings. |
| Global work plane | Capture original plane, set `new TransformationPlane()`, restore in `finally` | Implemented; restore failure stops the run. No orientation guess. |
| Native beam/polybeam/plate upsert | Strongly typed `Insert`/`Modify`; explicit geometry, placement, class, names, numbering, phase and ownership UDA fields | Compile implementation; **disabled** until exact frozen runtime approval, assembly hashes, source authority and persistence capabilities are proven. No native defaults accepted as engineering intent. |
| Persistent save | `ModelHandler.Save(comment,user,reason)`, saved-state and identity checks | Compile implementation; **disabled** without frozen native runtime evidence. `Model.CommitChanges` only commits changes and undo/view state. |
| Genuine reopen/readback | `ModelHandler.Close`, observed closed model, `Open(path,false)`, new `Model`, independent reread | Compile implementation; **disabled** without native runtime evidence. Open excludes autosave. Model/revision must match saved checkpoint before closing and after rereading. |
| Persistence verifier | In-memory snapshot SHA with unpredictable lifecycle nonce, model/revision, frozen evidence and actual assembly hashes; one-time consumption | Implemented. Uploading a JSON snapshot or nonempty proof string cannot establish production persistence. |
| Native removal | Dedicated ownership, transaction and removal proof not implemented | **Blocked**. No native `Delete` calls or guessed rollback deletion. |
| Manufacturing feature writes/readback | Exact shape/holes/bolts/welds/cuts/connections proof not implemented | **Blocked**. `ManufacturingHash` remains null; actual related object IDs do not prove detailed feature geometry. |

The production host uses `DisconnectedAdapter` until a verified session is configured. It throws a clear `TEKLA_DISCONNECTED` exception and never returns an empty “real model” or uses the test fixture as a production substitute.

Native ownership requires the six explicit UDA fields `CWS_OWNER`, `CWS_CANONICAL_ID`, `CWS_SOURCE_ID`, `CWS_SOURCE_REV`, `CWS_PHYSICAL_ROLE`, `CWS_SCHEMA`. Unknown/manual/downstream objects are protected. Missing UDA definitions are rejected by Tekla and leave the transaction requiring recovery; the bridge does not invent an unsafe delete rollback. UDA hashes are never copied into measured geometry/manufacturing evidence. S275JR remains S275JR; raw/resolved material differences are rejected until value-bound alias authority is actually implemented.

Native write candidates require `NATIVE_FEATURE_POLICY=EXPLICIT_NO_MANUFACTURING_FEATURES` and `NATIVE_GEOMETRY_POLICY=LINEAR_NO_CHAMFERS`, plus all explicit native placement/name/class/numbering/phase fields. This narrow contract does not accept source holes or cuts and quietly discard them. Other feature intents stay blocked. Frozen `AuthorityService` approval is checked for the operation component and `source.geometry`, `source.profile`, `source.material`. Test-fixture authority can never authorize this adapter.

Primary references verified during this build:

- [Official Trimble Tekla.Structures.Model 2024.0.0 package](https://api.nuget.org/v3-flatcontainer/tekla.structures.model/2024.0.0/tekla.structures.model.2024.0.0.nupkg), including `ModelHandler.Save`, `Close`, `Open`, `IsModelSaved` in the official XML.
- [Official coordinate systems/work planes guide](https://developer.tekla.com/documentation/coordinate-systems-and-work-planes).
- [ModelHandler.Save documentation](https://developer.tekla.com/doc/tekla-structures/2025/save-method-string-string-52977). The web page is 2025; the exact 2024 compile signature comes from official 2024 package XML.
- [ModelHandler.Open documentation](https://developer.tekla.com/doc/tekla-structures/2026/open-method-71972). The web page is 2026; the exact 2024 compile signature comes from official 2024 package XML.
- [Official catalog API](https://developer.tekla.com/doc/tekla-structures/2025/catalog-handler-methods-46543).

Exact downloaded package, DLL and XML SHA-256 values are recorded in `evidence/native-reference-assemblies.json`. A Windows compile proves references and syntax; it does not prove placement, factory behavior, runtime persistence, clashes, or manufacture correctness. All of those stay `NOT_RUN`/blocked until tested in the actual licensed Tekla installation and bound to the exact source commit.
