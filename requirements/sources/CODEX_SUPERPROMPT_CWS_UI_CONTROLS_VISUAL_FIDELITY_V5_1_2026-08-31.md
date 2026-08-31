# CODEX ADDENDUM-SUPERPROMPT
## CWS Convertor UI Master V5.1 FINAL
## Exacte visuele control-binding: alle knoppen, iconen, states, toolbars, contextacties, dialogen en ondersteunende schermen
### Doel: Codex voert uit; Codex ontwerpt niet zelfstandig

---

# 0. STATUS VAN DIT DOCUMENT

Dit document is een **bindende UI-uitwerkingslaag** bovenop:

- `CODEX_SUPERPROMPT_CWS_UI_MASTER_V5_1_FINAL_3_FASEN_2026-08-31.md`
- `SCREEN_MANIFEST.json`
- `CONTROL_INVENTORY_MASTER.json`
- `UI_COMPONENT_CATALOG.md`
- `UI_TEXT_MASTER.md`
- `DO_NOT_CHANGE.md`
- `UI_BINDING_ACCEPTANCE.md`
- de 25 V5 PNG-referenties
- de actuele repository

Gebruik dit document primair tijdens **Fase 2 — V5.1 UI + productiecompleetheid** van de algemene gap-closure-opdracht.

Dit document vervangt de functionele waarheid niet.

Het vult specifiek de ontbrekende laag aan:

> **hoe iedere control eruitziet, waar hij staat, welke iconografie hij gebruikt, hoe states worden getoond en hoe visuele gelijkheid wordt bewezen.**

---

# 1. ABSOLUTE OPDRACHT

Voer de V5.1 UI niet uit als een vrije interpretatie.

Bouw de UI als een **contractgestuurd Qt-product** waarbij voor iedere zichtbare interactieve control de volgende twee waarheden samenkomen:

```text
FUNCTIONELE WAARHEID
CONTROL_INVENTORY_MASTER.json
        +
VISUELE WAARHEID
deze prompt + V5 PNG + UI_COMPONENT_CATALOG
        ↓
WERKENDE QT CONTROL
```

Codex mag:

- implementeren;
- bestaande widgets refactoren;
- stijlen centraliseren;
- herbruikbare Qt-components maken;
- bestaande controls naar de juiste plek verplaatsen;
- missing states toevoegen;
- missing icon assets als originele/licentiegeschikte SVG maken.

Codex mag NIET:

- zelf een afwijkend visueel concept kiezen;
- controls schrappen om een scherm rustiger te maken;
- extra grote web-dashboardcards introduceren;
- willekeurige iconen kiezen;
- verschillende iconen gebruiken voor dezelfde actie;
- verschillende knopstijlen gebruiken voor dezelfde actieklasse;
- dark mode als default gebruiken;
- een zichtbaar functioneel element als mock/fake UI laten bestaan;
- een button toevoegen zonder `test_id`, handler en acceptance;
- een bestaand backend/servicecontract dupliceren vanwege UI-gemak.

---

# 2. PRIORITEIT BIJ CONFLICT

Gebruik deze volgorde:

1. actuele expliciete gebruikersrequirement;
2. `DO_NOT_CHANGE.md`;
3. deze Visual Control Fidelity prompt;
4. `SCREEN_MANIFEST.json`;
5. `CONTROL_INVENTORY_MASTER.json` voor functionaliteit;
6. bijbehorende V5 PNG voor schermstructuur;
7. `UI_COMPONENT_CATALOG.md`;
8. `UI_TEXT_MASTER.md`;
9. actuele canonical backend/servicecontracten;
10. V4 uitsluitend als algemene stijlreferentie.

Belangrijk:

- voor **wat een knop doet** wint de control inventory/backend authority;
- voor **waar en hoe de knop wordt weergegeven** wint deze prompt + V5 reference;
- een PNG mag nooit worden gebruikt om een fake functionaliteit te rechtvaardigen.

---

# 3. DEFAULT THEME = LIGHT — HARDE INVARIANT

De officiële V5/V5.1 productweergave is standaard **licht**.

Release-, comparison- en acceptance-screenshots worden standaard in Light uitgevoerd.

Gebruik bij 100% Windows scaling de volgende logical UI tokens:

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

### Hard gate

```text
default_theme = LIGHT
main_work_surface = #FFFFFF
app_background = #F4F7FA
dark_theme_default = FAIL
```

Dark mode mag bestaan als user preference, maar:

- geen dark screenshot als primaire V5-reference;
- geen dark-only styling;
- alle components moeten eerst in Light volledig correct zijn.

---

# 4. VISUELE TAAL

De app moet eruitzien als een professionele Windows engineering-app.

Wel:

- wit;
- lichtgrijs;
- subtiele grijsblauwe borders;
- donkerblauwgrijze topnav;
- blauwe primaire acties;
- compacte controls;
- heldere tabelstructuur;
- beperkte rounded corners;
- vaste iconografie;
- rustige informatiehiërarchie.

Niet:

- webdashboard;
- extreem afgeronde cards;
- grote gradientblokken;
- neon;
- grote marketingillustraties;
- oversized headings;
- enorme lege margins;
- elke sectie een losse floating card;
- willekeurige kleuren per feature.

---

# 5. LOGICAL PIXEL GRID

Alle maatvoering hieronder is in Qt logical pixels op 100% scaling.

Qt/DPI schaalt proportioneel.

