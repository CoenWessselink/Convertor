# CODEX MASTER-SUPERPROMPT
# CWS CONVERTOR — UI MASTER V5.2 CONTROL BUILD
## Bouw de volledige V5/V5.1 uitstraling daadwerkelijk in de bestaande Qt-app
### Alle schermen, alle knoppen, alle iconen, alle states, één design system, exact drie bouwfasen

---

# 0. DOEL VAN DEZE OPDRACHT

Deze prompt is geen ontwerpnotitie en geen mock-upopdracht.

Deze prompt is een **uitvoerbare bouwopdracht** voor de bestaande CWS Convertor repository.

Doel:

> Bouw de volledige laatste V5/V5.1 gebruikersinterface daadwerkelijk in de bestaande CWS Convertor Qt-applicatie, inclusief alle vereiste schermen, knoppen, iconen, toolbars, tabellen, contextacties, states, dialogen, support surfaces, DPI-gedrag, keyboardgedrag, screenshotacceptatie en packaged Windows-bewijs.

Codex moet de bestaande applicatie **migreren en consolideren**.

Codex mag GEEN parallelle demo-UI, screenshot-shell of tweede applicatie maken.

---

# 1. REPOSITORY EN VERPLICHTE PREFLIGHT

Repository:

`CoenWessselink/Convertor`

Audit-canonical branch:

`agent/cws-product-ui-reintegration-v1`

Audit-baseline SHA:

`dc4e3e2ec2f91c40aad271d985b3fe59a44c7325`

Deze SHA is alleen de laatst gecontroleerde auditbasis.

## Eerste handelingen

Voer vóór wijzigingen uit:

```text
git fetch --all --prune
git status
git branch -vv
git log -20 --oneline --decorate
```

Bepaal daarna:

```text
CURRENT_CANONICAL_BRANCH
CURRENT_HEAD_SHA40
CURRENT_VERSION
CURRENT_PROJECT_SCHEMA
CURRENT_PART_SCHEMA
WORKTREE_CLEAN
```

Als de canonical branch sinds de audit gewijzigd is:

- gebruik de actuele canonical HEAD;
- vergelijk nieuwe commits tegen deze prompt;
- neem reeds correct uitgevoerde V5.2-delen niet opnieuw mee;
- documenteer de delta.

Geen bouw starten vanaf een oude SHA zonder deze preflight.

---

# 2. DEZE PROMPT IS EEN BOUWOVERRIDE

Gebruik de volgende bronnen:

1. actuele expliciete gebruikersopdracht;
2. deze V5.2 Control Build prompt;
3. `DO_NOT_CHANGE.md`;
4. V5.1 FINAL masterprompt;
5. `SCREEN_MANIFEST.json`;
6. `CONTROL_INVENTORY_MASTER.json`;
7. V5 PNG-referenties;
8. `UI_COMPONENT_CATALOG.md`;
9. `UI_TEXT_MASTER.md`;
10. actuele canonical backend/servicecontracten;
11. eerdere prompts voor niet-vervangen functionaliteit.

## Belangrijk conflict dat hiermee expliciet wordt gecorrigeerd

De definitieve globale hoofdnavigatie is EXACT:

```text
PROJECT | VIEWER | PRODUCTIE | CONTROLE | UITVOER
```

User-facing:

```text
Project | Viewer | Productie | Controle | Uitvoer
```

Geen alternatief zoals:

```text
Project | Viewer | Bewerken | BOM & Productie | Uitvoer
```

`Bewerken` hoort onder `Productie`.

`BOM & Machines` hoort onder `Productie`.

`Controle` blijft een zelfstandige hoofdworkspace.

Deze V5.2-regel override iedere oudere promptpassage die een alternatieve vijfdeling suggereert.

---

# 3. GEEN GREENFIELD REWRITE

De huidige Qt-app heeft reeds:

- een geïntegreerde main window;
- project/context services;
- Viewer;
- Workbench;
- BOM;
- Scribing;
- Converter;
- drawing/PDF;
- validation/revision/product workspaces;
- ribbon/icon code;
- bestaande QSS/styling;
- Windows packaging.

Gebruik deze bestaande implementatie als migratiebasis.

Niet:

```text
new_app.py
new_v5_demo.py
ui_mockup.py
v5_preview_only.py
```

als alternatieve productapp bouwen.

Wel:

- huidige `main_window.py` consolideren;
- oude QSS centraliseren;
- bestaande widgets naar shared components migreren;
- oude icon resolver vervangen door expliciete icon authority;
- werkende services behouden;
- legacy widgets pas verwijderen nadat parity bewezen is.

---

# 4. ACTUELE TECHNISCHE GAPS DIE DEZE BUILD MOET SLUITEN

De auditbasis bevat nog oude UI-signalen zoals:

```text
V9
V15
primaryButton objectName
inline QSS
per-screen setStyleSheet()
keyword-driven icon lookup
oude toolbarstructuren
oude tabstructuren
```

Dit is ontwikkelhistorie, geen gewenste eind-UX.

Deze build moet:

1. intern migreren zonder canonical functionality te breken;
2. user-facing legacy ontwikkelcodes verwijderen;
3. styling centraliseren;
4. controls expliciet identificeren;
5. iconen semantisch binden;
6. vijf hoofdworkspaces invoeren;
7. alle V5-screen layouts implementeren;
8. alle controls functioneel koppelen;
9. alle states testen;
10. packaged Windows visueel/functioneel bewijzen.

---

# 5. HARDE PRODUCTARCHITECTUUR

Behoud:

```text
ONE Canonical Project Model
ONE Canonical Part Model
ONE UnifiedApplicationContext
ONE Viewer project/scene truth
ONE SelectionAuthority
ONE JobManager
ONE Workbench write path
ONE BOM quantity truth
ONE Machine routing truth
ONE ContextActionService
ONE DocumentOutputService
ONE Export scope truth
```

