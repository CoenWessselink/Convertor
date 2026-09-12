# CWS CONVERTOR — COMPLETE PRODUCT INTEGRATION & RELEASE SUPERPROMPT

## 0. HOOFDOPDRACHT

Voltooi de bestaande **CWS Convertor / SteelConverter** tot één samenhangende, productiegerichte Windows-applicatie.

Bouw **geen vervangend programma**.

Gebruik de bestaande architectuur, repository, canonieke ProjectModel-keten, Viewer, DrawingWorkspacePanel, BOM/Productiehub, herkenningsengines, profiel- en plaatnesting, manufacturing/scribing, export, installer en bestaande testinfrastructuur als basis.

Iedere wijziging moet bestaande werkende functionaliteit behouden.

Repository:

`CoenWessselink/Convertor`

Primaire werkbranch:

`agent/cws-pdf-ui-v3-complete-20260909`

Controleer vóór iedere wijziging eerst de actuele remote HEAD.

De laatst bekende HEAD uit deze opdracht was:

`df2029ac0ae50d78221dc38c962ccada91e8f28c`

Deze SHA is uitsluitend referentie. Neem hem nooit blind over indien de branch inmiddels verder staat.

Geen force push.

Behoud gelijktijdig werk.

Werk in kleine, herstelbare commits.

---

# 1. UITVOERSTRATEGIE — VERPLICHTE BOUWBLOKKEN

Voer de opdracht **niet als één onbeheerde megawijziging** uit.

Werk exact in onderstaande bouwblokken.

Een volgend bouwblok mag pas inhoudelijk worden gestart nadat:

1. het vorige blok is geïmplementeerd;
2. relevante tests groen zijn;
3. regressie is uitgevoerd;
4. bewijs is opgeslagen;
5. wijzigingen zijn gecommit;
6. de actuele GAP-status is bijgewerkt.

Als een extern bewijs ontbreekt, markeer het blokonderdeel als `BLOCKED_EXTERNAL` en ga door met andere softwarematige onderdelen.

Nooit externe acceptatie faken.

---

# BOUWBLOK 1 — MASTER REQUIREMENTS + BOM/W18 SLUITEN

## Doel

Maak eerst één actuele requirementsbasis en sluit de volledige BOM-actiematrix technisch af.

## Uitvoeren

Maak een nieuw **Master Requirements Register V2** op basis van:

* historische MASTER_REQUIREMENT_TRACEABILITY;
* Viewer requirements;
* BOM requirements;
* PDF/UI V3;
* materiaal/modelherkenning;
* converter;
* nesting;
* voorraad;
* purchase/weld;
* manufacturing/M1–M18;
* machine routing;
* planning;
* quality;
* installer/release;
* alle requirements in deze superprompt.

Iedere requirement bevat:

* requirement_id;
* source;
* category;
* description;
* applicable;
* implementation;
* test;
* evidence;
* source_commit;
* installed_commit;
* status;
* blocker;
* external_acceptance;
* supersedes;
* superseded_by.

Status:

* PASS
* PARTIAL
* FAIL
* BLOCKED_EXTERNAL
* OUT_OF_SCOPE_APPROVED

Historische PASS-statussen niet automatisch overnemen.

## W18 / 87 BOM-acties

Gebruik `ACTION_DEFINITIONS` als canonieke actiematrix.

Behoud bestaande 87/87 negatieve coverage.

Test ALLE 87 acties positief.

Per actie minimaal:

* empty selection;
* valid single;
* valid multiple waar relevant;
* mixed selection waar relevant;
* wrong family;
* blocked;
* stale;
* invalid;
* positive postcondition;
* exact selected IDs;
* no unintended widening;
* non-selected entities unchanged;
* save/reopen wanneer persistent;
* undo wanneer mutating;
* release invalidation waar relevant.

Een workspace openen telt niet als succesvolle uitvoering.

## Exitcriteria blok 1

* exact 87 unieke acties;
* 87/87 negatieve postconditions bewezen;
* 87/87 positieve postconditions bewezen of expliciet external;
* mutating acties hebben undo/persistence bewijs waar toepasselijk;
* Master Requirements V2 gegenereerd;
* geen stille routefallback;
* geen generieke route die action intent verliest.

## Oplevering blok 1

Commit(s):

`feat(requirements): establish master requirements v2`

