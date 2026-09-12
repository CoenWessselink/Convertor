# Master Requirements Register V2

Source baseline: `a67102384dd5ae0d99651f738074334ce37115be`. Installed commit: **not proven**.

Historical PASS results are not inherited. PARTIAL means current acceptance remains unverified. Existing paths are mapping candidates, not proof of behavior. Requirements from later blocks are registered now; their implementation remains subject to the mandatory block sequence.

3856 source assertions; 3843 applicable; 87 canonical W18 actions. Overlapping source assertions are retained with traceability, so these counts are not unique product features.

Evidence coverage is not product completion: the actual built/tested product percentages remain unknown. Dimension applicability is separately recorded; an unknown need for installed/real-world testing is neither an exemption nor a required test counted in its denominator.

| Evidence dimension | Proven | Known required | Applicability unknown | Evidence coverage % |
|---|---:|---:|---:|---:|
| functional_built | 0 | 3843 | 0 | 0.0 |
| integration_tested | 0 | 3843 | 0 | 0.0 |
| installed_tested | 0 | 734 | 3109 | 0.0 |
| real_world_tested | 0 | 121 | 3722 | 0.0 |
| release_ready | 0 | 79 | 3764 | 0.0 |

Historical PASS rows requiring revalidation: **355**. Implementation candidates: 468; test candidates: 468.

W18 has 15 scenario dimensions per action. Applicability is conservative, including undo/persistence until the actual action effects have been reviewed. Printer acceptance remains external. No source-only result proves an installed build or a real-world corpus.

Regenerate with `python tools/master_requirements_v2.py`; validate the checked-in inventory with `python tools/master_requirements_v2.py --check`. JSON carries every required field, source hash, historical link, scenario and evidence dimension.

| Requirement | Category | Status | Description | Source |
|---|---|---|---|---|
| F1-001 | historical | PARTIAL | All active requirement sources are versioned and reconciled without silent deletion | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/0) |
| F1-002 | historical | PARTIAL | Canonical product authorities remain unique and no parallel Viewer/Project/BOM engines are introduced | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/1) |
| F1-003 | historical | PARTIAL | IFC geometry uses a bounded persistent process worker pool with recovery and clean shutdown | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/2) |
| F1-004 | historical | PARTIAL | Geometry priority is dynamic, viewport-aware, hysteretic and starvation-safe | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/3) |
| F1-005 | historical | PARTIAL | MeshCache V2 persists complete mesh payloads atomically and rejects corruption | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/4) |
| F1-006 | historical | PARTIAL | Scene uploads are generation-safe and bounded by per-frame time budgets | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/5) |
| F1-007 | historical | PARTIAL | ViewerPerformanceGovernor controls interaction, recovery and idle rendering quality including MSAA | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/6) |
| F1-008 | historical | PARTIAL | Packaged cold, warm and same-session metrics include first usable, exact milestones, p95/p99 and memory/process counts | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/7) |
| F1-009 | historical | PARTIAL | A real ten-minute OpenGL Viewer soak proves bounded actors, workers and memory | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/8) |
| F1-010 | historical | PARTIAL | Viewer interaction, selection, visibility, section, measurement and saved-view behavior remains functional | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/9) |
| F1-011 | historical | PARTIAL | Unified intake handles IFC, STEP, NC1, Trusted PDF, External PDF and project packages fail-closed | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/10) |
| F1-012 | historical | PARTIAL | Project state and user preferences are versioned, separated and recover safely | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/11) |
| F1-013 | historical | PARTIAL | The exact primary navigation is Project, Viewer, Productie, Controle, Uitvoer | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/12) |
| F1-014 | historical | PARTIAL | V5.2 design system is light-first with a dark preference smoke path and yellow whole-object selection | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/13) |
| F1-015 | historical | PARTIAL | Owned controls use stable ui_test_id identity and central control/icon registries | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/14) |
| F2-001 | historical | PARTIAL | BOM is the immutable quantity truth with exact reconciliation and full traceability | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/15) |
| F2-002 | historical | PARTIAL | BOM and Machines joins production state through canonical IDs | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/16) |
| F2-003 | historical | PARTIAL | Machine routing has one versioned AUTO/MANUAL assignment authority | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/17) |
| F2-004 | historical | PARTIAL | Invalid machine overrides remain REVIEW/BLOCKED and never authorize transfer | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/18) |
| F2-005 | historical | PARTIAL | Machine library validates ranges, tools, operations, priorities and active state | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/19) |
| F2-006 | historical | PARTIAL | Workbench remains the single transactional write path with rollback and undo/redo | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/20) |
| F2-007 | historical | PARTIAL | Canonical rebuild and roundtrip invalidate stale derivatives | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/21) |
| F2-008 | historical | PARTIAL | Manufacturing Geometry Interpreter V3 full V2 gap closure with independent compound proof | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/22) |
| F2-009 | historical | PARTIAL | Interpreter exact READY requires two-way BREP proof and false READY remains zero | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/23) |
| F2-010 | historical | PARTIAL | Existing faces, contact, scribing, identification, capability and neutral-job chain remains authoritative | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/24) |
| F2-011 | historical | PARTIAL | Profile nesting preserves machine/tool/stock/remnant constraints and deterministic proof | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/25) |
| F2-012 | historical | PARTIAL | Plate nesting supports polygon geometry, holes, grain, rotations, remnants, locks and exact validation | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/26) |
| F2-013 | historical | PARTIAL | Converter capability registry blocks every feature not proven by serializer and reimport comparator | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/27) |
| F2-014 | historical | PARTIAL | Productie screens and controls operate on the same canonical project and selection | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/28) |
| F2-015 | historical | PARTIAL | Routing, nesting and production state survive save and reopen | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/29) |
| F3-001 | historical | PARTIAL | One production drawing engine emits vector geometry, dimensions, annotations and title blocks | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/30) |
| F3-002 | historical | PARTIAL | Production drawing PDF remains sharp at 800 percent and is not a full-page raster | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/31) |
| F3-003 | historical | PARTIAL | Drawing linter blocks incomplete, stale, clipped or raster-only production pages | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/32) |
| F3-004 | historical | PARTIAL | Trusted PDF payload and hash verification fails closed on tamper | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/33) |
| F3-005 | historical | PARTIAL | External PDF remains evidence/confidence gated and REVIEW_REQUIRED until proven | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/34) |
| F3-006 | historical | PARTIAL | One DocumentOutputService owns preview, print and batch output | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/35) |
| F3-007 | historical | PARTIAL | Ctrl+P opens the context Print Center and printer failure is fail-closed | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/36) |
| F3-008 | historical | PARTIAL | Controle exposes validation, compare, manufacturability, geometry, evidence and PDF review | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/37) |
| F3-009 | historical | PARTIAL | Problem Center reports blockers, errors and warnings without false green | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/38) |
| F3-010 | historical | PARTIAL | Quality inspection supports plans, measurements, NCR, rework, reinspection and release blocking | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/39) |
| F3-011 | historical | PARTIAL | Planning owns resources, work centers, shifts, requirements, orders and scheduled operations | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/40) |
| F3-012 | historical | PARTIAL | Finite-capacity scheduling respects availability, maintenance, material, priority and due dates | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/41) |
| F3-013 | historical | PARTIAL | Shopfloor transitions and quality hooks remain bounded and auditable | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/42) |
| F3-014 | historical | PARTIAL | Export uses Scope to Formats to Preflight to Generate to Verify to Package without scope broadening | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/43) |
| F3-015 | historical | PARTIAL | Readiness joins geometry, manufacturing, routing, nesting, drawing, quality and planning gates | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/44) |
| F3-016 | historical | PARTIAL | All 25 reference and 6 support surfaces are functional in the real Qt runtime | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/45) |
| F4-001 | historical | PARTIAL | Dynamic full acceptance is generated from this master traceability | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/46) |
| F4-002 | historical | PARTIAL | Runtime owned-control scan proves no missing, duplicate, dead or wrong-handler controls | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/47) |
| F4-003 | historical | PARTIAL | Visual acceptance covers required resolutions and DPI with light primary and dark smoke | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/48) |
| F4-004 | historical | PARTIAL | Full IFC, STEP, NC1, Trusted PDF and External PDF workflows are tested end to end | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/49) |
| F4-005 | historical | PARTIAL | Negative file, cache, worker, cancellation, stale-state and capacity paths fail closed | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/50) |
| F4-006 | historical | PARTIAL | Stress suite proves bounded workspace, selection, camera, save, import/export and optimization behavior | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/51) |
| F4-007 | historical | PARTIAL | Final Viewer cold/warm/same-session, interaction and resource metrics are packaged evidence | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/52) |
| F4-008 | historical | PARTIAL | One-folder black-box runtime works without developer Python PATH | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/53) |
| F4-009 | historical | PARTIAL | Fresh portable black-box runtime works without developer Python PATH | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/54) |
| F4-010 | historical | PARTIAL | Fresh installer black-box runtime works and preserves file associations | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/55) |
| F4-011 | historical | PARTIAL | Source zip, git bundle, checksums, SBOM and manifests bind to one exact source SHA | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/56) |
| F4-012 | historical | PARTIAL | Required FAIL, BLOCKED and NOT_TESTED counts are zero with false green zero | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/57) |
| F4-013 | historical | PARTIAL | Physical machine transfer remains blocked pending external qualification | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/58) |
| F4-014 | historical | PARTIAL | Release evidence and binaries are rebuilt after every code change and name the exact SHA | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/59) |
| UI-SCREEN-01 | historical | PARTIAL | Runtime surface 01 Start / Inlezen matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/60) |
| UI-SCREEN-02 | historical | PARTIAL | Runtime surface 02 Projectoverzicht matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/61) |
| UI-SCREEN-03 | historical | PARTIAL | Runtime surface 03 Projectstructuur matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/62) |
| UI-SCREEN-04 | historical | PARTIAL | Runtime surface 04 Profielen & Materialen matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/63) |
| UI-SCREEN-05 | historical | PARTIAL | Runtime surface 05 3D Viewer matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/64) |
| UI-SCREEN-06 | historical | PARTIAL | Runtime surface 06 Selectie & Context matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/65) |
| UI-SCREEN-07 | historical | PARTIAL | Runtime surface 07 Weergave & Meten matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/66) |
| UI-SCREEN-08 | historical | PARTIAL | Runtime surface 08 Doorsnede & Isoleren matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/67) |
| UI-SCREEN-09 | historical | PARTIAL | Runtime surface 09 Laadstatus & Prestaties matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/68) |
| UI-SCREEN-10 | historical | PARTIAL | Runtime surface 10 Projectreviews matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/69) |
| UI-SCREEN-11 | historical | PARTIAL | Runtime surface 11 BOM & Machines — BOM matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/70) |
| UI-SCREEN-12 | historical | PARTIAL | Runtime surface 12 Machine-indeling — Automatisch matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/71) |
| UI-SCREEN-13 | historical | PARTIAL | Runtime surface 13 Machine-indeling — Handmatig matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/72) |
| UI-SCREEN-14 | historical | PARTIAL | Runtime surface 14 Optimalisatie — Profile Nesting matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/73) |
| UI-SCREEN-15 | historical | PARTIAL | Runtime surface 15 Optimalisatie — Plate Nesting matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/74) |
| UI-SCREEN-16 | historical | PARTIAL | Runtime surface 16 Bewerken — Workbench matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/75) |
| UI-SCREEN-17 | historical | PARTIAL | Runtime surface 17 Scribing matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/76) |
| UI-SCREEN-18 | historical | PARTIAL | Runtime surface 18 Converteren matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/77) |
| UI-SCREEN-19 | historical | PARTIAL | Runtime surface 19 Tekeningen / PDF matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/78) |
| UI-SCREEN-20 | historical | PARTIAL | Runtime surface 20 Afdrukken / Print Center matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/79) |
| UI-SCREEN-21 | historical | PARTIAL | Runtime surface 21 Validatie matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/80) |
| UI-SCREEN-22 | historical | PARTIAL | Runtime surface 22 Revisies / Compare matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/81) |
| UI-SCREEN-23 | historical | PARTIAL | Runtime surface 23 Maakbaarheid matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/82) |
| UI-SCREEN-24 | historical | PARTIAL | Runtime surface 24 Export Center matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/83) |
| UI-SCREEN-25 | historical | PARTIAL | Runtime surface 25 Rapport / Pakket matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/84) |
| UI-SCREEN-26 | historical | PARTIAL | Runtime surface 26 Machinebibliotheek matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/85) |
| UI-SCREEN-27 | historical | PARTIAL | Runtime surface 27 PDF/Print & Tekeningtemplates matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/86) |
| UI-SCREEN-28 | historical | PARTIAL | Runtime surface 28 Activity Center matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/87) |
| UI-SCREEN-29 | historical | PARTIAL | Runtime surface 29 Problem / Status Center matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/88) |
| UI-SCREEN-30 | historical | PARTIAL | Runtime surface 30 Los Viewer-venster matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/89) |
| UI-SCREEN-31 | historical | PARTIAL | Runtime surface 31 Snelactie / Command Palette matches its active structural and functional contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/90) |
| UI-CONTROL-nav_project | historical | PARTIAL | Control nav_project (Project) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/91) |
| UI-CONTROL-nav_viewer | historical | PARTIAL | Control nav_viewer (Viewer) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/92) |
| UI-CONTROL-nav_productie | historical | PARTIAL | Control nav_productie (Productie) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/93) |
| UI-CONTROL-nav_controle | historical | PARTIAL | Control nav_controle (Controle) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/94) |
| UI-CONTROL-nav_uitvoer | historical | PARTIAL | Control nav_uitvoer (Uitvoer) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/95) |
| UI-CONTROL-global_undo | historical | PARTIAL | Control global_undo (Ongedaan maken) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/96) |
| UI-CONTROL-global_redo | historical | PARTIAL | Control global_redo (Opnieuw) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/97) |
| UI-CONTROL-global_activity | historical | PARTIAL | Control global_activity (Activiteit) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/98) |
| UI-CONTROL-global_problems | historical | PARTIAL | Control global_problems (Problemen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/99) |
| UI-CONTROL-global_settings | historical | PARTIAL | Control global_settings (Instellingen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/100) |
| UI-CONTROL-global_command | historical | PARTIAL | Control global_command (Snelactie) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/101) |
| UI-CONTROL-global_print | historical | PARTIAL | Control global_print (Afdrukken) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/102) |
| UI-CONTROL-import_dropzone | historical | PARTIAL | Control import_dropzone (Sleep bestanden hierheen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/103) |
| UI-CONTROL-btn_open_file | historical | PARTIAL | Control btn_open_file (Bestand openen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/104) |
| UI-CONTROL-btn_open_folder | historical | PARTIAL | Control btn_open_folder (Map openen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/105) |
| UI-CONTROL-btn_open_multiple | historical | PARTIAL | Control btn_open_multiple (Meerdere bestanden) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/106) |
| UI-CONTROL-btn_import_load | historical | PARTIAL | Control btn_import_load (Inladen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/107) |
| UI-CONTROL-btn_import_cancel | historical | PARTIAL | Control btn_import_cancel (Annuleren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/108) |
| UI-CONTROL-recent_projects | historical | PARTIAL | Control recent_projects (Recente projecten) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/109) |
| UI-CONTROL-import_options | historical | PARTIAL | Control import_options (Importopties) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/110) |
| UI-CONTROL-btn_project_open_viewer | historical | PARTIAL | Control btn_project_open_viewer (Open Viewer) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/111) |
| UI-CONTROL-btn_project_properties | historical | PARTIAL | Control btn_project_properties (Projectgegevens) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/112) |
| UI-CONTROL-btn_project_save | historical | PARTIAL | Control btn_project_save (Opslaan) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/113) |
| UI-CONTROL-btn_project_save_as | historical | PARTIAL | Control btn_project_save_as (Opslaan als) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/114) |
| UI-CONTROL-btn_project_revisions | historical | PARTIAL | Control btn_project_revisions (Revisies) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/115) |
| UI-CONTROL-btn_project_validate | historical | PARTIAL | Control btn_project_validate (Controleren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/116) |
| UI-CONTROL-tree_project | historical | PARTIAL | Control tree_project (Projectstructuur) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/117) |
| UI-CONTROL-txt_tree_search | historical | PARTIAL | Control txt_tree_search (Zoeken) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/118) |
| UI-CONTROL-btn_tree_expand | historical | PARTIAL | Control btn_tree_expand (Alles uitklappen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/119) |
| UI-CONTROL-btn_tree_collapse | historical | PARTIAL | Control btn_tree_collapse (Alles inklappen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/120) |
| UI-CONTROL-btn_tree_show_viewer | historical | PARTIAL | Control btn_tree_show_viewer (Toon in Viewer) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/121) |
| UI-CONTROL-btn_tree_isolate | historical | PARTIAL | Control btn_tree_isolate (Isoleren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/122) |
| UI-CONTROL-btn_tree_properties | historical | PARTIAL | Control btn_tree_properties (Eigenschappen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/123) |
| UI-CONTROL-tab_profiles | historical | PARTIAL | Control tab_profiles (Profielen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/124) |
| UI-CONTROL-tab_materials | historical | PARTIAL | Control tab_materials (Materialen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/125) |
| UI-CONTROL-txt_pm_search | historical | PARTIAL | Control txt_pm_search (Zoeken) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/126) |
| UI-CONTROL-btn_pm_select_viewer | historical | PARTIAL | Control btn_pm_select_viewer (Selecteer in Viewer) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/127) |
| UI-CONTROL-btn_pm_export | historical | PARTIAL | Control btn_pm_export (Exporteren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/128) |
| UI-CONTROL-viewer_canvas | historical | PARTIAL | Control viewer_canvas (3D Viewer) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/129) |
| UI-CONTROL-cmb_selection_level | historical | PARTIAL | Control cmb_selection_level (Selecteren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/130) |
| UI-CONTROL-btn_fit_all | historical | PARTIAL | Control btn_fit_all (Alles passend) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/131) |
| UI-CONTROL-btn_fit_selected | historical | PARTIAL | Control btn_fit_selected (Selectie passend) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/132) |
| UI-CONTROL-btn_view_front | historical | PARTIAL | Control btn_view_front (Voor) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/133) |
| UI-CONTROL-btn_view_top | historical | PARTIAL | Control btn_view_top (Boven) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/134) |
| UI-CONTROL-btn_view_iso | historical | PARTIAL | Control btn_view_iso (ISO) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/135) |
| UI-CONTROL-btn_hide | historical | PARTIAL | Control btn_hide (Verbergen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/136) |
| UI-CONTROL-btn_show_all | historical | PARTIAL | Control btn_show_all (Alles tonen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/137) |
| UI-CONTROL-btn_isolate | historical | PARTIAL | Control btn_isolate (Isoleren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/138) |
| UI-CONTROL-btn_ghost | historical | PARTIAL | Control btn_ghost (Ghost) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/139) |
| UI-CONTROL-btn_measure | historical | PARTIAL | Control btn_measure (Meten) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/140) |
| UI-CONTROL-btn_section | historical | PARTIAL | Control btn_section (Doorsnede) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/141) |
| UI-CONTROL-btn_detach_viewer | historical | PARTIAL | Control btn_detach_viewer (Los venster) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/142) |
| UI-CONTROL-btn_ctx_edit | historical | PARTIAL | Control btn_ctx_edit (Bewerken) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/143) |
| UI-CONTROL-btn_ctx_drawing | historical | PARTIAL | Control btn_ctx_drawing (Tekening) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/144) |
| UI-CONTROL-btn_ctx_machine | historical | PARTIAL | Control btn_ctx_machine (Machine) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/145) |
| UI-CONTROL-btn_ctx_optimize | historical | PARTIAL | Control btn_ctx_optimize (Optimaliseren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/146) |
| UI-CONTROL-btn_ctx_print | historical | PARTIAL | Control btn_ctx_print (Afdrukken) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/147) |
| UI-CONTROL-btn_ctx_more | historical | PARTIAL | Control btn_ctx_more (Meer) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/148) |
| UI-CONTROL-cmb_render_mode | historical | PARTIAL | Control cmb_render_mode (Weergave) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/149) |
| UI-CONTROL-cmb_color_mode | historical | PARTIAL | Control cmb_color_mode (Kleuren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/150) |
| UI-CONTROL-sld_transparency | historical | PARTIAL | Control sld_transparency (Transparantie) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/151) |
| UI-CONTROL-btn_measure_distance | historical | PARTIAL | Control btn_measure_distance (Afstand) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/152) |
| UI-CONTROL-btn_measure_angle | historical | PARTIAL | Control btn_measure_angle (Hoek) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/153) |
| UI-CONTROL-btn_measure_radius | historical | PARTIAL | Control btn_measure_radius (Radius) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/154) |
| UI-CONTROL-btn_measure_coordinates | historical | PARTIAL | Control btn_measure_coordinates (Coördinaten) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/155) |
| UI-CONTROL-btn_measure_clear | historical | PARTIAL | Control btn_measure_clear (Metingen wissen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/156) |
| UI-CONTROL-btn_section_new | historical | PARTIAL | Control btn_section_new (Nieuwe doorsnede) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/157) |
| UI-CONTROL-btn_section_from_face | historical | PARTIAL | Control btn_section_from_face (Vanaf vlak) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/158) |
| UI-CONTROL-btn_section_flip | historical | PARTIAL | Control btn_section_flip (Omkeren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/159) |
| UI-CONTROL-btn_section_toggle | historical | PARTIAL | Control btn_section_toggle (Aan/uit) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/160) |
| UI-CONTROL-btn_section_remove | historical | PARTIAL | Control btn_section_remove (Verwijderen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/161) |
| UI-CONTROL-btn_clip_box | historical | PARTIAL | Control btn_clip_box (Clipbox) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/162) |
| UI-CONTROL-btn_visibility_restore | historical | PARTIAL | Control btn_visibility_restore (Weergave herstellen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/163) |
| UI-CONTROL-cmb_performance_preset | historical | PARTIAL | Control cmb_performance_preset (Prestaties) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/164) |
| UI-CONTROL-btn_load_cancel | historical | PARTIAL | Control btn_load_cancel (Laden annuleren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/165) |
| UI-CONTROL-btn_load_retry | historical | PARTIAL | Control btn_load_retry (Opnieuw proberen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/166) |
| UI-CONTROL-btn_perf_details | historical | PARTIAL | Control btn_perf_details (Details) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/167) |
| UI-CONTROL-progress_geometry | historical | PARTIAL | Control progress_geometry (Geometrie) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/168) |
| UI-CONTROL-btn_view_create | historical | PARTIAL | Control btn_view_create (View opslaan) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/169) |
| UI-CONTROL-btn_view_update | historical | PARTIAL | Control btn_view_update (View bijwerken) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/170) |
| UI-CONTROL-btn_view_rename | historical | PARTIAL | Control btn_view_rename (Naam wijzigen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/171) |
| UI-CONTROL-btn_view_delete | historical | PARTIAL | Control btn_view_delete (Verwijderen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/172) |
| UI-CONTROL-btn_issue_new | historical | PARTIAL | Control btn_issue_new (Nieuw reviewpunt) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/173) |
| UI-CONTROL-btn_issue_open | historical | PARTIAL | Control btn_issue_open (Openen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/174) |
| UI-CONTROL-tab_bom | historical | PARTIAL | Control tab_bom (BOM) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/175) |
| UI-CONTROL-tab_machine_assignment | historical | PARTIAL | Control tab_machine_assignment (Machine-indeling) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/176) |
| UI-CONTROL-tab_optimization | historical | PARTIAL | Control tab_optimization (Optimalisatie) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/177) |
| UI-CONTROL-txt_bom_search | historical | PARTIAL | Control txt_bom_search (Zoeken) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/178) |
| UI-CONTROL-btn_bom_filter | historical | PARTIAL | Control btn_bom_filter (Filter) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/179) |
| UI-CONTROL-btn_bom_group | historical | PARTIAL | Control btn_bom_group (Groeperen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/180) |
| UI-CONTROL-btn_bom_columns | historical | PARTIAL | Control btn_bom_columns (Kolommen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/181) |
| UI-CONTROL-btn_bom_edit | historical | PARTIAL | Control btn_bom_edit (Bewerken) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/182) |
| UI-CONTROL-btn_bom_drawing | historical | PARTIAL | Control btn_bom_drawing (Tekening) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/183) |
| UI-CONTROL-btn_bom_machine | historical | PARTIAL | Control btn_bom_machine (Machine) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/184) |
| UI-CONTROL-btn_bom_optimize | historical | PARTIAL | Control btn_bom_optimize (Optimaliseren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/185) |
| UI-CONTROL-btn_bom_print | historical | PARTIAL | Control btn_bom_print (Afdrukken) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/186) |
| UI-CONTROL-btn_bom_more | historical | PARTIAL | Control btn_bom_more (Meer) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/187) |
| UI-CONTROL-btn_bom_export | historical | PARTIAL | Control btn_bom_export (Exporteren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/188) |
| UI-CONTROL-btn_route_recompute | historical | PARTIAL | Control btn_route_recompute (Opnieuw indelen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/189) |
| UI-CONTROL-btn_route_accept_all | historical | PARTIAL | Control btn_route_accept_all (Voorstellen toepassen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/190) |
| UI-CONTROL-btn_route_show_reason | historical | PARTIAL | Control btn_route_show_reason (Toon reden) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/191) |
| UI-CONTROL-cmb_route_machine_filter | historical | PARTIAL | Control cmb_route_machine_filter (Machine) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/192) |
| UI-CONTROL-cmb_route_status_filter | historical | PARTIAL | Control cmb_route_status_filter (Status) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/193) |
| UI-CONTROL-btn_route_manual | historical | PARTIAL | Control btn_route_manual (Handmatig wijzigen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/194) |
| UI-CONTROL-cmb_manual_machine | historical | PARTIAL | Control cmb_manual_machine (Machine) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/195) |
| UI-CONTROL-btn_manual_assign | historical | PARTIAL | Control btn_manual_assign (Toewijzen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/196) |
| UI-CONTROL-btn_manual_reset_auto | historical | PARTIAL | Control btn_manual_reset_auto (Terug naar automatisch) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/197) |
| UI-CONTROL-btn_manual_validate | historical | PARTIAL | Control btn_manual_validate (Controleren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/198) |
| UI-CONTROL-chk_allow_review_override | historical | PARTIAL | Control chk_allow_review_override (Alleen als reviewoverride opslaan) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/199) |
| UI-CONTROL-btn_profile_optimize | historical | PARTIAL | Control btn_profile_optimize (Optimaliseren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/200) |
| UI-CONTROL-btn_profile_compare | historical | PARTIAL | Control btn_profile_compare (Scenario's vergelijken) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/201) |
| UI-CONTROL-btn_profile_validate | historical | PARTIAL | Control btn_profile_validate (Controleren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/202) |
| UI-CONTROL-btn_profile_accept | historical | PARTIAL | Control btn_profile_accept (Accepteren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/203) |
| UI-CONTROL-btn_profile_reserve | historical | PARTIAL | Control btn_profile_reserve (Reserveren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/204) |
| UI-CONTROL-btn_profile_release | historical | PARTIAL | Control btn_profile_release (Reservering vrijgeven) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/205) |
| UI-CONTROL-btn_profile_lock | historical | PARTIAL | Control btn_profile_lock (Vergrendelen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/206) |
| UI-CONTROL-btn_profile_unlock | historical | PARTIAL | Control btn_profile_unlock (Ontgrendelen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/207) |
| UI-CONTROL-btn_profile_partial | historical | PARTIAL | Control btn_profile_partial (Gedeeltelijk heroptimaliseren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/208) |
| UI-CONTROL-btn_profile_report | historical | PARTIAL | Control btn_profile_report (Rapport) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/209) |
| UI-CONTROL-btn_plate_optimize | historical | PARTIAL | Control btn_plate_optimize (Optimaliseren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/210) |
| UI-CONTROL-btn_plate_rotate | historical | PARTIAL | Control btn_plate_rotate (Roteren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/211) |
| UI-CONTROL-btn_plate_lock | historical | PARTIAL | Control btn_plate_lock (Vergrendelen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/212) |
| UI-CONTROL-btn_plate_unlock | historical | PARTIAL | Control btn_plate_unlock (Ontgrendelen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/213) |
| UI-CONTROL-btn_plate_validate | historical | PARTIAL | Control btn_plate_validate (Controleren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/214) |
| UI-CONTROL-btn_plate_accept | historical | PARTIAL | Control btn_plate_accept (Accepteren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/215) |
| UI-CONTROL-btn_plate_report | historical | PARTIAL | Control btn_plate_report (Rapport) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/216) |
| UI-CONTROL-btn_wb_apply | historical | PARTIAL | Control btn_wb_apply (Toepassen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/217) |
| UI-CONTROL-btn_wb_validate | historical | PARTIAL | Control btn_wb_validate (Controleren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/218) |
| UI-CONTROL-btn_wb_cancel | historical | PARTIAL | Control btn_wb_cancel (Annuleren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/219) |
| UI-CONTROL-btn_wb_undo | historical | PARTIAL | Control btn_wb_undo (Ongedaan maken) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/220) |
| UI-CONTROL-btn_wb_redo | historical | PARTIAL | Control btn_wb_redo (Opnieuw) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/221) |
| UI-CONTROL-btn_wb_rebuild | historical | PARTIAL | Control btn_wb_rebuild (Opnieuw opbouwen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/222) |
| UI-CONTROL-tab_scribe_marks | historical | PARTIAL | Control tab_scribe_marks (Markeringen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/223) |
| UI-CONTROL-tab_scribe_holes | historical | PARTIAL | Control tab_scribe_holes (Gatreferenties) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/224) |
| UI-CONTROL-tab_scribe_id | historical | PARTIAL | Control tab_scribe_id (Identificatie) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/225) |
| UI-CONTROL-btn_scribe_generate | historical | PARTIAL | Control btn_scribe_generate (Genereren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/226) |
| UI-CONTROL-btn_scribe_validate | historical | PARTIAL | Control btn_scribe_validate (Controleren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/227) |
| UI-CONTROL-btn_scribe_apply | historical | PARTIAL | Control btn_scribe_apply (Toepassen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/228) |
| UI-CONTROL-btn_scribe_clear | historical | PARTIAL | Control btn_scribe_clear (Wissen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/229) |
| UI-CONTROL-cmb_convert_source | historical | PARTIAL | Control cmb_convert_source (Bron) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/230) |
| UI-CONTROL-cmb_convert_target | historical | PARTIAL | Control cmb_convert_target (Doel) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/231) |
| UI-CONTROL-cmb_convert_scope | historical | PARTIAL | Control cmb_convert_scope (Scope) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/232) |
| UI-CONTROL-btn_convert_check | historical | PARTIAL | Control btn_convert_check (Controleren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/233) |
| UI-CONTROL-btn_convert_run | historical | PARTIAL | Control btn_convert_run (Converteren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/234) |
| UI-CONTROL-chk_convert_reimport | historical | PARTIAL | Control chk_convert_reimport (Resultaat opnieuw inlezen en vergelijken) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/235) |
| UI-CONTROL-btn_convert_output | historical | PARTIAL | Control btn_convert_output (Doelmap) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/236) |
| UI-CONTROL-cmb_drawing_type | historical | PARTIAL | Control cmb_drawing_type (Type) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/237) |
| UI-CONTROL-cmb_paper_size | historical | PARTIAL | Control cmb_paper_size (Papier) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/238) |
| UI-CONTROL-cmb_orientation | historical | PARTIAL | Control cmb_orientation (Oriëntatie) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/239) |
| UI-CONTROL-cmb_scale | historical | PARTIAL | Control cmb_scale (Schaal) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/240) |
| UI-CONTROL-chk_view_front | historical | PARTIAL | Control chk_view_front (Voor) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/241) |
| UI-CONTROL-chk_view_top | historical | PARTIAL | Control chk_view_top (Boven) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/242) |
| UI-CONTROL-chk_view_right | historical | PARTIAL | Control chk_view_right (Rechts) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/243) |
| UI-CONTROL-chk_view_iso | historical | PARTIAL | Control chk_view_iso (ISO) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/244) |
| UI-CONTROL-btn_drawing_auto_layout | historical | PARTIAL | Control btn_drawing_auto_layout (Auto indelen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/245) |
| UI-CONTROL-btn_drawing_generate | historical | PARTIAL | Control btn_drawing_generate (Genereren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/246) |
| UI-CONTROL-btn_drawing_edit | historical | PARTIAL | Control btn_drawing_edit (Bewerken) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/247) |
| UI-CONTROL-btn_drawing_print | historical | PARTIAL | Control btn_drawing_print (Afdrukken) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/248) |
| UI-CONTROL-btn_drawing_export_pdf | historical | PARTIAL | Control btn_drawing_export_pdf (PDF opslaan) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/249) |
| UI-CONTROL-cmb_print_content | historical | PARTIAL | Control cmb_print_content (Inhoud) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/250) |
| UI-CONTROL-cmb_print_scope | historical | PARTIAL | Control cmb_print_scope (Scope) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/251) |
| UI-CONTROL-cmb_printer | historical | PARTIAL | Control cmb_printer (Printer) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/252) |
| UI-CONTROL-cmb_print_paper | historical | PARTIAL | Control cmb_print_paper (Papier) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/253) |
| UI-CONTROL-cmb_print_orientation | historical | PARTIAL | Control cmb_print_orientation (Oriëntatie) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/254) |
| UI-CONTROL-spin_print_copies | historical | PARTIAL | Control spin_print_copies (Aantal) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/255) |
| UI-CONTROL-btn_print_preview | historical | PARTIAL | Control btn_print_preview (Voorbeeld) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/256) |
| UI-CONTROL-btn_print_run | historical | PARTIAL | Control btn_print_run (Afdrukken) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/257) |
| UI-CONTROL-btn_print_pdf | historical | PARTIAL | Control btn_print_pdf (PDF opslaan) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/258) |
| UI-CONTROL-btn_print_batch | historical | PARTIAL | Control btn_print_batch (Batch) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/259) |
| UI-CONTROL-btn_validation_run | historical | PARTIAL | Control btn_validation_run (Opnieuw controleren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/260) |
| UI-CONTROL-cmb_validation_severity | historical | PARTIAL | Control cmb_validation_severity (Ernst) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/261) |
| UI-CONTROL-cmb_validation_domain | historical | PARTIAL | Control cmb_validation_domain (Onderdeel) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/262) |
| UI-CONTROL-btn_validation_show | historical | PARTIAL | Control btn_validation_show (Toon object) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/263) |
| UI-CONTROL-btn_validation_open | historical | PARTIAL | Control btn_validation_open (Open oplossen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/264) |
| UI-CONTROL-btn_validation_evidence | historical | PARTIAL | Control btn_validation_evidence (Evidence) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/265) |
| UI-CONTROL-cmb_compare_a | historical | PARTIAL | Control cmb_compare_a (Revisie A) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/266) |
| UI-CONTROL-cmb_compare_b | historical | PARTIAL | Control cmb_compare_b (Revisie B) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/267) |
| UI-CONTROL-btn_compare_run | historical | PARTIAL | Control btn_compare_run (Vergelijken) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/268) |
| UI-CONTROL-chk_compare_added | historical | PARTIAL | Control chk_compare_added (Toegevoegd) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/269) |
| UI-CONTROL-chk_compare_removed | historical | PARTIAL | Control chk_compare_removed (Verwijderd) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/270) |
| UI-CONTROL-chk_compare_changed | historical | PARTIAL | Control chk_compare_changed (Gewijzigd) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/271) |
| UI-CONTROL-chk_compare_same | historical | PARTIAL | Control chk_compare_same (Ongewijzigd) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/272) |
| UI-CONTROL-btn_compare_issue | historical | PARTIAL | Control btn_compare_issue (Reviewpunt maken) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/273) |
| UI-CONTROL-cmb_dfm_machine | historical | PARTIAL | Control cmb_dfm_machine (Machine) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/274) |
| UI-CONTROL-btn_dfm_run | historical | PARTIAL | Control btn_dfm_run (Controleren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/275) |
| UI-CONTROL-btn_dfm_show | historical | PARTIAL | Control btn_dfm_show (Toon probleem) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/276) |
| UI-CONTROL-btn_dfm_machine_route | historical | PARTIAL | Control btn_dfm_machine_route (Andere machine) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/277) |
| UI-CONTROL-btn_dfm_evidence | historical | PARTIAL | Control btn_dfm_evidence (Details) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/278) |
| UI-CONTROL-cmb_export_scope | historical | PARTIAL | Control cmb_export_scope (Scope) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/279) |
| UI-CONTROL-btn_export_formats | historical | PARTIAL | Control btn_export_formats (Formaten) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/280) |
| UI-CONTROL-btn_export_preflight | historical | PARTIAL | Control btn_export_preflight (Controleren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/281) |
| UI-CONTROL-btn_export_generate | historical | PARTIAL | Control btn_export_generate (Genereren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/282) |
| UI-CONTROL-btn_export_verify | historical | PARTIAL | Control btn_export_verify (Verifiëren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/283) |
| UI-CONTROL-btn_export_package | historical | PARTIAL | Control btn_export_package (Pakket maken) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/284) |
| UI-CONTROL-btn_export_folder | historical | PARTIAL | Control btn_export_folder (Doelmap) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/285) |
| UI-CONTROL-btn_report_refresh | historical | PARTIAL | Control btn_report_refresh (Status vernieuwen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/286) |
| UI-CONTROL-btn_report_open_blocker | historical | PARTIAL | Control btn_report_open_blocker (Open blokkade) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/287) |
| UI-CONTROL-btn_report_print | historical | PARTIAL | Control btn_report_print (Rapport afdrukken) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/288) |
| UI-CONTROL-btn_report_export | historical | PARTIAL | Control btn_report_export (Rapport opslaan) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/289) |
| UI-CONTROL-btn_report_package | historical | PARTIAL | Control btn_report_package (Productiepakket) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/290) |
| UI-CONTROL-btn_machine_new | historical | PARTIAL | Control btn_machine_new (Nieuwe machine) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/291) |
| UI-CONTROL-btn_machine_duplicate | historical | PARTIAL | Control btn_machine_duplicate (Dupliceren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/292) |
| UI-CONTROL-btn_machine_import | historical | PARTIAL | Control btn_machine_import (Importeren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/293) |
| UI-CONTROL-btn_machine_export | historical | PARTIAL | Control btn_machine_export (Exporteren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/294) |
| UI-CONTROL-btn_machine_test | historical | PARTIAL | Control btn_machine_test (Configuratie testen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/295) |
| UI-CONTROL-btn_machine_save | historical | PARTIAL | Control btn_machine_save (Opslaan) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/296) |
| UI-CONTROL-btn_machine_cancel | historical | PARTIAL | Control btn_machine_cancel (Annuleren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/297) |
| UI-CONTROL-btn_template_new | historical | PARTIAL | Control btn_template_new (Nieuw) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/298) |
| UI-CONTROL-btn_template_duplicate | historical | PARTIAL | Control btn_template_duplicate (Dupliceren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/299) |
| UI-CONTROL-btn_template_logo | historical | PARTIAL | Control btn_template_logo (Logo kiezen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/300) |
| UI-CONTROL-btn_template_preview | historical | PARTIAL | Control btn_template_preview (Voorbeeld) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/301) |
| UI-CONTROL-btn_template_save | historical | PARTIAL | Control btn_template_save (Opslaan) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/302) |
| UI-CONTROL-btn_template_reset | historical | PARTIAL | Control btn_template_reset (Standaard herstellen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/303) |
| UI-CONTROL-activity_jobs | historical | PARTIAL | Control activity_jobs (Activiteiten) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/304) |
| UI-CONTROL-btn_activity_cancel | historical | PARTIAL | Control btn_activity_cancel (Annuleren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/305) |
| UI-CONTROL-btn_activity_open | historical | PARTIAL | Control btn_activity_open (Openen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/306) |
| UI-CONTROL-btn_activity_clear_done | historical | PARTIAL | Control btn_activity_clear_done (Gereed wissen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/307) |
| UI-CONTROL-problem_list | historical | PARTIAL | Control problem_list (Problemen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/308) |
| UI-CONTROL-btn_problem_open | historical | PARTIAL | Control btn_problem_open (Openen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/309) |
| UI-CONTROL-btn_problem_show | historical | PARTIAL | Control btn_problem_show (Toon object) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/310) |
| UI-CONTROL-btn_problem_rerun | historical | PARTIAL | Control btn_problem_rerun (Opnieuw controleren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/311) |
| UI-CONTROL-detached_viewer_canvas | historical | PARTIAL | Control detached_viewer_canvas (Viewer) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/312) |
| UI-CONTROL-btn_detached_attach | historical | PARTIAL | Control btn_detached_attach (Terugplaatsen) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/313) |
| UI-CONTROL-txt_command_search | historical | PARTIAL | Control txt_command_search (Zoek actie) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/314) |
| UI-CONTROL-list_commands | historical | PARTIAL | Control list_commands (Acties) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/315) |
| UI-CONTROL-btn_command_execute | historical | PARTIAL | Control btn_command_execute (Uitvoeren) is present, uniquely owned and invokes its declared contract | requirements/MASTER_REQUIREMENT_TRACEABILITY.json (/requirements/316) |
| MGI3-MGI-V3-DOD-01 | manufacturing_machines | PARTIAL | Current canonical SHA audited | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/0) |
| MGI3-MGI-V3-DOD-02 | manufacturing_machines | PARTIAL | Original V2 requirements fully traceable | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/1) |
| MGI3-MGI-V3-DOD-03 | manufacturing_machines | PARTIAL | Duplicate authorities equal zero | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/2) |
| MGI3-MGI-V3-DOD-04 | manufacturing_machines | PARTIAL | Exact source gate correct | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/3) |
| MGI3-MGI-V3-DOD-05 | manufacturing_machines | PARTIAL | Approximate IFC and proxy never READY | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/4) |
| MGI3-MGI-V3-DOD-06 | manufacturing_machines | PARTIAL | Immutable source proof | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/5) |
| MGI3-MGI-V3-DOD-07 | manufacturing_machines | PARTIAL | Central tolerance policy | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/6) |
| MGI3-MGI-V3-DOD-08 | manufacturing_machines | PARTIAL | Deterministic source face and edge signatures | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/7) |
| MGI3-MGI-V3-DOD-09 | manufacturing_machines | PARTIAL | Analytic face grouping | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/8) |
| MGI3-MGI-V3-DOD-10 | manufacturing_machines | PARTIAL | Robust candidate axes | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/9) |
| MGI3-MGI-V3-DOD-11 | manufacturing_machines | PARTIAL | Deterministic manufacturing frame | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/10) |
| MGI3-MGI-V3-DOD-12 | manufacturing_machines | PARTIAL | Adaptive cross sections | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/11) |
| MGI3-MGI-V3-DOD-13 | manufacturing_machines | PARTIAL | Event and interval analysis | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/12) |
| MGI3-MGI-V3-DOD-14 | manufacturing_machines | PARTIAL | Multi-region extrusion candidates | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/13) |
| MGI3-MGI-V3-DOD-15 | manufacturing_machines | PARTIAL | Full contour profile geometry proof | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/14) |
| MGI3-MGI-V3-DOD-16 | manufacturing_machines | PARTIAL | All required profile families safe | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/15) |
| MGI3-MGI-V3-DOD-17 | manufacturing_machines | PARTIAL | Hole recognition | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/16) |
| MGI3-MGI-V3-DOD-18 | manufacturing_machines | PARTIAL | Split-cylinder grouping | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/17) |
| MGI3-MGI-V3-DOD-19 | manufacturing_machines | PARTIAL | Slot recognition | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/18) |
| MGI3-MGI-V3-DOD-20 | manufacturing_machines | PARTIAL | Countersink and counterbore candidates | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/19) |
| MGI3-MGI-V3-DOD-21 | manufacturing_machines | PARTIAL | Prismatic negative features | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/20) |
| MGI3-MGI-V3-DOD-22 | manufacturing_machines | PARTIAL | Cope and notch | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/21) |
| MGI3-MGI-V3-DOD-23 | manufacturing_machines | PARTIAL | Miter and end cut | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/22) |
| MGI3-MGI-V3-DOD-24 | manufacturing_machines | PARTIAL | Positive features | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/23) |
| MGI3-MGI-V3-DOD-25 | manufacturing_machines | PARTIAL | Multi-extrusion | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/24) |
| MGI3-MGI-V3-DOD-26 | manufacturing_machines | PARTIAL | FeatureGraph | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/25) |
| MGI3-MGI-V3-DOD-27 | manufacturing_machines | PARTIAL | Residual-driven solver | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/26) |
| MGI3-MGI-V3-DOD-28 | manufacturing_machines | PARTIAL | Multiple hypotheses | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/27) |
| MGI3-MGI-V3-DOD-29 | manufacturing_machines | PARTIAL | Bounded search | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/28) |
| MGI3-MGI-V3-DOD-30 | manufacturing_machines | PARTIAL | Ambiguity handling | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/29) |
| MGI3-MGI-V3-DOD-31 | manufacturing_machines | PARTIAL | Independent compound reconstruction | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/30) |
| MGI3-MGI-V3-DOD-32 | manufacturing_machines | PARTIAL | Two-way BREP residual proof | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/31) |
| MGI3-MGI-V3-DOD-33 | manufacturing_machines | PARTIAL | Connected residual diagnostics | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/32) |
| MGI3-MGI-V3-DOD-34 | manufacturing_machines | PARTIAL | Boundary-distance proof | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/33) |
| MGI3-MGI-V3-DOD-35 | manufacturing_machines | PARTIAL | Metric-only cannot READY | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/34) |
| MGI3-MGI-V3-DOD-36 | manufacturing_machines | PARTIAL | False READY equals zero | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/35) |
| MGI3-MGI-V3-DOD-37 | manufacturing_machines | PARTIAL | Representability per target | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/36) |
| MGI3-MGI-V3-DOD-38 | manufacturing_machines | PARTIAL | NC1 support tied to serializer and reimport evidence | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/37) |
| MGI3-MGI-V3-DOD-39 | manufacturing_machines | PARTIAL | Machine representability uses capability authority | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/38) |
| MGI3-MGI-V3-DOD-40 | manufacturing_machines | PARTIAL | Machine transfer remains false without external proof | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/39) |
| MGI3-MGI-V3-DOD-41 | manufacturing_machines | PARTIAL | Transactional Workbench promotion | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/40) |
| MGI3-MGI-V3-DOD-42 | manufacturing_machines | PARTIAL | Rollback works | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/41) |
| MGI3-MGI-V3-DOD-43 | manufacturing_machines | PARTIAL | Stale report blocks promotion | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/42) |
| MGI3-MGI-V3-DOD-44 | manufacturing_machines | PARTIAL | Supported roundtrips pass | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/43) |
| MGI3-MGI-V3-DOD-45 | manufacturing_machines | PARTIAL | Same permanent ViewerHost | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/44) |
| MGI3-MGI-V3-DOD-46 | manufacturing_machines | PARTIAL | Manufacturing Geometry workspace functional | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/45) |
| MGI3-MGI-V3-DOD-47 | manufacturing_machines | PARTIAL | Diagnostic overlays functional | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/46) |
| MGI3-MGI-V3-DOD-48 | manufacturing_machines | PARTIAL | No second SelectionAuthority | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/47) |
| MGI3-MGI-V3-DOD-49 | manufacturing_machines | PARTIAL | JobManager cancel and stale protection | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/48) |
| MGI3-MGI-V3-DOD-50 | manufacturing_machines | PARTIAL | Derived artifact persistence | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/49) |
| MGI3-MGI-V3-DOD-51 | manufacturing_machines | PARTIAL | Cache invalidation correct | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/50) |
| MGI3-MGI-V3-DOD-52 | manufacturing_machines | PARTIAL | Deterministic repeat output | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/51) |
| MGI3-MGI-V3-DOD-53 | manufacturing_machines | PARTIAL | CLI single and project batch | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/52) |
| MGI3-MGI-V3-DOD-54 | manufacturing_machines | PARTIAL | Minimum 45 corpus categories addressed | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/53) |
| MGI3-MGI-V3-DOD-55 | manufacturing_machines | PARTIAL | Adversarial corpus | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/54) |
| MGI3-MGI-V3-DOD-56 | manufacturing_machines | PARTIAL | Precision and recall metrics | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/55) |
| MGI3-MGI-V3-DOD-57 | manufacturing_machines | PARTIAL | Performance p50 p95 and max | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/56) |
| MGI3-MGI-V3-DOD-58 | manufacturing_machines | PARTIAL | Bounded memory and runtime | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/57) |
| MGI3-MGI-V3-DOD-59 | manufacturing_machines | PARTIAL | Three real screenshots per build phase | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/58) |
| MGI3-MGI-V3-DOD-60 | manufacturing_machines | PARTIAL | Windows packaged acceptance | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/59) |
| MGI3-MGI-V3-DOD-61 | manufacturing_machines | PARTIAL | Legacy regressions pass | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/60) |
| MGI3-MGI-V3-DOD-62 | manufacturing_machines | PARTIAL | Exact-SHA evidence | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/61) |
| MGI3-MGI-V3-DOD-63 | manufacturing_machines | PARTIAL | Queue and master traceability updated | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/62) |
| MGI3-MGI-V3-DOD-64 | manufacturing_machines | PARTIAL | Internal FAIL PARTIAL NOT_IMPLEMENTED NOT_INTEGRATED NOT_TESTED equals zero | validation/manufacturing_interpreter_v3/REQUIREMENT_TRACEABILITY.json (/requirements/63) |
| PDF-MATRIX-PDF-01 | pdf_ui_v3 | PARTIAL | ProductionDrawingRenderer + DocumentOutputService | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/0) |
| PDF-MATRIX-PDF-02 | pdf_ui_v3 | PARTIAL | A0-A4 physical page-size regression | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/1) |
| PDF-MATRIX-PDF-03 | pdf_ui_v3 | PARTIAL | orientation UI + DrawingDocument | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/2) |
| PDF-MATRIX-PDF-04 | pdf_ui_v3 | PARTIAL | standard scale fitting | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/3) |
| PDF-MATRIX-PDF-05 | pdf_ui_v3 | PARTIAL | visible mm/cm conversion | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/4) |
| PDF-MATRIX-PDF-06 | pdf_ui_v3 | PARTIAL | front/top/side projection | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/5) |
| PDF-MATRIX-PDF-07 | pdf_ui_v3 | PARTIAL | distinct ISO and 3D bases | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/6) |
| PDF-MATRIX-PDF-08 | pdf_ui_v3 | PARTIAL | PNG rasterized from final PDF | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/7) |
| PDF-MATRIX-PDF-09 | pdf_ui_v3 | PARTIAL | overall dimension layer | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/8) |
| PDF-MATRIX-PDF-10 | pdf_ui_v3 | PARTIAL | contour-and-holes mode | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/9) |
| PDF-MATRIX-PDF-11 | pdf_ui_v3 | PARTIAL | production-dimensions mode | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/10) |
| PDF-MATRIX-PDF-12 | pdf_ui_v3 | PARTIAL | anchored manual dimensions | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/11) |
| PDF-MATRIX-PDF-13 | pdf_ui_v3 | PARTIAL | hole callouts and center marks | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/12) |
| PDF-MATRIX-PDF-14 | pdf_ui_v3 | PARTIAL | slot geometry and callouts | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/13) |
| PDF-MATRIX-PDF-15 | pdf_ui_v3 | PARTIAL | countersink geometry and callouts | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/14) |
| PDF-MATRIX-PDF-16 | pdf_ui_v3 | PARTIAL | pocket/cope/cutout annotations | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/15) |
| PDF-MATRIX-PDF-17 | pdf_ui_v3 | PARTIAL | miter/end-cut callouts | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/16) |
| PDF-MATRIX-PDF-18 | pdf_ui_v3 | PARTIAL | scribe layer and feature binding | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/17) |
| PDF-MATRIX-PDF-19 | pdf_ui_v3 | PARTIAL | OCCT HLR native test | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/18) |
| PDF-MATRIX-PDF-20 | pdf_ui_v3 | PARTIAL | separate OCCT hidden layer | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/19) |
| PDF-MATRIX-PDF-21 | pdf_ui_v3 | PARTIAL | coplanar mesh diagonal regression | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/20) |
| PDF-MATRIX-PDF-22 | pdf_ui_v3 | PARTIAL | centerline layer | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/21) |
| PDF-MATRIX-PDF-23 | pdf_ui_v3 | PARTIAL | OCCT BREP plane section | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/22) |
| PDF-MATRIX-PDF-24 | pdf_ui_v3 | PARTIAL | per-feature detail pages | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/23) |
| PDF-MATRIX-PDF-25 | pdf_ui_v3 | PARTIAL | exact BREP end section | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/24) |
| PDF-MATRIX-PDF-26 | pdf_ui_v3 | PARTIAL | OCCT BREP ISO/3D projection | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/25) |
| PDF-MATRIX-PDF-27 | pdf_ui_v3 | PARTIAL | per-sheet title block | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/26) |
| PDF-MATRIX-PDF-28 | pdf_ui_v3 | PARTIAL | revision/status/sheet count | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/27) |
| PDF-MATRIX-PDF-29 | pdf_ui_v3 | PARTIAL | BOM schedule and pagination | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/28) |
| PDF-MATRIX-PDF-30 | pdf_ui_v3 | PARTIAL | notes and continuation page | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/29) |
| PDF-MATRIX-PDF-31 | pdf_ui_v3 | PARTIAL | automatic multi-sheet document | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/30) |
| PDF-MATRIX-PDF-32 | pdf_ui_v3 | PARTIAL | assembly selection and BOM; exact release remains blocked | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/31) |
| PDF-MATRIX-PDF-33 | pdf_ui_v3 | PARTIAL | canonical DimensionGraph input | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/32) |
| PDF-MATRIX-PDF-34 | pdf_ui_v3 | PARTIAL | central DrawingLinter | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/33) |
| PDF-MATRIX-PDF-35 | pdf_ui_v3 | PARTIAL | clipping/collision/coverage regression | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/34) |
| PDF-MATRIX-PDF-36 | pdf_ui_v3 | PARTIAL | vector primitive PDF renderer | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/35) |
| PDF-MATRIX-PDF-37 | pdf_ui_v3 | PARTIAL | Trusted model/manifest/document hashes | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/36) |
| PDF-MATRIX-PDF-38 | pdf_ui_v3 | PARTIAL | same visible DrawingDocument in Trusted PDF | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/37) |
| PDF-MATRIX-PDF-39 | pdf_ui_v3 | PARTIAL | visible content and embedded document verification | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/38) |
| PDF-MATRIX-PDF-40 | pdf_ui_v3 | PARTIAL | external PDF confidence and unresolved-question gate | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/39) |
| PDF-MATRIX-PDF-41 | pdf_ui_v3 | PARTIAL | final PDF registered for Print Center | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/40) |
| PDF-MATRIX-PDF-42 | pdf_ui_v3 | PARTIAL | drawing-state invalidation on manufacturing change | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/41) |
| PDF-MATRIX-PDF-43 | pdf_ui_v3 | PARTIAL | exact-head Windows source/package/portable workflow | validation/pdf_drawing/PDF_FUNCTIONAL_GAP_MATRIX_2026-09-02.json (/checks/42) |
| VIEWER-GAP-GAP-V-001 | viewer_openbim | PARTIAL | Exact remote HEAD exists; complete release bundle is not yet proven. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/0) |
| VIEWER-GAP-GAP-V-002 | viewer_openbim | PARTIAL | Interaction root cause fixed; fresh native HVPC FPS evidence required. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/1) |
| VIEWER-GAP-GAP-V-003 | viewer_openbim | PARTIAL | Duplicate render removed; fresh native input p95/p99 required. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/2) |
| VIEWER-GAP-GAP-V-004 | viewer_openbim | PARTIAL | Cold exact is 6.450 s; maximum is 5.000 s. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/3) |
| VIEWER-GAP-GAP-V-005 | viewer_openbim | PARTIAL | Local 602 s soak passed; exact-SHA real HVPC OpenGL soak pending. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/4) |
| VIEWER-GAP-GAP-V-006 | viewer_openbim | PARTIAL | Strict RSS gate implemented; current native HVPC result pending. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/5) |
| VIEWER-GAP-GAP-V-007 | viewer_openbim | BLOCKED_EXTERNAL | Human review of paired captures is required. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/6) |
| VIEWER-GAP-GAP-V-008 | viewer_openbim | PARTIAL | Qt chrome and native VTK framebuffer are composited. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/7) |
| VIEWER-GAP-GAP-V-009 | viewer_openbim | PARTIAL | All active master requirements are derived dynamically. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/8) |
| VIEWER-GAP-GAP-V-010 | viewer_openbim | PARTIAL | New exact-SHA Windows package matrix pending. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/9) |
| VIEWER-GAP-GAP-V-011 | viewer_openbim | BLOCKED_EXTERNAL | Same-machine Trimble session required. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/10) |
| VIEWER-GAP-GAP-V-012 | viewer_openbim | PARTIAL | Depth-aware feature-edge hidden-line pipeline delivered. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/11) |
| VIEWER-GAP-GAP-V-013 | viewer_openbim | PARTIAL | BCF 2.1 archive validates against official XSDs before promotion. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/12) |
| VIEWER-GAP-GAP-V-014 | viewer_openbim | PARTIAL | Model-dominant sizing implemented; human UX acceptance pending. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/13) |
| VIEWER-GAP-GAP-V-015 | viewer_openbim | PARTIAL | Exact-SHA real HVPC soak is wired into release CI. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/14) |
| VIEWER-GAP-GAP-V-016 | viewer_openbim | PARTIAL | Single Viewer version source and release-bound authority. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/15) |
| VIEWER-GAP-GAP-V-017 | viewer_openbim | PARTIAL | PR 9 exists but is not reviewed and merged to the designated default branch. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/16) |
| VIEWER-GAP-GAP-V-018 | viewer_openbim | PARTIAL | Light contracts import without CadQuery, VTK or PySide6. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/17) |
| VIEWER-GAP-GAP-V-019 | viewer_openbim | BLOCKED_EXTERNAL | iGPU/dGPU and 1080p/4K matrix requires external hardware. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/18) |
| VIEWER-GAP-GAP-V-020 | viewer_openbim | PARTIAL | DPI/focus covered; screenreader and complete contrast proof pending. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/19) |
| VIEWER-GAP-GAP-V-021 | viewer_openbim | PARTIAL | Version/eager-import drift reduced; wider legacy reduction remains. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/20) |
| VIEWER-GAP-GAP-V-022 | viewer_openbim | PARTIAL | A second large revision/clash regression model is unavailable. | docs/audit_sources/CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json (/gaps/21) |
| DOMAIN-D01 | historical | PARTIAL | Nieuwe subsystemen moeten aansluiten op bestaande authorities; legacy UI-surfaces en oude naming nog consolideren. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/0) |
| DOMAIN-D02 | historical | PARTIAL | Laatste V5 state/user-preference scheiding en migration/corruption/cross-project acceptance nog verbreden. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/1) |
| DOMAIN-D03 | historical | PARTIAL | Project baseline/service materialiseert primair IFC/STEP; NC1/PDF bestaan elders maar nog niet als één project-intake authority met alle edge cases. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/2) |
| DOMAIN-D04 | historical | PARTIAL | Geometry-based profielbewijs ontbreekt nog als onderdeel van de Manufacturing Geometry Interpreter; metadata/text recognition blijft reviewplichtig. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/3) |
| DOMAIN-D05 | historical | PARTIAL | Volledige V5.2 control mapping, box/crossing-selection parity, state persistence en actuele packaged acceptance opnieuw bewijzen. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/4) |
| DOMAIN-D06 | historical | PARTIAL | Single-worker exact load, Cache V1, selected-only priority, geen echte frame-upload governor, 8x interactive MSAA, geen volledige packaged cold/warm/soak proof. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/5) |
| DOMAIN-D07 | historical | PARTIAL | Gedragstestfoundation bestaat; complete same-machine/model behavior + performance matrix ontbreekt. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/6) |
| DOMAIN-D08 | historical | PARTIAL | Canonical main window is nog V9/12-tab shell met legacy teksten/QSS; definitieve vijfdeling Project\|Viewer\|Productie\|Controle\|Uitvoer ontbreekt. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/7) |
| DOMAIN-D09 | historical | PARTIAL | SCREEN_MANIFEST/control binding/ui_test_id/IconRegistry/V5.2 design system ontbreken in canonical repo. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/8) |
| DOMAIN-D10 | historical | PARTIAL | Legacy editor volledig terugtrekken na parity; unsupported richer feature rebuild/roundtrip uitbreiden; interpreter promotion koppelen. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/9) |
| DOMAIN-D11 | historical | PARTIAL | Nieuwe production-status joins en V5 hub moeten bovenop BOM truth komen zonder quantity truth te muteren. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/10) |
| DOMAIN-D12 | historical | PARTIAL | Geen centrale MachineRoutingService/assignment authority, recommended/assigned/auto-manual flow en V5 production hub gevonden. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/11) |
| DOMAIN-D13 | historical | PARTIAL | Capability is diep voor manufacturing/marking; route-aggregate, machine library UI en bredere operation mapping ontbreken. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/12) |
| DOMAIN-D14 | historical | PARTIAL | V5 Control/Manufacturing Geometry integratie, final E2E en interpreter-upstream feeding moeten nog volledig samenkomen. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/13) |
| DOMAIN-D15 | historical | PARTIAL | Geen source FAG, decomposition hypotheses, independent reconstruction/two-way BREP proof, residual solver of transactionele Workbench promotion aangetroffen. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/14) |
| DOMAIN-D16 | historical | PARTIAL | Complete V5 production flow, packaged E2E, full proof/status/UI reconciliation en current master acceptance nog afronden. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/15) |
| DOMAIN-D17 | historical | PARTIAL | Huidige solver is rechthoekige deterministic shelf solver; polygonen/holes/grain/remnants/reservations/manual locks/exact polygon validation ontbreken. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/16) |
| DOMAIN-D18 | historical | PARTIAL | Rijkere features dan hole blijven terecht geblokkeerd; scope-first V5 UX en uitgebreide lossless feature coverage nog sluiten. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/17) |
| DOMAIN-D19 | historical | PARTIAL | Consolidatie met production Drawing engine en actuele V5 PDF Review/evidence flow vereist; external PDF blijft confidence/review-gated. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/18) |
| DOMAIN-D20 | historical | PARTIAL | Vectorfoundation bestaat in pdf_support, maar de geïntegreerde DrawingWorkspace gebruikt PIL-rastergenerator en slaat de hele pagina als raster-PDF op. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/19) |
| DOMAIN-D21 | historical | PARTIAL | Geen centrale DocumentOutputService/Print Center authority gevonden; output zit verdeeld over drawing/PDF/export. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/20) |
| DOMAIN-D22 | historical | PARTIAL | Laatste V5 Controle-structuur, Manufacturing Geometry, Evidence, PDF Review en Problem Center nog integreren en volledig click-through bewijzen. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/21) |
| DOMAIN-D23 | historical | PARTIAL | Volledige operator-UI, traceability en koppeling met planning/shopfloor/product readiness nog afronden. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/22) |
| DOMAIN-D24 | historical | PARTIAL | Geen dedicated Resource/WorkCenter/Shift/ProductionOrder/ScheduledOperation finite-capacity subsystem aangetroffen. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/23) |
| DOMAIN-D25 | historical | PARTIAL | V5 scope→formats→preflight→generate→verify→package UX en nieuwe routing/quality/planning gates aan dezelfde releaseauthority koppelen. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/24) |
| DOMAIN-D26 | historical | PARTIAL | Projectstate en userprefs versioned scheiden; columns/theme/splitters/printer plus saved views/measurements/sections/markups volledig restart/migration testen. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/25) |
| DOMAIN-D27 | historical | PARTIAL | Repo traceability wijst nog naar 27-aug prompt; 30/31-aug UI/performance/interpreter requirements zijn niet onderdeel van de 29-aug 51/51 acceptance. | requirements/sources/CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json (/domains/26) |
| PI-0001 | product_integration | PARTIAL | Voltooi de bestaande **CWS Convertor / SteelConverter** tot één samenhangende, productiegerichte Windows-applicatie. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L5) |
| PI-0002 | product_integration | PARTIAL | Bouw **geen vervangend programma**. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L7) |
| PI-0003 | product_integration | PARTIAL | Gebruik de bestaande architectuur, repository, canonieke ProjectModel-keten, Viewer, DrawingWorkspacePanel, BOM/Productiehub, herkenningsengines, profiel- en plaatnesting, manufacturing/scribing, export, installer en bestaande testinfrastructuur als basis. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L9) |
| PI-0004 | product_integration | PARTIAL | Iedere wijziging moet bestaande werkende functionaliteit behouden. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L11) |
| PI-0005 | product_integration | PARTIAL | Repository: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L13) |
| PI-0006 | product_integration | PARTIAL | `CoenWessselink/Convertor` | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L15) |
| PI-0007 | product_integration | PARTIAL | Primaire werkbranch: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L17) |
| PI-0008 | product_integration | PARTIAL | `agent/cws-pdf-ui-v3-complete-20260909` | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L19) |
| PI-0009 | product_integration | PARTIAL | Controleer vóór iedere wijziging eerst de actuele remote HEAD. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L21) |
| PI-0010 | product_integration | PARTIAL | De laatst bekende HEAD uit deze opdracht was: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L23) |
| PI-0011 | product_integration | PARTIAL | `df2029ac0ae50d78221dc38c962ccada91e8f28c` | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L25) |
| PI-0012 | product_integration | PARTIAL | Deze SHA is uitsluitend referentie. Neem hem nooit blind over indien de branch inmiddels verder staat. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L27) |
| PI-0013 | product_integration | PARTIAL | Geen force push. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L29) |
| PI-0014 | product_integration | PARTIAL | Behoud gelijktijdig werk. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L31) |
| PI-0015 | product_integration | PARTIAL | Werk in kleine, herstelbare commits. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L33) |
| PI-0016 | product_integration | PARTIAL | Voer de opdracht **niet als één onbeheerde megawijziging** uit. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L39) |
| PI-0017 | product_integration | PARTIAL | Werk exact in onderstaande bouwblokken. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L41) |
| PI-0018 | product_integration | PARTIAL | Een volgend bouwblok mag pas inhoudelijk worden gestart nadat: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L43) |
| PI-0019 | product_integration | PARTIAL | Een volgend bouwblok mag pas inhoudelijk worden gestart nadat: 1. het vorige blok is geïmplementeerd; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L45) |
| PI-0020 | product_integration | PARTIAL | Een volgend bouwblok mag pas inhoudelijk worden gestart nadat: 2. relevante tests groen zijn; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L46) |
| PI-0021 | product_integration | PARTIAL | Een volgend bouwblok mag pas inhoudelijk worden gestart nadat: 3. regressie is uitgevoerd; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L47) |
| PI-0022 | product_integration | PARTIAL | Een volgend bouwblok mag pas inhoudelijk worden gestart nadat: 4. bewijs is opgeslagen; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L48) |
| PI-0023 | product_integration | PARTIAL | Een volgend bouwblok mag pas inhoudelijk worden gestart nadat: 5. wijzigingen zijn gecommit; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L49) |
| PI-0024 | product_integration | PARTIAL | Een volgend bouwblok mag pas inhoudelijk worden gestart nadat: 6. de actuele GAP-status is bijgewerkt. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L50) |
| PI-0025 | product_integration | PARTIAL | Als een extern bewijs ontbreekt, markeer het blokonderdeel als `BLOCKED_EXTERNAL` en ga door met andere softwarematige onderdelen. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L52) |
| PI-0026 | product_integration | PARTIAL | Nooit externe acceptatie faken. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L54) |
| PI-0027 | requirements_bom | PARTIAL | Maak eerst één actuele requirementsbasis en sluit de volledige BOM-actiematrix technisch af. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L62) |
| PI-0028 | requirements_bom | PARTIAL | Maak een nieuw **Master Requirements Register V2** op basis van: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L66) |
| PI-0029 | requirements_bom | PARTIAL | Maak een nieuw **Master Requirements Register V2** op basis van: historische MASTER_REQUIREMENT_TRACEABILITY; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L68) |
| PI-0030 | requirements_bom | PARTIAL | Maak een nieuw **Master Requirements Register V2** op basis van: Viewer requirements; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L69) |
| PI-0031 | requirements_bom | PARTIAL | Maak een nieuw **Master Requirements Register V2** op basis van: BOM requirements; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L70) |
| PI-0032 | requirements_bom | PARTIAL | Maak een nieuw **Master Requirements Register V2** op basis van: PDF/UI V3; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L71) |
| PI-0033 | requirements_bom | PARTIAL | Maak een nieuw **Master Requirements Register V2** op basis van: materiaal/modelherkenning; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L72) |
| PI-0034 | requirements_bom | PARTIAL | Maak een nieuw **Master Requirements Register V2** op basis van: converter; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L73) |
| PI-0035 | requirements_bom | PARTIAL | Maak een nieuw **Master Requirements Register V2** op basis van: nesting; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L74) |
| PI-0036 | requirements_bom | PARTIAL | Maak een nieuw **Master Requirements Register V2** op basis van: voorraad; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L75) |
| PI-0037 | requirements_bom | PARTIAL | Maak een nieuw **Master Requirements Register V2** op basis van: purchase/weld; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L76) |
| PI-0038 | requirements_bom | PARTIAL | Maak een nieuw **Master Requirements Register V2** op basis van: manufacturing/M1–M18; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L77) |
| PI-0039 | requirements_bom | PARTIAL | Maak een nieuw **Master Requirements Register V2** op basis van: machine routing; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L78) |
| PI-0040 | requirements_bom | PARTIAL | Maak een nieuw **Master Requirements Register V2** op basis van: planning; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L79) |
| PI-0041 | requirements_bom | PARTIAL | Maak een nieuw **Master Requirements Register V2** op basis van: quality; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L80) |
| PI-0042 | requirements_bom | PARTIAL | Maak een nieuw **Master Requirements Register V2** op basis van: installer/release; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L81) |
| PI-0043 | requirements_bom | PARTIAL | Maak een nieuw **Master Requirements Register V2** op basis van: alle requirements in deze superprompt. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L82) |
| PI-0044 | requirements_bom | PARTIAL | Iedere requirement bevat: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L84) |
| PI-0045 | requirements_bom | PARTIAL | Iedere requirement bevat: requirement_id; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L86) |
| PI-0046 | requirements_bom | PARTIAL | Iedere requirement bevat: source; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L87) |
| PI-0047 | requirements_bom | PARTIAL | Iedere requirement bevat: category; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L88) |
| PI-0048 | requirements_bom | PARTIAL | Iedere requirement bevat: description; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L89) |
| PI-0049 | requirements_bom | PARTIAL | Iedere requirement bevat: applicable; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L90) |
| PI-0050 | requirements_bom | PARTIAL | Iedere requirement bevat: implementation; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L91) |
| PI-0051 | requirements_bom | PARTIAL | Iedere requirement bevat: test; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L92) |
| PI-0052 | requirements_bom | PARTIAL | Iedere requirement bevat: evidence; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L93) |
| PI-0053 | requirements_bom | PARTIAL | Iedere requirement bevat: source_commit; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L94) |
| PI-0054 | requirements_bom | PARTIAL | Iedere requirement bevat: installed_commit; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L95) |
| PI-0055 | requirements_bom | PARTIAL | Iedere requirement bevat: status; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L96) |
| PI-0056 | requirements_bom | PARTIAL | Iedere requirement bevat: blocker; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L97) |
| PI-0057 | requirements_bom | PARTIAL | Iedere requirement bevat: external_acceptance; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L98) |
| PI-0058 | requirements_bom | PARTIAL | Iedere requirement bevat: supersedes; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L99) |
| PI-0059 | requirements_bom | PARTIAL | Iedere requirement bevat: superseded_by. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L100) |
| PI-0060 | requirements_bom | PARTIAL | Status: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L102) |
| PI-0061 | requirements_bom | PARTIAL | Status: PASS | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L104) |
| PI-0062 | requirements_bom | PARTIAL | Status: PARTIAL | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L105) |
| PI-0063 | requirements_bom | PARTIAL | Status: FAIL | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L106) |
| PI-0064 | requirements_bom | PARTIAL | Status: BLOCKED_EXTERNAL | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L107) |
| PI-0065 | requirements_bom | PARTIAL | Status: OUT_OF_SCOPE_APPROVED | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L108) |
| PI-0066 | requirements_bom | PARTIAL | Historische PASS-statussen niet automatisch overnemen. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L110) |
| PI-0067 | requirements_bom | PARTIAL | Gebruik `ACTION_DEFINITIONS` als canonieke actiematrix. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L114) |
| PI-0068 | requirements_bom | PARTIAL | Behoud bestaande 87/87 negatieve coverage. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L116) |
| PI-0069 | requirements_bom | PARTIAL | Test ALLE 87 acties positief. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L118) |
| PI-0070 | requirements_bom | PARTIAL | Per actie minimaal: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L120) |
| PI-0071 | requirements_bom | PARTIAL | Per actie minimaal: empty selection; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L122) |
| PI-0072 | requirements_bom | PARTIAL | Per actie minimaal: valid single; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L123) |
| PI-0073 | requirements_bom | PARTIAL | Per actie minimaal: valid multiple waar relevant; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L124) |
| PI-0074 | requirements_bom | PARTIAL | Per actie minimaal: mixed selection waar relevant; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L125) |
| PI-0075 | requirements_bom | PARTIAL | Per actie minimaal: wrong family; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L126) |
| PI-0076 | requirements_bom | PARTIAL | Per actie minimaal: blocked; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L127) |
| PI-0077 | requirements_bom | PARTIAL | Per actie minimaal: stale; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L128) |
| PI-0078 | requirements_bom | PARTIAL | Per actie minimaal: invalid; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L129) |
| PI-0079 | requirements_bom | PARTIAL | Per actie minimaal: positive postcondition; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L130) |
| PI-0080 | requirements_bom | PARTIAL | Per actie minimaal: exact selected IDs; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L131) |
| PI-0081 | requirements_bom | PARTIAL | Per actie minimaal: no unintended widening; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L132) |
| PI-0082 | requirements_bom | PARTIAL | Per actie minimaal: non-selected entities unchanged; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L133) |
| PI-0083 | requirements_bom | PARTIAL | Per actie minimaal: save/reopen wanneer persistent; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L134) |
| PI-0084 | requirements_bom | PARTIAL | Per actie minimaal: undo wanneer mutating; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L135) |
| PI-0085 | requirements_bom | PARTIAL | Per actie minimaal: release invalidation waar relevant. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L136) |
| PI-0086 | requirements_bom | PARTIAL | Een workspace openen telt niet als succesvolle uitvoering. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L138) |
| PI-0087 | requirements_bom | PARTIAL | exact 87 unieke acties; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L142) |
| PI-0088 | requirements_bom | PARTIAL | 87/87 negatieve postconditions bewezen; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L143) |
| PI-0089 | requirements_bom | PARTIAL | 87/87 positieve postconditions bewezen of expliciet external; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L144) |
| PI-0090 | requirements_bom | PARTIAL | mutating acties hebben undo/persistence bewijs waar toepasselijk; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L145) |
| PI-0091 | requirements_bom | PARTIAL | Master Requirements V2 gegenereerd; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L146) |
| PI-0092 | requirements_bom | PARTIAL | geen stille routefallback; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L147) |
| PI-0093 | requirements_bom | PARTIAL | geen generieke route die action intent verliest. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L148) |
| PI-0094 | requirements_bom | PARTIAL | Commit(s): | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L152) |
| PI-0095 | requirements_bom | PARTIAL | `feat(requirements): establish master requirements v2` | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L154) |
| PI-0096 | requirements_bom | PARTIAL | `fix(bom): close complete 87 action execution matrix` | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L156) |
| PI-0097 | requirements_bom | PARTIAL | `test(bom): prove all W18 action postconditions` | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L158) |
| PI-0098 | recognition_conversion | PARTIAL | Maak materiaal-/modelherkenning aantoonbaar bruikbaar op echte bronbestanden. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L166) |
| PI-0099 | recognition_conversion | PARTIAL | IFC | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L170) |
| PI-0100 | recognition_conversion | PARTIAL | STEP | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L171) |
| PI-0101 | recognition_conversion | PARTIAL | STP | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L172) |
| PI-0102 | recognition_conversion | PARTIAL | DXF | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L173) |
| PI-0103 | recognition_conversion | PARTIAL | NC1/DSTV | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L174) |
| PI-0104 | recognition_conversion | PARTIAL | trusted PDF | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L175) |
| PI-0105 | recognition_conversion | PARTIAL | externe vector-PDF | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L176) |
| PI-0106 | recognition_conversion | PARTIAL | raster/scan waar binnen scope | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L177) |
| PI-0107 | recognition_conversion | PARTIAL | Minimaal: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L181) |
| PI-0108 | recognition_conversion | PARTIAL | Minimaal: HEA | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L183) |
| PI-0109 | recognition_conversion | PARTIAL | Minimaal: HEB | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L184) |
| PI-0110 | recognition_conversion | PARTIAL | Minimaal: HEM | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L185) |
| PI-0111 | recognition_conversion | PARTIAL | Minimaal: IPE | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L186) |
| PI-0112 | recognition_conversion | PARTIAL | Minimaal: IPN | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L187) |
| PI-0113 | recognition_conversion | PARTIAL | Minimaal: UNP/UPE | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L188) |
| PI-0114 | recognition_conversion | PARTIAL | Minimaal: L | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L189) |
| PI-0115 | recognition_conversion | PARTIAL | Minimaal: T | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L190) |
| PI-0116 | recognition_conversion | PARTIAL | Minimaal: RHS | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L191) |
| PI-0117 | recognition_conversion | PARTIAL | Minimaal: SHS | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L192) |
| PI-0118 | recognition_conversion | PARTIAL | Minimaal: CHS | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L193) |
| PI-0119 | recognition_conversion | PARTIAL | Minimaal: strip | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L194) |
| PI-0120 | recognition_conversion | PARTIAL | Minimaal: flat | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L195) |
| PI-0121 | recognition_conversion | PARTIAL | Minimaal: round | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L196) |
| PI-0122 | recognition_conversion | PARTIAL | Minimaal: bar | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L197) |
| PI-0123 | recognition_conversion | PARTIAL | Minimaal: plate | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L198) |
| PI-0124 | recognition_conversion | PARTIAL | Minimaal: welded/custom profile | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L199) |
| PI-0125 | recognition_conversion | PARTIAL | Minimaal: manufacturer extrusion | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L200) |
| PI-0126 | recognition_conversion | PARTIAL | Minimaal: arbitrary STEP solid | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L201) |
| PI-0127 | recognition_conversion | PARTIAL | Minimaal: multisolid | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L202) |
| PI-0128 | recognition_conversion | PARTIAL | Minimaal: assembly | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L203) |
| PI-0129 | recognition_conversion | PARTIAL | hole | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L207) |
| PI-0130 | recognition_conversion | PARTIAL | slot | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L208) |
| PI-0131 | recognition_conversion | PARTIAL | notch | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L209) |
| PI-0132 | recognition_conversion | PARTIAL | cope | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L210) |
| PI-0133 | recognition_conversion | PARTIAL | mitre | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L211) |
| PI-0134 | recognition_conversion | PARTIAL | bevel | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L212) |
| PI-0135 | recognition_conversion | PARTIAL | cutout | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L213) |
| PI-0136 | recognition_conversion | PARTIAL | pocket | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L214) |
| PI-0137 | recognition_conversion | PARTIAL | contour | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L215) |
| PI-0138 | recognition_conversion | PARTIAL | chamfer | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L216) |
| PI-0139 | recognition_conversion | PARTIAL | weld preparation | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L217) |
| PI-0140 | recognition_conversion | PARTIAL | marking/scribing | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L218) |
| PI-0141 | recognition_conversion | PARTIAL | face | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L219) |
| PI-0142 | recognition_conversion | PARTIAL | orientation | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L220) |
| PI-0143 | recognition_conversion | PARTIAL | transformation | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L221) |
| PI-0144 | recognition_conversion | PARTIAL | Materiaal nooit uit vorm raden. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L225) |
| PI-0145 | recognition_conversion | PARTIAL | Bron moet zijn: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L227) |
| PI-0146 | recognition_conversion | PARTIAL | Bron moet zijn: source metadata; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L229) |
| PI-0147 | recognition_conversion | PARTIAL | Bron moet zijn: IFC property; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L230) |
| PI-0148 | recognition_conversion | PARTIAL | Bron moet zijn: NC data; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L231) |
| PI-0149 | recognition_conversion | PARTIAL | Bron moet zijn: certificate; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L232) |
| PI-0150 | recognition_conversion | PARTIAL | Bron moet zijn: controlled mapping; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L233) |
| PI-0151 | recognition_conversion | PARTIAL | Bron moet zijn: explicit user confirmation. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L234) |
| PI-0152 | recognition_conversion | PARTIAL | Onbekend blijft REVIEW_REQUIRED. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L236) |
| PI-0153 | recognition_conversion | PARTIAL | Voeg gecontroleerde custom-profile manager toe: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L240) |
| PI-0154 | recognition_conversion | PARTIAL | Voeg gecontroleerde custom-profile manager toe: DXF/STEP section extraction; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L242) |
| PI-0155 | recognition_conversion | PARTIAL | Voeg gecontroleerde custom-profile manager toe: profile fingerprint; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L243) |
| PI-0156 | recognition_conversion | PARTIAL | Voeg gecontroleerde custom-profile manager toe: rotation independent comparison; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L244) |
| PI-0157 | recognition_conversion | PARTIAL | Voeg gecontroleerde custom-profile manager toe: manufacturer; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L245) |
| PI-0158 | recognition_conversion | PARTIAL | Voeg gecontroleerde custom-profile manager toe: aliases; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L246) |
| PI-0159 | recognition_conversion | PARTIAL | Voeg gecontroleerde custom-profile manager toe: dimensions; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L247) |
| PI-0160 | recognition_conversion | PARTIAL | Voeg gecontroleerde custom-profile manager toe: tolerance; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L248) |
| PI-0161 | recognition_conversion | PARTIAL | Voeg gecontroleerde custom-profile manager toe: material compatibility; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L249) |
| PI-0162 | recognition_conversion | PARTIAL | Voeg gecontroleerde custom-profile manager toe: source evidence; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L250) |
| PI-0163 | recognition_conversion | PARTIAL | Voeg gecontroleerde custom-profile manager toe: user approval; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L251) |
| PI-0164 | recognition_conversion | PARTIAL | Voeg gecontroleerde custom-profile manager toe: versioning. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L252) |
| PI-0165 | recognition_conversion | PARTIAL | Gebruik alle eerder aangeleverde echte bestanden. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L256) |
| PI-0166 | recognition_conversion | PARTIAL | Per bestand: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L258) |
| PI-0167 | recognition_conversion | PARTIAL | Per bestand: SHA256; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L260) |
| PI-0168 | recognition_conversion | PARTIAL | Per bestand: source; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L261) |
| PI-0169 | recognition_conversion | PARTIAL | Per bestand: expected entities; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L262) |
| PI-0170 | recognition_conversion | PARTIAL | Per bestand: expected quantities; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L263) |
| PI-0171 | recognition_conversion | PARTIAL | Per bestand: dimensions; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L264) |
| PI-0172 | recognition_conversion | PARTIAL | Per bestand: profiles; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L265) |
| PI-0173 | recognition_conversion | PARTIAL | Per bestand: materials; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L266) |
| PI-0174 | recognition_conversion | PARTIAL | Per bestand: features; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L267) |
| PI-0175 | recognition_conversion | PARTIAL | Per bestand: expected blockers. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L268) |
| PI-0176 | recognition_conversion | PARTIAL | Rapporteer: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L270) |
| PI-0177 | recognition_conversion | PARTIAL | Rapporteer: precision; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L272) |
| PI-0178 | recognition_conversion | PARTIAL | Rapporteer: recall; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L273) |
| PI-0179 | recognition_conversion | PARTIAL | Rapporteer: false READY; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L274) |
| PI-0180 | recognition_conversion | PARTIAL | Rapporteer: false BLOCKED; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L275) |
| PI-0181 | recognition_conversion | PARTIAL | Rapporteer: review rate. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L276) |
| PI-0182 | recognition_conversion | PARTIAL | Een recognizer die alles blokkeert faalt. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L278) |
| PI-0183 | recognition_conversion | PARTIAL | False READY is altijd failure. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L280) |
| PI-0184 | recognition_conversion | PARTIAL | Test: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L284) |
| PI-0185 | recognition_conversion | PARTIAL | input format × output format × object family × feature. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L286) |
| PI-0186 | recognition_conversion | PARTIAL | Controleer: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L291) |
| PI-0187 | recognition_conversion | PARTIAL | Controleer: identity; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L293) |
| PI-0188 | recognition_conversion | PARTIAL | Controleer: quantity; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L294) |
| PI-0189 | recognition_conversion | PARTIAL | Controleer: dimensions; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L295) |
| PI-0190 | recognition_conversion | PARTIAL | Controleer: units; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L296) |
| PI-0191 | recognition_conversion | PARTIAL | Controleer: transforms; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L297) |
| PI-0192 | recognition_conversion | PARTIAL | Controleer: material provenance; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L298) |
| PI-0193 | recognition_conversion | PARTIAL | Controleer: features; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L299) |
| PI-0194 | recognition_conversion | PARTIAL | Controleer: assemblies. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L300) |
| PI-0195 | recognition_conversion | PARTIAL | alle eerder geleverde real-world bestanden opnieuw getest; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L304) |
| PI-0196 | recognition_conversion | PARTIAL | onafhankelijk expected result per bestand; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L305) |
| PI-0197 | recognition_conversion | PARTIAL | minimum precision/recall expliciet; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L306) |
| PI-0198 | recognition_conversion | PARTIAL | false READY = 0; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L307) |
| PI-0199 | recognition_conversion | PARTIAL | supported objectfamilies hebben positieve real-file cases; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L308) |
| PI-0200 | recognition_conversion | PARTIAL | converter heeft geen stille dataverliezen. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L309) |
| PI-0201 | viewer_openbim | PARTIAL | Maak Viewer/Controleren volledig bruikbaar als engineering reviewomgeving. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L317) |
| PI-0202 | viewer_openbim | PARTIAL | Voltooi/bewijs: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L321) |
| PI-0203 | viewer_openbim | PARTIAL | Voltooi/bewijs: exact IFC/STEP rendering; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L323) |
| PI-0204 | viewer_openbim | PARTIAL | Voltooi/bewijs: provenance; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L324) |
| PI-0205 | viewer_openbim | PARTIAL | Voltooi/bewijs: orbit/pan/zoom; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L325) |
| PI-0206 | viewer_openbim | PARTIAL | Voltooi/bewijs: standard views; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L326) |
| PI-0207 | viewer_openbim | PARTIAL | Voltooi/bewijs: orthographic/perspective; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L327) |
| PI-0208 | viewer_openbim | PARTIAL | Voltooi/bewijs: object selection; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L328) |
| PI-0209 | viewer_openbim | PARTIAL | Voltooi/bewijs: Ctrl selection; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L329) |
| PI-0210 | viewer_openbim | PARTIAL | Voltooi/bewijs: box; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L330) |
| PI-0211 | viewer_openbim | PARTIAL | Voltooi/bewijs: crossing; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L331) |
| PI-0212 | viewer_openbim | PARTIAL | Voltooi/bewijs: lasso; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L332) |
| PI-0213 | viewer_openbim | PARTIAL | Voltooi/bewijs: color; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L333) |
| PI-0214 | viewer_openbim | PARTIAL | Voltooi/bewijs: tree sync; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L334) |
| PI-0215 | viewer_openbim | PARTIAL | Voltooi/bewijs: BOM sync; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L335) |
| PI-0216 | viewer_openbim | PARTIAL | Voltooi/bewijs: properties; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L336) |
| PI-0217 | viewer_openbim | PARTIAL | Voltooi/bewijs: hide/show; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L337) |
| PI-0218 | viewer_openbim | PARTIAL | Voltooi/bewijs: isolate; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L338) |
| PI-0219 | viewer_openbim | PARTIAL | Voltooi/bewijs: ghost; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L339) |
| PI-0220 | viewer_openbim | PARTIAL | Voltooi/bewijs: transparency; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L340) |
| PI-0221 | viewer_openbim | PARTIAL | Voltooi/bewijs: source colors; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L341) |
| PI-0222 | viewer_openbim | PARTIAL | Voltooi/bewijs: wireframe; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L342) |
| PI-0223 | viewer_openbim | PARTIAL | Voltooi/bewijs: shaded; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L343) |
| PI-0224 | viewer_openbim | PARTIAL | Voltooi/bewijs: shaded with edges; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L344) |
| PI-0225 | viewer_openbim | PARTIAL | Voltooi/bewijs: hidden-line; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L345) |
| PI-0226 | viewer_openbim | PARTIAL | Voltooi/bewijs: sections; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L346) |
| PI-0227 | viewer_openbim | PARTIAL | Voltooi/bewijs: section from face; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L347) |
| PI-0228 | viewer_openbim | PARTIAL | Voltooi/bewijs: clipbox; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L348) |
| PI-0229 | viewer_openbim | PARTIAL | Voltooi/bewijs: explode; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L349) |
| PI-0230 | viewer_openbim | PARTIAL | Voltooi/bewijs: measurements; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L350) |
| PI-0231 | viewer_openbim | PARTIAL | Voltooi/bewijs: saved views; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L351) |
| PI-0232 | viewer_openbim | PARTIAL | Voltooi/bewijs: markups; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L352) |
| PI-0233 | viewer_openbim | PARTIAL | Voltooi/bewijs: issues; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L353) |
| PI-0234 | viewer_openbim | PARTIAL | Voltooi/bewijs: revision compare; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L354) |
| PI-0235 | viewer_openbim | PARTIAL | Voltooi/bewijs: deviation; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L355) |
| PI-0236 | viewer_openbim | PARTIAL | Voltooi/bewijs: clashes. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L356) |
| PI-0237 | viewer_openbim | PARTIAL | Voeg rule-based saved views toe: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L360) |
| PI-0238 | viewer_openbim | PARTIAL | Voeg rule-based saved views toe: query; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L362) |
| PI-0239 | viewer_openbim | PARTIAL | Voeg rule-based saved views toe: filters; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L363) |
| PI-0240 | viewer_openbim | PARTIAL | Voeg rule-based saved views toe: colours; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L364) |
| PI-0241 | viewer_openbim | PARTIAL | Voeg rule-based saved views toe: visibility; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L365) |
| PI-0242 | viewer_openbim | PARTIAL | Voeg rule-based saved views toe: grouping; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L366) |
| PI-0243 | viewer_openbim | PARTIAL | Voeg rule-based saved views toe: validation state. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L367) |
| PI-0244 | viewer_openbim | PARTIAL | Implementeer buildingSMART IDS validation: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L371) |
| PI-0245 | viewer_openbim | PARTIAL | Implementeer buildingSMART IDS validation: `.ids` import; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L373) |
| PI-0246 | viewer_openbim | PARTIAL | Implementeer buildingSMART IDS validation: IFC applicability; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L374) |
| PI-0247 | viewer_openbim | PARTIAL | Implementeer buildingSMART IDS validation: property; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L375) |
| PI-0248 | viewer_openbim | PARTIAL | Implementeer buildingSMART IDS validation: classification; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L376) |
| PI-0249 | viewer_openbim | PARTIAL | Implementeer buildingSMART IDS validation: material; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L377) |
| PI-0250 | viewer_openbim | PARTIAL | Implementeer buildingSMART IDS validation: value; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L378) |
| PI-0251 | viewer_openbim | PARTIAL | Implementeer buildingSMART IDS validation: unit checks. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L379) |
| PI-0252 | viewer_openbim | PARTIAL | Resultaat per object. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L381) |
| PI-0253 | viewer_openbim | PARTIAL | Viewer highlight. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L383) |
| PI-0254 | viewer_openbim | PARTIAL | Report. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L385) |
| PI-0255 | viewer_openbim | PARTIAL | Issue generation. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L387) |
| PI-0256 | viewer_openbim | PARTIAL | Voeg saved clash sets toe: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L391) |
| PI-0257 | viewer_openbim | PARTIAL | Voeg saved clash sets toe: scope A/B; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L393) |
| PI-0258 | viewer_openbim | PARTIAL | Voeg saved clash sets toe: hard clash; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L394) |
| PI-0259 | viewer_openbim | PARTIAL | Voeg saved clash sets toe: clearance; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L395) |
| PI-0260 | viewer_openbim | PARTIAL | Voeg saved clash sets toe: tolerance; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L396) |
| PI-0261 | viewer_openbim | PARTIAL | Voeg saved clash sets toe: exclusions; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L397) |
| PI-0262 | viewer_openbim | PARTIAL | Voeg saved clash sets toe: severity; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L398) |
| PI-0263 | viewer_openbim | PARTIAL | Voeg saved clash sets toe: assigned; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L399) |
| PI-0264 | viewer_openbim | PARTIAL | Voeg saved clash sets toe: status; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L400) |
| PI-0265 | viewer_openbim | PARTIAL | Voeg saved clash sets toe: rerun; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L401) |
| PI-0266 | viewer_openbim | PARTIAL | Voeg saved clash sets toe: stale-on-revision. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L402) |
| PI-0267 | viewer_openbim | PARTIAL | Ondersteun minimaal: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L406) |
| PI-0268 | viewer_openbim | PARTIAL | Ondersteun minimaal: BCF 2.1 import; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L408) |
| PI-0269 | viewer_openbim | PARTIAL | Ondersteun minimaal: BCF 3.0 import/export; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L409) |
| PI-0270 | viewer_openbim | PARTIAL | Ondersteun minimaal: GUID; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L410) |
| PI-0271 | viewer_openbim | PARTIAL | Ondersteun minimaal: camera; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L411) |
| PI-0272 | viewer_openbim | PARTIAL | Ondersteun minimaal: viewpoint; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L412) |
| PI-0273 | viewer_openbim | PARTIAL | Ondersteun minimaal: clipping; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L413) |
| PI-0274 | viewer_openbim | PARTIAL | Ondersteun minimaal: visible components; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L414) |
| PI-0275 | viewer_openbim | PARTIAL | Ondersteun minimaal: selected components; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L415) |
| PI-0276 | viewer_openbim | PARTIAL | Ondersteun minimaal: screenshot; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L416) |
| PI-0277 | viewer_openbim | PARTIAL | Ondersteun minimaal: comments; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L417) |
| PI-0278 | viewer_openbim | PARTIAL | Ondersteun minimaal: assignment; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L418) |
| PI-0279 | viewer_openbim | PARTIAL | Ondersteun minimaal: status. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L419) |
| PI-0280 | viewer_openbim | BLOCKED_EXTERNAL | Test BCF in onafhankelijke applicatie. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L421) |
| PI-0281 | viewer_openbim | PARTIAL | native Viewer tests; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L425) |
| PI-0282 | viewer_openbim | PARTIAL | no hidden-line source-only claim; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L426) |
| PI-0283 | viewer_openbim | PARTIAL | IDS end-to-end; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L427) |
| PI-0284 | viewer_openbim | PARTIAL | saved clash rerun na revision; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L428) |
| PI-0285 | viewer_openbim | PARTIAL | BCF roundtrip extern bewezen of BLOCKED_EXTERNAL; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L429) |
| PI-0286 | viewer_openbim | PARTIAL | Viewer state blijft behouden na save/reopen. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L430) |
| PI-0287 | drawings_change_impact | PARTIAL | Maak tekeningen volledig associatief met de engineeringketen. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L438) |
| PI-0288 | drawings_change_impact | PARTIAL | Behoud bestaande DrawingWorkspacePanel. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L442) |
| PI-0289 | drawings_change_impact | PARTIAL | Voltooi: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L444) |
| PI-0290 | drawings_change_impact | PARTIAL | Voltooi: part drawings; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L446) |
| PI-0291 | drawings_change_impact | PARTIAL | Voltooi: assembly drawings; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L447) |
| PI-0292 | drawings_change_impact | PARTIAL | Voltooi: GA indien in scope; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L448) |
| PI-0293 | drawings_change_impact | PARTIAL | Voltooi: automatic views; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L449) |
| PI-0294 | drawings_change_impact | PARTIAL | Voltooi: sections; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L450) |
| PI-0295 | drawings_change_impact | PARTIAL | Voltooi: scale; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L451) |
| PI-0296 | drawings_change_impact | PARTIAL | Voltooi: A4–A0; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L452) |
| PI-0297 | drawings_change_impact | PARTIAL | Voltooi: dimensions; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L453) |
| PI-0298 | drawings_change_impact | PARTIAL | Voltooi: marks; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L454) |
| PI-0299 | drawings_change_impact | PARTIAL | Voltooi: weld symbols; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L455) |
| PI-0300 | drawings_change_impact | PARTIAL | Voltooi: revision marks; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L456) |
| PI-0301 | drawings_change_impact | PARTIAL | Voltooi: title blocks; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L457) |
| PI-0302 | drawings_change_impact | PARTIAL | Voltooi: PDF; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L458) |
| PI-0303 | drawings_change_impact | PARTIAL | Voltooi: batch; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L459) |
| PI-0304 | drawings_change_impact | PARTIAL | Voltooi: print. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L460) |
| PI-0305 | drawings_change_impact | PARTIAL | Voeg toe: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L464) |
| PI-0306 | drawings_change_impact | PARTIAL | Voeg toe: drawing templates; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L466) |
| PI-0307 | drawings_change_impact | PARTIAL | Voeg toe: best template selection; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L467) |
| PI-0308 | drawings_change_impact | PARTIAL | Voeg toe: clone similar; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L468) |
| PI-0309 | drawings_change_impact | PARTIAL | Voeg toe: automatic views; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L469) |
| PI-0310 | drawings_change_impact | PARTIAL | Voeg toe: section suggestion; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L470) |
| PI-0311 | drawings_change_impact | PARTIAL | Voeg toe: dimension strategy; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L471) |
| PI-0312 | drawings_change_impact | PARTIAL | Voeg toe: annotation collision prevention; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L472) |
| PI-0313 | drawings_change_impact | PARTIAL | Voeg toe: drawing completeness; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L473) |
| PI-0314 | drawings_change_impact | PARTIAL | Voeg toe: revision impact preview; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L474) |
| PI-0315 | drawings_change_impact | PARTIAL | Voeg toe: bulk revision chart editing. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L475) |
| PI-0316 | drawings_change_impact | PARTIAL | Bouw één centrale dependencygraph. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L479) |
| PI-0317 | drawings_change_impact | PARTIAL | Voorbeeld: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L481) |
| PI-0318 | drawings_change_impact | PARTIAL | Part → Assembly → BOM → Drawing → Nesting → Stock → NC → Machine → Production Release → Inspection → Shipment. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L483) |
| PI-0319 | drawings_change_impact | PARTIAL | Als bron wijzigt: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L495) |
| PI-0320 | drawings_change_impact | PARTIAL | Als bron wijzigt: dependent outputs `STALE`; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L497) |
| PI-0321 | drawings_change_impact | PARTIAL | Als bron wijzigt: production release invalid; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L498) |
| PI-0322 | drawings_change_impact | PARTIAL | Als bron wijzigt: outdated drawings invalid; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L499) |
| PI-0323 | drawings_change_impact | PARTIAL | Als bron wijzigt: outdated nesting invalid; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L500) |
| PI-0324 | drawings_change_impact | PARTIAL | Als bron wijzigt: machine assignment opnieuw controleren indien relevant. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L501) |
| PI-0325 | drawings_change_impact | PARTIAL | Maak een Change Impact panel. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L503) |
| PI-0326 | drawings_change_impact | PARTIAL | Test één wijziging: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L507) |
| PI-0327 | drawings_change_impact | PARTIAL | Test één wijziging: profile; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L509) |
| PI-0328 | drawings_change_impact | PARTIAL | Test één wijziging: length; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L510) |
| PI-0329 | drawings_change_impact | PARTIAL | Test één wijziging: hole; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L511) |
| PI-0330 | drawings_change_impact | PARTIAL | Test één wijziging: material provenance. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L512) |
| PI-0331 | drawings_change_impact | PARTIAL | Controleer downstream: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L514) |
| PI-0332 | drawings_change_impact | PARTIAL | Controleer downstream: Viewer; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L516) |
| PI-0333 | drawings_change_impact | PARTIAL | Controleer downstream: BOM; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L517) |
| PI-0334 | drawings_change_impact | PARTIAL | Controleer downstream: mass; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L518) |
| PI-0335 | drawings_change_impact | PARTIAL | Controleer downstream: drawing; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L519) |
| PI-0336 | drawings_change_impact | PARTIAL | Controleer downstream: nesting; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L520) |
| PI-0337 | drawings_change_impact | PARTIAL | Controleer downstream: stock; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L521) |
| PI-0338 | drawings_change_impact | PARTIAL | Controleer downstream: machine; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L522) |
| PI-0339 | drawings_change_impact | PARTIAL | Controleer downstream: NC; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L523) |
| PI-0340 | drawings_change_impact | PARTIAL | Controleer downstream: exports; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L524) |
| PI-0341 | drawings_change_impact | PARTIAL | Controleer downstream: release. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L525) |
| PI-0342 | drawings_change_impact | PARTIAL | Save/reopen en undo inbegrepen. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L527) |
| PI-0343 | nesting_stock_purchase | PARTIAL | Maak materiaaloptimalisatie en fysieke voorraadlevensloop productiebruikbaar. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L535) |
| PI-0344 | nesting_stock_purchase | PARTIAL | Behoud bestaande engine. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L539) |
| PI-0345 | nesting_stock_purchase | PARTIAL | Ondersteun: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L541) |
| PI-0346 | nesting_stock_purchase | PARTIAL | Ondersteun: trade lengths; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L543) |
| PI-0347 | nesting_stock_purchase | PARTIAL | Ondersteun: stock; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L544) |
| PI-0348 | nesting_stock_purchase | PARTIAL | Ondersteun: remnants; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L545) |
| PI-0349 | nesting_stock_purchase | PARTIAL | Ondersteun: kerf; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L546) |
| PI-0350 | nesting_stock_purchase | PARTIAL | Ondersteun: multiple stock bars; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L547) |
| PI-0351 | nesting_stock_purchase | PARTIAL | Ondersteun: reservation; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L548) |
| PI-0352 | nesting_stock_purchase | PARTIAL | Ondersteun: alternatives; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L549) |
| PI-0353 | nesting_stock_purchase | PARTIAL | Ondersteun: compare; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L550) |
| PI-0354 | nesting_stock_purchase | PARTIAL | Ondersteun: procurement need. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L551) |
| PI-0355 | nesting_stock_purchase | PARTIAL | Status onderscheid: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L553) |
| PI-0356 | nesting_stock_purchase | PARTIAL | Status onderscheid: FEASIBLE; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L555) |
| PI-0357 | nesting_stock_purchase | PARTIAL | Status onderscheid: HEURISTIC; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L556) |
| PI-0358 | nesting_stock_purchase | PARTIAL | Status onderscheid: OPTIMAL_PROVEN; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L557) |
| PI-0359 | nesting_stock_purchase | PARTIAL | Status onderscheid: UNPROVEN. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L558) |
| PI-0360 | nesting_stock_purchase | PARTIAL | Geen optimaliteitsclaim zonder bewijs. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L560) |
| PI-0361 | nesting_stock_purchase | PARTIAL | Gebruik één canonieke engine. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L564) |
| PI-0362 | nesting_stock_purchase | PARTIAL | Ondersteun: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L566) |
| PI-0363 | nesting_stock_purchase | PARTIAL | Ondersteun: quantity; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L568) |
| PI-0364 | nesting_stock_purchase | PARTIAL | Ondersteun: exact material; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L569) |
| PI-0365 | nesting_stock_purchase | PARTIAL | Ondersteun: grade; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L570) |
| PI-0366 | nesting_stock_purchase | PARTIAL | Ondersteun: thickness; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L571) |
| PI-0367 | nesting_stock_purchase | PARTIAL | Ondersteun: contour; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L572) |
| PI-0368 | nesting_stock_purchase | PARTIAL | Ondersteun: holes; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L573) |
| PI-0369 | nesting_stock_purchase | PARTIAL | Ondersteun: concave geometry; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L574) |
| PI-0370 | nesting_stock_purchase | PARTIAL | Ondersteun: rotations; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L575) |
| PI-0371 | nesting_stock_purchase | PARTIAL | Ondersteun: grain; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L576) |
| PI-0372 | nesting_stock_purchase | PARTIAL | Ondersteun: kerf; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L577) |
| PI-0373 | nesting_stock_purchase | PARTIAL | Ondersteun: clearances; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L578) |
| PI-0374 | nesting_stock_purchase | PARTIAL | Ondersteun: stock; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L579) |
| PI-0375 | nesting_stock_purchase | PARTIAL | Ondersteun: remnants. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L580) |
| PI-0376 | nesting_stock_purchase | PARTIAL | Verdiep met: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L582) |
| PI-0377 | nesting_stock_purchase | PARTIAL | Verdiep met: true-shape; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L584) |
| PI-0378 | nesting_stock_purchase | PARTIAL | Verdiep met: clamp/no-cut; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L585) |
| PI-0379 | nesting_stock_purchase | PARTIAL | Verdiep met: collision; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L586) |
| PI-0380 | nesting_stock_purchase | PARTIAL | Verdiep met: common-line; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L587) |
| PI-0381 | nesting_stock_purchase | PARTIAL | Verdiep met: chain/bridge; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L588) |
| PI-0382 | nesting_stock_purchase | PARTIAL | Verdiep met: pierce minimization; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L589) |
| PI-0383 | nesting_stock_purchase | PARTIAL | Verdiep met: cut length; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L590) |
| PI-0384 | nesting_stock_purchase | PARTIAL | Verdiep met: true remnant contour. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L591) |
| PI-0385 | nesting_stock_purchase | PARTIAL | States: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L595) |
| PI-0386 | nesting_stock_purchase | PARTIAL | States: predicted; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L597) |
| PI-0387 | nesting_stock_purchase | PARTIAL | States: reserved_future; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L598) |
| PI-0388 | nesting_stock_purchase | PARTIAL | States: created; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L599) |
| PI-0389 | nesting_stock_purchase | PARTIAL | States: available; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L600) |
| PI-0390 | nesting_stock_purchase | PARTIAL | States: consumed; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L601) |
| PI-0391 | nesting_stock_purchase | PARTIAL | States: scrapped. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L602) |
| PI-0392 | nesting_stock_purchase | PARTIAL | Geen fysiek verbruik voordat broncut bevestigd is. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L604) |
| PI-0393 | nesting_stock_purchase | PARTIAL | Implementeer: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L608) |
| PI-0394 | nesting_stock_purchase | PARTIAL | NEED → REQUISITION → ORDERED → RECEIVED → AVAILABLE → RESERVED → ISSUED → CONSUMED. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L610) |
| PI-0395 | nesting_stock_purchase | PARTIAL | Remnant: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L619) |
| PI-0396 | nesting_stock_purchase | PARTIAL | CREATED → AVAILABLE → RESERVED → CONSUMED/SCRAPPED. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L621) |
| PI-0397 | nesting_stock_purchase | PARTIAL | Per stock item: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L628) |
| PI-0398 | nesting_stock_purchase | PARTIAL | Per stock item: supplier; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L630) |
| PI-0399 | nesting_stock_purchase | PARTIAL | Per stock item: PO; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L631) |
| PI-0400 | nesting_stock_purchase | PARTIAL | Per stock item: heat/charge; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L632) |
| PI-0401 | nesting_stock_purchase | PARTIAL | Per stock item: certificate; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L633) |
| PI-0402 | nesting_stock_purchase | PARTIAL | Per stock item: grade; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L634) |
| PI-0403 | nesting_stock_purchase | PARTIAL | Per stock item: dimensions; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L635) |
| PI-0404 | nesting_stock_purchase | PARTIAL | Per stock item: location; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L636) |
| PI-0405 | nesting_stock_purchase | PARTIAL | Per stock item: received date. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L637) |
| PI-0406 | nesting_stock_purchase | PARTIAL | Part moet terug te leiden zijn tot fysieke bron. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L639) |
| PI-0407 | nesting_stock_purchase | PARTIAL | reserve/reopen/release/replan; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L643) |
| PI-0408 | nesting_stock_purchase | PARTIAL | receive; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L644) |
| PI-0409 | nesting_stock_purchase | PARTIAL | partial consumption; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L645) |
| PI-0410 | nesting_stock_purchase | PARTIAL | remnant creation; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L646) |
| PI-0411 | nesting_stock_purchase | PARTIAL | no double booking; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L647) |
| PI-0412 | nesting_stock_purchase | PARTIAL | stock history; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L648) |
| PI-0413 | nesting_stock_purchase | PARTIAL | revision-safe; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L649) |
| PI-0414 | nesting_stock_purchase | PARTIAL | undo waar mogelijk; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L650) |
| PI-0415 | nesting_stock_purchase | PARTIAL | echte profiel- en plaatcases. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L651) |
| PI-0416 | manufacturing_machines | PARTIAL | Maak manufacturing feasibility volledig verklaarbaar. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L659) |
| PI-0417 | manufacturing_machines | PARTIAL | Per machine: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L663) |
| PI-0418 | manufacturing_machines | PARTIAL | Per machine: profile ranges; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L665) |
| PI-0419 | manufacturing_machines | PARTIAL | Per machine: material; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L666) |
| PI-0420 | manufacturing_machines | PARTIAL | Per machine: thickness; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L667) |
| PI-0421 | manufacturing_machines | PARTIAL | Per machine: max length; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L668) |
| PI-0422 | manufacturing_machines | PARTIAL | Per machine: max weight; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L669) |
| PI-0423 | manufacturing_machines | PARTIAL | Per machine: faces; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L670) |
| PI-0424 | manufacturing_machines | PARTIAL | Per machine: drills; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L671) |
| PI-0425 | manufacturing_machines | PARTIAL | Per machine: saw angles; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L672) |
| PI-0426 | manufacturing_machines | PARTIAL | Per machine: milling; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L673) |
| PI-0427 | manufacturing_machines | PARTIAL | Per machine: coping; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L674) |
| PI-0428 | manufacturing_machines | PARTIAL | Per machine: marking; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L675) |
| PI-0429 | manufacturing_machines | PARTIAL | Per machine: scribing; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L676) |
| PI-0430 | manufacturing_machines | PARTIAL | Per machine: clamps; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L677) |
| PI-0431 | manufacturing_machines | PARTIAL | Per machine: dead zones; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L678) |
| PI-0432 | manufacturing_machines | PARTIAL | Per machine: tools; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L679) |
| PI-0433 | manufacturing_machines | PARTIAL | Per machine: postprocessor; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L680) |
| PI-0434 | manufacturing_machines | PARTIAL | Per machine: controller; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L681) |
| PI-0435 | manufacturing_machines | PARTIAL | Per machine: qualification state. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L682) |
| PI-0436 | manufacturing_machines | PARTIAL | Part + features + orientation + machine profile → explicit report. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L686) |
| PI-0437 | manufacturing_machines | PARTIAL | Toon: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L689) |
| PI-0438 | manufacturing_machines | PARTIAL | Toon: eligible; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L691) |
| PI-0439 | manufacturing_machines | PARTIAL | Toon: blocked; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L692) |
| PI-0440 | manufacturing_machines | PARTIAL | Toon: unsupported features; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L693) |
| PI-0441 | manufacturing_machines | PARTIAL | Toon: required transform; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L694) |
| PI-0442 | manufacturing_machines | PARTIAL | Toon: tools; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L695) |
| PI-0443 | manufacturing_machines | PARTIAL | Toon: warnings. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L696) |
| PI-0444 | manufacturing_machines | PARTIAL | Maak volledige installed featurematrix. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L700) |
| PI-0445 | manufacturing_machines | PARTIAL | Test: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L702) |
| PI-0446 | manufacturing_machines | PARTIAL | Test: contacts; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L704) |
| PI-0447 | manufacturing_machines | PARTIAL | Test: faces; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L705) |
| PI-0448 | manufacturing_machines | PARTIAL | Test: orientation; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L706) |
| PI-0449 | manufacturing_machines | PARTIAL | Test: straight; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L707) |
| PI-0450 | manufacturing_machines | PARTIAL | Test: mitre; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L708) |
| PI-0451 | manufacturing_machines | PARTIAL | Test: compound; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L709) |
| PI-0452 | manufacturing_machines | PARTIAL | Test: marking; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L710) |
| PI-0453 | manufacturing_machines | PARTIAL | Test: assembly; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L711) |
| PI-0454 | manufacturing_machines | PARTIAL | Test: revision invalidation; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L712) |
| PI-0455 | manufacturing_machines | PARTIAL | Test: neutral job; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L713) |
| PI-0456 | manufacturing_machines | PARTIAL | Test: invalid geometry; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L714) |
| PI-0457 | manufacturing_machines | PARTIAL | Test: no authority. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L715) |
| PI-0458 | manufacturing_machines | PARTIAL | Per werkelijk gebruikte machine: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L719) |
| PI-0459 | manufacturing_machines | PARTIAL | Per werkelijk gebruikte machine: known input; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L721) |
| PI-0460 | manufacturing_machines | PARTIAL | Per werkelijk gebruikte machine: known machine setup; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L722) |
| PI-0461 | manufacturing_machines | PARTIAL | Per werkelijk gebruikte machine: expected output; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L723) |
| PI-0462 | manufacturing_machines | BLOCKED_EXTERNAL | Per werkelijk gebruikte machine: physical validation. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L724) |
| PI-0463 | manufacturing_machines | PARTIAL | Software CI mag fysieke kwalificatie nooit faken. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L726) |
| PI-0464 | manufacturing_machines | PARTIAL | Bouw geen connection solver na. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L730) |
| PI-0465 | manufacturing_machines | PARTIAL | Bouw bridge via ondersteunde API/interface. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L732) |
| PI-0466 | manufacturing_machines | PARTIAL | Koppel indien beschikbaar: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L734) |
| PI-0467 | manufacturing_machines | PARTIAL | Koppel indien beschikbaar: IDs; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L736) |
| PI-0468 | manufacturing_machines | PARTIAL | Koppel indien beschikbaar: plates; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L737) |
| PI-0469 | manufacturing_machines | PARTIAL | Koppel indien beschikbaar: bolts; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L738) |
| PI-0470 | manufacturing_machines | PARTIAL | Koppel indien beschikbaar: welds; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L739) |
| PI-0471 | manufacturing_machines | PARTIAL | Koppel indien beschikbaar: geometry; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L740) |
| PI-0472 | manufacturing_machines | PARTIAL | Koppel indien beschikbaar: forces; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L741) |
| PI-0473 | manufacturing_machines | PARTIAL | Koppel indien beschikbaar: check state; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L742) |
| PI-0474 | manufacturing_machines | PARTIAL | Koppel indien beschikbaar: revision. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L743) |
| PI-0475 | manufacturing_machines | PARTIAL | Na CWS-wijziging wordt resultaat STALE. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L745) |
| PI-0476 | manufacturing_machines | PARTIAL | machine recommendations verklaarbaar; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L749) |
| PI-0477 | manufacturing_machines | PARTIAL | invalid machine combinations fail closed; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L750) |
| PI-0478 | manufacturing_machines | PARTIAL | M1–M18 installed matrix; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L751) |
| PI-0479 | manufacturing_machines | BLOCKED_EXTERNAL | physical machine items BLOCKED_EXTERNAL totdat werkelijk gevalideerd; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L752) |
| PI-0480 | manufacturing_machines | PARTIAL | no direct transfer without authority. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L753) |
| PI-0481 | production_shopfloor | PARTIAL | Voeg gecontroleerde productie-uitvoering toe. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L761) |
| PI-0482 | production_shopfloor | PARTIAL | Maak `WorkPackage`. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L765) |
| PI-0483 | production_shopfloor | PARTIAL | Velden: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L767) |
| PI-0484 | production_shopfloor | PARTIAL | Velden: id; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L769) |
| PI-0485 | production_shopfloor | PARTIAL | Velden: project; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L770) |
| PI-0486 | production_shopfloor | PARTIAL | Velden: phase; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L771) |
| PI-0487 | production_shopfloor | PARTIAL | Velden: assembly; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L772) |
| PI-0488 | production_shopfloor | PARTIAL | Velden: parts; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L773) |
| PI-0489 | production_shopfloor | PARTIAL | Velden: operation; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L774) |
| PI-0490 | production_shopfloor | PARTIAL | Velden: machine/station; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L775) |
| PI-0491 | production_shopfloor | PARTIAL | Velden: priority; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L776) |
| PI-0492 | production_shopfloor | PARTIAL | Velden: planned; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L777) |
| PI-0493 | production_shopfloor | PARTIAL | Velden: due; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L778) |
| PI-0494 | production_shopfloor | PARTIAL | Velden: operator; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L779) |
| PI-0495 | production_shopfloor | PARTIAL | Velden: estimated time; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L780) |
| PI-0496 | production_shopfloor | PARTIAL | Velden: actual time; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L781) |
| PI-0497 | production_shopfloor | PARTIAL | Velden: material; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L782) |
| PI-0498 | production_shopfloor | PARTIAL | Velden: drawing revision; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L783) |
| PI-0499 | production_shopfloor | PARTIAL | Velden: NC revision; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L784) |
| PI-0500 | production_shopfloor | PARTIAL | Velden: inspections. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L785) |
| PI-0501 | production_shopfloor | PARTIAL | Statuses: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L787) |
| PI-0502 | production_shopfloor | PARTIAL | Statuses: PLANNED | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L789) |
| PI-0503 | production_shopfloor | PARTIAL | Statuses: READY | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L790) |
| PI-0504 | production_shopfloor | PARTIAL | Statuses: BLOCKED | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L791) |
| PI-0505 | production_shopfloor | PARTIAL | Statuses: QUEUED | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L792) |
| PI-0506 | production_shopfloor | PARTIAL | Statuses: IN_PROGRESS | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L793) |
| PI-0507 | production_shopfloor | PARTIAL | Statuses: PAUSED | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L794) |
| PI-0508 | production_shopfloor | PARTIAL | Statuses: COMPLETE | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L795) |
| PI-0509 | production_shopfloor | PARTIAL | Statuses: REJECTED | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L796) |
| PI-0510 | production_shopfloor | PARTIAL | Statuses: REWORK | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L797) |
| PI-0511 | production_shopfloor | PARTIAL | Voorbeeld: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L801) |
| PI-0512 | production_shopfloor | PARTIAL | Saw → Drill → Coping → Welding → Inspection → Coating → Shipping. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L803) |
| PI-0513 | production_shopfloor | PARTIAL | Cut confirmation moet: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L813) |
| PI-0514 | production_shopfloor | PARTIAL | Cut confirmation moet: consume stock; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L815) |
| PI-0515 | production_shopfloor | PARTIAL | Cut confirmation moet: update work package; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L816) |
| PI-0516 | production_shopfloor | PARTIAL | Cut confirmation moet: calculate drop; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L817) |
| PI-0517 | production_shopfloor | PARTIAL | Cut confirmation moet: create remnant; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L818) |
| PI-0518 | production_shopfloor | PARTIAL | Cut confirmation moet: create audit entry. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L819) |
| PI-0519 | production_shopfloor | PARTIAL | Gebruik stabiele canonical ID. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L823) |
| PI-0520 | production_shopfloor | PARTIAL | Support: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L825) |
| PI-0521 | production_shopfloor | PARTIAL | Support: part; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L827) |
| PI-0522 | production_shopfloor | PARTIAL | Support: assembly; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L828) |
| PI-0523 | production_shopfloor | PARTIAL | Support: stock; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L829) |
| PI-0524 | production_shopfloor | PARTIAL | Support: work package; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L830) |
| PI-0525 | production_shopfloor | PARTIAL | Support: shipment. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L831) |
| PI-0526 | production_shopfloor | PARTIAL | work package lifecycle; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L835) |
| PI-0527 | production_shopfloor | PARTIAL | exact source revision; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L836) |
| PI-0528 | production_shopfloor | PARTIAL | stock consumption; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L837) |
| PI-0529 | production_shopfloor | PARTIAL | operator feedback; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L838) |
| PI-0530 | production_shopfloor | PARTIAL | no production on stale drawing/NC; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L839) |
| PI-0531 | production_shopfloor | PARTIAL | save/reopen; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L840) |
| PI-0532 | production_shopfloor | PARTIAL | traceability compleet. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L841) |
| PI-0533 | quality_planning_delivery | PARTIAL | Voeg: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L849) |
| PI-0534 | quality_planning_delivery | PARTIAL | Voeg: InspectionPlan; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L851) |
| PI-0535 | quality_planning_delivery | PARTIAL | Voeg: InspectionRecord; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L852) |
| PI-0536 | quality_planning_delivery | PARTIAL | Voeg: hold points; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L853) |
| PI-0537 | quality_planning_delivery | PARTIAL | Voeg: tolerance; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L854) |
| PI-0538 | quality_planning_delivery | PARTIAL | Voeg: measured values; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L855) |
| PI-0539 | quality_planning_delivery | PARTIAL | Voeg: evidence; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L856) |
| PI-0540 | quality_planning_delivery | PARTIAL | Voeg: PASS/FAIL/REWORK. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L857) |
| PI-0541 | quality_planning_delivery | PARTIAL | Velden: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L861) |
| PI-0542 | quality_planning_delivery | PARTIAL | Velden: NCR ID; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L863) |
| PI-0543 | quality_planning_delivery | PARTIAL | Velden: object; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L864) |
| PI-0544 | quality_planning_delivery | PARTIAL | Velden: issue; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L865) |
| PI-0545 | quality_planning_delivery | PARTIAL | Velden: severity; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L866) |
| PI-0546 | quality_planning_delivery | PARTIAL | Velden: cause; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L867) |
| PI-0547 | quality_planning_delivery | PARTIAL | Velden: action; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L868) |
| PI-0548 | quality_planning_delivery | PARTIAL | Velden: responsible; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L869) |
| PI-0549 | quality_planning_delivery | PARTIAL | Velden: due; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L870) |
| PI-0550 | quality_planning_delivery | PARTIAL | Velden: evidence. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L871) |
| PI-0551 | quality_planning_delivery | PARTIAL | Disposition: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L873) |
| PI-0552 | quality_planning_delivery | PARTIAL | Disposition: rework; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L875) |
| PI-0553 | quality_planning_delivery | PARTIAL | Disposition: accept-as-is; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L876) |
| PI-0554 | quality_planning_delivery | PARTIAL | Disposition: scrap; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L877) |
| PI-0555 | quality_planning_delivery | PARTIAL | Disposition: replace. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L878) |
| PI-0556 | quality_planning_delivery | PARTIAL | Accept-as-is vereist authority. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L880) |
| PI-0557 | quality_planning_delivery | PARTIAL | Koppel: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L884) |
| PI-0558 | quality_planning_delivery | PARTIAL | Koppel: weld type; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L886) |
| PI-0559 | quality_planning_delivery | PARTIAL | Koppel: size; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L887) |
| PI-0560 | quality_planning_delivery | PARTIAL | Koppel: length; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L888) |
| PI-0561 | quality_planning_delivery | PARTIAL | Koppel: process; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L889) |
| PI-0562 | quality_planning_delivery | PARTIAL | Koppel: connected parts; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L890) |
| PI-0563 | quality_planning_delivery | PARTIAL | Koppel: WPS reference waar aanwezig; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L891) |
| PI-0564 | quality_planning_delivery | PARTIAL | Koppel: inspection. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L892) |
| PI-0565 | quality_planning_delivery | PARTIAL | Geen WPS verzinnen. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L894) |
| PI-0566 | quality_planning_delivery | PARTIAL | Resources: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L898) |
| PI-0567 | quality_planning_delivery | PARTIAL | Resources: machines; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L900) |
| PI-0568 | quality_planning_delivery | PARTIAL | Resources: stations; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L901) |
| PI-0569 | quality_planning_delivery | PARTIAL | Resources: labor groups. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L902) |
| PI-0570 | quality_planning_delivery | PARTIAL | Per resource: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L904) |
| PI-0571 | quality_planning_delivery | PARTIAL | Per resource: calendar; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L906) |
| PI-0572 | quality_planning_delivery | PARTIAL | Per resource: shifts; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L907) |
| PI-0573 | quality_planning_delivery | PARTIAL | Per resource: capacity; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L908) |
| PI-0574 | quality_planning_delivery | PARTIAL | Per resource: downtime. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L909) |
| PI-0575 | quality_planning_delivery | PARTIAL | Plan op: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L911) |
| PI-0576 | quality_planning_delivery | PARTIAL | Plan op: due date; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L913) |
| PI-0577 | quality_planning_delivery | PARTIAL | Plan op: priority; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L914) |
| PI-0578 | quality_planning_delivery | PARTIAL | Plan op: material; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L915) |
| PI-0579 | quality_planning_delivery | PARTIAL | Plan op: drawing release; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L916) |
| PI-0580 | quality_planning_delivery | PARTIAL | Plan op: NC; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L917) |
| PI-0581 | quality_planning_delivery | PARTIAL | Plan op: predecessor; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L918) |
| PI-0582 | quality_planning_delivery | PARTIAL | Plan op: machine eligibility. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L919) |
| PI-0583 | quality_planning_delivery | PARTIAL | Voeg: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L923) |
| PI-0584 | quality_planning_delivery | PARTIAL | Voeg: project Gantt; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L925) |
| PI-0585 | quality_planning_delivery | PARTIAL | Voeg: machine Gantt; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L926) |
| PI-0586 | quality_planning_delivery | PARTIAL | Voeg: capacity; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L927) |
| PI-0587 | quality_planning_delivery | PARTIAL | Voeg: overload; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L928) |
| PI-0588 | quality_planning_delivery | PARTIAL | Voeg: bottlenecks. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L929) |
| PI-0589 | quality_planning_delivery | PARTIAL | Ondersteun: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L933) |
| PI-0590 | quality_planning_delivery | PARTIAL | Ondersteun: phase; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L935) |
| PI-0591 | quality_planning_delivery | PARTIAL | Ondersteun: sequence; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L936) |
| PI-0592 | quality_planning_delivery | PARTIAL | Ondersteun: lot; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L937) |
| PI-0593 | quality_planning_delivery | PARTIAL | Ondersteun: delivery batch; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L938) |
| PI-0594 | quality_planning_delivery | PARTIAL | Ondersteun: bundle; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L939) |
| PI-0595 | quality_planning_delivery | PARTIAL | Ondersteun: shipment; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L940) |
| PI-0596 | quality_planning_delivery | PARTIAL | Ondersteun: destination; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L941) |
| PI-0597 | quality_planning_delivery | PARTIAL | Ondersteun: planned/actual delivery. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L942) |
| PI-0598 | quality_planning_delivery | PARTIAL | quality can block production/shipping; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L946) |
| PI-0599 | quality_planning_delivery | PARTIAL | NCR/rework changes status correctly; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L947) |
| PI-0600 | quality_planning_delivery | PARTIAL | planning respects readiness; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L948) |
| PI-0601 | quality_planning_delivery | PARTIAL | no duplicate shipping; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L949) |
| PI-0602 | quality_planning_delivery | PARTIAL | traceable from delivery back to parts/material. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L950) |
| PI-0603 | ui_performance_reporting | PARTIAL | Dashboards: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L958) |
| PI-0604 | ui_performance_reporting | PARTIAL | Dashboards: requested vs produced; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L960) |
| PI-0605 | ui_performance_reporting | PARTIAL | Dashboards: yield; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L961) |
| PI-0606 | ui_performance_reporting | PARTIAL | Dashboards: scrap; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L962) |
| PI-0607 | ui_performance_reporting | PARTIAL | Dashboards: remnants; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L963) |
| PI-0608 | ui_performance_reporting | PARTIAL | Dashboards: shortages; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L964) |
| PI-0609 | ui_performance_reporting | PARTIAL | Dashboards: machine utilization; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L965) |
| PI-0610 | ui_performance_reporting | PARTIAL | Dashboards: planned/actual hours; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L966) |
| PI-0611 | ui_performance_reporting | PARTIAL | Dashboards: throughput; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L967) |
| PI-0612 | ui_performance_reporting | PARTIAL | Dashboards: late work; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L968) |
| PI-0613 | ui_performance_reporting | PARTIAL | Dashboards: quality failures; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L969) |
| PI-0614 | ui_performance_reporting | PARTIAL | Dashboards: rework; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L970) |
| PI-0615 | ui_performance_reporting | PARTIAL | Dashboards: NCR; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L971) |
| PI-0616 | ui_performance_reporting | PARTIAL | Dashboards: revision impact; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L972) |
| PI-0617 | ui_performance_reporting | PARTIAL | Dashboards: delivery completeness. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L973) |
| PI-0618 | ui_performance_reporting | PARTIAL | Iedere KPI drilldown naar brondata. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L975) |
| PI-0619 | ui_performance_reporting | PARTIAL | Maak consistent: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L979) |
| PI-0620 | ui_performance_reporting | PARTIAL | Maak consistent: Viewer; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L981) |
| PI-0621 | ui_performance_reporting | PARTIAL | Maak consistent: Controleren; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L982) |
| PI-0622 | ui_performance_reporting | PARTIAL | Maak consistent: Bewerken; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L983) |
| PI-0623 | ui_performance_reporting | PARTIAL | Maak consistent: BOM; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L984) |
| PI-0624 | ui_performance_reporting | PARTIAL | Maak consistent: Drawing; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L985) |
| PI-0625 | ui_performance_reporting | PARTIAL | Maak consistent: Profile nesting; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L986) |
| PI-0626 | ui_performance_reporting | PARTIAL | Maak consistent: Plate nesting; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L987) |
| PI-0627 | ui_performance_reporting | PARTIAL | Maak consistent: Machines; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L988) |
| PI-0628 | ui_performance_reporting | PARTIAL | Maak consistent: Stock/Purchase; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L989) |
| PI-0629 | ui_performance_reporting | PARTIAL | Maak consistent: Planning; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L990) |
| PI-0630 | ui_performance_reporting | PARTIAL | Maak consistent: Production; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L991) |
| PI-0631 | ui_performance_reporting | PARTIAL | Maak consistent: Quality; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L992) |
| PI-0632 | ui_performance_reporting | PARTIAL | Maak consistent: Delivery; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L993) |
| PI-0633 | ui_performance_reporting | PARTIAL | Maak consistent: Reporting; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L994) |
| PI-0634 | ui_performance_reporting | PARTIAL | Maak consistent: Export. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L995) |
| PI-0635 | ui_performance_reporting | PARTIAL | Test: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L997) |
| PI-0636 | ui_performance_reporting | PARTIAL | Test: 100%; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L999) |
| PI-0637 | ui_performance_reporting | PARTIAL | Test: 125%; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1000) |
| PI-0638 | ui_performance_reporting | PARTIAL | Test: 150%; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1001) |
| PI-0639 | ui_performance_reporting | PARTIAL | Test: 175%; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1002) |
| PI-0640 | ui_performance_reporting | PARTIAL | Test: 200% DPI; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1003) |
| PI-0641 | ui_performance_reporting | PARTIAL | Test: 1080p; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1004) |
| PI-0642 | ui_performance_reporting | PARTIAL | Test: 1440p; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1005) |
| PI-0643 | ui_performance_reporting | PARTIAL | Test: 4K; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1006) |
| PI-0644 | ui_performance_reporting | PARTIAL | Test: small window; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1007) |
| PI-0645 | ui_performance_reporting | PARTIAL | Test: multi-monitor waar beschikbaar; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1008) |
| PI-0646 | ui_performance_reporting | PARTIAL | Test: keyboard. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1009) |
| PI-0647 | ui_performance_reporting | PARTIAL | Test finale EXE met: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1013) |
| PI-0648 | ui_performance_reporting | PARTIAL | Test finale EXE met: HVPC; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1015) |
| PI-0649 | ui_performance_reporting | PARTIAL | Test finale EXE met: tweede groot project. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1016) |
| PI-0650 | ui_performance_reporting | PARTIAL | Targets: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1018) |
| PI-0651 | ui_performance_reporting | PARTIAL | Targets: cold exact ≤5 s; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1020) |
| PI-0652 | ui_performance_reporting | PARTIAL | Targets: first usable preferably ≤3 s; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1021) |
| PI-0653 | ui_performance_reporting | PARTIAL | Targets: mean FPS ≥30; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1022) |
| PI-0654 | ui_performance_reporting | PARTIAL | Targets: frame p95 ≤33 ms; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1023) |
| PI-0655 | ui_performance_reporting | PARTIAL | Targets: input p95 ≤35 ms; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1024) |
| PI-0656 | ui_performance_reporting | PARTIAL | Targets: input p99 ≤50 ms; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1025) |
| PI-0657 | ui_performance_reporting | PARTIAL | Targets: pick p95 ≤150 ms; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1026) |
| PI-0658 | ui_performance_reporting | PARTIAL | Targets: zero freezes >100 ms; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1027) |
| PI-0659 | ui_performance_reporting | PARTIAL | Targets: RSS drift <10%. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1028) |
| PI-0660 | ui_performance_reporting | BLOCKED_EXTERNAL | Gebruik fysieke GPU voor final acceptance. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1030) |
| PI-0661 | ui_performance_reporting | PARTIAL | geen clipping; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1034) |
| PI-0662 | ui_performance_reporting | PARTIAL | geen onleesbare DPI states; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1035) |
| PI-0663 | ui_performance_reporting | PARTIAL | model dominant waar bedoeld; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1036) |
| PI-0664 | ui_performance_reporting | PARTIAL | performance report source-bound; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1037) |
| PI-0665 | ui_performance_reporting | PARTIAL | old performance measurements niet hergebruiken. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1038) |
| PI-0666 | installer_release_e2e | PARTIAL | Moet bevatten: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1048) |
| PI-0667 | installer_release_e2e | PARTIAL | Moet bevatten: profiles; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1050) |
| PI-0668 | installer_release_e2e | PARTIAL | Moet bevatten: plates; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1051) |
| PI-0669 | installer_release_e2e | PARTIAL | Moet bevatten: assemblies; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1052) |
| PI-0670 | installer_release_e2e | PARTIAL | Moet bevatten: bolts; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1053) |
| PI-0671 | installer_release_e2e | PARTIAL | Moet bevatten: welds; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1054) |
| PI-0672 | installer_release_e2e | PARTIAL | Moet bevatten: purchased items; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1055) |
| PI-0673 | installer_release_e2e | PARTIAL | Moet bevatten: stock; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1056) |
| PI-0674 | installer_release_e2e | PARTIAL | Moet bevatten: drawings; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1057) |
| PI-0675 | installer_release_e2e | PARTIAL | Moet bevatten: nesting; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1058) |
| PI-0676 | installer_release_e2e | PARTIAL | Moet bevatten: machine; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1059) |
| PI-0677 | installer_release_e2e | PARTIAL | Moet bevatten: production; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1060) |
| PI-0678 | installer_release_e2e | PARTIAL | Moet bevatten: inspection; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1061) |
| PI-0679 | installer_release_e2e | PARTIAL | Moet bevatten: shipping. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1062) |
| PI-0680 | installer_release_e2e | PARTIAL | Moet bevatten: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1066) |
| PI-0681 | installer_release_e2e | PARTIAL | Moet bevatten: custom profiles; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1068) |
| PI-0682 | installer_release_e2e | PARTIAL | Moet bevatten: unusual extrusions; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1069) |
| PI-0683 | installer_release_e2e | PARTIAL | Moet bevatten: compound solids; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1070) |
| PI-0684 | installer_release_e2e | PARTIAL | Moet bevatten: mixed formats; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1071) |
| PI-0685 | installer_release_e2e | PARTIAL | Moet bevatten: missing metadata; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1072) |
| PI-0686 | installer_release_e2e | PARTIAL | Moet bevatten: external PDF. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1073) |
| PI-0687 | installer_release_e2e | PARTIAL | Voor beide projecten: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1077) |
| PI-0688 | installer_release_e2e | PARTIAL | R1 volledige workflow. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1079) |
| PI-0689 | installer_release_e2e | PARTIAL | Daarna R2: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1081) |
| PI-0690 | installer_release_e2e | PARTIAL | Daarna R2: changed object; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1083) |
| PI-0691 | installer_release_e2e | PARTIAL | Daarna R2: added object; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1084) |
| PI-0692 | installer_release_e2e | PARTIAL | Daarna R2: deleted object; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1085) |
| PI-0693 | installer_release_e2e | PARTIAL | Daarna R2: moved object; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1086) |
| PI-0694 | installer_release_e2e | PARTIAL | Daarna R2: changed manufacturing feature. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1087) |
| PI-0695 | installer_release_e2e | PARTIAL | Controleer: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1089) |
| PI-0696 | installer_release_e2e | PARTIAL | Import → Recognition → Review → BOM → Stock → Nesting → Drawing → Machine → Production → Quality → Export → Delivery → Reopen. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1091) |
| PI-0697 | installer_release_e2e | PARTIAL | Finale SHA testen op Windows 11: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1107) |
| PI-0698 | installer_release_e2e | PARTIAL | Finale SHA testen op Windows 11: clean; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1109) |
| PI-0699 | installer_release_e2e | PARTIAL | Finale SHA testen op Windows 11: standard user; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1110) |
| PI-0700 | installer_release_e2e | PARTIAL | Finale SHA testen op Windows 11: admin; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1111) |
| PI-0701 | installer_release_e2e | PARTIAL | Finale SHA testen op Windows 11: default path; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1112) |
| PI-0702 | installer_release_e2e | PARTIAL | Finale SHA testen op Windows 11: custom path; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1113) |
| PI-0703 | installer_release_e2e | PARTIAL | Finale SHA testen op Windows 11: onefolder; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1114) |
| PI-0704 | installer_release_e2e | PARTIAL | Finale SHA testen op Windows 11: portable; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1115) |
| PI-0705 | installer_release_e2e | PARTIAL | Finale SHA testen op Windows 11: installer; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1116) |
| PI-0706 | installer_release_e2e | PARTIAL | Finale SHA testen op Windows 11: repair; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1117) |
| PI-0707 | installer_release_e2e | PARTIAL | Finale SHA testen op Windows 11: upgrade; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1118) |
| PI-0708 | installer_release_e2e | PARTIAL | Finale SHA testen op Windows 11: rollback; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1119) |
| PI-0709 | installer_release_e2e | PARTIAL | Finale SHA testen op Windows 11: reboot; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1120) |
| PI-0710 | installer_release_e2e | PARTIAL | Finale SHA testen op Windows 11: uninstall; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1121) |
| PI-0711 | installer_release_e2e | PARTIAL | Finale SHA testen op Windows 11: associations; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1122) |
| PI-0712 | installer_release_e2e | PARTIAL | Finale SHA testen op Windows 11: reopen projects/settings. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1123) |
| PI-0713 | installer_release_e2e | PARTIAL | Splits: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1127) |
| PI-0714 | installer_release_e2e | PARTIAL | BUILD | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1129) |
| PI-0715 | installer_release_e2e | PARTIAL | en | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1131) |
| PI-0716 | installer_release_e2e | PARTIAL | PROMOTE. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1133) |
| PI-0717 | installer_release_e2e | PARTIAL | PROMOTE vereist alle verplichte gates. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1135) |
| PI-0718 | installer_release_e2e | PARTIAL | sign installer; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1139) |
| PI-0719 | installer_release_e2e | PARTIAL | timestamp; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1140) |
| PI-0720 | installer_release_e2e | PARTIAL | verify publisher; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1141) |
| PI-0721 | installer_release_e2e | PARTIAL | recalculate hashes. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1142) |
| PI-0722 | installer_release_e2e | PARTIAL | Genereer artifact-bound SBOM: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1146) |
| PI-0723 | installer_release_e2e | PARTIAL | Genereer artifact-bound SBOM: Python; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1148) |
| PI-0724 | installer_release_e2e | PARTIAL | Genereer artifact-bound SBOM: Qt/PySide; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1149) |
| PI-0725 | installer_release_e2e | PARTIAL | Genereer artifact-bound SBOM: VTK; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1150) |
| PI-0726 | installer_release_e2e | PARTIAL | Genereer artifact-bound SBOM: OCCT/CadQuery; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1151) |
| PI-0727 | installer_release_e2e | PARTIAL | Genereer artifact-bound SBOM: IFCOpenShell; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1152) |
| PI-0728 | installer_release_e2e | PARTIAL | Genereer artifact-bound SBOM: native DLLs; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1153) |
| PI-0729 | installer_release_e2e | PARTIAL | Genereer artifact-bound SBOM: other runtime components. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1154) |
| PI-0730 | installer_release_e2e | PARTIAL | Leg vast: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1156) |
| PI-0731 | installer_release_e2e | PARTIAL | Leg vast: version; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1158) |
| PI-0732 | installer_release_e2e | PARTIAL | Leg vast: source; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1159) |
| PI-0733 | installer_release_e2e | PARTIAL | Leg vast: license; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1160) |
| PI-0734 | installer_release_e2e | PARTIAL | Leg vast: CVE scan; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1161) |
| PI-0735 | installer_release_e2e | PARTIAL | Leg vast: disposition. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1162) |
| PI-0736 | installer_release_e2e | PARTIAL | finale source SHA = tested SHA; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1166) |
| PI-0737 | installer_release_e2e | PARTIAL | final installer = tested binary; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1167) |
| PI-0738 | installer_release_e2e | PARTIAL | two end-to-end projects PASS; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1168) |
| PI-0739 | installer_release_e2e | PARTIAL | no open P0/P1 software gaps; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1169) |
| PI-0740 | installer_release_e2e | PARTIAL | external items clearly marked; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1170) |
| PI-0741 | installer_release_e2e | PARTIAL | checksums available; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1171) |
| PI-0742 | installer_release_e2e | PARTIAL | release manifest; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1172) |
| PI-0743 | installer_release_e2e | PARTIAL | SBOM; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1173) |
| PI-0744 | installer_release_e2e | PARTIAL | signed installer indien bedrijfsrelease vereist. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1174) |
| PI-0745 | product_integration | PARTIAL | Streef naar onderstaande workspaces: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1180) |
| PI-0746 | product_integration | PARTIAL | Streef naar onderstaande workspaces: 1. Start / Project | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1182) |
| PI-0747 | product_integration | PARTIAL | Streef naar onderstaande workspaces: 2. Viewer | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1183) |
| PI-0748 | product_integration | PARTIAL | Streef naar onderstaande workspaces: 3. Controleren | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1184) |
| PI-0749 | product_integration | PARTIAL | Streef naar onderstaande workspaces: 4. Bewerken | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1185) |
| PI-0750 | product_integration | PARTIAL | Streef naar onderstaande workspaces: 5. BOM / Productiehub | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1186) |
| PI-0751 | product_integration | PARTIAL | Streef naar onderstaande workspaces: 6. Tekeningen | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1187) |
| PI-0752 | product_integration | PARTIAL | Streef naar onderstaande workspaces: 7. Profielnesting | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1188) |
| PI-0753 | product_integration | PARTIAL | Streef naar onderstaande workspaces: 8. Plaatnesting | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1189) |
| PI-0754 | product_integration | PARTIAL | Streef naar onderstaande workspaces: 9. Machines | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1190) |
| PI-0755 | product_integration | PARTIAL | Streef naar onderstaande workspaces: 10. Voorraad & Inkoop | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1191) |
| PI-0756 | product_integration | PARTIAL | Streef naar onderstaande workspaces: 11. Planning | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1192) |
| PI-0757 | product_integration | PARTIAL | Streef naar onderstaande workspaces: 12. Productie | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1193) |
| PI-0758 | product_integration | PARTIAL | Streef naar onderstaande workspaces: 13. Kwaliteit | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1194) |
| PI-0759 | product_integration | PARTIAL | Streef naar onderstaande workspaces: 14. Levering | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1195) |
| PI-0760 | product_integration | PARTIAL | Streef naar onderstaande workspaces: 15. Rapportage | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1196) |
| PI-0761 | product_integration | PARTIAL | Streef naar onderstaande workspaces: 16. Export | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1197) |
| PI-0762 | product_integration | PARTIAL | Streef naar onderstaande workspaces: 17. Instellingen / Bibliotheken | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1198) |
| PI-0763 | product_integration | PARTIAL | Bestaande workspaces niet vervangen wanneer ze al correct functioneren. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1200) |
| PI-0764 | product_integration | PARTIAL | Integreer nieuwe functionaliteit in bestaande architectuur. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1202) |
| PI-0765 | product_integration | PARTIAL | Alle workspaces moeten één gedeeld ProjectModel gebruiken. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1208) |
| PI-0766 | product_integration | PARTIAL | Geen tweede waarheid. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1210) |
| PI-0767 | product_integration | PARTIAL | Objecttypen minimaal: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1212) |
| PI-0768 | product_integration | PARTIAL | Objecttypen minimaal: Part | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1214) |
| PI-0769 | product_integration | PARTIAL | Objecttypen minimaal: Assembly | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1215) |
| PI-0770 | product_integration | PARTIAL | Objecttypen minimaal: PurchasedItem | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1216) |
| PI-0771 | product_integration | PARTIAL | Objecttypen minimaal: Fastener | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1217) |
| PI-0772 | product_integration | PARTIAL | Objecttypen minimaal: Weld | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1218) |
| PI-0773 | product_integration | PARTIAL | Objecttypen minimaal: StockItem | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1219) |
| PI-0774 | product_integration | PARTIAL | Objecttypen minimaal: Remnant | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1220) |
| PI-0775 | product_integration | PARTIAL | Objecttypen minimaal: Drawing | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1221) |
| PI-0776 | product_integration | PARTIAL | Objecttypen minimaal: Revision | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1222) |
| PI-0777 | product_integration | PARTIAL | Objecttypen minimaal: MachineAssignment | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1223) |
| PI-0778 | product_integration | PARTIAL | Objecttypen minimaal: ProductionRelease | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1224) |
| PI-0779 | product_integration | PARTIAL | Objecttypen minimaal: Inspection | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1225) |
| PI-0780 | product_integration | PARTIAL | Objecttypen minimaal: WorkPackage | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1226) |
| PI-0781 | product_integration | PARTIAL | Objecttypen minimaal: Shipment | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1227) |
| PI-0782 | product_integration | PARTIAL | Traceability: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1229) |
| PI-0783 | product_integration | PARTIAL | Source → Canonical entity → Manufacturing → BOM → Drawing → Nest → Stock → Machine → Production → Quality → Delivery. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1231) |
| PI-0784 | product_integration | PARTIAL | Geen: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1247) |
| PI-0785 | product_integration | PARTIAL | Geen: hardcoded PASS; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1249) |
| PI-0786 | product_integration | PARTIAL | Geen: fictieve geometrie; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1250) |
| PI-0787 | product_integration | PARTIAL | Geen: fictief materiaal; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1251) |
| PI-0788 | product_integration | PARTIAL | Geen: fictieve voorraad; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1252) |
| PI-0789 | product_integration | PARTIAL | Geen: false production_ready; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1253) |
| PI-0790 | product_integration | PARTIAL | Geen: machine transfer zonder qualification; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1254) |
| PI-0791 | product_integration | PARTIAL | Geen: silent selection widening; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1255) |
| PI-0792 | product_integration | PARTIAL | Geen: stale output als current; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1256) |
| PI-0793 | product_integration | PARTIAL | Geen: test die alleen aanwezigheid controleert. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1257) |
| PI-0794 | product_integration | PARTIAL | Fail closed wanneer authority ontbreekt. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1259) |
| PI-0795 | product_integration | PARTIAL | Voor iedere wijziging: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1265) |
| PI-0796 | product_integration | PARTIAL | Voor iedere wijziging: 1. inspect; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1267) |
| PI-0797 | product_integration | PARTIAL | Voor iedere wijziging: 2. implement; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1268) |
| PI-0798 | product_integration | PARTIAL | Voor iedere wijziging: 3. compile; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1269) |
| PI-0799 | product_integration | PARTIAL | Voor iedere wijziging: 4. focused test; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1270) |
| PI-0800 | product_integration | PARTIAL | Voor iedere wijziging: 5. integration test; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1271) |
| PI-0801 | product_integration | PARTIAL | Voor iedere wijziging: 6. regression; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1272) |
| PI-0802 | product_integration | PARTIAL | Voor iedere wijziging: 7. Windows test indien relevant; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1273) |
| PI-0803 | product_integration | PARTIAL | Voor iedere wijziging: 8. evidence; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1274) |
| PI-0804 | product_integration | PARTIAL | Voor iedere wijziging: 9. commit; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1275) |
| PI-0805 | product_integration | PARTIAL | Voor iedere wijziging: 10. push. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1276) |
| PI-0806 | product_integration | PARTIAL | Kleine commits. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1278) |
| PI-0807 | product_integration | PARTIAL | Geen force. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1280) |
| PI-0808 | product_integration | PARTIAL | Iedere evidencefile bevat: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1286) |
| PI-0809 | product_integration | PARTIAL | Iedere evidencefile bevat: commit; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1288) |
| PI-0810 | product_integration | PARTIAL | Iedere evidencefile bevat: app version; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1289) |
| PI-0811 | product_integration | PARTIAL | Iedere evidencefile bevat: environment; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1290) |
| PI-0812 | product_integration | PARTIAL | Iedere evidencefile bevat: input hash; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1291) |
| PI-0813 | product_integration | PARTIAL | Iedere evidencefile bevat: scenario; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1292) |
| PI-0814 | product_integration | PARTIAL | Iedere evidencefile bevat: result; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1293) |
| PI-0815 | product_integration | PARTIAL | Iedere evidencefile bevat: output hash. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1294) |
| PI-0816 | product_integration | PARTIAL | Screenshots moeten echte runtime zijn. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1296) |
| PI-0817 | product_integration | PARTIAL | Geen illustraties als acceptance evidence. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1298) |
| PI-0818 | product_integration | PARTIAL | Na elk bouwblok genereer: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1304) |
| PI-0819 | product_integration | PARTIAL | Na elk bouwblok genereer: implemented; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1306) |
| PI-0820 | product_integration | PARTIAL | Na elk bouwblok genereer: partial; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1307) |
| PI-0821 | product_integration | PARTIAL | Na elk bouwblok genereer: missing; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1308) |
| PI-0822 | product_integration | PARTIAL | Na elk bouwblok genereer: tested; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1309) |
| PI-0823 | product_integration | PARTIAL | Na elk bouwblok genereer: installed; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1310) |
| PI-0824 | product_integration | PARTIAL | Na elk bouwblok genereer: real-file; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1311) |
| PI-0825 | product_integration | PARTIAL | Na elk bouwblok genereer: external; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1312) |
| PI-0826 | product_integration | PARTIAL | Na elk bouwblok genereer: blockers. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1313) |
| PI-0827 | product_integration | PARTIAL | Percentages afzonderlijk voor: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1315) |
| PI-0828 | product_integration | PARTIAL | Percentages afzonderlijk voor: 1. functioneel gebouwd; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1317) |
| PI-0829 | product_integration | PARTIAL | Percentages afzonderlijk voor: 2. integration tested; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1318) |
| PI-0830 | product_integration | PARTIAL | Percentages afzonderlijk voor: 3. installed tested; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1319) |
| PI-0831 | product_integration | PARTIAL | Percentages afzonderlijk voor: 4. real-world tested; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1320) |
| PI-0832 | product_integration | PARTIAL | Percentages afzonderlijk voor: 5. release ready. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1321) |
| PI-0833 | product_integration | PARTIAL | Geen cosmetisch totaalpercentage. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1323) |
| PI-0834 | product_integration | PARTIAL | Stop een specifieke actie en rapporteer een blocker wanneer: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1329) |
| PI-0835 | product_integration | PARTIAL | Stop een specifieke actie en rapporteer een blocker wanneer: required source ontbreekt; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1331) |
| PI-0836 | product_integration | PARTIAL | Stop een specifieke actie en rapporteer een blocker wanneer: materiaal authority ontbreekt; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1332) |
| PI-0837 | product_integration | PARTIAL | Stop een specifieke actie en rapporteer een blocker wanneer: machine qualification ontbreekt; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1333) |
| PI-0838 | product_integration | PARTIAL | Stop een specifieke actie en rapporteer een blocker wanneer: physical printer acceptance nodig is; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1334) |
| PI-0839 | product_integration | PARTIAL | Stop een specifieke actie en rapporteer een blocker wanneer: external BCF application nodig is; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1335) |
| PI-0840 | product_integration | PARTIAL | Stop een specifieke actie en rapporteer een blocker wanneer: user/business decision nodig is. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1336) |
| PI-0841 | product_integration | PARTIAL | Ga vervolgens verder met andere onafhankelijke softwarematige taken. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1338) |
| PI-0842 | product_integration | PARTIAL | Vraag niet routinematig om toestemming. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1340) |
| PI-0843 | product_integration | PARTIAL | Niet uitbreiden naar volledig: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1346) |
| PI-0844 | product_integration | OUT_OF_SCOPE_APPROVED | Niet uitbreiden naar volledig: ERP; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1348) |
| PI-0845 | product_integration | OUT_OF_SCOPE_APPROVED | Niet uitbreiden naar volledig: accounting; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1349) |
| PI-0846 | product_integration | OUT_OF_SCOPE_APPROVED | Niet uitbreiden naar volledig: payroll; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1350) |
| PI-0847 | product_integration | OUT_OF_SCOPE_APPROVED | Niet uitbreiden naar volledig: HR; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1351) |
| PI-0848 | product_integration | OUT_OF_SCOPE_APPROVED | Niet uitbreiden naar volledig: CRM; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1352) |
| PI-0849 | product_integration | OUT_OF_SCOPE_APPROVED | Niet uitbreiden naar volledig: Revit replacement; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1353) |
| PI-0850 | product_integration | OUT_OF_SCOPE_APPROVED | Niet uitbreiden naar volledig: Tekla replacement; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1354) |
| PI-0851 | product_integration | OUT_OF_SCOPE_APPROVED | Niet uitbreiden naar volledig: structural calculation suite; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1355) |
| PI-0852 | product_integration | OUT_OF_SCOPE_APPROVED | Niet uitbreiden naar volledig: generic cloud CDE. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1356) |
| PI-0853 | product_integration | PARTIAL | Integraties zijn toegestaan. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1358) |
| PI-0854 | product_integration | PARTIAL | Cloud/multi-user/pointcloud/sync is geen huidige desktop blocker tenzij expliciet opnieuw als release-eis bevestigd. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1364) |
| PI-0855 | product_integration | PARTIAL | Local openBIM/BCF/IDS wel. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1366) |
| PI-0856 | product_integration | PARTIAL | Een bouwblok is pas `DONE` indien: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1372) |
| PI-0857 | product_integration | PARTIAL | Een bouwblok is pas `DONE` indien: implementation complete; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1374) |
| PI-0858 | product_integration | PARTIAL | Een bouwblok is pas `DONE` indien: source tests PASS; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1375) |
| PI-0859 | product_integration | PARTIAL | Een bouwblok is pas `DONE` indien: integration tests PASS; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1376) |
| PI-0860 | product_integration | PARTIAL | Een bouwblok is pas `DONE` indien: applicable Windows tests PASS; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1377) |
| PI-0861 | product_integration | PARTIAL | Een bouwblok is pas `DONE` indien: no regression; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1378) |
| PI-0862 | product_integration | PARTIAL | Een bouwblok is pas `DONE` indien: evidence generated; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1379) |
| PI-0863 | product_integration | PARTIAL | Een bouwblok is pas `DONE` indien: commit pushed; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1380) |
| PI-0864 | product_integration | PARTIAL | Een bouwblok is pas `DONE` indien: gap register updated. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1381) |
| PI-0865 | product_integration | PARTIAL | Anders: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1383) |
| PI-0866 | product_integration | PARTIAL | `PARTIAL` of `BLOCKED_EXTERNAL`. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1385) |
| PI-0867 | product_integration | PARTIAL | Noem CWS Convertor uitsluitend **100% gereed** wanneer: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1391) |
| PI-0868 | product_integration | PARTIAL | Noem CWS Convertor uitsluitend **100% gereed** wanneer: alle toepasselijke Master Requirements V2 PASS zijn; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1393) |
| PI-0869 | product_integration | PARTIAL | Noem CWS Convertor uitsluitend **100% gereed** wanneer: alle 87 BOM-acties positief én negatief bewezen zijn; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1394) |
| PI-0870 | product_integration | PARTIAL | Noem CWS Convertor uitsluitend **100% gereed** wanneer: echte recognition corpus voldoende dekking heeft; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1395) |
| PI-0871 | product_integration | PARTIAL | Noem CWS Convertor uitsluitend **100% gereed** wanneer: converter-matrix sluit; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1396) |
| PI-0872 | product_integration | PARTIAL | Noem CWS Convertor uitsluitend **100% gereed** wanneer: Viewer native/performance-evidence sluit; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1397) |
| PI-0873 | product_integration | PARTIAL | Noem CWS Convertor uitsluitend **100% gereed** wanneer: drawing/change-impact sluit; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1398) |
| PI-0874 | product_integration | PARTIAL | Noem CWS Convertor uitsluitend **100% gereed** wanneer: stock lifecycle sluit; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1399) |
| PI-0875 | product_integration | PARTIAL | Noem CWS Convertor uitsluitend **100% gereed** wanneer: nesting benchmark sluit; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1400) |
| PI-0876 | product_integration | PARTIAL | Noem CWS Convertor uitsluitend **100% gereed** wanneer: M1–M18 installed sluit; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1401) |
| PI-0877 | product_integration | PARTIAL | Noem CWS Convertor uitsluitend **100% gereed** wanneer: twee representatieve R1/R2-projecten end-to-end sluiten; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1402) |
| PI-0878 | product_integration | PARTIAL | Noem CWS Convertor uitsluitend **100% gereed** wanneer: final Windows build exact bij geteste source hoort; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1403) |
| PI-0879 | product_integration | PARTIAL | Noem CWS Convertor uitsluitend **100% gereed** wanneer: geen open P0/P1 softwaregap resteert; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1404) |
| PI-0880 | product_integration | PARTIAL | Noem CWS Convertor uitsluitend **100% gereed** wanneer: external machine/printer/hardwarepunten werkelijk zijn uitgevoerd of expliciet BLOCKED_EXTERNAL blijven; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1405) |
| PI-0881 | product_integration | PARTIAL | Noem CWS Convertor uitsluitend **100% gereed** wanneer: geen unsupported claim als PASS wordt gepresenteerd. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1406) |
| PI-0882 | product_integration | PARTIAL | Lever: | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1412) |
| PI-0883 | product_integration | PARTIAL | Lever: branch; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1414) |
| PI-0884 | product_integration | PARTIAL | Lever: final SHA; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1415) |
| PI-0885 | product_integration | PARTIAL | Lever: commits per bouwblok; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1416) |
| PI-0886 | product_integration | PARTIAL | Lever: Master Requirements V2; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1417) |
| PI-0887 | product_integration | PARTIAL | Lever: tests per blok; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1418) |
| PI-0888 | product_integration | PARTIAL | Lever: complete recognition report; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1419) |
| PI-0889 | product_integration | PARTIAL | Lever: conversion report; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1420) |
| PI-0890 | product_integration | PARTIAL | Lever: BOM 87 report; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1421) |
| PI-0891 | product_integration | PARTIAL | Lever: Viewer report; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1422) |
| PI-0892 | product_integration | PARTIAL | Lever: Drawing report; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1423) |
| PI-0893 | product_integration | PARTIAL | Lever: nesting benchmarks; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1424) |
| PI-0894 | product_integration | PARTIAL | Lever: stock lifecycle report; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1425) |
| PI-0895 | product_integration | PARTIAL | Lever: M1–M18 report; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1426) |
| PI-0896 | product_integration | PARTIAL | Lever: shopfloor report; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1427) |
| PI-0897 | product_integration | PARTIAL | Lever: quality/planning report; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1428) |
| PI-0898 | product_integration | PARTIAL | Lever: R1/R2 end-to-end reports; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1429) |
| PI-0899 | product_integration | PARTIAL | Lever: Windows installer; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1430) |
| PI-0900 | product_integration | PARTIAL | Lever: portable; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1431) |
| PI-0901 | product_integration | PARTIAL | Lever: checksums; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1432) |
| PI-0902 | product_integration | PARTIAL | Lever: signing status; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1433) |
| PI-0903 | product_integration | PARTIAL | Lever: SBOM; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1434) |
| PI-0904 | product_integration | PARTIAL | Lever: remaining external blockers; | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1435) |
| PI-0905 | product_integration | PARTIAL | Lever: finale GAP-analyse. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1436) |
| PI-0906 | product_integration | PARTIAL | Bouw het bestaande CWS Convertor gecontroleerd af. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1438) |
| PI-0907 | product_integration | PARTIAL | Geen parallel vervangend programma. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1440) |
| PI-0908 | product_integration | PARTIAL | Geen cosmetische 100%. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1442) |
| PI-0909 | product_integration | PARTIAL | Traceability, reproduceerbaarheid en fail-closed productieautoriteit zijn leidend. | requirements/sources/CWS_PRODUCT_INTEGRATION_RELEASE_20260912.md (L1444) |
| PDFUI3-0001 | pdf_ui_v3 | PARTIAL | Werk deze opdracht in één aaneengesloten build volledig uit in de bestaande repository `CoenWessselink/Convertor`. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L5) |
| PDFUI3-0002 | pdf_ui_v3 | PARTIAL | Integreer de interactieve PDF-/tekeningenwerkruimte als een volwaardig onderdeel van het totale CWS Convertor-pakket. Gebruik de drie meegeleverde afbeeldingen uitsluitend als visueel referentiedoel. Bouw alle bediening native in de bestaande PySide6-applicatie; toon de mock-ups niet als vervanging voor werkende UI en gebruik geen statische nepknoppen, vooraf getekende maatvoering of hardcoded bewijsresultaten. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L7) |
| PDFUI3-0003 | pdf_ui_v3 | PARTIAL | De actuele ontwikkellijn bevat reeds de PDF-V2-functies, projectpersistentie, echte EXE-herstarttest en Viewer-correcties. Behoud deze werking. Start met het vastleggen van branch, exacte HEAD, tree-hash en werkboomstatus. Lees `AGENTS.md` en alle repository-instructies volledig. Verwijder of overschrijf geen bestaande gebruikerswijzigingen. Werk vanaf de actuele branch en niet vanaf een oudere snapshot. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L9) |
| PDFUI3-0004 | pdf_ui_v3 | PARTIAL | Gebruik deze bestanden relatief aan dit document: | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L13) |
| PDFUI3-0005 | pdf_ui_v3 | PARTIAL | Gebruik deze bestanden relatief aan dit document: 1. `references/01_PDF_WERKRUIMTE_VOLLEDIG.png` | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L15) |
| PDFUI3-0006 | pdf_ui_v3 | PARTIAL | Gebruik deze bestanden relatief aan dit document: volledige PDF-/tekeningenwerkruimte; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L16) |
| PDFUI3-0007 | pdf_ui_v3 | PARTIAL | Gebruik deze bestanden relatief aan dit document: linker productnavigatie; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L17) |
| PDFUI3-0008 | pdf_ui_v3 | PARTIAL | Gebruik deze bestanden relatief aan dit document: compacte maatvoering-toolbar; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L18) |
| PDFUI3-0009 | pdf_ui_v3 | PARTIAL | Gebruik deze bestanden relatief aan dit document: centrale A3-tekening; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L19) |
| PDFUI3-0010 | pdf_ui_v3 | PARTIAL | Gebruik deze bestanden relatief aan dit document: rechter eigenschappeninspecteur; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L20) |
| PDFUI3-0011 | pdf_ui_v3 | PARTIAL | Gebruik deze bestanden relatief aan dit document: formaat, oriëntatie, schaal en PASS-status. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L21) |
| PDFUI3-0012 | pdf_ui_v3 | PARTIAL | Gebruik deze bestanden relatief aan dit document: 2. `references/02_MAAT_SELECTEREN_EN_BEWERKEN.png` | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L22) |
| PDFUI3-0013 | pdf_ui_v3 | PARTIAL | Gebruik deze bestanden relatief aan dit document: bestaande maat selecteren; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L23) |
| PDFUI3-0014 | pdf_ui_v3 | PARTIAL | Gebruik deze bestanden relatief aan dit document: geometrische ankerpunten en snapmarkeringen; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L24) |
| PDFUI3-0015 | pdf_ui_v3 | PARTIAL | Gebruik deze bestanden relatief aan dit document: maatlijn- en tekstgrips; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L25) |
| PDFUI3-0016 | pdf_ui_v3 | PARTIAL | Gebruik deze bestanden relatief aan dit document: opnieuw ankeren, verwijderen, verbergen, undo en redo; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L26) |
| PDFUI3-0017 | pdf_ui_v3 | PARTIAL | Gebruik deze bestanden relatief aan dit document: eigenschappen zoals offset, tolerantie, prefix en suffix. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L27) |
| PDFUI3-0018 | pdf_ui_v3 | PARTIAL | Gebruik deze bestanden relatief aan dit document: 3. `references/03_ASSEMBLY_PERSISTENTIE_EN_LINTER.png` | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L28) |
| PDFUI3-0019 | pdf_ui_v3 | PARTIAL | Gebruik deze bestanden relatief aan dit document: assembly A1 met afzonderlijke onderdelen P1 en P2; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L29) |
| PDFUI3-0020 | pdf_ui_v3 | PARTIAL | Gebruik deze bestanden relatief aan dit document: onderdeeloverschrijdende hart-op-hart- en horizontale maat; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L30) |
| PDFUI3-0021 | pdf_ui_v3 | PARTIAL | Gebruik deze bestanden relatief aan dit document: modelboom, BOM, DrawingLinter en revisiestatus; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L31) |
| PDFUI3-0022 | pdf_ui_v3 | PARTIAL | Gebruik deze bestanden relatief aan dit document: project opnieuw openen en persistent maatdocument herstellen. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L32) |
| PDFUI3-0023 | pdf_ui_v3 | PARTIAL | De afbeeldingen zijn ontwerpvoorbeelden en geen testbewijs. Alleen nieuwe screenshots uit de werkelijk gebouwde bronapp, one-folder EXE, portable runtime en geïnstalleerde applicatie gelden als bewijs. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L34) |
| PDFUI3-0024 | pdf_ui_v3 | PARTIAL | Integreer de werkruimte in de bestaande hoofdschil en projectcontext. Zij moet minimaal ondersteunen: | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L40) |
| PDFUI3-0025 | pdf_ui_v3 | PARTIAL | Integreer de werkruimte in de bestaande hoofdschil en projectcontext. Zij moet minimaal ondersteunen: openen vanuit het hoofdmenu en vanuit geselecteerde onderdelen/merken/assemblies; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L42) |
| PDFUI3-0026 | pdf_ui_v3 | PARTIAL | Integreer de werkruimte in de bestaande hoofdschil en projectcontext. Zij moet minimaal ondersteunen: bron uit NC1, IFC, STEP, CWS/canoniek onderdeel of volledig project; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L43) |
| PDFUI3-0027 | pdf_ui_v3 | PARTIAL | Integreer de werkruimte in de bestaande hoofdschil en projectcontext. Zij moet minimaal ondersteunen: tekeningstype onderdeel, merk en assembly; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L44) |
| PDFUI3-0028 | pdf_ui_v3 | PARTIAL | Integreer de werkruimte in de bestaande hoofdschil en projectcontext. Zij moet minimaal ondersteunen: papierformaten A4, A3, A2, A1 en A0; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L45) |
| PDFUI3-0029 | pdf_ui_v3 | PARTIAL | Integreer de werkruimte in de bestaande hoofdschil en projectcontext. Zij moet minimaal ondersteunen: staand/liggend; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L46) |
| PDFUI3-0030 | pdf_ui_v3 | PARTIAL | Integreer de werkruimte in de bestaande hoofdschil en projectcontext. Zij moet minimaal ondersteunen: automatische schaal en handmatige genormeerde schalen; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L47) |
| PDFUI3-0031 | pdf_ui_v3 | PARTIAL | Integreer de werkruimte in de bestaande hoofdschil en projectcontext. Zij moet minimaal ondersteunen: voor-, boven-, zij-, kop- en isometrisch aanzicht; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L48) |
| PDFUI3-0032 | pdf_ui_v3 | PARTIAL | Integreer de werkruimte in de bestaande hoofdschil en projectcontext. Zij moet minimaal ondersteunen: doorsneden, detailviews en vervolgbladen; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L49) |
| PDFUI3-0033 | pdf_ui_v3 | PARTIAL | Integreer de werkruimte in de bestaande hoofdschil en projectcontext. Zij moet minimaal ondersteunen: titelblok, revisietabel, materiaal, profiel, positienummer, aantal, status en BOM; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L50) |
| PDFUI3-0034 | pdf_ui_v3 | PARTIAL | Integreer de werkruimte in de bestaande hoofdschil en projectcontext. Zij moet minimaal ondersteunen: normale PDF-export en Trusted PDF-route zonder verlies van semantiek. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L51) |
| PDFUI3-0035 | pdf_ui_v3 | PARTIAL | Gebruik bestaande productie-authorities zoals `DrawingWorkspacePanel`, `ProductionDrawingEngine`, `ProductionDrawingRenderer`, het canonieke model en `ProjectSession`. Maak geen tweede, concurrerende tekenengine of losstaande projectopslag. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L53) |
| PDFUI3-0036 | pdf_ui_v3 | PARTIAL | Bied herkenbare, compacte tools voor: | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L57) |
| PDFUI3-0037 | pdf_ui_v3 | PARTIAL | Bied herkenbare, compacte tools voor: selecteren; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L59) |
| PDFUI3-0038 | pdf_ui_v3 | PARTIAL | Bied herkenbare, compacte tools voor: horizontale maat; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L60) |
| PDFUI3-0039 | pdf_ui_v3 | PARTIAL | Bied herkenbare, compacte tools voor: verticale maat; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L61) |
| PDFUI3-0040 | pdf_ui_v3 | PARTIAL | Bied herkenbare, compacte tools voor: uitgelijnde maat; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L62) |
| PDFUI3-0041 | pdf_ui_v3 | PARTIAL | Bied herkenbare, compacte tools voor: kettingmaat; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L63) |
| PDFUI3-0042 | pdf_ui_v3 | PARTIAL | Bied herkenbare, compacte tools voor: baseline-maat; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L64) |
| PDFUI3-0043 | pdf_ui_v3 | PARTIAL | Bied herkenbare, compacte tools voor: ordinaat X/Y; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L65) |
| PDFUI3-0044 | pdf_ui_v3 | PARTIAL | Bied herkenbare, compacte tools voor: hoekmaat; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L66) |
| PDFUI3-0045 | pdf_ui_v3 | PARTIAL | Bied herkenbare, compacte tools voor: radius; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L67) |
| PDFUI3-0046 | pdf_ui_v3 | PARTIAL | Bied herkenbare, compacte tools voor: diameter; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L68) |
| PDFUI3-0047 | pdf_ui_v3 | PARTIAL | Bied herkenbare, compacte tools voor: hart-op-hart; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L69) |
| PDFUI3-0048 | pdf_ui_v3 | PARTIAL | Bied herkenbare, compacte tools voor: leader/callout en tekst; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L70) |
| PDFUI3-0049 | pdf_ui_v3 | PARTIAL | Bied herkenbare, compacte tools voor: opnieuw ankeren; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L71) |
| PDFUI3-0050 | pdf_ui_v3 | PARTIAL | Bied herkenbare, compacte tools voor: verplaatsen van maatlijn; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L72) |
| PDFUI3-0051 | pdf_ui_v3 | PARTIAL | Bied herkenbare, compacte tools voor: verplaatsen van maattekst; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L73) |
| PDFUI3-0052 | pdf_ui_v3 | PARTIAL | Bied herkenbare, compacte tools voor: individueel verwijderen; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L74) |
| PDFUI3-0053 | pdf_ui_v3 | PARTIAL | Bied herkenbare, compacte tools voor: multiselectie en bulkbewerking; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L75) |
| PDFUI3-0054 | pdf_ui_v3 | PARTIAL | Bied herkenbare, compacte tools voor: verbergen/tonen; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L76) |
| PDFUI3-0055 | pdf_ui_v3 | PARTIAL | Bied herkenbare, compacte tools voor: undo/redo. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L77) |
| PDFUI3-0056 | pdf_ui_v3 | PARTIAL | Gebruik waar mogelijk de bestaande applicatie-iconen en kleur-/spacingtokens. Maak ontbrekende iconen als consistente native/vectorassets. Gebruik de rastermock-ups niet als knoppen of achtergronden. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L79) |
| PDFUI3-0057 | pdf_ui_v3 | PARTIAL | Dit onderdeel is verplicht en mag niet worden gesimuleerd. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L83) |
| PDFUI3-0058 | pdf_ui_v3 | PARTIAL | Laat de gebruiker een maattool kiezen en vervolgens één of meer echte geometrische punten selecteren. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L85) |
| PDFUI3-0059 | pdf_ui_v3 | PARTIAL | Ondersteun endpoints, midpoints, centers, gatcentra, boog-/cirkelcentra, snijpunten en relevante featurepunten. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L86) |
| PDFUI3-0060 | pdf_ui_v3 | PARTIAL | Toon hovermarkering, snaptype, onderdeel-ID, feature-ID en view-ID. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L87) |
| PDFUI3-0061 | pdf_ui_v3 | PARTIAL | Gebruik een configureerbaar selectiefilter: alles, eindpunten, middelpunten, centra/gaten en relevante combinaties. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L88) |
| PDFUI3-0062 | pdf_ui_v3 | PARTIAL | `Tab` wisselt deterministisch tussen overlappende kandidaten zonder focus uit de tekenwerkruimte te verplaatsen. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L89) |
| PDFUI3-0063 | pdf_ui_v3 | PARTIAL | Het eerste anker blijft zichtbaar; na het tweede anker verschijnt een dynamische preview; een volgende klik legt maatlijn/tekstpositie vast. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L90) |
| PDFUI3-0064 | pdf_ui_v3 | PARTIAL | Iedere kandidaat-ID is uniek per view en entity; semantisch identieke doelen worden gededupliceerd. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L91) |
| PDFUI3-0065 | pdf_ui_v3 | PARTIAL | Een assemblymaat bewaart beide afzonderlijke componentidentiteiten, bijvoorbeeld P1 en P2. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L92) |
| PDFUI3-0066 | pdf_ui_v3 | PARTIAL | De maatwaarde wordt uit de geometrie berekend. Alleen expliciete tekstoverride mag de getoonde tekst wijzigen; de werkelijke meetwaarde blijft traceerbaar. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L93) |
| PDFUI3-0067 | pdf_ui_v3 | PARTIAL | Een bestaande maat moet direct selecteerbaar zijn via maatlijn, tekst of grip. Toon daarna in het eigenschappenpaneel: | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L97) |
| PDFUI3-0068 | pdf_ui_v3 | PARTIAL | Een bestaande maat moet direct selecteerbaar zijn via maatlijn, tekst of grip. Toon daarna in het eigenschappenpaneel: type en unieke maat-ID; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L99) |
| PDFUI3-0069 | pdf_ui_v3 | PARTIAL | Een bestaande maat moet direct selecteerbaar zijn via maatlijn, tekst of grip. Toon daarna in het eigenschappenpaneel: berekende waarde en eenheid; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L100) |
| PDFUI3-0070 | pdf_ui_v3 | PARTIAL | Een bestaande maat moet direct selecteerbaar zijn via maatlijn, tekst of grip. Toon daarna in het eigenschappenpaneel: ankers en betrokken entity-/feature-/view-ID's; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L101) |
| PDFUI3-0071 | pdf_ui_v3 | PARTIAL | Een bestaande maat moet direct selecteerbaar zijn via maatlijn, tekst of grip. Toon daarna in het eigenschappenpaneel: offset en maatlijnpositie; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L102) |
| PDFUI3-0072 | pdf_ui_v3 | PARTIAL | Een bestaande maat moet direct selecteerbaar zijn via maatlijn, tekst of grip. Toon daarna in het eigenschappenpaneel: tekstpositie en eventuele override; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L103) |
| PDFUI3-0073 | pdf_ui_v3 | PARTIAL | Een bestaande maat moet direct selecteerbaar zijn via maatlijn, tekst of grip. Toon daarna in het eigenschappenpaneel: boven-/ondertolerantie; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L104) |
| PDFUI3-0074 | pdf_ui_v3 | PARTIAL | Een bestaande maat moet direct selecteerbaar zijn via maatlijn, tekst of grip. Toon daarna in het eigenschappenpaneel: prefix en suffix; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L105) |
| PDFUI3-0075 | pdf_ui_v3 | PARTIAL | Een bestaande maat moet direct selecteerbaar zijn via maatlijn, tekst of grip. Toon daarna in het eigenschappenpaneel: laag, kleur, lijntype, teksthoogte en pijlpunt; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L106) |
| PDFUI3-0076 | pdf_ui_v3 | PARTIAL | Een bestaande maat moet direct selecteerbaar zijn via maatlijn, tekst of grip. Toon daarna in het eigenschappenpaneel: zichtbaarheid; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L107) |
| PDFUI3-0077 | pdf_ui_v3 | PARTIAL | Een bestaande maat moet direct selecteerbaar zijn via maatlijn, tekst of grip. Toon daarna in het eigenschappenpaneel: status `RESOLVED`, `STALE`, `ORPHANED` of overeenkomstige bestaande domeinstatus; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L108) |
| PDFUI3-0078 | pdf_ui_v3 | PARTIAL | Een bestaande maat moet direct selecteerbaar zijn via maatlijn, tekst of grip. Toon daarna in het eigenschappenpaneel: tekeningrevisie, bronrevisie en lockversie. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L109) |
| PDFUI3-0079 | pdf_ui_v3 | PARTIAL | Wijzigingen moeten onmiddellijk vectorieel in de tekening worden gerenderd en via één transactiemodel worden opgeslagen. Verwijderen werkt voor één maat en multiselectie, vraagt bevestiging waar passend, ondersteunt undo/redo en schrijft auditinformatie. Opnieuw ankeren laat de gebruiker nieuwe echte geometriepunten selecteren zonder de maat-ID onnodig te vervangen. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L111) |
| PDFUI3-0080 | pdf_ui_v3 | PARTIAL | Sla maatdocumenten per entity op in het bestaande `.cwscproj`-project. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L115) |
| PDFUI3-0081 | pdf_ui_v3 | PARTIAL | Bewaar stabiele maat-ID's, ankers, stijl, status, audit en revisie over save/open. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L116) |
| PDFUI3-0082 | pdf_ui_v3 | PARTIAL | Bewijs heropening binnen dezelfde applicatie én via een werkelijk tweede EXE-proces met een andere PID. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L117) |
| PDFUI3-0083 | pdf_ui_v3 | PARTIAL | Vergelijk vóór en na herstart de project-SHA256 en maat-ID's. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L118) |
| PDFUI3-0084 | pdf_ui_v3 | PARTIAL | Bewaar minstens één onafhankelijke A1-maat nadat een andere maat in de revisietest bewust is gewijzigd/verwijderd. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L119) |
| PDFUI3-0085 | pdf_ui_v3 | PARTIAL | Autosave/crashherstel mag geen maat verliezen of dupliceren. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L120) |
| PDFUI3-0086 | pdf_ui_v3 | PARTIAL | Verwijderde geometrie maakt een maat zichtbaar orphaned; herstel/re-anchor maakt haar weer resolved. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L121) |
| PDFUI3-0087 | pdf_ui_v3 | PARTIAL | Een released/read-only tekening blokkeert alle mutaties fail-closed. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L122) |
| PDFUI3-0088 | pdf_ui_v3 | PARTIAL | Revisievergelijking bewaart de released snapshot en toont toegevoegde, gewijzigde én verwijderde objecten. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L123) |
| PDFUI3-0089 | pdf_ui_v3 | PARTIAL | DrawingLinter toont blokkerende problemen zichtbaar en voorkomt vrijgave bij ontbrekend of tegenstrijdig bewijs. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L124) |
| PDFUI3-0090 | pdf_ui_v3 | PARTIAL | Benader de informatiehiërarchie uit de afbeeldingen, maar houd de bestaande CWS-stijl leidend: | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L128) |
| PDFUI3-0091 | pdf_ui_v3 | PARTIAL | Benader de informatiehiërarchie uit de afbeeldingen, maar houd de bestaande CWS-stijl leidend: centrale tekening krijgt maximale bruikbare ruimte; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L130) |
| PDFUI3-0092 | pdf_ui_v3 | PARTIAL | Benader de informatiehiërarchie uit de afbeeldingen, maar houd de bestaande CWS-stijl leidend: maattools staan gegroepeerd boven het canvas; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L131) |
| PDFUI3-0093 | pdf_ui_v3 | PARTIAL | Benader de informatiehiërarchie uit de afbeeldingen, maar houd de bestaande CWS-stijl leidend: formaat, oriëntatie en schaal blijven direct zichtbaar; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L132) |
| PDFUI3-0094 | pdf_ui_v3 | PARTIAL | Benader de informatiehiërarchie uit de afbeeldingen, maar houd de bestaande CWS-stijl leidend: rechter inspector is contextgevoelig en inklapbaar; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L133) |
| PDFUI3-0095 | pdf_ui_v3 | PARTIAL | Benader de informatiehiërarchie uit de afbeeldingen, maar houd de bestaande CWS-stijl leidend: modelboom/BOM/linter worden alleen getoond wanneer zij relevant zijn; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L134) |
| PDFUI3-0096 | pdf_ui_v3 | PARTIAL | Benader de informatiehiërarchie uit de afbeeldingen, maar houd de bestaande CWS-stijl leidend: actieve tool, hover, eerste anker, preview, selectie, grips, orphaned en read-only hebben onderling duidelijk verschillende toestanden; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L135) |
| PDFUI3-0097 | pdf_ui_v3 | PARTIAL | Benader de informatiehiërarchie uit de afbeeldingen, maar houd de bestaande CWS-stijl leidend: bruikbaar op 100%, 125%, 150%, 175% en 200% Windows-schaal; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L136) |
| PDFUI3-0098 | pdf_ui_v3 | PARTIAL | Benader de informatiehiërarchie uit de afbeeldingen, maar houd de bestaande CWS-stijl leidend: toetsenbordnavigatie, focus, tooltips, toegankelijke namen en voldoende contrast; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L137) |
| PDFUI3-0099 | pdf_ui_v3 | PARTIAL | Benader de informatiehiërarchie uit de afbeeldingen, maar houd de bestaande CWS-stijl leidend: geen clipping, overlappende bediening, onleesbare tekst of horizontale schuifbalk voor de primaire bediening. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L138) |
| PDFUI3-0100 | pdf_ui_v3 | PARTIAL | Maak na implementatie een visuele vergelijking per referentiebeeld. Leg afwijkingen vast als bewust en functioneel gemotiveerd; kopieer geen toevallige fictieve projectnamen, klantnamen, data of maatwaarden uit de mock-ups. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L140) |
| PDFUI3-0101 | pdf_ui_v3 | PARTIAL | 1. Inventariseer eerst de bestaande implementatie en maak een requirement-to-code-matrix. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L144) |
| PDFUI3-0102 | pdf_ui_v3 | PARTIAL | 2. Hergebruik en consolideer bestaande productiecode; verwijder geen compatibiliteitsroute voordat tests het aantoonbaar toestaan. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L145) |
| PDFUI3-0103 | pdf_ui_v3 | PARTIAL | 3. Houd model, controller/state-machine, renderer, projectstore en UI van elkaar gescheiden. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L146) |
| PDFUI3-0104 | pdf_ui_v3 | PARTIAL | 4. Alle acties lopen via dezelfde transacties, audit en undo/redo-authority. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L147) |
| PDFUI3-0105 | pdf_ui_v3 | PARTIAL | 5. Voeg gerichte unit-, integratie-, GUI- en packaged-runtime-tests toe. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L148) |
| PDFUI3-0106 | pdf_ui_v3 | PARTIAL | 6. Gebruik echte PySide6-events voor GUI-tests; roep niet rechtstreeks handlers aan wanneer de gebruiker normaal klikt of typt. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L149) |
| PDFUI3-0107 | pdf_ui_v3 | PARTIAL | 7. Bewijs PDF-uitvoer door werkelijk PDF-bestanden te maken, terug te lezen en naar PNG te renderen. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L150) |
| PDFUI3-0108 | pdf_ui_v3 | PARTIAL | 8. Bewijs EXE-gedrag vanuit een schone Windows-build; bron-Python alleen is onvoldoende. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L151) |
| PDFUI3-0109 | pdf_ui_v3 | PARTIAL | 9. Behoud fail-closed checks voor canonieke hashes, bronexactheid, PDF-integriteit, installer en Viewer. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L152) |
| PDFUI3-0110 | pdf_ui_v3 | PARTIAL | 10. Verruim geen acceptatiegrens en verander geen PASS-criteria uitsluitend om CI groen te maken. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L153) |
| PDFUI3-0111 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L157) |
| PDFUI3-0112 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 1. toolbar | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0113 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 2. selectiefilter | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0114 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 3. endpoint-hover | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0115 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 4. gatcentrum-hover | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0116 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 5. eerste anker | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0117 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 6. dynamische preview | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0118 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 7. horizontaal | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0119 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 8. verticaal | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0120 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 9. aligned | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0121 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 10. chain | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0122 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 11. baseline/ordinate | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0123 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 12. angle | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0124 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 13. radius/diameter | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0125 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 14. center-distance | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0126 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 15. leader | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0127 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 16. selectie/grips | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0128 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 17. properties | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0129 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 18. maatlijn verplaatsen | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0130 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 19. tekst verplaatsen | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0131 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 20. één maat verwijderen | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0132 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 21. multiselect/bulk | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0133 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 22. re-anchor | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0134 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 23. hide/show | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0135 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 24. undo/redo | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0136 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 25. section | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0137 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 26. detail | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0138 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 27. continuation | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0139 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 28. assembly P1/P2 | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0140 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 29. project reopen | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0141 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 30. tweede EXE-restart | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0142 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 31. crash recovery | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0143 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 32. orphaned | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0144 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 33. revision compare | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0145 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 34. released/read-only | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0146 | pdf_ui_v3 | PARTIAL | Test ten minste de bestaande 35 PDF-GUI-bewijspunten aaneengesloten: 35. DrawingLinter-block. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L159) |
| PDFUI3-0147 | pdf_ui_v3 | PARTIAL | Daarnaast: | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L161) |
| PDFUI3-0148 | pdf_ui_v3 | PARTIAL | Daarnaast: voer alle bestaande PDF-V2-tests uit met `0 failed` en `0 skipped`; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L163) |
| PDFUI3-0149 | pdf_ui_v3 | PARTIAL | Daarnaast: controleer de volledige PDF-functiematrix en behoud 43/43 waar de repository die matrix voorschrijft; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L164) |
| PDFUI3-0150 | pdf_ui_v3 | PARTIAL | Daarnaast: maak per bewijs-ID een echte PNG met zichtbare test-ID en PASS-status; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L165) |
| PDFUI3-0151 | pdf_ui_v3 | PARTIAL | Daarnaast: lever een machineleesbaar JSON-manifest met pad, SHA256, runtime, PID waar relevant, status en gekoppelde requirement; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L166) |
| PDFUI3-0152 | pdf_ui_v3 | PARTIAL | Daarnaast: neem één screenshot op uit bronapp, one-folder EXE, verse portable runtime en geïnstalleerde applicatie; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L167) |
| PDFUI3-0153 | pdf_ui_v3 | PARTIAL | Daarnaast: controleer dat screenshots niet identiek gekopieerd zijn en werkelijk uit de betreffende runtime komen; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L168) |
| PDFUI3-0154 | pdf_ui_v3 | PARTIAL | Daarnaast: controleer geproduceerde normale en Trusted PDF op openen, pagina's, vectorinhoud, metadata en renderbaarheid; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L169) |
| PDFUI3-0155 | pdf_ui_v3 | PARTIAL | Daarnaast: voer alle bestaande conversie-, Viewer-, project-, release- en installer-smokes uit. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L170) |
| PDFUI3-0156 | pdf_ui_v3 | PARTIAL | Werk door totdat de actuele commit volledig groen is. Vereist: | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L174) |
| PDFUI3-0157 | pdf_ui_v3 | PARTIAL | Werk door totdat de actuele commit volledig groen is. Vereist: schone exacte SHA en ongewijzigde tracked worktree na tests; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L176) |
| PDFUI3-0158 | pdf_ui_v3 | PARTIAL | Werk door totdat de actuele commit volledig groen is. Vereist: volledige bronacceptatie; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L177) |
| PDFUI3-0159 | pdf_ui_v3 | PARTIAL | Werk door totdat de actuele commit volledig groen is. Vereist: Windows Phase 1, 2 en 3 groen; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L178) |
| PDFUI3-0160 | pdf_ui_v3 | PARTIAL | Werk door totdat de actuele commit volledig groen is. Vereist: alle 12 packaged conversieroutes groen; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L179) |
| PDFUI3-0161 | pdf_ui_v3 | PARTIAL | Werk door totdat de actuele commit volledig groen is. Vereist: PDF-V2 en volledige PDF-functiematrix groen; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L180) |
| PDFUI3-0162 | pdf_ui_v3 | PARTIAL | Werk door totdat de actuele commit volledig groen is. Vereist: echte app-herstart groen; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L181) |
| PDFUI3-0163 | pdf_ui_v3 | PARTIAL | Werk door totdat de actuele commit volledig groen is. Vereist: Viewer-gates groen zonder grensverruiming; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L182) |
| PDFUI3-0164 | pdf_ui_v3 | PARTIAL | Werk door totdat de actuele commit volledig groen is. Vereist: one-folder EXE, verse portable ZIP en installer getest; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L183) |
| PDFUI3-0165 | pdf_ui_v3 | PARTIAL | Werk door totdat de actuele commit volledig groen is. Vereist: installatie in een schone tijdelijke map, starten, project openen, PDF maken en afsluiten; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L184) |
| PDFUI3-0166 | pdf_ui_v3 | PARTIAL | Werk door totdat de actuele commit volledig groen is. Vereist: checksums en manifesten gebonden aan dezelfde commit; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L185) |
| PDFUI3-0167 | pdf_ui_v3 | PARTIAL | Werk door totdat de actuele commit volledig groen is. Vereist: final release artifact pas publiceren wanneer iedere verplichte gate PASS is. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L186) |
| PDFUI3-0168 | pdf_ui_v3 | PARTIAL | Bij een rode CI-run: download de diagnostics, bepaal de eerste echte oorzaak, herstel productiecode of een aantoonbare fout in de testopzet, voeg een regressietest toe, commit en herhaal. Maskeer geen fout met `continue-on-error`, skips, vaste PASS-data, hogere toleranties of gedeactiveerde checks. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L188) |
| PDFUI3-0169 | pdf_ui_v3 | PARTIAL | Lever minimaal: | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L192) |
| PDFUI3-0170 | pdf_ui_v3 | PARTIAL | Lever minimaal: Windows x64 installer; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L194) |
| PDFUI3-0171 | pdf_ui_v3 | PARTIAL | Lever minimaal: Windows x64 portable ZIP; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L195) |
| PDFUI3-0172 | pdf_ui_v3 | PARTIAL | Lever minimaal: one-folder runtime of bijbehorend releaseartifact; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L196) |
| PDFUI3-0173 | pdf_ui_v3 | PARTIAL | Lever minimaal: broncommit en volledige SHA; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L197) |
| PDFUI3-0174 | pdf_ui_v3 | PARTIAL | Lever minimaal: `RELEASE_MANIFEST.json` met SHA256 per bestand; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L198) |
| PDFUI3-0175 | pdf_ui_v3 | PARTIAL | Lever minimaal: `PDF_FUNCTION_GAP_MATRIX.json` en `.md` met totalen en percentages; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L199) |
| PDFUI3-0176 | pdf_ui_v3 | PARTIAL | Lever minimaal: `PDF_RUNTIME_EVIDENCE.json`; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L200) |
| PDFUI3-0177 | pdf_ui_v3 | PARTIAL | Lever minimaal: alle 35 PDF-GUI-screenshots plus extra runtimebeelden; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L201) |
| PDFUI3-0178 | pdf_ui_v3 | PARTIAL | Lever minimaal: normale en Trusted voorbeeld-PDF; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L202) |
| PDFUI3-0179 | pdf_ui_v3 | PARTIAL | Lever minimaal: voorbeeldproject `.cwscproj` voor P1 en assembly A1; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L203) |
| PDFUI3-0180 | pdf_ui_v3 | PARTIAL | Lever minimaal: revision audit en migratierapport; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L204) |
| PDFUI3-0181 | pdf_ui_v3 | PARTIAL | Lever minimaal: test-/CI-samenvatting met aantallen passed, failed en skipped; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L205) |
| PDFUI3-0182 | pdf_ui_v3 | PARTIAL | Lever minimaal: beknopte gebruikershandleiding voor maat toevoegen, selecteren, verplaatsen, opnieuw ankeren en verwijderen. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L206) |
| PDFUI3-0183 | pdf_ui_v3 | PARTIAL | Meld het werk uitsluitend als 100% gereed wanneer: | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L210) |
| PDFUI3-0184 | pdf_ui_v3 | PARTIAL | Meld het werk uitsluitend als 100% gereed wanneer: iedere functionele eis aan productiecode én testbewijs is gekoppeld; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L212) |
| PDFUI3-0185 | pdf_ui_v3 | PARTIAL | Meld het werk uitsluitend als 100% gereed wanneer: er geen verplichte `FAIL`, `PARTIAL`, `BLOCKED`, `NOT_IMPLEMENTED`, `NOT_INTEGRATED`, `NOT_TESTED` of `SKIPPED` resteert; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L213) |
| PDFUI3-0186 | pdf_ui_v3 | PARTIAL | Meld het werk uitsluitend als 100% gereed wanneer: percentages uit getelde requirements worden berekend en samen optellen tot 100%; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L214) |
| PDFUI3-0187 | pdf_ui_v3 | PARTIAL | Meld het werk uitsluitend als 100% gereed wanneer: de drie distributievormen werkelijk starten en dezelfde kernfuncties uitvoeren; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L215) |
| PDFUI3-0188 | pdf_ui_v3 | PARTIAL | Meld het werk uitsluitend als 100% gereed wanneer: de PDF-maatvoering na opslaan, projectheropening, tweede EXE-herstart en crashherstel intact blijft; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L216) |
| PDFUI3-0189 | pdf_ui_v3 | PARTIAL | Meld het werk uitsluitend als 100% gereed wanneer: CI op exact de opgeleverde commit groen is; | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L217) |
| PDFUI3-0190 | pdf_ui_v3 | PARTIAL | Meld het werk uitsluitend als 100% gereed wanneer: de downloadbare releaseartifacten bestaan en hun checksums zijn gecontroleerd. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L218) |
| PDFUI3-0191 | pdf_ui_v3 | PARTIAL | Als iets niet aantoonbaar gereed is, rapporteer dan exact wat ontbreekt, waarom, welk bewijs ontbreekt en welk bestand of welke test dit blokkeert. Noem het resultaat dan niet 100%. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L220) |
| PDFUI3-0192 | pdf_ui_v3 | PARTIAL | Begin direct zonder een nieuwe fasering aan de gebruiker te vragen. Werk zelfstandig door in één build, geef korte voortgangsupdates, maak kleine logisch samenhangende commits en push alleen gecontroleerde wijzigingen. Stop niet na code of na een lokale test: volg ook GitHub Actions tot de finale uitslag en lever de daadwerkelijke installatie- en bewijsbestanden op. | docs/pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md (L224) |
| PDFUI3-REVIEW-0001 | pdf_ui_v3 | PARTIAL | De gebruiker heeft `CWS_CODEX_PDF_UI_INTEGRATIE_V3_2026-09-06(2).zip` opnieuw aangeleverd. De daadwerkelijk gelezen 4.022.148 bytes hebben SHA-256 `f20b9597ee02eab1c45f06d85ae3d652d03eaeddb68614cc3bbcd15716a7f06e`. Alle zes manifestbestanden zijn afzonderlijk gehasht; volledige prompt, README, referentietoelichting en alle drie originele PNG's zijn gelezen/bekeken. De bestandsnaam verschilt, de bytes zijn identiek aan de historische specificatie. | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L5) |
| PDFUI3-REVIEW-0002 | pdf_ui_v3 | PARTIAL | Hervat vanaf de opnieuw gecontroleerde branch-HEAD `abe29e0447b8bed034711eddf7cf2bffdaa74e7a` en tree `ef4fa2423def5ac194facf47f473e5a3c770c855`. De lokale bron is per Git-blob en volledige tree tegen de commitgebonden bronsnapshot gecontroleerd, met lege werkboom vóór wijzigingen. Er is geen oudere UI-branch gemerged of vervangend programma gebouwd. De drie oorspronkelijke basiscommits zijn in de ancestry van de bronsnapshot bevestigd. Een remote GitHub-commit zegt niets over niet-gepusht werk op een andere computer; dat is niet als gecontroleerd geclaimd. | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L12) |
| PDFUI3-REVIEW-0003 | pdf_ui_v3 | PARTIAL | `pdf_ui_v3_original/INPUT_REVIEW.json` bevat de originele bestandshashes, werkelijke afmetingen en de visuele vergelijking. De originele tekstbestanden staan byte-identiek in dezelfde map. De originele PNG's zijn designinput, geen runtime- bewijs en geen UI-achtergrond. De ZIP/PNG-bytes zijn vóór commit gecontroleerd; CI herhaalt de hashcontrole van de vastgelegde tekst en review, niet van PNG's die niet in zijn checkout staan. De oorspronkelijke ZIP blijft bij de chatoplevering. `tools/verify_original_pdf_ui_spec.py --archive <originele ZIP> --output <rapport>` herhaalt desgewenst de volledige controle van de daadwerkelijke ZIP-bytes. | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L21) |
| PDFUI3-REVIEW-0004 | pdf_ui_v3 | PARTIAL | 1. Vrijgave regenereert de bestaande tekening vanuit de actuele selectie en | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L32) |
| PDFUI3-REVIEW-0005 | pdf_ui_v3 | PARTIAL | componentgeometrie, controleert documentbinding en voert DrawingLinter opnieuw uit. Ontbrekend, leeg of vals groen cachebewijs is nooit een vrijgaveautorisatie. De nieuwe native regressie was vóór herstel rood op drie concrete aanvallen. Geen nieuwe drawing-engine of extra projectstore is toegevoegd. | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L33) |
| PDFUI3-REVIEW-0006 | pdf_ui_v3 | PARTIAL | 2. De canonieke DimensionGraph levert `dimension_ids`, datum, absolute ketens en | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L37) |
| PDFUI3-REVIEW-0007 | pdf_ui_v3 | PARTIAL | totaalmaat. De eerdere linter controleerde uitsluitend het andere `members`- contract en blokkeerde daardoor ook een correct gecontroleerde gatplaat. Beide expliciete contracts worden nu gevalideerd. Ontbrekende/dubbele/onbekende verwijzingen, niet-eindige waarden, afwijkende cumulatieve/absolute ketens en overschrijding van de totaalmaat blokkeren. De bestaande 0,05 mm graphtolerantie is behouden. Ongeldige DimensionGraph-validatie is geen actuele Trusted-authoriteit. | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L38) |
| PDFUI3-REVIEW-0008 | pdf_ui_v3 | PARTIAL | 3. De onderste statusregel wordt niet meer verticaal afgesneden. Lange teksten zijn | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L44) |
| PDFUI3-REVIEW-0009 | pdf_ui_v3 | PARTIAL | herkenbaar afgekort met volledige tooltip/toegankelijke beschrijving; de Linter-tab houdt alle afzonderlijke meldingen beschikbaar. Nominale maten worden niet gewijzigd. | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L45) |
| PDFUI3-REVIEW-0010 | pdf_ui_v3 | PARTIAL | Een positieve native knoptest gebruikt een gedeclareerde synthetische canonieke plaat, werkelijke BREP-rebuild, NC1/STEP/IFC/PDF-roundtrips en Workbench-vrijgave. Hierna moet de echte maatvoering-vrijgaveknop slagen. Negatieve tests blijven blokkeren. Het echte hoofdvenster test cachebeschadiging ook binnen bron, onefolder, portable en geïnstalleerde EXE. De finale gate vereist deze nieuwe testnamen in alle acht runtime-/DPI-groepen: oude screenshots of rapporten kunnen ze niet vervangen. | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L48) |
| PDFUI3-REVIEW-0011 | pdf_ui_v3 | PARTIAL | Referentie \| Overgenomen informatiehiërarchie \| Bewuste afwijkingen en bewijs | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L57) |
| PDFUI3-REVIEW-0012 | pdf_ui_v3 | PARTIAL | 01 — volledige werkruimte \| Native gegroepeerde maattools, blijvend zichtbare papierinstellingen, modelboom, vectorblad, inklapbare inspecteur \| Bestaande CWS-hoofdschil/productnavigatie blijft behouden. Echte STEP-geometrie bepaalt schaal en bladinhoud. Oranje Review in plaats van een fictieve vaste PASS. `UI3-01-native-workspace.png`. | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L59) |
| PDFUI3-REVIEW-0013 | pdf_ui_v3 | PARTIAL | 02 — maat selecteren/bewerken \| Echte selectiegrips, geometrische ankers, inline offset/tolerantie/prefix/suffix/opmaak, puntgestuurd verplaatsen en herankeren \| Gegroepeerde eigenschappenboom met verticale scroll, geen tweede modal als primaire inspecteur. Gemengde multiselectie overschrijft geen ongewijzigde velden. Geen fictieve DWG of hardcoded 1250 mm. `UI3-02-native-selection-inspector.png` en PDF-GUI-16 t/m 24. | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L60) |
| PDFUI3-REVIEW-0014 | pdf_ui_v3 | PARTIAL | 03 — assembly, persistentie, linter \| Afzonderlijke P1/P2-identiteiten, assemblymaten, modelboom/BOM/revisies/linter, onafhankelijke projectherstart \| Contexttabbladen bewaren tekenruimte. Alleen echte opgeslagen status wordt getoond. Een niet-gekwalificeerde mesh-assembly blijft Review/Trusted-geblokkeerd zonder partfallback. `UI3-04`, `UI3-07`, `UI3-08`, PDF-GUI-28 t/m 35. | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L61) |
| PDFUI3-REVIEW-0015 | pdf_ui_v3 | PARTIAL | Dit is een inhoudelijke vergelijking met de oorspronkelijke referenties, geen pixel-identieke reproductie of onafhankelijke handmatige goedkeuring van alle Windows-/hardwarecombinaties. De oorspronkelijke CWS-stijl heeft conform de opdracht voorrang. Nieuwe screenshotbestanden en hashes staan uitsluitend in de uiteindelijke runtime-manifesten; lokale werkboomproeven zijn geen releasebewijs. | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L63) |
| PDFUI3-REVIEW-0016 | pdf_ui_v3 | PARTIAL | De volledige originele prompt staat in `pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md`. De tabel in `PDF_UI_V3_NATIVE_INTEGRATION.md` koppelt alle hoofdgroepen aan de bestaande authorities en tests. Aanvullend zijn nu verplicht: | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L71) |
| PDFUI3-REVIEW-0017 | pdf_ui_v3 | PARTIAL | De volledige originele prompt staat in `pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md`. De tabel in `PDF_UI_V3_NATIVE_INTEGRATION.md` koppelt alle hoofdgroepen aan de bestaande authorities en tests. Aanvullend zijn nu verplicht: Gerichte eis \| Productiecode \| Test/bewijs | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L76) |
| PDFUI3-REVIEW-0018 | pdf_ui_v3 | PARTIAL | De volledige originele prompt staat in `pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md`. De tabel in `PDF_UI_V3_NATIVE_INTEGRATION.md` koppelt alle hoofdgroepen aan de bestaande authorities en tests. Aanvullend zijn nu verplicht: Geen vrijgave met ontbrekend/tegenstrijdig bewijs \| `functional_workspaces.py::_release_dimension_revision` \| `drawing_v3_release_evidence_smoke.py`, echte native `UI3-08`, 8 runtime/DPI-rapporten | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L78) |
| PDFUI3-REVIEW-0019 | pdf_ui_v3 | PARTIAL | De volledige originele prompt staat in `pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md`. De tabel in `PDF_UI_V3_NATIVE_INTEGRATION.md` koppelt alle hoofdgroepen aan de bestaande authorities en tests. Aanvullend zijn nu verplicht: Canonieke ketens en positieve geldige vrijgave \| `drawings/linter.py`, `engineering_drawing.py` \| `drawing_canonical_chain_binding_smoke.py`, positieve native vrijgave met 4 echte roundtrips | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L79) |
| PDFUI3-REVIEW-0020 | pdf_ui_v3 | PARTIAL | De volledige originele prompt staat in `pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md`. De tabel in `PDF_UI_V3_NATIVE_INTEGRATION.md` koppelt alle hoofdgroepen aan de bestaande authorities en tests. Aanvullend zijn nu verplicht: Volledige status toegankelijk, geen verticale clipping \| `drawing_workspace_layout.py::_DrawingStatusLabel` \| Gerichte statustest en echte hoofdvenstercontrole bij elke DPI/runtime | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L80) |
| PDFUI3-REVIEW-0021 | pdf_ui_v3 | PARTIAL | De volledige originele prompt staat in `pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md`. De tabel in `PDF_UI_V3_NATIVE_INTEGRATION.md` koppelt alle hoofdgroepen aan de bestaande authorities en tests. Aanvullend zijn nu verplicht: Originele invoercontrole niet vervangen door hardcoded hash \| `verify_original_pdf_ui_spec.py` \| `ui_v3_original_input_smoke.py`, inputreview + ongewijzigde prompt in uiteindelijke release | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L81) |
| PDFUI3-REVIEW-0022 | pdf_ui_v3 | PARTIAL | De volledige originele prompt staat in `pdf_ui_v3_original/CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md`. De tabel in `PDF_UI_V3_NATIVE_INTEGRATION.md` koppelt alle hoofdgroepen aan de bestaande authorities en tests. Aanvullend zijn nu verplicht: Geen oude groene rapporten na beveiligingsherstel \| `finalize_ui_v3_delivery.py` \| Negatieve manifesttest en verplichte nieuwe checks in alle 8 rapportgroepen | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L82) |
| PDFUI3-REVIEW-0023 | pdf_ui_v3 | PARTIAL | Alle bestaande gate-eisen blijven staan: PDF-V2 23 tests zonder fail/skip, 43 PDF-functies met daadwerkelijke uitvoering, 35 PDF-GUI-scenario's, volledige Phase 1/2/3 en 600 seconden soak, 12 packaged conversieroutes, vijf DPI's, drie runtimes, onafhankelijke herstarts, installatie/herinstallatie/uninstall. De 35 oudere scenario's gebruiken een echte productiepanel met gedeclareerde synthetische fixture; de extra hoofdvensterproeven gebruiken werkelijke STEP-intake in de volledige native CWS-app. Dit zijn verschillende, elkaar aanvullende bewijslagen. Geen enkel designbeeld geldt als screenshotbewijs. | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L84) |
| PDFUI3-REVIEW-0024 | pdf_ui_v3 | PARTIAL | De definitieve broncommit, echte aantallen en checksums staan in de gegenereerde releasebestanden. Dit document bevat geen vooraf toegekende test-PASS. Het resultaat blijft een niet-ondertekende softwarebeta: geen universele herkenningsgarantie, hardwarecertificering, machineautorisatie of vrijgave van onvoldoende bewezen assemblygeometrie. Historische upgrades buiten de geteste herinstallatie blijven afzonderlijk te kwalificeren. Deze grenzen mogen niet met het percentage van de concrete 43 geautomatiseerde PDF-functies worden verward. | docs/PDF_UI_V3_SPEC_REVIEW_20260911.md (L95) |
| BOM-SPEC-0001 | bom | PARTIAL | > Integration note, 2026-09-08: the implementation below originated at BOM commit `528cf4326fc613746f1eb90354998492c656888d`. It is integrated with recognition authority `5a4208f739a218976e9cb5812c55f8a48a9ff863` without importing the older branch release/version metadata. Structural coverage percentages below are not full-program release approval. Current-source native acceptance, real control captures and packaged Windows installer evidence remain separate gates. The integrated BOM additionally checks exact material evidence and canonical per-part release blockers. | docs/BOM_COMPLETE_IMPLEMENTATION.md (L1) |
| BOM-SPEC-0002 | bom | PARTIAL | Deze oplevering sluit de zeven expliciete BOM-gaps op één canonieke `ProjectModel 2.25`- en `BOMSnapshot`-autoriteit. De Windows-releaseworkflow maakt op de exacte Git-SHA een machineleesbaar acceptance-rapport, acht echte Qt-afbeeldingen, installer, portable pakket, bron-ZIP, Git-bundle, SBOM en checksums. | docs/BOM_COMPLETE_IMPLEMENTATION.md (L5) |
| BOM-SPEC-0003 | bom | PARTIAL | Eis \| Implementatie \| Bewijs | docs/BOM_COMPLETE_IMPLEMENTATION.md (L11) |
| BOM-SPEC-0004 | bom | PARTIAL | Selectieafhankelijke actiematrix \| 87 unieke acties, gegroepeerd per bekijken, bewerken, tekenen, machine/productie, voorraad/optimalisatie en export; enablement per familie, blocker, fysieke beschikbaarheid, tekening-, machine-, inkoop-, NC-, vrijgave- en globale readiness \| `BOMActionMatrix`; runtimecapture en acceptance controleren minimaal 87 unieke acties | docs/BOM_COMPLETE_IMPLEMENTATION.md (L13) |
| BOM-SPEC-0005 | bom | PARTIAL | Veldniveau revisie en verwijderd \| Canonieke entity-ID-correlatie over gewijzigde groepssleutels; exacte `BOMFieldDelta`-paden met before/after per BOM- én entityveld; geometrie-, manufacturing- en featuredelta; historische verwijderde regels en rode 3D-bounds \| `BOMHubState.revision_deltas`; revisietab; Viewer tombstones | docs/BOM_COMPLETE_IMPLEMENTATION.md (L14) |
| BOM-SPEC-0006 | bom | PARTIAL | Productiegereedheidskolommen \| Elf afzonderlijke statussen: geometrie, materiaal, tekening, machine, nesting, NC, scribing, conflicten, vrijgave, productie en levering \| 37-koloms `BomWorkspacePanel`; productiepreset | docs/BOM_COMPLETE_IMPLEMENTATION.md (L15) |
| BOM-SPEC-0007 | bom | PARTIAL | Voorraad/reststuk en inkoop \| Deterministische occurrence-packing over gemengde fysieke reststukken en handelslengten met kerf, gedeeltelijke plannen, optimistische reserveringsrevisie en één atomaire ledgertransactie; exact resterend tekort voedt canonieke `PurchasedItem`-behoeften; edit, vrijgave, annulering en reserveringsvrijgave zijn beschikbaar \| `BOMStockAllocationPlan`; `BOMStockAllocator.reserve_plan`; `BOMProcurementService`; restart-roundtriptests | docs/BOM_COMPLETE_IMPLEMENTATION.md (L16) |
| BOM-SPEC-0008 | bom | PARTIAL | Slimme selectie/lasso/kleur \| Persistente, recursief geneste EN/OF/NIET-query's met tekst-, leegte- en numerieke operatoren; vrije schermpolygonen met volledige polygon/rechthoek-intersectie; selectie op effectieve renderkleur \| `BOMQueryGroup`; `BOMScopeEngine.query`; `select_polygon`; `select_same_display_color` | docs/BOM_COMPLETE_IMPLEMENTATION.md (L17) |
| BOM-SPEC-0009 | bom | PARTIAL | Transacties/resultaten/undo \| Eén projectbrede rollbacktransactie met snapshot- en preflighthash, succes/foutrapport per BOM-groep, duur, audit en persistente inverse patch; undo werkt na projectherstart, blokkeert bij latere inhoudswijziging en blijft gekoppeld aan externe vrijgaven \| `execute_transaction`; `BOMBatchResult.item_results`; `persistent_inverse_patch`; `_release_barrier` | docs/BOM_COMPLETE_IMPLEMENTATION.md (L18) |
| BOM-SPEC-0010 | bom | PARTIAL | Gedeelde rendercache \| Procesbrede, thread-safe weak cache per exacte `MeshRepository`; mesh-hashgebonden immutable polydata en feature-edges gedeeld, automatische invalidatie bij geometrievervanging en identity-hashbewijs; actors/OpenGL blijven per venster \| `SharedRenderResourceCache.evidence`; `MeshRepository.revision`; hit/build/invalidation-statistiek in Traceability | docs/BOM_COMPLETE_IMPLEMENTATION.md (L19) |
| BOM-SPEC-0011 | bom | PARTIAL | Het acceptance-rapport gebruikt schema `cws-bom-completion-acceptance-2.0` en rapporteert elk van de zeven eisen afzonderlijk met een voltooiingspercentage. Op Windows voert `.github/workflows/build-windows-exe.yml` aanvullend de echte Qt-capture, native selftest, PyInstaller-, portable-, installatie-, associatie- en uninstallmatrix uit. Alleen een groen `CODEX_RELEASE_MANIFEST.json` geldt als volledige softwareoplevering. Dit bewijs geeft geen fysieke machinevrijgave; die grens blijft fail-closed. | docs/BOM_COMPLETE_IMPLEMENTATION.md (L28) |
| BOM-REPAIR-0001 | bom | PARTIAL | Deze wijziging bouwt door op `e5e28fb4ce2a504f244dce829f5247a3af366cfc`, branch `agent/cws-pdf-ui-v3-complete-20260909`. Geen oudere UI-branch gemerged, geen vervangend programma. De bestaande project-, selectie-, JobManager-, voorraad-, tekening-, export- en vrijgaveketens blijven leidend. | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L5) |
| BOM-REPAIR-0002 | bom | PARTIAL | **W01:** BOM-plaatnesting gaat naar de bestaande plaatnestinguitvoerder. | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L12) |
| BOM-REPAIR-0003 | bom | PARTIAL | Zowel plaat- als profielsolver krijgt uitsluitend expliciete geselecteerde canonieke onderdeel-IDs met hun werkelijke quantities/occurrences. Een lege, onbekende, gemengde of verkeerde familieselectie wordt niet verbreed. | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L13) |
| BOM-REPAIR-0004 | bom | PARTIAL | **W02:** aanbevelen, opnieuw controleren, alternatieven en uitleg gebruiken | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L16) |
| BOM-REPAIR-0005 | bom | PARTIAL | de bestaande machinedetails. Per onderdeel wordt ReadinessGate opnieuw uitgevoerd en worden bestaande capabilityrapporten met actuele manufacturing-hashbinding gecontroleerd. Het advies blijft zichtbaar na verversen; gewijzigde onderdelen/rapporten of beschadigde opgeslagen data maken het zichtbaar verouderd. Er worden geen assignments of machine- of transportrechten verleend. Dit is geen nieuwe fysieke machinekwalificatie of herberekening van nog ontbrekende capabilityrapporten. | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L17) |
| BOM-REPAIR-0006 | bom | PARTIAL | **W03 gedeeltelijk:** een expliciete, gehashte opdracht bewaart de actie, | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L24) |
| BOM-REPAIR-0007 | bom | PARTIAL | selectie, project-, BOM- en preflightbinding. Naar een scherm navigeren of exportinstellingen voorbereiden telt als `prepared`, niet als `passed`. Nesting telt pas als uitgevoerd na een werkelijk voltooid, geldig resultaat; project-/berekeningswissels blokkeren de oude callback. | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L25) |
| BOM-REPAIR-0008 | bom | PARTIAL | Reststukken wel/niet opnemen heeft effect op de daadwerkelijke | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L29) |
| BOM-REPAIR-0009 | bom | PARTIAL | plaatvoorraad of profielvoorraadpolicy. Deze keuze wordt met het plaatplan opgeslagen en bij heropenen hersteld. Fysieke voorraad wordt niet verzonnen. | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L30) |
| BOM-REPAIR-0010 | bom | PARTIAL | Expliciete NC1/STEP/IFC/DXF/PDF-keuzes worden met dezelfde geselecteerde IDs | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L32) |
| BOM-REPAIR-0011 | bom | PARTIAL | in het bestaande Export Center voorbereid. De actuele uitvoergates blijven vereist. Een geblokkeerd exportresultaat telt nooit als re-import verified, ook niet wanneer er al een package-pad bestaat. | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L33) |
| BOM-REPAIR-0012 | bom | PARTIAL | Niet-aangesloten groeperings-, alternatieven-, print- en batchtekenacties | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L36) |
| BOM-REPAIR-0013 | bom | PARTIAL | worden expliciet geweigerd, niet vervangen door een andere functie. Een handmatig gekozen niet-ondersteunde exportgroepering kan deze blokkade niet omzeilen. Combined is de expliciet ondersteunde packagegroepering. | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L37) |
| BOM-REPAIR-0014 | bom | PARTIAL | Een canonieke voorraadcompatibiliteitsfout is hersteld: oudere optionele | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L40) |
| BOM-REPAIR-0015 | bom | PARTIAL | voorraadvelden worden uit de bestaande properties gelezen, met ontbrekend bewijs als onbekend/leeg en niet als verzonnen certificaat. | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L41) |
| BOM-REPAIR-0016 | bom | PARTIAL | 1. `tests/bom_scope_safety_smoke.py`: domein- en veiligheidstests met werkelijke | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L46) |
| BOM-REPAIR-0017 | bom | PARTIAL | geselecteerde profielsolve/commit, voorraad en opgeslagen plaatplan. | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L47) |
| BOM-REPAIR-0018 | bom | PARTIAL | 2. `tests/bom_action_routing_smoke.py`: echte shipping Qt-panelen en QAction- | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L48) |
| BOM-REPAIR-0019 | bom | PARTIAL | triggers in een herkenbaar gelabelde testhost, echte plaatberekening en expliciet synthetische materiaal-/capabilitydata. Dit is geen complete hoofdapplicatie of machinekwalificatie. | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L49) |
| BOM-REPAIR-0020 | bom | PARTIAL | 3. `pdf_ui_v3_evidence.py`: extra machine-actie via echte QAction en echte | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L52) |
| BOM-REPAIR-0021 | bom | PARTIAL | bevestigingsdialoog in de bestaande native CWSMainWindow, zonder vervangen viewer of router. Vijf bron-DPI's en de drie packaged runtimes gebruiken dezelfde bestaande acceptatieketen. | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L53) |
| BOM-REPAIR-0022 | bom | PARTIAL | 4. `--bom-action-evidence` wordt in de nieuw geïnstalleerde EXE aangeroepen | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L56) |
| BOM-REPAIR-0023 | bom | PARTIAL | zonder externe Python op PATH. Het nieuwe rapport en screenshots worden aan dezelfde broncommit/EXE-hash gebonden en zijn verplicht bij promotie. | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L57) |
| BOM-REPAIR-0024 | bom | PARTIAL | 5. Bestaande BOM-selectie/undo, plaatintegratie, profielnesting en PDF/V3- | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L59) |
| BOM-REPAIR-0025 | bom | PARTIAL | regressies blijven verplicht. De bestaande skips worden niet als PASS gepresenteerd. | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L60) |
| BOM-REPAIR-0026 | bom | PARTIAL | Lokale dirty-tree-tests zijn voorcontrole. Alleen een nieuwe clean-source Windows-run met installer, onafhankelijke reopen, volledige regressies, 600-seconden-soak en de aanvullende BOM-bewijsgates mag een nieuwe beta promoveren. Oude installers en bewijs van `e5e28fb4` bewijzen deze wijziging niet. De finale broncommit wordt door de bouwmanifesten vastgelegd. | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L63) |
| BOM-REPAIR-0027 | bom | PARTIAL | W03/W18 blijven deels open: afzonderlijke grouped packages, complete batch-/ print-/tekenacties, volledig onderscheid van XLSX/CSV/JSON reviewexports, alle 87 acties met volledige transactie/revisie/undo-lifecycle, en relevante voorraad/inkoop/las/renderer-cacheketens. Blokkeren is niet implementeren. Het advies hergebruikt alleen brongebonden bestaande capabilityrapporten; ontbrekende rapporten, machineprofielwijzigingen en externe fysieke afname blijven afzonderlijke verantwoordelijkheden van de capability-/vrijgaveketen. | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L71) |
| BOM-REPAIR-0028 | bom | PARTIAL | W04–W35 buiten de hier genoemde deelreparaties blijven ongewijzigd: onder meer 317 actuele requirements, skips, leveranciers-/extrusieherkenning, externe PDF/AI, doelhardware/Trimble/60 UI-beelden, 481 referentiemodellen, machines, ondertekening, update/rollback en licentieafname. Er is geen algemene 100%-herkenning of volledige productvrijgave geclaimd. | docs/BOM_ACTION_GAP_REPAIR_20260911.md (L79) |
| BOM-EXPORT-0001 | bom | PARTIAL | Deze gerichte aanvulling gebruikt de bestaande bron `721b9b70` op `agent/cws-pdf-ui-v3-complete-20260909`. De voorgaande Windows-run `34622890577` is opnieuw gecontroleerd en volledig geslaagd. Geen oude UI-branch is gemerged en geen vervangend programma is gebouwd. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L5) |
| BOM-EXPORT-0002 | bom | PARTIAL | De bestaande V15 Export Center-service maakt een exacte, disjuncte partitie | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L12) |
| BOM-EXPORT-0003 | bom | PARTIAL | van de selectie: per onderdeel/object, positie, assembly, assemblymerk, fase, batch, machine of gecombineerd. Elk kindpakket wordt geproduceerd door de bestaande ProjectProductionExportEngine met haar bestaande onderdeel-, materiaal-, review-, roundtrip- en vrijgavecontroles. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L13) |
| BOM-EXPORT-0004 | bom | PARTIAL | DSTV en PDF/labels zijn aan de bestaande NC1-, production_pdf- en label_pdf- | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L17) |
| BOM-EXPORT-0005 | bom | PARTIAL | uitvoer gekoppeld; er wordt geen nieuwe geometriewriter geïntroduceerd. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L18) |
| BOM-EXPORT-0006 | bom | PARTIAL | Machinegroepering vraagt een expliciete toewijzing en een actueel, | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L19) |
| BOM-EXPORT-0007 | bom | PARTIAL | manufacturing-hashgebonden capabilityrapport. Een advies is geen toewijzing; groeperen verleent geen machine- of transportbevoegdheid. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L20) |
| BOM-EXPORT-0008 | bom | PARTIAL | Bij ontbrekende/conflicterende groepsinformatie wordt geblokkeerd. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L22) |
| BOM-EXPORT-0009 | bom | PARTIAL | Onderdelen met meer dan één assembly-eigenaar worden niet gekopieerd naar meerdere groepen met telkens het volledige aantal. Occurrence- verdeling over meerdere eigenaren blijft een expliciete vervolgopdracht. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L23) |
| BOM-EXPORT-0010 | bom | PARTIAL | De Qt-werkruimte houdt scope, formaat, groepering en oorspronkelijke | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L26) |
| BOM-EXPORT-0011 | bom | PARTIAL | BOM-opdracht vast. Alleen een geverifieerd geschreven pakket levert een geslaagd BOM-resultaat op. Een andere projectcontext ontvangt dat oude achtergrondresultaat niet. Gelijktijdig opnieuw starten wordt geweigerd. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L27) |
| BOM-EXPORT-0012 | bom | PARTIAL | XLSX, CSV en JSON in de BOM maken nu hun afzonderlijke payload in plaats | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L30) |
| BOM-EXPORT-0013 | bom | PARTIAL | van telkens het hele pakket. De bestaande XLSX-opmaak en bescherming tegen spreadsheetformules blijven behouden. Reviewexport blijft review: manifest, validatierapport en hashes worden als bijlagen meegeleverd. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L31) |
| BOM-EXPORT-0014 | bom | PARTIAL | Bij een gedeeltelijke selectie van een geaggregeerde BOM-regel worden | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L34) |
| BOM-EXPORT-0015 | bom | PARTIAL | uitsluitend de gekozen canonieke IDs, aantallen en individuele massa's opgenomen. Een gehighlighte groep voegt geen niet-geselecteerde delen toe. Onbekende individuele massa/aantallen worden niet pro rata gegokt. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L35) |
| BOM-EXPORT-0016 | bom | PARTIAL | De productie-export voegt een exacte part-BOM toe, geen volledige project- | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L38) |
| BOM-EXPORT-0017 | bom | PARTIAL | BOM bij elke groep. De standaard assembly-packagecontrole van de originele engine blijft behouden. Losse onderdeel-/fase-/machinegroepen vragen alleen onderdeeluitvoer; ze doen geen onterechte assemblyvrijgaveclaim. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L39) |
| BOM-EXPORT-0018 | bom | PARTIAL | Alle groepen worden eerst in een private tijdelijke map geschreven, daarna teruggelezen en tegen manifest, ZIP-inhoud en checksums gecontroleerd. De complete partitie moet iedere gekozen ID precies eenmaal bevatten. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L45) |
| BOM-EXPORT-0019 | bom | PARTIAL | De bronrevisie omvat ook ruwe velden, werkbankvrijgave, groepsmetadata en machinebewijs. Gewijzigde bron, beschadigde preflight, geannuleerde opdracht of fout in een latere groep voorkomt publicatie van de volledige batch. Een reeds bestaand uitvoerpakket wordt niet overschreven of verwijderd. Publicatie gebeurt door één rename op hetzelfde bestandssysteem. Annuleren ná die publicatie trekt een reeds geverifieerd pakket niet achteraf in. Pakketten blijven aan hun bronrevisie gekoppeld; een export is geen modelmutatie of undo van een machinebewerking. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L49) |
| BOM-EXPORT-0020 | bom | PARTIAL | Groepsvolgorde en leden zijn stabiel. Pakketnamen zijn veilig, uniek en herleidbaar; vrije naamtemplates blijven niet geïmplementeerd en worden niet stilzwijgend genegeerd. Een herhaling hoeft door nieuwe job-/tijdstempels niet byte-identiek aan een eerdere export te zijn. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L58) |
| BOM-EXPORT-0021 | bom | PARTIAL | `tests/bom_grouped_export_smoke.py` test de partitie, lege/onbekende scope, verouderde metadata, herstart, cancellation, beschadigde output, fout in de tweede groep, behouden bestaande bestanden en afzonderlijke reviewformaten. De manifest-exporter in deze unitproeven is expliciet synthetisch en geldt niet als native CAD- of installerbewijs. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L65) |
| BOM-EXPORT-0022 | bom | PARTIAL | `bom_export_evidence.run_bom_export_evidence` bouwt twee expliciet synthetische platen via de echte Workbench → canonical rebuild → roundtrip → review → release-keten. De echte BOM- en Export Center-QWidgets/QActions starten de echte JobManager en exportengine. Alle acht hoofdgroeperingen leveren opnieuw gecontroleerde STEP/NC1/PDF-pakketten. Een extra niet-vrijgegeven onderdeel blijft buiten de selectie. Afzonderlijke XLSX/CSV/JSON-acties testen de geaggregeerde-regelvalkuil en concrete uitvoerbestanden. Dit is een test van de echte componenten, niet een vervangend programma of een leverancierstest. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L71) |
| BOM-EXPORT-0023 | bom | PARTIAL | Deze proef wordt vanuit de bestaande BOM-acceptatie gestart in de werkelijk geïnstalleerde EXE, zonder externe Python op PATH. De installer- en finale promotiegates vereisen hetzelfde source-SHA, EXE-hash, alle acht groeperingen, alle drie reviewformaten en de hashes van de echte pakketten en screenshots. Een oud groen BOM-rapport zonder dit aanvullende bewijs faalt de nieuwe gate. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L80) |
| BOM-EXPORT-0024 | bom | PARTIAL | Het echte volledige CWSMainWindow krijgt daarnaast native muis-/toetsproeven voor de exacte exportselectie en het blokkeren van niet-vrijgegeven invoer. Deze draaien in de bron op vijf DPI-schalen en in de drie verpakte uitvoeringen bij 100%. Zij vervangen de al bestaande hoofdvenster- en V3-maatproeven niet. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L86) |
| BOM-EXPORT-0025 | bom | PARTIAL | Lokale diagnostiek vóór commit heeft een gewijzigde werkboom en is geen releasebewijs. Alleen de verse Windows-uitvoer van de uiteindelijke commit mag als geleverde installatie-afname worden gepresenteerd. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L91) |
| BOM-EXPORT-0026 | bom | PARTIAL | W03 en W18 zijn verder ingevuld, niet volledig afgesloten. Batchgeneratie van interactieve tekeningen, batchplotten, alle 87 BOM-acties en alle revisie/undo-/occurrencecombinaties blijven afzonderlijk te testen/bouwen. Ook vrije naamtemplates, multi-assembly occurrenceverdeling, de onafhankelijke leveranciers-/DXF-/complex-profielmatrix, echte certificaten en machine-, GPU-, printer-, Windows 11- en upgradeafname blijven open volgens het werkregister. Er wordt geen universele herkenning of volledige productievrijgave verklaard. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L97) |
| BOM-EXPORT-0027 | bom | PARTIAL | De verse gegroepeerde PDF bevatte een oude generieke H-profielschets bij een plaat. De roundtrip geeft nu de echte canonical rebuild-BREP door aan Trusted PDF. De bestaande gedeelde DrawingProjectionModel/OCCT-HLR verzorgt de isometrie; er is geen nieuwe geometriewriter. Zonder BREP verschijnt een expliciete ontbreektmelding, nooit een verzonnen H-profiel. Een mislukte HLR bij aangeleverde BREP breekt de export af. De zichtbare PDF-roundtrip vereist het bewijslabel van deze exacte projectie. Plaatrandaanzichten heten geen flenzen meer. Individueel passende nevenaanzichten worden NTS gemarkeerd. De schaal van het hoofdaanzicht wordt werkelijk toegepast, niet afgerond naar een andere opdruk; een niet-passende vaste schaal wordt geweigerd. Deze correctie verandert geen STEP/IFC/NC1-writer of materiaalautoriteit. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L107) |
| BOM-EXPORT-0028 | bom | PARTIAL | Een extra adversariele proef met twee geldige delen, dezelfde positie en dezelfde 12-teken-ID-prefix reproduceerde een bestaande bestandsoverschrijving. De algemene checksumlijst kon toch kloppen, terwijl vier artefactverwijzingen van het eerste deel niet langer overeenkwamen. Onderdeelmappen gebruiken nu een hash van de volledige stabiele ID in plaats van alleen haar prefix. De bestaande map-/ZIP-verifier toetst ook elke geëxporteerde artefactverwijzing, bestandshash, omvang en objecteigenaar. Dubbele ZIP-namen worden geweigerd. Dit geldt ook voor de bestaande legacywriter; verschillende objecten krijgen geen gedeeld pad. De werkelijke CAD-regressie controleert beide identiteiten na gegroepeerde export. Synthetische negatieve manifestproeven zijn geen CAD/installerbewijs. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L122) |
| BOM-EXPORT-0029 | bom | PARTIAL | De brede Windows-regressie op `1dfed35c` toonde twee fouten in externe-PDF-review: het nieuw strikt renderen behandelde de gedetecteerde bronbladschaal als een expliciet gevraagde uitvoerschaal. De fout is lokaal opnieuw aangetoond. Nieuwe externe-PDF-analyses bewaren schaal, bladformaat, orientatie en bronhash als `source_drawing`-bewijs. Het nieuwe uitvoerblad begint in Auto; detectiewaarden en oorspronkelijke veld-evidence blijven ongewijzigd. Het bestaande reviewveld heet nu Uitvoerschaal. Een expliciete gebruikerskeuze blijft strikt: een te grote schaal wordt niet naar Auto omgezet. Vier regressies controleren de bronherkomst, fysieke PDF-lijnlengte, expliciete schaal en weigering zonder gepubliceerd bestand. De twee eerder falende reviewproeven blijven ongewijzigd en moeten opnieuw slagen. Reeds opgeslagen expliciete schaalkeuzes worden niet door deze reparatie gewist. | docs/BOM_EXPORT_GAP_REPAIR_20260911.md (L136) |
| BOM-REVIEW-0001 | bom | PARTIAL | Dit gerichte herstel bouwt op `721b9b705fff5604c05c7237572b06b26e158c8a`, branch `agent/cws-pdf-ui-v3-complete-20260909`. Tijdens de uitvoering schoof HEAD door naar `483fe1813967452dc7d83667150960e001adffda`. De veranderingen zijn daarop opnieuw vergeleken, geïntegreerd en getest. De gelijktijdige format-aware writer, exacte partselectie, acht productiepackagegroeperingen en canonieke BREP-/schaalreparatie zijn behouden; niet met de oudere bron overschreven. De onderstaande eerste fouten zijn op 721b9b70 gereproduceerd; een deel was ook in de tussentijdse commits hersteld. De bronbytes en oorspronkelijke Git-tree van het aangeleverde snapshot zijn opnieuw gecontroleerd. Er is geen andere UI-branch samengevoegd en geen vervangend programma gebouwd. | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L5) |
| BOM-REVIEW-0002 | bom | PARTIAL | 1. `export.xlsx`, `export.csv`, `export.json` en `export.review` riepen dezelfde | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L18) |
| BOM-REVIEW-0003 | bom | PARTIAL | volledige package-export aan. De specifieke QAction ging verloren. | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L19) |
| BOM-REVIEW-0004 | bom | PARTIAL | 2. De geretourneerde dictionary werd op keys in plaats van outputpaden doorlopen; | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L20) |
| BOM-REVIEW-0005 | bom | PARTIAL | het resultaatrapport bevatte daardoor namen in plaats van werkelijke paden. | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L21) |
| BOM-REVIEW-0006 | bom | PARTIAL | 3. De oude review-scope kon via een gedeeld merk of parent assembly verbreden: | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L22) |
| BOM-REVIEW-0007 | bom | PARTIAL | selectie P1 met aantal 2 leverde P1+P2 met aantal 5. Die verbreding is lokaal vóór de reparatie opnieuw aangetoond. | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L23) |
| BOM-REVIEW-0008 | bom | PARTIAL | 4. Een projectwissel of wijziging tijdens een bevestigings-/mapdialoog werd in | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L25) |
| BOM-REVIEW-0009 | bom | PARTIAL | deze reviewexport niet opnieuw tegen de vastgelegde opdracht gecontroleerd. | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L26) |
| BOM-REVIEW-0010 | bom | PARTIAL | De bestaande BOM QAction-router draagt de exacte reviewactie over. XLSX maakt | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L30) |
| BOM-REVIEW-0011 | bom | PARTIAL | de bestaande workbookweergave, CSV de acht bestaande datasets, JSON de ongewijzigde ruwe snapshotstructuur. Alleen de expliciete complete reviewactie maakt daarnaast PDF en het bestaande BOM-package. Manifest en checksums zijn bij ieder formaat aanwezig; ze zijn geen extra model-/productie-export. | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L31) |
| BOM-REVIEW-0012 | bom | PARTIAL | De bestaande writers en opmaak blijven behouden. De gelijktijdig toegevoegde | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L35) |
| BOM-REVIEW-0013 | bom | PARTIAL | `_part_snapshot` en `_export_review`-API zijn behouden; de laatste gebruikt dezelfde format-aware packagewriter, met aanvullende hash-/stalecontrole. CSV/XLSX behouden hun injectiebeveiliging; JSON blijft brongetrouwe data, niet spreadsheetinhoud. | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L36) |
| BOM-REVIEW-0014 | bom | PARTIAL | `strict_entities=True` is een opt-in op de bestaande snapshotketen. De UI | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L39) |
| BOM-REVIEW-0015 | bom | PARTIAL | gebruikt deze exacte scope: geen siblingparts, geen vollediger materiaalstaat bij een smaller geselecteerd onderdeel, en geen door groepslidmaatschap toegevoegde traceability-IDs. Assemblagemerk blijft context bij het onderdeel. De oude ruimere review-API blijft ongewijzigd voor bestaande callers. | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L40) |
| BOM-REVIEW-0016 | bom | PARTIAL | De opt-in generieke strikte scope maakt part- en fasteneraantallen niet | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L44) |
| BOM-REVIEW-0017 | bom | PARTIAL | minimaal één. Nul blijft daar nul en ongeldige aantallen worden geweigerd. De recente conservatieve part-only projectie houdt haar eigen bestaande massa-/aantalvalidatie. Lege objectselecties en ambigue geneste assemblygroepen worden geweigerd, niet naar siblings verbreed. | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L45) |
| BOM-REVIEW-0018 | bom | PARTIAL | Een expliciete matrixactie met lege selectie exporteert nooit alle zichtbare | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L49) |
| BOM-REVIEW-0019 | bom | PARTIAL | regels. De algemene werkbalkactie blijft expliciet de zichtbare scope aanbieden. | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L50) |
| BOM-REVIEW-0020 | bom | PARTIAL | Iedere export schrijft eerst naar staging en publiceert pas na voltooiing, | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L51) |
| BOM-REVIEW-0021 | bom | PARTIAL | hashcontrole en nieuwe broncontrole. Iedere uitvoering krijgt een eigen map; eerdere uitvoer en andere formaten worden niet overschreven of vermengd. | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L52) |
| BOM-REVIEW-0022 | bom | PARTIAL | Resultaatregistratie behoudt de exacte actie, werkelijke absolute paden, | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L54) |
| BOM-REVIEW-0023 | bom | PARTIAL | preflightbinding en passed/failed/cancelled. Exports verlenen geen productie-, voorraad-, machine- of transportrechten. Een file-export krijgt geen fictieve model-undo. De bestaande BOM-resultaatdialoog toont de uitvoering. | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L55) |
| BOM-REVIEW-0024 | bom | PARTIAL | `tests/bom_review_export_smoke.py`: exacte selectie/aantallen, gescheiden | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L61) |
| BOM-REVIEW-0025 | bom | PARTIAL | formats, injectiebeveiliging, legacycompatibiliteit, ontbrekende scope, gewijzigde snapshot, verouderde bron, schrijverfout en uitvoerbotsing. | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L62) |
| BOM-REVIEW-0026 | bom | PARTIAL | `bom_action_evidence.py`: echte shipping QAction-triggers en writers voor alle | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L64) |
| BOM-REVIEW-0027 | bom | PARTIAL | vier reviewacties; bestanden opnieuw lezen en hashen; vijf A-occurrences, geen drie B-occurrences; annulering, projectwijziging, lege selectie, echte resultaatdialoog en canonieke serialisatie van de audit. | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L65) |
| BOM-REVIEW-0028 | bom | PARTIAL | De bestaande shipping-panel-testhost blijft herkenbaar een componententest, | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L68) |
| BOM-REVIEW-0029 | bom | PARTIAL | geen vervangende hoofdapplicatie of GPU-pariteitsclaim. | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L69) |
| BOM-REVIEW-0030 | bom | PARTIAL | De installerketen voert dezelfde test in de geïnstalleerde EXE uit. Build én | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L70) |
| BOM-REVIEW-0031 | bom | PARTIAL | eindpromotie vereisen vier afzonderlijke reviewacties, concrete asserties, exact passende formaten en correcte hashes van alle feitelijke uitvoerfiles. Een oud groen rapport of ontbrekende reviewactie blokkeert promotie. | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L71) |
| BOM-REVIEW-0032 | bom | PARTIAL | De finalizer-unitfixtures zijn duidelijk synthetisch; ze zijn geen native | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L74) |
| BOM-REVIEW-0033 | bom | PARTIAL | applicatiebewijs. Twee extra negatieve tests bewijzen afwijzing van een ontbrekende reviewactie en een gewijzigd uitvoerbestand. | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L75) |
| BOM-REVIEW-0034 | bom | PARTIAL | Lokale gewijzigde bron is voorcontrole, geen releasebewijs. Een nieuwe beta mag uitsluitend na de bestaande volledige Windows-acceptatie op de finale commit worden aangeboden; de installer van 721b9b70 wordt niet omgelabeld. | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L78) |
| BOM-REVIEW-0035 | bom | PARTIAL | W03/W18 zijn niet volledig dicht: complete batchteken-/printacties, alle 87 acties en hun volledige lifecycle, 481 bronmodellen, herkenningsdekking, fysieke apparatuur en bedrijfsafname blijven afzonderlijke werkpakketten. De acht productiepackagegroeperingen uit de gelijktijdige commits zijn behouden en in de regressie meegenomen, inclusief hun oorspronkelijke installed-evidencegate. Dit document claimt ze niet als nieuw eigen werk. De aanvullende reviewgate moet naast die bestaande grouped-exportgate slagen; geen van beide vervangt de andere. Dit herstel verleent geen productie- of machinevrijgave. De definitieve Windows-resultaten worden aan de nieuwe gezamenlijke broncommit gebonden, niet aan een van de losse voorcontroles. | docs/BOM_REVIEW_EXPORT_REPAIR_20260911.md (L84) |
| BOM-DRAWING-0001 | bom | PARTIAL | Gerichte voortzetting van `483fe1813967452dc7d83667150960e001adffda` op `agent/cws-pdf-ui-v3-complete-20260909`. Vóór de push bleek de branch doorgeschoven naar `21e1b56fc77591a438e9695c2b1a8d7fe5d42c4f`. Alle acht tussenliggende commits, waaronder artifact-identiteit, exacte reviewexports, hun geïnstalleerde bewijsgates en de invoerschaalreparatie, zijn behouden. De batchwijziging is daarop zonder conflicten toegepast en opnieuw getest. Geen oudere UI-branch overgenomen, geen vervangende applicatie of tweede tekenengine gemaakt. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L5) |
| BOM-DRAWING-0002 | bom | PARTIAL | Dit pakket implementeert de bestaande `drawing.batch_pdf`-actie uit W03/W18. Het sluit niet de volledige matrix van 87 BOM-acties, batchgoedkeuring, machineafname of alle 35 gapanalysewerkpakketten. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L14) |
| BOM-DRAWING-0003 | bom | PARTIAL | Windows-run 34631058867 faalde in `pdf_review_smoke` en `review_workflow_smoke`: de automatisch gedetecteerde invoerschaal werd onbedoeld als vaste schaal voor een anders ingedeeld uitvoerblad gebruikt. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L20) |
| BOM-DRAWING-0004 | bom | PARTIAL | De lokale correctie is niet over de gelijktijdige upstream-reparatie gelegd. De behouden implementatie van `21e1b56f` slaat de invoerschaal op onder `properties.source_drawing` en begint nieuwe review-uitvoer met Auto. Expliciete menselijke wijzigingen aan `drawing.scale` blijven strikt; een niet-passende vaste uitvoerschaal blijft een fout. De bijbehorende upstream-provenance- en fysieke-schaaltests blijven ongewijzigd behouden. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L24) |
| BOM-DRAWING-0005 | bom | PARTIAL | De bestaande BOM-actie maakt een gecombineerd vector-PDF én afzonderlijke | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L33) |
| BOM-DRAWING-0006 | bom | PARTIAL | object-PDFs met bladwijzers en een controlemanifest. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L34) |
| BOM-DRAWING-0007 | bom | PARTIAL | Exact geselecteerde canonieke object-IDs blijven behouden, ook wanneer een | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L35) |
| BOM-DRAWING-0008 | bom | PARTIAL | BOM-regel meerdere gelijk gemerkte onderdelen/assembly-occurrences bevat. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L36) |
| BOM-DRAWING-0009 | bom | PARTIAL | Een geselecteerde assembly blijft een assembly met alle traceerbare | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L37) |
| BOM-DRAWING-0010 | bom | PARTIAL | componenten. Een ontbrekend noodzakelijk component blokkeert de hele batch. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L38) |
| BOM-DRAWING-0011 | bom | PARTIAL | Ieder object gebruikt zijn eigen opgeslagen DimensionDocument, maatstijl, | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L39) |
| BOM-DRAWING-0012 | bom | PARTIAL | maatrecords, audit en bladinstellingen. Geen hergebruik van de laatst geselecteerde maatdocumenten voor andere objecten. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L40) |
| BOM-DRAWING-0013 | bom | PARTIAL | `EngineeringDrawingGenerator` en `ProductionDrawingEngine` blijven de | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L42) |
| BOM-DRAWING-0014 | bom | PARTIAL | autoriteiten. Alleen de registratie van afgeleide uitvoer/projectstatus kan tijdens een readonly batch expliciet worden uitgezet. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L43) |
| BOM-DRAWING-0015 | bom | PARTIAL | Bronproject, meshes en plaatsingen worden gekopieerd voordat de centrale | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L45) |
| BOM-DRAWING-0016 | bom | PARTIAL | JobManager het werk uitvoert. De worker gebruikt geen live Qt-widget. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L46) |
| BOM-DRAWING-0017 | bom | PARTIAL | PDF-samenvoeging gebruikt de bestaande pypdf-afhankelijkheid. MuPDF wordt | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L47) |
| BOM-DRAWING-0018 | bom | PARTIAL | niet in deze worker aangeroepen naast de interactieve GUI. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L48) |
| BOM-DRAWING-0019 | bom | PARTIAL | De GUI publiceert pas na nieuwe controle van bronrevisie, geometrie, scope, | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L49) |
| BOM-DRAWING-0020 | bom | PARTIAL | lintergegevens, bestandshashes en volledigheid. De complete tijdelijke map wordt in één hernoemstap gepubliceerd, nooit bestand voor bestand. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L50) |
| BOM-DRAWING-0021 | bom | PARTIAL | Annuleren, een andere projectcontext, een verouderde job, een gewijzigde | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L52) |
| BOM-DRAWING-0022 | bom | PARTIAL | bron, een fout in de tweede tekening en bestaande bestemmingen worden expliciet afgehandeld zonder halve publicatie of overschrijving. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L53) |
| BOM-DRAWING-0023 | bom | PARTIAL | De mapkeuze is aan het oorspronkelijke project en bronrevisie gebonden. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L55) |
| BOM-DRAWING-0024 | bom | PARTIAL | Dit is een reviewbatch, geen nieuwe revisie- of machinevrijgave. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L56) |
| BOM-DRAWING-0025 | bom | PARTIAL | `production_release_granted` blijft false. Bestaande autoriteiten worden niet verhoogd. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L57) |
| BOM-DRAWING-0026 | bom | PARTIAL | Tijdens de echte CWSMainWindow-proef bleven context-echo's telkens een kleurverversing plannen. De kleurwijziging publiceerde opnieuw viewerstate, waardoor die verversing zichzelf opnieuw kon inplannen. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L62) |
| BOM-DRAWING-0027 | bom | PARTIAL | De bestaande BOM-context plant dit nu alleen bij een gewijzigde workspace, renderer, BOM-snapshothash, kleurmodus of revisiestatus. Selectieoverdracht blijft ongewijzigd plaatsvinden. De regressietest bewijst dat twintig selectie-echo's één kleurtaak plannen en dat elk relevant gewijzigd gegeven wel opnieuw een taak plant. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L66) |
| BOM-DRAWING-0028 | bom | PARTIAL | Gerichte regressies omvatten echte vector-PDFs, volledige assemblies, individuele bladinstellingen, ongeldige/lege scopes, ontbrekende geometrie, dubbele/onveilige namen, annuleren, gewijzigde bestanden en brongegevens. De historische twee P1811-skips in `pdf_review_smoke` blijven expliciet skips; er zijn geen bestaande acceptatievoorwaarden verzwakt. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L74) |
| BOM-DRAWING-0029 | bom | PARTIAL | De werkelijke hoofdvenstertest voert drie scenario's uit: één geselecteerd onderdeel, beide onderdelen en een geselecteerde assembly. Alle drie gebruiken de bestaande QAction en JobManager; alleen de directorykeuze wordt geautomatiseerd. De onafhankelijke PDF-lezer controleert bladen, bladwijzers en vectorinhoud. Opgeslagen maatdocumenten blijven gelijk. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L80) |
| BOM-DRAWING-0030 | bom | PARTIAL | Deze controles draaien in dezelfde vijf bron-DPI-runs en drie packaged runtimes als de bestaande V3-bewijzen. De finalizer vereist de nieuwe namen én herberekent de hashes van de echte batchmanifesten en alle PDF-bestanden. Een eerder groen rapport zonder de nieuwe batchbijlagen kan niet promoveren. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L86) |
| BOM-DRAWING-0031 | bom | PARTIAL | Lokale gewijzigde-sourceproeven zijn diagnostiek, geen releasebewijs. Installer/portable en alle definitieve bewijzen moeten uit de nieuwe ongewijzigde broncommit komen. Alleen een gezamenlijke geslaagde Windows-run met installatiecontrole mag de beta promoveren. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L91) |
| BOM-DRAWING-0032 | bom | PARTIAL | De eerste Windows-run op `464dbad1` voerde 234 scripts uit waarvan één oude BOM-componentproef na 300 seconden stopte: zij verwachtte nog dat `drawing.batch_pdf` niet bestond. Nu de functie is aangesloten, opende die ongewijzigde test een native mapkeuze waarop niemand antwoordde. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L98) |
| BOM-DRAWING-0033 | bom | PARTIAL | De proef stuurt nu expliciet die echte mapkeuze aan. De eenvoudige componenthost heeft geen viewer-meshes en moet daarom correct weigeren: geen PDF, geen tijdelijke bestanden en geen achterblijvende job. De positieve deel-, subset- en assemblybatches blijven in de afzonderlijke echte CWSMainWindow-proef verplicht. Geen productielogica of timeout is versoepeld. De finalizer vereist beide nieuwe negatieve controlepunten; een eenheidstest bewijst dat het weglaten ervan promotie verhindert. De aangepaste componentproef is lokaal werkelijk uitgevoerd, niet geskipt. Definitief Windows-/installerbewijs vereist een nieuwe commitgebonden run. | docs/BOM_DRAWING_BATCH_REPAIR_20260911.md (L103) |
| VIEWER-ACCEPT-0001 | viewer_openbim | PARTIAL | scene schema serialiseert/deserialiseert deterministisch; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L5) |
| VIEWER-ACCEPT-0002 | viewer_openbim | PARTIAL | unknown future major schema wordt geweigerd; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L6) |
| VIEWER-ACCEPT-0003 | viewer_openbim | PARTIAL | immutable scene nodes; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L7) |
| VIEWER-ACCEPT-0004 | viewer_openbim | PARTIAL | duplicate stable IDs worden geblokkeerd; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L8) |
| VIEWER-ACCEPT-0005 | viewer_openbim | PARTIAL | missing parent/geometry refs worden geblokkeerd; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L9) |
| VIEWER-ACCEPT-0006 | viewer_openbim | PARTIAL | transform is finite en rechtsgeldig; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L10) |
| VIEWER-ACCEPT-0007 | viewer_openbim | PARTIAL | content hashes worden gecontroleerd. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L11) |
| VIEWER-ACCEPT-0008 | viewer_openbim | PARTIAL | orbit behoudt target; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L15) |
| VIEWER-ACCEPT-0009 | viewer_openbim | PARTIAL | pan behoudt viewrichting; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L16) |
| VIEWER-ACCEPT-0010 | viewer_openbim | PARTIAL | zoom heeft configureerbare snelheid; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L17) |
| VIEWER-ACCEPT-0011 | viewer_openbim | PARTIAL | fit-all bevat alle zichtbare bounds; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L18) |
| VIEWER-ACCEPT-0012 | viewer_openbim | PARTIAL | fit-selection bevat selectie; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L19) |
| VIEWER-ACCEPT-0013 | viewer_openbim | PARTIAL | zes orthogonale views; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L20) |
| VIEWER-ACCEPT-0014 | viewer_openbim | PARTIAL | isometrische view; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L21) |
| VIEWER-ACCEPT-0015 | viewer_openbim | PARTIAL | perspective/orthographic roundtrip; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L22) |
| VIEWER-ACCEPT-0016 | viewer_openbim | PARTIAL | camera save/reopen binnen tolerantie. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L23) |
| VIEWER-ACCEPT-0017 | viewer_openbim | PARTIAL | part, assembly, model en feature modes; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L27) |
| VIEWER-ACCEPT-0018 | viewer_openbim | PARTIAL | Ctrl add/remove; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L28) |
| VIEWER-ACCEPT-0019 | viewer_openbim | PARTIAL | selection persists na style update; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L29) |
| VIEWER-ACCEPT-0020 | viewer_openbim | PARTIAL | hide/show/isolate/show-all; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L30) |
| VIEWER-ACCEPT-0021 | viewer_openbim | PARTIAL | ghost context; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L31) |
| VIEWER-ACCEPT-0022 | viewer_openbim | PARTIAL | selected hidden state expliciet zichtbaar; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L32) |
| VIEWER-ACCEPT-0023 | viewer_openbim | PARTIAL | tree/grid/3D synchronisatie; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L33) |
| VIEWER-ACCEPT-0024 | viewer_openbim | PARTIAL | deleted node verdwijnt uit selection. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L34) |
| VIEWER-ACCEPT-0025 | viewer_openbim | PARTIAL | shaded; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L38) |
| VIEWER-ACCEPT-0026 | viewer_openbim | PARTIAL | shaded + edges; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L39) |
| VIEWER-ACCEPT-0027 | viewer_openbim | PARTIAL | wireframe; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L40) |
| VIEWER-ACCEPT-0028 | viewer_openbim | PARTIAL | transparency sortering zonder crashes; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L41) |
| VIEWER-ACCEPT-0029 | viewer_openbim | PARTIAL | per-object color; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L42) |
| VIEWER-ACCEPT-0030 | viewer_openbim | PARTIAL | selection outline; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L43) |
| VIEWER-ACCEPT-0031 | viewer_openbim | PARTIAL | section rendering; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L44) |
| VIEWER-ACCEPT-0032 | viewer_openbim | PARTIAL | screenshot; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L45) |
| VIEWER-ACCEPT-0033 | viewer_openbim | PARTIAL | device lost/fallbackdiagnostiek. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L46) |
| VIEWER-ACCEPT-0034 | viewer_openbim | PARTIAL | Fixtures: | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L50) |
| VIEWER-ACCEPT-0035 | viewer_openbim | PARTIAL | Fixtures: 100 nodes; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L52) |
| VIEWER-ACCEPT-0036 | viewer_openbim | PARTIAL | Fixtures: 1.000 nodes; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L53) |
| VIEWER-ACCEPT-0037 | viewer_openbim | PARTIAL | Fixtures: 10.000 nodes; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L54) |
| VIEWER-ACCEPT-0038 | viewer_openbim | PARTIAL | Fixtures: echte Tekla IFC-scene; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L55) |
| VIEWER-ACCEPT-0039 | viewer_openbim | PARTIAL | Fixtures: herhaalde geometry hashes voor instancing; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L56) |
| VIEWER-ACCEPT-0040 | viewer_openbim | PARTIAL | Fixtures: zeer groot partmesh. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L57) |
| VIEWER-ACCEPT-0041 | viewer_openbim | PARTIAL | Rapporteer: | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L59) |
| VIEWER-ACCEPT-0042 | viewer_openbim | PARTIAL | Rapporteer: parse/adapter time; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L61) |
| VIEWER-ACCEPT-0043 | viewer_openbim | PARTIAL | Rapporteer: cache build; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L62) |
| VIEWER-ACCEPT-0044 | viewer_openbim | PARTIAL | Rapporteer: first frame; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L63) |
| VIEWER-ACCEPT-0045 | viewer_openbim | PARTIAL | Rapporteer: peak RSS; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L64) |
| VIEWER-ACCEPT-0046 | viewer_openbim | PARTIAL | Rapporteer: orbit FPS p50/p95; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L65) |
| VIEWER-ACCEPT-0047 | viewer_openbim | PARTIAL | Rapporteer: pick latency p50/p95; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L66) |
| VIEWER-ACCEPT-0048 | viewer_openbim | PARTIAL | Rapporteer: isolate latency; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L67) |
| VIEWER-ACCEPT-0049 | viewer_openbim | PARTIAL | Rapporteer: section latency; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L68) |
| VIEWER-ACCEPT-0050 | viewer_openbim | PARTIAL | Rapporteer: cache reopen time. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L69) |
| VIEWER-ACCEPT-0051 | viewer_openbim | PARTIAL | Geen universele SLA claimen voordat Windowsmetingen bestaan. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L71) |
| VIEWER-ACCEPT-0052 | viewer_openbim | PARTIAL | Analytische fixtures met bekende waarden: | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L75) |
| VIEWER-ACCEPT-0053 | viewer_openbim | PARTIAL | Analytische fixtures met bekende waarden: point distance 100 mm; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L77) |
| VIEWER-ACCEPT-0054 | viewer_openbim | PARTIAL | Analytische fixtures met bekende waarden: edge 160 mm; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L78) |
| VIEWER-ACCEPT-0055 | viewer_openbim | PARTIAL | Analytische fixtures met bekende waarden: perpendicular face distance 10 mm; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L79) |
| VIEWER-ACCEPT-0056 | viewer_openbim | PARTIAL | Analytische fixtures met bekende waarden: angle 45°/90°; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L80) |
| VIEWER-ACCEPT-0057 | viewer_openbim | PARTIAL | Analytische fixtures met bekende waarden: radius 13,5 mm; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L81) |
| VIEWER-ACCEPT-0058 | viewer_openbim | PARTIAL | Analytische fixtures met bekende waarden: diameter 14/20 mm; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L82) |
| VIEWER-ACCEPT-0059 | viewer_openbim | PARTIAL | Analytische fixtures met bekende waarden: area en volume alleen uit canonical service. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L83) |
| VIEWER-ACCEPT-0060 | viewer_openbim | PARTIAL | Negatief: | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L85) |
| VIEWER-ACCEPT-0061 | viewer_openbim | PARTIAL | Negatief: verdwenen anchor; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L87) |
| VIEWER-ACCEPT-0062 | viewer_openbim | PARTIAL | Negatief: changed geometry hash; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L88) |
| VIEWER-ACCEPT-0063 | viewer_openbim | PARTIAL | Negatief: non-planar face voor unsupported measurement; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L89) |
| VIEWER-ACCEPT-0064 | viewer_openbim | PARTIAL | Negatief: mixed coordinate systems; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L90) |
| VIEWER-ACCEPT-0065 | viewer_openbim | PARTIAL | Negatief: non-finite input. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L91) |
| VIEWER-ACCEPT-0066 | viewer_openbim | PARTIAL | plane origin/normal; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L95) |
| VIEWER-ACCEPT-0067 | viewer_openbim | PARTIAL | invert; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L96) |
| VIEWER-ACCEPT-0068 | viewer_openbim | PARTIAL | multiple planes; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L97) |
| VIEWER-ACCEPT-0069 | viewer_openbim | PARTIAL | clip box; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L98) |
| VIEWER-ACCEPT-0070 | viewer_openbim | PARTIAL | section state in viewpoint; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L99) |
| VIEWER-ACCEPT-0071 | viewer_openbim | PARTIAL | section does not mutate source; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L100) |
| VIEWER-ACCEPT-0072 | viewer_openbim | PARTIAL | selection achter clip consistent; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L101) |
| VIEWER-ACCEPT-0073 | viewer_openbim | PARTIAL | caps optioneel en niet als echte geometry exporteren. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L102) |
| VIEWER-ACCEPT-0074 | viewer_openbim | PARTIAL | gesloten contour; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L108) |
| VIEWER-ACCEPT-0075 | viewer_openbim | PARTIAL | through holes; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L109) |
| VIEWER-ACCEPT-0076 | viewer_openbim | PARTIAL | exact volume/area/bounds; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L110) |
| VIEWER-ACCEPT-0077 | viewer_openbim | PARTIAL | face/edge/feature picking. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L111) |
| VIEWER-ACCEPT-0078 | viewer_openbim | PARTIAL | echte arcs/radii; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L115) |
| VIEWER-ACCEPT-0079 | viewer_openbim | PARTIAL | radiusmeting; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L116) |
| VIEWER-ACCEPT-0080 | viewer_openbim | PARTIAL | geen grove polygon feature-identiteit. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L117) |
| VIEWER-ACCEPT-0081 | viewer_openbim | PARTIAL | profielassen; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L121) |
| VIEWER-ACCEPT-0082 | viewer_openbim | PARTIAL | flens/lijf selecteerbaar; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L122) |
| VIEWER-ACCEPT-0083 | viewer_openbim | PARTIAL | lengte en eindvlakken. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L123) |
| VIEWER-ACCEPT-0084 | viewer_openbim | PARTIAL | analytische cylinder/round section; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L127) |
| VIEWER-ACCEPT-0085 | viewer_openbim | PARTIAL | diameter 20; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L128) |
| VIEWER-ACCEPT-0086 | viewer_openbim | PARTIAL | geen polygonclassificatie. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L129) |
| VIEWER-ACCEPT-0087 | viewer_openbim | PARTIAL | geen automatische production release; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L133) |
| VIEWER-ACCEPT-0088 | viewer_openbim | PARTIAL | review/blocking code zichtbaar. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L134) |
| VIEWER-ACCEPT-0089 | viewer_openbim | PARTIAL | identical; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L138) |
| VIEWER-ACCEPT-0090 | viewer_openbim | PARTIAL | placement-only; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L139) |
| VIEWER-ACCEPT-0091 | viewer_openbim | PARTIAL | added; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L140) |
| VIEWER-ACCEPT-0092 | viewer_openbim | PARTIAL | removed; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L141) |
| VIEWER-ACCEPT-0093 | viewer_openbim | PARTIAL | geometry changed; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L142) |
| VIEWER-ACCEPT-0094 | viewer_openbim | PARTIAL | hole changed; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L143) |
| VIEWER-ACCEPT-0095 | viewer_openbim | PARTIAL | material changed; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L144) |
| VIEWER-ACCEPT-0096 | viewer_openbim | PARTIAL | mirror changed; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L145) |
| VIEWER-ACCEPT-0097 | viewer_openbim | PARTIAL | metadata-only; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L146) |
| VIEWER-ACCEPT-0098 | viewer_openbim | PARTIAL | roundtrip tolerance. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L147) |
| VIEWER-ACCEPT-0099 | viewer_openbim | PARTIAL | Resultaat bevat stable IDs, deltas en blocking implications. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L149) |
| VIEWER-ACCEPT-0100 | viewer_openbim | PARTIAL | 10.000+ rows virtualized; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L153) |
| VIEWER-ACCEPT-0101 | viewer_openbim | PARTIAL | drag/drop columns; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L154) |
| VIEWER-ACCEPT-0102 | viewer_openbim | PARTIAL | sort/group/filter; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L155) |
| VIEWER-ACCEPT-0103 | viewer_openbim | PARTIAL | column chooser; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L156) |
| VIEWER-ACCEPT-0104 | viewer_openbim | PARTIAL | sums; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L157) |
| VIEWER-ACCEPT-0105 | viewer_openbim | PARTIAL | saved user/project/company presets; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L158) |
| VIEWER-ACCEPT-0106 | viewer_openbim | PARTIAL | all/visible/selected modes; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L159) |
| VIEWER-ACCEPT-0107 | viewer_openbim | PARTIAL | select in 3D; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L160) |
| VIEWER-ACCEPT-0108 | viewer_openbim | PARTIAL | colorize 3D; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L161) |
| VIEWER-ACCEPT-0109 | viewer_openbim | PARTIAL | CSV/Excel escaping. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L162) |
| VIEWER-ACCEPT-0110 | viewer_openbim | PARTIAL | Test vanuit: | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L166) |
| VIEWER-ACCEPT-0111 | viewer_openbim | PARTIAL | Test vanuit: 1. source environment; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L168) |
| VIEWER-ACCEPT-0112 | viewer_openbim | PARTIAL | Test vanuit: 2. PyInstaller dist; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L169) |
| VIEWER-ACCEPT-0113 | viewer_openbim | PARTIAL | Test vanuit: 3. opnieuw uitgepakte portable ZIP; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L170) |
| VIEWER-ACCEPT-0114 | viewer_openbim | PARTIAL | Test vanuit: 4. geïnstalleerde app zonder Python in PATH. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L171) |
| VIEWER-ACCEPT-0115 | viewer_openbim | PARTIAL | Minimaal: | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L173) |
| VIEWER-ACCEPT-0116 | viewer_openbim | PARTIAL | Minimaal: viewer backend imports; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L175) |
| VIEWER-ACCEPT-0117 | viewer_openbim | PARTIAL | Minimaal: GPU/context init; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L176) |
| VIEWER-ACCEPT-0118 | viewer_openbim | PARTIAL | Minimaal: synthetic scene; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L177) |
| VIEWER-ACCEPT-0119 | viewer_openbim | PARTIAL | Minimaal: exact BREP fixture; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L178) |
| VIEWER-ACCEPT-0120 | viewer_openbim | PARTIAL | Minimaal: screenshot; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L179) |
| VIEWER-ACCEPT-0121 | viewer_openbim | PARTIAL | Minimaal: open/close zonder exception; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L180) |
| VIEWER-ACCEPT-0122 | viewer_openbim | PARTIAL | Minimaal: installer/uninstaller; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L181) |
| VIEWER-ACCEPT-0123 | viewer_openbim | PARTIAL | Minimaal: SHA-256. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L182) |
| VIEWER-ACCEPT-0124 | viewer_openbim | PARTIAL | path traversal in cache/project refs; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L186) |
| VIEWER-ACCEPT-0125 | viewer_openbim | PARTIAL | corrupt mesh payload; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L187) |
| VIEWER-ACCEPT-0126 | viewer_openbim | PARTIAL | hash mismatch; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L188) |
| VIEWER-ACCEPT-0127 | viewer_openbim | PARTIAL | oversized payload limits; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L189) |
| VIEWER-ACCEPT-0128 | viewer_openbim | PARTIAL | WebView origin allowlist; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L190) |
| VIEWER-ACCEPT-0129 | viewer_openbim | PARTIAL | invalid native message schema; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L191) |
| VIEWER-ACCEPT-0130 | viewer_openbim | PARTIAL | cancellation leaves old scene intact; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L192) |
| VIEWER-ACCEPT-0131 | viewer_openbim | PARTIAL | renderer failure never changes canonical project. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L193) |
| VIEWER-ACCEPT-0132 | viewer_openbim | PARTIAL | 1. volledig CWS-projectmodel zichtbaar; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L197) |
| VIEWER-ACCEPT-0133 | viewer_openbim | PARTIAL | 2. responsive totaalmodel; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L198) |
| VIEWER-ACCEPT-0134 | viewer_openbim | PARTIAL | 3. tree/grid/3D sync; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L199) |
| VIEWER-ACCEPT-0135 | viewer_openbim | PARTIAL | 4. hide/show/isolate/transparency/colorize; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L200) |
| VIEWER-ACCEPT-0136 | viewer_openbim | PARTIAL | 5. camera, standaardviews en viewpoints; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L201) |
| VIEWER-ACCEPT-0137 | viewer_openbim | PARTIAL | 6. section/clipping; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L202) |
| VIEWER-ACCEPT-0138 | viewer_openbim | PARTIAL | 7. professionele measurements; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L203) |
| VIEWER-ACCEPT-0139 | viewer_openbim | PARTIAL | 8. exact Part Workbench source/canonical view; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L204) |
| VIEWER-ACCEPT-0140 | viewer_openbim | PARTIAL | 9. compare/revisions; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L205) |
| VIEWER-ACCEPT-0141 | viewer_openbim | PARTIAL | 10. property grid en export; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L206) |
| VIEWER-ACCEPT-0142 | viewer_openbim | PARTIAL | 11. audit/undo integratie; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L207) |
| VIEWER-ACCEPT-0143 | viewer_openbim | PARTIAL | 12. één geïntegreerde Windows-app zonder Python; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L208) |
| VIEWER-ACCEPT-0144 | viewer_openbim | PARTIAL | 13. echte referentietests en meetrapport; | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L209) |
| VIEWER-ACCEPT-0145 | viewer_openbim | PARTIAL | 14. geen Trimble-runtime of proprietary code in CWS release. | docs/viewer/CWS_VIEWER_ACCEPTANCE_TESTS.md (L210) |
| VIEWER-V5-0001 | viewer_openbim | PARTIAL | Werk verder in de bestaande repository: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L9) |
| VIEWER-V5-0002 | viewer_openbim | PARTIAL | `CoenWessselink/Convertor` | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L11) |
| VIEWER-V5-0003 | viewer_openbim | PARTIAL | De laatst gecontroleerde canonical productlijn was: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L13) |
| VIEWER-V5-0004 | viewer_openbim | PARTIAL | `agent/cws-product-ui-reintegration-v1` | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L15) |
| VIEWER-V5-0005 | viewer_openbim | PARTIAL | De laatst gecontroleerde SHA tijdens de gap-audit was: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L17) |
| VIEWER-V5-0006 | viewer_openbim | PARTIAL | `dc4e3e2ec2f91c40aad271d985b3fe59a44c7325` | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L19) |
| VIEWER-V5-0007 | viewer_openbim | PARTIAL | Versie op die audit-SHA: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L21) |
| VIEWER-V5-0008 | viewer_openbim | PARTIAL | `0.10.18-beta-dev` | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L23) |
| VIEWER-V5-0009 | viewer_openbim | PARTIAL | **BELANGRIJK:** behandel bovenstaande SHA alleen als audit-baseline. Start IEDERE bouwsessie met: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L25) |
| VIEWER-V5-0010 | viewer_openbim | PARTIAL | **BELANGRIJK:** behandel bovenstaande SHA alleen als audit-baseline. Start IEDERE bouwsessie met: 1. fetch remote; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L26) |
| VIEWER-V5-0011 | viewer_openbim | PARTIAL | **BELANGRIJK:** behandel bovenstaande SHA alleen als audit-baseline. Start IEDERE bouwsessie met: 2. bepaal actuele canonical branch; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L27) |
| VIEWER-V5-0012 | viewer_openbim | PARTIAL | **BELANGRIJK:** behandel bovenstaande SHA alleen als audit-baseline. Start IEDERE bouwsessie met: 3. bepaal actuele HEAD; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L28) |
| VIEWER-V5-0013 | viewer_openbim | PARTIAL | **BELANGRIJK:** behandel bovenstaande SHA alleen als audit-baseline. Start IEDERE bouwsessie met: 4. controleer of na de audit nieuwe commits zijn verschenen; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L29) |
| VIEWER-V5-0014 | viewer_openbim | PARTIAL | **BELANGRIJK:** behandel bovenstaande SHA alleen als audit-baseline. Start IEDERE bouwsessie met: 5. vergelijk die commits met deze opdracht; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L30) |
| VIEWER-V5-0015 | viewer_openbim | PARTIAL | **BELANGRIJK:** behandel bovenstaande SHA alleen als audit-baseline. Start IEDERE bouwsessie met: 6. werk vanaf de actuele canonical HEAD, niet blind vanaf de oude audit-SHA. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L31) |
| VIEWER-V5-0016 | viewer_openbim | PARTIAL | Doel is **niet** om CWS Convertor opnieuw te bouwen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L33) |
| VIEWER-V5-0017 | viewer_openbim | PARTIAL | Doel is: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L35) |
| VIEWER-V5-0018 | viewer_openbim | PARTIAL | > behoud alles wat aantoonbaar correct, geïntegreerd en getest is; sluit alleen de resterende gaps; consolideer de volledige productworkflow; voer de laatste V5/V5.1 UI correct door; verbeter de Viewer aantoonbaar in snelheid en gebruiksgevoel; en lever daarna één reproduceerbaar, volledig getest Windows-product op exact één source SHA. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L37) |
| VIEWER-V5-0019 | viewer_openbim | PARTIAL | Gebruik als requirement-basis, in deze volgorde: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L43) |
| VIEWER-V5-0020 | viewer_openbim | PARTIAL | Gebruik als requirement-basis, in deze volgorde: 1. actuele repository en actuele canonical HEAD; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L45) |
| VIEWER-V5-0021 | viewer_openbim | PARTIAL | Gebruik als requirement-basis, in deze volgorde: 2. laatste UI Master V5/V5.1 + UI Binding specificatie van 31-08-2026; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L46) |
| VIEWER-V5-0022 | viewer_openbim | PARTIAL | Gebruik als requirement-basis, in deze volgorde: 3. laatste Trimble / Viewer / snelheid / BOM / machine-routing / vector-PDF prompt van 30-08-2026; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L47) |
| VIEWER-V5-0023 | viewer_openbim | PARTIAL | Gebruik als requirement-basis, in deze volgorde: 4. Full Product Acceptance prompt van 28-08-2026; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L48) |
| VIEWER-V5-0024 | viewer_openbim | PARTIAL | Gebruik als requirement-basis, in deze volgorde: 5. Completion 100% prompt van 28-08-2026; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L49) |
| VIEWER-V5-0025 | viewer_openbim | PARTIAL | Gebruik als requirement-basis, in deze volgorde: 6. Unified 3-fasen prompt van 27-08-2026; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L50) |
| VIEWER-V5-0026 | viewer_openbim | PARTIAL | Gebruik als requirement-basis, in deze volgorde: 7. bestaande tests, manifests, evidence en eerdere bewezen subsystemen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L51) |
| VIEWER-V5-0027 | viewer_openbim | PARTIAL | Bij inhoudelijke conflicten: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L55) |
| VIEWER-V5-0028 | viewer_openbim | PARTIAL | Bij inhoudelijke conflicten: **laatste expliciete gebruikersrequirement wint** voor zichtbare UX en workflow; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L57) |
| VIEWER-V5-0029 | viewer_openbim | PARTIAL | Bij inhoudelijke conflicten: canonical engineering truth, safety, data-integriteit en fail-closed gedrag mogen NIET door een latere cosmetische/UI-eis worden verzwakt; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L58) |
| VIEWER-V5-0030 | viewer_openbim | PARTIAL | Bij inhoudelijke conflicten: bestaande bewezen functionaliteit mag niet worden verwijderd omdat ze niet zichtbaar is in een mock-up; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L59) |
| VIEWER-V5-0031 | viewer_openbim | PARTIAL | Bij inhoudelijke conflicten: een mock-up bepaalt presentatie, niet automatisch backendsemantiek; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L60) |
| VIEWER-V5-0032 | viewer_openbim | PARTIAL | Bij inhoudelijke conflicten: production release en machine-transfer blijven fail-closed. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L61) |
| VIEWER-V5-0033 | viewer_openbim | PARTIAL | De huidige productbasis is substantieel. Bouw daarop voort. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L67) |
| VIEWER-V5-0034 | viewer_openbim | PARTIAL | Aantoonbaar bestaande foundations: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L69) |
| VIEWER-V5-0035 | viewer_openbim | PARTIAL | Aantoonbaar bestaande foundations: Canonical Project Model; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L71) |
| VIEWER-V5-0036 | viewer_openbim | PARTIAL | Aantoonbaar bestaande foundations: canonical Part Model; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L72) |
| VIEWER-V5-0037 | viewer_openbim | PARTIAL | Aantoonbaar bestaande foundations: Unified Application Context; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L73) |
| VIEWER-V5-0038 | viewer_openbim | PARTIAL | Aantoonbaar bestaande foundations: geïntegreerde permanente Viewer; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L74) |
| VIEWER-V5-0039 | viewer_openbim | PARTIAL | Aantoonbaar bestaande foundations: Viewer selectiecontext; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L75) |
| VIEWER-V5-0040 | viewer_openbim | PARTIAL | Aantoonbaar bestaande foundations: Project/Viewer/Workbench/Converter/BOM/Manufacturing foundations; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L76) |
| VIEWER-V5-0041 | viewer_openbim | PARTIAL | Aantoonbaar bestaande foundations: Profile Nesting; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L77) |
| VIEWER-V5-0042 | viewer_openbim | PARTIAL | Aantoonbaar bestaande foundations: Quality/Inspection backend; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L78) |
| VIEWER-V5-0043 | viewer_openbim | PARTIAL | Aantoonbaar bestaande foundations: machine capability evidence; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L79) |
| VIEWER-V5-0044 | viewer_openbim | PARTIAL | Aantoonbaar bestaande foundations: progressive/proxy Viewer load; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L80) |
| VIEWER-V5-0045 | viewer_openbim | PARTIAL | Aantoonbaar bestaande foundations: isolated native IFC tessellation; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L81) |
| VIEWER-V5-0046 | viewer_openbim | PARTIAL | Aantoonbaar bestaande foundations: meshcache; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L82) |
| VIEWER-V5-0047 | viewer_openbim | PARTIAL | Aantoonbaar bestaande foundations: adaptive Viewer rendering; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L83) |
| VIEWER-V5-0048 | viewer_openbim | PARTIAL | Aantoonbaar bestaande foundations: sections/clipping/explode/measurements; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L84) |
| VIEWER-V5-0049 | viewer_openbim | PARTIAL | Aantoonbaar bestaande foundations: Windows build/release infrastructuur; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L85) |
| VIEWER-V5-0050 | viewer_openbim | PARTIAL | Aantoonbaar bestaande foundations: eerdere exact-SHA releaseproof voor de pre-30/31-08 scope. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L86) |
| VIEWER-V5-0051 | viewer_openbim | PARTIAL | Belangrijkste openstaande gaps uit de audit: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L88) |
| VIEWER-V5-0052 | viewer_openbim | PARTIAL | Belangrijkste openstaande gaps uit de audit: 1. Viewer laadsnelheid is nog onvoldoende geoptimaliseerd en onvoldoende bewezen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L90) |
| VIEWER-V5-0053 | viewer_openbim | PARTIAL | Belangrijkste openstaande gaps uit de audit: 2. Viewer frame-/inputperformance is onvoldoende black-box bewezen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L91) |
| VIEWER-V5-0054 | viewer_openbim | PARTIAL | Belangrijkste openstaande gaps uit de audit: 3. Trimble observable parity is niet volledig bewezen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L92) |
| VIEWER-V5-0055 | viewer_openbim | PARTIAL | Belangrijkste openstaande gaps uit de audit: 4. de laatste V5/V5.1 UI is nog niet als canonical product-UI doorgevoerd. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L93) |
| VIEWER-V5-0056 | viewer_openbim | PARTIAL | Belangrijkste openstaande gaps uit de audit: 5. de 226-control UI-binding is nog niet volledig uitgevoerd/geaccepteerd. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L94) |
| VIEWER-V5-0057 | viewer_openbim | PARTIAL | Belangrijkste openstaande gaps uit de audit: 6. BOM & Machines is nog geen complete production hub. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L95) |
| VIEWER-V5-0058 | viewer_openbim | PARTIAL | Belangrijkste openstaande gaps uit de audit: 7. automatische én handmatige machine-routing is nog niet compleet. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L96) |
| VIEWER-V5-0059 | viewer_openbim | PARTIAL | Belangrijkste openstaande gaps uit de audit: 8. Plate Nesting is nog een beperkte rechthoekige shelf solver. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L97) |
| VIEWER-V5-0060 | viewer_openbim | PARTIAL | Belangrijkste openstaande gaps uit de audit: 9. productie Drawing/PDF is nog rastergebaseerd waar vector vereist is. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L98) |
| VIEWER-V5-0061 | viewer_openbim | PARTIAL | Belangrijkste openstaande gaps uit de audit: 10. centrale Print/Output workflow moet conform V5 worden geconsolideerd. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L99) |
| VIEWER-V5-0062 | viewer_openbim | PARTIAL | Belangrijkste openstaande gaps uit de audit: 11. Planning/Shopfloor completeness is onvoldoende bewezen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L100) |
| VIEWER-V5-0063 | viewer_openbim | PARTIAL | Belangrijkste openstaande gaps uit de audit: 12. alle oudere prompts zijn nog niet in één master traceability + acceptance samengebracht. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L101) |
| VIEWER-V5-0064 | viewer_openbim | PARTIAL | Belangrijkste openstaande gaps uit de audit: 13. de bestaande releaseproof certificeert niet automatisch de requirements van 30/31 augustus. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L102) |
| VIEWER-V5-0065 | viewer_openbim | PARTIAL | Er mag uiteindelijk slechts één authority per domein zijn. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L108) |
| VIEWER-V5-0066 | viewer_openbim | PARTIAL | Behoud of consolideer naar: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L110) |
| VIEWER-V5-0067 | viewer_openbim | PARTIAL | Verboden: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L132) |
| VIEWER-V5-0068 | viewer_openbim | PARTIAL | Verboden: tweede Viewer core; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L134) |
| VIEWER-V5-0069 | viewer_openbim | PARTIAL | Verboden: tweede projectmodel; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L135) |
| VIEWER-V5-0070 | viewer_openbim | PARTIAL | Verboden: tweede BOM waarheid; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L136) |
| VIEWER-V5-0071 | viewer_openbim | PARTIAL | Verboden: een machinekeuze die quantity truth verandert; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L137) |
| VIEWER-V5-0072 | viewer_openbim | PARTIAL | Verboden: UI-workarounds die direct data muteren buiten de canonical write path; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L138) |
| VIEWER-V5-0073 | viewer_openbim | PARTIAL | Verboden: full scene rebuild bij normale selectie/hide/show als incremental patch mogelijk is; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L139) |
| VIEWER-V5-0074 | viewer_openbim | PARTIAL | Verboden: duplicate legacy workspaces die dezelfde functie uitvoeren; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L140) |
| VIEWER-V5-0075 | viewer_openbim | PARTIAL | Verboden: dead buttons; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L141) |
| VIEWER-V5-0076 | viewer_openbim | PARTIAL | Verboden: `pass`, lege lambda, TODO-handler of statuslabel-only actie als zogenaamd functionele control; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L142) |
| VIEWER-V5-0077 | viewer_openbim | PARTIAL | Verboden: swallowing van exceptions zonder zichtbare foutstatus/evidence; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L143) |
| VIEWER-V5-0078 | viewer_openbim | PARTIAL | Verboden: productieclaims zonder bewijs; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L144) |
| VIEWER-V5-0079 | viewer_openbim | PARTIAL | Verboden: machine-transfer vrijgeven zonder externe kwalificatie. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L145) |
| VIEWER-V5-0080 | viewer_openbim | PARTIAL | Gebruik voor ieder requirement en iedere acceptance case exact één van: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L151) |
| VIEWER-V5-0081 | viewer_openbim | PARTIAL | Gebruik voor ieder requirement en iedere acceptance case exact één van: `PASS` | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L153) |
| VIEWER-V5-0082 | viewer_openbim | PARTIAL | Gebruik voor ieder requirement en iedere acceptance case exact één van: `FAIL` | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L154) |
| VIEWER-V5-0083 | viewer_openbim | PARTIAL | Gebruik voor ieder requirement en iedere acceptance case exact één van: `BLOCKED` | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L155) |
| VIEWER-V5-0084 | viewer_openbim | PARTIAL | Gebruik voor ieder requirement en iedere acceptance case exact één van: `NOT_TESTED` | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L156) |
| VIEWER-V5-0085 | viewer_openbim | PARTIAL | Gebruik voor ieder requirement en iedere acceptance case exact één van: `NOT_APPLICABLE` | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L157) |
| VIEWER-V5-0086 | viewer_openbim | PARTIAL | Aanvullend mag voor externe machinekwalificatie: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L159) |
| VIEWER-V5-0087 | viewer_openbim | PARTIAL | Aanvullend mag voor externe machinekwalificatie: `BLOCKED_EXTERNAL_EVIDENCE` | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L161) |
| VIEWER-V5-0088 | viewer_openbim | PARTIAL | Nooit: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L163) |
| VIEWER-V5-0089 | viewer_openbim | PARTIAL | Nooit: “done-ish” | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L165) |
| VIEWER-V5-0090 | viewer_openbim | PARTIAL | Nooit: “mostly” | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L166) |
| VIEWER-V5-0091 | viewer_openbim | PARTIAL | Nooit: “probably” | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L167) |
| VIEWER-V5-0092 | viewer_openbim | PARTIAL | Nooit: “looks good” | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L168) |
| VIEWER-V5-0093 | viewer_openbim | PARTIAL | Nooit: “implemented therefore passed” | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L169) |
| VIEWER-V5-0094 | viewer_openbim | PARTIAL | Houd expliciet apart: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L171) |
| VIEWER-V5-0095 | viewer_openbim | PARTIAL | Een feature mag bijvoorbeeld zijn: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L180) |
| VIEWER-V5-0096 | viewer_openbim | PARTIAL | Dat is géén PASS. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L189) |
| VIEWER-V5-0097 | viewer_openbim | PARTIAL | Werk in exact drie grote fasen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L195) |
| VIEWER-V5-0098 | viewer_openbim | PARTIAL | Niet opsplitsen in tientallen kunstmatige microfasen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L197) |
| VIEWER-V5-0099 | viewer_openbim | PARTIAL | Binnen een fase mag je wel werkpakketten, commits en tests gebruiken. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L199) |
| VIEWER-V5-0100 | viewer_openbim | PARTIAL | **Viewer Performance + Viewer UX/Trimble-parity + harde meetbaseline** | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L202) |
| VIEWER-V5-0101 | viewer_openbim | PARTIAL | **V5.1 Product-UI + BOM/Machines + Nesting + vector Drawing/PDF + Print** | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L205) |
| VIEWER-V5-0102 | viewer_openbim | PARTIAL | **Alle eerdere prompts reconciliëren + totale acceptance + Windows final release proof** | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L208) |
| VIEWER-V5-0103 | viewer_openbim | PARTIAL | Een volgende fase mag pas formeel PASS zijn wanneer alle verplichte gates van de vorige fase PASS zijn. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L210) |
| VIEWER-V5-0104 | viewer_openbim | PARTIAL | Maak de Viewer aantoonbaar: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L220) |
| VIEWER-V5-0105 | viewer_openbim | PARTIAL | Maak de Viewer aantoonbaar: sneller bij cold load; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L222) |
| VIEWER-V5-0106 | viewer_openbim | PARTIAL | Maak de Viewer aantoonbaar: sneller bij warm reopen; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L223) |
| VIEWER-V5-0107 | viewer_openbim | PARTIAL | Maak de Viewer aantoonbaar: eerder bruikbaar; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L224) |
| VIEWER-V5-0108 | viewer_openbim | PARTIAL | Maak de Viewer aantoonbaar: vloeiender tijdens orbit/pan/zoom; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L225) |
| VIEWER-V5-0109 | viewer_openbim | PARTIAL | Maak de Viewer aantoonbaar: stabieler bij grote modellen; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L226) |
| VIEWER-V5-0110 | viewer_openbim | PARTIAL | Maak de Viewer aantoonbaar: sneller bij selectie; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L227) |
| VIEWER-V5-0111 | viewer_openbim | PARTIAL | Maak de Viewer aantoonbaar: correct bij identieke/instanced geometrie; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L228) |
| VIEWER-V5-0112 | viewer_openbim | PARTIAL | Maak de Viewer aantoonbaar: visueel rustiger/natuurlijker; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L229) |
| VIEWER-V5-0113 | viewer_openbim | PARTIAL | Maak de Viewer aantoonbaar: consistent met Trimble-observable gedrag binnen expliciete toleranties; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L230) |
| VIEWER-V5-0114 | viewer_openbim | PARTIAL | Maak de Viewer aantoonbaar: technisch meetbaar vanuit packaged Windows runtime. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L231) |
| VIEWER-V5-0115 | viewer_openbim | PARTIAL | Niet alleen optimaliseren; **meten vóór en na**. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L233) |
| VIEWER-V5-0116 | viewer_openbim | PARTIAL | Voordat performancecode wordt aangepast: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L239) |
| VIEWER-V5-0117 | viewer_openbim | PARTIAL | Voordat performancecode wordt aangepast: 1. bouw/launch actuele canonical Windows runtime; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L241) |
| VIEWER-V5-0118 | viewer_openbim | PARTIAL | Voordat performancecode wordt aangepast: 2. leg hardware en environment vast; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L242) |
| VIEWER-V5-0119 | viewer_openbim | PARTIAL | Voordat performancecode wordt aangepast: 3. gebruik minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L243) |
| VIEWER-V5-0120 | viewer_openbim | PARTIAL | Voordat performancecode wordt aangepast: klein model; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L244) |
| VIEWER-V5-0121 | viewer_openbim | PARTIAL | Voordat performancecode wordt aangepast: middelgroot model; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L245) |
| VIEWER-V5-0122 | viewer_openbim | PARTIAL | Voordat performancecode wordt aangepast: groot werkelijk IFC-model; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L246) |
| VIEWER-V5-0123 | viewer_openbim | PARTIAL | Voordat performancecode wordt aangepast: model met veel identieke profielen/instances; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L247) |
| VIEWER-V5-0124 | viewer_openbim | PARTIAL | Voordat performancecode wordt aangepast: 4. voer cold en warm tests uit; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L248) |
| VIEWER-V5-0125 | viewer_openbim | PARTIAL | Voordat performancecode wordt aangepast: 5. meet baseline; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L249) |
| VIEWER-V5-0126 | viewer_openbim | PARTIAL | Voordat performancecode wordt aangepast: 6. schrijf baseline weg onder bijvoorbeeld: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L250) |
| VIEWER-V5-0127 | viewer_openbim | PARTIAL | Verplicht registreren: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L256) |
| VIEWER-V5-0128 | viewer_openbim | PARTIAL | Geen modelnaam/path/hash publiceren als bron vertrouwelijk is, tenzij daarvoor toestemming/evidencebeleid bestaat. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L279) |
| VIEWER-V5-0129 | viewer_openbim | PARTIAL | Meet minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L285) |
| VIEWER-V5-0130 | viewer_openbim | PARTIAL | Cold en warm. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L302) |
| VIEWER-V5-0131 | viewer_openbim | PARTIAL | Gebruik deze acceptance-targets, tenzij de bestaande repo al strengere bewezen targets hanteert. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L357) |
| VIEWER-V5-0132 | viewer_openbim | PARTIAL | 60 Hz scherm: frame p50 ≤ 16.7 ms waar hardware/model dit redelijk maakt. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L361) |
| VIEWER-V5-0133 | viewer_openbim | PARTIAL | frame p95 ≤ 25 ms. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L362) |
| VIEWER-V5-0134 | viewer_openbim | PARTIAL | input → visible render p95 ≤ 35 ms. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L363) |
| VIEWER-V5-0135 | viewer_openbim | PARTIAL | geen normale navigatie-freeze > 100 ms nadat first usable is bereikt. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L364) |
| VIEWER-V5-0136 | viewer_openbim | PARTIAL | medium model pick p95 ≤ 80 ms; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L368) |
| VIEWER-V5-0137 | viewer_openbim | PARTIAL | large model pick p95 ≤ 150 ms; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L369) |
| VIEWER-V5-0138 | viewer_openbim | PARTIAL | whole-object highlight ≤ 100 ms; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L370) |
| VIEWER-V5-0139 | viewer_openbim | PARTIAL | wrong-instance-picks = 0 in de officiële stressset. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L371) |
| VIEWER-V5-0140 | viewer_openbim | PARTIAL | 10 minuten navigation/selection/hide/show memory drift < 10% zonder verklaarde cachegroei. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L375) |
| VIEWER-V5-0141 | viewer_openbim | PARTIAL | Op dezelfde machine en hetzelfde model: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L379) |
| VIEWER-V5-0142 | viewer_openbim | PARTIAL | Als Trimble sneller is, rapporteer dat transparant. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L387) |
| VIEWER-V5-0143 | viewer_openbim | PARTIAL | Als Trimble niet beschikbaar is, status = `NOT_TESTED`/`BLOCKED`, nooit PASS. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L389) |
| VIEWER-V5-0144 | viewer_openbim | PARTIAL | De audit toont dat de huidige loading foundation nuttig is maar niet maximaal. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L395) |
| VIEWER-V5-0145 | viewer_openbim | PARTIAL | Bouw een **Loader Engine V2** bovenop de bestaande project/loadarchitectuur. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L397) |
| VIEWER-V5-0146 | viewer_openbim | PARTIAL | Geen greenfield projectloader. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L399) |
| VIEWER-V5-0147 | viewer_openbim | PARTIAL | De huidige isolated IFC-provider mag niet meer de schaalbaarheidsbottleneck zijn. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L403) |
| VIEWER-V5-0148 | viewer_openbim | PARTIAL | Maak een bounded persistent worker pool, bijvoorbeeld: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L405) |
| VIEWER-V5-0149 | viewer_openbim | PARTIAL | Eisen: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L424) |
| VIEWER-V5-0150 | viewer_openbim | PARTIAL | Eisen: crash-isolation behouden; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L426) |
| VIEWER-V5-0151 | viewer_openbim | PARTIAL | Eisen: één native crash mag GUI niet meenemen; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L427) |
| VIEWER-V5-0152 | viewer_openbim | PARTIAL | Eisen: worker automatisch vervangen; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L428) |
| VIEWER-V5-0153 | viewer_openbim | PARTIAL | Eisen: geen onbeperkte worker spawn; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L429) |
| VIEWER-V5-0154 | viewer_openbim | PARTIAL | Eisen: defaults hardware-aware; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L430) |
| VIEWER-V5-0155 | viewer_openbim | PARTIAL | Eisen: min/max configureerbaar; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L431) |
| VIEWER-V5-0156 | viewer_openbim | PARTIAL | Eisen: voorkom RAM-explosie; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L432) |
| VIEWER-V5-0157 | viewer_openbim | PARTIAL | Eisen: deterministic cancellation; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L433) |
| VIEWER-V5-0158 | viewer_openbim | PARTIAL | Eisen: stale generation results nooit in actuele scene injecteren; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L434) |
| VIEWER-V5-0159 | viewer_openbim | PARTIAL | Eisen: worker shutdown clean; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L435) |
| VIEWER-V5-0160 | viewer_openbim | PARTIAL | Eisen: frozen Windows EXE route expliciet testen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L436) |
| VIEWER-V5-0161 | viewer_openbim | PARTIAL | Onderzoek 2/3/4/6 workers. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L438) |
| VIEWER-V5-0162 | viewer_openbim | PARTIAL | Kies op basis van meetdata, niet gevoel. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L440) |
| VIEWER-V5-0163 | viewer_openbim | PARTIAL | De audit toont een seriële `max_workers=1` route. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L444) |
| VIEWER-V5-0164 | viewer_openbim | PARTIAL | Paralleliseer alleen waar provider/thread/process safety aantoonbaar is. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L446) |
| VIEWER-V5-0165 | viewer_openbim | PARTIAL | Als OCP/CadQuery intern serialiseert: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L448) |
| VIEWER-V5-0166 | viewer_openbim | PARTIAL | Als OCP/CadQuery intern serialiseert: gebruik process-isolation; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L450) |
| VIEWER-V5-0167 | viewer_openbim | PARTIAL | Als OCP/CadQuery intern serialiseert: of laat gericht serialiseren en optimaliseer elders; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L451) |
| VIEWER-V5-0168 | viewer_openbim | PARTIAL | Als OCP/CadQuery intern serialiseert: documenteer bewijs. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L452) |
| VIEWER-V5-0169 | viewer_openbim | PARTIAL | Geen unsafe threading om alleen een benchmark mooier te maken. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L454) |
| VIEWER-V5-0170 | viewer_openbim | PARTIAL | Prioriteit minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L458) |
| VIEWER-V5-0171 | viewer_openbim | PARTIAL | Voorkom starvation. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L470) |
| VIEWER-V5-0172 | viewer_openbim | PARTIAL | Ondersteun reprioritization tijdens load. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L472) |
| VIEWER-V5-0173 | viewer_openbim | PARTIAL | Gebruiker moet zo snel mogelijk een bruikbaar model zien. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L476) |
| VIEWER-V5-0174 | viewer_openbim | PARTIAL | Pipeline: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L478) |
| VIEWER-V5-0175 | viewer_openbim | PARTIAL | Belangrijk: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L489) |
| VIEWER-V5-0176 | viewer_openbim | PARTIAL | Belangrijk: geen geometry accuracy verloren in de uiteindelijke canonical state; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L491) |
| VIEWER-V5-0177 | viewer_openbim | PARTIAL | Belangrijk: proxy is display-only; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L492) |
| VIEWER-V5-0178 | viewer_openbim | PARTIAL | Belangrijk: productie-evidence mag nooit op proxy exactness vertrouwen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L493) |
| VIEWER-V5-0179 | viewer_openbim | PARTIAL | Behoud content-addressed correctness, maar verminder reopen-overhead. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L499) |
| VIEWER-V5-0180 | viewer_openbim | PARTIAL | Onderzoek en implementeer indien meetbaar beter: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L501) |
| VIEWER-V5-0181 | viewer_openbim | PARTIAL | Onderzoek en implementeer indien meetbaar beter: versioned binary cache; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L503) |
| VIEWER-V5-0182 | viewer_openbim | PARTIAL | Onderzoek en implementeer indien meetbaar beter: mmap waar passend; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L504) |
| VIEWER-V5-0183 | viewer_openbim | PARTIAL | Onderzoek en implementeer indien meetbaar beter: minder decompressie; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L505) |
| VIEWER-V5-0184 | viewer_openbim | PARTIAL | Onderzoek en implementeer indien meetbaar beter: minder volledige array copies; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L506) |
| VIEWER-V5-0185 | viewer_openbim | PARTIAL | Onderzoek en implementeer indien meetbaar beter: metadata manifest; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L507) |
| VIEWER-V5-0186 | viewer_openbim | PARTIAL | Onderzoek en implementeer indien meetbaar beter: persisted normals; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L508) |
| VIEWER-V5-0187 | viewer_openbim | PARTIAL | Onderzoek en implementeer indien meetbaar beter: persisted feature edges; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L509) |
| VIEWER-V5-0188 | viewer_openbim | PARTIAL | Onderzoek en implementeer indien meetbaar beter: persisted LOD/coarse mesh; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L510) |
| VIEWER-V5-0189 | viewer_openbim | PARTIAL | Onderzoek en implementeer indien meetbaar beter: provider/settings/schema in key; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L511) |
| VIEWER-V5-0190 | viewer_openbim | PARTIAL | Onderzoek en implementeer indien meetbaar beter: corruption detection; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L512) |
| VIEWER-V5-0191 | viewer_openbim | PARTIAL | Onderzoek en implementeer indien meetbaar beter: invalidation; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L513) |
| VIEWER-V5-0192 | viewer_openbim | PARTIAL | Onderzoek en implementeer indien meetbaar beter: cache migration/fallback; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L514) |
| VIEWER-V5-0193 | viewer_openbim | PARTIAL | Onderzoek en implementeer indien meetbaar beter: bounded RAM LRU. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L515) |
| VIEWER-V5-0194 | viewer_openbim | PARTIAL | Meet: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L517) |
| VIEWER-V5-0195 | viewer_openbim | PARTIAL | Cache mag nooit stale geometry tonen na bronwijziging. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L526) |
| VIEWER-V5-0196 | viewer_openbim | PARTIAL | Voorkom dat background loading alsnog de GUI blokkeert. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L532) |
| VIEWER-V5-0197 | viewer_openbim | PARTIAL | Maak een centrale scene patch/upload queue. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L534) |
| VIEWER-V5-0198 | viewer_openbim | PARTIAL | Eisen: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L536) |
| VIEWER-V5-0199 | viewer_openbim | PARTIAL | Eisen: maximum work per UI frame; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L538) |
| VIEWER-V5-0200 | viewer_openbim | PARTIAL | Eisen: target bijvoorbeeld 2–6 ms per frame, dynamisch; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L539) |
| VIEWER-V5-0201 | viewer_openbim | PARTIAL | Eisen: grote batches in kleinere incremental batches; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L540) |
| VIEWER-V5-0202 | viewer_openbim | PARTIAL | Eisen: selection/visibility state behouden; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L541) |
| VIEWER-V5-0203 | viewer_openbim | PARTIAL | Eisen: camera niet resetten; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L542) |
| VIEWER-V5-0204 | viewer_openbim | PARTIAL | Eisen: focus/pivot niet resetten; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L543) |
| VIEWER-V5-0205 | viewer_openbim | PARTIAL | Eisen: geen full scene rebuild tenzij structureel noodzakelijk; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L544) |
| VIEWER-V5-0206 | viewer_openbim | PARTIAL | Eisen: stale patches negeren; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L545) |
| VIEWER-V5-0207 | viewer_openbim | PARTIAL | Eisen: patch metrics loggen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L546) |
| VIEWER-V5-0208 | viewer_openbim | PARTIAL | Auditfeit: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L552) |
| VIEWER-V5-0209 | viewer_openbim | PARTIAL | de huidige adaptive backend gebruikt tijdens interactie 8x MSAA. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L554) |
| VIEWER-V5-0210 | viewer_openbim | PARTIAL | Dit moet NIET blind blijven. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L556) |
| VIEWER-V5-0211 | viewer_openbim | PARTIAL | Benchmark: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L558) |
| VIEWER-V5-0212 | viewer_openbim | PARTIAL | in: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L567) |
| VIEWER-V5-0213 | viewer_openbim | PARTIAL | in: klein model; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L569) |
| VIEWER-V5-0214 | viewer_openbim | PARTIAL | in: medium model; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L570) |
| VIEWER-V5-0215 | viewer_openbim | PARTIAL | in: groot model; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L571) |
| VIEWER-V5-0216 | viewer_openbim | PARTIAL | in: integrated GPU indien beschikbaar; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L572) |
| VIEWER-V5-0217 | viewer_openbim | PARTIAL | in: discrete GPU. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L573) |
| VIEWER-V5-0218 | viewer_openbim | PARTIAL | Doel: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L575) |
| VIEWER-V5-0219 | viewer_openbim | PARTIAL | Doel: tijdens beweging maximale respons; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L577) |
| VIEWER-V5-0220 | viewer_openbim | PARTIAL | Doel: na idle snel terug naar hoge kwaliteit. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L578) |
| VIEWER-V5-0221 | viewer_openbim | PARTIAL | Mogelijk target: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L580) |
| VIEWER-V5-0222 | viewer_openbim | PARTIAL | Maar implementeer op basis van metingen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L594) |
| VIEWER-V5-0223 | viewer_openbim | PARTIAL | De huidige ongeveer 60 Hz scheduler is een goede basis. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L600) |
| VIEWER-V5-0224 | viewer_openbim | PARTIAL | Breid dit alleen uit als het stabiel kan: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L602) |
| VIEWER-V5-0225 | viewer_openbim | PARTIAL | Breid dit alleen uit als het stabiel kan: detecteer display refresh of effectieve framebudgetcontext; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L604) |
| VIEWER-V5-0226 | viewer_openbim | PARTIAL | Breid dit alleen uit als het stabiel kan: ondersteun 60/120/144 Hz zonder raw-event render storm; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L605) |
| VIEWER-V5-0227 | viewer_openbim | PARTIAL | Breid dit alleen uit als het stabiel kan: coalesce motion events; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L606) |
| VIEWER-V5-0228 | viewer_openbim | PARTIAL | Breid dit alleen uit als het stabiel kan: één authoritative frame scheduler; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L607) |
| VIEWER-V5-0229 | viewer_openbim | PARTIAL | Breid dit alleen uit als het stabiel kan: voorkom duplicate renders per input event; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L608) |
| VIEWER-V5-0230 | viewer_openbim | PARTIAL | Breid dit alleen uit als het stabiel kan: fallback naar 60 Hz als GPU/scene framebudget niet haalbaar is. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L609) |
| VIEWER-V5-0231 | viewer_openbim | PARTIAL | Geen kunstmatige 144 Hz claim wanneer frames feitelijk 40 ms duren. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L611) |
| VIEWER-V5-0232 | viewer_openbim | PARTIAL | De selectie moet altijd het complete maakdeel/assembly correct raken. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L617) |
| VIEWER-V5-0233 | viewer_openbim | PARTIAL | Pipeline: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L619) |
| VIEWER-V5-0234 | viewer_openbim | PARTIAL | Gates: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L631) |
| VIEWER-V5-0235 | viewer_openbim | PARTIAL | Test: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L640) |
| VIEWER-V5-0236 | viewer_openbim | PARTIAL | Test: lange liggers; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L642) |
| VIEWER-V5-0237 | viewer_openbim | PARTIAL | Test: identieke profielen; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L643) |
| VIEWER-V5-0238 | viewer_openbim | PARTIAL | Test: dicht op elkaar liggende instances; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L644) |
| VIEWER-V5-0239 | viewer_openbim | PARTIAL | Test: assemblies; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L645) |
| VIEWER-V5-0240 | viewer_openbim | PARTIAL | Test: partially hidden; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L646) |
| VIEWER-V5-0241 | viewer_openbim | PARTIAL | Test: transparency; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L647) |
| VIEWER-V5-0242 | viewer_openbim | PARTIAL | Test: clipping; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L648) |
| VIEWER-V5-0243 | viewer_openbim | PARTIAL | Test: explode; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L649) |
| VIEWER-V5-0244 | viewer_openbim | PARTIAL | Test: proxy → exact patch; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L650) |
| VIEWER-V5-0245 | viewer_openbim | PARTIAL | Test: multi-selection. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L651) |
| VIEWER-V5-0246 | viewer_openbim | PARTIAL | Doel is geen proprietary codekopie. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L657) |
| VIEWER-V5-0247 | viewer_openbim | PARTIAL | Doel is **observable behavior parity**. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L659) |
| VIEWER-V5-0248 | viewer_openbim | PARTIAL | Maak: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L661) |
| VIEWER-V5-0249 | viewer_openbim | PARTIAL | Cases minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L676) |
| VIEWER-V5-0250 | viewer_openbim | PARTIAL | Toleranties: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L723) |
| VIEWER-V5-0251 | viewer_openbim | PARTIAL | Toleranties: wheel zoom ratio ±2% t.o.v. Trimble reference; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L725) |
| VIEWER-V5-0252 | viewer_openbim | PARTIAL | Toleranties: fixed-drag pan/orbit result ±2 px of ±2%; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L726) |
| VIEWER-V5-0253 | viewer_openbim | PARTIAL | Toleranties: pivot drift ≤ 2 px; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L727) |
| VIEWER-V5-0254 | viewer_openbim | PARTIAL | Toleranties: standard-view orientation ≤ 0.1°; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L728) |
| VIEWER-V5-0255 | viewer_openbim | PARTIAL | Toleranties: fit occupancy ±2%; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L729) |
| VIEWER-V5-0256 | viewer_openbim | PARTIAL | Toleranties: wrong mapping = 0; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L730) |
| VIEWER-V5-0257 | viewer_openbim | PARTIAL | Toleranties: unwanted roll = 0. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L731) |
| VIEWER-V5-0258 | viewer_openbim | PARTIAL | Als geen Trimble reference beschikbaar is: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L733) |
| VIEWER-V5-0259 | viewer_openbim | PARTIAL | Nooit zelf screenshots als “Trimble reference” verzinnen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L739) |
| VIEWER-V5-0260 | viewer_openbim | PARTIAL | Maak minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L745) |
| VIEWER-V5-0261 | viewer_openbim | PARTIAL | Plus Windows: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L765) |
| VIEWER-V5-0262 | viewer_openbim | PARTIAL | Plus Windows: one-folder build; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L767) |
| VIEWER-V5-0263 | viewer_openbim | PARTIAL | Plus Windows: fresh portable; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L768) |
| VIEWER-V5-0264 | viewer_openbim | PARTIAL | Plus Windows: smoke run zonder developer Python PATH; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L769) |
| VIEWER-V5-0265 | viewer_openbim | PARTIAL | Plus Windows: packaged Viewer benchmark; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L770) |
| VIEWER-V5-0266 | viewer_openbim | PARTIAL | Plus Windows: packaged large-model test. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L771) |
| VIEWER-V5-0267 | viewer_openbim | PARTIAL | Alleen PASS als: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L775) |
| VIEWER-V5-0268 | viewer_openbim | PARTIAL | Alleen PASS als: Viewer build werkt; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L777) |
| VIEWER-V5-0269 | viewer_openbim | PARTIAL | Alleen PASS als: load benchmark bestaat; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L778) |
| VIEWER-V5-0270 | viewer_openbim | PARTIAL | Alleen PASS als: no regression correctness; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L779) |
| VIEWER-V5-0271 | viewer_openbim | PARTIAL | Alleen PASS als: no UI freeze > target; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L780) |
| VIEWER-V5-0272 | viewer_openbim | PARTIAL | Alleen PASS als: picking gates PASS; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L781) |
| VIEWER-V5-0273 | viewer_openbim | PARTIAL | Alleen PASS als: worker/cancel/restart PASS; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L782) |
| VIEWER-V5-0274 | viewer_openbim | PARTIAL | Alleen PASS als: cache invalidation PASS; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L783) |
| VIEWER-V5-0275 | viewer_openbim | PARTIAL | Alleen PASS als: packaged benchmark PASS; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L784) |
| VIEWER-V5-0276 | viewer_openbim | PARTIAL | Alleen PASS als: Trimble parity PASS **of**, indien reference werkelijk niet beschikbaar is, expliciet `BLOCKED/NOT_TESTED` en de fase mag dan NIET als volledige parity-release worden geclaimd. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L785) |
| VIEWER-V5-0277 | viewer_openbim | PARTIAL | Voer de **laatste goedgekeurde V5/V5.1 UI** daadwerkelijk door. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L795) |
| VIEWER-V5-0278 | viewer_openbim | PARTIAL | De UI is niet alleen styling. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L797) |
| VIEWER-V5-0279 | viewer_openbim | PARTIAL | De UI moet de bestaande én nieuwe services correct ontsluiten. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L799) |
| VIEWER-V5-0280 | viewer_openbim | PARTIAL | Doel: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L801) |
| VIEWER-V5-0281 | viewer_openbim | PARTIAL | Doel: rustige professionele productinterface; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L803) |
| VIEWER-V5-0282 | viewer_openbim | PARTIAL | Doel: vaste terminologie; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L804) |
| VIEWER-V5-0283 | viewer_openbim | PARTIAL | Doel: geen zichtbare legacy V6/V9/V15/M18/U4/experimental labels voor normale gebruiker; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L805) |
| VIEWER-V5-0284 | viewer_openbim | PARTIAL | Doel: een eenvoudige hoofdworkflow; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L806) |
| VIEWER-V5-0285 | viewer_openbim | PARTIAL | Doel: alle controls functioneel; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L807) |
| VIEWER-V5-0286 | viewer_openbim | PARTIAL | Doel: contextbehoud; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L808) |
| VIEWER-V5-0287 | viewer_openbim | PARTIAL | Doel: productie-acties logisch vanuit Viewer, BOM en Bewerken. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L809) |
| VIEWER-V5-0288 | viewer_openbim | PARTIAL | Gebruik de laatste UI package/spec als bindende visuele bron. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L815) |
| VIEWER-V5-0289 | viewer_openbim | PARTIAL | Verwachte scope uit de laatste UI master: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L817) |
| VIEWER-V5-0290 | viewer_openbim | PARTIAL | Verwachte scope uit de laatste UI master: 25 bindende PNG screens; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L819) |
| VIEWER-V5-0291 | viewer_openbim | PARTIAL | Verwachte scope uit de laatste UI master: 31 total screens/support surfaces; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L820) |
| VIEWER-V5-0292 | viewer_openbim | PARTIAL | Verwachte scope uit de laatste UI master: 226 bindende controls/test IDs; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L821) |
| VIEWER-V5-0293 | viewer_openbim | PARTIAL | Verwachte scope uit de laatste UI master: screen manifest; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L822) |
| VIEWER-V5-0294 | viewer_openbim | PARTIAL | Verwachte scope uit de laatste UI master: control inventory; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L823) |
| VIEWER-V5-0295 | viewer_openbim | PARTIAL | Verwachte scope uit de laatste UI master: component catalog; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L824) |
| VIEWER-V5-0296 | viewer_openbim | PARTIAL | Verwachte scope uit de laatste UI master: text master; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L825) |
| VIEWER-V5-0297 | viewer_openbim | PARTIAL | Verwachte scope uit de laatste UI master: invariants; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L826) |
| VIEWER-V5-0298 | viewer_openbim | PARTIAL | Verwachte scope uit de laatste UI master: DO NOT CHANGE. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L827) |
| VIEWER-V5-0299 | viewer_openbim | PARTIAL | Als die bestanden niet in repo/workspace beschikbaar zijn: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L829) |
| VIEWER-V5-0300 | viewer_openbim | PARTIAL | Als die bestanden niet in repo/workspace beschikbaar zijn: 1. zoek projectinputs; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L831) |
| VIEWER-V5-0301 | viewer_openbim | PARTIAL | Als die bestanden niet in repo/workspace beschikbaar zijn: 2. zoek generated design package; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L832) |
| VIEWER-V5-0302 | viewer_openbim | PARTIAL | Als die bestanden niet in repo/workspace beschikbaar zijn: 3. zoek File/attachment references indien beschikbaar in de buildomgeving; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L833) |
| VIEWER-V5-0303 | viewer_openbim | PARTIAL | Als die bestanden niet in repo/workspace beschikbaar zijn: 4. documenteer exact wat ontbreekt; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L834) |
| VIEWER-V5-0304 | viewer_openbim | PARTIAL | Als die bestanden niet in repo/workspace beschikbaar zijn: 5. NIET improviseren alsof de referentie gezien is. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L835) |
| VIEWER-V5-0305 | viewer_openbim | PARTIAL | Houd de primaire productstructuur compact. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L841) |
| VIEWER-V5-0306 | viewer_openbim | PARTIAL | De definitieve globale hoofdnavigatie is exact: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L843) |
| VIEWER-V5-0307 | viewer_openbim | PARTIAL | Settings/Help/Activity/Problems/Quick Action zijn secundaire globale functies en geen zesde hoofdworkspace. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L853) |
| VIEWER-V5-0308 | viewer_openbim | PARTIAL | Deze indeling volgt de laatste V5.1 UI authority en mag niet door een oudere shellindeling worden overschreven. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L887) |
| VIEWER-V5-0309 | viewer_openbim | PARTIAL | Maak één authoritative context action service. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L893) |
| VIEWER-V5-0310 | viewer_openbim | PARTIAL | Bijvoorbeeld: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L895) |
| VIEWER-V5-0311 | viewer_openbim | PARTIAL | Actions: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L904) |
| VIEWER-V5-0312 | viewer_openbim | PARTIAL | Dezelfde actie vanuit Viewer, BOM, Tree of Bewerken moet: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L916) |
| VIEWER-V5-0313 | viewer_openbim | PARTIAL | Dezelfde actie vanuit Viewer, BOM, Tree of Bewerken moet: dezelfde command authority gebruiken; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L918) |
| VIEWER-V5-0314 | viewer_openbim | PARTIAL | Dezelfde actie vanuit Viewer, BOM, Tree of Bewerken moet: dezelfde entity scope gebruiken; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L919) |
| VIEWER-V5-0315 | viewer_openbim | PARTIAL | Dezelfde actie vanuit Viewer, BOM, Tree of Bewerken moet: dezelfde validation uitvoeren; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L920) |
| VIEWER-V5-0316 | viewer_openbim | PARTIAL | Dezelfde actie vanuit Viewer, BOM, Tree of Bewerken moet: dezelfde audit trail geven. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L921) |
| VIEWER-V5-0317 | viewer_openbim | PARTIAL | Verboden: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L923) |
| VIEWER-V5-0318 | viewer_openbim | PARTIAL | vier verschillende `print_selected()` implementations per workspace. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L925) |
| VIEWER-V5-0319 | viewer_openbim | PARTIAL | Iedere interactieve Qt-control moet in runtime inventaris terechtkomen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L931) |
| VIEWER-V5-0320 | viewer_openbim | PARTIAL | Scan dynamisch: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L933) |
| VIEWER-V5-0321 | viewer_openbim | PARTIAL | Scan dynamisch: QPushButton; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L935) |
| VIEWER-V5-0322 | viewer_openbim | PARTIAL | Scan dynamisch: QToolButton; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L936) |
| VIEWER-V5-0323 | viewer_openbim | PARTIAL | Scan dynamisch: QAction; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L937) |
| VIEWER-V5-0324 | viewer_openbim | PARTIAL | Scan dynamisch: QCheckBox; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L938) |
| VIEWER-V5-0325 | viewer_openbim | PARTIAL | Scan dynamisch: QRadioButton; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L939) |
| VIEWER-V5-0326 | viewer_openbim | PARTIAL | Scan dynamisch: QComboBox; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L940) |
| VIEWER-V5-0327 | viewer_openbim | PARTIAL | Scan dynamisch: QLineEdit; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L941) |
| VIEWER-V5-0328 | viewer_openbim | PARTIAL | Scan dynamisch: QSpinBox; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L942) |
| VIEWER-V5-0329 | viewer_openbim | PARTIAL | Scan dynamisch: QDoubleSpinBox; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L943) |
| VIEWER-V5-0330 | viewer_openbim | PARTIAL | Scan dynamisch: QSlider; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L944) |
| VIEWER-V5-0331 | viewer_openbim | PARTIAL | Scan dynamisch: QTableView/QTableWidget acties; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L945) |
| VIEWER-V5-0332 | viewer_openbim | PARTIAL | Scan dynamisch: QTreeView/QTreeWidget acties; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L946) |
| VIEWER-V5-0333 | viewer_openbim | PARTIAL | Scan dynamisch: tabs; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L947) |
| VIEWER-V5-0334 | viewer_openbim | PARTIAL | Scan dynamisch: menus; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L948) |
| VIEWER-V5-0335 | viewer_openbim | PARTIAL | Scan dynamisch: docks; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L949) |
| VIEWER-V5-0336 | viewer_openbim | PARTIAL | Scan dynamisch: contextmenus. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L950) |
| VIEWER-V5-0337 | viewer_openbim | PARTIAL | Per control: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L952) |
| VIEWER-V5-0338 | viewer_openbim | PARTIAL | Onbekende/ongecoverde interactieve control = `FAIL`. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L972) |
| VIEWER-V5-0339 | viewer_openbim | PARTIAL | Iedere control: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L974) |
| VIEWER-V5-0340 | viewer_openbim | PARTIAL | Iedere control: werkt; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L976) |
| VIEWER-V5-0341 | viewer_openbim | PARTIAL | Iedere control: of is disabled met concrete reden; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L977) |
| VIEWER-V5-0342 | viewer_openbim | PARTIAL | Iedere control: of is expliciet hidden conform spec. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L978) |
| VIEWER-V5-0343 | viewer_openbim | PARTIAL | Geen klikbare placebo. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L980) |
| VIEWER-V5-0344 | viewer_openbim | PARTIAL | Test minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L986) |
| VIEWER-V5-0345 | viewer_openbim | PARTIAL | DPI: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L994) |
| VIEWER-V5-0346 | viewer_openbim | PARTIAL | Gates: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1003) |
| VIEWER-V5-0347 | viewer_openbim | PARTIAL | Gebruik screenshots en reference comparison. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1015) |
| VIEWER-V5-0348 | viewer_openbim | PARTIAL | Niet alleen headless widget tests. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1017) |
| VIEWER-V5-0349 | viewer_openbim | PARTIAL | De huidige BOM quantity truth moet behouden blijven. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1023) |
| VIEWER-V5-0350 | viewer_openbim | PARTIAL | Machine-routing is een aparte truth en wordt gejoined via canonical IDs. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1025) |
| VIEWER-V5-0351 | viewer_openbim | PARTIAL | Niet machinevelden rechtstreeks “in de quantity waarheid” bakken. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1027) |
| VIEWER-V5-0352 | viewer_openbim | PARTIAL | Maak of consolideer versioned modellen zoals: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1029) |
| VIEWER-V5-0353 | viewer_openbim | PARTIAL | Ondersteun minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1041) |
| VIEWER-V5-0354 | viewer_openbim | PARTIAL | Ondersteun minimaal: Project; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1043) |
| VIEWER-V5-0355 | viewer_openbim | PARTIAL | Ondersteun minimaal: Assemblies; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1044) |
| VIEWER-V5-0356 | viewer_openbim | PARTIAL | Ondersteun minimaal: Parts; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1045) |
| VIEWER-V5-0357 | viewer_openbim | PARTIAL | Ondersteun minimaal: Purchased; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1046) |
| VIEWER-V5-0358 | viewer_openbim | PARTIAL | Ondersteun minimaal: Fasteners; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1047) |
| VIEWER-V5-0359 | viewer_openbim | PARTIAL | Ondersteun minimaal: Welds; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1048) |
| VIEWER-V5-0360 | viewer_openbim | PARTIAL | Ondersteun minimaal: Materials; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1049) |
| VIEWER-V5-0361 | viewer_openbim | PARTIAL | Ondersteun minimaal: Profiles; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1050) |
| VIEWER-V5-0362 | viewer_openbim | PARTIAL | Ondersteun minimaal: Weight/Area/Coating; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1051) |
| VIEWER-V5-0363 | viewer_openbim | PARTIAL | Ondersteun minimaal: Stock/Remnants/Purchase; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1052) |
| VIEWER-V5-0364 | viewer_openbim | PARTIAL | Ondersteun minimaal: Nesting; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1053) |
| VIEWER-V5-0365 | viewer_openbim | PARTIAL | Ondersteun minimaal: Machine Routing; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1054) |
| VIEWER-V5-0366 | viewer_openbim | PARTIAL | Ondersteun minimaal: Drawing; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1055) |
| VIEWER-V5-0367 | viewer_openbim | PARTIAL | Ondersteun minimaal: Manufacturing; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1056) |
| VIEWER-V5-0368 | viewer_openbim | PARTIAL | Ondersteun minimaal: Scribing; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1057) |
| VIEWER-V5-0369 | viewer_openbim | PARTIAL | Ondersteun minimaal: Release/Blockers; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1058) |
| VIEWER-V5-0370 | viewer_openbim | PARTIAL | Ondersteun minimaal: Traceability. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1059) |
| VIEWER-V5-0371 | viewer_openbim | PARTIAL | Niet alles standaard tonen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1061) |
| VIEWER-V5-0372 | viewer_openbim | PARTIAL | Gebruik rustige presets: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1063) |
| VIEWER-V5-0373 | viewer_openbim | PARTIAL | Maak onafhankelijke BOM validation. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1106) |
| VIEWER-V5-0374 | viewer_openbim | PARTIAL | Gates: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1108) |
| VIEWER-V5-0375 | viewer_openbim | PARTIAL | Valideer onafhankelijk: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1117) |
| VIEWER-V5-0376 | viewer_openbim | PARTIAL | Valideer onafhankelijk: aantallen; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1119) |
| VIEWER-V5-0377 | viewer_openbim | PARTIAL | Valideer onafhankelijk: lengtes; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1120) |
| VIEWER-V5-0378 | viewer_openbim | PARTIAL | Valideer onafhankelijk: profiel; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1121) |
| VIEWER-V5-0379 | viewer_openbim | PARTIAL | Valideer onafhankelijk: materiaal; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1122) |
| VIEWER-V5-0380 | viewer_openbim | PARTIAL | Valideer onafhankelijk: gewicht; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1123) |
| VIEWER-V5-0381 | viewer_openbim | PARTIAL | Valideer onafhankelijk: oppervlakte; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1124) |
| VIEWER-V5-0382 | viewer_openbim | PARTIAL | Valideer onafhankelijk: assemblies; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1125) |
| VIEWER-V5-0383 | viewer_openbim | PARTIAL | Valideer onafhankelijk: purchased; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1126) |
| VIEWER-V5-0384 | viewer_openbim | PARTIAL | Valideer onafhankelijk: fasteners; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1127) |
| VIEWER-V5-0385 | viewer_openbim | PARTIAL | Valideer onafhankelijk: welds; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1128) |
| VIEWER-V5-0386 | viewer_openbim | PARTIAL | Valideer onafhankelijk: status; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1129) |
| VIEWER-V5-0387 | viewer_openbim | PARTIAL | Valideer onafhankelijk: blockers; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1130) |
| VIEWER-V5-0388 | viewer_openbim | PARTIAL | Valideer onafhankelijk: source IDs; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1131) |
| VIEWER-V5-0389 | viewer_openbim | PARTIAL | Valideer onafhankelijk: hashes. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1132) |
| VIEWER-V5-0390 | viewer_openbim | PARTIAL | Rond alleen display. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1134) |
| VIEWER-V5-0391 | viewer_openbim | PARTIAL | Nooit round-trip business truth uit afgeronde UI-string. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1136) |
| VIEWER-V5-0392 | viewer_openbim | PARTIAL | Doel: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1142) |
| VIEWER-V5-0393 | viewer_openbim | PARTIAL | na import automatisch een logische machine voorstellen/toewijzen, maar eenvoudig handmatig wijzigbaar. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1144) |
| VIEWER-V5-0394 | viewer_openbim | PARTIAL | Geen hardcoded “als IPE dan machine X” in UI-code. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1146) |
| VIEWER-V5-0395 | viewer_openbim | PARTIAL | Gebruik capabilities. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1148) |
| VIEWER-V5-0396 | viewer_openbim | PARTIAL | Input: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1150) |
| VIEWER-V5-0397 | viewer_openbim | PARTIAL | Resultaat: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1167) |
| VIEWER-V5-0398 | viewer_openbim | PARTIAL | Velden: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1180) |
| VIEWER-V5-0399 | viewer_openbim | PARTIAL | Eenvoudige mapping UI: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1195) |
| VIEWER-V5-0400 | viewer_openbim | PARTIAL | per groep een voorkeursmachine/prioriteit. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1208) |
| VIEWER-V5-0401 | viewer_openbim | PARTIAL | Volledige capability rules. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1212) |
| VIEWER-V5-0402 | viewer_openbim | PARTIAL | Ondersteun: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1216) |
| VIEWER-V5-0403 | viewer_openbim | PARTIAL | Ondersteun: row assign; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1218) |
| VIEWER-V5-0404 | viewer_openbim | PARTIAL | Ondersteun: multi-row bulk assign; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1219) |
| VIEWER-V5-0405 | viewer_openbim | PARTIAL | Ondersteun: reset Auto; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1220) |
| VIEWER-V5-0406 | viewer_openbim | PARTIAL | Ondersteun: manual lock; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1221) |
| VIEWER-V5-0407 | viewer_openbim | PARTIAL | Ondersteun: “waarom deze machine?”; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1222) |
| VIEWER-V5-0408 | viewer_openbim | PARTIAL | Ondersteun: filter unassigned/review/blocked. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1223) |
| VIEWER-V5-0409 | viewer_openbim | PARTIAL | Een incompatibele handmatige machinekeuze mag eventueel vastgelegd worden voor review, maar: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1225) |
| VIEWER-V5-0410 | viewer_openbim | PARTIAL | Niet stilzwijgend READY. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1231) |
| VIEWER-V5-0411 | viewer_openbim | PARTIAL | UI mag standaard één Hoofdmachine tonen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1235) |
| VIEWER-V5-0412 | viewer_openbim | PARTIAL | Backend moet uitbreidbaar zijn naar: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1237) |
| VIEWER-V5-0413 | viewer_openbim | PARTIAL | voor zaag/boor/scribe/plate/etc. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1243) |
| VIEWER-V5-0414 | viewer_openbim | PARTIAL | Niet opnieuw schrijven als de bestaande backend correct is. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1249) |
| VIEWER-V5-0415 | viewer_openbim | PARTIAL | Doe: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1251) |
| VIEWER-V5-0416 | viewer_openbim | PARTIAL | Doe: inventariseer actuele Profile Nesting capabilities; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1253) |
| VIEWER-V5-0417 | viewer_openbim | PARTIAL | Doe: preserve solver/validator; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1254) |
| VIEWER-V5-0418 | viewer_openbim | PARTIAL | Doe: verbind contextacties; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1255) |
| VIEWER-V5-0419 | viewer_openbim | PARTIAL | Doe: verbind machine routing; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1256) |
| VIEWER-V5-0420 | viewer_openbim | PARTIAL | Doe: verbind stock/remnants; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1257) |
| VIEWER-V5-0421 | viewer_openbim | PARTIAL | Doe: verbind BOM; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1258) |
| VIEWER-V5-0422 | viewer_openbim | PARTIAL | Doe: verbind output/print; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1259) |
| VIEWER-V5-0423 | viewer_openbim | PARTIAL | Doe: voeg alleen ontbrekende functionaliteit toe; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1260) |
| VIEWER-V5-0424 | viewer_openbim | PARTIAL | Doe: voer determinism + regression tests uit. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1261) |
| VIEWER-V5-0425 | viewer_openbim | PARTIAL | Workflow: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1263) |
| VIEWER-V5-0426 | viewer_openbim | PARTIAL | Auditfeit: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1280) |
| VIEWER-V5-0427 | viewer_openbim | PARTIAL | huidige core is een kleine rectangular shelf solver. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1282) |
| VIEWER-V5-0428 | viewer_openbim | PARTIAL | Dat is onvoldoende voor finale scope. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1284) |
| VIEWER-V5-0429 | viewer_openbim | PARTIAL | Behoud die solver eventueel als eenvoudige fallback/baseline, maar maak een volledige plate nesting authority. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1286) |
| VIEWER-V5-0430 | viewer_openbim | PARTIAL | Minimaal ondersteunen: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1288) |
| VIEWER-V5-0431 | viewer_openbim | PARTIAL | Minimaal ondersteunen: arbitrary closed polygons; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1290) |
| VIEWER-V5-0432 | viewer_openbim | PARTIAL | Minimaal ondersteunen: concave contours; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1291) |
| VIEWER-V5-0433 | viewer_openbim | PARTIAL | Minimaal ondersteunen: internal holes/cutouts; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1292) |
| VIEWER-V5-0434 | viewer_openbim | PARTIAL | Minimaal ondersteunen: thickness; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1293) |
| VIEWER-V5-0435 | viewer_openbim | PARTIAL | Minimaal ondersteunen: material; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1294) |
| VIEWER-V5-0436 | viewer_openbim | PARTIAL | Minimaal ondersteunen: grade; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1295) |
| VIEWER-V5-0437 | viewer_openbim | PARTIAL | Minimaal ondersteunen: part quantity; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1296) |
| VIEWER-V5-0438 | viewer_openbim | PARTIAL | Minimaal ondersteunen: rotation policy; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1297) |
| VIEWER-V5-0439 | viewer_openbim | PARTIAL | Minimaal ondersteunen: mirror policy; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1298) |
| VIEWER-V5-0440 | viewer_openbim | PARTIAL | Minimaal ondersteunen: grain direction; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1299) |
| VIEWER-V5-0441 | viewer_openbim | PARTIAL | Minimaal ondersteunen: kerf; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1300) |
| VIEWER-V5-0442 | viewer_openbim | PARTIAL | Minimaal ondersteunen: margin; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1301) |
| VIEWER-V5-0443 | viewer_openbim | PARTIAL | Minimaal ondersteunen: clamp/edge zones; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1302) |
| VIEWER-V5-0444 | viewer_openbim | PARTIAL | Minimaal ondersteunen: true stock sheet polygons; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1303) |
| VIEWER-V5-0445 | viewer_openbim | PARTIAL | Minimaal ondersteunen: remnant polygons; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1304) |
| VIEWER-V5-0446 | viewer_openbim | PARTIAL | Minimaal ondersteunen: reservations; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1305) |
| VIEWER-V5-0447 | viewer_openbim | PARTIAL | Minimaal ondersteunen: manual placement; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1306) |
| VIEWER-V5-0448 | viewer_openbim | PARTIAL | Minimaal ondersteunen: lock placement; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1307) |
| VIEWER-V5-0449 | viewer_openbim | PARTIAL | Minimaal ondersteunen: unplaced demand; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1308) |
| VIEWER-V5-0450 | viewer_openbim | PARTIAL | Minimaal ondersteunen: deterministic result; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1309) |
| VIEWER-V5-0451 | viewer_openbim | PARTIAL | Minimaal ondersteunen: exact overlap validator; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1310) |
| VIEWER-V5-0452 | viewer_openbim | PARTIAL | Minimaal ondersteunen: containment validator; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1311) |
| VIEWER-V5-0453 | viewer_openbim | PARTIAL | Minimaal ondersteunen: remnant generation; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1312) |
| VIEWER-V5-0454 | viewer_openbim | PARTIAL | Minimaal ondersteunen: utilization; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1313) |
| VIEWER-V5-0455 | viewer_openbim | PARTIAL | Minimaal ondersteunen: traceability; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1314) |
| VIEWER-V5-0456 | viewer_openbim | PARTIAL | Minimaal ondersteunen: proof/status. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1315) |
| VIEWER-V5-0457 | viewer_openbim | PARTIAL | Waar common-line cutting wordt ondersteund: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1317) |
| VIEWER-V5-0458 | viewer_openbim | PARTIAL | Waar common-line cutting wordt ondersteund: expliciete policy; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1319) |
| VIEWER-V5-0459 | viewer_openbim | PARTIAL | Waar common-line cutting wordt ondersteund: machine capability gate; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1320) |
| VIEWER-V5-0460 | viewer_openbim | PARTIAL | Waar common-line cutting wordt ondersteund: geometrische bewijsregels; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1321) |
| VIEWER-V5-0461 | viewer_openbim | PARTIAL | Waar common-line cutting wordt ondersteund: geen impliciete common-line. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1322) |
| VIEWER-V5-0462 | viewer_openbim | PARTIAL | Maak separate solver en validator. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1324) |
| VIEWER-V5-0463 | viewer_openbim | PARTIAL | Een solverresultaat is pas bruikbaar als independent validation PASS is. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1326) |
| VIEWER-V5-0464 | viewer_openbim | PARTIAL | Auditfeit: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1332) |
| VIEWER-V5-0465 | viewer_openbim | PARTIAL | de huidige `EngineeringDrawingGenerator` gebruikt PIL/rasteroutput. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1334) |
| VIEWER-V5-0466 | viewer_openbim | PARTIAL | Dat mag voor review thumbnails/legacy compatibility blijven, maar niet als canonical Production Drawing engine. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1336) |
| VIEWER-V5-0467 | viewer_openbim | PARTIAL | Bouw: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1338) |
| VIEWER-V5-0468 | viewer_openbim | PARTIAL | Production PDF: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1358) |
| VIEWER-V5-0469 | viewer_openbim | PARTIAL | Production PDF: technische lijnen = vector; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1360) |
| VIEWER-V5-0470 | viewer_openbim | PARTIAL | Production PDF: maatlijnen = vector; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1361) |
| VIEWER-V5-0471 | viewer_openbim | PARTIAL | Production PDF: pijlpunten = vector; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1362) |
| VIEWER-V5-0472 | viewer_openbim | PARTIAL | Production PDF: centerlines = vector; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1363) |
| VIEWER-V5-0473 | viewer_openbim | PARTIAL | Production PDF: tekst = echte tekst/vector; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1364) |
| VIEWER-V5-0474 | viewer_openbim | PARTIAL | Production PDF: geen full-page JPEG/PNG; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1365) |
| VIEWER-V5-0475 | viewer_openbim | PARTIAL | Production PDF: raster alleen optioneel voor kleine shaded iso inset. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1366) |
| VIEWER-V5-0476 | viewer_openbim | PARTIAL | Scherp op: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1368) |
| VIEWER-V5-0477 | viewer_openbim | PARTIAL | Portrait/landscape waar relevant. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1387) |
| VIEWER-V5-0478 | viewer_openbim | PARTIAL | Auto paper/scale. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1389) |
| VIEWER-V5-0479 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1393) |
| VIEWER-V5-0480 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: part mark; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1395) |
| VIEWER-V5-0481 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: assembly mark; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1396) |
| VIEWER-V5-0482 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: profile; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1397) |
| VIEWER-V5-0483 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: material; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1398) |
| VIEWER-V5-0484 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: length; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1399) |
| VIEWER-V5-0485 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: quantity; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1400) |
| VIEWER-V5-0486 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: revision; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1401) |
| VIEWER-V5-0487 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: project; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1402) |
| VIEWER-V5-0488 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: page; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1403) |
| VIEWER-V5-0489 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: units; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1404) |
| VIEWER-V5-0490 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: scale; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1405) |
| VIEWER-V5-0491 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: status; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1406) |
| VIEWER-V5-0492 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: source/revision binding; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1407) |
| VIEWER-V5-0493 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: manufacturing hash / drawing hash waar passend; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1408) |
| VIEWER-V5-0494 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: front/top/side/iso; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1409) |
| VIEWER-V5-0495 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: holes; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1410) |
| VIEWER-V5-0496 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: slots; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1411) |
| VIEWER-V5-0497 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: countersinks; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1412) |
| VIEWER-V5-0498 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: miters; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1413) |
| VIEWER-V5-0499 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: end cuts; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1414) |
| VIEWER-V5-0500 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: dimensions; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1415) |
| VIEWER-V5-0501 | viewer_openbim | PARTIAL | Minimaal waar brondata beschikbaar: sections/details. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1416) |
| VIEWER-V5-0502 | viewer_openbim | PARTIAL | Blokkeer productie-uitvoer bij: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1420) |
| VIEWER-V5-0503 | viewer_openbim | PARTIAL | Blokkeer productie-uitvoer bij: ontbrekende hoofdmaat; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1422) |
| VIEWER-V5-0504 | viewer_openbim | PARTIAL | Blokkeer productie-uitvoer bij: niet gepositioneerde holes; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1423) |
| VIEWER-V5-0505 | viewer_openbim | PARTIAL | Blokkeer productie-uitvoer bij: profile mismatch; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1424) |
| VIEWER-V5-0506 | viewer_openbim | PARTIAL | Blokkeer productie-uitvoer bij: material mismatch; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1425) |
| VIEWER-V5-0507 | viewer_openbim | PARTIAL | Blokkeer productie-uitvoer bij: length mismatch; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1426) |
| VIEWER-V5-0508 | viewer_openbim | PARTIAL | Blokkeer productie-uitvoer bij: mark/quantity mismatch; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1427) |
| VIEWER-V5-0509 | viewer_openbim | PARTIAL | Blokkeer productie-uitvoer bij: incomplete titleblock; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1428) |
| VIEWER-V5-0510 | viewer_openbim | PARTIAL | Blokkeer productie-uitvoer bij: clipping; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1429) |
| VIEWER-V5-0511 | viewer_openbim | PARTIAL | Blokkeer productie-uitvoer bij: dimension collisions; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1430) |
| VIEWER-V5-0512 | viewer_openbim | PARTIAL | Blokkeer productie-uitvoer bij: contradictory dimensions; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1431) |
| VIEWER-V5-0513 | viewer_openbim | PARTIAL | Blokkeer productie-uitvoer bij: geometry outside page; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1432) |
| VIEWER-V5-0514 | viewer_openbim | PARTIAL | Blokkeer productie-uitvoer bij: non-vector technical production geometry; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1433) |
| VIEWER-V5-0515 | viewer_openbim | PARTIAL | Blokkeer productie-uitvoer bij: stale source hash/payload mismatch. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1434) |
| VIEWER-V5-0516 | viewer_openbim | PARTIAL | Preview moet: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1440) |
| VIEWER-V5-0517 | viewer_openbim | PARTIAL | Preview moet: vector PDF scherp tonen; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1442) |
| VIEWER-V5-0518 | viewer_openbim | PARTIAL | Preview moet: fit page; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1443) |
| VIEWER-V5-0519 | viewer_openbim | PARTIAL | Preview moet: fit width; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1444) |
| VIEWER-V5-0520 | viewer_openbim | PARTIAL | Preview moet: 100%; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1445) |
| VIEWER-V5-0521 | viewer_openbim | PARTIAL | Preview moet: smooth pan/zoom; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1446) |
| VIEWER-V5-0522 | viewer_openbim | PARTIAL | Preview moet: thumbnails/pages; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1447) |
| VIEWER-V5-0523 | viewer_openbim | PARTIAL | Preview moet: print preview; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1448) |
| VIEWER-V5-0524 | viewer_openbim | PARTIAL | Preview moet: 100–800% visueel schoon blijven. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1449) |
| VIEWER-V5-0525 | viewer_openbim | PARTIAL | Geen blurry preview pipeline die eerst PDF naar lage resolutie rastert. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1451) |
| VIEWER-V5-0526 | viewer_openbim | PARTIAL | Maak één authority, bijvoorbeeld: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1457) |
| VIEWER-V5-0527 | viewer_openbim | PARTIAL | Globale: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1466) |
| VIEWER-V5-0528 | viewer_openbim | PARTIAL | Print vanuit: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1472) |
| VIEWER-V5-0529 | viewer_openbim | PARTIAL | Print vanuit: Viewer; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1474) |
| VIEWER-V5-0530 | viewer_openbim | PARTIAL | Print vanuit: BOM; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1475) |
| VIEWER-V5-0531 | viewer_openbim | PARTIAL | Print vanuit: Drawing/PDF; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1476) |
| VIEWER-V5-0532 | viewer_openbim | PARTIAL | Print vanuit: Project; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1477) |
| VIEWER-V5-0533 | viewer_openbim | PARTIAL | Print vanuit: Converter. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1478) |
| VIEWER-V5-0534 | viewer_openbim | PARTIAL | Scopes: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1480) |
| VIEWER-V5-0535 | viewer_openbim | PARTIAL | Instellingen: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1496) |
| VIEWER-V5-0536 | viewer_openbim | PARTIAL | Instellingen: printer; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1498) |
| VIEWER-V5-0537 | viewer_openbim | PARTIAL | Instellingen: PDF; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1499) |
| VIEWER-V5-0538 | viewer_openbim | PARTIAL | Instellingen: paper; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1500) |
| VIEWER-V5-0539 | viewer_openbim | PARTIAL | Instellingen: orientation; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1501) |
| VIEWER-V5-0540 | viewer_openbim | PARTIAL | Instellingen: scale; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1502) |
| VIEWER-V5-0541 | viewer_openbim | PARTIAL | Instellingen: copies; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1503) |
| VIEWER-V5-0542 | viewer_openbim | PARTIAL | Instellingen: group by machine/profile/assembly; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1504) |
| VIEWER-V5-0543 | viewer_openbim | PARTIAL | Instellingen: preview. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1505) |
| VIEWER-V5-0544 | viewer_openbim | PARTIAL | Minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1509) |
| VIEWER-V5-0545 | viewer_openbim | PARTIAL | Minimaal: project; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1511) |
| VIEWER-V5-0546 | viewer_openbim | PARTIAL | Minimaal: revision; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1512) |
| VIEWER-V5-0547 | viewer_openbim | PARTIAL | Minimaal: date; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1513) |
| VIEWER-V5-0548 | viewer_openbim | PARTIAL | Minimaal: logo; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1514) |
| VIEWER-V5-0549 | viewer_openbim | PARTIAL | Minimaal: filters; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1515) |
| VIEWER-V5-0550 | viewer_openbim | PARTIAL | Minimaal: repeating table header; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1516) |
| VIEWER-V5-0551 | viewer_openbim | PARTIAL | Minimaal: readable font; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1517) |
| VIEWER-V5-0552 | viewer_openbim | PARTIAL | Minimaal: no clipping; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1518) |
| VIEWER-V5-0553 | viewer_openbim | PARTIAL | Minimaal: smart column widths; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1519) |
| VIEWER-V5-0554 | viewer_openbim | PARTIAL | Minimaal: landscape where needed; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1520) |
| VIEWER-V5-0555 | viewer_openbim | PARTIAL | Minimaal: page numbers; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1521) |
| VIEWER-V5-0556 | viewer_openbim | PARTIAL | Minimaal: totals; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1522) |
| VIEWER-V5-0557 | viewer_openbim | PARTIAL | Minimaal: routing columns optioneel. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1523) |
| VIEWER-V5-0558 | viewer_openbim | PARTIAL | Behouden wat al bestaat. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1529) |
| VIEWER-V5-0559 | viewer_openbim | PARTIAL | Niet tweede Quality backend maken. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1531) |
| VIEWER-V5-0560 | viewer_openbim | PARTIAL | Koppel V5 Productiecontrole/Controle op bestaande: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1533) |
| VIEWER-V5-0561 | viewer_openbim | PARTIAL | Koppel V5 Productiecontrole/Controle op bestaande: InspectionPlan; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1535) |
| VIEWER-V5-0562 | viewer_openbim | PARTIAL | Koppel V5 Productiecontrole/Controle op bestaande: characteristics; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1536) |
| VIEWER-V5-0563 | viewer_openbim | PARTIAL | Koppel V5 Productiecontrole/Controle op bestaande: measurements; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1537) |
| VIEWER-V5-0564 | viewer_openbim | PARTIAL | Koppel V5 Productiecontrole/Controle op bestaande: NCR; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1538) |
| VIEWER-V5-0565 | viewer_openbim | PARTIAL | Koppel V5 Productiecontrole/Controle op bestaande: rework; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1539) |
| VIEWER-V5-0566 | viewer_openbim | PARTIAL | Koppel V5 Productiecontrole/Controle op bestaande: reinspection; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1540) |
| VIEWER-V5-0567 | viewer_openbim | PARTIAL | Koppel V5 Productiecontrole/Controle op bestaande: heat certs; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1541) |
| VIEWER-V5-0568 | viewer_openbim | PARTIAL | Koppel V5 Productiecontrole/Controle op bestaande: approvals; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1542) |
| VIEWER-V5-0569 | viewer_openbim | PARTIAL | Koppel V5 Productiecontrole/Controle op bestaande: release blockers; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1543) |
| VIEWER-V5-0570 | viewer_openbim | PARTIAL | Koppel V5 Productiecontrole/Controle op bestaande: hashes. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1544) |
| VIEWER-V5-0571 | viewer_openbim | PARTIAL | E2E bewijzen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1546) |
| VIEWER-V5-0572 | viewer_openbim | PARTIAL | Dit was in eerdere completion-scope onvoldoende bewezen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1552) |
| VIEWER-V5-0573 | viewer_openbim | PARTIAL | Doe eerst een repo-audit: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1554) |
| VIEWER-V5-0574 | viewer_openbim | PARTIAL | Maak een requirement matrix van de eerdere planning/shopfloor eisen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1563) |
| VIEWER-V5-0575 | viewer_openbim | PARTIAL | Als een volwaardige planning/shopfloor subsystem volgens de eerdere bindende prompts vereist is: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1565) |
| VIEWER-V5-0576 | viewer_openbim | PARTIAL | Als een volwaardige planning/shopfloor subsystem volgens de eerdere bindende prompts vereist is: voer ontbrekende delen uit. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1567) |
| VIEWER-V5-0577 | viewer_openbim | PARTIAL | Als bepaalde ideeën later aantoonbaar zijn superseded: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1569) |
| VIEWER-V5-0578 | viewer_openbim | PARTIAL | Als bepaalde ideeën later aantoonbaar zijn superseded: markeer met source/decision; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1571) |
| VIEWER-V5-0579 | viewer_openbim | PARTIAL | Als bepaalde ideeën later aantoonbaar zijn superseded: verwijder ze niet stilzwijgend uit traceability. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1572) |
| VIEWER-V5-0580 | viewer_openbim | PARTIAL | Geen “niet gevonden dus niet nodig”. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1574) |
| VIEWER-V5-0581 | viewer_openbim | PARTIAL | Golden workflows minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1580) |
| VIEWER-V5-0582 | viewer_openbim | PARTIAL | Iedere workflow heeft: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1607) |
| VIEWER-V5-0583 | viewer_openbim | PARTIAL | Iedere workflow heeft: input fixture; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1609) |
| VIEWER-V5-0584 | viewer_openbim | PARTIAL | Iedere workflow heeft: expected canonical facts; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1610) |
| VIEWER-V5-0585 | viewer_openbim | PARTIAL | Iedere workflow heeft: expected UI state; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1611) |
| VIEWER-V5-0586 | viewer_openbim | PARTIAL | Iedere workflow heeft: expected blockers; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1612) |
| VIEWER-V5-0587 | viewer_openbim | PARTIAL | Iedere workflow heeft: expected files; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1613) |
| VIEWER-V5-0588 | viewer_openbim | PARTIAL | Iedere workflow heeft: expected hashes where deterministic; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1614) |
| VIEWER-V5-0589 | viewer_openbim | PARTIAL | Iedere workflow heeft: screenshot evidence; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1615) |
| VIEWER-V5-0590 | viewer_openbim | PARTIAL | Iedere workflow heeft: result JSON. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1616) |
| VIEWER-V5-0591 | viewer_openbim | PARTIAL | Minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1622) |
| VIEWER-V5-0592 | viewer_openbim | PARTIAL | Plus fresh: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1644) |
| VIEWER-V5-0593 | viewer_openbim | PARTIAL | Plus fresh: Windows one-folder; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1646) |
| VIEWER-V5-0594 | viewer_openbim | PARTIAL | Plus fresh: portable; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1647) |
| VIEWER-V5-0595 | viewer_openbim | PARTIAL | Plus fresh: packaged UI smoke; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1648) |
| VIEWER-V5-0596 | viewer_openbim | PARTIAL | Plus fresh: screenshots 100/125/150/200%; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1649) |
| VIEWER-V5-0597 | viewer_openbim | PARTIAL | Plus fresh: packaged drawing/PDF/print smoke. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1650) |
| VIEWER-V5-0598 | viewer_openbim | PARTIAL | Nadat fase 1 en 2 technisch klaar zijn: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1660) |
| VIEWER-V5-0599 | viewer_openbim | PARTIAL | > bewijs dat alle bindende requirements uit de eerdere prompts, de laatste gap-analyse en de laatste V5.1 UI samen één consistent product vormen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1662) |
| VIEWER-V5-0600 | viewer_openbim | PARTIAL | Geen “we hebben al een groene workflow van vorige week”. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1664) |
| VIEWER-V5-0601 | viewer_openbim | PARTIAL | Nieuwe scope = nieuwe acceptance. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1666) |
| VIEWER-V5-0602 | viewer_openbim | PARTIAL | Maak: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1672) |
| VIEWER-V5-0603 | viewer_openbim | PARTIAL | Bronnen: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1679) |
| VIEWER-V5-0604 | viewer_openbim | PARTIAL | Per requirement: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1691) |
| VIEWER-V5-0605 | viewer_openbim | PARTIAL | Iedere actieve requirement moet eindigen met: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1711) |
| VIEWER-V5-0606 | viewer_openbim | PARTIAL | of een expliciet door de gebruiker geaccepteerde uitzondering. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1717) |
| VIEWER-V5-0607 | viewer_openbim | PARTIAL | Maak een automatische inventory van: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1723) |
| VIEWER-V5-0608 | viewer_openbim | PARTIAL | Maak een automatische inventory van: UI controls; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1725) |
| VIEWER-V5-0609 | viewer_openbim | PARTIAL | Maak een automatische inventory van: commands; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1726) |
| VIEWER-V5-0610 | viewer_openbim | PARTIAL | Maak een automatische inventory van: actions; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1727) |
| VIEWER-V5-0611 | viewer_openbim | PARTIAL | Maak een automatische inventory van: workspaces; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1728) |
| VIEWER-V5-0612 | viewer_openbim | PARTIAL | Maak een automatische inventory van: export formats; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1729) |
| VIEWER-V5-0613 | viewer_openbim | PARTIAL | Maak een automatische inventory van: import formats; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1730) |
| VIEWER-V5-0614 | viewer_openbim | PARTIAL | Maak een automatische inventory van: Viewer tools; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1731) |
| VIEWER-V5-0615 | viewer_openbim | PARTIAL | Maak een automatische inventory van: nesting modes; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1732) |
| VIEWER-V5-0616 | viewer_openbim | PARTIAL | Maak een automatische inventory van: machine routes; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1733) |
| VIEWER-V5-0617 | viewer_openbim | PARTIAL | Maak een automatische inventory van: Drawing/PDF actions; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1734) |
| VIEWER-V5-0618 | viewer_openbim | PARTIAL | Maak een automatische inventory van: print scopes; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1735) |
| VIEWER-V5-0619 | viewer_openbim | PARTIAL | Maak een automatische inventory van: settings; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1736) |
| VIEWER-V5-0620 | viewer_openbim | PARTIAL | Maak een automatische inventory van: safety gates. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1737) |
| VIEWER-V5-0621 | viewer_openbim | PARTIAL | Controleer: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1739) |
| VIEWER-V5-0622 | viewer_openbim | PARTIAL | Controleer: unreachable code; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1741) |
| VIEWER-V5-0623 | viewer_openbim | PARTIAL | Controleer: duplicate authorities; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1742) |
| VIEWER-V5-0624 | viewer_openbim | PARTIAL | Controleer: legacy UI entrypoints; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1743) |
| VIEWER-V5-0625 | viewer_openbim | PARTIAL | Controleer: unreferenced production actions; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1744) |
| VIEWER-V5-0626 | viewer_openbim | PARTIAL | Controleer: dead menus; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1745) |
| VIEWER-V5-0627 | viewer_openbim | PARTIAL | Controleer: dead hotkeys; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1746) |
| VIEWER-V5-0628 | viewer_openbim | PARTIAL | Controleer: dead buttons. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1747) |
| VIEWER-V5-0629 | viewer_openbim | PARTIAL | Doel: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1749) |
| VIEWER-V5-0630 | viewer_openbim | PARTIAL | Minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1761) |
| VIEWER-V5-0631 | viewer_openbim | PARTIAL | Minimaal: corrupt IFC; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1763) |
| VIEWER-V5-0632 | viewer_openbim | PARTIAL | Minimaal: corrupt STEP; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1764) |
| VIEWER-V5-0633 | viewer_openbim | PARTIAL | Minimaal: corrupt NC1; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1765) |
| VIEWER-V5-0634 | viewer_openbim | PARTIAL | Minimaal: corrupt project; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1766) |
| VIEWER-V5-0635 | viewer_openbim | PARTIAL | Minimaal: stale cache; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1767) |
| VIEWER-V5-0636 | viewer_openbim | PARTIAL | Minimaal: corrupt cache entry; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1768) |
| VIEWER-V5-0637 | viewer_openbim | PARTIAL | Minimaal: worker crash; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1769) |
| VIEWER-V5-0638 | viewer_openbim | PARTIAL | Minimaal: worker timeout; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1770) |
| VIEWER-V5-0639 | viewer_openbim | PARTIAL | Minimaal: user cancel during import; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1771) |
| VIEWER-V5-0640 | viewer_openbim | PARTIAL | Minimaal: user cancel during exact refinement; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1772) |
| VIEWER-V5-0641 | viewer_openbim | PARTIAL | Minimaal: source removed; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1773) |
| VIEWER-V5-0642 | viewer_openbim | PARTIAL | Minimaal: source changed; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1774) |
| VIEWER-V5-0643 | viewer_openbim | PARTIAL | Minimaal: selected entity disappears on revision; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1775) |
| VIEWER-V5-0644 | viewer_openbim | PARTIAL | Minimaal: incompatible machine override; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1776) |
| VIEWER-V5-0645 | viewer_openbim | PARTIAL | Minimaal: no eligible machine; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1777) |
| VIEWER-V5-0646 | viewer_openbim | PARTIAL | Minimaal: plate part does not fit stock; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1778) |
| VIEWER-V5-0647 | viewer_openbim | PARTIAL | Minimaal: profile part does not fit stock; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1779) |
| VIEWER-V5-0648 | viewer_openbim | PARTIAL | Minimaal: optimizer cancellation; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1780) |
| VIEWER-V5-0649 | viewer_openbim | PARTIAL | Minimaal: PDF output unwritable; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1781) |
| VIEWER-V5-0650 | viewer_openbim | PARTIAL | Minimaal: printer unavailable; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1782) |
| VIEWER-V5-0651 | viewer_openbim | PARTIAL | Minimaal: drawing linter fail; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1783) |
| VIEWER-V5-0652 | viewer_openbim | PARTIAL | Minimaal: BOM discrepancy; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1784) |
| VIEWER-V5-0653 | viewer_openbim | PARTIAL | Minimaal: invalid quality measurement; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1785) |
| VIEWER-V5-0654 | viewer_openbim | PARTIAL | Minimaal: open NCR; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1786) |
| VIEWER-V5-0655 | viewer_openbim | PARTIAL | Minimaal: missing external machine proof; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1787) |
| VIEWER-V5-0656 | viewer_openbim | PARTIAL | Minimaal: stale release hash. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1788) |
| VIEWER-V5-0657 | viewer_openbim | PARTIAL | Fail closed. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1790) |
| VIEWER-V5-0658 | viewer_openbim | PARTIAL | Minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1796) |
| VIEWER-V5-0659 | viewer_openbim | PARTIAL | Plus waar praktisch: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1810) |
| VIEWER-V5-0660 | viewer_openbim | PARTIAL | Plus waar praktisch: repeated project open/close; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1812) |
| VIEWER-V5-0661 | viewer_openbim | PARTIAL | Plus waar praktisch: warm-cache reopen; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1813) |
| VIEWER-V5-0662 | viewer_openbim | PARTIAL | Plus waar praktisch: worker crash/restart injection; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1814) |
| VIEWER-V5-0663 | viewer_openbim | PARTIAL | Plus waar praktisch: plate/profile optimization repeated; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1815) |
| VIEWER-V5-0664 | viewer_openbim | PARTIAL | Plus waar praktisch: PDF generation batch. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1816) |
| VIEWER-V5-0665 | viewer_openbim | PARTIAL | Meet memory growth en handles/processes. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1818) |
| VIEWER-V5-0666 | viewer_openbim | PARTIAL | Tests moeten worden uitgevoerd op een echte Windows x64 packaged runtime. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1824) |
| VIEWER-V5-0667 | viewer_openbim | PARTIAL | Headless tests zijn aanvullend, niet equivalent. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1826) |
| VIEWER-V5-0668 | viewer_openbim | PARTIAL | Acceptance op: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1828) |
| VIEWER-V5-0669 | viewer_openbim | PARTIAL | Bevat: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1832) |
| VIEWER-V5-0670 | viewer_openbim | PARTIAL | Bevat: echte GUI EXE; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1834) |
| VIEWER-V5-0671 | viewer_openbim | PARTIAL | Bevat: echte CLI EXE; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1835) |
| VIEWER-V5-0672 | viewer_openbim | PARTIAL | Bevat: volledige runtime dependencies; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1836) |
| VIEWER-V5-0673 | viewer_openbim | PARTIAL | Bevat: worker EXE/service dependencies; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1837) |
| VIEWER-V5-0674 | viewer_openbim | PARTIAL | Bevat: Qt/VTK plugins; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1838) |
| VIEWER-V5-0675 | viewer_openbim | PARTIAL | Bevat: geen developer Python vereist. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1839) |
| VIEWER-V5-0676 | viewer_openbim | PARTIAL | Fresh ZIP van exact dezelfde source SHA. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1843) |
| VIEWER-V5-0677 | viewer_openbim | PARTIAL | Na extract: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1845) |
| VIEWER-V5-0678 | viewer_openbim | PARTIAL | Na extract: launch GUI; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1847) |
| VIEWER-V5-0679 | viewer_openbim | PARTIAL | Na extract: launch CLI; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1848) |
| VIEWER-V5-0680 | viewer_openbim | PARTIAL | Na extract: load fixture; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1849) |
| VIEWER-V5-0681 | viewer_openbim | PARTIAL | Na extract: Viewer; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1850) |
| VIEWER-V5-0682 | viewer_openbim | PARTIAL | Na extract: selection; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1851) |
| VIEWER-V5-0683 | viewer_openbim | PARTIAL | Na extract: save/reopen; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1852) |
| VIEWER-V5-0684 | viewer_openbim | PARTIAL | Na extract: drawing/PDF; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1853) |
| VIEWER-V5-0685 | viewer_openbim | PARTIAL | Na extract: BOM; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1854) |
| VIEWER-V5-0686 | viewer_openbim | PARTIAL | Na extract: optimizer smoke. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1855) |
| VIEWER-V5-0687 | viewer_openbim | PARTIAL | install; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1859) |
| VIEWER-V5-0688 | viewer_openbim | PARTIAL | first launch; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1860) |
| VIEWER-V5-0689 | viewer_openbim | PARTIAL | normal user path; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1861) |
| VIEWER-V5-0690 | viewer_openbim | PARTIAL | file/runtime access; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1862) |
| VIEWER-V5-0691 | viewer_openbim | PARTIAL | worker launch; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1863) |
| VIEWER-V5-0692 | viewer_openbim | PARTIAL | save/export; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1864) |
| VIEWER-V5-0693 | viewer_openbim | PARTIAL | uninstall; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1865) |
| VIEWER-V5-0694 | viewer_openbim | PARTIAL | cleanup. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1866) |
| VIEWER-V5-0695 | viewer_openbim | PARTIAL | Geen “PyInstaller exe bestaat” als voldoende bewijs. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1868) |
| VIEWER-V5-0696 | viewer_openbim | PARTIAL | Final releasepakket minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1874) |
| VIEWER-V5-0697 | viewer_openbim | PARTIAL | `BUILD_INFO.json`: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1890) |
| VIEWER-V5-0698 | viewer_openbim | PARTIAL | Alle artifacts moeten naar exact dezelfde source SHA verwijzen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1908) |
| VIEWER-V5-0699 | viewer_openbim | PARTIAL | Vermijd de fout waarbij acceptance evidence zelf de source tree wijzigt en daardoor exact-SHA proof ondermijnt. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1914) |
| VIEWER-V5-0700 | viewer_openbim | PARTIAL | Gebruik: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1916) |
| VIEWER-V5-0701 | viewer_openbim | PARTIAL | Gebruik: CI artifacts; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1918) |
| VIEWER-V5-0702 | viewer_openbim | PARTIAL | Gebruik: ignored validation output; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1919) |
| VIEWER-V5-0703 | viewer_openbim | PARTIAL | Gebruik: out-of-tree evidence directory; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1920) |
| VIEWER-V5-0704 | viewer_openbim | PARTIAL | Gebruik: of commit evidence eerst en bouw daarna vanaf de nieuwe exact-evidence SHA. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1921) |
| VIEWER-V5-0705 | viewer_openbim | PARTIAL | Maar één final manifest moet ondubbelzinnig zijn. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1923) |
| VIEWER-V5-0706 | viewer_openbim | PARTIAL | Software acceptance kan PASS zijn. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1929) |
| VIEWER-V5-0707 | viewer_openbim | PARTIAL | Werkelijke machine-transfer blijft een aparte externe grens. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1931) |
| VIEWER-V5-0708 | viewer_openbim | PARTIAL | Behoud: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1933) |
| VIEWER-V5-0709 | viewer_openbim | PARTIAL | tot er: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1939) |
| VIEWER-V5-0710 | viewer_openbim | PARTIAL | tot er: machinefabrikant/postprocessor evidence; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1941) |
| VIEWER-V5-0711 | viewer_openbim | PARTIAL | tot er: fysieke dry-run; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1942) |
| VIEWER-V5-0712 | viewer_openbim | PARTIAL | tot er: controller acceptance; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1943) |
| VIEWER-V5-0713 | viewer_openbim | PARTIAL | tot er: operationele kwalificatie; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1944) |
| VIEWER-V5-0714 | viewer_openbim | PARTIAL | tot er: release approval | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1945) |
| VIEWER-V5-0715 | viewer_openbim | PARTIAL | bestaat. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1947) |
| VIEWER-V5-0716 | viewer_openbim | PARTIAL | Nooit machine-transfer groen maken om total acceptance “100%” te laten lijken. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1949) |
| VIEWER-V5-0717 | viewer_openbim | PARTIAL | Gebruik: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1951) |
| VIEWER-V5-0718 | viewer_openbim | PARTIAL | `BLOCKED_EXTERNAL_EVIDENCE` | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1953) |
| VIEWER-V5-0719 | viewer_openbim | PARTIAL | waar dat werkelijk de enige resterende machinegrens is. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1955) |
| VIEWER-V5-0720 | viewer_openbim | PARTIAL | Maak minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L1961) |
| VIEWER-V5-0721 | viewer_openbim | PARTIAL | De finale scope is pas PASS wanneer: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2000) |
| VIEWER-V5-0722 | viewer_openbim | PARTIAL | uitgezonderd expliciet toegestane: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2008) |
| VIEWER-V5-0723 | viewer_openbim | PARTIAL | voor werkelijke machine kwalificatie/transfer. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2014) |
| VIEWER-V5-0724 | viewer_openbim | PARTIAL | Verder verplicht: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2016) |
| VIEWER-V5-0725 | viewer_openbim | PARTIAL | Geen final PASS op basis van alleen unit tests. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2045) |
| VIEWER-V5-0726 | viewer_openbim | PARTIAL | Commit regelmatig per coherent werkpakket. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2051) |
| VIEWER-V5-0727 | viewer_openbim | PARTIAL | Voorbeeld binnen fase 1: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2053) |
| VIEWER-V5-0728 | viewer_openbim | PARTIAL | Fase 2: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2064) |
| VIEWER-V5-0729 | viewer_openbim | PARTIAL | Fase 3: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2076) |
| VIEWER-V5-0730 | viewer_openbim | PARTIAL | Geen giant commit met alles als dat root cause debugging onmogelijk maakt. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2085) |
| VIEWER-V5-0731 | viewer_openbim | PARTIAL | Voor iedere wijziging: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2091) |
| VIEWER-V5-0732 | viewer_openbim | PARTIAL | Voor iedere wijziging: 1. reproduceren; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2093) |
| VIEWER-V5-0733 | viewer_openbim | PARTIAL | Voor iedere wijziging: 2. baseline test vastleggen; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2094) |
| VIEWER-V5-0734 | viewer_openbim | PARTIAL | Voor iedere wijziging: 3. wijzigen; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2095) |
| VIEWER-V5-0735 | viewer_openbim | PARTIAL | Voor iedere wijziging: 4. target test; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2096) |
| VIEWER-V5-0736 | viewer_openbim | PARTIAL | Voor iedere wijziging: 5. relevante subsystem regressie; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2097) |
| VIEWER-V5-0737 | viewer_openbim | PARTIAL | Voor iedere wijziging: 6. E2E; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2098) |
| VIEWER-V5-0738 | viewer_openbim | PARTIAL | Voor iedere wijziging: 7. checklist bijwerken. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2099) |
| VIEWER-V5-0739 | viewer_openbim | PARTIAL | Bij Viewer performance-optimalisaties altijd ook correctness testen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2101) |
| VIEWER-V5-0740 | viewer_openbim | PARTIAL | Bij UI-wijzigingen geen bestaande service verwijderen omdat een knop elders staat. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2103) |
| VIEWER-V5-0741 | viewer_openbim | PARTIAL | Bij data model wijzigingen altijd migration/roundtrip testen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2105) |
| VIEWER-V5-0742 | viewer_openbim | PARTIAL | Wanneer de gebruiker zegt: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2111) |
| VIEWER-V5-0743 | viewer_openbim | PARTIAL | Wanneer de gebruiker zegt: “Ga verder” | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2113) |
| VIEWER-V5-0744 | viewer_openbim | PARTIAL | Wanneer de gebruiker zegt: “Bouw verder” | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2114) |
| VIEWER-V5-0745 | viewer_openbim | PARTIAL | Wanneer de gebruiker zegt: “Volgende fase” | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2115) |
| VIEWER-V5-0746 | viewer_openbim | PARTIAL | Wanneer de gebruiker zegt: “Test verder” | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2116) |
| VIEWER-V5-0747 | viewer_openbim | PARTIAL | Wanneer de gebruiker zegt: “Herstel verder” | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2117) |
| VIEWER-V5-0748 | viewer_openbim | PARTIAL | doe dan automatisch: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2119) |
| VIEWER-V5-0749 | viewer_openbim | PARTIAL | Niet opnieuw vragen wat de bedoeling is als de checklist het ondubbelzinnig bepaalt. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2135) |
| VIEWER-V5-0750 | viewer_openbim | PARTIAL | Rapporteer compact maar technisch: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2141) |
| VIEWER-V5-0751 | viewer_openbim | PARTIAL | Geen marketingtaal. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2159) |
| VIEWER-V5-0752 | viewer_openbim | PARTIAL | Geen “100% klaar” zolang een vereiste acceptance case geen PASS is. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2161) |
| VIEWER-V5-0753 | viewer_openbim | PARTIAL | Voer NU eerst uit: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2167) |
| VIEWER-V5-0754 | viewer_openbim | PARTIAL | fetch current canonical branch; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2171) |
| VIEWER-V5-0755 | viewer_openbim | PARTIAL | actuele HEAD; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2172) |
| VIEWER-V5-0756 | viewer_openbim | PARTIAL | diff t.o.v. audit SHA `dc4e3e2...`; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2173) |
| VIEWER-V5-0757 | viewer_openbim | PARTIAL | recente workflows; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2174) |
| VIEWER-V5-0758 | viewer_openbim | PARTIAL | actieve release artifacts; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2175) |
| VIEWER-V5-0759 | viewer_openbim | PARTIAL | open/stale overlapping branches/PR’s alleen ter context, niet als alternatieve truth. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2176) |
| VIEWER-V5-0760 | viewer_openbim | PARTIAL | Maak voorlopige master matrix uit: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2180) |
| VIEWER-V5-0761 | viewer_openbim | PARTIAL | Maak voorlopige master matrix uit: huidige repo; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2182) |
| VIEWER-V5-0762 | viewer_openbim | PARTIAL | Maak voorlopige master matrix uit: eerdere prompts; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2183) |
| VIEWER-V5-0763 | viewer_openbim | PARTIAL | Maak voorlopige master matrix uit: nieuwste V5/V5.1; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2184) |
| VIEWER-V5-0764 | viewer_openbim | PARTIAL | Maak voorlopige master matrix uit: huidige gap-analyse. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2185) |
| VIEWER-V5-0765 | viewer_openbim | PARTIAL | Meet bestaande packaged Viewer vóór optimalisaties. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2189) |
| VIEWER-V5-0766 | viewer_openbim | PARTIAL | Inspecteer: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2193) |
| VIEWER-V5-0767 | viewer_openbim | PARTIAL | Inspecteer: project loader; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2195) |
| VIEWER-V5-0768 | viewer_openbim | PARTIAL | Inspecteer: exact geometry worker; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2196) |
| VIEWER-V5-0769 | viewer_openbim | PARTIAL | Inspecteer: isolated IFC provider; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2197) |
| VIEWER-V5-0770 | viewer_openbim | PARTIAL | Inspecteer: cache; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2198) |
| VIEWER-V5-0771 | viewer_openbim | PARTIAL | Inspecteer: frame scheduler; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2199) |
| VIEWER-V5-0772 | viewer_openbim | PARTIAL | Inspecteer: adaptive rendering; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2200) |
| VIEWER-V5-0773 | viewer_openbim | PARTIAL | Inspecteer: picking; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2201) |
| VIEWER-V5-0774 | viewer_openbim | PARTIAL | Inspecteer: scene patch path. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2202) |
| VIEWER-V5-0775 | viewer_openbim | PARTIAL | Maak alle Phase 1 rows met: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2206) |
| VIEWER-V5-0776 | viewer_openbim | PARTIAL | Begin daarna direct met de **eerste aantoonbare P0 bottleneck uit Fase 1**. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2218) |
| VIEWER-V5-0777 | viewer_openbim | PARTIAL | Niet eerst V5-cosmetica implementeren. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2220) |
| VIEWER-V5-0778 | viewer_openbim | PARTIAL | Het eindproduct moet niet alleen “meer functies” hebben. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2226) |
| VIEWER-V5-0779 | viewer_openbim | PARTIAL | Het moet: | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2228) |
| VIEWER-V5-0780 | viewer_openbim | PARTIAL | Het moet: sneller starten; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2230) |
| VIEWER-V5-0781 | viewer_openbim | PARTIAL | Het moet: eerder bruikbaar zijn; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2231) |
| VIEWER-V5-0782 | viewer_openbim | PARTIAL | Het moet: grote modellen vloeiender bewegen; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2232) |
| VIEWER-V5-0783 | viewer_openbim | PARTIAL | Het moet: natuurlijker renderen; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2233) |
| VIEWER-V5-0784 | viewer_openbim | PARTIAL | Het moet: betrouwbaar complete objecten selecteren; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2234) |
| VIEWER-V5-0785 | viewer_openbim | PARTIAL | Het moet: aantoonbaar Trimble-observable gedrag benaderen; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2235) |
| VIEWER-V5-0786 | viewer_openbim | PARTIAL | Het moet: eenvoudiger ogen; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2236) |
| VIEWER-V5-0787 | viewer_openbim | PARTIAL | Het moet: alle benodigde functies logisch ontsluiten; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2237) |
| VIEWER-V5-0788 | viewer_openbim | PARTIAL | Het moet: BOM als productiehart gebruiken; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2238) |
| VIEWER-V5-0789 | viewer_openbim | PARTIAL | Het moet: automatisch en handmatig machine-routing ondersteunen; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2239) |
| VIEWER-V5-0790 | viewer_openbim | PARTIAL | Het moet: Profile én Plate Nesting correct integreren; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2240) |
| VIEWER-V5-0791 | viewer_openbim | PARTIAL | Het moet: echte vector productietekeningen/PDF maken; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2241) |
| VIEWER-V5-0792 | viewer_openbim | PARTIAL | Het moet: vanuit relevante schermen eenvoudig afdrukken/exporteren; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2242) |
| VIEWER-V5-0793 | viewer_openbim | PARTIAL | Het moet: alle eerdere actieve requirements traceerbaar afdekken; | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2243) |
| VIEWER-V5-0794 | viewer_openbim | PARTIAL | Het moet: en vanuit exact één source SHA reproduceerbaar als Windows one-folder, portable en installer worden bewezen. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2244) |
| VIEWER-V5-0795 | viewer_openbim | PARTIAL | **Evidence is de productstatus.** | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2246) |
| VIEWER-V5-0796 | viewer_openbim | PARTIAL | Begin met Fase 1. | requirements/sources/CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md (L2248) |
| VIEWER-PERF-0001 | ui_performance_reporting | PARTIAL | Werk verder in de bestaande CWS Convertor repository. Bouw geen tweede Viewer en geen benchmark-demo naast de productapp. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L6) |
| VIEWER-PERF-0002 | ui_performance_reporting | PARTIAL | Doel: > Maak de bestaande CWS Viewer aantoonbaar sneller bij cold load, warm reopen en same-session gebruik; houd orbit/pan/zoom vloeiend terwijl geometry op de achtergrond binnenkomt; meet de echte packaged Windows-runtime; vergelijk waar mogelijk op dezelfde pc/model met Trimble; voer pas daarna rendering-microtuning uit. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L8) |
| VIEWER-PERF-0003 | ui_performance_reporting | PARTIAL | Behoud bestaande sterke foundations: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L11) |
| VIEWER-PERF-0004 | ui_performance_reporting | PARTIAL | Behoud bestaande sterke foundations: progressive/proxy-first Viewer; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L12) |
| VIEWER-PERF-0005 | ui_performance_reporting | PARTIAL | Behoud bestaande sterke foundations: één permanente Viewer/context; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L13) |
| VIEWER-PERF-0006 | ui_performance_reporting | PARTIAL | Behoud bestaande sterke foundations: shared geometry/instancing; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L14) |
| VIEWER-PERF-0007 | ui_performance_reporting | PARTIAL | Behoud bestaande sterke foundations: 60 Hz input coalescing; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L15) |
| VIEWER-PERF-0008 | ui_performance_reporting | PARTIAL | Behoud bestaande sterke foundations: upright orbit/pivot/zoom; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L16) |
| VIEWER-PERF-0009 | ui_performance_reporting | PARTIAL | Behoud bestaande sterke foundations: spatial picking; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L17) |
| VIEWER-PERF-0010 | ui_performance_reporting | PARTIAL | Behoud bestaande sterke foundations: whole-object selection; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L18) |
| VIEWER-PERF-0011 | ui_performance_reporting | PARTIAL | Behoud bestaande sterke foundations: crash-isolated IFC workerfoundation; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L19) |
| VIEWER-PERF-0012 | ui_performance_reporting | PARTIAL | Behoud bestaande sterke foundations: ViewerPerformanceEvidence; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L20) |
| VIEWER-PERF-0013 | ui_performance_reporting | PARTIAL | Behoud bestaande sterke foundations: canonical Project/Geometry/Selection truths. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L21) |
| VIEWER-PERF-0014 | ui_performance_reporting | PARTIAL | Auditbaseline: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L24) |
| VIEWER-PERF-0015 | ui_performance_reporting | PARTIAL | Auditbaseline: repo: `CoenWessselink/Convertor` | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L25) |
| VIEWER-PERF-0016 | ui_performance_reporting | PARTIAL | Auditbaseline: branch: `agent/cws-product-ui-reintegration-v1` | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L26) |
| VIEWER-PERF-0017 | ui_performance_reporting | PARTIAL | Auditbaseline: audit-SHA: `dc4e3e2ec2f91c40aad271d985b3fe59a44c7325` | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L27) |
| VIEWER-PERF-0018 | ui_performance_reporting | PARTIAL | Deze SHA is alleen baseline. Start met: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L29) |
| VIEWER-PERF-0019 | ui_performance_reporting | PARTIAL | Leg vast: `CURRENT_CANONICAL_BRANCH`, `CURRENT_HEAD_SHA40`, `CURRENT_VERSION`, `WORKTREE_CLEAN`. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L36) |
| VIEWER-PERF-0020 | ui_performance_reporting | PARTIAL | Als er nieuwere commits zijn: audit ze eerst en hergebruik correct uitgevoerde performancecode. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L39) |
| VIEWER-PERF-0021 | ui_performance_reporting | PARTIAL | Maak: `validation/viewer_performance_closeout/PREFLIGHT.json` `validation/viewer_performance_closeout/PREFLIGHT.md` | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L41) |
| VIEWER-PERF-0022 | ui_performance_reporting | PARTIAL | Gebruik uitsluitend: `PASS \| FAIL \| BLOCKED \| NOT_TESTED \| NOT_APPLICABLE` | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L46) |
| VIEWER-PERF-0023 | ui_performance_reporting | PARTIAL | Houd apart: `IMPLEMENTED \| INTEGRATED \| TESTED \| PACKAGED_PROVEN \| TRIMBLE_PROVEN` | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L49) |
| VIEWER-PERF-0024 | ui_performance_reporting | PARTIAL | Geen “mostly done”, “looks faster” of “smooth enough”. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L52) |
| VIEWER-PERF-0025 | ui_performance_reporting | PARTIAL | Sluit exact deze punten: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L55) |
| VIEWER-PERF-0026 | ui_performance_reporting | PARTIAL | Sluit exact deze punten: 1. IFC persistent process worker pool. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L56) |
| VIEWER-PERF-0027 | ui_performance_reporting | PARTIAL | Sluit exact deze punten: 2. echte dynamische geometry priority scheduler. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L57) |
| VIEWER-PERF-0028 | ui_performance_reporting | PARTIAL | Sluit exact deze punten: 3. MeshCache V2. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L58) |
| VIEWER-PERF-0029 | ui_performance_reporting | PARTIAL | Sluit exact deze punten: 4. per-frame VTK upload budget + backpressure. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L59) |
| VIEWER-PERF-0030 | ui_performance_reporting | PARTIAL | Sluit exact deze punten: 5. MSAA/FXAA tijdens interactie benchmarken en tunen. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L60) |
| VIEWER-PERF-0031 | ui_performance_reporting | PARTIAL | Sluit exact deze punten: 6. echte packaged performance instrumentation. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L61) |
| VIEWER-PERF-0032 | ui_performance_reporting | PARTIAL | Sluit exact deze punten: 7. cold/warm/same-session benchmark. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L62) |
| VIEWER-PERF-0033 | ui_performance_reporting | PARTIAL | Sluit exact deze punten: 8. 10-minuten real Viewer soak. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L63) |
| VIEWER-PERF-0034 | ui_performance_reporting | PARTIAL | Sluit exact deze punten: 9. same-machine Trimble comparison. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L64) |
| VIEWER-PERF-0035 | ui_performance_reporting | PARTIAL | Sluit exact deze punten: 10. daarna pas finale rendering microtuning. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L65) |
| VIEWER-PERF-0036 | ui_performance_reporting | PARTIAL | Aanvulling: maak één centrale `ViewerPerformanceGovernor`. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L67) |
| VIEWER-PERF-0037 | ui_performance_reporting | PARTIAL | Behoud: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L70) |
| VIEWER-PERF-0038 | ui_performance_reporting | PARTIAL | Behoud: ONE ViewerHost | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L71) |
| VIEWER-PERF-0039 | ui_performance_reporting | PARTIAL | Behoud: ONE SelectionAuthority | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L72) |
| VIEWER-PERF-0040 | ui_performance_reporting | PARTIAL | Behoud: ONE Project Model | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L73) |
| VIEWER-PERF-0041 | ui_performance_reporting | PARTIAL | Behoud: ONE Geometry Repository truth | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L74) |
| VIEWER-PERF-0042 | ui_performance_reporting | PARTIAL | Behoud: ONE load priority authority | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L75) |
| VIEWER-PERF-0043 | ui_performance_reporting | PARTIAL | Behoud: ONE Viewer scheduler authority | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L76) |
| VIEWER-PERF-0044 | ui_performance_reporting | PARTIAL | Behoud: ONE ViewerPerformanceGovernor | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L77) |
| VIEWER-PERF-0045 | ui_performance_reporting | PARTIAL | Behoud: ONE MeshCache authority | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L78) |
| VIEWER-PERF-0046 | ui_performance_reporting | PARTIAL | Geen tweede Viewer, geen alternate performance-app, geen benchmarkroute die andere productcode gebruikt. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L80) |
| VIEWER-PERF-0047 | ui_performance_reporting | PARTIAL | Breid `ViewerPerformanceEvidence` uit waar nodig. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L83) |
| VIEWER-PERF-0048 | ui_performance_reporting | PARTIAL | shell_visible_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L86) |
| VIEWER-PERF-0049 | ui_performance_reporting | PARTIAL | first_tree_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L87) |
| VIEWER-PERF-0050 | ui_performance_reporting | PARTIAL | first_pixels_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L88) |
| VIEWER-PERF-0051 | ui_performance_reporting | PARTIAL | proxy_scene_ready_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L89) |
| VIEWER-PERF-0052 | ui_performance_reporting | PARTIAL | first_usable_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L90) |
| VIEWER-PERF-0053 | ui_performance_reporting | PARTIAL | exact_25_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L91) |
| VIEWER-PERF-0054 | ui_performance_reporting | PARTIAL | exact_50_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L92) |
| VIEWER-PERF-0055 | ui_performance_reporting | PARTIAL | exact_75_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L93) |
| VIEWER-PERF-0056 | ui_performance_reporting | PARTIAL | exact_100_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L94) |
| VIEWER-PERF-0057 | ui_performance_reporting | PARTIAL | geometry_ready_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L95) |
| VIEWER-PERF-0058 | ui_performance_reporting | PARTIAL | frame_p50_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L98) |
| VIEWER-PERF-0059 | ui_performance_reporting | PARTIAL | frame_p95_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L99) |
| VIEWER-PERF-0060 | ui_performance_reporting | PARTIAL | frame_p99_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L100) |
| VIEWER-PERF-0061 | ui_performance_reporting | PARTIAL | stall_33ms_count | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L101) |
| VIEWER-PERF-0062 | ui_performance_reporting | PARTIAL | stall_50ms_count | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L102) |
| VIEWER-PERF-0063 | ui_performance_reporting | PARTIAL | stall_100ms_count | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L103) |
| VIEWER-PERF-0064 | ui_performance_reporting | PARTIAL | input_to_render_p50_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L106) |
| VIEWER-PERF-0065 | ui_performance_reporting | PARTIAL | input_to_render_p95_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L107) |
| VIEWER-PERF-0066 | ui_performance_reporting | PARTIAL | orbit_latency_p95_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L108) |
| VIEWER-PERF-0067 | ui_performance_reporting | PARTIAL | pan_latency_p95_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L109) |
| VIEWER-PERF-0068 | ui_performance_reporting | PARTIAL | zoom_latency_p95_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L110) |
| VIEWER-PERF-0069 | ui_performance_reporting | PARTIAL | fit_latency_p95_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L111) |
| VIEWER-PERF-0070 | ui_performance_reporting | PARTIAL | pick_p50_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L114) |
| VIEWER-PERF-0071 | ui_performance_reporting | PARTIAL | pick_p95_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L115) |
| VIEWER-PERF-0072 | ui_performance_reporting | PARTIAL | selection_p95_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L116) |
| VIEWER-PERF-0073 | ui_performance_reporting | PARTIAL | whole_object_highlight_p95_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L117) |
| VIEWER-PERF-0074 | ui_performance_reporting | PARTIAL | wrong_instance_picks | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L118) |
| VIEWER-PERF-0075 | ui_performance_reporting | PARTIAL | hidden_object_false_picks | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L119) |
| VIEWER-PERF-0076 | ui_performance_reporting | PARTIAL | geometry_queue_depth_peak | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L122) |
| VIEWER-PERF-0077 | ui_performance_reporting | PARTIAL | upload_queue_depth_peak | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L123) |
| VIEWER-PERF-0078 | ui_performance_reporting | PARTIAL | upload_frame_p50_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L124) |
| VIEWER-PERF-0079 | ui_performance_reporting | PARTIAL | upload_frame_p95_ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L125) |
| VIEWER-PERF-0080 | ui_performance_reporting | PARTIAL | cache_memory_hits | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L126) |
| VIEWER-PERF-0081 | ui_performance_reporting | PARTIAL | cache_disk_hits | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L127) |
| VIEWER-PERF-0082 | ui_performance_reporting | PARTIAL | cache_misses | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L128) |
| VIEWER-PERF-0083 | ui_performance_reporting | PARTIAL | cache_corruptions | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L129) |
| VIEWER-PERF-0084 | ui_performance_reporting | PARTIAL | worker_count | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L130) |
| VIEWER-PERF-0085 | ui_performance_reporting | PARTIAL | worker_utilization | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L131) |
| VIEWER-PERF-0086 | ui_performance_reporting | PARTIAL | worker_restart_count | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L132) |
| VIEWER-PERF-0087 | ui_performance_reporting | PARTIAL | worker_crash_count | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L133) |
| VIEWER-PERF-0088 | ui_performance_reporting | PARTIAL | rss_start_mb / rss_peak_mb / rss_end_mb / rss_drift_percent | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L136) |
| VIEWER-PERF-0089 | ui_performance_reporting | PARTIAL | vram_start_mb / vram_peak_mb / vram_end_mb | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L137) |
| VIEWER-PERF-0090 | ui_performance_reporting | PARTIAL | thread_count_start/end | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L138) |
| VIEWER-PERF-0091 | ui_performance_reporting | PARTIAL | process_count_start/end | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L139) |
| VIEWER-PERF-0092 | ui_performance_reporting | PARTIAL | actor_count_start/end | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L140) |
| VIEWER-PERF-0093 | ui_performance_reporting | PARTIAL | Onmeetbaar = null + NOT_TESTED. Niets verzinnen. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L142) |
| VIEWER-PERF-0094 | ui_performance_reporting | PARTIAL | medium first usable preferred ≤ 2 s | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L146) |
| VIEWER-PERF-0095 | ui_performance_reporting | PARTIAL | large first usable preferred ≤ 3 s | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L147) |
| VIEWER-PERF-0096 | ui_performance_reporting | PARTIAL | large hard target ≤ 5 s | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L148) |
| VIEWER-PERF-0097 | ui_performance_reporting | PARTIAL | warm reopen preferred ≤ 1–2 s waar hardware/model/cache dit toelaat | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L149) |
| VIEWER-PERF-0098 | ui_performance_reporting | PARTIAL | 60 Hz: frame p50 ≤ 16.7 ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L152) |
| VIEWER-PERF-0099 | ui_performance_reporting | PARTIAL | frame p95 ≤ 25 ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L153) |
| VIEWER-PERF-0100 | ui_performance_reporting | PARTIAL | heavy large scene p95 ≤ 33 ms where feasible | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L154) |
| VIEWER-PERF-0101 | ui_performance_reporting | PARTIAL | input→render p95 ≤ 35 ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L155) |
| VIEWER-PERF-0102 | ui_performance_reporting | PARTIAL | medium p95 ≤ 80 ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L158) |
| VIEWER-PERF-0103 | ui_performance_reporting | PARTIAL | large p95 ≤ 150 ms | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L159) |
| VIEWER-PERF-0104 | ui_performance_reporting | PARTIAL | wrong_instance_picks = 0 | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L160) |
| VIEWER-PERF-0105 | ui_performance_reporting | PARTIAL | unintended stalls >100 ms = 0 na first usable bij normale interactie | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L163) |
| VIEWER-PERF-0106 | ui_performance_reporting | PARTIAL | 10-min real Viewer RSS drift <10% | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L164) |
| VIEWER-PERF-0107 | ui_performance_reporting | PARTIAL | Op dezelfde machine/model: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L167) |
| VIEWER-PERF-0108 | ui_performance_reporting | PARTIAL | Op dezelfde machine/model: CWS first usable ≤ Trimble ×1.10 | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L168) |
| VIEWER-PERF-0109 | ui_performance_reporting | PARTIAL | Op dezelfde machine/model: CWS navigation p95 ≤ Trimble ×1.10 | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L169) |
| VIEWER-PERF-0110 | ui_performance_reporting | PARTIAL | Op dezelfde machine/model: CWS pick p95 ≤ Trimble ×1.10 | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L170) |
| VIEWER-PERF-0111 | ui_performance_reporting | PARTIAL | Geen echte Trimbledata = NOT_TESTED, nooit PASS. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L172) |
| VIEWER-PERF-0112 | ui_performance_reporting | PARTIAL | Bouw bovenop de bestaande crash-isolated workerfoundation een bounded persistent pool: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L177) |
| VIEWER-PERF-0113 | ui_performance_reporting | PARTIAL | Eisen: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L187) |
| VIEWER-PERF-0114 | ui_performance_reporting | PARTIAL | Eisen: iedere worker eigen IFC/OCP context; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L188) |
| VIEWER-PERF-0115 | ui_performance_reporting | PARTIAL | Eisen: geen native state sharing; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L189) |
| VIEWER-PERF-0116 | ui_performance_reporting | PARTIAL | Eisen: persistent reuse; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L190) |
| VIEWER-PERF-0117 | ui_performance_reporting | PARTIAL | Eisen: crash vervangt alleen de defecte worker; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L191) |
| VIEWER-PERF-0118 | ui_performance_reporting | PARTIAL | Eisen: cancellation/generation safe; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L192) |
| VIEWER-PERF-0119 | ui_performance_reporting | PARTIAL | Eisen: timeout; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L193) |
| VIEWER-PERF-0120 | ui_performance_reporting | PARTIAL | Eisen: clean shutdown; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L194) |
| VIEWER-PERF-0121 | ui_performance_reporting | PARTIAL | Eisen: frozen Windows worker support; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L195) |
| VIEWER-PERF-0122 | ui_performance_reporting | PARTIAL | Eisen: geen zombie processes. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L196) |
| VIEWER-PERF-0123 | ui_performance_reporting | PARTIAL | Benchmark worker counts 1/2/3/4/6 en meet first usable, exact100, CPU, worker RSS, total RSS, crash/restart. Kies beste default op throughput versus RAM, niet hoogste getal. Voeg benchmarkoverride `CWS_VIEWER_IFC_WORKERS` toe. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L198) |
| VIEWER-PERF-0124 | ui_performance_reporting | PARTIAL | Audit provider/thread/process safety. Indien OCP/CadQuery niet thread-safe genoeg is, gebruik processen of houd uitsluitend de unsafe route serial. Documenteer in `NON_IFC_PARALLELISM_REPORT.md`. Geen unsafe threading voor mooie cijfers. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L201) |
| VIEWER-PERF-0125 | ui_performance_reporting | PARTIAL | Vervang FIFO + selected-only door één dynamische authority. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L204) |
| VIEWER-PERF-0126 | ui_performance_reporting | PARTIAL | Signalen minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L206) |
| VIEWER-PERF-0127 | ui_performance_reporting | PARTIAL | Signalen minimaal: 1. selected | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L207) |
| VIEWER-PERF-0128 | ui_performance_reporting | PARTIAL | Signalen minimaal: 2. under cursor / recently picked | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L208) |
| VIEWER-PERF-0129 | ui_performance_reporting | PARTIAL | Signalen minimaal: 3. visible | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L209) |
| VIEWER-PERF-0130 | ui_performance_reporting | PARTIAL | Signalen minimaal: 4. projected screen area / visual dominance | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L210) |
| VIEWER-PERF-0131 | ui_performance_reporting | PARTIAL | Signalen minimaal: 5. camera distance | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L211) |
| VIEWER-PERF-0132 | ui_performance_reporting | PARTIAL | Signalen minimaal: 6. current assembly/context | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L212) |
| VIEWER-PERF-0133 | ui_performance_reporting | PARTIAL | Signalen minimaal: 7. rest | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L213) |
| VIEWER-PERF-0134 | ui_performance_reporting | PARTIAL | Gebruik bij voorkeur: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L215) |
| VIEWER-PERF-0135 | ui_performance_reporting | PARTIAL | Eisen: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L227) |
| VIEWER-PERF-0136 | ui_performance_reporting | PARTIAL | Eisen: deterministic; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L228) |
| VIEWER-PERF-0137 | ui_performance_reporting | PARTIAL | Eisen: reprioritize op betekenisvolle camera/contextchange; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L229) |
| VIEWER-PERF-0138 | ui_performance_reporting | PARTIAL | Eisen: geen volledige queue rebuild per raw mouse event; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L230) |
| VIEWER-PERF-0139 | ui_performance_reporting | PARTIAL | Eisen: hysteresis; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L231) |
| VIEWER-PERF-0140 | ui_performance_reporting | PARTIAL | Eisen: starvation prevention; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L232) |
| VIEWER-PERF-0141 | ui_performance_reporting | PARTIAL | Eisen: selected preemption; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L233) |
| VIEWER-PERF-0142 | ui_performance_reporting | PARTIAL | Eisen: queue metrics. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L234) |
| VIEWER-PERF-0143 | ui_performance_reporting | PARTIAL | Nieuwe versie: `cws-viewer-mesh-cache-v2`. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L237) |
| VIEWER-PERF-0144 | ui_performance_reporting | PARTIAL | Persist minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L239) |
| VIEWER-PERF-0145 | ui_performance_reporting | PARTIAL | Persist minimaal: vertices | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L240) |
| VIEWER-PERF-0146 | ui_performance_reporting | PARTIAL | Persist minimaal: triangles/indices | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L241) |
| VIEWER-PERF-0147 | ui_performance_reporting | PARTIAL | Persist minimaal: normals | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L242) |
| VIEWER-PERF-0148 | ui_performance_reporting | PARTIAL | Persist minimaal: feature/sharp edges | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L243) |
| VIEWER-PERF-0149 | ui_performance_reporting | PARTIAL | Persist minimaal: bounds | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L244) |
| VIEWER-PERF-0150 | ui_performance_reporting | PARTIAL | Persist minimaal: LOD0 | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L245) |
| VIEWER-PERF-0151 | ui_performance_reporting | PARTIAL | Persist minimaal: LOD1 | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L246) |
| VIEWER-PERF-0152 | ui_performance_reporting | PARTIAL | Persist minimaal: LOD2 waar gegenereerd | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L247) |
| VIEWER-PERF-0153 | ui_performance_reporting | PARTIAL | Persist minimaal: metadata | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L248) |
| VIEWER-PERF-0154 | ui_performance_reporting | PARTIAL | Eisen: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L250) |
| VIEWER-PERF-0155 | ui_performance_reporting | PARTIAL | Eisen: mmap waar passend; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L251) |
| VIEWER-PERF-0156 | ui_performance_reporting | PARTIAL | Eisen: minimale decompress/copy overhead; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L252) |
| VIEWER-PERF-0157 | ui_performance_reporting | PARTIAL | Eisen: immutable/versioned format; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L253) |
| VIEWER-PERF-0158 | ui_performance_reporting | PARTIAL | Eisen: dtype/endian metadata; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L254) |
| VIEWER-PERF-0159 | ui_performance_reporting | PARTIAL | Eisen: atomic write; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L255) |
| VIEWER-PERF-0160 | ui_performance_reporting | PARTIAL | Eisen: corruption recovery; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L256) |
| VIEWER-PERF-0161 | ui_performance_reporting | PARTIAL | Eisen: source/settings/provider invalidation; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L257) |
| VIEWER-PERF-0162 | ui_performance_reporting | PARTIAL | Eisen: Windows mmap/file handle cleanup; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L258) |
| VIEWER-PERF-0163 | ui_performance_reporting | PARTIAL | Eisen: bounded RAM LRU. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L259) |
| VIEWER-PERF-0164 | ui_performance_reporting | PARTIAL | V1 mag veilig worden verwijderd/opnieuw opgebouwd in plaats van complexe migratie. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L261) |
| VIEWER-PERF-0165 | ui_performance_reporting | PARTIAL | Benchmark: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L263) |
| VIEWER-PERF-0166 | ui_performance_reporting | PARTIAL | Benchmark: cold no-cache | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L264) |
| VIEWER-PERF-0167 | ui_performance_reporting | PARTIAL | Benchmark: V1 warm indien reproduceerbaar | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L265) |
| VIEWER-PERF-0168 | ui_performance_reporting | PARTIAL | Benchmark: V2 disk warm new process | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L266) |
| VIEWER-PERF-0169 | ui_performance_reporting | PARTIAL | Benchmark: V2 same-session RAM hit | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L267) |
| VIEWER-PERF-0170 | ui_performance_reporting | PARTIAL | V2 warm moet meetbaar sneller zijn. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L269) |
| VIEWER-PERF-0171 | ui_performance_reporting | PARTIAL | Niet alleen batch size. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L272) |
| VIEWER-PERF-0172 | ui_performance_reporting | PARTIAL | Adaptief budget via governor: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L283) |
| VIEWER-PERF-0173 | ui_performance_reporting | PARTIAL | Adaptief budget via governor: INTERACTIVE: 1–3 ms/frame | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L284) |
| VIEWER-PERF-0174 | ui_performance_reporting | PARTIAL | Adaptief budget via governor: RECOVERY: 3–4 ms/frame | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L285) |
| VIEWER-PERF-0175 | ui_performance_reporting | PARTIAL | Adaptief budget via governor: IDLE_HIGH_QUALITY: 6–8 ms/frame | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L286) |
| VIEWER-PERF-0176 | ui_performance_reporting | PARTIAL | Benchmark de exacte defaults. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L288) |
| VIEWER-PERF-0177 | ui_performance_reporting | PARTIAL | Eisen: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L290) |
| VIEWER-PERF-0178 | ui_performance_reporting | PARTIAL | Eisen: backpressure; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L291) |
| VIEWER-PERF-0179 | ui_performance_reporting | PARTIAL | Eisen: stale generation discard; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L292) |
| VIEWER-PERF-0180 | ui_performance_reporting | PARTIAL | Eisen: cancellation; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L293) |
| VIEWER-PERF-0181 | ui_performance_reporting | PARTIAL | Eisen: camera/selection/visibility blijven intact; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L294) |
| VIEWER-PERF-0182 | ui_performance_reporting | PARTIAL | Eisen: incremental mesh refresh; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L295) |
| VIEWER-PERF-0183 | ui_performance_reporting | PARTIAL | Eisen: geen full scene rebuild; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L296) |
| VIEWER-PERF-0184 | ui_performance_reporting | PARTIAL | Eisen: queue/upload metrics. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L297) |
| VIEWER-PERF-0185 | ui_performance_reporting | PARTIAL | Maak één centrale authority met states: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L300) |
| VIEWER-PERF-0186 | ui_performance_reporting | PARTIAL | Maak één centrale authority met states: INTERACTIVE | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L301) |
| VIEWER-PERF-0187 | ui_performance_reporting | PARTIAL | Maak één centrale authority met states: RECOVERY | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L302) |
| VIEWER-PERF-0188 | ui_performance_reporting | PARTIAL | Maak één centrale authority met states: IDLE_HIGH_QUALITY | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L303) |
| VIEWER-PERF-0189 | ui_performance_reporting | PARTIAL | Maak één centrale authority met states: BACKGROUND_LOADING | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L304) |
| VIEWER-PERF-0190 | ui_performance_reporting | PARTIAL | Governor bepaalt: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L306) |
| VIEWER-PERF-0191 | ui_performance_reporting | PARTIAL | Governor bepaalt: MSAA | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L307) |
| VIEWER-PERF-0192 | ui_performance_reporting | PARTIAL | Governor bepaalt: FXAA | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L308) |
| VIEWER-PERF-0193 | ui_performance_reporting | PARTIAL | Governor bepaalt: SSAO | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L309) |
| VIEWER-PERF-0194 | ui_performance_reporting | PARTIAL | Governor bepaalt: shadows | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L310) |
| VIEWER-PERF-0195 | ui_performance_reporting | PARTIAL | Governor bepaalt: upload budget | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L311) |
| VIEWER-PERF-0196 | ui_performance_reporting | PARTIAL | Governor bepaalt: LOD target | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L312) |
| VIEWER-PERF-0197 | ui_performance_reporting | PARTIAL | Governor bepaalt: exact-refinement aggressiveness | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L313) |
| VIEWER-PERF-0198 | ui_performance_reporting | PARTIAL | Governor bepaalt: measurement preview rate | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L314) |
| VIEWER-PERF-0199 | ui_performance_reporting | PARTIAL | Governor bepaalt: non-critical inspector refresh/defer | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L315) |
| VIEWER-PERF-0200 | ui_performance_reporting | PARTIAL | Input → INTERACTIVE. Na inputstop → RECOVERY. Na ca. 100–200 ms stabiele idle → IDLE_HIGH_QUALITY. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L317) |
| VIEWER-PERF-0201 | ui_performance_reporting | PARTIAL | Benchmark: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L320) |
| VIEWER-PERF-0202 | ui_performance_reporting | PARTIAL | Benchmark: 0x MSAA + FXAA | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L321) |
| VIEWER-PERF-0203 | ui_performance_reporting | PARTIAL | Benchmark: 2x | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L322) |
| VIEWER-PERF-0204 | ui_performance_reporting | PARTIAL | Benchmark: 4x | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L323) |
| VIEWER-PERF-0205 | ui_performance_reporting | PARTIAL | Benchmark: 8x | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L324) |
| VIEWER-PERF-0206 | ui_performance_reporting | PARTIAL | Op medium/large en indien mogelijk geïntegreerde + discrete GPU. Meet p50/p95/p99 en stalls, plus screenshots. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L326) |
| VIEWER-PERF-0207 | ui_performance_reporting | PARTIAL | Kies policy uit bewijs. Waarschijnlijke richting maar niet vooraf hardcoderen: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L328) |
| VIEWER-PERF-0208 | ui_performance_reporting | PARTIAL | Kies policy uit bewijs. Waarschijnlijke richting maar niet vooraf hardcoderen: interactive 0–2x/FXAA | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L329) |
| VIEWER-PERF-0209 | ui_performance_reporting | PARTIAL | Kies policy uit bewijs. Waarschijnlijke richting maar niet vooraf hardcoderen: recovery 2x | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L330) |
| VIEWER-PERF-0210 | ui_performance_reporting | PARTIAL | Kies policy uit bewijs. Waarschijnlijke richting maar niet vooraf hardcoderen: idle HQ 4x | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L331) |
| VIEWER-PERF-0211 | ui_performance_reporting | PARTIAL | Verplicht: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L334) |
| VIEWER-PERF-0212 | ui_performance_reporting | PARTIAL | Verplicht: pool startup/shutdown; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L335) |
| VIEWER-PERF-0213 | ui_performance_reporting | PARTIAL | Verplicht: worker crash/restart; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L336) |
| VIEWER-PERF-0214 | ui_performance_reporting | PARTIAL | Verplicht: timeout/cancel; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L337) |
| VIEWER-PERF-0215 | ui_performance_reporting | PARTIAL | Verplicht: stale generation; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L338) |
| VIEWER-PERF-0216 | ui_performance_reporting | PARTIAL | Verplicht: priority reprioritization/starvation; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L339) |
| VIEWER-PERF-0217 | ui_performance_reporting | PARTIAL | Verplicht: Cache V2 R/W/corruption/invalidation; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L340) |
| VIEWER-PERF-0218 | ui_performance_reporting | PARTIAL | Verplicht: Windows mmap release; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L341) |
| VIEWER-PERF-0219 | ui_performance_reporting | PARTIAL | Verplicht: upload backpressure/time budget; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L342) |
| VIEWER-PERF-0220 | ui_performance_reporting | PARTIAL | Verplicht: governor transitions; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L343) |
| VIEWER-PERF-0221 | ui_performance_reporting | PARTIAL | Verplicht: MSAA policy; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L344) |
| VIEWER-PERF-0222 | ui_performance_reporting | PARTIAL | Verplicht: camera/selection persistence during patch. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L345) |
| VIEWER-PERF-0223 | ui_performance_reporting | PARTIAL | Deliverables onder `validation/viewer_performance_closeout/phase1/`: `WORKER_POOL_MATRIX.json`, `PRIORITY_SCHEDULER_MATRIX.json`, `CACHE_V2_REPORT.json/.md`, `UPLOAD_BUDGET_REPORT.json`, `GOVERNOR_REPORT.json`, `MSAA_FXAA_MATRIX.json`, `PHASE_1_CHECKLIST.json/.md`. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L347) |
| VIEWER-PERF-0224 | ui_performance_reporting | PARTIAL | Fase 1 PASS alleen wanneer alle bovenstaande onderdelen functioneel + geïntegreerd + regressievrij zijn. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L350) |
| VIEWER-PERF-0225 | ui_performance_reporting | PARTIAL | Koppel metrics aan dezelfde echte productviewer voor: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L355) |
| VIEWER-PERF-0226 | ui_performance_reporting | PARTIAL | Koppel metrics aan dezelfde echte productviewer voor: source run | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L356) |
| VIEWER-PERF-0227 | ui_performance_reporting | PARTIAL | Koppel metrics aan dezelfde echte productviewer voor: one-folder EXE | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L357) |
| VIEWER-PERF-0228 | ui_performance_reporting | PARTIAL | Koppel metrics aan dezelfde echte productviewer voor: fresh portable | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L358) |
| VIEWER-PERF-0229 | ui_performance_reporting | PARTIAL | Geen developer Python PATH. Eventueel `--viewer-performance-probe`, maar dezelfde Viewer/servicecode. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L360) |
| VIEWER-PERF-0230 | ui_performance_reporting | PARTIAL | Per run: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L363) |
| VIEWER-PERF-0231 | ui_performance_reporting | PARTIAL | Per run: CPU/model/cores | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L364) |
| VIEWER-PERF-0232 | ui_performance_reporting | PARTIAL | Per run: RAM | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L365) |
| VIEWER-PERF-0233 | ui_performance_reporting | PARTIAL | Per run: GPU/VRAM/driver | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L366) |
| VIEWER-PERF-0234 | ui_performance_reporting | PARTIAL | Per run: Windows | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L367) |
| VIEWER-PERF-0235 | ui_performance_reporting | PARTIAL | Per run: resolution/DPI/refresh | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L368) |
| VIEWER-PERF-0236 | ui_performance_reporting | PARTIAL | Per run: source SHA/version | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L369) |
| VIEWER-PERF-0237 | ui_performance_reporting | PARTIAL | Per run: model class/input size/entity/geometry/triangle count | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L370) |
| VIEWER-PERF-0238 | ui_performance_reporting | PARTIAL | Per run: cache mode | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L371) |
| VIEWER-PERF-0239 | ui_performance_reporting | PARTIAL | Per run: worker count | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L372) |
| VIEWER-PERF-0240 | ui_performance_reporting | PARTIAL | COLD: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L375) |
| VIEWER-PERF-0241 | ui_performance_reporting | PARTIAL | COLD: new process | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L376) |
| VIEWER-PERF-0242 | ui_performance_reporting | PARTIAL | COLD: CWS cache absent/cleared | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L377) |
| VIEWER-PERF-0243 | ui_performance_reporting | PARTIAL | COLD: minimaal 5 runs | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L378) |
| VIEWER-PERF-0244 | ui_performance_reporting | PARTIAL | WARM: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L380) |
| VIEWER-PERF-0245 | ui_performance_reporting | PARTIAL | WARM: new process | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L381) |
| VIEWER-PERF-0246 | ui_performance_reporting | PARTIAL | WARM: V2 disk cache populated | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L382) |
| VIEWER-PERF-0247 | ui_performance_reporting | PARTIAL | WARM: minimaal 10 runs | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L383) |
| VIEWER-PERF-0248 | ui_performance_reporting | PARTIAL | SAME SESSION: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L385) |
| VIEWER-PERF-0249 | ui_performance_reporting | PARTIAL | SAME SESSION: same process/session | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L386) |
| VIEWER-PERF-0250 | ui_performance_reporting | PARTIAL | SAME SESSION: minimaal 10 runs | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L387) |
| VIEWER-PERF-0251 | ui_performance_reporting | PARTIAL | Rapporteer min/median/p90/p95/max/stddev voor loadmetrics en resources. Geen “beste run” als enige conclusie. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L389) |
| VIEWER-PERF-0252 | ui_performance_reporting | PARTIAL | Modelset minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L391) |
| VIEWER-PERF-0253 | ui_performance_reporting | PARTIAL | Modelset minimaal: SMALL | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L392) |
| VIEWER-PERF-0254 | ui_performance_reporting | PARTIAL | Modelset minimaal: MEDIUM | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L393) |
| VIEWER-PERF-0255 | ui_performance_reporting | PARTIAL | Modelset minimaal: LARGE | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L394) |
| VIEWER-PERF-0256 | ui_performance_reporting | PARTIAL | Modelset minimaal: INSTANCE_HEAVY | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L395) |
| VIEWER-PERF-0257 | ui_performance_reporting | PARTIAL | Real large model preferred; ontbreekt deze dan status NOT_TESTED. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L397) |
| VIEWER-PERF-0258 | ui_performance_reporting | PARTIAL | Na first usable vaste reproduceerbare sequence: orbit, pan, wheel zoom, fit, front/top/iso, select, multi-select, hide/show, isolate. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L400) |
| VIEWER-PERF-0259 | ui_performance_reporting | PARTIAL | Meet frame p50/p95/p99, input p50/p95, stalls, pick p95, selection p95 en wrong-instance picks. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L403) |
| VIEWER-PERF-0260 | ui_performance_reporting | PARTIAL | Duur ≥600 s. Niet headless-only. Real VTK/OpenGL + representatieve geometry. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L406) |
| VIEWER-PERF-0261 | ui_performance_reporting | PARTIAL | Cycli: orbit/pan/zoom/fit/standard views/part selection/assembly selection/multiselect/hide/show/isolate/ghost/section/measure, en zo mogelijk progressive exact patches. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L410) |
| VIEWER-PERF-0262 | ui_performance_reporting | PARTIAL | Meet: RSS/VRAM/threads/processes/workers/actors/mesh groups/widgets + frame p50/p95/p99 + stall counts. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L413) |
| VIEWER-PERF-0263 | ui_performance_reporting | PARTIAL | Hard: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L416) |
| VIEWER-PERF-0264 | ui_performance_reporting | PARTIAL | Hard: RSS drift <10% | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L417) |
| VIEWER-PERF-0265 | ui_performance_reporting | PARTIAL | Hard: worker leak 0 | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L418) |
| VIEWER-PERF-0266 | ui_performance_reporting | PARTIAL | Hard: thread leak 0 | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L419) |
| VIEWER-PERF-0267 | ui_performance_reporting | PARTIAL | Hard: actor leak 0 | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L420) |
| VIEWER-PERF-0268 | ui_performance_reporting | PARTIAL | Hard: unintended >100 ms stalls 0 | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L421) |
| VIEWER-PERF-0269 | ui_performance_reporting | PARTIAL | Hard: crash 0 | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L422) |
| VIEWER-PERF-0270 | ui_performance_reporting | PARTIAL | Maak rapport: `metric \| before \| after \| delta \| % improvement \| status` | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L425) |
| VIEWER-PERF-0271 | ui_performance_reporting | PARTIAL | Minimaal: first usable, exact100, warm reopen, frame p95, frame p99, input p95, pick p95, RSS, stalls. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L428) |
| VIEWER-PERF-0272 | ui_performance_reporting | PARTIAL | Ontbrekende baseline = transparant NOT_TESTED. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L431) |
| VIEWER-PERF-0273 | ui_performance_reporting | PARTIAL | Deliverables phase2: `ENVIRONMENT.json`, `COLD_RUNS.json`, `WARM_RUNS.json`, `SAME_SESSION_RUNS.json`, `LOAD_BENCHMARK_SUMMARY.json/.md`, `FRAME_INPUT_BENCHMARK.json`, `PICKING_BENCHMARK.json`, `REAL_10MIN_SOAK.json/.md`, `BEFORE_AFTER.json/.md`, `PACKAGED_ONE_FOLDER_PROBE.json`, `PACKAGED_PORTABLE_PROBE.json`, `PHASE_2_CHECKLIST.json/.md`. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L433) |
| VIEWER-PERF-0274 | ui_performance_reporting | PARTIAL | Twee matrices. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L439) |
| VIEWER-PERF-0275 | ui_performance_reporting | PARTIAL | Behavior: orbit direction, pan, zoom, cursor zoom, pivot, fit, standard views, part/assembly/multi selection, hide/isolate/show, section, measure. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L441) |
| VIEWER-PERF-0276 | ui_performance_reporting | PARTIAL | Performance op exact dezelfde machine/model/camera: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L444) |
| VIEWER-PERF-0277 | ui_performance_reporting | PARTIAL | Performance op exact dezelfde machine/model/camera: first pixels | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L445) |
| VIEWER-PERF-0278 | ui_performance_reporting | PARTIAL | Performance op exact dezelfde machine/model/camera: first usable | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L446) |
| VIEWER-PERF-0279 | ui_performance_reporting | PARTIAL | Performance op exact dezelfde machine/model/camera: warm reopen | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L447) |
| VIEWER-PERF-0280 | ui_performance_reporting | PARTIAL | Performance op exact dezelfde machine/model/camera: frame p50/p95/p99 | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L448) |
| VIEWER-PERF-0281 | ui_performance_reporting | PARTIAL | Performance op exact dezelfde machine/model/camera: pick p95 | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L449) |
| VIEWER-PERF-0282 | ui_performance_reporting | PARTIAL | Performance op exact dezelfde machine/model/camera: memory | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L450) |
| VIEWER-PERF-0283 | ui_performance_reporting | PARTIAL | Rapporteer CWS/Trimble ratio. Target ≤1.10. Geen reference = NOT_TESTED, geen parityclaim. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L452) |
| VIEWER-PERF-0284 | ui_performance_reporting | PARTIAL | Tune pas na benchmarks: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L455) |
| VIEWER-PERF-0285 | ui_performance_reporting | PARTIAL | Tune pas na benchmarks: lighting | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L456) |
| VIEWER-PERF-0286 | ui_performance_reporting | PARTIAL | Tune pas na benchmarks: material response | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L457) |
| VIEWER-PERF-0287 | ui_performance_reporting | PARTIAL | Tune pas na benchmarks: normals | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L458) |
| VIEWER-PERF-0288 | ui_performance_reporting | PARTIAL | Tune pas na benchmarks: feature/silhouette edges | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L459) |
| VIEWER-PERF-0289 | ui_performance_reporting | PARTIAL | Tune pas na benchmarks: SSAO idle | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L460) |
| VIEWER-PERF-0290 | ui_performance_reporting | PARTIAL | Tune pas na benchmarks: shadows | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L461) |
| VIEWER-PERF-0291 | ui_performance_reporting | PARTIAL | Tune pas na benchmarks: idle MSAA/FXAA | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L462) |
| VIEWER-PERF-0292 | ui_performance_reporting | PARTIAL | Tune pas na benchmarks: background | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L463) |
| VIEWER-PERF-0293 | ui_performance_reporting | PARTIAL | Tune pas na benchmarks: selection fill/outline | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L464) |
| VIEWER-PERF-0294 | ui_performance_reporting | PARTIAL | Tune pas na benchmarks: LOD thresholds | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L465) |
| VIEWER-PERF-0295 | ui_performance_reporting | PARTIAL | Geen first-usable regressie. Geen frame p95 regressie >5% zonder onderbouwde visuele winst. Geen nieuwe >100 ms stalls. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L467) |
| VIEWER-PERF-0296 | ui_performance_reporting | PARTIAL | Fresh exact SHA: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L470) |
| VIEWER-PERF-0297 | ui_performance_reporting | PARTIAL | Fresh exact SHA: one-folder | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L471) |
| VIEWER-PERF-0298 | ui_performance_reporting | PARTIAL | Fresh exact SHA: portable | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L472) |
| VIEWER-PERF-0299 | ui_performance_reporting | PARTIAL | Fresh exact SHA: installer indien release-scope | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L473) |
| VIEWER-PERF-0300 | ui_performance_reporting | PARTIAL | Test launch/open/first pixels/first usable/orbit/pan/zoom/pick/selection/progressive exact/cache reopen/save/close/reopen. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L475) |
| VIEWER-PERF-0301 | ui_performance_reporting | PARTIAL | Bind evidence aan branch, commit40, tree SHA, version, worker/cache/scheduler/governor version, Python/Qt/VTK. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L477) |
| VIEWER-PERF-0302 | ui_performance_reporting | PARTIAL | Deliverables phase3: `TRIMBLE_ENVIRONMENT.json`, `TRIMBLE_BEHAVIOR_MATRIX.json`, `TRIMBLE_PERFORMANCE_MATRIX.json`, `TRIMBLE_COMPARISON.md`, `RENDER_MICROTUNING_MATRIX.json`, `RENDER_MICROTUNING.md`, `PACKAGED_FINAL_ACCEPTANCE.json/.md`, `FINAL_VIEWER_PERFORMANCE_ACCEPTANCE.json/.md`. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L479) |
| VIEWER-PERF-0303 | ui_performance_reporting | PARTIAL | Bereken: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L483) |
| VIEWER-PERF-0304 | ui_performance_reporting | PARTIAL | Bereken: IMPLEMENTATION_SCORE | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L484) |
| VIEWER-PERF-0305 | ui_performance_reporting | PARTIAL | Bereken: INTEGRATION_TEST_SCORE | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L485) |
| VIEWER-PERF-0306 | ui_performance_reporting | PARTIAL | Bereken: PACKAGED_PROOF_SCORE | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L486) |
| VIEWER-PERF-0307 | ui_performance_reporting | PARTIAL | Bereken: TRIMBLE_PROOF_SCORE | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L487) |
| VIEWER-PERF-0308 | ui_performance_reporting | PARTIAL | Voor elk van de 10 hoofdpunten: 0–100%, evidence refs, resterende gaps. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L489) |
| VIEWER-PERF-0309 | ui_performance_reporting | PARTIAL | Geen 100% zonder bewijs. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L491) |
| VIEWER-PERF-0310 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L494) |
| VIEWER-PERF-0311 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 1. current canonical SHA geaudit; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L495) |
| VIEWER-PERF-0312 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 2. worker pool gebouwd + benchmarked; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L496) |
| VIEWER-PERF-0313 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 3. crash isolation behouden; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L497) |
| VIEWER-PERF-0314 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 4. dynamic priority actief; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L498) |
| VIEWER-PERF-0315 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 5. starvation tests groen; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L499) |
| VIEWER-PERF-0316 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 6. Cache V2 actief; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L500) |
| VIEWER-PERF-0317 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 7. warm reopen meetbaar verbeterd; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L501) |
| VIEWER-PERF-0318 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 8. per-frame uploadbudget/backpressure actief; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L502) |
| VIEWER-PERF-0319 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 9. governor actief; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L503) |
| VIEWER-PERF-0320 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 10. MSAA/FXAA uit benchmark gekozen; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L504) |
| VIEWER-PERF-0321 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 11. packaged instrumentation werkt; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L505) |
| VIEWER-PERF-0322 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 12. cold/warm/same-session complete; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L506) |
| VIEWER-PERF-0323 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 13. frame p50/p95/p99 gemeten; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L507) |
| VIEWER-PERF-0324 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 14. input/pick gemeten; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L508) |
| VIEWER-PERF-0325 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 15. 10-min real soak PASS; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L509) |
| VIEWER-PERF-0326 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 16. RSS drift <10%; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L510) |
| VIEWER-PERF-0327 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 17. geen worker/thread/actor leaks; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L511) |
| VIEWER-PERF-0328 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 18. unintended >100 ms stalls = 0; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L512) |
| VIEWER-PERF-0329 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 19. before/after bewijs aanwezig; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L513) |
| VIEWER-PERF-0330 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 20. microtuning pas na benchmark; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L514) |
| VIEWER-PERF-0331 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 21. exact-SHA one-folder PASS; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L515) |
| VIEWER-PERF-0332 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 22. fresh portable PASS; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L516) |
| VIEWER-PERF-0333 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 23. geometry/selection/camera regressievrij; | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L517) |
| VIEWER-PERF-0334 | ui_performance_reporting | PARTIAL | `VIEWER PERFORMANCE CLOSEOUT = PASS` alleen wanneer: 24. Trimble PASS waar reference beschikbaar is, anders expliciet NOT_TESTED. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L518) |
| VIEWER-PERF-0335 | ui_performance_reporting | PARTIAL | 1 correctness/crash 2 UI freeze/>100ms stalls 3 first usable 4 worker throughput 5 cache reopen 6 frame p95/p99 7 input latency 8 picking 9 memory 10 renderingbeauty | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L521) |
| VIEWER-PERF-0336 | ui_performance_reporting | PARTIAL | Voorbeeld: | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L533) |
| VIEWER-PERF-0337 | ui_performance_reporting | PARTIAL | Voorbeeld: `perf(viewer): add persistent IFC process worker pool` | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L534) |
| VIEWER-PERF-0338 | ui_performance_reporting | PARTIAL | Voorbeeld: `perf(viewer): add dynamic viewport priority scheduler` | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L535) |
| VIEWER-PERF-0339 | ui_performance_reporting | PARTIAL | Voorbeeld: `perf(cache): add memory-mapped MeshCache V2` | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L536) |
| VIEWER-PERF-0340 | ui_performance_reporting | PARTIAL | Voorbeeld: `perf(viewer): add adaptive per-frame upload backpressure` | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L537) |
| VIEWER-PERF-0341 | ui_performance_reporting | PARTIAL | Voorbeeld: `perf(viewer): add centralized performance governor` | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L538) |
| VIEWER-PERF-0342 | ui_performance_reporting | PARTIAL | Voorbeeld: `perf(render): tune interaction AA from benchmark` | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L539) |
| VIEWER-PERF-0343 | ui_performance_reporting | PARTIAL | Voorbeeld: `test(perf): add packaged cold warm session benchmarks` | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L540) |
| VIEWER-PERF-0344 | ui_performance_reporting | PARTIAL | Voorbeeld: `test(perf): add 10-minute real Viewer soak` | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L541) |
| VIEWER-PERF-0345 | ui_performance_reporting | PARTIAL | Voorbeeld: `test(perf): add same-machine Trimble harness` | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L542) |
| VIEWER-PERF-0346 | ui_performance_reporting | PARTIAL | Voorbeeld: `perf(render): apply measured final microtuning` | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L543) |
| VIEWER-PERF-0347 | ui_performance_reporting | PARTIAL | Voorbeeld: `test(release): bind Viewer performance proof to exact SHA` | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L544) |
| VIEWER-PERF-0348 | ui_performance_reporting | PARTIAL | Bij “Ga verder / Bouw verder / Test verder / Volgende fase”: 1 fetch canonical HEAD 2 lees fasechecklist 3 pak eerste niet-PASS 4 reproduceer 5 fix 6 targeted tests 7 benchmark 8 regressie 9 evidence 10 commit 11 ga door | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L547) |
| VIEWER-PERF-0349 | ui_performance_reporting | PARTIAL | Geen nieuwe vraag wanneer checklist ondubbelzinnig is. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L560) |
| VIEWER-PERF-0350 | ui_performance_reporting | PARTIAL | A. preflight B. actual code audit van de 10 punten C. before-baseline waar nog mogelijk D. bouw/finaliseer Fase 1 E. voer Fase 1 gate uit | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L563) |
| VIEWER-PERF-0351 | ui_performance_reporting | PARTIAL | Niet eerst V5 UI-cosmetica. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L569) |
| VIEWER-PERF-0352 | ui_performance_reporting | PARTIAL | Niet stoppen na alleen documentaudit als codebouw veilig kan doorgaan. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L571) |
| VIEWER-PERF-0353 | ui_performance_reporting | PARTIAL | Het doel is niet meer performanceclasses, maar: > een aantoonbaar snellere, stabielere en vloeiendere CWS Viewer in de echte Windows-app, met meetbare cold/warm/session winst, geen langdurige UI-stalls, gecontroleerd geheugengedrag en waar mogelijk een onderbouwde same-machine vergelijking met Trimble. | requirements/sources/CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md (L574) |
| BOM-PARITY-0001 | bom | PARTIAL | Werk de bestaande **CWS Convertor** door tot één professionele, zeer eenvoudige en aantoonbaar correcte desktopapplicatie voor staalengineering en productievoorbereiding. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L9) |
| BOM-PARITY-0002 | bom | PARTIAL | De hoogste prioriteiten zijn: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L11) |
| BOM-PARITY-0003 | bom | PARTIAL | De hoogste prioriteiten zijn: 1. **Viewer exact vergelijken met Trimble Connect op observeerbaar gedrag en werkbaarheid.** | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L13) |
| BOM-PARITY-0004 | bom | PARTIAL | De hoogste prioriteiten zijn: 2. **Viewer veel sneller en vloeiender maken** bij openen, laden, selecteren, orbit, pan, zoom, hide/show en workspace-wissels. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L14) |
| BOM-PARITY-0005 | bom | PARTIAL | De hoogste prioriteiten zijn: 3. **Selectie moet op objectniveau kloppen:** klikken op ieder zichtbaar deel van een onderdeel selecteert standaard het volledige canonical object, niet toevallig één meshdriehoek of losse renderactor. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L15) |
| BOM-PARITY-0006 | bom | PARTIAL | De hoogste prioriteiten zijn: 4. De route **inladen → controleren → bewerken → Viewer → converteren → BOM → machine-indeling → optimaliseren → tekening/PDF → afdrukken/exporteren → save/reopen** moet integraal kloppen. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L16) |
| BOM-PARITY-0007 | bom | PARTIAL | De hoogste prioriteiten zijn: 5. **BOM moet 100% betrouwbaar** zijn en het centrale productie-overzicht worden. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L17) |
| BOM-PARITY-0008 | bom | PARTIAL | De hoogste prioriteiten zijn: 6. **Machine-indeling moet automatisch ontstaan na import/classificatie**, maar vanuit BOM eenvoudig handmatig te wijzigen zijn. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L18) |
| BOM-PARITY-0009 | bom | PARTIAL | De hoogste prioriteiten zijn: 7. **PDF/technische tekeningen moeten professioneel vector-based worden**, op maximaal praktisch kwaliteitsniveau, en eenvoudig te printen zijn. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L19) |
| BOM-PARITY-0010 | bom | PARTIAL | De hoogste prioriteiten zijn: 8. Het totale pakket moet **veel eenvoudiger, rustiger, visueel consistenter en logischer** worden zonder functies weg te gooien. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L20) |
| BOM-PARITY-0011 | bom | PARTIAL | De hoogste prioriteiten zijn: 9. **Iedere zichtbare knop, QAction, menuactie, contextmenuactie en interactieve control moet echt functioneren**, of aantoonbaar disabled zijn met een duidelijke reden. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L21) |
| BOM-PARITY-0012 | bom | PARTIAL | De hoogste prioriteiten zijn: 10. Pas na volledige end-to-end en Windows EXE/portable acceptatie mag de nieuwe productlijn als compleet worden aangeduid. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L22) |
| BOM-PARITY-0013 | bom | PARTIAL | Dit is **GEEN greenfield rewrite**. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L24) |
| BOM-PARITY-0014 | bom | PARTIAL | Bestaande bewezen subsystemen moeten worden: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L26) |
| BOM-PARITY-0015 | bom | PARTIAL | Bestaande bewezen subsystemen moeten worden: geïnventariseerd; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L27) |
| BOM-PARITY-0016 | bom | PARTIAL | Bestaande bewezen subsystemen moeten worden: behouden waar goed; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L28) |
| BOM-PARITY-0017 | bom | PARTIAL | Bestaande bewezen subsystemen moeten worden: geconsolideerd; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L29) |
| BOM-PARITY-0018 | bom | PARTIAL | Bestaande bewezen subsystemen moeten worden: sneller gemaakt; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L30) |
| BOM-PARITY-0019 | bom | PARTIAL | Bestaande bewezen subsystemen moeten worden: vereenvoudigd in de UI; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L31) |
| BOM-PARITY-0020 | bom | PARTIAL | Bestaande bewezen subsystemen moeten worden: geïntegreerd; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L32) |
| BOM-PARITY-0021 | bom | PARTIAL | Bestaande bewezen subsystemen moeten worden: getest; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L33) |
| BOM-PARITY-0022 | bom | PARTIAL | Bestaande bewezen subsystemen moeten worden: alleen herschreven wanneer de huidige architectuur aantoonbaar een blocker is. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L34) |
| BOM-PARITY-0023 | bom | PARTIAL | Repository: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L40) |
| BOM-PARITY-0024 | bom | PARTIAL | Canonical branch: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L46) |
| BOM-PARITY-0025 | bom | PARTIAL | Auditbaseline bij het opstellen van deze prompt: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L52) |
| BOM-PARITY-0026 | bom | PARTIAL | Deze SHA is alleen de baseline van deze prompt. **Negeer nooit een nieuwere canonical HEAD.** | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L61) |
| BOM-PARITY-0027 | bom | PARTIAL | Bij iedere Codex-sessie eerst: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L63) |
| BOM-PARITY-0028 | bom | PARTIAL | Lees minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L74) |
| BOM-PARITY-0029 | bom | PARTIAL | Eerste response van een nieuwe Codex-sessie: maximaal 30 regels met: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L100) |
| BOM-PARITY-0030 | bom | PARTIAL | Controleer dit opnieuw op actuele HEAD, maar de auditbaseline laat minimaal het volgende zien: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L121) |
| BOM-PARITY-0031 | bom | PARTIAL | `cws_convertor/ui_qt/engineering_drawing.py` bouwt de tekening met PIL en schrijft de PDF via een gerasterde `Image.save(..., format="PDF", resolution=300.0)` route. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L125) |
| BOM-PARITY-0032 | bom | PARTIAL | Dat is niet voldoende voor de gewenste productie-PDF. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L127) |
| BOM-PARITY-0033 | bom | PARTIAL | Nieuwe eis: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L129) |
| BOM-PARITY-0034 | bom | PARTIAL | De huidige `BomWorkspacePanel` toont hoofdzakelijk: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L138) |
| BOM-PARITY-0035 | bom | PARTIAL | en heeft zoeken/filteren/groeperen/export. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L152) |
| BOM-PARITY-0036 | bom | PARTIAL | Nieuwe eis: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L154) |
| BOM-PARITY-0037 | bom | PARTIAL | BOM wordt het centrale **BOM & Productie**-werkgebied inclusief: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L156) |
| BOM-PARITY-0038 | bom | PARTIAL | BOM wordt het centrale **BOM & Productie**-werkgebied inclusief: machine-indeling; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L157) |
| BOM-PARITY-0039 | bom | PARTIAL | BOM wordt het centrale **BOM & Productie**-werkgebied inclusief: optimalisatie; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L158) |
| BOM-PARITY-0040 | bom | PARTIAL | BOM wordt het centrale **BOM & Productie**-werkgebied inclusief: tekening/PDF; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L159) |
| BOM-PARITY-0041 | bom | PARTIAL | BOM wordt het centrale **BOM & Productie**-werkgebied inclusief: print; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L160) |
| BOM-PARITY-0042 | bom | PARTIAL | BOM wordt het centrale **BOM & Productie**-werkgebied inclusief: edit; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L161) |
| BOM-PARITY-0043 | bom | PARTIAL | BOM wordt het centrale **BOM & Productie**-werkgebied inclusief: convert/export; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L162) |
| BOM-PARITY-0044 | bom | PARTIAL | BOM wordt het centrale **BOM & Productie**-werkgebied inclusief: production status; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L163) |
| BOM-PARITY-0045 | bom | PARTIAL | BOM wordt het centrale **BOM & Productie**-werkgebied inclusief: blockers; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L164) |
| BOM-PARITY-0046 | bom | PARTIAL | BOM wordt het centrale **BOM & Productie**-werkgebied inclusief: traceability. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L165) |
| BOM-PARITY-0047 | bom | PARTIAL | Gebruik bestaande machine-/nesting-capability code. Niet omzeilen. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L169) |
| BOM-PARITY-0048 | bom | PARTIAL | De bestaande safety-boundary blijft gelden: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L171) |
| BOM-PARITY-0049 | bom | PARTIAL | zolang echte specifieke controller-/machinequalification niet extern is bewezen. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L177) |
| BOM-PARITY-0050 | bom | PARTIAL | De gebruiker mag geen V6/V9/V15/preview/legacy-architectuur hoeven begrijpen. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L181) |
| BOM-PARITY-0051 | bom | PARTIAL | Product-UI toont één naam: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L183) |
| BOM-PARITY-0052 | bom | PARTIAL | Interne versielabels horen alleen in About/Diagnostics/Evidence. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L189) |
| BOM-PARITY-0053 | bom | PARTIAL | Prioriteitsvolgorde bij conflict: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L195) |
| BOM-PARITY-0054 | bom | PARTIAL | Prioriteitsvolgorde bij conflict: 1. actuele gebruikersopdracht; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L197) |
| BOM-PARITY-0055 | bom | PARTIAL | Prioriteitsvolgorde bij conflict: 2. actuele canonical code en tests; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L198) |
| BOM-PARITY-0056 | bom | PARTIAL | Prioriteitsvolgorde bij conflict: 3. deze superprompt; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L199) |
| BOM-PARITY-0057 | bom | PARTIAL | Prioriteitsvolgorde bij conflict: 4. huidige product authority/status documentatie; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L200) |
| BOM-PARITY-0058 | bom | PARTIAL | Prioriteitsvolgorde bij conflict: 5. bestaande Full Product Acceptance requirements; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L201) |
| BOM-PARITY-0059 | bom | PARTIAL | Prioriteitsvolgorde bij conflict: 6. gespecialiseerde moduleprompts; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L202) |
| BOM-PARITY-0060 | bom | PARTIAL | Prioriteitsvolgorde bij conflict: 7. historische branches/handovers; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L203) |
| BOM-PARITY-0061 | bom | PARTIAL | Prioriteitsvolgorde bij conflict: 8. Trimble Connect als **observeerbare functionele/UX referentie**. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L204) |
| BOM-PARITY-0062 | bom | PARTIAL | Trimble-regel: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L206) |
| BOM-PARITY-0063 | bom | PARTIAL | Trimble-regel: Vergelijk observeerbaar gedrag, layout, rendering, interactie en performance. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L208) |
| BOM-PARITY-0064 | bom | PARTIAL | Trimble-regel: Kopieer geen proprietary broncode, binaire implementatie of assets. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L209) |
| BOM-PARITY-0065 | bom | PARTIAL | Trimble-regel: Reverse-engineer geen private protocollen die niet nodig zijn voor de gebruikerservaring. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L210) |
| BOM-PARITY-0066 | bom | PARTIAL | Trimble-regel: "Exact hetzelfde" betekent hier: **geen materieel verschil in waarneembare bediening en werkbaarheid binnen de vastgelegde paritycases**. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L211) |
| BOM-PARITY-0067 | bom | PARTIAL | Trimble-regel: Wanneer exact gedrag niet objectief kan worden gemeten: `NOT_PROVEN`, niet gokken. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L212) |
| BOM-PARITY-0068 | bom | PARTIAL | Safety: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L214) |
| BOM-PARITY-0069 | bom | PARTIAL | blijft gelden zonder externe evidence. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L222) |
| BOM-PARITY-0070 | bom | PARTIAL | Behoud/realiseer: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L228) |
| BOM-PARITY-0071 | bom | PARTIAL | Verboden: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L250) |
| BOM-PARITY-0072 | bom | PARTIAL | Verboden: tweede projectmodel in een tab; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L252) |
| BOM-PARITY-0073 | bom | PARTIAL | Verboden: Viewer opnieuw opbouwen bij workspacewissel; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L253) |
| BOM-PARITY-0074 | bom | PARTIAL | Verboden: directe UI-mutaties buiten canonical transaction services; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L254) |
| BOM-PARITY-0075 | bom | PARTIAL | Verboden: aparte BOM-data die niet uit Canonical Project Model traceerbaar is; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L255) |
| BOM-PARITY-0076 | bom | PARTIAL | Verboden: machinekeuze hardcoden op alleen profieltekst; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L256) |
| BOM-PARITY-0077 | bom | PARTIAL | Verboden: raster-PDF als production drawing bestempelen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L257) |
| BOM-PARITY-0078 | bom | PARTIAL | Verboden: knoppen laten bestaan die niets doen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L258) |
| BOM-PARITY-0079 | bom | PARTIAL | Verboden: unsupported actie stil uitvoeren via fallback; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L259) |
| BOM-PARITY-0080 | bom | PARTIAL | Verboden: lege selection als projectscope interpreteren bij selection-export; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L260) |
| BOM-PARITY-0081 | bom | PARTIAL | Verboden: performance winnen door geometrie/feature-inhoud stil te verliezen. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L261) |
| BOM-PARITY-0082 | bom | PARTIAL | Gebruik alleen: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L267) |
| BOM-PARITY-0083 | bom | PARTIAL | Geen "lijkt goed", "waarschijnlijk", "ongeveer compleet" als eindstatus. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L277) |
| BOM-PARITY-0084 | bom | PARTIAL | Een fase is alleen COMPLETE als: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L279) |
| BOM-PARITY-0085 | bom | PARTIAL | Uitzondering: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L287) |
| BOM-PARITY-0086 | bom | PARTIAL | Echte specifieke machine/controllerqualification mag als: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L289) |
| BOM-PARITY-0087 | bom | PARTIAL | apart blijven, mits software hier fail-closed blijft en niet als production transfer wordt vrijgegeven. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L295) |
| BOM-PARITY-0088 | bom | PARTIAL | Trimble parity mag **niet** als PASS worden verklaard zonder echte Trimble-reference evidence. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L297) |
| BOM-PARITY-0089 | bom | PARTIAL | Doel: een normale gebruiker moet zonder kennis van interne modules begrijpen wat hij moet doen. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L303) |
| BOM-PARITY-0090 | bom | PARTIAL | Maak de productie-UI logisch rond: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L307) |
| BOM-PARITY-0091 | bom | PARTIAL | Settings/Help/About zijn secundair. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L317) |
| BOM-PARITY-0092 | bom | PARTIAL | Bestaande subsystemen verdwijnen niet, maar worden logisch gegroepeerd. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L319) |
| BOM-PARITY-0093 | bom | PARTIAL | Subtabs of compacte views: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L323) |
| BOM-PARITY-0094 | bom | PARTIAL | Productiecontrole mag advanced functies bevatten zoals: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L332) |
| BOM-PARITY-0095 | bom | PARTIAL | Productiecontrole mag advanced functies bevatten zoals: Manufacturing Faces; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L333) |
| BOM-PARITY-0096 | bom | PARTIAL | Productiecontrole mag advanced functies bevatten zoals: Contact; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L334) |
| BOM-PARITY-0097 | bom | PARTIAL | Productiecontrole mag advanced functies bevatten zoals: Scribing/Marking; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L335) |
| BOM-PARITY-0098 | bom | PARTIAL | Productiecontrole mag advanced functies bevatten zoals: Hole References; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L336) |
| BOM-PARITY-0099 | bom | PARTIAL | Productiecontrole mag advanced functies bevatten zoals: Identification; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L337) |
| BOM-PARITY-0100 | bom | PARTIAL | Productiecontrole mag advanced functies bevatten zoals: Machine Reachability; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L338) |
| BOM-PARITY-0101 | bom | PARTIAL | Productiecontrole mag advanced functies bevatten zoals: Sequence; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L339) |
| BOM-PARITY-0102 | bom | PARTIAL | Productiecontrole mag advanced functies bevatten zoals: blockers. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L340) |
| BOM-PARITY-0103 | bom | PARTIAL | Laat advanced details pas zien wanneer de gebruiker ze nodig heeft. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L342) |
| BOM-PARITY-0104 | bom | PARTIAL | Bij een geselecteerd onderdeel of meerdere onderdelen zijn dezelfde kernacties vanuit Viewer, Project Tree en BOM beschikbaar: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L354) |
| BOM-PARITY-0105 | bom | PARTIAL | Gebruik één centrale commandservice, bijvoorbeeld conceptueel: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L366) |
| BOM-PARITY-0106 | bom | PARTIAL | De UI mag niet zelf per scherm eigen businesslogica dupliceren. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L373) |
| BOM-PARITY-0107 | bom | PARTIAL | Een actie die niet kan: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L377) |
| BOM-PARITY-0108 | bom | PARTIAL | Een actie die niet kan: disabled; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L379) |
| BOM-PARITY-0109 | bom | PARTIAL | Een actie die niet kan: duidelijke tooltip/reason; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L380) |
| BOM-PARITY-0110 | bom | PARTIAL | Een actie die niet kan: eventueel link naar blocker. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L381) |
| BOM-PARITY-0111 | bom | PARTIAL | Nooit een zichtbare knop die klikt maar niets doet. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L383) |
| BOM-PARITY-0112 | bom | PARTIAL | De Viewer moet **side-by-side** met Trimble Connect worden getest met hetzelfde model op dezelfde machine waar mogelijk. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L389) |
| BOM-PARITY-0113 | bom | PARTIAL | Directory: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L393) |
| BOM-PARITY-0114 | bom | PARTIAL | Maak: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L405) |
| BOM-PARITY-0115 | bom | PARTIAL | Leg vast: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L417) |
| BOM-PARITY-0116 | bom | PARTIAL | Leg vast: Trimble-versie/build; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L419) |
| BOM-PARITY-0117 | bom | PARTIAL | Leg vast: CWS HEAD; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L420) |
| BOM-PARITY-0118 | bom | PARTIAL | Leg vast: Windows-versie; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L421) |
| BOM-PARITY-0119 | bom | PARTIAL | Leg vast: schermresolutie; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L422) |
| BOM-PARITY-0120 | bom | PARTIAL | Leg vast: DPI scaling; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L423) |
| BOM-PARITY-0121 | bom | PARTIAL | Leg vast: monitor refresh; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L424) |
| BOM-PARITY-0122 | bom | PARTIAL | Leg vast: CPU; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L425) |
| BOM-PARITY-0123 | bom | PARTIAL | Leg vast: RAM; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L426) |
| BOM-PARITY-0124 | bom | PARTIAL | Leg vast: GPU/driver; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L427) |
| BOM-PARITY-0125 | bom | PARTIAL | Leg vast: exact hetzelfde testmodel/hash; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L428) |
| BOM-PARITY-0126 | bom | PARTIAL | Leg vast: camera startpositie voor iedere testcase; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L429) |
| BOM-PARITY-0127 | bom | PARTIAL | Leg vast: inputdevice; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L430) |
| BOM-PARITY-0128 | bom | PARTIAL | Leg vast: capture frame rate. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L431) |
| BOM-PARITY-0129 | bom | PARTIAL | Als Trimble niet op de Codex-machine toegankelijk is: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L433) |
| BOM-PARITY-0130 | bom | PARTIAL | Als Trimble niet op de Codex-machine toegankelijk is: 1. zoek naar bestaande referentievideo's/screenshots/metingen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L435) |
| BOM-PARITY-0131 | bom | PARTIAL | Als Trimble niet op de Codex-machine toegankelijk is: 2. maak tooling/scripts waarmee de gebruiker op Windows de reference kan opnemen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L436) |
| BOM-PARITY-0132 | bom | PARTIAL | Als Trimble niet op de Codex-machine toegankelijk is: 3. leg exact vast welke evidence ontbreekt; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L437) |
| BOM-PARITY-0133 | bom | PARTIAL | Als Trimble niet op de Codex-machine toegankelijk is: 4. verbeter CWS verder waar intern bewijs mogelijk is; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L438) |
| BOM-PARITY-0134 | bom | PARTIAL | Als Trimble niet op de Codex-machine toegankelijk is: 5. declareer parity niet als PASS zonder reference. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L439) |
| BOM-PARITY-0135 | bom | PARTIAL | Minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L443) |
| BOM-PARITY-0136 | bom | PARTIAL | Meet scripted drags/wheel events. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L492) |
| BOM-PARITY-0137 | bom | PARTIAL | Voor dezelfde viewport, camera start en input: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L494) |
| BOM-PARITY-0138 | bom | PARTIAL | Voor dezelfde viewport, camera start en input: orbit direction exact; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L496) |
| BOM-PARITY-0139 | bom | PARTIAL | Voor dezelfde viewport, camera start en input: pan direction exact; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L497) |
| BOM-PARITY-0140 | bom | PARTIAL | Voor dezelfde viewport, camera start en input: wheel direction exact; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L498) |
| BOM-PARITY-0141 | bom | PARTIAL | Voor dezelfde viewport, camera start en input: pivotgedrag gelijk; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L499) |
| BOM-PARITY-0142 | bom | PARTIAL | Voor dezelfde viewport, camera start en input: cursor-anchored zoom gelijk; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L500) |
| BOM-PARITY-0143 | bom | PARTIAL | Voor dezelfde viewport, camera start en input: world-up gedrag gelijk; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L501) |
| BOM-PARITY-0144 | bom | PARTIAL | Voor dezelfde viewport, camera start en input: geen onverwachte camera roll; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L502) |
| BOM-PARITY-0145 | bom | PARTIAL | Voor dezelfde viewport, camera start en input: fit framing visueel gelijkwaardig; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L503) |
| BOM-PARITY-0146 | bom | PARTIAL | Voor dezelfde viewport, camera start en input: mouse sensitivity praktisch gelijk. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L504) |
| BOM-PARITY-0147 | bom | PARTIAL | Kalibratiedoelen na reference capture: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L506) |
| BOM-PARITY-0148 | bom | PARTIAL | Wanneer Trimble-observatie een ander exact patroon toont, volgt CWS die reference. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L519) |
| BOM-PARITY-0149 | bom | PARTIAL | Default selectiemodus: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L523) |
| BOM-PARITY-0150 | bom | PARTIAL | Klikken op: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L533) |
| BOM-PARITY-0151 | bom | PARTIAL | Klikken op: web; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L534) |
| BOM-PARITY-0152 | bom | PARTIAL | Klikken op: flens; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L535) |
| BOM-PARITY-0153 | bom | PARTIAL | Klikken op: rand; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L536) |
| BOM-PARITY-0154 | bom | PARTIAL | Klikken op: deel van tessellated mesh; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L537) |
| BOM-PARITY-0155 | bom | PARTIAL | Klikken op: zichtbaar submesh; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L538) |
| BOM-PARITY-0156 | bom | PARTIAL | moet hetzelfde Part/Assembly-object selecteren volgens actieve selection mode. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L540) |
| BOM-PARITY-0157 | bom | PARTIAL | Geen losse triangle-selection in de normale gebruikersmodus. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L542) |
| BOM-PARITY-0158 | bom | PARTIAL | Feature/subshape-selectie mag alleen in expliciete advanced/edit/measure mode. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L544) |
| BOM-PARITY-0159 | bom | PARTIAL | Verplicht: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L546) |
| BOM-PARITY-0160 | bom | PARTIAL | Vergelijk en kalibreer: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L557) |
| BOM-PARITY-0161 | bom | PARTIAL | Gebruik screenshot-diff als hulpmiddel, niet als enige waarheid. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L582) |
| BOM-PARITY-0162 | bom | PARTIAL | Geen eigen decoratieve effecten toevoegen die de technische leesbaarheid slechter maken. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L584) |
| BOM-PARITY-0163 | bom | PARTIAL | Meet CWS én Trimble op hetzelfde model/hardware. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L588) |
| BOM-PARITY-0164 | bom | PARTIAL | Minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L590) |
| BOM-PARITY-0165 | bom | PARTIAL | CWS doel: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L616) |
| BOM-PARITY-0166 | bom | PARTIAL | Relatief doel op dezelfde machine/model: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L629) |
| BOM-PARITY-0167 | bom | PARTIAL | Als CWS sneller is: behouden. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L637) |
| BOM-PARITY-0168 | bom | PARTIAL | Als Trimble de absolute target niet haalt, gebruik beide resultaten en motiveer de acceptatie. Geen verborgen targetverlaging. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L639) |
| BOM-PARITY-0169 | bom | PARTIAL | Optimaliseer op profilerbewijs, niet op gevoel. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L645) |
| BOM-PARITY-0170 | bom | PARTIAL | Prioriteiten: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L647) |
| BOM-PARITY-0171 | bom | PARTIAL | Prioriteiten: 1. één permanent renderwindow/viewer host; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L649) |
| BOM-PARITY-0172 | bom | PARTIAL | Prioriteiten: 2. geen full scene rebuild op selectie; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L650) |
| BOM-PARITY-0173 | bom | PARTIAL | Prioriteiten: 3. geen full scene rebuild op hide/show; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L651) |
| BOM-PARITY-0174 | bom | PARTIAL | Prioriteiten: 4. incremental scene patches; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L652) |
| BOM-PARITY-0175 | bom | PARTIAL | Prioriteiten: 5. content-hash geometry cache; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L653) |
| BOM-PARITY-0176 | bom | PARTIAL | Prioriteiten: 6. background import/meshing; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L654) |
| BOM-PARITY-0177 | bom | PARTIAL | Prioriteiten: 7. progressive coarse → refined geometry; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L655) |
| BOM-PARITY-0178 | bom | PARTIAL | Prioriteiten: 8. selected object exact upgrade on demand; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L656) |
| BOM-PARITY-0179 | bom | PARTIAL | Prioriteiten: 9. bounded/cancellable workers; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L657) |
| BOM-PARITY-0180 | bom | PARTIAL | Prioriteiten: 10. stale-generation rejection; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L658) |
| BOM-PARITY-0181 | bom | PARTIAL | Prioriteiten: 11. spatial/scene index voor picking; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L659) |
| BOM-PARITY-0182 | bom | PARTIAL | Prioriteiten: 12. entity-to-render-handle mapping; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L660) |
| BOM-PARITY-0183 | bom | PARTIAL | Prioriteiten: 13. vermijd duizenden onnodige afzonderlijke actors wanneer batching aantoonbaar sneller is; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L661) |
| BOM-PARITY-0184 | bom | PARTIAL | Prioriteiten: 14. geen zware sync call op UI-thread > 50 ms zonder aantoonbare noodzaak; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L662) |
| BOM-PARITY-0185 | bom | PARTIAL | Prioriteiten: 15. workspace switch verandert alleen UI-compositie, niet project/viewer authority. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L663) |
| BOM-PARITY-0186 | bom | PARTIAL | Behoud de huidige hybride sterke punten wanneer bewezen: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L665) |
| BOM-PARITY-0187 | bom | PARTIAL | Behoud de huidige hybride sterke punten wanneer bewezen: snelle VTK projectweergave; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L666) |
| BOM-PARITY-0188 | bom | PARTIAL | Behoud de huidige hybride sterke punten wanneer bewezen: exact OCCT/OCP waar nodig; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L667) |
| BOM-PARITY-0189 | bom | PARTIAL | Behoud de huidige hybride sterke punten wanneer bewezen: canonical geometry authority. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L668) |
| BOM-PARITY-0190 | bom | PARTIAL | Geen geometry downgrade om benchmark groen te maken. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L670) |
| BOM-PARITY-0191 | bom | PARTIAL | Dit is een harde end-to-end requirement. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L676) |
| BOM-PARITY-0192 | bom | PARTIAL | Voor iedere ondersteunde bronroute: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L678) |
| BOM-PARITY-0193 | bom | PARTIAL | Minimale golden workflows: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L703) |
| BOM-PARITY-0194 | bom | PARTIAL | BOM is geen losse tabel maar een gecontroleerde projectafleiding. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L780) |
| BOM-PARITY-0195 | bom | PARTIAL | Ondersteun views/exports voor: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L784) |
| BOM-PARITY-0196 | bom | PARTIAL | Behoud BOM hoeveelheden als eigen versioned snapshot. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L812) |
| BOM-PARITY-0197 | bom | PARTIAL | Voeg machine-indeling bij voorkeur toe als aparte versioned authority, conceptueel: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L814) |
| BOM-PARITY-0198 | bom | PARTIAL | joinbaar op canonical entity/group IDs. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L824) |
| BOM-PARITY-0199 | bom | PARTIAL | Waarom: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L826) |
| BOM-PARITY-0200 | bom | PARTIAL | Een machinewijziging mag nooit stil het aantal, profiel, materiaal, gewicht of geometry hash veranderen. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L832) |
| BOM-PARITY-0201 | bom | PARTIAL | Voor golden projecten: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L836) |
| BOM-PARITY-0202 | bom | PARTIAL | Controleer onafhankelijk: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L849) |
| BOM-PARITY-0203 | bom | PARTIAL | Controleer onafhankelijk: aantallen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L851) |
| BOM-PARITY-0204 | bom | PARTIAL | Controleer onafhankelijk: lengtes; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L852) |
| BOM-PARITY-0205 | bom | PARTIAL | Controleer onafhankelijk: profiel; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L853) |
| BOM-PARITY-0206 | bom | PARTIAL | Controleer onafhankelijk: materiaal; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L854) |
| BOM-PARITY-0207 | bom | PARTIAL | Controleer onafhankelijk: gewicht; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L855) |
| BOM-PARITY-0208 | bom | PARTIAL | Controleer onafhankelijk: total weight; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L856) |
| BOM-PARITY-0209 | bom | PARTIAL | Controleer onafhankelijk: area; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L857) |
| BOM-PARITY-0210 | bom | PARTIAL | Controleer onafhankelijk: assemblies/occurrences; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L858) |
| BOM-PARITY-0211 | bom | PARTIAL | Controleer onafhankelijk: purchased quantities; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L859) |
| BOM-PARITY-0212 | bom | PARTIAL | Controleer onafhankelijk: fasteners; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L860) |
| BOM-PARITY-0213 | bom | PARTIAL | Controleer onafhankelijk: welds; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L861) |
| BOM-PARITY-0214 | bom | PARTIAL | Controleer onafhankelijk: status; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L862) |
| BOM-PARITY-0215 | bom | PARTIAL | Controleer onafhankelijk: blockers; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L863) |
| BOM-PARITY-0216 | bom | PARTIAL | Controleer onafhankelijk: source identity; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L864) |
| BOM-PARITY-0217 | bom | PARTIAL | Controleer onafhankelijk: geometry/manufacturing hashes waar relevant. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L865) |
| BOM-PARITY-0218 | bom | PARTIAL | Rond alleen voor display af. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L867) |
| BOM-PARITY-0219 | bom | PARTIAL | Interne berekening behoudt volledige vereiste precisie. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L869) |
| BOM-PARITY-0220 | bom | PARTIAL | Hoofdtabel minimaal optioneel beschikbaar: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L873) |
| BOM-PARITY-0221 | bom | PARTIAL | Niet alle kolommen hoeven standaard zichtbaar. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L899) |
| BOM-PARITY-0222 | bom | PARTIAL | Default view moet rustig blijven. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L901) |
| BOM-PARITY-0223 | bom | PARTIAL | Kolomsets: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L903) |
| BOM-PARITY-0224 | bom | PARTIAL | Behoud: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L914) |
| BOM-PARITY-0225 | bom | PARTIAL | Behoud: zoeken; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L915) |
| BOM-PARITY-0226 | bom | PARTIAL | Behoud: filter; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L916) |
| BOM-PARITY-0227 | bom | PARTIAL | Behoud: sort; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L917) |
| BOM-PARITY-0228 | bom | PARTIAL | Behoud: group; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L918) |
| BOM-PARITY-0229 | bom | PARTIAL | Behoud: column chooser; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L919) |
| BOM-PARITY-0230 | bom | PARTIAL | Behoud: reorder; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L920) |
| BOM-PARITY-0231 | bom | PARTIAL | Behoud: saved layouts; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L921) |
| BOM-PARITY-0232 | bom | PARTIAL | Behoud: multiselect; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L922) |
| BOM-PARITY-0233 | bom | PARTIAL | Behoud: Viewer sync. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L923) |
| BOM-PARITY-0234 | bom | PARTIAL | Voor selectie: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L927) |
| BOM-PARITY-0235 | bom | PARTIAL | Bulkselectie moet werken. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L940) |
| BOM-PARITY-0236 | bom | PARTIAL | Contextmenu idem via dezelfde centrale action service. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L942) |
| BOM-PARITY-0237 | bom | PARTIAL | Doelvoorbeeld van de gebruiker: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L948) |
| BOM-PARITY-0238 | bom | PARTIAL | Doelvoorbeeld van de gebruiker: vlak/plat profielmateriaal kan naar een andere machine dan balkprofielen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L950) |
| BOM-PARITY-0239 | bom | PARTIAL | Doelvoorbeeld van de gebruiker: balkstaal kan automatisch naar de daarvoor geconfigureerde machine; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L951) |
| BOM-PARITY-0240 | bom | PARTIAL | Doelvoorbeeld van de gebruiker: de gebruiker moet dit eenvoudig vanuit BOM kunnen wijzigen. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L952) |
| BOM-PARITY-0241 | bom | PARTIAL | Maak dit generiek en configureerbaar. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L954) |
| BOM-PARITY-0242 | bom | PARTIAL | Niet: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L958) |
| BOM-PARITY-0243 | bom | PARTIAL | Wel: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L965) |
| BOM-PARITY-0244 | bom | PARTIAL | Conceptueel: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L984) |
| BOM-PARITY-0245 | bom | PARTIAL | Voor simpele bediening bied je een Basic mode: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1001) |
| BOM-PARITY-0246 | bom | PARTIAL | bijvoorbeeld categorieën: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1007) |
| BOM-PARITY-0247 | bom | PARTIAL | Advanced mode gebruikt de volledige capability rules. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1020) |
| BOM-PARITY-0248 | bom | PARTIAL | Na import/classificatie: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1024) |
| BOM-PARITY-0249 | bom | PARTIAL | Resultaat per BOM-regel: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1035) |
| BOM-PARITY-0250 | bom | PARTIAL | De gebruiker kan: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1049) |
| BOM-PARITY-0251 | bom | PARTIAL | De gebruiker kan: één rij machine kiezen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1051) |
| BOM-PARITY-0252 | bom | PARTIAL | De gebruiker kan: meerdere rijen bulk toewijzen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1052) |
| BOM-PARITY-0253 | bom | PARTIAL | De gebruiker kan: selectie resetten naar Auto; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1053) |
| BOM-PARITY-0254 | bom | PARTIAL | De gebruiker kan: manual assignment locken; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1054) |
| BOM-PARITY-0255 | bom | PARTIAL | De gebruiker kan: zien waarom een machine wel/niet geschikt is. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1055) |
| BOM-PARITY-0256 | bom | PARTIAL | Vrije keuze betekent: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1057) |
| BOM-PARITY-0257 | bom | PARTIAL | Vrije keuze betekent: alle geconfigureerde machines mogen zichtbaar zijn; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1059) |
| BOM-PARITY-0258 | bom | PARTIAL | Vrije keuze betekent: een incompatibele manual choice mag worden gekozen voor review, maar krijgt duidelijk `BLOCKED/REVIEW`; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1060) |
| BOM-PARITY-0259 | bom | PARTIAL | Vrije keuze betekent: unsupported productie mag niet stil worden vrijgegeven. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1061) |
| BOM-PARITY-0260 | bom | PARTIAL | Houd de standaard-UI simpel met één `Hoofdmachine`. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1065) |
| BOM-PARITY-0261 | bom | PARTIAL | Onderliggend moet route-uitbreiding mogelijk zijn: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1067) |
| BOM-PARITY-0262 | bom | PARTIAL | op één of meerdere machines. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1073) |
| BOM-PARITY-0263 | bom | PARTIAL | Advanced details mogen `MachineRouteStep[]` tonen. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1075) |
| BOM-PARITY-0264 | bom | PARTIAL | Ontwerp logisch: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1079) |
| BOM-PARITY-0265 | bom | PARTIAL | Links: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1081) |
| BOM-PARITY-0266 | bom | PARTIAL | Links: machines; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1082) |
| BOM-PARITY-0267 | bom | PARTIAL | Links: aantal toegewezen onderdelen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1083) |
| BOM-PARITY-0268 | bom | PARTIAL | Links: totaal gewicht/lengte; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1084) |
| BOM-PARITY-0269 | bom | PARTIAL | Links: blockers. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1085) |
| BOM-PARITY-0270 | bom | PARTIAL | Midden: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1087) |
| BOM-PARITY-0271 | bom | PARTIAL | Midden: eenvoudige routingregels; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1088) |
| BOM-PARITY-0272 | bom | PARTIAL | Midden: prioriteit; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1089) |
| BOM-PARITY-0273 | bom | PARTIAL | Midden: Auto/Manual counts. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1090) |
| BOM-PARITY-0274 | bom | PARTIAL | Rechts: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1092) |
| BOM-PARITY-0275 | bom | PARTIAL | Rechts: niet toegewezen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1093) |
| BOM-PARITY-0276 | bom | PARTIAL | Rechts: review; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1094) |
| BOM-PARITY-0277 | bom | PARTIAL | Rechts: geblokkeerd; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1095) |
| BOM-PARITY-0278 | bom | PARTIAL | Rechts: uitleg "Waarom?". | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1096) |
| BOM-PARITY-0279 | bom | PARTIAL | Ondersteun drag/drop alleen als dit de bediening werkelijk eenvoudiger maakt. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1098) |
| BOM-PARITY-0280 | bom | PARTIAL | Gebruik dezelfde context action vanuit: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1104) |
| BOM-PARITY-0281 | bom | PARTIAL | Gebruik dezelfde context action vanuit: BOM; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1106) |
| BOM-PARITY-0282 | bom | PARTIAL | Gebruik dezelfde context action vanuit: Viewer contextmenu; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1107) |
| BOM-PARITY-0283 | bom | PARTIAL | Gebruik dezelfde context action vanuit: Project Tree; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1108) |
| BOM-PARITY-0284 | bom | PARTIAL | Gebruik dezelfde context action vanuit: geselecteerd onderdeel in Bewerken. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1109) |
| BOM-PARITY-0285 | bom | PARTIAL | Flow: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1111) |
| BOM-PARITY-0286 | bom | PARTIAL | Geen verkeerde optimizer door alleen naamherkenning. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1125) |
| BOM-PARITY-0287 | bom | PARTIAL | BOM toont: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1127) |
| BOM-PARITY-0288 | bom | PARTIAL | Afdrukken/exporteren van optimalisatierapport moet vanuit dezelfde scope mogelijk zijn. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1139) |
| BOM-PARITY-0289 | bom | PARTIAL | Dit is een harde upgrade. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1145) |
| BOM-PARITY-0290 | bom | PARTIAL | Review Snapshot: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1154) |
| BOM-PARITY-0291 | bom | PARTIAL | Review Snapshot: mag raster zijn; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1155) |
| BOM-PARITY-0292 | bom | PARTIAL | Review Snapshot: is visuele referentie; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1156) |
| BOM-PARITY-0293 | bom | PARTIAL | Review Snapshot: watermerk/status als review. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1157) |
| BOM-PARITY-0294 | bom | PARTIAL | Production Drawing: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1159) |
| BOM-PARITY-0295 | bom | PARTIAL | Production Drawing: **vector geometry verplicht**; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1160) |
| BOM-PARITY-0296 | bom | PARTIAL | Production Drawing: canonical exact/analytical geometry als bron; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1161) |
| BOM-PARITY-0297 | bom | PARTIAL | Production Drawing: geen viewer screenshot als geometrie-authority. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1162) |
| BOM-PARITY-0298 | bom | PARTIAL | Conceptueel: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1166) |
| BOM-PARITY-0299 | bom | PARTIAL | Verplicht: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1186) |
| BOM-PARITY-0300 | bom | PARTIAL | Verplicht: vectorlijnen blijven scherp bij 800%+ zoom; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1188) |
| BOM-PARITY-0301 | bom | PARTIAL | Verplicht: tekst als echte tekst/vector, niet gerasterd; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1189) |
| BOM-PARITY-0302 | bom | PARTIAL | Verplicht: embedded fonts waar praktisch/licentie-technisch toegestaan; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1190) |
| BOM-PARITY-0303 | bom | PARTIAL | Verplicht: fysieke lineweights in mm; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1191) |
| BOM-PARITY-0304 | bom | PARTIAL | Verplicht: consistente hidden/center/dimension line styles; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1192) |
| BOM-PARITY-0305 | bom | PARTIAL | Verplicht: hoogwaardige anti-aliasing in preview; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1193) |
| BOM-PARITY-0306 | bom | PARTIAL | Verplicht: geen jpeg-compressie op technische lijngeometrie; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1194) |
| BOM-PARITY-0307 | bom | PARTIAL | Verplicht: A4, A3, A2, A1, A0; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1195) |
| BOM-PARITY-0308 | bom | PARTIAL | Verplicht: portrait/landscape; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1196) |
| BOM-PARITY-0309 | bom | PARTIAL | Verplicht: Auto scale + handmatige schaal; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1197) |
| BOM-PARITY-0310 | bom | PARTIAL | Verplicht: Fit en Actual scale duidelijk gescheiden; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1198) |
| BOM-PARITY-0311 | bom | PARTIAL | Verplicht: vooraanzicht; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1199) |
| BOM-PARITY-0312 | bom | PARTIAL | Verplicht: bovenaanzicht; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1200) |
| BOM-PARITY-0313 | bom | PARTIAL | Verplicht: zij-/eindaanzicht; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1201) |
| BOM-PARITY-0314 | bom | PARTIAL | Verplicht: iso waar nuttig; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1202) |
| BOM-PARITY-0315 | bom | PARTIAL | Verplicht: sections/details waar nodig; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1203) |
| BOM-PARITY-0316 | bom | PARTIAL | Verplicht: maatvoering; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1204) |
| BOM-PARITY-0317 | bom | PARTIAL | Verplicht: gaten/slots/countersinks; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1205) |
| BOM-PARITY-0318 | bom | PARTIAL | Verplicht: verstek/end cuts; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1206) |
| BOM-PARITY-0319 | bom | PARTIAL | Verplicht: mark/part/assembly; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1207) |
| BOM-PARITY-0320 | bom | PARTIAL | Verplicht: profiel; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1208) |
| BOM-PARITY-0321 | bom | PARTIAL | Verplicht: materiaal; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1209) |
| BOM-PARITY-0322 | bom | PARTIAL | Verplicht: lengte; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1210) |
| BOM-PARITY-0323 | bom | PARTIAL | Verplicht: hoeveelheid; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1211) |
| BOM-PARITY-0324 | bom | PARTIAL | Verplicht: revision; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1212) |
| BOM-PARITY-0325 | bom | PARTIAL | Verplicht: status; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1213) |
| BOM-PARITY-0326 | bom | PARTIAL | Verplicht: project; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1214) |
| BOM-PARITY-0327 | bom | PARTIAL | Verplicht: company/logo template; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1215) |
| BOM-PARITY-0328 | bom | PARTIAL | Verplicht: pagina x/y; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1216) |
| BOM-PARITY-0329 | bom | PARTIAL | Verplicht: drawing/document hash. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1217) |
| BOM-PARITY-0330 | bom | PARTIAL | Een kleine shaded 3D-inset mag raster zijn, maar de productiegeometrie en maatvoering blijven vector. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1219) |
| BOM-PARITY-0331 | bom | PARTIAL | Auto layout moet: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1223) |
| BOM-PARITY-0332 | bom | PARTIAL | Auto layout moet: geen view afsnijden; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1225) |
| BOM-PARITY-0333 | bom | PARTIAL | Auto layout moet: schaal maximaal benutten; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1226) |
| BOM-PARITY-0334 | bom | PARTIAL | Auto layout moet: dimension collisions voorkomen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1227) |
| BOM-PARITY-0335 | bom | PARTIAL | Auto layout moet: tekst niet overlappen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1228) |
| BOM-PARITY-0336 | bom | PARTIAL | Auto layout moet: belangrijke views prioriteren; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1229) |
| BOM-PARITY-0337 | bom | PARTIAL | Auto layout moet: automatisch ander papierformaat of schaal voorstellen wanneer nodig; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1230) |
| BOM-PARITY-0338 | bom | PARTIAL | Auto layout moet: meerpagina-output ondersteunen voor complexe sets. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1231) |
| BOM-PARITY-0339 | bom | PARTIAL | Blokkeer productie-PDF bij minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1235) |
| BOM-PARITY-0340 | bom | PARTIAL | Voor PDF weergave in de applicatie: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1261) |
| BOM-PARITY-0341 | bom | PARTIAL | Voor PDF weergave in de applicatie: geen vaste lage-resolutie page bitmap; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1263) |
| BOM-PARITY-0342 | bom | PARTIAL | Voor PDF weergave in de applicatie: zoom-adaptive rendering; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1264) |
| BOM-PARITY-0343 | bom | PARTIAL | Voor PDF weergave in de applicatie: Fit Page; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1265) |
| BOM-PARITY-0344 | bom | PARTIAL | Voor PDF weergave in de applicatie: Fit Width; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1266) |
| BOM-PARITY-0345 | bom | PARTIAL | Voor PDF weergave in de applicatie: 100%; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1267) |
| BOM-PARITY-0346 | bom | PARTIAL | Voor PDF weergave in de applicatie: soepel pan/zoom; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1268) |
| BOM-PARITY-0347 | bom | PARTIAL | Voor PDF weergave in de applicatie: scherpe tekst/lijnen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1269) |
| BOM-PARITY-0348 | bom | PARTIAL | Voor PDF weergave in de applicatie: page navigation; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1270) |
| BOM-PARITY-0349 | bom | PARTIAL | Voor PDF weergave in de applicatie: thumbnails waar nuttig; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1271) |
| BOM-PARITY-0350 | bom | PARTIAL | Voor PDF weergave in de applicatie: print preview; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1272) |
| BOM-PARITY-0351 | bom | PARTIAL | Voor PDF weergave in de applicatie: actuele geselecteerde part/document context. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1273) |
| BOM-PARITY-0352 | bom | PARTIAL | Bij 100%, 200%, 400%, 800% zoom mag de preview geen onnodige blokkerige lijnweergave tonen wanneer de bron vector is. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1275) |
| BOM-PARITY-0353 | bom | PARTIAL | Maak één centrale service, conceptueel: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1281) |
| BOM-PARITY-0354 | bom | PARTIAL | Geen aparte printbusinesslogica per tab. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1290) |
| BOM-PARITY-0355 | bom | PARTIAL | Minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1294) |
| BOM-PARITY-0356 | bom | PARTIAL | Viewer: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1296) |
| BOM-PARITY-0357 | bom | PARTIAL | Viewer: current review view; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1297) |
| BOM-PARITY-0358 | bom | PARTIAL | Viewer: selected scope. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1298) |
| BOM-PARITY-0359 | bom | PARTIAL | BOM: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1300) |
| BOM-PARITY-0360 | bom | PARTIAL | BOM: huidige BOM; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1301) |
| BOM-PARITY-0361 | bom | PARTIAL | BOM: geselecteerde regels; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1302) |
| BOM-PARITY-0362 | bom | PARTIAL | BOM: geselecteerde productietekeningen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1303) |
| BOM-PARITY-0363 | bom | PARTIAL | BOM: machine worklist; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1304) |
| BOM-PARITY-0364 | bom | PARTIAL | BOM: optimalisatierapport; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1305) |
| BOM-PARITY-0365 | bom | PARTIAL | BOM: complete production document pack. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1306) |
| BOM-PARITY-0366 | bom | PARTIAL | Drawing/PDF: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1308) |
| BOM-PARITY-0367 | bom | PARTIAL | Drawing/PDF: huidige tekening; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1309) |
| BOM-PARITY-0368 | bom | PARTIAL | Drawing/PDF: batch drawings. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1310) |
| BOM-PARITY-0369 | bom | PARTIAL | Project: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1312) |
| BOM-PARITY-0370 | bom | PARTIAL | Project: complete geselecteerde projectdocumentset. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1313) |
| BOM-PARITY-0371 | bom | PARTIAL | Converter/Uitvoer: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1315) |
| BOM-PARITY-0372 | bom | PARTIAL | Converter/Uitvoer: printable generated artifacts. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1316) |
| BOM-PARITY-0373 | bom | PARTIAL | `Ctrl+P` opent een context-aware Output/Print Center. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1320) |
| BOM-PARITY-0374 | bom | PARTIAL | Toon: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1322) |
| BOM-PARITY-0375 | bom | PARTIAL | BOM PDF/print: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1340) |
| BOM-PARITY-0376 | bom | PARTIAL | BOM PDF/print: duidelijke titel; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1342) |
| BOM-PARITY-0377 | bom | PARTIAL | BOM PDF/print: project/revision/date; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1343) |
| BOM-PARITY-0378 | bom | PARTIAL | BOM PDF/print: logo; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1344) |
| BOM-PARITY-0379 | bom | PARTIAL | BOM PDF/print: scope/filter metadata; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1345) |
| BOM-PARITY-0380 | bom | PARTIAL | BOM PDF/print: repeating table header; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1346) |
| BOM-PARITY-0381 | bom | PARTIAL | BOM PDF/print: geen afgebroken tekst; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1347) |
| BOM-PARITY-0382 | bom | PARTIAL | BOM PDF/print: slimme kolombreedtes; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1348) |
| BOM-PARITY-0383 | bom | PARTIAL | BOM PDF/print: landscape/portrait auto; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1349) |
| BOM-PARITY-0384 | bom | PARTIAL | BOM PDF/print: page numbers; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1350) |
| BOM-PARITY-0385 | bom | PARTIAL | BOM PDF/print: groepstotalen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1351) |
| BOM-PARITY-0386 | bom | PARTIAL | BOM PDF/print: eindtotalen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1352) |
| BOM-PARITY-0387 | bom | PARTIAL | BOM PDF/print: machine-indeling optioneel zichtbaar; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1353) |
| BOM-PARITY-0388 | bom | PARTIAL | BOM PDF/print: blockers/status visueel duidelijk maar ook in tekst; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1354) |
| BOM-PARITY-0389 | bom | PARTIAL | BOM PDF/print: consistente typografie met de rest van CWS. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1355) |
| BOM-PARITY-0390 | bom | PARTIAL | Doel: modern, professioneel, rustig, technisch, duidelijk. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1361) |
| BOM-PARITY-0391 | bom | PARTIAL | Geen "dashboard om het dashboard". | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1363) |
| BOM-PARITY-0392 | bom | PARTIAL | Centraliseer: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1367) |
| BOM-PARITY-0393 | bom | PARTIAL | Gebruik één consistente Segoe UI/Windows-native typografische lijn waar mogelijk. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1384) |
| BOM-PARITY-0394 | bom | PARTIAL | Standaard gebruiker ziet alleen de meest gebruikte acties. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1388) |
| BOM-PARITY-0395 | bom | PARTIAL | Advanced: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1390) |
| BOM-PARITY-0396 | bom | PARTIAL | Advanced: machine capability details; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1391) |
| BOM-PARITY-0397 | bom | PARTIAL | Advanced: hashes; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1392) |
| BOM-PARITY-0398 | bom | PARTIAL | Advanced: solver evidence; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1393) |
| BOM-PARITY-0399 | bom | PARTIAL | Advanced: internal IDs; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1394) |
| BOM-PARITY-0400 | bom | PARTIAL | Advanced: diagnostics; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1395) |
| BOM-PARITY-0401 | bom | PARTIAL | zijn bereikbaar via Details/Advanced, niet standaard prominent. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1397) |
| BOM-PARITY-0402 | bom | PARTIAL | Niet prominent tonen: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1401) |
| BOM-PARITY-0403 | bom | PARTIAL | Tenzij in Diagnostics/About/Evidence. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1413) |
| BOM-PARITY-0404 | bom | PARTIAL | Screenshots van alle primaire schermen op: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1417) |
| BOM-PARITY-0405 | bom | PARTIAL | Controleer: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1426) |
| BOM-PARITY-0406 | bom | PARTIAL | Voer opnieuw de Full Product Acceptance control inventory uit. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1441) |
| BOM-PARITY-0407 | bom | PARTIAL | Inventariseer dynamisch: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1443) |
| BOM-PARITY-0408 | bom | PARTIAL | Per interactieve control: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1466) |
| BOM-PARITY-0409 | bom | PARTIAL | Een zichtbare interactieve control zonder echte functionele test: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1484) |
| BOM-PARITY-0410 | bom | PARTIAL | Een zichtbare actie met: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1490) |
| BOM-PARITY-0411 | bom | PARTIAL | Een zichtbare actie met: `pass`; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1492) |
| BOM-PARITY-0412 | bom | PARTIAL | Een zichtbare actie met: lege lambda; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1493) |
| BOM-PARITY-0413 | bom | PARTIAL | Een zichtbare actie met: alleen statuslabel wijzigen zonder functionele uitkomst; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1494) |
| BOM-PARITY-0414 | bom | PARTIAL | Een zichtbare actie met: TODO/NotImplemented; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1495) |
| BOM-PARITY-0415 | bom | PARTIAL | Een zichtbare actie met: swallow exception; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1496) |
| BOM-PARITY-0416 | bom | PARTIAL | is FAIL tenzij die control expliciet disabled en niet als functioneel productgedrag wordt aangeboden. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1498) |
| BOM-PARITY-0417 | bom | PARTIAL | Gebruik centrale commands zodat dezelfde actie hetzelfde werkt. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1504) |
| BOM-PARITY-0418 | bom | PARTIAL | Minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1506) |
| BOM-PARITY-0419 | bom | PARTIAL | Beschikbaar via: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1522) |
| BOM-PARITY-0420 | bom | PARTIAL | Beschikbaar via: Viewer contextmenu; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1524) |
| BOM-PARITY-0421 | bom | PARTIAL | Beschikbaar via: Project Tree contextmenu; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1525) |
| BOM-PARITY-0422 | bom | PARTIAL | Beschikbaar via: BOM toolbar/contextmenu; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1526) |
| BOM-PARITY-0423 | bom | PARTIAL | Beschikbaar via: Drawing/PDF context; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1527) |
| BOM-PARITY-0424 | bom | PARTIAL | Beschikbaar via: eventueel keyboard shortcuts. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1528) |
| BOM-PARITY-0425 | bom | PARTIAL | Resultaat moet dezelfde canonical selection gebruiken. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1530) |
| BOM-PARITY-0426 | bom | PARTIAL | Bouw/gebruik een Golden Test Library met: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1536) |
| BOM-PARITY-0427 | bom | PARTIAL | Voor ieder fixture: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1558) |
| BOM-PARITY-0428 | bom | PARTIAL | Real source files mogen lokaal als acceptance evidence worden gebruikt wanneer zij niet in Git mogen worden opgeslagen. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1572) |
| BOM-PARITY-0429 | bom | PARTIAL | Documenteer dan hash/path class zonder gevoelige inhoud te committen. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1574) |
| BOM-PARITY-0430 | bom | PARTIAL | Dit is bewust de minimale veilige fasering. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1580) |
| BOM-PARITY-0431 | bom | PARTIAL | Twee fasen is te riskant omdat Viewer/shell-fundament, productiehub/documentoutput en onafhankelijke eindacceptatie anders door elkaar lopen. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1582) |
| BOM-PARITY-0432 | bom | PARTIAL | Meer dan drie fasen is niet nodig als iedere fase groot en hard gated wordt uitgevoerd. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1584) |
| BOM-PARITY-0433 | bom | PARTIAL | Maak eerst de dagelijkse bediening perfect en snel. Geen uitgebreide nieuwe BOM/PDF-features bovenop een trage of complexe basis. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1592) |
| BOM-PARITY-0434 | bom | PARTIAL | bouw `validation/trimble_parity`; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1598) |
| BOM-PARITY-0435 | bom | PARTIAL | leg Trimble-reference vast; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1599) |
| BOM-PARITY-0436 | bom | PARTIAL | maak scripted input cases; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1600) |
| BOM-PARITY-0437 | bom | PARTIAL | capture screenshots/video/timing; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1601) |
| BOM-PARITY-0438 | bom | PARTIAL | maak parity matrix. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1602) |
| BOM-PARITY-0439 | bom | PARTIAL | Kalibreer: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1606) |
| BOM-PARITY-0440 | bom | PARTIAL | Kalibreer: mouse buttons; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1608) |
| BOM-PARITY-0441 | bom | PARTIAL | Kalibreer: orbit; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1609) |
| BOM-PARITY-0442 | bom | PARTIAL | Kalibreer: picked/selected pivot; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1610) |
| BOM-PARITY-0443 | bom | PARTIAL | Kalibreer: cursor zoom; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1611) |
| BOM-PARITY-0444 | bom | PARTIAL | Kalibreer: pan; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1612) |
| BOM-PARITY-0445 | bom | PARTIAL | Kalibreer: fit; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1613) |
| BOM-PARITY-0446 | bom | PARTIAL | Kalibreer: standard views; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1614) |
| BOM-PARITY-0447 | bom | PARTIAL | Kalibreer: perspective/orthographic; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1615) |
| BOM-PARITY-0448 | bom | PARTIAL | Kalibreer: world-up; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1616) |
| BOM-PARITY-0449 | bom | PARTIAL | Kalibreer: camera history; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1617) |
| BOM-PARITY-0450 | bom | PARTIAL | Kalibreer: Escape/cancel. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1618) |
| BOM-PARITY-0451 | bom | PARTIAL | entity-level picking; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1622) |
| BOM-PARITY-0452 | bom | PARTIAL | complete object highlight; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1623) |
| BOM-PARITY-0453 | bom | PARTIAL | stable occurrence identity; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1624) |
| BOM-PARITY-0454 | bom | PARTIAL | overlap cases; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1625) |
| BOM-PARITY-0455 | bom | PARTIAL | Ctrl multiselect; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1626) |
| BOM-PARITY-0456 | bom | PARTIAL | tree/BOM context sync. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1627) |
| BOM-PARITY-0457 | bom | PARTIAL | background; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1631) |
| BOM-PARITY-0458 | bom | PARTIAL | source colors; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1632) |
| BOM-PARITY-0459 | bom | PARTIAL | edges; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1633) |
| BOM-PARITY-0460 | bom | PARTIAL | lighting; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1634) |
| BOM-PARITY-0461 | bom | PARTIAL | shadow; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1635) |
| BOM-PARITY-0462 | bom | PARTIAL | transparency; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1636) |
| BOM-PARITY-0463 | bom | PARTIAL | selection; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1637) |
| BOM-PARITY-0464 | bom | PARTIAL | anti-aliasing; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1638) |
| BOM-PARITY-0465 | bom | PARTIAL | technical readability. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1639) |
| BOM-PARITY-0466 | bom | PARTIAL | Profile en verbeter: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1643) |
| BOM-PARITY-0467 | bom | PARTIAL | Profile en verbeter: import background jobs; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1645) |
| BOM-PARITY-0468 | bom | PARTIAL | Profile en verbeter: first pixels; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1646) |
| BOM-PARITY-0469 | bom | PARTIAL | Profile en verbeter: geometry cache; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1647) |
| BOM-PARITY-0470 | bom | PARTIAL | Profile en verbeter: progressive mesh; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1648) |
| BOM-PARITY-0471 | bom | PARTIAL | Profile en verbeter: scene index; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1649) |
| BOM-PARITY-0472 | bom | PARTIAL | Profile en verbeter: picking; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1650) |
| BOM-PARITY-0473 | bom | PARTIAL | Profile en verbeter: incremental visibility/selection; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1651) |
| BOM-PARITY-0474 | bom | PARTIAL | Profile en verbeter: selected exact upgrade; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1652) |
| BOM-PARITY-0475 | bom | PARTIAL | Profile en verbeter: workspace switching. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1653) |
| BOM-PARITY-0476 | bom | PARTIAL | Reduceer de hoofdworkflow tot: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1657) |
| BOM-PARITY-0477 | bom | PARTIAL | Interne/legacy schermen niet meer als losse top-level gebruikerskeuzes. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1667) |
| BOM-PARITY-0478 | bom | PARTIAL | Leg infrastructuur voor dezelfde actions vanuit Viewer/Tree/BOM. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1671) |
| BOM-PARITY-0479 | bom | PARTIAL | Alle required TP-Viewer cases die reference beschikbaar hebben PASS. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1687) |
| BOM-PARITY-0480 | bom | PARTIAL | Daarnaast: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1689) |
| BOM-PARITY-0481 | bom | PARTIAL | Niet COMPLETE zonder evidence. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1714) |
| BOM-PARITY-0482 | bom | PARTIAL | Commit logisch en klein binnen deze grote fase. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1716) |
| BOM-PARITY-0483 | bom | PARTIAL | Maak na de stabiele Viewer de complete dagelijkse productievoorbereiding eenvoudig vanuit één centrale BOM & Productie flow. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1724) |
| BOM-PARITY-0484 | bom | PARTIAL | all object families; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1730) |
| BOM-PARITY-0485 | bom | PARTIAL | quantities; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1731) |
| BOM-PARITY-0486 | bom | PARTIAL | totals; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1732) |
| BOM-PARITY-0487 | bom | PARTIAL | traceability; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1733) |
| BOM-PARITY-0488 | bom | PARTIAL | refresh after edit; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1734) |
| BOM-PARITY-0489 | bom | PARTIAL | save/reopen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1735) |
| BOM-PARITY-0490 | bom | PARTIAL | exports; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1736) |
| BOM-PARITY-0491 | bom | PARTIAL | no orphan/duplicates. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1737) |
| BOM-PARITY-0492 | bom | PARTIAL | Bouw subtabs: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1741) |
| BOM-PARITY-0493 | bom | PARTIAL | Realiseer: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1752) |
| BOM-PARITY-0494 | bom | PARTIAL | Automatisch na import en relevante edit. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1767) |
| BOM-PARITY-0495 | bom | PARTIAL | Volledig werkend: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1771) |
| BOM-PARITY-0496 | bom | PARTIAL | Profile Nesting voor lineaire profielen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1785) |
| BOM-PARITY-0497 | bom | PARTIAL | Plate Nesting voor platen waar ondersteund; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1786) |
| BOM-PARITY-0498 | bom | PARTIAL | machine/stock capability gates; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1787) |
| BOM-PARITY-0499 | bom | PARTIAL | resultaat terug in BOM. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1788) |
| BOM-PARITY-0500 | bom | PARTIAL | Vervang raster production-PDF authority door vector pipeline. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1792) |
| BOM-PARITY-0501 | bom | PARTIAL | De huidige PIL-generator mag alleen als review renderer blijven indien nuttig. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1794) |
| BOM-PARITY-0502 | bom | PARTIAL | zoom-adaptive; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1798) |
| BOM-PARITY-0503 | bom | PARTIAL | sharp vector display; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1799) |
| BOM-PARITY-0504 | bom | PARTIAL | fit page/width; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1800) |
| BOM-PARITY-0505 | bom | PARTIAL | smooth pan/zoom. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1801) |
| BOM-PARITY-0506 | bom | PARTIAL | Ctrl+P; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1805) |
| BOM-PARITY-0507 | bom | PARTIAL | Viewer print; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1806) |
| BOM-PARITY-0508 | bom | PARTIAL | BOM print; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1807) |
| BOM-PARITY-0509 | bom | PARTIAL | selected drawing pack; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1808) |
| BOM-PARITY-0510 | bom | PARTIAL | optimization report; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1809) |
| BOM-PARITY-0511 | bom | PARTIAL | machine worklist; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1810) |
| BOM-PARITY-0512 | bom | PARTIAL | project pack; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1811) |
| BOM-PARITY-0513 | bom | PARTIAL | vector PDF export. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1812) |
| BOM-PARITY-0514 | bom | PARTIAL | Minimaal WF-01 t/m WF-04 volledig. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1816) |
| BOM-PARITY-0515 | bom | PARTIAL | Voor golden fixtures: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1820) |
| BOM-PARITY-0516 | bom | PARTIAL | Bewijs dat niet alleen losse modules, maar het volledige pakket eenvoudig, snel en correct werkt. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1881) |
| BOM-PARITY-0517 | bom | PARTIAL | Geen grote nieuwe features meer tenzij een test een blocker blootlegt. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1883) |
| BOM-PARITY-0518 | bom | PARTIAL | Iedere interactieve control. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1887) |
| BOM-PARITY-0519 | bom | PARTIAL | Doel: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1889) |
| BOM-PARITY-0520 | bom | PARTIAL | Niet alleen source/dev runtime. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1897) |
| BOM-PARITY-0521 | bom | PARTIAL | Zelfde: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1899) |
| BOM-PARITY-0522 | bom | PARTIAL | Zelfde: model; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1900) |
| BOM-PARITY-0523 | bom | PARTIAL | Zelfde: hardware; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1901) |
| BOM-PARITY-0524 | bom | PARTIAL | Zelfde: DPI; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1902) |
| BOM-PARITY-0525 | bom | PARTIAL | Zelfde: input cases; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1903) |
| BOM-PARITY-0526 | bom | PARTIAL | Zelfde: performance metingen. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1904) |
| BOM-PARITY-0527 | bom | PARTIAL | Test meerdere echte: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1908) |
| BOM-PARITY-0528 | bom | PARTIAL | Test meerdere echte: IFC; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1910) |
| BOM-PARITY-0529 | bom | PARTIAL | Test meerdere echte: STEP; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1911) |
| BOM-PARITY-0530 | bom | PARTIAL | Test meerdere echte: NC1; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1912) |
| BOM-PARITY-0531 | bom | PARTIAL | Test meerdere echte: PDF; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1913) |
| BOM-PARITY-0532 | bom | PARTIAL | Test meerdere echte: project packages. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1914) |
| BOM-PARITY-0533 | bom | PARTIAL | Vanuit schone Windows install/portable: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1918) |
| BOM-PARITY-0534 | bom | PARTIAL | Minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1943) |
| BOM-PARITY-0535 | bom | PARTIAL | Controleer: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1956) |
| BOM-PARITY-0536 | bom | PARTIAL | Controleer: RAM drift; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1958) |
| BOM-PARITY-0537 | bom | PARTIAL | Controleer: handles; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1959) |
| BOM-PARITY-0538 | bom | PARTIAL | Controleer: threads; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1960) |
| BOM-PARITY-0539 | bom | PARTIAL | Controleer: Qt object leaks; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1961) |
| BOM-PARITY-0540 | bom | PARTIAL | Controleer: signal multiplication; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1962) |
| BOM-PARITY-0541 | bom | PARTIAL | Controleer: Viewer latency; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1963) |
| BOM-PARITY-0542 | bom | PARTIAL | Controleer: wrong picks; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1964) |
| BOM-PARITY-0543 | bom | PARTIAL | Controleer: stale selection; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1965) |
| BOM-PARITY-0544 | bom | PARTIAL | Controleer: crashes. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1966) |
| BOM-PARITY-0545 | bom | PARTIAL | Alle hoofdschermen 100/125/150/200% DPI. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1970) |
| BOM-PARITY-0546 | bom | PARTIAL | Verplicht: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1974) |
| BOM-PARITY-0547 | bom | PARTIAL | Verplicht: exact commit binding; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1976) |
| BOM-PARITY-0548 | bom | PARTIAL | Verplicht: GUI EXE; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1977) |
| BOM-PARITY-0549 | bom | PARTIAL | Verplicht: CLI EXE; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1978) |
| BOM-PARITY-0550 | bom | PARTIAL | Verplicht: one-folder runtime; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1979) |
| BOM-PARITY-0551 | bom | PARTIAL | Verplicht: fresh portable extract; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1980) |
| BOM-PARITY-0552 | bom | PARTIAL | Verplicht: PATH zonder dev Python; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1981) |
| BOM-PARITY-0553 | bom | PARTIAL | Verplicht: native imports; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1982) |
| BOM-PARITY-0554 | bom | PARTIAL | Verplicht: selftest; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1983) |
| BOM-PARITY-0555 | bom | PARTIAL | Verplicht: GUI smoke; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1984) |
| BOM-PARITY-0556 | bom | PARTIAL | Verplicht: installer; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1985) |
| BOM-PARITY-0557 | bom | PARTIAL | Verplicht: installed launch; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1986) |
| BOM-PARITY-0558 | bom | PARTIAL | Verplicht: file associations waar bedoeld; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1987) |
| BOM-PARITY-0559 | bom | PARTIAL | Verplicht: uninstall; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1988) |
| BOM-PARITY-0560 | bom | PARTIAL | Verplicht: checksums; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1989) |
| BOM-PARITY-0561 | bom | PARTIAL | Verplicht: SBOM. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1990) |
| BOM-PARITY-0562 | bom | PARTIAL | Maak/update: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L1994) |
| BOM-PARITY-0563 | bom | PARTIAL | Final PASS alleen als: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2023) |
| BOM-PARITY-0564 | bom | PARTIAL | Specifieke real-machine transfer blijft extern geblokkeerd zolang niet gekwalificeerd. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2043) |
| BOM-PARITY-0565 | bom | PARTIAL | Een actie telt pas als PASS als: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2049) |
| BOM-PARITY-0566 | bom | PARTIAL | Voor conversion: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2063) |
| BOM-PARITY-0567 | bom | PARTIAL | Voor BOM: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2074) |
| BOM-PARITY-0568 | bom | PARTIAL | Voor PDF: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2085) |
| BOM-PARITY-0569 | bom | PARTIAL | Minimaal: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2100) |
| BOM-PARITY-0570 | bom | PARTIAL | Fail closed, met duidelijke gebruikerstaal. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2133) |
| BOM-PARITY-0571 | bom | PARTIAL | Geen benchmark die alleen een interne functie timet. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2139) |
| BOM-PARITY-0572 | bom | PARTIAL | Meet: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2141) |
| BOM-PARITY-0573 | bom | PARTIAL | Maak latency regressions CI-gated waar stabiel genoeg. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2155) |
| BOM-PARITY-0574 | bom | PARTIAL | De simpelste correcte route wint. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2161) |
| BOM-PARITY-0575 | bom | PARTIAL | Voorkeur: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2163) |
| BOM-PARITY-0576 | bom | PARTIAL | Voorkeur: één primaire actie per scherm; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2165) |
| BOM-PARITY-0577 | bom | PARTIAL | Voorkeur: duidelijke secundaire acties; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2166) |
| BOM-PARITY-0578 | bom | PARTIAL | Voorkeur: weinig permanente knoppen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2167) |
| BOM-PARITY-0579 | bom | PARTIAL | Voorkeur: context actions voor selectie; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2168) |
| BOM-PARITY-0580 | bom | PARTIAL | Voorkeur: logisch groeperen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2169) |
| BOM-PARITY-0581 | bom | PARTIAL | Voorkeur: geen dubbele schermen voor dezelfde taak; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2170) |
| BOM-PARITY-0582 | bom | PARTIAL | Voorkeur: geen tech jargon in normale workflow; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2171) |
| BOM-PARITY-0583 | bom | PARTIAL | Voorkeur: duidelijke statuschips; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2172) |
| BOM-PARITY-0584 | bom | PARTIAL | Voorkeur: blockers direct klikbaar; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2173) |
| BOM-PARITY-0585 | bom | PARTIAL | Voorkeur: dezelfde actie overal dezelfde naam/icon; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2174) |
| BOM-PARITY-0586 | bom | PARTIAL | Voorkeur: geen modale dialoog wanneer inline/sidepanel eenvoudiger is; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2175) |
| BOM-PARITY-0587 | bom | PARTIAL | Voorkeur: wel bevestiging bij destructieve acties. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2176) |
| BOM-PARITY-0588 | bom | PARTIAL | Maak een automatische gate die nieuwe UI-controls detecteert. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2182) |
| BOM-PARITY-0589 | bom | PARTIAL | Als een nieuwe interactieve control geen `ui_test_id` en mapping heeft: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2184) |
| BOM-PARITY-0590 | bom | PARTIAL | Exclusion alleen: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2190) |
| BOM-PARITY-0591 | bom | PARTIAL | Streef naar: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2198) |
| BOM-PARITY-0592 | bom | PARTIAL | Binnen iedere grote fase meerdere logische commits toegestaan en gewenst. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2208) |
| BOM-PARITY-0593 | bom | PARTIAL | Voorbeelden: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2210) |
| BOM-PARITY-0594 | bom | PARTIAL | Geen megacommit waarin drie domeinen onleesbaar door elkaar lopen. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2225) |
| BOM-PARITY-0595 | bom | PARTIAL | Verboden om completion te halen door: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2231) |
| BOM-PARITY-0596 | bom | PARTIAL | Verboden om completion te halen door: tests te verwijderen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2233) |
| BOM-PARITY-0597 | bom | PARTIAL | Verboden om completion te halen door: expected outputs aan de bug aan te passen; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2234) |
| BOM-PARITY-0598 | bom | PARTIAL | Verboden om completion te halen door: requirement te hernoemen naar optional; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2235) |
| BOM-PARITY-0599 | bom | PARTIAL | Verboden om completion te halen door: hidden fallback naar projectscope; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2236) |
| BOM-PARITY-0600 | bom | PARTIAL | Verboden om completion te halen door: Viewer parity te claimen zonder Trimble evidence; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2237) |
| BOM-PARITY-0601 | bom | PARTIAL | Verboden om completion te halen door: screenshot existence als visual PASS te gebruiken; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2238) |
| BOM-PARITY-0602 | bom | PARTIAL | Verboden om completion te halen door: file existence als conversion PASS te gebruiken; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2239) |
| BOM-PARITY-0603 | bom | PARTIAL | Verboden om completion te halen door: BOM totalen alleen uit dezelfde functie opnieuw te berekenen als "independent" proof; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2240) |
| BOM-PARITY-0604 | bom | PARTIAL | Verboden om completion te halen door: PDF alleen op 300-dpi raster hoger op te slaan; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2241) |
| BOM-PARITY-0605 | bom | PARTIAL | Verboden om completion te halen door: machine capability checks over te slaan voor handmatige selectie; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2242) |
| BOM-PARITY-0606 | bom | PARTIAL | Verboden om completion te halen door: direct machine transfer aan te zetten; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2243) |
| BOM-PARITY-0607 | bom | PARTIAL | Verboden om completion te halen door: UI knop te verbergen alleen om coverage te halen wanneer de functie required is; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2244) |
| BOM-PARITY-0608 | bom | PARTIAL | Verboden om completion te halen door: legacy duplicate UI in productie te laten staan als een simpeler canonical scherm bestaat; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2245) |
| BOM-PARITY-0609 | bom | PARTIAL | Verboden om completion te halen door: performance target te halen door objecten/features niet te laden. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2246) |
| BOM-PARITY-0610 | bom | PARTIAL | Als gebruiker zegt: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2252) |
| BOM-PARITY-0611 | bom | PARTIAL | Dan: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2260) |
| BOM-PARITY-0612 | bom | PARTIAL | Dan: 1. fetch current canonical HEAD; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2262) |
| BOM-PARITY-0613 | bom | PARTIAL | Dan: 2. lees actieve phase checklist; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2263) |
| BOM-PARITY-0614 | bom | PARTIAL | Dan: 3. kies eerste required non-PASS item; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2264) |
| BOM-PARITY-0615 | bom | PARTIAL | Dan: 4. reproduceer/test; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2265) |
| BOM-PARITY-0616 | bom | PARTIAL | Dan: 5. fix; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2266) |
| BOM-PARITY-0617 | bom | PARTIAL | Dan: 6. voeg regression test/evidence toe; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2267) |
| BOM-PARITY-0618 | bom | PARTIAL | Dan: 7. voer relevante subsystem tests uit; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2268) |
| BOM-PARITY-0619 | bom | PARTIAL | Dan: 8. voer impacted E2E uit; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2269) |
| BOM-PARITY-0620 | bom | PARTIAL | Dan: 9. update checklist/matrices; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2270) |
| BOM-PARITY-0621 | bom | PARTIAL | Dan: 10. commit logisch; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2271) |
| BOM-PARITY-0622 | bom | PARTIAL | Dan: 11. ga door naar volgende non-PASS. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2272) |
| BOM-PARITY-0623 | bom | PARTIAL | Niet opnieuw vragen welke fase bedoeld wordt wanneer checklist dit ondubbelzinnig bepaalt. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2274) |
| BOM-PARITY-0624 | bom | PARTIAL | De gewenste eindsituatie is niet alleen: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2280) |
| BOM-PARITY-0625 | bom | PARTIAL | De eindsituatie is: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2286) |
| BOM-PARITY-0626 | bom | PARTIAL | De enige expliciet externe boundary blijft specifieke echte machine/controllerqualification. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2311) |
| BOM-PARITY-0627 | bom | PARTIAL | Zonder echte machine-evidence: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2313) |
| BOM-PARITY-0628 | bom | PARTIAL | blijft correct. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2319) |
| BOM-PARITY-0629 | bom | PARTIAL | Begin niet meteen te bouwen. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2325) |
| BOM-PARITY-0630 | bom | PARTIAL | Doe eerst op de actuele canonical HEAD: | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2327) |
| BOM-PARITY-0631 | bom | PARTIAL | Doe eerst op de actuele canonical HEAD: 1. repo/status audit; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2329) |
| BOM-PARITY-0632 | bom | PARTIAL | Doe eerst op de actuele canonical HEAD: 2. Trimble-reference availability audit; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2330) |
| BOM-PARITY-0633 | bom | PARTIAL | Doe eerst op de actuele canonical HEAD: 3. Viewer/profile baseline; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2331) |
| BOM-PARITY-0634 | bom | PARTIAL | Doe eerst op de actuele canonical HEAD: 4. BOM current-state audit; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2332) |
| BOM-PARITY-0635 | bom | PARTIAL | Doe eerst op de actuele canonical HEAD: 5. drawing/PDF current-state audit; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2333) |
| BOM-PARITY-0636 | bom | PARTIAL | Doe eerst op de actuele canonical HEAD: 6. machine-routing current-state audit; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2334) |
| BOM-PARITY-0637 | bom | PARTIAL | Doe eerst op de actuele canonical HEAD: 7. UI clutter/control audit; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2335) |
| BOM-PARITY-0638 | bom | PARTIAL | Doe eerst op de actuele canonical HEAD: 8. maak de Phase 1/2/3 checklists met bestaande PASS-items en echte gaps; | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2336) |
| BOM-PARITY-0639 | bom | PARTIAL | Doe eerst op de actuele canonical HEAD: 9. bouw daarna direct Phase 1 af volgens eerste non-PASS item. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2337) |
| BOM-PARITY-0640 | bom | PARTIAL | Geef geen 100%-claim op basis van implementatie alleen. | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2339) |
| BOM-PARITY-0641 | bom | PARTIAL | **Evidence is de productstatus.** | requirements/sources/CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md (L2341) |
| RECOGNITION-REAL-0001 | recognition_conversion | PARTIAL | Deze wijziging bouwt voort op `1d83feaca1bc9b9f21e0e7cdc69db0933b9e6008`. De bestaande project-, BOM-, materiaal- en machinevrijgavepaden blijven leidend. De oorspronkelijke klantbijlagen en de private verwachtingen zijn **niet** in het openbare repository opgenomen. Tests in het repository maken eigen fixtures. | docs/REAL_FILE_RECOGNITION_REPAIR.md (L3) |
| RECOGNITION-REAL-0002 | recognition_conversion | PARTIAL | Audit-ID \| Gewijzigd gedrag \| Negatieve bescherming | docs/REAL_FILE_RECOGNITION_REPAIR.md (L10) |
| RECOGNITION-REAL-0003 | recognition_conversion | PARTIAL | STEP-01 \| Volledige occurrence-paden; ieder hergebruikt samenstellingsexemplaar krijgt eigen bladonderdelen en samengestelde wereldplaatsing. \| Cycli en onbegrensde expansie worden afgewezen; geen aantallen uit bestandsnamen. | docs/REAL_FILE_RECOGNITION_REPAIR.md (L12) |
| RECOGNITION-REAL-0004 | recognition_conversion | PARTIAL | STEP-02 \| Witruimte wordt verwijderd vóór naamterugval; productnamen en volledige exemplaarpaden blijven bewaard. \| Geen lege weergavenaam wanneer een bronproductnaam bestaat. | docs/REAL_FILE_RECOGNITION_REPAIR.md (L13) |
| RECOGNITION-REAL-0005 | recognition_conversion | PARTIAL | STEP-03 \| Geometrisch bewezen maatwerkdoorsneden krijgen een reproduceerbare CUSTOM-naam en doorsnedegegevens. \| Dit is geen fictieve catalogusmatch; onbekende materiaalgrade blijft onbekend. | docs/REAL_FILE_RECOGNITION_REPAIR.md (L14) |
| RECOGNITION-REAL-0006 | recognition_conversion | PARTIAL | STEP-04 \| Native componentselectie via de oorspronkelijke Part-21-entiteitslabels, inclusief complex samengestelde records. Referenties blijven apart. \| Selectie niet op lijstvolgorde; bronhash, geselecteerde rootgrafiek en onderdeelidentiteit moeten overeenkomen. | docs/REAL_FILE_RECOGNITION_REPAIR.md (L15) |
| RECOGNITION-REAL-0007 | recognition_conversion | PARTIAL | STEP-05 \| Ook zelfstandige rootproducten naast samenstellingen worden meegenomen. \| Geen stille uitsluiting van losse top-level volumes. | docs/REAL_FILE_RECOGNITION_REPAIR.md (L16) |
| RECOGNITION-REAL-0008 | recognition_conversion | PARTIAL | PDF-01 \| Gelabelde assemblagestuklijsten worden ruimtelijk gescheiden van tolerantie-/titelblokken. \| DIN of PART NUMBER is geen profiel; onvolledige rijen worden niet goedgekeurd. | docs/REAL_FILE_RECOGNITION_REPAIR.md (L17) |
| RECOGNITION-REAL-0009 | recognition_conversion | PARTIAL | DXF-01 \| Model-contouren/boringen onder INSERT-blokken worden gekoppeld aan de expliciete layout-stuklijst, grade, dikte, aantallen en samenstellingsmerken. \| Geen standaardgrade, onbekende units, niet-sluitende aantallen, meerdere ambigu gekoppelde delen of stille contourbenadering. | docs/REAL_FILE_RECOGNITION_REPAIR.md (L18) |
| RECOGNITION-REAL-0010 | recognition_conversion | PARTIAL | IFC-01 \| Expliciete Tekla Part mark wordt het positienummer; technische Tag blijft bronidentiteit. \| Een technisch ID overschrijft geen expliciet posmerk. | docs/REAL_FILE_RECOGNITION_REPAIR.md (L19) |
| RECOGNITION-REAL-0011 | recognition_conversion | PARTIAL | IFC-02 \| Expliciet metselwerk blijft bronmateriaal en wordt bouwkundige context. \| Tegenspraak met een bekende metaalgrade blijft een conflict; geen staalproductievrijgave. | docs/REAL_FILE_RECOGNITION_REPAIR.md (L20) |
| RECOGNITION-REAL-0012 | recognition_conversion | PARTIAL | NC-01 \| Volledige canonieke NC1-payload blijft behouden; oorspronkelijke profielparameters krijgen onafhankelijk lokaal BREP-bewijs. \| Bronpayload wordt eerst met de oorspronkelijke NC1-attachment vergeleken; geen gedwongen catalogusmatch. | docs/REAL_FILE_RECOGNITION_REPAIR.md (L21) |
| RECOGNITION-REAL-0013 | recognition_conversion | PARTIAL | NC-02 \| Een ontbrekende lokale bewerking kan niet door een kleine globale volumeverhouding worden verborgen. Bronboringen worden één-op-één op diameter, as, wandzijde en positie gekoppeld. \| Een ontbrekende, extra of afwijkende boring blokkeert; een eenvoudiger maar niet-bewezen hypothese wint niet. | docs/REAL_FILE_RECOGNITION_REPAIR.md (L22) |
| RECOGNITION-REAL-0014 | recognition_conversion | PARTIAL | NC-03 \| Vereenvoudigde geometrie van NC1-inkoopartikelen blijft expliciet een proxy. \| Geen verzonnen draad/binnengat of CNC-geschiktheid. | docs/REAL_FILE_RECOGNITION_REPAIR.md (L23) |
| RECOGNITION-REAL-0015 | recognition_conversion | PARTIAL | TEST-01 \| Private, hash-gebonden acceptatierunner en publieke synthetische regressies zijn toegevoegd. \| Source-runtime-controle is geen afname van een nieuwe geïnstalleerde Windows-EXE met de private bijlagen. | docs/REAL_FILE_RECOGNITION_REPAIR.md (L24) |
| RECOGNITION-REAL-0016 | recognition_conversion | PARTIAL | `tools/verify_private_recognition_set.py` accepteert een manifest buiten het repository. Elk bestand bevat `file`, `sha256` en een niet-lege `expected` map. De verwachtingen moeten onafhankelijk uit de bron of geaccordeerde referentie komen; nooit uit de te testen uitvoer worden gegenereerd. | docs/REAL_FILE_RECOGNITION_REPAIR.md (L28) |
| RECOGNITION-REAL-0017 | recognition_conversion | PARTIAL | De uitvoer bevat alle afwijkingen, ongewijzigde bronhashes, bron/runtime-identiteit, selectie- en herkenningsresultaten en controle na opslaan/heropenen. Uitvoer blijft in de opgegeven private map. Een fout of ontbrekende verwachting wordt geen PASS. | docs/REAL_FILE_RECOGNITION_REPAIR.md (L37) |
| RECOGNITION-REAL-0018 | recognition_conversion | PARTIAL | Voor door IFC als solid verklaarde Body-geometrie kunnen losse native BREP-vlakken zonder toegevoegde geometrie tot één gesloten shell worden samengevoegd. Vrije, meervoudige of verwijderde randen/vlakken, meerdere shells, gewijzigd oppervlak of een ongeldig volume worden afgewezen. Een open referentieoppervlak wordt hiermee niet stilzwijgend tot maakdeel omgezet; de meshfallback blijft apart. | docs/REAL_FILE_RECOGNITION_REPAIR.md (L43) |
| RECOGNITION-REAL-0019 | recognition_conversion | PARTIAL | Een correcte naam, aantal, profiel of contour is geen automatische productievrijgave. Ontbrekende grades, complexe/buiten de ondersteunde route vallende documenten, referentieoppervlakken, inkoopproxies en machinekwalificatie blijven afzonderlijk zichtbaar. Bestaande projecten met oude of gewijzigde bronselectorgrafieken moeten opnieuw via het revisie-/importpad worden ingelezen; de nieuwe validator accepteert geen oude grafiekhash op basis van een toevallige geometriepositie. | docs/REAL_FILE_RECOGNITION_REPAIR.md (L51) |
| RECOGNITION-REAL-0020 | recognition_conversion | PARTIAL | De GitHub-workflow test de exacte commit op Windows met publieke synthetische fixtures, strikte acceptatie en het bestaande herkenningscorpus. De private set wordt afzonderlijk lokaal uitgevoerd. Een nieuwe installer en private Windows-/ GUI-afname zijn niet door alleen deze broncommit bewezen. | docs/REAL_FILE_RECOGNITION_REPAIR.md (L58) |
| RECOGNITION-0001 | recognition_conversion | PARTIAL | Iedere ingelezen modelcomponent moet expliciet behandeld worden: herkend met herleidbaar bewijs, als kandidaat aangeboden, of als onopgelost/geconflicteerd geblokkeerd. Het programma mag geen staalsoort, aluminiumtoestand, materiaalsterkte of dichtheid verzinnen omdat een geometrie op een bekend extrusieprofiel lijkt. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L5) |
| RECOGNITION-0002 | recognition_conversion | PARTIAL | Een geometrisch bewezen profiel is niet hetzelfde als een bewezen materiaalkwaliteit. Een 100% geslaagde acceptatiesuite bewijst alleen de omschreven regressiegevallen, niet dat elk wereldwijd materiaal of willekeurig beschadigd model automatisch herkend wordt. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L7) |
| RECOGNITION-0003 | recognition_conversion | PARTIAL | Onderdeel \| Implementatie en controle | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L11) |
| RECOGNITION-0004 | recognition_conversion | PARTIAL | Materiaalcatalogus en resolver \| `materials.json`, `material_database.py`, `cws_convertor/material_resolution.py`: exacte codes, expliciete aliassen, confidence, reden en bron; onbekend blijft onbekend. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L13) |
| RECOGNITION-0005 | recognition_conversion | PARTIAL | Hoeveelheden en massa \| `quantities.py`: geen stilzwijgende staalfallback; massa alleen wanneer materiaal en toegestane dichtheid beschikbaar zijn. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L14) |
| RECOGNITION-0006 | recognition_conversion | PARTIAL | IFC-bronnen \| `cws_convertor/importers/ifc_project.py`: bronrelaties, type-informatie, materiaalstructuren en conflicten; herkomst wordt bewaard. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L15) |
| RECOGNITION-0007 | recognition_conversion | PARTIAL | Native IFC-materiaalbinding \| `ifc_native.py`: materiaal per object binden; geen eerste-declaratie-fallback, geen staaletiket voor aluminium en geen verzonnen materiaal bij leeg bronveld. De serializer-unitcontrole is geen native CAD-geometriebewijs. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L16) |
| RECOGNITION-0008 | recognition_conversion | PARTIAL | Classificatie bij import \| `cws_convertor/project/service.py` en `classification.py`: classificatie na semantische import; onderscheiden beoordeling, bevestiging en conflicten. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L17) |
| RECOGNITION-0009 | recognition_conversion | PARTIAL | STEP en extrusies \| `cws_convertor/manufacturing_interpreter/` en `importers/step_project.py`: geometrie/profielherkenning apart van materiaalbewijs; stabiele bronbinding en cache; onveilige promotie blokkeren. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L18) |
| RECOGNITION-0010 | recognition_conversion | PARTIAL | Conversieroutes zonder stilzwijgende defaults \| CLI, applicatie, conversieservice, IFC-conversie en viewer-roundtrip: bronmateriaal of expliciete gebruikerstoewijzing behouden; een leeg veld wordt geen standaardstaal. Pure dispatch-/beleidtests zijn gescheiden van werkelijke CAD-conversies. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L19) |
| RECOGNITION-0011 | recognition_conversion | PARTIAL | Veilige NC1-uitvoer \| STEP→NC1 valideert in staging op hetzelfde bestandssysteem en vervangt het doel pas na succes. Fouten behouden bestaande uitvoer; bron en doel mogen geen identiek bestand zijn. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L20) |
| RECOGNITION-0012 | recognition_conversion | PARTIAL | PDF/DXF-kandidaten \| `cws_convertor/importers/source_material_evidence.py`: tekst/metadata met bronlocatie; geen materiaalkwaliteit afleiden uit kleur of geometrie. Kandidaten vragen beoordeling. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L21) |
| RECOGNITION-0013 | recognition_conversion | PARTIAL | Materiaalreview \| `cws_convertor/ui/material_review.py` en Qt-werkruimte: bewijs, cataloguskandidaten, reden, bevestigen/afwijzen, bulkpreview en bewaakte undo. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L22) |
| RECOGNITION-0014 | recognition_conversion | PARTIAL | Productievrijgave \| Workbench- en exportgates: materiaal/profielbevestiging, confidence, productie-identiteit en bestaande geometrie-/roundtripvoorwaarden. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L23) |
| RECOGNITION-0015 | recognition_conversion | PARTIAL | Reproduceerbare controle \| `tools/run_material_model_recognition_acceptance.py`: subprocess per suite, JSON per test, logs, dependencies en bronfingerprint. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L24) |
| RECOGNITION-0016 | recognition_conversion | PARTIAL | De geselecteerde STEP-herkenning is beschikbaar via **Bewerken → Extra info → STEP-profiel herkennen**. De achtergrondtaak werkt op een losse projectsnapshot; wijzigingen worden alleen op de UI-thread overgenomen als project, onderdeel en bron nog overeenkomen. Gestarte Workbench-revisies en bevestigde onderdelen worden behouden. Het service-equivalent is `ProjectSession.recognize_deferred_step_sources(...)` en de gelijknamige methode op `ProjectService` voor een projectpad. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L26) |
| RECOGNITION-0017 | recognition_conversion | PARTIAL | De IFC-tessellatieserializer schrijft bij onbekend materiaal geen fictieve materiaalrelatie. De bijbehorende lichte lezer volgt per object de expliciete materiaalrelatie; een eerste materiaaldeclaratie wordt niet over alle objecten verspreid. Catalogusdichtheden en andere materiaalwaarden zijn nominale rekengegevens, geen materiaalcertificaat of constructieve geschiktheidsverklaring. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L28) |
| RECOGNITION-0018 | recognition_conversion | PARTIAL | Materiaalafhankelijke NC1-massa en de omrekening van brongewicht naar profieloppervlakte gebruiken de gevonden dichtheid. Ontbrekende betrouwbare dichtheid blokkeert een noodzakelijke massaomrekening. Een nulgewicht uit NC1 blijft in het geïmporteerde profiel nul. Bestaande geometrische profielcatalogi kunnen nominale staalmassa bevatten; die waarde is op zichzelf geen bronmateriaalbewijs. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L30) |
| RECOGNITION-0019 | recognition_conversion | PARTIAL | Dit document beschrijft het werkpakket. De actuele aantoonbare teststatus staat uitsluitend in de gegenereerde `FINAL_ACCEPTANCE.json` van de te leveren bronrevisie. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L32) |
| RECOGNITION-0020 | recognition_conversion | PARTIAL | Gebruik de bestaande repo, Python 3.12 x64 en een eigen virtuele omgeving. Installeer geen willekeurige nieuwere CAD-versies naast de lock. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L36) |
| RECOGNITION-0021 | recognition_conversion | PARTIAL | De runner gebruikt de actuele Python-interpreter en controleert echte imports van CadQuery, OCP, IfcOpenShell, PySide6, PyMuPDF, ezdxf, ReportLab, pypdf en NumPy. De CI-workflow `material-model-recognition.yml` voert dezelfde strikte opdracht uit op Windows en uploadt het bewijs ook bij een mislukte test of dependency-installatie. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L44) |
| RECOGNITION-0022 | recognition_conversion | PARTIAL | De bestaande workflows `final-release-proof.yml` en `build-product-ui-reintegration-exe.yml` vereisen deze strikte gate eveneens vóór hun verpakkingsstappen. Zij schrijven naar `build/material_model_recognition/`, zodat een CI-run niet de meegeleverde lokale validatiebestanden overschrijft. Een geblokkeerde herkenningsgate stopt daar de installatiebuild; bewijs wordt ook bij fouten geüpload. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L46) |
| RECOGNITION-0023 | recognition_conversion | PARTIAL | Een gerichte ontwikkelcontrole kan wel, maar is nooit volledige acceptatie: | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L48) |
| RECOGNITION-0024 | recognition_conversion | PARTIAL | Een geslaagde selectie geeft `SUBSET_PASS`, `acceptance_passed: false` en percentages met de volledige manifestnoemer. `--require-native` mag niet met `--suite` worden gecombineerd. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L54) |
| RECOGNITION-0025 | recognition_conversion | PARTIAL | Standaard komen de resultaten onder `validation/material_model_recognition/`: | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L58) |
| RECOGNITION-0026 | recognition_conversion | PARTIAL | Standaard komen de resultaten onder `validation/material_model_recognition/`: Bestand/map \| Betekenis | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L60) |
| RECOGNITION-0027 | recognition_conversion | PARTIAL | Standaard komen de resultaten onder `validation/material_model_recognition/`: `FINAL_ACCEPTANCE.json` \| Volledige status, suite- en testaantallen, percentages per gebied, blokkades, runtime en bronbinding. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L62) |
| RECOGNITION-0028 | recognition_conversion | PARTIAL | Standaard komen de resultaten onder `validation/material_model_recognition/`: `SOURCE_FINGERPRINT.json` \| Git-SHA, branch en SHA256 van bronbestanden, inclusief nog niet gecommitteerde bronwijzigingen. Gegenereerde validatiebestanden tellen niet mee in de bronhash. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L63) |
| RECOGNITION-0029 | recognition_conversion | PARTIAL | Standaard komen de resultaten onder `validation/material_model_recognition/`: `DEPENDENCIES.json` \| Werkelijke importresultaten; een aanwezige maar defecte module telt niet als beschikbaar. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L64) |
| RECOGNITION-0030 | recognition_conversion | PARTIAL | Standaard komen de resultaten onder `validation/material_model_recognition/`: `suites/*.json` \| Werkelijke uitkomsten per testmethode/functie, inclusief fout-, skip- en fixture-events. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L65) |
| RECOGNITION-0031 | recognition_conversion | PARTIAL | Standaard komen de resultaten onder `validation/material_model_recognition/`: `logs/*.log` \| Uitvoer en fouten per geïsoleerde testsuite. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L66) |
| RECOGNITION-0032 | recognition_conversion | PARTIAL | Standaard komen de resultaten onder `validation/material_model_recognition/`: `screenshots/` \| Echte UI-captures wanneer de UI-tests deze produceren; geen gegenereerde voorbeeldafbeeldingen als testbewijs gebruiken. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L67) |
| RECOGNITION-0033 | recognition_conversion | PARTIAL | Rekenregels: | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L69) |
| RECOGNITION-0034 | recognition_conversion | PARTIAL | Rekenregels: Suitepercentage = geslaagde suites / alle verplichte suites in het vaste manifest × 100. Geblokkeerde, ontbrekende en niet-geselecteerde suites blijven in de noemer. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L71) |
| RECOGNITION-0035 | recognition_conversion | PARTIAL | Rekenregels: Uitgevoerde-testpercentage = geslaagde logische tests / werkelijk uitgevoerde logische tests × 100. Subtestfouten worden afzonderlijk geregistreerd en tellen niet als extra uitgevoerde testmethoden. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L72) |
| RECOGNITION-0036 | recognition_conversion | PARTIAL | Rekenregels: Een geblokkeerde suite krijgt geen verzonnen testaantal. Daardoor kan het uitgevoerde-testpercentage 100% zijn terwijl het suitepercentage lager is en de totale acceptatie niet is geslaagd. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L73) |
| RECOGNITION-0037 | recognition_conversion | PARTIAL | Rekenregels: `SKIPPED`, expected failures, nul ontdekte tests, importfouten, time-outs en ontbrekende native afhankelijkheden zijn nooit `PASS`. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L74) |
| RECOGNITION-0038 | recognition_conversion | PARTIAL | Rekenregels: Een gewijzigde bronfingerprint tijdens de run maakt de run ongeldig. Stop parallelle bronwijzigingen vóór de definitieve acceptatierun. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L75) |
| RECOGNITION-0039 | recognition_conversion | PARTIAL | Rekenregels: De runner controleert tevens dat een oud resultaatsbestand niet als nieuw bewijs hergebruikt wordt wanneer een subprocess geen resultaat schrijft. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L76) |
| RECOGNITION-0040 | recognition_conversion | PARTIAL | De exacte testnamen zijn leidend in de `SUITES`-manifest van de runner. Het pakket bestrijkt: | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L80) |
| RECOGNITION-0041 | recognition_conversion | PARTIAL | De exacte testnamen zijn leidend in de `SUITES`-manifest van de runner. Het pakket bestrijkt: 1. Bekende exacte materiaalcode, expliciete alias en onbekende/incomplete code; geen impliciete default. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L82) |
| RECOGNITION-0042 | recognition_conversion | PARTIAL | De exacte testnamen zijn leidend in de `SUITES`-manifest van de runner. Het pakket bestrijkt: 2. Staal, RVS, aluminium, bevestigingsklassen, hout, beton en kunststoffen; geblokkeerde massa als de dichtheid onvoldoende is onderbouwd. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L83) |
| RECOGNITION-0043 | recognition_conversion | PARTIAL | De exacte testnamen zijn leidend in de `SUITES`-manifest van de runner. Het pakket bestrijkt: 3. IFC-materiaalrelaties, type-overerving, samengestelde materialen, conflicten en semantische import. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L84) |
| RECOGNITION-0044 | recognition_conversion | PARTIAL | De exacte testnamen zijn leidend in de `SUITES`-manifest van de runner. Het pakket bestrijkt: 4. STEP zonder materiaalbewijs, bronhashcontrole, uitgestelde geometrieherkenning en veilige MGI-promotie. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L85) |
| RECOGNITION-0045 | recognition_conversion | PARTIAL | De exacte testnamen zijn leidend in de `SUITES`-manifest van de runner. Het pakket bestrijkt: 5. Doorsneden met segmentatie, gaten, bogen en niet-standaardvormen; onduidelijke vormen blijven onopgelost/CUSTOM. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L86) |
| RECOGNITION-0046 | recognition_conversion | PARTIAL | De exacte testnamen zijn leidend in de `SUITES`-manifest van de runner. Het pakket bestrijkt: 6. Importclassificatie en projectpersistentie, ontbrekende materiaal/profielbevestiging en vrijgaveblokkades. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L87) |
| RECOGNITION-0047 | recognition_conversion | PARTIAL | De exacte testnamen zijn leidend in de `SUITES`-manifest van de runner. Het pakket bestrijkt: 7. PDF/DXF-tekst als kandidaat, conflicterende materiaalnamen en uitgesloten kleur-/geometrie-inferentie. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L88) |
| RECOGNITION-0048 | recognition_conversion | PARTIAL | De exacte testnamen zijn leidend in de `SUITES`-manifest van de runner. Het pakket bestrijkt: 8. Materiaalreview, bulkpreview, expliciete reden, bevestigen/afwijzen, stale-state-bewaking en undo. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L89) |
| RECOGNITION-0049 | recognition_conversion | PARTIAL | De exacte testnamen zijn leidend in de `SUITES`-manifest van de runner. Het pakket bestrijkt: 9. Native CAD-herkenning, canonieke roundtrip en de werkelijke Qt-reviewwerkruimte. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L90) |
| RECOGNITION-0050 | recognition_conversion | PARTIAL | De exacte testnamen zijn leidend in de `SUITES`-manifest van de runner. Het pakket bestrijkt: 10. De acceptatierunner zelf: fout- en skipdetectie, exacte telling, bronfingerprint en bescherming tegen oud bewijs. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L91) |
| RECOGNITION-0051 | recognition_conversion | PARTIAL | De exacte testnamen zijn leidend in de `SUITES`-manifest van de runner. Het pakket bestrijkt: 11. Projectmodel, opslag/heropenen, BOM, projectservice, semantische service en uniform projectschema als regressievoorwaarden. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L92) |
| RECOGNITION-0052 | recognition_conversion | PARTIAL | De exacte testnamen zijn leidend in de `SUITES`-manifest van de runner. Het pakket bestrijkt: 12. Productienormalisatie: bronmetrics en expliciete vrijgavevoorwaarden; drie niet-native controles plus twee werkelijke native metricfixtures. Zonder CAD blijven die twee native checks expliciet overgeslagen en de suite onvolledig. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L93) |
| RECOGNITION-0053 | recognition_conversion | PARTIAL | De exacte testnamen zijn leidend in de `SUITES`-manifest van de runner. Het pakket bestrijkt: 13. Stille materiaaldefaults in CLI/GUI/helpers en IFC-conversiebeleid; afzonderlijke native conversiecontroles voor het daadwerkelijk gegenereerde model. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L94) |
| RECOGNITION-0054 | recognition_conversion | PARTIAL | De aanvullende native PDF-modelgate bouwt een echte STEP-fixture en controleert dat import zonder materiaalkwaliteit concept/onopgelost blijft, terwijl een expliciet opgegeven catalogusmateriaal met herkomst behouden blijft. PDF-tekstanalyse heeft geen CAD-kernel nodig en wordt afzonderlijk getest. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L96) |
| RECOGNITION-0055 | recognition_conversion | PARTIAL | Voor een visuele oplevering zijn echte, actuele screenshots nodig van minimaal: de bronbewijstabel en reviewwachtrij, een bekende en onbekende kandidaat, bulkpreview, bevestiging, afwijzing/conflict, undo en de productievrijgaveblokkade. Leg project/part-ID, testnaam, bronfingerprint en verwacht resultaat vast naast de afbeelding. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L100) |
| RECOGNITION-0056 | recognition_conversion | PARTIAL | Een afbeelding bewijst geen geometrische equivalentie of materiaalkwaliteit. Combineer haar met de machineleesbare uitkomst. Ontbrekende screenshots blijven een expliciete visuele opleveringsgap; deze runner geeft nooit zelfstandig toestemming voor een installerrelease. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L102) |
| RECOGNITION-0057 | recognition_conversion | PARTIAL | De herkenningsgate bouwt zelf geen EXE of installer. `installer_release_approved` blijft daarom bewust `false`, ook als alle herkenningstests groen zijn. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L106) |
| RECOGNITION-0058 | recognition_conversion | PARTIAL | Codex moet vóór een installatieoplevering: | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L108) |
| RECOGNITION-0059 | recognition_conversion | PARTIAL | Codex moet vóór een installatieoplevering: 1. De bedoelde branch en definitieve commit vaststellen; geen oude acceptatie van een andere SHA hergebruiken. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L110) |
| RECOGNITION-0060 | recognition_conversion | PARTIAL | Codex moet vóór een installatieoplevering: 2. De strikte herkenningsgate op die commit uitvoeren zonder skips en de overige bestaande programmabrede gates uitvoeren. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L111) |
| RECOGNITION-0061 | recognition_conversion | PARTIAL | Codex moet vóór een installatieoplevering: 3. Werkelijke UI-bewijsafbeeldingen controleren; ontbrekende of lege captures herstellen. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L112) |
| RECOGNITION-0062 | recognition_conversion | PARTIAL | Codex moet vóór een installatieoplevering: 4. De bestaande Windows-releaseketen gebruiken (`.github/workflows/final-release-proof.yml`, locked buildruntime en bestaande release-/installerscripts), zonder een tweede los productpakket te bouwen. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L113) |
| RECOGNITION-0063 | recognition_conversion | PARTIAL | Codex moet vóór een installatieoplevering: 5. One-folder runtime, vers uitgepakte portable en werkelijk geïnstalleerde applicatie testen, inclusief voorbeeld-IFC, STEP, PDF en DXF. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L114) |
| RECOGNITION-0064 | recognition_conversion | PARTIAL | Codex moet vóór een installatieoplevering: 6. Installatie, eerste start, opslaan/heropenen en uninstall bewijzen op een schone Windows-testomgeving. Geen productiegegevens of bestaande gebruikersinstallatie wissen. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L115) |
| RECOGNITION-0065 | recognition_conversion | PARTIAL | Codex moet vóór een installatieoplevering: 7. EXE/portable/installer, checksums, bron-SHA, buildlog, actuele acceptatie-JSON en screenshots samen opleveren. Niet-uitgevoerde checks expliciet rapporteren. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L116) |
| RECOGNITION-0066 | recognition_conversion | PARTIAL | Chemische samenstelling en sterkte zijn niet uit alleen vorm, kleur, mesh of extrusie te bepalen. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L120) |
| RECOGNITION-0067 | recognition_conversion | PARTIAL | De materiaalcatalogus is uitbreidbaar, niet een inventaris van alle ooit bestaande materiaalsoorten. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L121) |
| RECOGNITION-0068 | recognition_conversion | PARTIAL | Een generieke of onvolledige materiaalnaam is geen bewijs van de exacte productiekwaliteit. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L122) |
| RECOGNITION-0069 | recognition_conversion | PARTIAL | Complexe, beschadigde of niet-standaard doorsneden kunnen veilig onopgelost blijven; dit is geen toestemming voor productie. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L123) |
| RECOGNITION-0070 | recognition_conversion | PARTIAL | Native tests die niet in de huidige omgeving kunnen draaien, moeten op de bedoelde runtime/CI worden uitgevoerd; lokaal groen op pure tests vervangt dit niet. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L124) |
| RECOGNITION-0071 | recognition_conversion | PARTIAL | Deze vaste regressiesuite is geen representatief nauwkeurigheidspercentage over alle klantmodellen. Daarvoor is een geannoteerde praktijkcorpus nodig met afzonderlijke juist/onjuist/onopgelost/conflict-tellingen. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L125) |
| RECOGNITION-0072 | recognition_conversion | PARTIAL | Een STEP-bron met meerdere onderdelen wordt nog niet per solid door de nieuwe uitgestelde projectactie geïsoleerd: deze actie blokkeert dit expliciet. Hetzelfde geldt voor geometrieën zonder voldoende doorsnede- en equivalentiebewijs. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L126) |
| RECOGNITION-0073 | recognition_conversion | PARTIAL | Semantische IGES/IGS- en losse BREP-projectimport is in deze build niet toegevoegd. IFC/STEP-bronstructuur en PDF/DXF-documentbewijs zijn de geïntegreerde routes. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L127) |
| RECOGNITION-0074 | recognition_conversion | PARTIAL | Binaire DXF en een raster-PDF zonder tekst/OCR leveren in de nieuwe documentbewijsroute geen automatische materiaalwaarde. Materiaalkandidaten uit een document moeten aan het juiste onderdeel gekoppeld en bevestigd worden. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L128) |
| RECOGNITION-0075 | recognition_conversion | PARTIAL | Qt-schermen, native CAD-geometrie, prestatiegedrag op grote modellen en Windows-installatie vereisen eigen werkelijk uitgevoerde controles. In het bijzonder is het geheugengebruik van de volledige projectsnapshot voor een bulkactie nog niet gemeten met de native viewer. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L129) |
| RECOGNITION-0076 | recognition_conversion | PARTIAL | Dit herimporteert de ingesloten bron uit het beschikbare HVPC-referentieproject in een nieuw tijdelijk project, plus de expliciet als gegenereerd/synthetisch gelabelde STEP-regressiebestanden. Het oorspronkelijke projectpakket wordt niet opgeslagen of gewijzigd. `validation/material_model_recognition/reference/corpus.json` bevat bronhashes, catalogustreffers, onbekende waarden, classificatie en exportblokkades apart. Extra echte STEP-bronnen kunnen met herhaalde `--step PAD` argumenten worden toegevoegd. Een catalogustrefferpercentage is geen gemeten herkenningsnauwkeurigheid zonder onafhankelijk vastgestelde juiste waarden. | docs/handover/MATERIAL_MODEL_RECOGNITION_BUILD.md (L137) |
| W18-viewer.zoom | bom_w18 | PARTIAL | Execute viewer.zoom: Zoom naar selectie; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (viewer.zoom) |
| W18-viewer.fit | bom_w18 | PARTIAL | Execute viewer.fit: Passend in beeld; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (viewer.fit) |
| W18-viewer.isolate | bom_w18 | PARTIAL | Execute viewer.isolate: Isoleren; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (viewer.isolate) |
| W18-viewer.ghost | bom_w18 | PARTIAL | Execute viewer.ghost: Andere objecten ghosten; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (viewer.ghost) |
| W18-viewer.hide | bom_w18 | PARTIAL | Execute viewer.hide: Verbergen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (viewer.hide) |
| W18-viewer.show_all | bom_w18 | PARTIAL | Execute viewer.show_all: Alles opnieuw tonen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (viewer.show_all) |
| W18-viewer.section | bom_w18 | PARTIAL | Execute viewer.section: Doorsnede rond selectie; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (viewer.section) |
| W18-viewer.measure | bom_w18 | PARTIAL | Execute viewer.measure: Meten; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (viewer.measure) |
| W18-inspect.properties | bom_w18 | PARTIAL | Execute inspect.properties: Eigenschappen openen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (inspect.properties) |
| W18-inspect.source | bom_w18 | PARTIAL | Execute inspect.source: Bronobject tonen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (inspect.source) |
| W18-inspect.assembly | bom_w18 | PARTIAL | Execute inspect.assembly: Assemblycontext tonen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (inspect.assembly) |
| W18-inspect.hashes | bom_w18 | PARTIAL | Execute inspect.hashes: Geometrie/productiehash bekijken; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (inspect.hashes) |
| W18-inspect.blockers | bom_w18 | PARTIAL | Execute inspect.blockers: Conflicten en blockers tonen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (inspect.blockers) |
| W18-edit.profile | bom_w18 | PARTIAL | Execute edit.profile: Profiel aanpassen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (edit.profile) |
| W18-edit.material | bom_w18 | PARTIAL | Execute edit.material: Materiaal aanpassen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (edit.material) |
| W18-edit.length | bom_w18 | PARTIAL | Execute edit.length: Lengte aanpassen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (edit.length) |
| W18-edit.mark | bom_w18 | PARTIAL | Execute edit.mark: Merk/positie aanpassen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (edit.mark) |
| W18-edit.phase | bom_w18 | PARTIAL | Execute edit.phase: Fase wijzigen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (edit.phase) |
| W18-edit.classification | bom_w18 | PARTIAL | Execute edit.classification: Classificatie wijzigen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (edit.classification) |
| W18-edit.assembly_add | bom_w18 | PARTIAL | Execute edit.assembly_add: Aan assembly toevoegen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (edit.assembly_add) |
| W18-edit.assembly_remove | bom_w18 | PARTIAL | Execute edit.assembly_remove: Uit assembly verwijderen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (edit.assembly_remove) |
| W18-edit.orientation | bom_w18 | PARTIAL | Execute edit.orientation: Productieoriëntatie aanpassen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (edit.orientation) |
| W18-edit.revision | bom_w18 | PARTIAL | Execute edit.revision: Revisiestatus aanpassen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (edit.revision) |
| W18-edit.comment | bom_w18 | PARTIAL | Execute edit.comment: Opmerking toevoegen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (edit.comment) |
| W18-drawing.open_part | bom_w18 | PARTIAL | Execute drawing.open_part: Onderdeeltekening openen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (drawing.open_part) |
| W18-drawing.generate | bom_w18 | PARTIAL | Execute drawing.generate: Tekening genereren; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (drawing.generate) |
| W18-drawing.regenerate | bom_w18 | PARTIAL | Execute drawing.regenerate: Tekening opnieuw genereren; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (drawing.regenerate) |
| W18-drawing.open_assembly | bom_w18 | PARTIAL | Execute drawing.open_assembly: Assemblytekening openen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (drawing.open_assembly) |
| W18-drawing.preview | bom_w18 | PARTIAL | Execute drawing.preview: PDF-preview; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (drawing.preview) |
| W18-drawing.setup | bom_w18 | PARTIAL | Execute drawing.setup: Formaat, schaal en aanzichten instellen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (drawing.setup) |
| W18-drawing.format | bom_w18 | PARTIAL | Execute drawing.format: Formaat kiezen (A4 t/m A0); prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (drawing.format) |
| W18-drawing.scale | bom_w18 | PARTIAL | Execute drawing.scale: Schaal automatisch of handmatig; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (drawing.scale) |
| W18-drawing.views | bom_w18 | PARTIAL | Execute drawing.views: Aanzichten kiezen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (drawing.views) |
| W18-drawing.dimension_check | bom_w18 | PARTIAL | Execute drawing.dimension_check: Maatvoering controleren; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (drawing.dimension_check) |
| W18-drawing.revision | bom_w18 | PARTIAL | Execute drawing.revision: Tekeningrevisie toevoegen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (drawing.revision) |
| W18-drawing.approve | bom_w18 | PARTIAL | Execute drawing.approve: Tekening goedkeuren; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (drawing.approve) |
| W18-drawing.batch_pdf | bom_w18 | PARTIAL | Execute drawing.batch_pdf: Batch-PDF maken; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (drawing.batch_pdf) |
| W18-drawing.print | bom_w18 | BLOCKED_EXTERNAL | Execute drawing.print: Printen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (drawing.print) |
| W18-machine.recommend | bom_w18 | PARTIAL | Execute machine.recommend: Aanbevolen machine bekijken; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (machine.recommend) |
| W18-machine.explain | bom_w18 | PARTIAL | Execute machine.explain: Waarom deze machine?; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (machine.explain) |
| W18-machine.assign | bom_w18 | PARTIAL | Execute machine.assign: Machine toewijzen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (machine.assign) |
| W18-machine.auto_accept | bom_w18 | PARTIAL | Execute machine.auto_accept: Automatische toewijzing accepteren; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (machine.auto_accept) |
| W18-machine.manual_lock | bom_w18 | PARTIAL | Execute machine.manual_lock: Handmatige toewijzing vergrendelen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (machine.manual_lock) |
| W18-machine.reset | bom_w18 | PARTIAL | Execute machine.reset: Machinekeuze resetten; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (machine.reset) |
| W18-machine.validate | bom_w18 | PARTIAL | Execute machine.validate: Geschiktheid opnieuw controleren; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (machine.validate) |
| W18-machine.alternatives | bom_w18 | PARTIAL | Execute machine.alternatives: Alternatieve machine tonen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (machine.alternatives) |
| W18-machine.blocker | bom_w18 | PARTIAL | Execute machine.blocker: Productieblokker bekijken; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (machine.blocker) |
| W18-production.route | bom_w18 | PARTIAL | Execute production.route: Productieroute bekijken; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (production.route) |
| W18-production.operations | bom_w18 | PARTIAL | Execute production.operations: Bewerkingen bekijken; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (production.operations) |
| W18-production.nc_preview | bom_w18 | PARTIAL | Execute production.nc_preview: NC1/DSTV-preview; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (production.nc_preview) |
| W18-production.release | bom_w18 | PARTIAL | Execute production.release: Vrijgeven voor productie; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (production.release) |
| W18-production.withdraw | bom_w18 | PARTIAL | Execute production.withdraw: Productievrijgave intrekken; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (production.withdraw) |
| W18-optimize.profile | bom_w18 | PARTIAL | Execute optimize.profile: Profielnesting starten; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (optimize.profile) |
| W18-optimize.plate | bom_w18 | PARTIAL | Execute optimize.plate: Plaatnesting starten; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (optimize.plate) |
| W18-optimize.trade_length | bom_w18 | PARTIAL | Execute optimize.trade_length: Optimaliseren op handelslengte; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (optimize.trade_length) |
| W18-optimize.stock | bom_w18 | PARTIAL | Execute optimize.stock: Optimaliseren op aanwezige voorraad; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (optimize.stock) |
| W18-optimize.remnants_include | bom_w18 | PARTIAL | Execute optimize.remnants_include: Reststukken meenemen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (optimize.remnants_include) |
| W18-optimize.remnants_exclude | bom_w18 | PARTIAL | Execute optimize.remnants_exclude: Reststukken uitsluiten; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (optimize.remnants_exclude) |
| W18-optimize.kerf | bom_w18 | PARTIAL | Execute optimize.kerf: Zaagverlies instellen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (optimize.kerf) |
| W18-stock.plan | bom_w18 | PARTIAL | Execute stock.plan: Voorraad- en reststukplan berekenen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (stock.plan) |
| W18-stock.assign | bom_w18 | PARTIAL | Execute stock.assign: Toewijzen aan voorraadstuk; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (stock.assign) |
| W18-stock.release | bom_w18 | PARTIAL | Execute stock.release: Voorraadreservering vrijgeven; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (stock.release) |
| W18-stock.shortage | bom_w18 | PARTIAL | Execute stock.shortage: Materiaaltekort berekenen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (stock.shortage) |
| W18-purchase.generate | bom_w18 | PARTIAL | Execute purchase.generate: Inkoopbehoefte genereren; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (purchase.generate) |
| W18-purchase.edit | bom_w18 | PARTIAL | Execute purchase.edit: Inkoopgegevens bewerken; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (purchase.edit) |
| W18-purchase.release | bom_w18 | PARTIAL | Execute purchase.release: Inkoop vrijgeven; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (purchase.release) |
| W18-purchase.cancel | bom_w18 | PARTIAL | Execute purchase.cancel: Inkoop annuleren; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (purchase.cancel) |
| W18-optimize.alternatives | bom_w18 | PARTIAL | Execute optimize.alternatives: Alternatieve profielen/materialen; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (optimize.alternatives) |
| W18-optimize.compare | bom_w18 | PARTIAL | Execute optimize.compare: Vergelijken met vorige optimalisatie; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (optimize.compare) |
| W18-export.production | bom_w18 | PARTIAL | Execute export.production: NC1/STEP/IFC/DXF/productie-PDF; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (export.production) |
| W18-export.review | bom_w18 | PARTIAL | Execute export.review: XLSX/CSV/JSON/PDF/BOM-package; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (export.review) |
| W18-export.grouping | bom_w18 | PARTIAL | Execute export.grouping: Groeperen per onderdeel/merk/assembly/machine/fase/levering; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (export.grouping) |
| W18-export.nc1 | bom_w18 | PARTIAL | Execute export.nc1: NC1/DSTV; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (export.nc1) |
| W18-export.step | bom_w18 | PARTIAL | Execute export.step: STEP; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (export.step) |
| W18-export.ifc | bom_w18 | PARTIAL | Execute export.ifc: IFC; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (export.ifc) |
| W18-export.dxf | bom_w18 | PARTIAL | Execute export.dxf: DXF; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (export.dxf) |
| W18-export.pdf | bom_w18 | PARTIAL | Execute export.pdf: PDF; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (export.pdf) |
| W18-export.xlsx | bom_w18 | PARTIAL | Execute export.xlsx: XLSX; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (export.xlsx) |
| W18-export.csv | bom_w18 | PARTIAL | Execute export.csv: CSV; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (export.csv) |
| W18-export.json | bom_w18 | PARTIAL | Execute export.json: JSON; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (export.json) |
| W18-export.package | bom_w18 | PARTIAL | Execute export.package: Productiepackage; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (export.package) |
| W18-export.occurrences | bom_w18 | PARTIAL | Execute export.occurrences: Alleen geselecteerde occurrences; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (export.occurrences) |
| W18-export.per_part | bom_w18 | PARTIAL | Execute export.per_part: Eén bestand per onderdeel; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (export.per_part) |
| W18-export.per_mark | bom_w18 | PARTIAL | Execute export.per_mark: Eén bestand per merk; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (export.per_mark) |
| W18-export.per_assembly | bom_w18 | PARTIAL | Execute export.per_assembly: Eén package per assembly; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (export.per_assembly) |
| W18-export.per_machine | bom_w18 | PARTIAL | Execute export.per_machine: Eén package per machine; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (export.per_machine) |
| W18-export.per_phase | bom_w18 | PARTIAL | Execute export.per_phase: Eén package per fase of levering; prove exact selection and the action-specific result. | cws_convertor/bom/production_hub.py (export.per_phase) |
| LEGACY-NAV-12 | historical_superseded | OUT_OF_SCOPE_APPROVED | Twelve legacy top-level product tabs | requirements/SUPERSEDED_REQUIREMENTS.json (LEGACY-NAV-12) |
| LEGACY-DARK-DEFAULT | historical_superseded | OUT_OF_SCOPE_APPROVED | Engineering Dark as mandatory/default product theme | requirements/SUPERSEDED_REQUIREMENTS.json (LEGACY-DARK-DEFAULT) |
| LEGACY-ACCEPTANCE-51 | historical_superseded | OUT_OF_SCOPE_APPROVED | A fixed 51-check report as complete current acceptance | requirements/SUPERSEDED_REQUIREMENTS.json (LEGACY-ACCEPTANCE-51) |
| LEGACY-RASTER-DRAWING | historical_superseded | OUT_OF_SCOPE_APPROVED | Full-page raster production PDF route | requirements/SUPERSEDED_REQUIREMENTS.json (LEGACY-RASTER-DRAWING) |
