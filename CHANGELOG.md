# Changelog

## 0.10.21-beta-dev - BOM production hub full extended closure

- Selectieafhankelijke actiematrix uitgebreid naar 87 acties met concrete
  voorraad-, inkoop-, tekening-, machine-, NC- en vrijgavevoorwaarden.
- Revisievergelijking levert exacte before/after-veldpaden per BOM-groep en
  canoniek object, inclusief verwijderde objecten en opgeslagen 3D-bounds.
- Gemengde reststuk-/handelslengteplanning reserveert meerdere fysieke bronnen
  atomair en zet alleen werkelijk niet-toegewezen occurrences door naar inkoop.
- Slimme selecties ondersteunen recursieve EN/OF/NIET-groepen; de vrije lasso
  verwerkt ook volledige omsluiting en randkruising.
- Transacties schrijven resultaatregels per BOM-groep en persistente inverse
  patches; releasegebonden undo werkt na projectherstart en faalt gesloten bij
  een nieuwere projectinhoud.
- De gedeelde rendercache is mesh-hashgebonden, invalideert bij vervanging en
  publiceert controleerbaar resource-identitybewijs.

## 0.9.0-alpha-dev - V9 viewer, centrale werkruimtes en A3-tekening

- V9 Viewer componentgewijs geintegreerd met behoud van projectmodel 2.5 en de bestaande Part Workbench.
- Hoofdschil geordend in elf werkruimtes met Viewer / Project als centrale selectie- en actiecontext.
- Contextacties toegevoegd aan modeltree, 3D-viewer en property grid; selectie wordt doorgegeven aan converter, PDF, profielen, tekeningen, scribing, hoeveelheden en export.
- Onderdeel-PDF vernieuwd naar Tasche A3-standaard met elevatie, planzichten, doorsnede, gatdetail, 3D-review en fabricagetabellen.
- Horizontale maten blijven incrementeel plus absoluut; verticale maten absoluut; alle gaten worden geidentificeerd en gemaatvoerd.
- Optimalisatie is als `UI integration gap` vastgelegd omdat de huidige backend geen solver aanbiedt.

## 0.8.3-beta-dev - Released production packages and drawings

- Viewer V0-V6 is integrated into the existing CWS Convertor main application
  through the canonical SteelModel and ViewerHost boundaries.
- The Project Viewer now combines the project tree, parts grid, properties,
  validation and the VTK total-model renderer with synchronized stable IDs.
- Professional display controls, workspace schema 1.1, measurements, sections,
  viewpoints and display-only history are included without changing project truth.
- The Part Workbench now contains an experimental exact OCCT/BREP viewer for
  source/canonical inspection, stable subshape picking, snapping and compare.
- Viewer code cannot authorize production release; NC1, STEP, IFC and Trusted PDF
  remain controlled by the existing canonical validation and release services.
- Part drawings now use the Tasche Staalbouw sheet identity and logo, a structured
  engineering header/sidebar/title block and a permanent drawing standard.
- Horizontal hole positions are always shown incrementally and absolutely;
  vertical positions remain absolute, with every hole identified and dimensioned.
- GitHub-hosted Windows validates VTK mesh construction and deterministic OCCT
  topology without creating an unstable native OpenGL window. Local native,
  dist, portable and installed gates retain the full render and picking checks.
- PyInstaller now registers native package DLL directories for CasADi, Qt, VTK
  and OCCT before application imports.
- Two permanent regressions cover exact STEP metric persistence and deterministic
  replay of IFC display-approximation warnings from the shared mesh cache.
- Phase B batch 3 adds bounded progressive whole-project mesh loading with
  selected-part priority, cooperative cancellation and stale-result guards.
- Mesh resources are attached in grouped scene patches; a rejected resource is
  isolated so valid batch neighbours continue loading.
- The viewer footer now exposes determinate load progress, failure counts and a
  stop command, with selection-only restart after cancellation.
- A 5,000-entity scheduler validation and six permanent regressions cover
  concurrency, priority, retry, cancellation, batching and malformed resources.
- Phase B batch 2 adds hash-bound real STEP, IFC and current-canonical viewer
  meshes through the SteelModel 1.0 / ViewerHost 1.0 boundary.
- The existing Tk workspace now renders verified meshes with an off-screen VTK
  pipeline, synchronized picking, fit/isometric views, orbit and zoom.
- Meshes load lazily from re-verified source bytes; manual/unverified selections
  never become display geometry and runtime inspection does not upgrade project truth.
- Structural visual-golden, transform, tamper and 600-instance shared-geometry
  regressions plus a packaged VTK native self-test were added.
- Installer automation now supports an explicit per-user validation mode;
  file associations use the matching user/machine Classes root and are covered
  by an installed-registry regression before uninstall.
