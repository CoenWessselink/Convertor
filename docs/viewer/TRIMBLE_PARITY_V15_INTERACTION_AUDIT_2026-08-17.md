# CWS Viewer V15 — interaction/navigation parity audit

Auditdatum: 2026-08-17  
Branch: `feature/trimble-parity-v15`  
Status: **T3 INTERACTION GATE HEROPEND — niet meer als volledig VERIFIED behandelen totdat Windows source + packaged GUI evidence groen zijn**

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
- Keyboard Shortcuts: Space = fit selectie; dubbelklik object = fit + objectcontext; Alt+dubbelklik surface = orthogonaal aan surface; Ctrl+U/I/O/P = Rotate/Pan/Walk/Look; Esc beëindigt operatie en wist selectie; Backspace/Shift+Backspace = hide/hide others;
- Making Selections: single, area en assembly selection; links→rechts = volledig binnen, rechts→links = crossing; selection mode is gekoppeld aan Objects-context.

Referenties:

- https://help.trimble.com/doc/trimble-connect/trimble-connect/connect-for-windows/working-in-3d/navigation-and-camera-controls
- https://help.trimble.com/doc/trimble-connect/trimble-connect/connect-for-windows/working-in-3d/keyboard-shortcuts
- https://help.trimble.com/doc/trimble-connect/trimble-connect/connect-for-windows/working-in-3d/making-selections

## 3. Root cause in CWS vóór herstel

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

Er bestond geen aparte orbitpivot en `set_selection()` wijzigde de orbitfocus niet. Alleen `fit_selection()` zette toevallig `camera.target` op de selectie-bounds. Hierdoor werkte orbit na een gewone klik alleen correct wanneer de gebruiker daarna expliciet Fit Selectie uitvoerde.

## 4. Nieuw verplicht interactiecontract

### 4.1 Persistent selectie-orbitpivot

Bij een niet-lege selectie:

```text
orbit_pivot = center(combined world bounds of selected nodes)
```

Dit geldt voor:

- klik in viewport;
- selectie vanuit projectboom;
- selectie vanuit grid/property-context;
- multi-selectie;
- assembly-selectie zodra die selection level actief is;
- area selection.

De camera zelf beweegt **niet** op het moment van selecteren. Selectie mag dus geen onverwachte pan/zoom/view jump veroorzaken.

### 4.2 Exact modelpunt tijdens Rotate-drag

Bij mouse-down in Rotate mode:

```text
non-mutating surface probe
  -> PickResult.world_point
  -> transient orbit_pivot = picked world point
```

Daarna roteert de drag rond exact dat punt. Een drag selecteert het object niet opnieuw; een klik zonder drag blijft een normale selectiehandeling.

Dit volgt rechtstreeks het zichtbare Trimble Rotate-concept: rotate around the point picked in the model.

### 4.3 Rigid camera rotation om pivot

Orbit draait niet alleen de eye-position om het pivotpunt. Zowel camera eye als camera focal target worden als rigide cameraframe om de pivot geroteerd. Daardoor kan het pivotpunt buiten het bestaande `camera.target` liggen zonder terug te vallen op een oud scene-centrum.

### 4.4 Fit-regels

- Fit All: camera fit naar scene en orbitpivot terug naar het nieuwe camera target.
- Fit Selection: fit naar selectie en orbitpivot blijft selectiecentrum.
- Selection zonder fit: camera blijft exact staan, alleen toekomstige orbitfocus verandert.
- Selection clear: laatste bruikbare orbitpivot blijft behouden; er is geen onverwachte sprong terug naar oorsprong.

### 4.5 Restore-regels

Na undo/redo, saved-view activation en workspace restore wordt transient orbitfocus opnieuw afgeleid:

1. selectie aanwezig -> selectie-bounds centrum;
2. geen selectie -> actuele camera target.

Hierdoor kan opgeslagen state niet een oude onzichtbare pivot achterlaten.

## 5. Keyboard/mouse parity hardening in deze batch