De UI is presentation/orchestration.

Nooit:

- tweede Viewer truth;
- tweede selection service;
- tweede BOM;
- tweede machine-routing authority;
- direct model muteren vanuit widgets;
- data business logic in QSS/widgets dupliceren.

---

# 6. BINDENDE VISUELE BRONNEN MOETEN IN DE REPOSITORY BESCHIKBAAR ZIJN

De 25 V5 PNG's mogen niet alleen in een tijdelijke chat-/handovermap leven.

Importeer of kopieer de bindende referenties naar bijvoorbeeld:

```text
docs/ui/v5_2/references/
```

of een gelijkwaardige versioned directory.

Maak:

```text
docs/ui/v5_2/REFERENCE_MANIFEST.json
docs/ui/v5_2/REFERENCE_SHA256SUMS.txt
```

Per reference:

```text
screen_id
filename
sha256
width
height
role
```

De build/testpipeline moet de referenties kunnen vinden vanaf een fresh checkout.

Geen hardcoded `/mnt/data`, chatpath of lokale developerdesktop-path.

---

# 7. VISUELE SSOT

Voor schermen 01–25:

- bijbehorende V5 PNG = structurele/visuele SSOT;
- SCREEN_MANIFEST = inhoud/controls/states;
- CONTROL_INVENTORY = functionaliteit;
- V5.2 component system = exacte control presentation.

Voor support surfaces 26–31 bestaat nog geen bindende oorspronkelijke PNG.

Daarom geldt voor 26–31:

```text
V5.2 textual layout spec
+ component catalog
+ control binding
= temporary visual authority
```

Bouw ze volledig.

Maak na correcte runtimeimplementatie reference screenshots:

```text
26_MACHINEBIBLIOTHEEK_REFERENCE.png
27_PDF_PRINT_TEMPLATES_REFERENCE.png
28_ACTIVITY_CENTER_REFERENCE.png
29_PROBLEM_CENTER_REFERENCE.png
30_DETACHED_VIEWER_REFERENCE.png
31_COMMAND_PALETTE_REFERENCE.png
```

Freeze die pas als canonical V5.2 support references nadat:

- layout review PASS;
- control coverage PASS;
- Light theme PASS;
- DPI 100/125/150/200 PASS.

Tot die tijd:

```text
REFERENCE_STATUS = GENERATED_PENDING_ACCEPTANCE
```

Niet automatisch `APPROVED`.

---

# 8. DEFAULT THEME — EXACT

Default:

```text
LIGHT
```

Tokens:

```text
surface.app       #F4F7FA
surface.panel     #FFFFFF
surface.subtle    #EEF3F7
surface.hover     #E8F0F6
surface.selected  #DDEBF6

nav.background    #263C50
nav.active        #1E5E91

accent.primary    #1F6FA8
accent.hover      #185B8A
accent.pressed    #12496E
accent.soft       #E5F0F8

text.primary      #1F2D3D
text.secondary    #617387
text.disabled     #8E9AA7
text.on_primary   #FFFFFF

border.default    #D4DDE6
border.strong     #AEBECD
focus.ring        #2B7FB8

viewer.selection  #F7C600

status.success    #2E7D32
status.warning    #B56A00
status.error      #B42318
status.info       #246B9E
```

## Belangrijke selectiecorrectie

Gebruik twee verschillende selection-semantics:

```text
3D VIEWER WHOLE-OBJECT HIGHLIGHT
= geel #F7C600

2D UI / TABLE / TREE SELECTION
= lichtblauw/blue accent
```

Geen conflict tussen gele 3D-highlight en blauwe tabelrijselectie.

---

# 9. DESIGN SYSTEM — ÉÉN IMPLEMENTATIE

Bouw een centrale Qt design-system package, bijvoorbeeld:

```text
cws_convertor/ui_qt/design_system/
    __init__.py
    tokens.py
    palette.py
    stylesheet.py
    components.py
    icons.py
    test_ids.py
    control_registry.py
    preferences.py
```

Naam mag aangepast worden aan repo-architectuur, maar authority moet centraal zijn.

## Verboden na migratie

Geen brede verspreiding van:

```text
widget.setStyleSheet("...")
```

voor normale productcomponenten.

Inline styling mag alleen:

- uitzonderlijke custom renderwidget;
- aantoonbare technische noodzaak;
- expliciet gedocumenteerd.

Doel:

```text
scattered product styles = 0
duplicate base button style definitions = 0
```

---

# 10. MIGRATIE VAN HUIDIGE QSS

De bestaande app heeft al globale `_QSS`.

Migreer gecontroleerd.

Niet één dag alles weggooien.

Werk:

```text
OLD QSS
→ token mapping
→ component mapping
→ screen migration
→ screenshot test
→ old selector removal
```

Maak:

```text
validation/ui_v5_2/LEGACY_QSS_MIGRATION_MATRIX.json
```

Per selector:

```text
old_selector
current_usage
new_component/token
migration_status
screens
test
```

Pas oude QSS-regel verwijderen wanneer usages = 0 of gemigreerd.

---

# 11. OBJECTNAME VERSUS UI TEST ID — CORRECT MODEL

Qt `objectName` is niet automatisch hetzelfde als een producttest-ID.

Sommige bestaande objectNames kunnen:

- persistence beïnvloeden;
- dock restoration beïnvloeden;
- tests beïnvloeden;
- compatibility beïnvloeden.

Daarom:

## Nieuwe harde property

Iedere CWS-productcontrol krijgt:

```python
widget.setProperty("ui_test_id", "btn_bom_machine")
```

Voor `QAction`:

```python
action.setProperty("ui_test_id", "action_bom_machine")
```

Daarnaast mag een semantic `objectName` bestaan.

Regels:

- `ui_test_id` is de authoritative UI automation ID;
- stable en uniek;
- geen runtime index;
- geen Nederlandse displaytekst als ID;
- `objectName` niet massaal renamen zonder persistence audit.

Voor widgets die aantoonbaar veilig gemigreerd kunnen worden:

```text
objectName = semantische componentnaam
ui_test_id = functionele unieke control-ID
```

---

# 12. RUNTIME INVENTORY — VOORKOM FALSE POSITIVES

Scan NIET blind ieder intern Qt child widget als “CWS-control”.

Qt maakt intern onder andere:

- scrollbars;
- combo line edits;
- viewport children;
- header internals;
- native dialog children.

Dat zijn geen 226 productcontrols.

## Product-control scope

Een control telt als CWS productcontrol wanneer:

- hij expliciet `ui_test_id` heeft;
- of hij in de static expected control manifest staat;
- of hij door de CWS ControlRegistry wordt geregistreerd.

Hard gate:

```text
CWS product controls without ui_test_id = 0
expected CWS controls missing = 0
duplicate ui_test_id = 0
```

Niet:

```text
all Qt interactive child widgets without test_id = FAIL
```

want dat produceert incorrecte failures op Qt internals.

Nieuwe eigen zichtbare CWS-control zonder registratie = FAIL.

---

# 13. CONTROL COUNT IS DYNAMIC

Audit baseline:

```text
global controls = 12
screen controls = 214
total = 226
```

Maar 226 is geen eeuwige magic number.

Lees bij iedere build:

```text
CONTROL_INVENTORY_MASTER.json
```

Bepaal:

```text
EXPECTED_CONTROL_COUNT
```

Acceptance:

```text
mapped = EXPECTED_CONTROL_COUNT
functional_tested = EXPECTED_CONTROL_COUNT
missing = 0
```

Als requirements later bewust 230 controls bevatten, is 230 de nieuwe authority.

---

# 14. COMPONENT MASTER

Minimaal:

```text
CwsMainWindow
CwsTopNavigation
CwsWorkspaceHeader
CwsSubTabs
CwsPrimaryButton
CwsSecondaryButton
CwsCompactButton
CwsToolButton
CwsToggleToolButton
CwsContextActionButton
CwsDangerButton
CwsMenuButton
CwsSplitButton
CwsStatusBadge
CwsActionBar
CwsViewerToolbar
CwsDataTable
CwsProjectTree
CwsInspectorPanel
CwsSearchField
CwsFilterButton
CwsInlineMessage
CwsEmptyState
CwsLoadingState
CwsActivityCenter
CwsProblemCenter
CwsModalDialog
CwsPopover
CwsCommandPalette
```

Gebruik composition/subclassing passend bij PySide6.

Geen overengineered widget framework.

---

# 15. BUTTON MASTER

## Primary

```text
height 32
min width 88
padding 0 12
radius 4
font Semibold
icon 18
gap 6
```

Normal `#1F6FA8`
Hover `#185B8A`
Pressed `#12496E`
Disabled neutral grey.

Max één dominante primary action per lokale actiecluster.

## Secondary

```text
height 32
background #FFFFFF
border #AEBECD
text #1F2D3D
radius 4
```

## Compact

```text
height 28
icon 16
padding 0 9
```

## Tool button

```text
30x30
icon 18
```

## Context action

```text
height 32
icon 18–20
text visible at normal desktop widths
```

## Danger

Alleen destructief.

`Annuleren` is geen danger.

---

# 16. STATES

Iedere relevante control:

```text
NORMAL
HOVER
PRESSED
FOCUSED
CHECKED
DISABLED
BUSY
WARNING
ERROR
```

Niet iedere component hoeft alle states te gebruiken.

## Disabled

Verplichte concrete reden wanneer gebruiker actie logisch verwacht.

Tooltip:

```text
Niet beschikbaar omdat <reden>.
```

## Busy

Async action:

- dubbelstart blokkeren;
- echte JobManager-state;
- cancel indien supported;
- progress alleen als echt.

---

# 17. ICON AUTHORITY — VERVANG TEKSTHEURISTIEK

De huidige productbasis gebruikt een icon helper die op action/title tekst zoekt.

Dat is te fragiel als finale authority.

Bouw:

```text
IconRegistry
ICON_MASTER.json
```

Gebruik:

```text
icon_id -> exact icon asset/vector painter
```

Niet:

```text
if "export" in label.lower():
```

als primaire semantische binding.

Bestaande line-icon code mag:

- als artistieke basis worden hergebruikt;
- worden omgezet naar expliciete icon IDs;
- worden getest.

Maar user-facing labelwijziging mag niet onverwacht een ander icoon veroorzaken.

---

# 18. ICON IMPLEMENTATIE

Voorkeur:

- originele/licentiegeschikte SVG;
- of bestaande CWS vector painter paths onder expliciet icon ID.

Geen proprietary Trimble assets.

Geen emoji.

Geen OS-font glyphs als kritieke iconen.

## DPI

IconRegistry:

- cache per icon ID;
- palette/state aware;
- logical size aware;
- DPI aware;
- geen eenmalige 64px bitmap die op 200% wazig wordt.

Test:

```text
100%
125%
150%
200%
```

---

# 19. ICON SEMANTICS

Definieer minimaal:

```text
nav.project
nav.viewer
nav.production
nav.control
nav.output

action.open_file
action.open_folder
action.import
action.save
action.save_as
action.undo
action.redo
action.cancel
action.delete
action.search
action.filter
action.group
action.columns
action.more

viewer.select
viewer.fit_all
viewer.fit_selected
viewer.front
viewer.back
viewer.left
viewer.right
viewer.top
viewer.bottom
viewer.iso
viewer.perspective
viewer.orthographic
viewer.hide
viewer.show_all
viewer.isolate
viewer.ghost
viewer.transparency
viewer.section
viewer.clip_box
viewer.measure
viewer.explode
viewer.detach

production.edit
production.drawing
production.machine
production.optimize
production.print

machine.auto
machine.manual
machine.recalculate
machine.assign
machine.reset_auto
machine.capability
machine.library

nesting.profile
nesting.plate
nesting.optimize
nesting.compare
nesting.lock
nesting.unlock
nesting.validate
nesting.accept
nesting.reserve
nesting.release

scribing.mark
scribing.hole_reference
scribing.identification
scribing.generate

drawing.auto_layout
drawing.generate
drawing.edit
drawing.preview
drawing.pdf

print.preview
print.printer
print.pdf
print.batch

validation.run
validation.blocker
validation.error
validation.warning
validation.info
validation.open_object
validation.evidence

revision.compare
review.new
review.saved_view

export.scope
export.formats
export.preflight
export.generate
export.verify
export.package

global.activity
global.problems
global.settings
global.command
global.help

status.success
status.warning
status.error
status.info
```

Een actie gebruikt overal exact hetzelfde `icon_id`.

---

# 20. CONTROL VISUAL BINDING

Genereer:

```text
validation/ui_v5_2/CONTROL_VISUAL_BINDING.json
```

Voor 100% van de actuele Control Inventory.

Per record:

```text
test_id
screen_id
label
component
variant
icon_id
placement_zone
group_id
group_order
height
width_policy
tooltip
disabled_reason_template
shortcut
reference_screen
handler/service
```

Hard:

```text
missing binding = 0
unknown component = 0
unknown icon = 0
duplicate visual binding = 0
```

---

# 21. GLOBAL SHELL

Exact:

```text
┌──────────────────────────────────────────────────────────────┐
│ CWS Convertor | project/breadcrumb                           │
│ Project | Viewer | Productie | Controle | Uitvoer            │
│                              Undo Redo Activity Problems ⚙   │
├──────────────────────────────────────────────────────────────┤
│ workspace                                                    │
└──────────────────────────────────────────────────────────────┘
```

Light work area.

Topnav donker blauwgrijs.

Active main workspace duidelijk maar rustig.

Geen tweede verticale globale nav.

Geen oude 11-tab appbar naast deze nieuwe nav.

---

# 22. WORKSPACE STRUCTUUR

## Project

```text
Start / Inlezen
Projectoverzicht
Projectstructuur
Profielen & Materialen
Projectreviews
```

## Viewer

```text
3D cockpit
Selectie & Context
Weergave & Meten
Doorsnede & Isoleren
Laadstatus & Prestaties
```

Dit hoeven niet vijf grote zichtbare tabs te zijn.

Ze kunnen contextpanelen/toolgroups zijn binnen één Viewer workspace.

## Productie

```text
BOM & Machines
  BOM
  Machine-indeling
  Optimalisatie

Bewerken
Scribing
Tekeningen / PDF
Converteren
```

## Controle

```text
Validatie
Revisies / Compare
Maakbaarheid
Manufacturing Geometry
Evidence
PDF Review
```

## Uitvoer

```text
Afdrukken
Rapport
Export Center
```

---

# 23. VIEWER BLIJFT PERMANENT

Geen tweede Viewer bij:

- Workbench;
- Scribing;
- Controle;
- BOM preview;
- detached view.

Geometriecontext blijft dezelfde canonical projectcontext.

Detached Viewer:

- presentatievariant;
- same context;
- same selection authority;
- geen re-import.

---

# 24. VIEWER TOOLBAR

Normale structuur:

```text
SELECTIE
[Onderdeel/Samenstelling ▼]

CAMERA
[Fit] [Voor] [Boven] [ISO] [Projectie ▼]

WEERGAVE
[Verbergen] [Isoleren] [Ghost] [Alles tonen]

ANALYSE
[Meten] [Doorsnede]

[Meer ▼]
```

Extra standaard views blijven bereikbaar:

```text
Achter
Links
Rechts
Onder
```

Geen verlies omdat ze niet allemaal direct in de toolbar passen.

---

# 25. CONTEXT ACTION BAR

Single selection:

```text
[ Bewerken ]
[ Tekening ]
[ Machine ]
[ Optimaliseren ]
[ Afdrukken ]
[ Meer ▼ ]
```

Multi BOM selection:

```text
<n> geselecteerd
[ Machine wijzigen ]
[ Optimaliseren ]
[ Afdrukken ]
[ Exporteren ]
[ Meer ▼ ]
```

Actions gebruiken exact dezelfde authoritative command route vanuit Viewer, BOM en Tree.

---

# 26. BOM V5.2

Subtabs:

```text
BOM | Machine-indeling | Optimalisatie
```

Default zichtbare kolommen:

```text
Merk / Part ID
Profiel
Materiaal
Lengte
Aantal
Gewicht
Voorgestelde machine
Toegewezen machine
Auto/Handmatig
Status
```

Optioneel via column chooser:

```text
Samenstelling
Fase
Capabilitystatus
Nestingstatus
Tekeningstatus
Scribingstatus
Exportstatus
Blockers
Source/canonical IDs
```

Geen extreem brede default tabel met alle expertkolommen.

---

# 27. MACHINE ASSIGNMENT UI

## Automatisch

Actions:

```text
Opnieuw indelen
Voorstellen toepassen
Handmatig wijzigen
```

Data:

```text
Part
Profile
Operations
Suggested machine
Suitability
Reason
Status
```

## Handmatig

```text
Machine ▼
Controleren
Toewijzen
Terug naar automatisch
```

Unsafe assignment:

- warning/error visual;
- release blocked/review;
- nooit groene fake READY.

---

# 28. PROFILE / PLATE NESTING

De UI deelt componenten, backend authorities blijven gescheiden.

Primary flow:

