# SteelConverter-superprompt — traceability voor CWS Viewer V6

De aangeleverde SteelConverter-superprompt blijft een requirementsbron. `SteelModel` is in CWS gemapt op het bestaande Canonical Project/Part Model; er is geen tweede waarheid toegevoegd.

| Requirement | V6-uitvoering | Status |
|---|---|---|
| Viewer/import accuracy eerst | exact BREP-catalogus en compare vóór exportgate | Gereed binnen V6-scope |
| Geen vrije CAD-modeler | begrensde plate/hole-editor | Gereed |
| Geen gokken | ambiguous multi-solid en unsupported features blocked | Gereed |
| Exacte productieassen | rechterhandig frame + review | Gereed |
| Referentiezijden | exact face-ID + reviewer/reason | Gereed |
| Gaten, contouren, bogen en slots | analytische features en canonical builders | Gereed binnen testscope |
| Wijzigingen direct traceerbaar | manufacturing hash, audit, undo/redo | Gereed |
| Scribing/contactlijnen | BREP-section proposals, preview, confirm/reject, provenance | Gereed als reviewdata |
| Onderscheid scribe/mark/cut | operation contract staat alleen scribe/mark toe | Gereed |
| Geen geometrie gokken voor scribe | geen contact = geen proposal; multi-solid blocked | Gereed |
| Exporteerbare scribe-data | checksum-JSON reviewpayload | Gereed; geen machineadapterclaim |
| Productie-output alleen na bewijs | compare + formatspecifieke roundtripgate | Gereed voor geteste plaatklasse |
| Complete professionele editor | V6 exact geometrytabs; prijzen/tijden blijven hoofdappscope | Gedeeltelijk/later |
| Willekeurig IFC-projectdeel exact isoleren | niet algemeen beschikbaar | Open |
| Machine-/DSTV-scribing | vereist gevalideerde adapter | Open |