Geïmplementeerd / aangescherpt:

| Gedrag | Vóór audit | Nieuwe status |
|---|---|---|
| Orbit rond gekozen modelpunt | fout | geïmplementeerd, Windows gate vereist |
| Selectie bepaalt volgende orbitfocus | ontbrak | geïmplementeerd |
| Tree/grid selectie bepaalt orbitfocus | ontbrak impliciet | centraal via controller-selection |
| Multi-select orbitfocus | ontbrak | combined bounds center |
| Space = fit selectie | aanwezig | behouden |
| Dubbelklik object = select + fit | aanwezig | behouden |
| Alt+dubbelklik surface = orthogonaal | ontbrak | geïmplementeerd via echte pick-normal/world-point |
| Ctrl+U = Rotate | ontbrak | geïmplementeerd |
| Ctrl+I = Pan | ontbrak | geïmplementeerd |
| Ctrl+O = Walk | ontbrak | geïmplementeerd |
| Ctrl+P = Look | ontbrak | geïmplementeerd |
| Esc = tool beëindigen + selectie wissen | gedeeltelijk | aangescherpt |
| Backspace = hide selection | ontbrak op widget | geïmplementeerd |
| Shift+Backspace = hide others | ontbrak op widget | geïmplementeerd |
| L→R area = fully inside | aanwezig | behouden |
| R→L area = crossing | aanwezig | behouden |
| Right-click context | aanwezig | behouden |

## 6. Bewust nog niet als volledig gelijk verklaard

Onderstaande punten moeten nog apart worden bewezen of verdiept voordat de gehele handling als parity-complete wordt gemarkeerd:

1. **Pan point anchoring / snelheid** — huidige pan is cameradistance-geschaald; nog vergelijken met de aangeleverde executable op echte muisbewegingen.
2. **Walk Around / Look Around sensitivity** — modus bestaat, maar snelheid/acceleratie/dead-zone moeten met echte Windows input worden vergeleken.
3. **F11 full-screen** — nog shell-level paritytest.
4. **Alt inversion Object ↔ Assembly Selection** — selection-level contract bestaat, maar de exacte temporary Alt-inversion moet nog als één centrale interaction rule worden getest.
5. **Selection modifier conflict in Trimble Help** — verschillende Help-pagina's beschrijven Shift/Ctrl op detailniveau niet volledig hetzelfde. Geen CWS-semantiek wijzigen op basis van een onzekere interpretatie; lokale reference-app owner test gebruiken als oracle.
6. **Trackpad/touch** — niet claimen zolang CWS Windows desktop input daarvoor niet apart getest is.
7. **Packaged physical GUI input gate** — source unit tests zijn onvoldoende voor mouse interaction; de uiteindelijke Windows packaged build moet real Qt/VTK interaction evidence leveren.

## 7. Nieuwe regressiegate

Minimaal automatisch bewijzen:

- selectie zet orbitpivot op exacte selection bounds center;
- selectie verandert de camera niet;
- multi-select gebruikt combined bounds;
- selectie wissen veroorzaakt geen pivot jump;
- expliciet picked world point kan pivot worden zonder camera mutation;
- orbit behoudt eye- en target-radius om de pivot;
- Fit Selection centreert camera én pivot op selectie;
- view-from-normal accepteert exact picked surface point;
- zoom-area behoudt selectie en bindt pivot aan fitted camera target;
- workspace/view restore laat geen stale orbitfocus achter.

Daarbovenop blijft Windows source compile/self-test verplicht. Daarna volgt packaged GUI interaction evidence.

## 8. Statusregel

Tot die packaged gate groen is:

```text
viewer_interaction_trimble_parity = PARTIAL_HARDENED
orbit_selection_focus = IMPLEMENTED_PENDING_WINDOWS_EVIDENCE
trimble_proprietary_code_copied = false
```

De eerdere generieke claim `3D orbit/pan/zoom/fit = VERIFIED_BASELINE` is voor interaction parity te breed gebleken en wordt met deze audit gecorrigeerd.