- Atomic per-part and per-assembly-mark release packages added to Project Model workflows.
- Every release re-runs the canonical NC1, STEP, IFC and Trusted PDF import comparison.
- Part artifacts include production/review PDF, optional plate DXF, CSV, JSON, label PDF and preview PNG.
- Assembly packages include A3 vector drawings, semantic STEP/IFC, NC/PDF folders, BOM extracts and a total report.
- Artifact identity, revision, manufacturing hash, canonical signature, roundtrip report hash and SHA-256 are recorded.
- Duplicate visible positions with different manufacturing identities and stale releases are hard-blocked.
- Project GUI, main CLI, export CLI, packaged runtime smoke and Windows build dependencies cover the release path.
- External reference models remain `manual_validation_required`; this version does not infer golden values.

## 0.8.2-alpha-dev - Part Workbench production roundtrips

- Project Model 2.5 and Part Workbench 1.1 bind the recognition candidate to the manufacturing hash.
- Existing 2.x projects migrate explicitly; old rebuild, roundtrip and production artifacts are invalidated.
- Analytical arcs, custom cross-sections and worked catalogue profiles are rebuilt as exact CadQuery solids.
- Self-intersecting contours and arcs without an explicit direction are blocked before rebuild.
- NC1, STEP, IFC and Trusted PDF are exported, re-imported and compared as one required matrix.
- Payload identity, features, volume, area, bounding box, solid count and validity are reported per format.
- Reports and artifacts are hash-bound to the current manufacturing state and canonical signature.
- Part Workbench UI and CLI expose canonical rebuild, roundtrip validation and guarded release.
- Non-exact IFC meshes remain `manual_validation_required`; no engineering truth is inferred from tessellation.

## 0.8.1-alpha-dev - Windows native runtime repair

- CasADi 3.7.2 is pinned and its complete native wheel is collected by PyInstaller.
- A frozen-runtime hook registers CasADi's bundled DLL directory before CadQuery starts.
- Native self-test and GUI-smoke modes exercise CasADi, CadQuery/OCP, IfcOpenShell, PyMuPDF, Matplotlib, NumPy, SciPy and Pillow.
- Windows CI now validates the dist folder, a freshly extracted portable ZIP and the installed application without Python on the child PATH.
- Each packaged runtime also creates a project and performs a real NC1-to-STEP conversion.
- The earlier 0.8.0 Windows artifact is superseded because its packaged GUI/CAD stack was not exercised.

## 0.8.0-alpha-dev - Part Workbench foundation

- Versioned Part Workbench state added with immutable source geometry references.
- Analytical part forms, production frame, reference sides, contours and features added.
- Field provenance, validation issues, audit, undo/redo and artifact invalidation added.
- Project Model schema raised to 2.4 with migration and save/reopen coverage.
- Integrated Part Workbench added to the existing Project / Productie screen.
- Synchronized part selection, sortable grid, property/validation panels and required detail tabs added.
- Source-envelope and analytical 3D/2D comparison added without claiming an exact source BREP.
- Plate bounding-box candidate and through-hole editing use one atomic service update.
- GUI regression covers start, apply, validate, undo and redo; release remains roundtrip-blocked.
- Windows build workflow now runs every `tests/*_smoke.py` file.
- Windows release configuration smoke prevents non-numeric Inno version metadata.
- Explicit reviewed length, plate thickness and diameter values added to Workbench revisions.
- Deterministic canonical-solid rebuild added for straight plates with inner contours and through holes, solid round bars and unworked exact catalogue profiles.
- Source comparison added for volume, area and bounding dimensions with tolerances, plus exact solid-count and validity checks.
- Missing or non-part-scoped source measurements now produce `manual_validation_required` instead of invented expectations.
- Hashed rebuild reports are persisted beside the revision and invalidated when the manufacturing hash changes.
- Canonical comparison tab added with expected, found, delta, result and blocking reason reporting.
- Six canonical rebuild regressions and updated GUI validation added; all 28 smoke scripts pass locally on Windows.
- Production release remains blocked pending exact source isolation and NC1/STEP/IFC/PDF roundtrip validation.
- Canonical builder loading is lazy so the packaged project CLI does not initialize CadQuery/CasADi for non-geometry commands.
- Native Windows workflow 31685684421 passed its then-current gates, which were later found insufficient because they did not start the packaged GUI/CAD stack.

## 0.7.0-alpha — Semantische IFC/STEP-projectimport