Gebruik een 4px spacing grid.

Basis:

```text
2 px   micro
4 px   compact
8 px   standard
12 px  panel inset
16 px  section separation
24 px  major separation
```

### Paneel

```text
panel padding        10–12 px
panel gap            8 px
panel border         1 px
panel radius         3–4 px
```

### Controlhoogtes

```text
toolbar icon button        28–30 px
compact button             28 px
standard button            30–32 px
context action button      32 px
combo / edit               30–32 px
tab                        34–36 px
top navigation             40 px target
table row                  30 px target
status bar                 26 px target
```

Geen control die per scherm spontaan 4–8 px hoger/lager wordt zonder componentvariant.

---

# 6. TYPOGRAFIE

Gebruik Windows-native:

```text
Segoe UI
```

Fallback alleen wanneer nodig.

Logical font targets:

```text
body                   10.5–11 pt
table                   10–10.5 pt
small secondary         minimaal 9.5 pt
button                  10–10.5 pt
panel heading           11.5–12 pt Semibold
workspace title         14–16 pt Semibold
top navigation          10.5–11 pt Semibold
status badge            9.5–10 pt Semibold
```

Verboden:

- zeer kleine 7–8 pt functionele labels;
- ultralight;
- full caps voor normale labels;
- fontwissels per scherm.

---

# 7. VERPLICHTE COMPONENTCLASSES

Bouw één gedeelde componentbibliotheek.

Minimaal:

```text
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
CwsTopNavigation
CwsSubTabs
CwsWorkspaceHeader
CwsActionBar
CwsViewerToolbar
CwsDataTable
CwsInspectorPanel
CwsSearchField
CwsFilterButton
CwsInlineMessage
CwsEmptyState
CwsActivityCenter
CwsProblemCenter
CwsModalDialog
CwsPopover
CwsCommandPalette
```

Hard:

```text
same semantic component = same base style everywhere
```

Geen lokale stylesheet-copy per screen als dezelfde componentklasse bestaat.

---

# 8. BUTTON MASTER

## 8.1 CwsPrimaryButton

Gebruik voor de primaire vervolgstap van de actuele taak.

Voorbeelden:

- `Inladen`
- `Genereren`
- `Afdrukken`
- `Toepassen`
- `Voorstellen toepassen`
- `Optimaliseren`

Style:

```text
height       32 px
min width    88 px
padding      0 12 px
radius       4 px
border       none
background   accent.primary
text         text.on_primary
font         Semibold
icon         18 px
icon gap     6 px
```

Normal:
- `#1F6FA8`

Hover:
- `#185B8A`

Pressed:
- `#12496E`

Focus:
- 1–2 px focus ring buiten control, niet layoutverschuivend.

Disabled:
- neutraal grijs;
- geen blauwe misleading state;
- tooltip bevat reden wanneer actie contextueel logisch is.

Rule:

> maximaal één duidelijke primary action per lokale taakgroep.

Niet iedere blauwe knop is primary.

---

## 8.2 CwsSecondaryButton

Voor normale acties:

```text
height       32 px
background   #FFFFFF
border       1 px #AEBECD
text         #1F2D3D
radius       4 px
```

Hover:
- `#EEF4F8`

Pressed:
- `#E2EBF1`

Focus:
- `focus.ring`

---

## 8.3 CwsCompactButton

Voor compacte forms en tabelacties.

```text
height       28 px
padding      0 9 px
icon         16 px
```

Geen primary styling tenzij expliciet variant.

---

## 8.4 CwsToolButton

Voor Viewer/camera/table toolbars.

Icon-only wanneer icoon voldoende herkenbaar is.

```text
size         30 x 30 px
icon         18 px
radius       3 px
background   transparent/white
border       transparent
```

Hover:
- `surface.hover`

Pressed:
- `surface.selected`

Checked:
- `accent.soft`
- border `accent.primary`
- icon/text primary.

Iedere icon-only control heeft tooltip.

---

## 8.5 CwsToggleToolButton

Voor modes:

- Orbit;
- Pan;
- Select;
- Measurement mode;
- Section mode;
- Ghost;
- rendering mode where toggle.

Checked state is altijd zichtbaar.

Niet alleen met een veranderend icoontje van 1 px verschil.

---

## 8.6 CwsContextActionButton

Belangrijk voor Viewer/BOM/Production.

Height 32 px.

Default combinatie:

```text
[icon 18] [label]
```

Do not use huge colored tiles.

Default contextacties, in deze volgorde wanneer geldig:

```text
Bewerken
Tekening
Machine
Optimaliseren
Afdrukken
Meer
```

Bij beperkte breedte:

- labels mogen via responsive policy verminderen;
- belangrijke controls blijven bereikbaar;
- nooit stil verdwijnen.

---

## 8.7 CwsDangerButton

Alleen:

- permanent delete;
- irreversible discard;
- destructive reset waar relevant.

Normale `Annuleren` is NIET rood.

Normale `Verwijderen` kan secondary met rood icoon/tekst zijn; echte destructive confirmation mag Danger variant gebruiken.

---

## 8.8 CwsMenuButton

Voor:

- `Meer`
- filter preset
- context action collections.

Gebruik chevron/down indicator.

Menu item spacing consistent.

---

## 8.9 CwsSplitButton

Alleen wanneer:

- één standaardactie vaak gebruikt wordt;
- alternatieve output naast dezelfde actie logisch is.