```text
Optimaliseren
Controleren
Accepteren
```

Secondary:

```text
Scenario's vergelijken
Vergrendelen
Ontgrendelen
Reserveren
Vrijgeven
Rapport
```

Geen knop “Optimaal” die een solverstatus forceert.

---

# 29. WORKBENCH

Layout:

- Viewer dominant;
- contextual edit panel;
- feature/operation details;
- validation area.

Actions:

```text
Controleren
Toepassen
Annuleren
Opnieuw opbouwen
```

Global undo/redo blijft authority.

---

# 30. SCRIBING

Tabs:

```text
Markeringen
Gatreferenties
Identificatie
```

Actions:

```text
Genereren
Controleren
Toepassen
Wissen
```

Geen fake apply bij invalid draft.

---

# 31. CONVERTER

Flow:

```text
Bron
Doel
Scope
Controleren
Converteren
```

Preflight zichtbaar.

Unsupported cases expliciet.

Re-import/compare als option.

---

# 32. DRAWINGS / PDF

Layout:

- settings links;
- dominante drawing/PDF preview midden;
- page/detail area rechts.

Controls:

```text
Type
Papier
Oriëntatie
Schaal
Aanzichten
Auto indelen
Genereren
Bewerken
Afdrukken
PDF opslaan
```

Geen twee primaire acties tegelijk.

---

# 33. PRINT

User-facing:

```text
Afdrukken
```

Controls:

```text
Inhoud
Scope
Printer
Papier
Oriëntatie
Aantal
Voorbeeld
Afdrukken
PDF opslaan
Batch
```

`Afdrukken` primary als printer geldig.

---

# 34. VALIDATIE / PROBLEMS

Status:

```text
Blokkade
Fout
Waarschuwing
Info
```

Acties:

```text
Opnieuw controleren
Toon object
Open oplossen
Evidence
```

Kleur nooit als enige informatie.

---

# 35. EXPORT CENTER

Flow exact:

```text
Scope
→ Formaten
→ Controleren
→ Genereren
→ Verifiëren
→ Pakket maken
```

Alleen eerstvolgende geldige stap primary.

Scope mag nooit stil uitbreiden.

---

# 36. SUPPORT SURFACE 26 — MACHINEBIBLIOTHEEK

Build verplicht.

Links:

```text
Machinegroepen
V550
V623
VB1250
THQ
Kleine lintzaag
Plate Line
```

Boven:

```text
Nieuwe machine
Dupliceren
Importeren
Exporteren
```

Midden capability matrix:

```text
Machine
Type
Profielgroepen
Materiaal
Min lengte
Max lengte
Doorsnede
Tools
Bewerkingen
Zaaghoeken
Scribing
Prioriteit
Actief
```

Rechts:

```text
Algemeen
Capaciteit
Profielen
Gereedschappen
Bewerkingen
Scribing
Routingvoorkeur
Validatie
```

Footer:

```text
Configuratie testen
Annuleren
Opslaan
```

---

# 37. SUPPORT SURFACE 27 — TEMPLATES

Links:

```text
Productietekening
Samenstelling
BOM
Machinewerklijst
Zaaglijst
Label
Nestingrapport
Projectrapport
```

Midden live page preview.

Rechts:

```text
papier
oriëntatie
marges
logo
title block
font
lineweights
revision
page numbering
PDF metadata
printer defaults
```

Actions:

```text
Voorbeeld
Standaard herstellen
Opslaan
```

---

# 38. SUPPORT SURFACE 28 — ACTIVITY CENTER

Non-modal drawer/popover.

Groups:

```text
Actief
Wachten
Gereed
Mislukt
```

Jobrow:

```text
icon
title
scope
progress
status
elapsed
Openen
Annuleren if cancellable
```

Progress alleen JobManager truth.

---

# 39. SUPPORT SURFACE 29 — PROBLEM CENTER

Global drawer.

Header:

```text
Blokkades
Fouten
Waarschuwingen
```

Row:

```text
severity
domain
object
message
Openen
Toon object
```

Click-through naar canonical object/workspace.

---

# 40. SUPPORT SURFACE 30 — DETACHED VIEWER

Zelfde project/context.

Compact:

```text
project
selection
Fit
Weergave
Terugplaatsen
```

Geen tweede main navigation.

---

# 41. SUPPORT SURFACE 31 — CTRL+K

Centered command palette.

Search:

```text
Zoek actie…
```

Groups:

```text
Navigatie
Acties voor selectie
Project
Viewer
Productie
Controle
Uitvoer
```

Result gebruikt dezelfde command en icon ID als normale UI.

---

# 42. TYPOGRAFIE

Gebruik `Segoe UI`.

Target:

```text
body              10–10.5 pt
table              9.5–10 pt
button            10 pt
secondary           9.5 pt minimum
panel heading      11.5–12 pt Semibold
workspace title    14–16 pt Semibold
top navigation     10.5–11 pt Semibold
```

Waarom niet één globale 11pt voor alles:

- engineering density moet behouden blijven;
- tabellen mogen compact blijven;
- accessibility komt uit DPI scaling + minimum readable sizes.

Geen kritieke usertekst onder 9.5pt.

---

# 43. LAYOUT — VERMIJD HARD FIXED WIDTH

Gebruik:

- layouts;
- size policies;
- stretch;
- QSplitter waar passend;
- sensible min/max widths.

Niet overal:

```python
setFixedWidth(...)
```

Hardcoded fixed width alleen waar inhoud echt fixed is.

Viewer blijft bij resize de dominante centrale ruimte houden.

---

# 44. PERSISTENCE

Maak/gebruik versioned UI preference store voor:

- theme;
- window geometry;
- splitter sizes;
- panel visibility;
- column widths/order;
- selected column preset;
- last workspace;
- optional toolbar density;
- printer preference.