- Gedeelde, dependency-light ISO-10303-21-grafiekkern toegevoegd voor IFC en STEP.
- IFC2X3/IFC4 assemblies, parts, fasteners, lassen, placements, properties, materialen en relaties als actieve Project Model-entiteiten gematerialiseerd.
- STEP AP203/AP214/AP242 product definitions, occurrences, placements en BREP-roots gematerialiseerd zonder fictieve opsplitsing.
- Stabiele bron-ID, geometry hash en manufacturing hash per onderdeel toegevoegd en over opslaan/herimport getest.
- Semantische import transactioneel gemaakt met bronhashcontrole, bronpurge en rollback bij fouten.
- Project Model opgehoogd naar schema 2.1 en projecthashing geoptimaliseerd voor grote modellen.
- `.cwscproj`-manifest uitgebreid met semantic, content, revision-content en manufacturing-state hashes.
- CLI-opdrachten `project-import`, `project-tree`, `project-list-parts` en `project-list-assemblies` toegevoegd.
- Project/Productie-GUI uitgebreid met echte semantische import, interne voortgang en materialisatiecounts.
- Tekla-referentie gematerialiseerd als 353 assemblies, 2.429 parts, 723 fasteners en 2.654 lassen.
- Drie echte AP242 STEP-referenties elk als precies één product/solid/part geïmporteerd.
- Productiegate bewust gesloten gehouden tot classificatie, featureherkenning en roundtripvalidatie.
- Windows-buildstraat en installerconfiguratie bijgewerkt naar 0.7.0-alpha.
- STEP-route `C_fused_review` toegevoegd voor bronnen zonder betrouwbare solid-root; er wordt geen geometrie, occurrence, assembly of opsplitsing verzonnen.
- Coöperatief annuleren toegevoegd aan Part 21-parser, importers, projectservice en GUI, met volledige transactionele rollback.
- Canonical JSON-hashing en grote-projectopslag versneld zonder het bestaande hashcontract te wijzigen.
- Vrijgavevalidatie uitgebreid naar 82/82 controles; referentiematerialisatie 14,20 s en geverifieerd opslaan/openen 13,01 s in de huidige Linuxomgeving.

## 0.6.0-beta — Project Foundation

- Productnaam en zichtbare distributie hernoemd naar **CWS Convertor**.
- Centrale product- en versieconstanten toegevoegd.
- Canonical Project Model 2.0 toegevoegd met project-, assembly-, part-, inkoop-, fastener-, weld-, voorraad-, operatie- en machine-entiteiten.
- Stabiele bronidentiteit, placement-onafhankelijke geometry hash en manufacturing hash toegevoegd.
- Draagbaar `.cwscproj`-formaat gebouwd op ZIP + SQLite met manifest, SHA-256, CRC, integriteitscontrole en veilige extractie.
- Projectpreviews worden hash-gecontroleerd bewaard bij openen/opslaan, autosaveherstel en pakketmigratie.
- Atomisch opslaan, backups, revisies, auditlog, lichtgewicht autosave, herstel en read-only/migratieroute toegevoegd.
- Deterministische IFC/STEP-nulmeting en selectie van importstrategie A/B/C toegevoegd.
- Productiepoort toegevoegd: complete-model-export blijft geblokkeerd zolang semantische import/validatie niet is afgerond.
- Functioneel **Project / Productie**-tabblad toegevoegd.
- Project-CLI toegevoegd voor maken, importnulmeting, informatie, bronnen, verificatie, JSON-export, extractie, herstel en migratie.
- Annuleerbare achtergrondjobmanager toegevoegd.
- Regressietests toegevoegd voor model, opslag, baseline, CLI, jobs, service en de vier echte referentiemodellen.
- Windows PyInstaller/Inno Setup-build hernoemd en uitgebreid met projecttests, `.cwscproj`-associatie en installatiesmoke.
- Reproduceerbare directe dependency locks en SPDX-SBOM toegevoegd.
- Bestaande NC1/STEP/IFC/PDF-kern en legacy payloadcompatibiliteit behouden.
- Project Foundation-validatie: 117/117 controles geslaagd op het Tekla IFC-model en drie AP242 STEP-modellen.

## 0.5.1 — PDF review en maatgrafiek

- Deterministische feature-gekoppelde maatgrafiek toegevoegd.
- Interactieve PDF-review met bronbewijs, correcties, bevestigingen en audit toegevoegd.
- Begrensde AI-laag voor semantische voorstellen geïntegreerd.
- Trusted Converter PDF en synthetische LO4-keten uitgebreid en getest.

## 0.5.0 — Trusted PDF en AI-fundament

- Trusted Converter PDF met embedded canoniek model en hashes toegevoegd.
- Externe vector-PDF-analyse en veilige reviewbasis toegevoegd.

## 0.4.0 — Canonieke IFC-roundtrip

- Canoniek onderdeelmodel en lossless converter-eigen IFC-payload toegevoegd.
- Focusroundtrips voor NC1/STEP/IFC hersteld.