Niet gebruiken om een onduidelijke workflow te verbergen.

---

# 9. BUTTON STATE MASTER

Iedere control moet minimaal deze states hebben wanneer technisch relevant:

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

## Disabled

Disabled state:

- minder contrast;
- geen fake green/blue active appearance;
- cursor/default platform behavior;
- tooltip:
  `Niet beschikbaar omdat …`

## Busy

Bij async taak:

- button dubbelklikken mag geen tweede job starten;
- label mag tijdelijk bijvoorbeeld `Bezig…` worden;
- spinner/progress alleen wanneer echt aan JobManager gekoppeld;
- cancel button apart waar cancellation supported.

## Warning

Waarschuwing hoort primair in data/status/inline message.

Maak een normale actie niet automatisch oranje tenzij de actie zelf “review uitvoeren” betekent.

## Error

Rood voor foutstatus, niet als algemeen accent.

---

# 10. ICON MASTER — ABSOLUTE REGELS

Bouw één `ICON_MASTER.json`.

Iedere action `test_id` verwijst naar één `icon_id`.

Geen iconengokwerk per screen.

## 10.1 Vector

Gebruik SVG/vector.

Geen PNG icon sprites tenzij technisch onvermijdelijk.

Gebruik één consistente, licentiegeschikte of originele iconfamilie.

Geen proprietary Trimble-assets.

Geen emoji.

Geen font-icon afhankelijkheid die in packaged Windows kan ontbreken.

## 10.2 Style

Target:

```text
viewbox      24x24
stroke       ongeveer 1.75–2 logical units
round cap    ja
round join   ja
fill         none voor standaard iconen
```

Statusiconen mogen beperkt filled zijn.

## 10.3 Sizes

```text
compact/table          16 px
normal button          18 px
toolbar                18 px
context action         18–20 px
status                 16 px
exceptional major      max 20–22 px
```

Geen 28–32 px iconen in normale desktop toolbar.

---

# 11. VERPLICHTE SEMANTISCHE ICONEN

Gebruik één vaste betekenis.

Voorbeeld icon IDs:

```text
action.open_file
action.open_folder
action.import
action.save
action.save_as
action.undo
action.redo
action.close
action.cancel

nav.project
nav.viewer
nav.production
nav.control
nav.output

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
viewer.orbit
viewer.pan
viewer.zoom_area
viewer.hide
viewer.show
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
production.more

bom.search
bom.filter
bom.group
bom.columns
bom.sort
bom.export

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

Wanneer een nieuw icon ID nodig is:

1. voeg eerst toe aan `ICON_MASTER.json`;
2. definieer betekenis;
3. definieer SVG asset;
4. pas daarna toe.

---

# 12. VERBODEN ICONOGRAFIE

Niet gebruiken:

- tandwiel voor zowel `Machine` als `Instellingen`;
- oog-icoon voor zowel `Show all` als `Preview`;
- printer-icoon voor `PDF opslaan`;
- download-icoon als algemene `Exporteren` én `Opslaan`;
- willekeurige cube-icons voor vijf verschillende Viewerfuncties;
- rood kruis als normale Close van paneel wanneer het foutstatus suggereert.

Semantiek moet uniek en herkenbaar blijven.

---

# 13. CONTROL-TO-VISUAL BINDING

Maak:

```text
CONTROL_VISUAL_BINDING.json
```

Voor iedere entry uit `CONTROL_INVENTORY_MASTER.json`.

Geen exception.

Schema per control:

```json
{
  "test_id": "btn_bom_machine",
  "screen_id": "11",
  "label": "Machine",
  "visual_component": "CwsContextActionButton",
  "variant": "secondary",
  "icon_id": "production.machine",
  "icon_position": "left",
  "show_label": true,
  "group_id": "bom.selection.actions",
  "group_order": 3,
  "placement_zone": "bottom_context_action_bar",
  "width_policy": "content",
  "height_px": 32,
  "shortcut": null,
  "checked_state": false,
  "busy_state": false,
  "disabled_reason_template": "Selecteer eerst één of meer onderdelen.",
  "tooltip": "Wijzig de machine voor de geselecteerde onderdelen.",
  "reference_screen": "11_PRODUCTIE_BOM_Machines_BOM.png"
}
```

Gates:

```text
expected controls          226
visual bindings            226
missing                    0
duplicate test_id          0
unknown visual component   0
unknown icon_id            0
```

Als de actuele control inventory door een latere bindende wijziging meer controls bevat:

- 100% van de actuele set mappen;
- niet blijven hangen op letterlijk 226.

---

# 14. CONTROL GROUPS

Iedere screen definieert groepen.

Voorbeeld BOM:

```text
bom.navigation
bom.search_filter
bom.view_configuration
bom.selection.actions
bom.export
```

Viewer:

```text
viewer.selection
viewer.camera
viewer.visibility
viewer.analysis
viewer.context.actions
```

Drawing:

```text
drawing.document_setup
drawing.views
drawing.layout
drawing.output
```

Groups zijn visueel gescheiden door:

- 8–12 px ruimte;
- subtiele separator;
- group heading alleen wanneer nodig.

Geen toolbar met 25 onafgebroken iconen.

---

# 15. GLOBAL SHELL — EXACTE STRUCTUUR

## Topbar

Gebruik overal dezelfde hoofdbar.

Volgorde:

```text
[Product/logo]
Project
Viewer
Productie
Controle
Uitvoer

                         Undo Redo
                         Activiteit
                         Problemen
                         Instellingen
