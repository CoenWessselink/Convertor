# CWS Viewer V15 — interaction/navigation parity audit

Auditdatum: 2026-08-17  
Branch: `feature/trimble-parity-v15`  
Status: **SOURCE HARDENED / WINDOWS T3 GREEN — packaged physical GUI interaction evidence blijft verplicht**

## 1. Aanleiding

De bestaande T0/T3 documentatie markeerde orbit/pan/zoom als bewezen baseline. Bij gericht gebruik bleek echter een fundamentele interactiefout:

> na selectie van een onderdeel bleef orbit rond het oude `camera.target` / scene-fitpunt draaien in plaats van rond het gekozen onderdeel.

Dit is geen cosmetische afwijking. Het bepaalt of de 3D-viewer als engineeringviewer natuurlijk bestuurbaar is.

## 2. Bronnen voor deze audit

### Aangeleverde lokale referentie

De eerder vastgelegde checksum-lock blijft leidend:

- `Trimble Connect.zip`
- SHA-256 `6298196885a51784f557e0f9e6cf18d1f60bc68c35b4c03913f3771e1923455e`

De aangeleverde package is uitsluitend een zichtbare gedrags-/workflowreferentie. Geen proprietary DLL-logica, private endpoints, assets of gedecompileerde implementatie wordt in CWS overgenomen.

### Officiële actuele Trimble Help

Gecontroleerd op 2026-08-17 tegen Connect for Windows documentatie:

- Navigation and Camera Controls: Rotate, Pan, Walk Around, Look Around;
- Rotate: muisknop vasthouden op een gekozen modelpunt en rond **dat gekozen punt** roteren;
- Pan: eveneens een modelpunt kiezen en vanaf dat punt slepen;
- Keyboard Shortcuts: Space = fit selectie; dubbelklik object = fit + objectcontext; Alt+dubbelklik surface = orthogonaal aan surface; Ctrl+U/I/O/P = Rotate/Pan/Walk/Look; Esc beëindigt operatie en wist selectie; F11 = full-screen; Backspace/Shift+Backspace = hide/hide others;
- Making Selections: single, area en assembly selection; links→rechts = volledig binnen, rechts→links = crossing; Alt keert Object/Assembly-selectiemodus tijdelijk om.

Referenties:

- https://help.trimble.com/doc/trimble-connect/trimble-connect/connect-for-windows/working-in-3d/navigation-and-camera-controls
- https://help.trimble.com/doc/trimble-connect/trimble-connect/connect-for-windows/working-in-3d/keyboard-shortcuts
- https://help.trimble.com/doc/trimble-connect/trimble-connect/connect-for-windows/working-in-3d/making-selections

## 3. Root cause in CWS vóór herstel

De oude orbitketen was:

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

Er bestond geen aparte orbitpivot en `set_selection()` wijzigde de orbitfocus niet. Alleen `fit_selection()` zette toevallig `camera.target` op de selectie-bounds. Hierdoor werkte orbit na een gewone klik alleen correct wanneer de gebruiker daarna expliciet Fit Selectie uitvoerde.

De oude pan gebruikte daarnaast een vaste, cameradistance-afgeleide gevoeligheid uit muisdelta's. Daardoor was de bediening afhankelijk van modelschaal en niet van het werkelijk gekozen punt in perspectief.

## 4. Nieuw verplicht interactiecontract

### 4.1 Persistent selectie-orbitpivot

Bij een niet-lege selectie:

```text
orbit_pivot = center(combined world bounds of selected nodes)
```

Dit geldt voor klik in viewport, projectboom/gridselectie, multi-selectie, assemblyselectie en area selection. De camera beweegt **niet** door alleen te selecteren; uitsluitend de focus voor de volgende orbit verandert.

### 4.2 Exact modelpunt tijdens Rotate-drag

Bij mouse-down in Rotate mode:

```text
non-mutating surface probe
  -> PickResult.world_point
  -> transient orbit_pivot = picked world point
```

De V14 real-mesh backend probeert eerst een `vtkCellPicker` op de echte meshgroepen; alleen wanneer die geen geldige surface-hit geeft, blijft de oudere center-proxy fallback beschikbaar. Daarmee is de Rotate-focus op de real-project renderer daadwerkelijk surface-gebaseerd waar de meshbackend dit kan bewijzen.

### 4.3 Picked-depth Pan

Bij mouse-down in Pan mode wordt eveneens het zichtbare modelpunt geprobed. De panverschuiving per pixel wordt daarna bepaald vanuit:

- perspectief: actuele FOV + diepte van het gekozen modelpunt;
- orthografisch: de ingestelde verticale `ortho_scale`.

Hierdoor beweegt een punt dat dichter bij de camera ligt minder wereldmillimeters per pixel dan een punt op grotere diepte, zoals een perspectiefcamera geometrisch vereist. De pan is niet langer gebaseerd op één willekeurige model-schaalfactor.

### 4.4 Object / Assembly selection

```text
persistent selection level = Object | Assembly
Alt + click = temporary inverse level
```

De tijdelijke Alt-keuze verandert de opgeslagen selectiemodus niet. De V15 Aanzicht/Navigatie-dock toont expliciet `Object` / `Assembly` en de Alt-inversie. Selection level blijft onderdeel van viewer workspace/session state.

### 4.5 Rigid camera rotation om pivot

