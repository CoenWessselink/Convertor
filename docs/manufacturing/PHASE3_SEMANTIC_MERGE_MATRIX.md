# Fase 3 semantic merge matrix

Deze matrix benoemt per concept exact een live contract. Modules met een
algoritme blijven producent of validator, maar definieren geen tweede publiek
contract.

| Concept | Canonieke definitie | Producent / validator |
|---|---|---|
| ManufacturingFace | `manufacturing.faces_model.ManufacturingFace` | `ManufacturingFaceService` |
| FaceLocalFrame | `manufacturing.faces_model.FaceLocalFrame` | `ManufacturingFaceService` |
| ContactPatch | `manufacturing.contact_model.ContactPatch` | contact engine |
| ManufacturingMark | `manufacturing.marking_model.MarkFeature` | `ContactScribingEngine` |
| MarkGeometry2D | `manufacturing.marking_model.MarkSegment2D` | marking engine |
| ManufacturingRuleSet | `manufacturing.marking_model.MarkingRuleSet` | declaratieve ruleset store |
| MachineCapability | `manufacturing.machine_capability_model.MachineCapabilityReport` | `MachineCapabilityEvaluator` |
| PieceInstance | `optimization.profile_nesting.models.PieceInstance` | profile nesting |
| ProductionInstanceIdentity | `project.manufacturing_contracts.ProductionInstanceIdentity` | production context |
| ManufacturingSequenceOperation | `manufacturing.neutral_job_model.NeutralOperation` | `NeutralJobBuilder` |
| ExportScope | `project.manufacturing_contracts.ExportScope` | scope-first export |
| NeutralManufacturingJob | `manufacturing.neutral_job_model.NeutralManufacturingJob` | `NeutralJobBuilder` |

Alle namen worden voor consumers samengebracht door
`cws_convertor.manufacturing.contracts`; de facade bevat uitsluitend aliases.

## Hash- en invalidatievolgorde

`geometry_hash -> base_manufacturing_hash -> manufacturing_face_hash -> contact_hash -> mark_set_hash -> ruleset_hash -> assembly_marking_variant_hash -> production_instance_hash -> nesting_hash -> sequence_hash -> artifact_hash -> release_hash`

Een gewijzigde laag verwijdert automatisch alle bestaande downstream hashes.
Een export/release mag alleen ontstaan nadat `require_through()` voor de
benodigde laag slaagt.

## Veiligheidsgrens

M9-M18 blijven frozen authority. Machine transfer, machine polling en remote
control blijven uitgeschakeld. Een ontbrekende of afwijkende M18 authority is
een blocker en wordt nooit door een lokale vervanging of scopeverbreding
omzeild.