`fix(bom): close complete 87 action execution matrix`

`test(bom): prove all W18 action postconditions`

---

# BOUWBLOK 2 — REAL-WORLD HERKENNING + CONVERSIE

## Doel

Maak materiaal-/modelherkenning aantoonbaar bruikbaar op echte bronbestanden.

## Ondersteunde input

* IFC
* STEP
* STP
* DXF
* NC1/DSTV
* trusted PDF
* externe vector-PDF
* raster/scan waar binnen scope

## Herken objectfamilies

Minimaal:

* HEA
* HEB
* HEM
* IPE
* IPN
* UNP/UPE
* L
* T
* RHS
* SHS
* CHS
* strip
* flat
* round
* bar
* plate
* welded/custom profile
* manufacturer extrusion
* arbitrary STEP solid
* multisolid
* assembly

## Manufacturing features

* hole
* slot
* notch
* cope
* mitre
* bevel
* cutout
* pocket
* contour
* chamfer
* weld preparation
* marking/scribing
* face
* orientation
* transformation

## Materiaal

Materiaal nooit uit vorm raden.

Bron moet zijn:

* source metadata;
* IFC property;
* NC data;
* certificate;
* controlled mapping;
* explicit user confirmation.

Onbekend blijft REVIEW_REQUIRED.

## Custom Profile Library

Voeg gecontroleerde custom-profile manager toe:

* DXF/STEP section extraction;
* profile fingerprint;
* rotation independent comparison;
* manufacturer;
* aliases;
* dimensions;
* tolerance;
* material compatibility;
* source evidence;
* user approval;
* versioning.

## Real-world corpus

Gebruik alle eerder aangeleverde echte bestanden.

Per bestand:

* SHA256;
* source;
* expected entities;
* expected quantities;
* dimensions;
* profiles;
* materials;
* features;
* expected blockers.

Rapporteer:

* precision;
* recall;
* false READY;
* false BLOCKED;
* review rate.

Een recognizer die alles blokkeert faalt.

False READY is altijd failure.

## Conversion matrix

Test:

input format
× output format
× object family
× feature.

Controleer:

* identity;
* quantity;
* dimensions;
* units;
* transforms;
* material provenance;
* features;
* assemblies.

## Exitcriteria blok 2

* alle eerder geleverde real-world bestanden opnieuw getest;
* onafhankelijk expected result per bestand;
* minimum precision/recall expliciet;
* false READY = 0;
* supported objectfamilies hebben positieve real-file cases;
* converter heeft geen stille dataverliezen.

---

# BOUWBLOK 3 — VIEWER + CONTROLEREN + OPENBIM

## Doel

Maak Viewer/Controleren volledig bruikbaar als engineering reviewomgeving.

## Viewer

Voltooi/bewijs:

* exact IFC/STEP rendering;
* provenance;
* orbit/pan/zoom;
* standard views;
* orthographic/perspective;
* object selection;
* Ctrl selection;
* box;
* crossing;
* lasso;
* color;
* tree sync;
* BOM sync;
* properties;
* hide/show;
* isolate;
* ghost;
* transparency;
* source colors;
* wireframe;
* shaded;
* shaded with edges;
* hidden-line;
* sections;
* section from face;
* clipbox;
* explode;
* measurements;
* saved views;
* markups;
* issues;
* revision compare;
* deviation;
* clashes.

## Smart Views

Voeg rule-based saved views toe:

* query;
* filters;
* colours;
* visibility;
* grouping;
* validation state.

## IDS

Implementeer buildingSMART IDS validation:

* `.ids` import;
* IFC applicability;
* property;
* classification;
* material;
* value;
* unit checks.

Resultaat per object.

Viewer highlight.

Report.

Issue generation.

## Clash sets

Voeg saved clash sets toe:

* scope A/B;
* hard clash;
* clearance;
* tolerance;
* exclusions;
* severity;
* assigned;
* status;
* rerun;
* stale-on-revision.

## BCF

Ondersteun minimaal:

* BCF 2.1 import;
* BCF 3.0 import/export;
* GUID;
* camera;
* viewpoint;
* clipping;
* visible components;
* selected components;
* screenshot;
* comments;
* assignment;
* status.

Test BCF in onafhankelijke applicatie.

## Exitcriteria blok 3

