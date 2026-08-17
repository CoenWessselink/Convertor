# CWS Viewer V15 — interaction/navigation parity audit

Auditdatum: 2026-08-17  
Branch: `feature/trimble-parity-v15`  
Windows source evidence commit: `b865e2b2fef2d8f15387a2abccdd5ffe6679117c`  
Status: **SOURCE HARDENED / WINDOWS T3 GREEN — packaged physical GUI interaction evidence blijft verplicht**

## 1. Aanleiding

De bestaande T0/T3 documentatie markeerde orbit/pan/zoom als bewezen baseline. Bij gericht gebruik bleek echter een fundamentele interactiefout:

> na selectie van een onderdeel bleef orbit rond het oude `camera.target` / scene-fitpunt draaien in plaats van rond het gekozen onderdeel.

Dit is geen cosmetische afwijking. Het bepaalt of de 3D-viewer als engineeringviewer natuurlijk bestuurbaar is. Daarom is niet alleen orbit gepatcht; de volledige selectie/camera/displaybasis is opnieuw langs de aangeleverde Trimble-referentie en de openbare Connect for Windows workflow gelegd.

## 2. Bronnen voor deze audit

### Aangeleverde lokale referentie

De eerder vastgelegde checksum-lock blijft leidend:

- `Trimble Connect.zip`
- SHA-256 `6298196885a51784f557e0f9e6cf18d1f60bc68c35b4c03913f3771e1923455e`

De aangeleverde package is uitsluitend een zichtbare gedrags-/workflowreferentie. Geen proprietary DLL-logica, private endpoints, assets of gedecompileerde implementatie wordt in CWS overgenomen.

### Officiële actuele Trimble Help

Gecontroleerd op 2026-08-17 tegen Connect for Windows documentatie:

- Rotate, Pan, Walk Around en Look Around zijn afzonderlijke cameramodi;
- Rotate start op een gekozen modelpunt en draait rond die gekozen modelcontext;
- Pan start eveneens vanaf een gekozen modelpunt;
- Space = fit selectie;
- dubbelklik object = geselecteerd object in beeld brengen;
- Alt+dubbelklik surface = camera loodrecht op dat vlak;
- Ctrl+U/I/O/P = Rotate/Pan/Walk/Look;
- Esc beëindigt de actieve operatie en wist selectie;
- F11 = full-screen;
- Backspace / Shift+Backspace = hide selection / hide others;
- Enter opent details van het geselecteerde object;
- single, area en assembly selection bestaan naast elkaar;
- links→rechts area = volledig binnen; rechts→links = crossing;
- Alt keert Object/Assembly-selectiemodus tijdelijk om;
- ghosted context is visuele context en hoort niet als normaal selectiedoel te functioneren.

Referenties:

- https://help.trimble.com/doc/trimble-connect/trimble-connect/connect-for-windows/working-in-3d/navigation-and-camera-controls
- https://help.trimble.com/doc/trimble-connect/trimble-connect/connect-for-windows/working-in-3d/keyboard-shortcuts
- https://help.trimble.com/doc/trimble-connect/trimble-connect/connect-for-windows/working-in-3d/making-selections
- https://help.trimble.com/doc/trimble-connect/trimble-connect/connect-for-windows/working-in-3d/hide-models-and-objects

## 3. Root causes in CWS vóór herstel

### 3.1 Orbit gebruikte een stale camera target

De oude keten was:

```text
mouse drag
  -> controller.orbit(dx, dy)
  -> offset = camera.position - camera.target
  -> rotate offset rond camera.target
```

Selectie deed alleen:

```text
pick_at
  -> set_selection(...)
```

Er bestond geen aparte orbitpivot. Alleen `fit_selection()` zette toevallig `camera.target` op de selectie-bounds. Een gewone klik op een onderdeel veranderde dus niet waar de volgende orbit omheen draaide.

### 3.2 Pan was niet aan het gekozen modelpunt gebonden

De oude pan gebruikte een cameradistance-/modelschaalheuristiek. Een identieke muisbeweging voelde daardoor anders bij verschillende modeldieptes.

### 3.3 Assembly-selectie en renderhighlight waren niet één contract

Een assembly-knooppunt kan semantisch geselecteerd zijn zonder eigen geometrie. De oude renderstate markeerde dan alleen renderbare selectie-IDs, waardoor een assemblyselectie intern bestond maar visueel niet noodzakelijk blauw oplichtte.

### 3.4 Explode en camerabounds gebruikten verschillende werkelijkheden

De renderer verplaatste exploded objecten met viewer-only offsets, terwijl selection focus / Fit Selection / Fit All / Zoom Area nog van canonical pre-explode bounds konden uitgaan. Daardoor kon een zichtbaar verplaatst onderdeel nog om zijn oude positie draaien.

### 3.5 Ghost/hidden geometry kon op controller-niveau nog als renderer-hit terugkomen