Project state en user preferences gescheiden.

Test:

```text
save
close
restart
restore
```

Geen layout leakage tussen projecten waar projectstate bedoeld is.

---

# 45. TOOLTIP MASTER

Icon-only controls altijd tooltip.

Disabled context action:

```text
Niet beschikbaar omdat <reden>.
```

Geen generieke:

```text
Niet beschikbaar
```

als preciezere oorzaak bekend is.

---

# 46. SHORTCUT MASTER

Maak:

```text
validation/ui_v5_2/SHORTCUT_MASTER.json
```

Minimaal:

```text
Ctrl+O Openen
Ctrl+S Opslaan
Ctrl+P Afdrukken
Ctrl+K Snelactie
Ctrl+Z Undo
Ctrl+Y Redo
Esc Cancel actieve tool/dialoog
F Fit
```

Collision scan verplicht.

Context-sensitive shortcuts moeten precedence expliciet vastleggen.

---

# 47. TABELLEN

Shared `CwsDataTable`.

Rules:

```text
header 30–32 px
row 30 px
numeric right aligned
text left aligned
status compact
selection blue accent
hover subtle
grid subtle
```

Features waar relevant:

- sort;
- filter;
- group;
- column chooser;
- hide/show;
- reorder;
- saved layouts;
- multi-select;
- keyboard.

Geen full table rebuild op normale selection.

---

# 48. STATUSBADGES

Tekst + icon + kleur.

Voorbeelden:

```text
Gereed
Review
Geblokkeerd
Exact
Benadering
Proxy
Onbekend
Geschikt
Geschikt met waarschuwing
Niet geschikt
```

Kleur alleen ondersteunt de betekenis.

---

# 49. DIALOGEN

Centraliseer:

```text
CwsConfirmDialog
CwsErrorDialog
CwsValidationDialog
CwsMachineOverrideDialog
CwsFileConflictDialog
```

Structure:

```text
title
short explanation
impact
primary action
cancel
Details expander
```

Geen kale QMessageBox voor complexe production/safety errors indien structured evidence nodig is.

Eenvoudige info mag platformdialog blijven.

---

# 50. EMPTY / LOADING / ERROR STATES

Ieder hoofdscherm:

```text
DEFAULT
EMPTY
LOADING/BUSY
SELECTION
WARNING
ERROR
```

waar relevant.

Kritieke schermen aanvullend:

```text
multi-selection
blocked
success/ready
partial
cancelled
```

Geen lege witte pagina.

---

# 51. CRITICAL STATE SCREENSHOTS

Niet alleen default screenshot testen.

Minimaal:

## Start/Inlezen

```text
empty
source selected
loading
error
```

## Viewer

```text
loading proxy
idle
part selected
assembly selected
section
measurement
```

## BOM

```text
loaded
single select
multi select
filtered
machine warning
```

## Machine

```text
auto suggestions
manual valid
manual invalid
```

## Drawing

```text
not generated
generated valid
lint blocked
```

## Export

```text
preflight fail
ready generate
verified
```

---

# 52. SCREENSHOT ACCEPTANCE

Voor 01–25:

```text
reference
runtime
mask
diff
layout metrics
review
```

Geen SSIM-only acceptance.

Primaire gates:

```text
required controls
group order
panel hierarchy
component style
topnav
subtabs
actionbar
table structure
spacing bands
```

Secondary metric:

```text
masked chrome SSIM >= 0.94
```

Alleen stabiele chrome.

Dynamic model/table data maskeren.

---

# 53. SCREEN GEOMETRY METRICS

Meet logical rectangles van:

```text
main nav
workspace header
left panel
central content/viewer
right inspector
subtabs
primary action
context action bar
table header
status bar
```

Richtwaarde:

```text
major structure ±8 logical px
standard control height ±1 logical px
group order exact
```

DPI scaling afzonderlijk beoordelen.

---

# 54. QT RUNTIME CONTROL SCANNER

Maak scanner die CWS productcontrols vindt via:

```text
ui_test_id property
ControlRegistry
expected manifest
```

Per record:

```text
ui_test_id
objectName
type
screen
visible
enabled
label
tooltip
geometry
icon_id
shortcut
checked
handler
```

Exclusions:

- internal scrollbar child;
- Qt viewport helper;
- native file dialog internals;
- combo internal line edit tenzij expliciet productcontrol;
- platform-internal menu plumbing.

Maar iedere eigen zichtbare functionele CWS-control moet wel geregistreerd zijn.

---

# 55. FUNCTIONAL CONTROL TEST

Per control:

```text
expected context
enabled state
trigger/click
expected command
expected service
expected state mutation/output
error path
```

Test contexts:

```text
no project
project loaded
part selected
assembly selected
multi selection
valid machine
invalid machine
unassigned
nesting ready
nesting blocked
drawing absent
drawing ready
validation blocker
export preflight fail
export ready
```

Geen status-only fake.

---

# 56. USER-FACING TEXT

Gebruik `UI_TEXT_MASTER.md`.

Maak checker:

```text
validation/ui_v5_2/UI_TEXT_CONSISTENCY.json
```

Controle:

- forbidden old labels;
- duplicate synonyms;
- English/Nederlands conflict;
- legacy V9/V15/U4/M18 visible strings;
- `Print` versus `Afdrukken`;
- `Production` versus `Productie`.

Technische terms mogen onder Evidence/Details wanneer vastgelegd.

---

# 57. LEGACY FUNCTION PARITY

Maak:

```text
OLD UI CONTROL
→ NEW UI CONTROL
→ SAME COMMAND/SERVICE
→ TEST
→ STATUS
```

Statuses:

```text
PASS
MOVED
MERGED_PRESENTATION_ONLY
FAIL
BLOCKED
```

`MERGED_PRESENTATION_ONLY` mag alleen als backendfunctionaliteit volledig behouden is.