Orbit roteert zowel camera eye als focal target als één rigide cameraframe om de actieve pivot. Daardoor blijft een gekozen selectie/pick werkelijk het draaipunt, ook wanneer het oude `camera.target` ergens anders lag.

### 4.6 Fit- en restore-regels

- Fit All: scene fit + pivot naar nieuw camera target;
- Fit Selection: selectie fit + pivot op selectiecentrum;
- Selection zonder fit: geen camera-jump;
- selectie wissen: laatste bruikbare focus blijft staan;
- undo/redo, saved-view activation en workspace restore: pivot wordt opnieuw afgeleid van herstelde selectie, anders van actuele camera target.

## 5. Keyboard/mouse parity hardening

| Gedrag | Bestaande basis vóór audit | Huidige status |
|---|---|---|
| Orbit rond gekozen modelpunt | fout: rond `camera.target` | Windows source gate groen |
| Selectie bepaalt orbitfocus | ontbrak | Windows source gate groen |
| Tree/grid selectie bepaalt orbitfocus | selectie-sync bestond, focus ontbrak | centraal via controller-selection |
| Multi-select orbitfocus | ontbrak | combined bounds center |
| Pan vanaf gekozen modelpunt | schaal-/distanceheuristiek | picked-depth pan + Windows contracttest |
| Object/Assembly selectiemodus | intern SelectionLevel bestond | expliciete UI + tijdelijke Alt-inversie |
| Space = fit selectie | aanwezig | behouden |
| Dubbelklik object = select + fit | aanwezig | behouden |
| Alt+dubbelklik surface = orthogonaal | ontbrak in viewportinput | surface normal + exact picked point |
| Ctrl+U/I/O/P | aanwezig als cockpit shortcuts | behouden + viewer-focus fallback |
| F11 | aanwezig | behouden + viewer-focus fallback |
| Esc | tool cancel aanwezig | aangevuld met selectie wissen |
| Backspace | cockpit shortcut aanwezig | behouden + viewer-focus fallback |
| Shift+Backspace | niet centraal afgedekt | hide-others fallback toegevoegd |
| L→R area | aanwezig | fully-inside behouden |
| R→L area | aanwezig | crossing behouden |
| Right-click context | aanwezig | behouden |

## 6. Windows source evidence

Run `32004795315`, commit `30ce1106258a89ffc113219693ee77f1d84a063b`:

```text
Compile T3 modules                         PASS
Deterministic T3 navigation contract       PASS
V15 self-test contract                     PASS
Windows runner                             windows-2022 / Python 3.12 x64
```

De packaged V15-self-test is vervolgens aangescherpt zodat toekomstige frozen/portable/installed builds ook de nieuwe interaction-capabilities expliciet moeten bevatten: picked-point orbit, selection orbit focus, picked-depth pan, Object/Assembly selection en Alt inversion.

## 7. Bewust nog niet als volledig gelijk verklaard

1. **Walk Around / Look Around feel** — de modi bestaan, maar exacte gevoeligheid/acceleratie/dead-zone is niet uit de aangeleverde binaries of openbare Help als numerieke formule bewezen. Niet op gevoel herschrijven.
2. **Zoom feel / cursor anchoring** — wheel zoom werkt; exacte Trimble cursor/depth semantics zijn nog niet hard genoeg bewezen om een andere formule te claimen.
3. **F11 packaged focus/state** — implementation aanwezig; packaged focus/state-restore moet in eindbuild worden bewezen.
4. **Ctrl/Shift selectieconflict in Help** — actuele Trimble-pagina's spreken elkaar op detailniveau tegen. De aangeleverde Windows-reference-app/owner-test is hiervoor de beslissende oracle.
5. **Trackpad/touch** — niet claimen zonder apart Windows inputbewijs.
6. **Physical packaged GUI interaction** — headless GUI/screenshot en contracttests zijn niet hetzelfde als echte muisbediening op de frozen EXE. Dit blijft een expliciete releasegate.

## 8. Nieuwe regressiegate

Automatisch bewezen / verplicht:

- selectie zet pivot op selection bounds center zonder camera te verplaatsen;
- multi-select gebruikt combined bounds;
- gekozen surface/world point kan orbitpivot worden zonder selectie-mutatie;
- orbit behoudt eye- en target-radius om pivot;
- perspective pan schaalt met picked depth;
- orthographic pan is depth-independent;
- tijdelijke Object/Assembly inversion bewaart persistent selection level;
- Fit Selection centreert camera én pivot;
- view-from-normal gebruikt picked point of actieve selectie-orbitfocus;
- zoom-area behoudt selectie en bindt pivot aan fitted target;
- workspace/saved-view restore laat geen stale orbitfocus achter.

## 9. Statusregel

```text
viewer_interaction_source_gate = GREEN
orbit_selection_focus = WINDOWS_SOURCE_VERIFIED
picked_depth_pan = WINDOWS_SOURCE_VERIFIED
object_assembly_selection = WINDOWS_SOURCE_VERIFIED
packaged_physical_input_gate = REQUIRED_NOT_YET_GREEN
trimble_proprietary_code_copied = false
```

De eerdere generieke claim `3D orbit/pan/zoom/fit = VERIFIED_BASELINE` was te breed. Vanaf deze audit geldt alleen een capability als VERIFIED wanneer de betreffende input-/camera-semantiek afzonderlijk is getest.