```

Geen tweede globale nav links.

### Top navigation

- dezelfde hoogte op alle schermen;
- active item zichtbaar;
- geen grote pill buttons;
- app-level nav blijft staan tijdens workspacewisseling.

### Activity

Badge alleen als er actieve/niet-gelezen relevante jobstatus is.

### Problems

Badge:

- rood voor blockers/errors;
- oranje voor warnings;
- geen groene badge als er niets te melden is.

---

# 16. VIEWER TOOLBAR — ONTWERP HIER ZELF NIET VAN AF

Viewer blijft centraal en rustig.

Gebruik maximaal een compacte toolbar met logische clusters.

Aanbevolen structuur:

```text
SELECTIE
[Selectieniveau ▼]

CAMERA
[Fit] [Voor] [Boven] [ISO] [Projectie ▼]

WEERGAVE
[Verbergen] [Isoleren] [Ghost] [Alles tonen]

ANALYSE
[Meten] [Doorsnede]

[Meer ▼]
```

Orbit/pan gedrag mag default mouse navigation zijn.

Wanneer expliciete mode-buttons nodig zijn:

- compact;
- checked state zichtbaar;
- niet dubbel met standaard mouse controls.

### Responsive Viewer

Bij kleinere breedte:

- minder belangrijke labels mogen icon-only worden;
- groepen mogen in `Meer` verplaatsen volgens vaste prioriteit;
- `Fit`, selectie, hide/isolate, measure/section blijven goed bereikbaar.

---

# 17. VIEWER CONTEXT ACTION BAR

Bij selectie:

```text
[ Bewerken ] [ Tekening ] [ Machine ] [ Optimaliseren ] [ Afdrukken ] [ Meer ▼ ]
```

Rules:

- verschijnt/activeert op context;
- selectieaantal zichtbaar indien multi;
- geen lokale alternatieve knoplabels;
- gebruikt exact dezelfde command handlers als BOM contextacties;
- hidden only als actie productmatig niet bestaat voor dat entity type.

---

# 18. BOM — EXACTE ACTIEHIËRARCHIE

Scherm 11:

boven lokale subtabs:

```text
BOM | Machine-indeling | Optimalisatie
```

boven tabel:

```text
[Zoeken________________]
[Filter]
[Groeperen]
[Kolommen]
```

Een primaire exportactie hoeft niet permanent dominant te zijn wanneer contextacties belangrijker zijn.

Onderaan bij selectie:

```text
<n> geselecteerd
[ Bewerken ]
[ Tekening ]
[ Machine ]
[ Optimaliseren ]
[ Afdrukken ]
[ Meer ▼ ]
```

### Multi-select

Bij meerdere regels:

```text
36 geselecteerd
[ Machine wijzigen ]
[ Optimaliseren ]
[ Afdrukken ]
[ Exporteren ]
[ Meer ▼ ]
```

Gebruik geen twee verschillende action bars tegelijk.

---

# 19. MACHINE-INDDELING

Auto screen:

primaire actie:

```text
[ Opnieuw indelen ]
```

daarnaast:

```text
[ Voorstellen toepassen ]
[ Handmatig wijzigen ]
```

Capability status is data/status, geen buttonkleurencircus.

Machine details rechts:

- reason;
- capability;
- limits;
- operations;
- warnings.

`Voorstellen toepassen` alleen primary als de actuele computed suggestions geldig zijn.

---

# 20. HANDMATIGE MACHINE-OVERRIDE

Layout:

```text
geselecteerde parts
→ machine chooser
→ capability result
→ apply
```

Buttons:

```text
[ Controleren ]
[ Toewijzen ]
[ Terug naar automatisch ]
```

Een ongeschikte machinekeuze:

- rood/oranje statuspaneel;
- geen green primary success appearance;
- release blijft blocked/review.

---

# 21. PROFILE / PLATE NESTING

Gebruik dezelfde action-class voor beide.

Core bar:

```text
[ Optimaliseren ]
[ Scenario's vergelijken ]
[ Controleren ]
[ Accepteren ]
```

Secondary:

```text
[ Vergrendelen ]
[ Ontgrendelen ]
[ Reserveren ]
[ Reservering vrijgeven ]
[ Rapport ]
```

Plate-specific icons verschillen semantisch van profile nesting, maar styling niet.

---

# 22. WORKBENCH

Primaire edit flow:

```text
[ Controleren ] [ Toepassen ]
```

`Toepassen` primary wanneer edit dirty + validation state allows.

`Annuleren` secondary.

`Opnieuw opbouwen` secondary/technical action.

Undo/redo global; lokale workbench buttons alleen wanneer functioneel nodig en exact dezelfde authority gebruiken.

---

# 23. SCRIBING

Tabs:

```text
Markeringen | Gatreferenties | Identificatie
```

Actions:

```text
[ Genereren ]
[ Controleren ]
[ Toepassen ]
[ Wissen ]
```

`Genereren` is niet automatisch “accept”.

`Toepassen` pas enabled bij valide draft.

---

# 24. CONVERTER

Flow visueel links→rechts/boven→onder:

```text
Bron
Doel
Scope
↓
Controleren
↓
resultaat/capabilities
↓
Converteren
```

Primary:

```text
[ Converteren ]
```

maar disabled totdat preflight geldig is.

Geen grote knop die zonder scope direct output maakt.

---

# 25. TEKENINGEN / PDF

Links instellingen.

Midden dominante preview.

Actions:

```text
[ Auto indelen ]
[ Genereren ]
[ Bewerken ]
[ Afdrukken ]
[ PDF opslaan ]
```

Primary is context-afhankelijk:

- vóór generation: `Genereren`;
- na geldige generation: `Afdrukken` of `PDF opslaan` niet beide visueel dominant.

`PDF opslaan` gebruikt PDF/document icon, niet printer.

---

# 26. AFDRUKKEN / PRINT CENTER

User-facing naam:

`Afdrukken`

Niet overal `Print Center` tonen.

Bottom/right final actions:

```text
[ Voorbeeld ]
[ PDF opslaan ]
[ Afdrukken ]
```

`Afdrukken` primary indien fysieke printer geselecteerd en geldig.

Batch:

- secondary;
- opent settings, geen stille batchstart.

---

# 27. VALIDATIE / PROBLEM CENTER

Status gebruikt kleur semantisch.

Nooit kleur als enige informatie.

Iedere row:

- statusicoon;
- severitytekst;
- object;
- melding;
- source/workspace action.

Actions:

```text
[ Toon object ]
[ Open oplossen ]
[ Evidence ]
```

`Opnieuw controleren` bovenaan.

---

# 28. EXPORT CENTER

Exacte flow:

```text
1 Scope
2 Formaten
3 Controleren
4 Genereren
5 Verifiëren
6 Pakket maken
```

Toon state-progress zonder wizard-gimmicks die veel ruimte innemen.

Buttons:

- `Controleren`
- `Genereren`
- `Verifiëren`
- `Pakket maken`

Alleen één primary op basis van eerstvolgende geldige stap.

---

# 29. RAPPORT / PROJECT READY

Groen `Project gereed` alleen wanneer authoritative gate PASS is.

Geen handmatige toggle.

Blockers/warnings zichtbaar.

Actions:

```text
[ Status vernieuwen ]
[ Open blokkade ]
[ Rapport opslaan ]
[ Rapport afdrukken ]
[ Productiepakket ]
```

`Productiepakket` alleen enabled wanneer interne gates groen zijn.

---

# 30. ONDERSTEUNEND SCHERM 26 — MACHINEBIBLIOTHEEK

Er is mogelijk nog geen bindende PNG.

Daarom is deze layout bindend totdat een latere reference PNG hem vervangt.

### Links — Machines

Breedte circa 260–320 logical px.

Groups:

```text
Zaag-/boorlijnen
  V550
  V623
  VB1250
  THQ
  Kleine lintzaag

Plaat
  Plate Line
```

Toolbar:

```text
[ Nieuwe machine ]
[ Dupliceren ]
[ Importeren ▼ ]
[ Exporteren ▼ ]
```

### Midden — Capability matrix

Columns minimaal:

```text
Machine
Type
Profielgroepen
Min lengte
Max lengte
Min doorsnede
Max doorsnede
Tools
Bewerkingen
Zaaghoeken
Scribing
Prioriteit
Actief
```

### Rechts — Detail

Sections:

```text
Algemeen
Capaciteit
Profielgroepen
Gereedschappen
Bewerkingen
Scribing
Routingvoorkeur
Validatie
```

Footer:

```text
[ Configuratie testen ]
[ Annuleren ]
[ Opslaan ]
```

`Opslaan` primary.

---

# 31. ONDERSTEUNEND SCHERM 27 — PDF/PRINT & TEKENINGTEMPLATES

### Links

Template tree:

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

### Midden

Live page preview.

### Rechts

Properties:

```text
papier
oriëntatie
marges
logo
title block
font
lineweights
revision fields
page numbering
printer defaults
PDF metadata
```

Footer:

```text
[ Voorbeeld ] [ Standaard herstellen ] [ Opslaan ]
```

---

# 32. ONDERSTEUNEND SCHERM 28 — ACTIVITY CENTER

Geen volledig groot workspace nodig voor dagelijkse flow.

Primair een non-modal side drawer/popover.

Elke jobrow:

```text
icon
job title
scope
progress
status
elapsed
[Openen]
[Annuleren] if cancellable
```

Groups:

```text
Actief
Wachten
Gereed
Mislukt
```

Geen fake progress.

---

# 33. ONDERSTEUNEND SCHERM 29 — PROBLEM / STATUS CENTER

Global drawer/popover.

Header:

```text
Blokkades <n>
Fouten <n>
Waarschuwingen <n>
```

Rows:

```text
severity
domain
object
message
[Openen]
[Toon object]
```

Click row:

- select exact object;
- open owning workspace when requested.

---

# 34. ONDERSTEUNEND SCHERM 30 — DETACHED VIEWER

Detached window:

- zelfde Viewer projectcontext;
- geen bron opnieuw inladen;
- geen tweede BOM;
- geen tweede selection authority.

Minimal header:

```text
project
selection
[Fit]
[Weergave]
[Terugplaatsen]
```

Geen complete tweede CWS-main navigation nodig.

---

# 35. ONDERSTEUNEND SCHERM 31 — COMMAND PALETTE / CTRL+K

Centered overlay.

Input:

```text
Zoek actie…
```

Grouped results:

```text
Navigatie
Acties voor selectie
Project
Viewer
Productie
Uitvoer
```

Iedere result gebruikt dezelfde icon ID en command handler als gewone UI.

Geen command die alleen in palette bestaat zonder registry.

---

# 36. TOOLTIP MASTER

Maak voor iedere icon-only of niet-volledig-zelfverklarende control een tooltip.

Formule:

```text
<actie>.
```

Disabled:

```text
Niet beschikbaar omdat <concrete reden>.
```

Voorbeelden:

```text
Isoleer de geselecteerde onderdelen.
Pas de geldige machinevoorstellen toe.
Niet beschikbaar omdat geen onderdeel is geselecteerd.
Niet beschikbaar omdat de exportcontrole nog niet is uitgevoerd.
```

Tooltips mogen niet vol interne jargon zitten.

---

# 37. SHORTCUT MASTER

Maak:

```text
SHORTCUT_MASTER.json
```

Minimaal:

```text
Ctrl+O  Bestand openen
Ctrl+S  Opslaan
Ctrl+P  Afdrukken
Ctrl+K  Snelactie
Ctrl+Z  Ongedaan maken
Ctrl+Y  Opnieuw
Esc     actieve tool/dialoog annuleren
F       Alles passend / Viewer fit volgens productcontract
Delete  alleen veilige contextuele delete met validation
```

Detecteer collisions.

Zelfde shortcut nooit twee simultaan geldige conflicterende acties.

---

# 38. TABELLEN

Gebruik een gedeelde `CwsDataTable`.

Visual rules:

```text
header height    30–32 px
row height       30 px
selection        accent.soft
current cell     subtiele focus border
grid             zeer subtiel
numeric          right aligned
text             left aligned
status           compact
```

Column chooser:

- één gedeeld patroon;
- checkable fields;
- reset layout.

Drag/drop columns waar toegestaan.

Geen volledig andere tabelstijl voor BOM, validation en routing.

---

# 39. STATUSBADGES

Status = tekst + eventueel icon + kleur.

Niet alleen kleur.

Voorbeelden:

```text
✓ Gereed
! Review
× Geblokkeerd
i Info
```

Gebruik echte vectorstatusiconen, geen tekstsymbolen in productie.

Machine:

```text
Geschikt
Geschikt met waarschuwing
Niet geschikt
```

Geometry:

```text
Exact
Benadering
Proxy
Onbekend
```

Production:

```text
Gereed
Review
Geblokkeerd
```

---

# 40. DIALOGEN

Geen generieke QMessageBox-chaos als een structured dialog nodig is.

Maak gedeelde patterns:

```text
CwsConfirmDialog
CwsErrorDialog
CwsValidationDialog
CwsFileConflictDialog
CwsMachineOverrideDialog
```

Dialog rules:

- title;
- duidelijke oorzaak;
- gevolgen;
- primary action;
- cancel;
- details expander voor technische evidence.

Geen irreversible default button zonder duidelijke confirmation.

---

# 41. EMPTY / LOADING / ERROR STATES

Ieder hoofdscherm moet echte states hebben.

## Empty

Toon:

- wat ontbreekt;
- één duidelijke volgende stap.

Niet leeg wit vlak.

## Loading

Toon:

- welke echte job loopt;
- progress indien betrouwbaar;
- cancel indien supported.

Geen fake indeterminate spinner als backend exacte progress levert.

## Error

Toon:

- wat misging;
- affected scope;
- retry;
- details;
- evidence/log link waar relevant.

---

# 42. RESPONSIVE PRIORITY

Bij onvoldoende breedte geldt:

1. Viewer/model blijft bruikbaar.
2. primary action blijft zichtbaar.
3. contextacties blijven bereikbaar.
4. secondary detail mag collapsen.
5. advanced detail mag achter `Meer`.
6. kernfunctie mag niet verdwijnen.

Geen horizontale scroll over de volledige app-shell.

---

# 43. DPI ACCEPTANCE

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

Waar CI/hardware geen 4K kan testen:

- minstens synthetic Qt scaling test;
- echte 4K status niet faken.

Gates:

```text
clipped primary controls = 0
overlap = 0
unreachable controls = 0
font too small = 0
off-screen modal actions = 0
```

---

# 44. SCREENSHOT-REGRESSION

Voor ieder van de 25 V5 reference screens:

```text
reference.png
runtime.png
masked_runtime.png
diff.png
metrics.json
review.md
```

Dynamic zones maskeren:

- projectnaam;
- table data;
- timestamps;
- actual 3D geometry;
- transient progress.

Niet maskeren:

- nav;
- panel boundaries;
- control positions;
- toolbar groups;
- button labels;
- icon presence;
- tab layout;
- standard status components.

Structural metrics:

```text
topnav height
workspace header
left panel bbox
main content bbox
right inspector bbox
subtabs bbox
primary action bbox
context action bar bbox
table header bbox
```

Target:

- belangrijke paneelgrenzen circa ±8 logical px;
- standard buttonhoogtes ±1 px;
- fonts volgens token master;
- control group order exact;
- required controls 100%.

Gebruik perceptual similarity alleen op stabiele chrome-regions.

Richtwaarde:

```text
SSIM >= 0.94
```

op gemaskeerde stabiele UI-chrome, maar een hoge SSIM mag geen ontbrekende knop verbergen.

Functionele/structural gates hebben voorrang.

---

# 45. RUNTIME CONTROL INVENTORY

Naast static manifest:

scan de echte Qt object tree tijdens packaged GUI tests.

Produceer:

```text
runtime_control_inventory.json
```

Per control:

```text
test_id
objectName
type
screen
visible
enabled
text
tooltip
geometry
icon_id
shortcut
checked
handler binding
```

Vergelijk met expected.

Gates:

```text
expected_missing = 0
unexpected_interactive = 0
duplicate_test_id = 0
missing_tooltip_where_required = 0
icon_binding_missing = 0
```

Een nieuwe onverwachte interactieve control is FAIL totdat hij expliciet gemanifesteerd is.

---

# 46. FUNCTIONELE CLICK-TESTS

Iedere control wordt niet alleen gevonden maar gebruikt.

Maak per context fixtures:

```text
no project
project loaded
part selected
assembly selected
multi-selection
invalid machine
valid machine
nesting unplanned
nesting planned
drawing missing
drawing valid
export preflight fail
export preflight pass
validation blocker
```

Voor ieder enabled control:

```text
click
→ expected command
→ expected service
→ expected state/result
```

Geen action mag alleen een label wijzigen.

---

# 47. ICON PACKAGING TEST

Test packaged Windows build.

Gates:

```text
missing icon files = 0
fallback empty icons = 0
incorrect dark/light inversion = 0
pixelated normal-size icons = 0
```

SVG assets moeten in PyInstaller/installer correct meegeleverd zijn.

---

# 48. ACCESSIBILITY / KEYBOARD

Minimaal:

- tab navigation;
- keyboard focus zichtbaar;
- Enter activeert default action;
- Space toggle controls;
- Escape cancel;
- screenreader accessibleName voor icon-only controls waar Qt ondersteund;
- tooltip/accessible description.

Geen muis-only kritieke action.

---

# 49. PERFORMANCE VAN UI

De visuele refactor mag Viewer/performance niet verslechteren.

Meet:

- workspace switch;
- BOM filter;
- table selection;
- opening context menu;
- Activity Center;
- Problem Center;
- Settings;
- drawing preview.

Doel:

```text
normal UI command feedback < 100 ms waar geen zware job nodig is
```

Zware jobs starten async via JobManager.

Geen full model rebuild omdat gebruiker een panel opent.

---

# 50. GEEN FUNCTIONALITEITSVERLIES

Bij het verplaatsen/verbergen van oude toolbaritems:

maak een function parity map:

```text
OLD CONTROL
→ NEW CONTROL
→ SAME COMMAND
→ SAME SERVICE
→ TEST
```

Status:

```text
PASS
MOVED
MERGED_UI_ONLY
BLOCKED
FAIL
```

`MERGED_UI_ONLY` betekent alleen dat presentation is samengevoegd; backendfunctionaliteit blijft volledig.

Geen functie mag verdwijnen omdat V5 een rustigere toolbar heeft.

---

# 51. 3 UI-WERKPAKKETTEN BINNEN GLOBALE FASE 2

Dit zijn **geen nieuwe globale productfasen**.

Ze worden uitgevoerd binnen de bestaande globale Fase 2.

## UI-WERKPAKKET A — DESIGN SYSTEM + COMPLETE BINDING

Bouw eerst:

```text
Cws component library
VISUAL_TOKENS.json
ICON_MASTER.json
BUTTON_STATE_MASTER.md
SHORTCUT_MASTER.json
CONTROL_VISUAL_BINDING.json
```

Map 100% van `CONTROL_INVENTORY_MASTER.json`.

### Gate A

```text
expected controls = current authoritative count
mapped controls = 100%
unknown component = 0
unknown icon = 0
duplicate semantic icon conflict = 0
unresolved label = 0
```

Nog geen scherm als “final” claimen vóór Gate A.

---

## UI-WERKPAKKET B — ALLE SCHERMEN IMPLEMENTEREN

Pas het component system toe op:

- alle 25 V5 visual screens;
- support surfaces 26–31;
- alle states;
- alle dialogs/contextmenus.

Behoud bestaande services.

Per screen:

```text
screen_id
reference
implemented
controls expected
controls present
visual structure
functional parity
runtime screenshot
status
```

### Gate B

```text
25/25 visual SSOT screens = PASS
6/6 support surfaces = PASS or explicitly approved replacement
required controls present = 100%
legacy duplicate workspace controls = 0
dead controls = 0
```

---

## UI-WERKPAKKET C — VISUAL + FUNCTIONAL ACCEPTANCE

Run:

- runtime control inventory;
- click tests;
- screenshot diffs;
- DPI matrix;
- keyboard;
- packaged icons;
- resize;
- dark theme secondary smoke;
- Windows portable smoke.

### Gate C

```text
missing controls = 0
dead controls = 0
wrong handlers = 0
wrong labels = 0
icon violations = 0
critical visual differences = 0
DPI clipping = 0
```

Pas daarna mag:

```text
V5.1 UI CONTROL FIDELITY = PASS
```

---

# 52. VERPLICHTE OUTPUTBESTANDEN

Maak minimaal:

```text
validation/ui_v5_1/
  VISUAL_TOKENS.json
  ICON_MASTER.json
  BUTTON_STATE_MASTER.md
  SHORTCUT_MASTER.json
  CONTROL_VISUAL_BINDING.json

  SCREEN_IMPLEMENTATION_MATRIX.json
  SCREEN_IMPLEMENTATION_MATRIX.md

  runtime_control_inventory.json
  CONTROL_RUNTIME_COVERAGE.json
  CONTROL_RUNTIME_COVERAGE.md

  UI_FUNCTION_PARITY_MATRIX.json
  UI_FUNCTION_PARITY_MATRIX.md

  UI_VISUAL_ACCEPTANCE.json
  UI_VISUAL_ACCEPTANCE.md

  UI_DPI_ACCEPTANCE.json
  UI_KEYBOARD_ACCEPTANCE.json
  UI_ICON_PACKAGING_ACCEPTANCE.json

  screenshots/
    screen_01/
    ...
    screen_31/

  FINAL_UI_V5_1_ACCEPTANCE.json
  FINAL_UI_V5_1_ACCEPTANCE.md
```

---

# 53. FINAL UI ACCEPTANCE

Final report exact:

```text
CWS V5.1 UI CONTROL FIDELITY

Source SHA:
Version:

Visual SSOT screens:
Expected:
PASS:
FAIL:

Support surfaces:
Expected:
PASS:
FAIL:

Controls:
Expected:
Runtime discovered:
Mapped:
Functional PASS:
Missing:
Unexpected:
Dead:
Duplicate test_id:

Icons:
Defined:
Bound:
Missing:
Semantic conflicts:

Labels:
Correct:
Incorrect:

Tooltips:
Required:
Present:
Missing:

DPI:
100%:
125%:
150%:
200%:

Keyboard:
PASS/FAIL

Visual structure:
PASS/FAIL

Packaged Windows:
PASS/FAIL

Functional parity:
PASS/FAIL

V5.1 UI CONTROL FIDELITY:
PASS / FAILED
```

---

# 54. HARDE FINAL GATE

`V5.1 UI CONTROL FIDELITY = PASS`

alleen wanneer:

1. alle bindende V5 screens aanwezig zijn;
2. alle support surfaces functioneel aanwezig zijn;
3. alle actuele required controls gemapt zijn;
4. missing required control = 0;
5. unexpected unmanifested interactive control = 0;
6. dead/no-op control = 0;
7. duplicate test_id = 0;
8. button styles consistent zijn;
9. icon semantics consistent zijn;
10. default theme Light is;
11. witte content/panel background correct is;
12. nav consistent is;
13. context action order correct is;
14. disabled reasons correct zijn;
15. tooltips compleet zijn;
16. screen hierarchy overeenkomt;
17. DPI clipping = 0;
18. packaged icons = PASS;
19. click/action tests = PASS;
20. bestaande required functionaliteit niet verdwenen is.

---

# 55. UITVOERREGEL VOOR CODEX

Wanneer een huidige control visueel niet in de V5 PNG staat maar aantoonbaar required functionaliteit bevat:

**niet verwijderen.**

Bepaal in deze volgorde:

1. hoort hij als primary/common action zichtbaar?
2. hoort hij in context action bar?
3. hoort hij onder `Meer`?
4. hoort hij in Inspector?
5. hoort hij onder `Details/Geavanceerd`?
6. hoort hij in Settings?

Documenteer de verplaatsing.

Nooit functie verliezen.

---

# 56. GEEN ZELFSTANDIGE ONTWERPBESLISSINGEN ZONDER EVIDENCE

Wanneer iets niet beschreven is:

1. zoek V5 screen manifest;
2. zoek control inventory;
3. zoek component catalog;
4. zoek text master;
5. zoek V4 style reference;
6. behoud bestaand bewezen Qt-patroon indien consistent;
7. documenteer de gekozen fallback.

Niet:

> “I redesigned it for a cleaner look.”

Wel:

> “The reference did not define this secondary dialog; I applied CwsModalDialog + existing context semantics, with all required controls preserved.”

---

# 57. STARTOPDRACHT AAN CODEX

Begin niet direct met willekeurige widgets wijzigen.

Voer eerst uit:

```text
1. git fetch
2. bepaal canonical branch + HEAD
3. lees V5.1 master
4. lees SCREEN_MANIFEST
5. lees CONTROL_INVENTORY_MASTER
6. lees UI_COMPONENT_CATALOG
7. lees UI_TEXT_MASTER
8. lees DO_NOT_CHANGE
9. inventariseer huidige Qt controls runtime/static
10. maak OLD -> TARGET screen/control map
11. maak VISUAL_TOKENS
12. maak ICON_MASTER
13. maak CONTROL_VISUAL_BINDING voor 100% van controls
14. voer Gate A uit
15. implementeer scherm voor scherm
16. screenshot + click-test per scherm
17. voer Gate B uit
18. packaged DPI/control/visual acceptance
19. voer Gate C uit
```

Geen final claim vóór Gate C.

---

# 58. EINDDOEL

Na deze opdracht mag Codex niet langer zelf hoeven beslissen:

- welke knopkleur gebruikt wordt;
- welke knophoogte gebruikt wordt;
- welke iconfamilie gebruikt wordt;
- welk icoon bij een kernactie hoort;
- waar contextacties staan;
- hoe hover/pressed/disabled eruitzien;
- welke tekst op een actie staat;
- hoe de Viewer-toolbar gegroepeerd is;
- hoe BOM selection actions staan;
- hoe machine-routing acties staan;
- hoe Drawing/PDF outputacties staan;
- hoe support drawers eruitzien.

Dat is nu een contract.

Codex moet vooral:

> **bouwen, koppelen, testen en bewijzen.**