Doel:

```text
required legacy function loss = 0
```

---

# 58. UI PERFORMANCE

De nieuwe UI mag de Viewer niet vertragen.

Verboden:

- blur backgrounds;
- realtime drop shadows over grote panels;
- zware animations;
- per-frame stylesheet rebuild;
- per-cell SVG render zonder cache.

Targets:

```text
simple workspace switch feedback < 100 ms
context menu open < 100 ms
table selection feedback < 100 ms
Problem Center open < 100 ms
Activity Center open < 100 ms
```

Zware acties gaan async via JobManager.

---

# 59. DPI / RESOLUTION

Test:

```text
1366x768 @ 100%
1920x1080 @ 100%
1920x1080 @ 125%
2560x1440 @ 100%
2560x1440 @ 150%
3840x2160 @ 150%
3840x2160 @ 200%
```

Hard:

```text
clipped primary controls = 0
overlap = 0
offscreen modal primary action = 0
unreadable core text = 0
```

Als echte 4K environment niet beschikbaar:

status `NOT_TESTED`, niet fake PASS.

---

# 60. LIGHT EN DARK

Light is primary release SSOT.

Dark is secundaire feature wanneer V5.1 dat vereist.

Dark acceptance minimaal:

- no unreadable text;
- no white-on-white;
- no lost icons;
- no invisible selection;
- status semantics preserved.

Maar dark hoeft niet pixelmatch met Light-reference te halen.

---

# 61. ACCESSIBILITY

Minimaal:

- keyboard focus visible;
- Tab;
- Shift+Tab;
- Enter;
- Space;
- Esc;
- accessibleName voor icon-only CWS controls;
- adequate text contrast;
- status niet alleen kleur.

Doel text contrast ongeveer 4.5:1 waar normaal toepasbaar.

---

# 62. PACKAGING

Icon/style/reference resources moeten in:

- source run;
- one-folder;
- portable;
- installer

beschikbaar zijn.

Geen developer-filesystem dependency.

Test:

```text
missing icons = 0
missing stylesheet = 0
missing reference assets for tests = 0
fallback blank icon = 0
```

---

# 63. EXACT DRIE BOUWFASEN

Deze UI-build wordt in exact drie fasen uitgevoerd.

---

# ======================================================================
# FASE 1 — AUDIT + DESIGN SYSTEM + 100% CONTROL BINDING
# ======================================================================

## 64. FASE 1 OPDRACHT

Bouw nog niet meteen alle schermen om.

Eerst:

1. actuele repo baseline;
2. huidige Qt surface/control inventory;
3. old-to-new screen map;
4. old-to-new action map;
5. design system;
6. tokens;
7. explicit icon registry;
8. `ui_test_id` infrastructure;
9. ControlRegistry;
10. visual binding voor 100% van expected controls;
11. central stylesheet;
12. persistence foundation;
13. reference assets versioned in repo.

## 65. FASE 1 DELIVERABLES

```text
docs/ui/v5_2/REFERENCE_MANIFEST.json
docs/ui/v5_2/REFERENCE_SHA256SUMS.txt

validation/ui_v5_2/
  CURRENT_UI_SURFACE_INVENTORY.json
  CURRENT_UI_CONTROL_INVENTORY.json
  LEGACY_QSS_MIGRATION_MATRIX.json
  OLD_TO_NEW_SCREEN_MAP.json
  UI_FUNCTION_PARITY_BASELINE.json
  VISUAL_TOKENS.json
  ICON_MASTER.json
  CONTROL_VISUAL_BINDING.json
  SHORTCUT_MASTER.json
  UI_PREFERENCES_SCHEMA.json
  PHASE_1_UI_FOUNDATION_REPORT.md
  PHASE_1_UI_FOUNDATION_REPORT.json
```

## 66. FASE 1 HARD GATE

```text
canonical HEAD recorded = PASS
reference assets accessible from fresh checkout = PASS
expected control count derived = PASS
control visual binding = 100%
unknown icon IDs = 0
duplicate ui_test_id = 0
design system source exists = PASS
old/new navigation decision = PASS
function parity baseline complete = PASS
```

Geen Fase 2 voordat dit groen is.

---

# ======================================================================
# FASE 2 — BOUW ALLE 31 SCREENS/SURFACES EN ALLE CONTROLS
# ======================================================================

## 67. FASE 2 OPDRACHT

Migreer scherm voor scherm naar V5.2.

Volgorde:

```text
1 shell/topnav
2 Project
3 Viewer
4 Productie BOM/Machines
5 Workbench
6 Scribing
7 Nesting
8 Drawing/PDF
9 Converter
10 Controle
11 Uitvoer
12 support surfaces 26–31
```

Na ieder scherm:

- compile;
- targeted Qt test;
- control coverage;
- screenshot;
- function parity;
- commit.

## 68. SCREEN IMPLEMENTATION MATRIX

Per screen:

```text
screen_id
reference
old surfaces replaced
new surface
expected controls
present controls
functional controls
missing
layout status
states status
DPI status
screenshot status
legacy parity
packaged smoke
```

## 69. FASE 2 SUPPORT REFERENCES

Voor 26–31:

- build textual spec;
- capture runtime reference;
- mark pending;
- compare against component rules;
- freeze only after acceptance.

## 70. FASE 2 HARD GATE

```text
01–25 implemented = 25/25
26–31 implemented = 6/6
expected controls present = 100%
enabled dead controls = 0
function loss = 0
topnav exact = PASS
default Light = PASS
white panel system = PASS
context actions = PASS
Viewer persistence = PASS
BOM V5 = PASS
support surfaces = PASS
```

---

# ======================================================================
# FASE 3 — VISUAL + FUNCTIONAL + DPI + PACKAGED WINDOWS ACCEPTANCE
# ======================================================================