* native Viewer tests;
* no hidden-line source-only claim;
* IDS end-to-end;
* saved clash rerun na revision;
* BCF roundtrip extern bewezen of BLOCKED_EXTERNAL;
* Viewer state blijft behouden na save/reopen.

---

# BOUWBLOK 4 — DRAWINGS + CHANGE IMPACT

## Doel

Maak tekeningen volledig associatief met de engineeringketen.

## DrawingWorkspace

Behoud bestaande DrawingWorkspacePanel.

Voltooi:

* part drawings;
* assembly drawings;
* GA indien in scope;
* automatic views;
* sections;
* scale;
* A4–A0;
* dimensions;
* marks;
* weld symbols;
* revision marks;
* title blocks;
* PDF;
* batch;
* print.

## Smart Drawing

Voeg toe:

* drawing templates;
* best template selection;
* clone similar;
* automatic views;
* section suggestion;
* dimension strategy;
* annotation collision prevention;
* drawing completeness;
* revision impact preview;
* bulk revision chart editing.

## Change Impact Engine

Bouw één centrale dependencygraph.

Voorbeeld:

Part
→ Assembly
→ BOM
→ Drawing
→ Nesting
→ Stock
→ NC
→ Machine
→ Production Release
→ Inspection
→ Shipment.

Als bron wijzigt:

* dependent outputs `STALE`;
* production release invalid;
* outdated drawings invalid;
* outdated nesting invalid;
* machine assignment opnieuw controleren indien relevant.

Maak een Change Impact panel.

## Exitcriteria blok 4

Test één wijziging:

* profile;
* length;
* hole;
* material provenance.

Controleer downstream:

* Viewer;
* BOM;
* mass;
* drawing;
* nesting;
* stock;
* machine;
* NC;
* exports;
* release.

Save/reopen en undo inbegrepen.

---

# BOUWBLOK 5 — NESTING + VOORRAAD + INKOOP

## Doel

Maak materiaaloptimalisatie en fysieke voorraadlevensloop productiebruikbaar.

## Profielnesting

Behoud bestaande engine.

Ondersteun:

* trade lengths;
* stock;
* remnants;
* kerf;
* multiple stock bars;
* reservation;
* alternatives;
* compare;
* procurement need.

Status onderscheid:

* FEASIBLE;
* HEURISTIC;
* OPTIMAL_PROVEN;
* UNPROVEN.

Geen optimaliteitsclaim zonder bewijs.

## Plaatnesting

Gebruik één canonieke engine.

Ondersteun:

* quantity;
* exact material;
* grade;
* thickness;
* contour;
* holes;
* concave geometry;
* rotations;
* grain;
* kerf;
* clearances;
* stock;
* remnants.

Verdiep met:

* true-shape;
* clamp/no-cut;
* collision;
* common-line;
* chain/bridge;
* pierce minimization;
* cut length;
* true remnant contour.

## Future Remnants

States:

* predicted;
* reserved_future;
* created;
* available;
* consumed;
* scrapped.

Geen fysiek verbruik voordat broncut bevestigd is.

## Voorraad lifecycle

Implementeer:

NEED
→ REQUISITION
→ ORDERED
→ RECEIVED
→ AVAILABLE
→ RESERVED
→ ISSUED
→ CONSUMED.

Remnant:

CREATED
→ AVAILABLE
→ RESERVED
→ CONSUMED/SCRAPPED.

## Materiaaltraceability

Per stock item:

* supplier;
* PO;
* heat/charge;
* certificate;
* grade;
* dimensions;
* location;
* received date.

Part moet terug te leiden zijn tot fysieke bron.

## Exitcriteria blok 5

* reserve/reopen/release/replan;
* receive;
* partial consumption;
* remnant creation;
* no double booking;
* stock history;
* revision-safe;
* undo waar mogelijk;
* echte profiel- en plaatcases.

---

# BOUWBLOK 6 — MACHINES + M1–M18 + IDEA

## Doel

Maak manufacturing feasibility volledig verklaarbaar.

## Machine Capability Profiles

Per machine:

* profile ranges;
* material;
* thickness;
* max length;
* max weight;
* faces;
* drills;
* saw angles;
* milling;
* coping;
* marking;
* scribing;
* clamps;
* dead zones;
* tools;
* postprocessor;
* controller;
* qualification state.

## Machine feasibility

Part + features + orientation + machine profile
→ explicit report.

Toon:

* eligible;
* blocked;
* unsupported features;
* required transform;
* tools;
* warnings.

## M1–M18

Maak volledige installed featurematrix.

Test:

* contacts;
* faces;
* orientation;
* straight;
* mitre;
* compound;
* marking;
* assembly;
* revision invalidation;
* neutral job;
* invalid geometry;
* no authority.

## Golden jobs

Per werkelijk gebruikte machine:

* known input;
* known machine setup;
* expected output;
* physical validation.

Software CI mag fysieke kwalificatie nooit faken.

## IDEA StatiCa

Bouw geen connection solver na.

Bouw bridge via ondersteunde API/interface.

Koppel indien beschikbaar:

* IDs;
* plates;
* bolts;
* welds;
* geometry;
* forces;
* check state;
* revision.

Na CWS-wijziging wordt resultaat STALE.

## Exitcriteria blok 6

* machine recommendations verklaarbaar;
* invalid machine combinations fail closed;
* M1–M18 installed matrix;
* physical machine items BLOCKED_EXTERNAL totdat werkelijk gevalideerd;
* no direct transfer without authority.

---

# BOUWBLOK 7 — PRODUCTIE + SHOPFLOOR

## Doel

Voeg gecontroleerde productie-uitvoering toe.

## Productie workspace

Maak `WorkPackage`.

Velden:

* id;
* project;
* phase;
* assembly;
* parts;
* operation;
* machine/station;
* priority;
* planned;
* due;
* operator;
* estimated time;
* actual time;
* material;
* drawing revision;
* NC revision;
* inspections.

Statuses:

* PLANNED
* READY
* BLOCKED
* QUEUED
* IN_PROGRESS
* PAUSED
* COMPLETE
* REJECTED
* REWORK

## Routing

Voorbeeld:

Saw
→ Drill
→ Coping
→ Welding
→ Inspection
→ Coating
→ Shipping.

## Cut Lists

Cut confirmation moet:

* consume stock;
* update work package;
* calculate drop;
* create remnant;
* create audit entry.

## QR / barcode

Gebruik stabiele canonical ID.

Support:

* part;
* assembly;
* stock;
* work package;
* shipment.

## Exitcriteria blok 7

* work package lifecycle;
* exact source revision;
* stock consumption;
* operator feedback;
* no production on stale drawing/NC;
* save/reopen;
* traceability compleet.

---

# BOUWBLOK 8 — KWALITEIT + PLANNING + LOGISTIEK

## Quality Hub

Voeg:

* InspectionPlan;
* InspectionRecord;
* hold points;
* tolerance;
* measured values;
* evidence;
* PASS/FAIL/REWORK.

## NCR

Velden:

* NCR ID;
* object;
* issue;
* severity;
* cause;
* action;
* responsible;
* due;
* evidence.

Disposition:

* rework;
* accept-as-is;
* scrap;
* replace.

Accept-as-is vereist authority.

## Weld quality

Koppel:

* weld type;
* size;
* length;
* process;
* connected parts;
* WPS reference waar aanwezig;
* inspection.

Geen WPS verzinnen.

## Planning

Resources:

* machines;
* stations;
* labor groups.

Per resource:

* calendar;
* shifts;
* capacity;
* downtime.

Plan op:

* due date;
* priority;
* material;
* drawing release;
* NC;
* predecessor;
* machine eligibility.

## Gantt

Voeg:

* project Gantt;
* machine Gantt;
* capacity;
* overload;
* bottlenecks.

## Delivery

Ondersteun:

* phase;
* sequence;
* lot;
* delivery batch;
* bundle;
* shipment;
* destination;
* planned/actual delivery.

## Exitcriteria blok 8

* quality can block production/shipping;
* NCR/rework changes status correctly;
* planning respects readiness;
* no duplicate shipping;
* traceable from delivery back to parts/material.

---

# BOUWBLOK 9 — RAPPORTAGE + UI + PERFORMANCE

## KPI

Dashboards:

* requested vs produced;
* yield;
* scrap;
* remnants;
* shortages;
* machine utilization;
* planned/actual hours;
* throughput;
* late work;
* quality failures;
* rework;
* NCR;
* revision impact;
* delivery completeness.

Iedere KPI drilldown naar brondata.

## UI

Maak consistent:

* Viewer;
* Controleren;
* Bewerken;
* BOM;
* Drawing;
* Profile nesting;
* Plate nesting;
* Machines;
* Stock/Purchase;
* Planning;
* Production;
* Quality;
* Delivery;
* Reporting;
* Export.

Test:

* 100%;
* 125%;
* 150%;
* 175%;
* 200% DPI;
* 1080p;
* 1440p;
* 4K;
* small window;
* multi-monitor waar beschikbaar;
* keyboard.

## Viewer performance

Test finale EXE met:

* HVPC;
* tweede groot project.

Targets:

* cold exact ≤5 s;
* first usable preferably ≤3 s;
* mean FPS ≥30;
* frame p95 ≤33 ms;
* input p95 ≤35 ms;
* input p99 ≤50 ms;
* pick p95 ≤150 ms;
* zero freezes >100 ms;
* RSS drift <10%.

Gebruik fysieke GPU voor final acceptance.

## Exitcriteria blok 9

* geen clipping;
* geen onleesbare DPI states;
* model dominant waar bedoeld;
* performance report source-bound;
* old performance measurements niet hergebruiken.

---

# BOUWBLOK 10 — END-TO-END + WINDOWS + FINALE RELEASE

## Twee representatieve projecten

### Project R — staal

Moet bevatten:

* profiles;
* plates;
* assemblies;
* bolts;
* welds;
* purchased items;
* stock;
* drawings;
* nesting;
* machine;
* production;
* inspection;
* shipping.

### Project H — heterogeen

Moet bevatten:

* custom profiles;
* unusual extrusions;
* compound solids;
* mixed formats;
* missing metadata;
* external PDF.

## R1 → R2

Voor beide projecten:

R1 volledige workflow.

Daarna R2:

* changed object;
* added object;
* deleted object;
* moved object;
* changed manufacturing feature.

Controleer:

Import
→ Recognition
→ Review
→ BOM
→ Stock
→ Nesting
→ Drawing
→ Machine
→ Production
→ Quality
→ Export
→ Delivery
→ Reopen.

## Windows acceptance

Finale SHA testen op Windows 11:

* clean;
* standard user;
* admin;
* default path;
* custom path;
* onefolder;
* portable;
* installer;
* repair;
* upgrade;
* rollback;
* reboot;
* uninstall;
* associations;
* reopen projects/settings.

## Release promotion

Splits:

BUILD

en

PROMOTE.

PROMOTE vereist alle verplichte gates.

## Signing

* sign installer;
* timestamp;
* verify publisher;
* recalculate hashes.

## SBOM

Genereer artifact-bound SBOM:

* Python;
* Qt/PySide;
* VTK;
* OCCT/CadQuery;
* IFCOpenShell;
* native DLLs;
* other runtime components.

Leg vast:

* version;
* source;
* license;
* CVE scan;
* disposition.

## Exitcriteria blok 10

* finale source SHA = tested SHA;
* final installer = tested binary;
* two end-to-end projects PASS;
* no open P0/P1 software gaps;
* external items clearly marked;
* checksums available;
* release manifest;
* SBOM;
* signed installer indien bedrijfsrelease vereist.

---

# 2. CANONIEKE APPLICATIESTRUCTUUR

Streef naar onderstaande workspaces:

1. Start / Project
2. Viewer
3. Controleren
4. Bewerken
5. BOM / Productiehub
6. Tekeningen
7. Profielnesting
8. Plaatnesting
9. Machines
10. Voorraad & Inkoop
11. Planning
12. Productie
13. Kwaliteit
14. Levering
15. Rapportage
16. Export
17. Instellingen / Bibliotheken

Bestaande workspaces niet vervangen wanneer ze al correct functioneren.

Integreer nieuwe functionaliteit in bestaande architectuur.

---

# 3. CANONIEK PROJECTMODEL

Alle workspaces moeten één gedeeld ProjectModel gebruiken.

Geen tweede waarheid.

Objecttypen minimaal:

* Part
* Assembly
* PurchasedItem
* Fastener
* Weld
* StockItem
* Remnant
* Drawing
* Revision
* MachineAssignment
* ProductionRelease
* Inspection
* WorkPackage
* Shipment

Traceability:

Source
→ Canonical entity
→ Manufacturing
→ BOM
→ Drawing
→ Nest
→ Stock
→ Machine
→ Production
→ Quality
→ Delivery.

---

# 4. ALGEMENE VEILIGHEIDSREGELS