Een rendererpicker kan technisch een actor raken die als ghost-context wordt getekend. Zonder controllerfilter kon die context een normale selectie stelen.

## 4. Nieuw centraal interactiecontract

### 4.1 Selectie bepaalt orbitfocus zonder camera-jump

Bij een niet-lege selectie:

```text
orbit_pivot = center(displayed bounds of selected hierarchy)
```

Dit geldt centraal voor viewport, projectboom/grid, multi-selectie, assemblyselectie en area selection. Alleen de toekomstige orbitfocus verandert; de camera wordt door een gewone selectie niet gepand, gezoomd of gefit.

### 4.2 Rotate-drag gebruikt exact picked surface point

Bij mouse-down in Rotate mode:

```text
non-mutating surface probe
  -> PickResult.world_point
  -> transient orbit_pivot = picked world point
```

De real-mesh backend probeert eerst `vtkCellPicker` op de echte meshactoren. Alleen wanneer geen geldige surface-hit bestaat, blijft de oudere fallback beschikbaar. De drag zelf muteert de selectie niet.

### 4.3 Orbit roteert het volledige cameraframe om de pivot

Zowel eye-position als focal target worden rigide om het actieve pivotpunt geroteerd. Een geselecteerd/picked punt blijft daardoor de werkelijke rotatiecontext, ook als het oude camera target elders lag.

### 4.4 Picked-depth Pan

Bij Pan wordt het gekozen modelpunt vastgelegd. Wereldverplaatsing per pixel wordt bepaald uit:

- perspectief: camera-FOV + diepte van het gekozen modelpunt;
- orthografisch: actuele `ortho_scale`.

Zowel Pan-mode met LMB als de bestaande middle-mouse pan lopen door dezelfde berekening.

### 4.5 Object / Assembly selection is expliciet en hiërarchisch

```text
persistent selection level = Object | Assembly
Alt + click = one-shot inverse level
```

De Alt-inversie wordt nu berekend zonder `session.selection_level` ook maar tijdelijk te muteren. De persistente UI-modus kan dus niet knipperen, opgeslagen worden of plugin-events veroorzaken door een one-shot Alt-click.

Een assemblyselectie blijft semantisch één assembly-ID, maar de renderselection wordt voor highlight uitsluitend naar de renderbare descendants uitgebreid. Daardoor blijven selectie-identiteit, properties, orbit-bounds en blauwe highlight onderling consistent.

### 4.6 Hidden en ghost context zijn geen normale selectiedoelen

`pick_at()` valideert een renderer-hit nu tegen de actuele visible/ghosted state vóór de semantische selectie wordt gewijzigd. Hidden en ghosted context kunnen de actieve isolatiescope niet meer stelen.

De non-mutating `probe_at()` blijft bewust apart voor cameragebruik; selectie en navigatie gebruiken dus niet dezelfde muterende pickroute.

### 4.7 Fit en orbit volgen displayed geometry, ook bij Explode

Canonical scene bounds blijven immutable. Viewer-only explode offsets worden uitsluitend bij `display_bounds_for()` toegepast.

Daarop zijn nu gebaseerd:

- selection orbit focus;
- Fit Selection;
- Fit All;
- Zoom Area;
- assembly/group bounds;
- selectie-focus na `explode()`;
- selectie-focus na `reset_explode()`.

De camera volgt dus de positie die de gebruiker werkelijk op het scherm ziet zonder canonical geometry te vervormen.

### 4.8 State restore en live scene updates mogen geen stale pivot achterlaten

Na:

- undo/redo;
- saved-view activation;
- workspace restore;
- live scene/revision patch;
- explode/reset-explode;

wordt de transient orbitfocus opnieuw afgeleid van de huidige selectie/displaybounds, of van het actuele camera target wanneer geen selectie bestaat.

## 5. Keyboard/mouse parity hardening

| Gedrag | Voor audit | Huidige bronstatus |
|---|---|---|
| Orbit rond geselecteerd/picked onderdeel | fout/stale target | Windows source verified |
| Pan vanaf gekozen modelpunt | schaalheuristiek | picked-depth, Windows source verified |
| Tree/grid/viewport selectie → zelfde orbitfocus | onvolledig | centraal controllercontract |
| Multi-select orbitfocus | onvolledig | combined displayed bounds |
| Assemblyselectie highlight | semantisch maar mogelijk onzichtbaar | descendants highlight |
| Object/Assembly mode | intern SelectionLevel | expliciete UI + one-shot Alt inversion |
| Exploded object focus/fit | canonical oude positie mogelijk | displayed bounds |
| Ghost/hidden selection | renderer-afhankelijk | centraal geblokkeerd |
| Space = fit selectie | aanwezig | behouden |
| Dubbelklik object = select + fit | aanwezig | behouden, gebruikt displayed bounds |
| Alt+dubbelklik surface | ontbrak in viewportinput | exact picked point + normal |
| Enter = selectie-details | ontbrak als zichtbare parity shortcut | Properties/Provenance dock focus |
| Ctrl+U/I/O/P | aanwezig | behouden + viewer-focus fallback |
| F11 | aanwezig | behouden + viewer-focus fallback |
| Esc | tool cancel aanwezig | tool cancel + selectie wissen |
| Backspace | aanwezig | behouden + viewer-focus fallback |
| Shift+Backspace | niet centraal afgedekt | hide-others/isolate fallback |
| L→R area | aanwezig | volledig-binnen behouden |
| R→L area | aanwezig | crossing behouden |
| Right-click context | aanwezig | behouden |