## 71. FASE 3 OPDRACHT

Voer totale UI-acceptance uit op de echte app.

Niet alleen source/headless.

## 72. TESTLAGEN

### Source

- unit;
- static manifests;
- text consistency;
- icon registry;
- duplicate IDs.

### Integrated Qt

- runtime scanner;
- click tests;
- states;
- keyboard;
- screen routing;
- persistence.

### Packaged Windows

- one-folder;
- fresh portable;
- installer where global releasephase dit bouwt;
- resources;
- screenshots;
- DPI.

---

# 73. VISUAL TESTSET

01–25:

- default screenshot;
- critical states zoals gedefinieerd.

26–31:

- accepted generated references + runtime compare.

Light primary.

Dark smoke.

---

# 74. CONTROL ACCEPTANCE

Produceer:

```text
expected_controls
runtime_controls
mapped_controls
functional_pass
missing
unexpected_owned_controls
dead
duplicate_ids
wrong_label
wrong_icon
wrong_handler
missing_tooltip
shortcut_collision
```

Final:

```text
missing = 0
dead = 0
duplicate = 0
wrong handler = 0
```

---

# 75. PACKAGE ACCEPTANCE

Fresh portable:

```text
extract empty dir
start
open fixture
navigate all 5 main workspaces
open 31 surfaces
exercise representative controls
Viewer works
icons present
Light default
save/restart
```

No developer PATH.

---

# 76. FASE 3 DELIVERABLES

```text
validation/ui_v5_2/
  SCREEN_IMPLEMENTATION_MATRIX.json
  SCREEN_IMPLEMENTATION_MATRIX.md

  RUNTIME_CONTROL_INVENTORY.json
  CONTROL_RUNTIME_COVERAGE.json
  CONTROL_RUNTIME_COVERAGE.md

  UI_FUNCTION_PARITY_FINAL.json
  UI_FUNCTION_PARITY_FINAL.md

  UI_TEXT_CONSISTENCY.json
  UI_ICON_ACCEPTANCE.json
  UI_SHORTCUT_ACCEPTANCE.json
  UI_KEYBOARD_ACCEPTANCE.json
  UI_PERSISTENCE_ACCEPTANCE.json
  UI_DPI_ACCEPTANCE.json
  UI_VISUAL_ACCEPTANCE.json
  UI_PACKAGED_ACCEPTANCE.json

  screenshots/
    screen_01/
    ...
    screen_31/

  FINAL_UI_V5_2_ACCEPTANCE.json
  FINAL_UI_V5_2_ACCEPTANCE.md
```

---

# 77. FINAL UI REPORT

Exacte samenvatting:

```text
CWS UI V5.2 CONTROL BUILD

Branch:
Commit40:
Version:
Worktree clean:

Main navigation:
Project | Viewer | Productie | Controle | Uitvoer
PASS/FAIL

Theme:
Default Light:
White content surfaces:
Dark secondary:
PASS/FAIL

Screens 01–25:
Expected: 25
PASS:
FAIL:

Support surfaces 26–31:
Expected: 6
PASS:
FAIL:
Pending reference approval:

Controls:
Expected:
Mapped:
Runtime found:
Functional PASS:
Missing:
Dead:
Unexpected owned:
Duplicate IDs:
Wrong handlers:

Icons:
Defined:
Bound:
Missing:
Semantic conflicts:
Packaging failures:

Text:
Wrong labels:
Legacy user-facing dev labels:

DPI:
100:
125:
150:
200:

Keyboard:
PASS/FAIL

Persistence:
PASS/FAIL

Legacy functional parity:
PASS/FAIL

Packaged Windows:
PASS/FAIL

V5.2 UI CONTROL BUILD:
PASS / FAILED
```

---

# 78. FINAL PASS

`V5.2 UI CONTROL BUILD = PASS`

alleen als:

1. exacte vijf hoofdworkspaces bestaan;
2. default Light;
3. witte panel/content surfaces;
4. 25/25 V5 visual screens correct;
5. 6/6 support surfaces gebouwd;
6. 100% expected controls gemapt;
7. missing controls = 0;
8. dead controls = 0;
9. duplicate ui_test_id = 0;
10. icon semantics = PASS;
11. label/text consistency = PASS;
12. disabled reasons = PASS;
13. Viewer context preserved;
14. BOM/machine contextactions correct;
15. layout/DPI PASS;
16. keyboard PASS;
17. persistence PASS;
18. legacy functional loss = 0;
19. packaged Windows resources PASS;
20. visual acceptance PASS.

---

# 79. RELATIE MET DE ALGEMENE GAP-CLOSURE PROMPT

Deze UI build hoort inhoudelijk bij de algemene **Fase 2** van:

`CWS GAP CLOSURE VIEWER V5`

Maar deze prompt mag zelfstandig aan Codex worden gegeven.

Wanneer beide prompts tegelijk gebruikt worden:

- Fase 1 van algemene gap-closure = Viewer performance;
- daarna deze volledige V5.2 UI-build;
- daarna algemene finale acceptance/release.

De hoofdnavigatie uit deze V5.2 prompt is bindend en corrigeert de oudere afwijkende passage.

---

# 80. START NU

Begin met:

```text
1 fetch current canonical HEAD
2 read V5.1 handover
3 read 25 references
4 read screen manifest
5 read control inventory
6 scan current Qt surfaces
7 scan current QSS and inline styles
8 scan current icon helper
9 establish expected control count
10 create old→new map
11 create design system
12 create IconRegistry
13 add ui_test_id property system
14 create CONTROL_VISUAL_BINDING
15 run Fase 1 gate
```

Daarna:

**bouw alle schermen daadwerkelijk.**

Geen extra vraag stellen wanneer de requirements uit de supplied package ondubbelzinnig zijn.

Geen cosmetische PASS zonder runtime bewijs.