Geen:

* hardcoded PASS;
* fictieve geometrie;
* fictief materiaal;
* fictieve voorraad;
* false production_ready;
* machine transfer zonder qualification;
* silent selection widening;
* stale output als current;
* test die alleen aanwezigheid controleert.

Fail closed wanneer authority ontbreekt.

---

# 5. TESTDISCIPLINE PER COMMIT

Voor iedere wijziging:

1. inspect;
2. implement;
3. compile;
4. focused test;
5. integration test;
6. regression;
7. Windows test indien relevant;
8. evidence;
9. commit;
10. push.

Kleine commits.

Geen force.

---

# 6. BEWIJSREGELS

Iedere evidencefile bevat:

* commit;
* app version;
* environment;
* input hash;
* scenario;
* result;
* output hash.

Screenshots moeten echte runtime zijn.

Geen illustraties als acceptance evidence.

---

# 7. GAPANALYSE NA IEDER BOUWBLOK

Na elk bouwblok genereer:

* implemented;
* partial;
* missing;
* tested;
* installed;
* real-file;
* external;
* blockers.

Percentages afzonderlijk voor:

1. functioneel gebouwd;
2. integration tested;
3. installed tested;
4. real-world tested;
5. release ready.

Geen cosmetisch totaalpercentage.

---

# 8. STOPREGELS

Stop een specifieke actie en rapporteer een blocker wanneer:

* required source ontbreekt;
* materiaal authority ontbreekt;
* machine qualification ontbreekt;
* physical printer acceptance nodig is;
* external BCF application nodig is;
* user/business decision nodig is.

Ga vervolgens verder met andere onafhankelijke softwarematige taken.

Vraag niet routinematig om toestemming.

---

# 9. WAT NIET GEBOUWD MOET WORDEN

Niet uitbreiden naar volledig:

* ERP;
* accounting;
* payroll;
* HR;
* CRM;
* Revit replacement;
* Tekla replacement;
* structural calculation suite;
* generic cloud CDE.

Integraties zijn toegestaan.

---

# 10. CLOUD/CDE

Cloud/multi-user/pointcloud/sync is geen huidige desktop blocker tenzij expliciet opnieuw als release-eis bevestigd.

Local openBIM/BCF/IDS wel.

---

# 11. DEFINITION OF DONE PER BOUWBLOK

Een bouwblok is pas `DONE` indien:

* implementation complete;
* source tests PASS;
* integration tests PASS;
* applicable Windows tests PASS;
* no regression;
* evidence generated;
* commit pushed;
* gap register updated.

Anders:

`PARTIAL` of `BLOCKED_EXTERNAL`.

---

# 12. DEFINITIE VAN 100% TOTAAL

Noem CWS Convertor uitsluitend **100% gereed** wanneer:

* alle toepasselijke Master Requirements V2 PASS zijn;
* alle 87 BOM-acties positief én negatief bewezen zijn;
* echte recognition corpus voldoende dekking heeft;
* converter-matrix sluit;
* Viewer native/performance-evidence sluit;
* drawing/change-impact sluit;
* stock lifecycle sluit;
* nesting benchmark sluit;
* M1–M18 installed sluit;
* twee representatieve R1/R2-projecten end-to-end sluiten;
* final Windows build exact bij geteste source hoort;
* geen open P0/P1 softwaregap resteert;
* external machine/printer/hardwarepunten werkelijk zijn uitgevoerd of expliciet BLOCKED_EXTERNAL blijven;
* geen unsupported claim als PASS wordt gepresenteerd.

---

# 13. FINALE OPLEVERING

Lever:

* branch;
* final SHA;
* commits per bouwblok;
* Master Requirements V2;
* tests per blok;
* complete recognition report;
* conversion report;
* BOM 87 report;
* Viewer report;
* Drawing report;
* nesting benchmarks;
* stock lifecycle report;
* M1–M18 report;
* shopfloor report;
* quality/planning report;
* R1/R2 end-to-end reports;
* Windows installer;
* portable;
* checksums;
* signing status;
* SBOM;
* remaining external blockers;
* finale GAP-analyse.

Bouw het bestaande CWS Convertor gecontroleerd af.

Geen parallel vervangend programma.

Geen cosmetische 100%.

Traceability, reproduceerbaarheid en fail-closed productieautoriteit zijn leidend.