## 6. Windows evidence — huidige interaction foundation

Laatste volledige T3 source gate op de geharde basis:

- Git commit: `b865e2b2fef2d8f15387a2abccdd5ffe6679117c`
- GitHub Actions run: `32006882656`
- Runner: `windows-2022`
- Python: 3.12 x64

Resultaat:

```text
Compile T3 interaction modules            PASS
Deterministic T3 navigation contract       PASS
Interaction foundation regressions         PASS
V15 standalone self-test contract          PASS
Overall T3 job                             PASS
```

De interaction-foundation regressies bewijzen onder andere:

- assemblyselectie highlight alle renderbare descendants;
- tijdelijke Assembly/Object pick bewaart de persistente selectiemodus;
- ghost context kan selectie niet stelen;
- hidden geometry kan niet worden geselecteerd;
- echte `explode()` verplaatst selection orbit focus naar displayed position;
- reset-explode herstelt die focus;
- Fit All respecteert actuele isolatiescope;
- selected semantic group blijft één selectie terwijl renderselection alleen geometrie bevat;
- perspective pan schaalt met picked depth;
- orthographic pan is depth-independent;
- workspace/saved-view restore laat geen stale orbitpivot achter.

De standalone V15-self-test vereist bovendien expliciet de geharde T3-capabilities, waaronder picked-point orbit, selection focus, picked-depth pan, display-space fit met explode, Object/Assembly mode, Alt inversion en geselecteerd-object-details.

## 7. Bewust nog niet als volledig Trimble-gelijk verklaard

De onderstaande onderdelen worden niet op gevoel gekopieerd zolang de aangeleverde reference-app / owner test of een expliciet openbaar contract niet voldoende bewijs geeft:

1. **Walk Around / Look Around feel** — exacte gevoeligheid, acceleratie en dead-zone zijn niet als numerieke formule bewezen.
2. **Wheel zoom feel / cursor anchoring** — scroll zoom werkt, maar exacte cursor-/depth-zoomsemantiek is nog niet bewezen.
3. **Ctrl/Shift multi-selection conflict** — actuele Trimble Help-pagina's spreken elkaar op detailniveau tegen; de aangeleverde Windows-reference-app wordt hiervoor de beslissende oracle.
4. **Trackpad/touch** — niet claimen zonder apart Windows inputbewijs.
5. **Physical packaged GUI input** — headless Qt/VTK smoke en contracttests zijn geen echte fysieke muis-/toetsenbordtest op de frozen/installed EXE.

## 8. Releasegate voor de viewerhandling

Broncode is pas de eerste helft. Voor een definitieve `VERIFIED` handlingstatus moet exact dezelfde commit ook als Windows packaged build aantonen:

```text
PyInstaller/frozen V15 self-test
portable GUI start
installed GUI start
real QVTK renderer active
real model loaded
physical/scripted mouse rotate on selected part
physical/scripted picked-depth pan
Object/Assembly + Alt inversion
Space / double-click / Alt-double-click
hide / isolate / show-all
explode + fit/orbit on displayed position
section/clipping state
camera state save/reopen
```

Daarna pas mag de algemene viewerhandling weer als parity-verified worden aangemerkt.

## 9. Statusregel

```text
viewer_interaction_source_gate = GREEN
source_commit = b865e2b2fef2d8f15387a2abccdd5ffe6679117c
source_windows_run = 32006882656
orbit_selection_focus = WINDOWS_SOURCE_VERIFIED
picked_depth_pan = WINDOWS_SOURCE_VERIFIED
hierarchy_selection_visualization = WINDOWS_SOURCE_VERIFIED
display_space_explode_fit = WINDOWS_SOURCE_VERIFIED
ghost_hidden_pick_exclusion = WINDOWS_SOURCE_VERIFIED
packaged_physical_input_gate = REQUIRED_NOT_YET_GREEN
trimble_proprietary_code_copied = false
```

De eerdere generieke claim `3D orbit/pan/zoom/fit = VERIFIED_BASELINE` was te breed. Vanaf deze audit geldt alleen een interaction capability als VERIFIED wanneer de betreffende camera-/selectionsemantiek afzonderlijk is getest.
