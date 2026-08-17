# CWS Viewer V15 — Trimble handling parity audit

Auditdatum: 2026-08-17  
Scope: desktop 3D input, selectie, camera, visibility en tool-capture  
Status: **HANDLING CONTRACT REBUILT + EXACT-SHA WINDOWS/RELEASE GATED**

## 1. Bronnen en grens

Deze audit gebruikt drie lagen:

1. de eerder checksum-locked aangeleverde `Trimble Connect.zip` als lokale product/package-referentie (`SHA-256 6298196885a51784f557e0f9e6cf18d1f60bc68c35b4c03913f3771e1923455e`);
2. de zichtbare workflows uit de actuele Trimble Connect for Windows Help, met name Navigation and Camera Controls, Keyboard Shortcuts, Making Selections en 3D Viewer Reference Guide;
3. de bestaande CWS V14/V15 controller-, renderer- en Qt-inputcode.

De aangeleverde Trimble binaries worden niet als CWS-broncode gebruikt. Het doel is dezelfde voorspelbare **zichtbare bediening** met eigen CWS-code, eigen UI en eigen canonical state.

## 2. Root cause van de gemelde orbitfout

De controller had al correcte selectie-focus: na selectie van een part of assembly werd het centrum van de daadwerkelijk getoonde selectie-bounds als `orbit_pivot` opgeslagen.

De V15 Qt-inputlaag maakte dit gedrag echter ongedaan. Bij de start van iedere orbit-drag werd opnieuw het losse surface-hitpoint onder de muis geprobed en als pivot ingesteld. Daardoor kon een correct geselecteerd onderdeel niet stabiel het draaipunt blijven.

Dit was geen cosmetisch probleem maar een input-contractfout tussen:

`semantic selection -> controller pivot -> Qt mouse press -> renderer hit`

De fout is verwijderd. De Qt-laag mag de geselecteerde semantic focus niet meer overschrijven met een toevallige nieuwe hit.

## 3. Nieuwe CWS pivotregel

CWS hanteert voortaan deterministisch:

1. **Part/assembly/multiselect geselecteerd:** displayed bounds center van die selectie is de actieve orbit- en zoomanchor.
2. **Exploded selectie:** displayed/exploded bounds center is leidend; canonical pre-explode positie niet.
3. **Geen selectie:** exacte wereldpositie onder de muis bij mouse-down wordt gebruikt, overeenkomstig point-orbit gedrag van Trimble Connect for Windows.
4. **Fit Selection:** camera wordt op selectie gefit en dezelfde selectie-pivot blijft actief.
5. **Saved view/workspace restore:** orbitfocus wordt opnieuw uit de herstelde selectie bepaald.
6. **Measurement/tool pick:** levert geometriepunt aan de tool maar muteert de semantic part/assembly-selectie niet.
7. **Hidden/ghost context:** mag geen selectie-, orbit-, pan- of measurement-hit overnemen.

De selectie-eerst regel is een bewuste CWS-uitbreiding bovenop Trimble's gedocumenteerde picked-point rotate, omdat de eigenaar expliciet vereist dat een geselecteerd onderdeel het orbitcentrum wordt.

## 4. Desktop handling matrix

| Gebruikershandeling | Trimble-visible gedrag | CWS V15 contract |
|---|---|---|
| Rotate | pick point + left drag | selectiecentrum indien geselecteerd; anders exact picked point + left drag |
| Pan | pick point + left drag | picked-depth pan; middle drag blijft CWS snelle pan |
| Walk Around | aparte mode | aparte mode + left drag + WASD/QE ondersteuning |
| Look Around | aparte mode | camera-position-fixed look mode |
| Scroll zoom | zoom | zoom rond actieve selectie/picked pivot zodat focus niet wegdrijft |
| Space | fit selected | fit selection |
| Double-click object | fit + object focus | select + fit selection |
| Alt + double-click surface | orthogonal surface view | exact face-normal orthogonal view zonder impliciete Fit All |
| Ctrl+U/I/O/P | Rotate/Pan/Walk/Look | gelijk |
| F11 | fullscreen toggle | gelijk |
| Ctrl+Click | add to selection | gelijk |
| Shift+Click | add/remove selection | toggle gelijk |
| Alt+Click | reverse object/assembly selection hierarchy | tijdelijke part/assembly inversion; persistente mode blijft intact |
| Backspace | hide selected | gelijk |
| Shift+Backspace | hide others | isolate geselecteerde context |
| Enter | selected object details | CWS Properties/Provenance dock voor huidige selectie |
| Esc | end tool / clear selection | tool annuleren en selectie wissen volgens actieve state |
| Ctrl+Z / Ctrl+Y | undo / redo | CWS viewer-state undo/redo + orbitfocus resync |
| Right click object | context menu | CWS object context menu |
| Area selection L->R | window semantics | volledig-binnen selectie |
| Area selection R->L | crossing semantics | crossing selectie |
| Measurement active | normal selection disabled | probe-only tool pick; semantic selectie blijft intact |

## 5. Waarom zoom ook is aangepast

Alleen orbit rond een geselecteerd onderdeel corrigeren is onvoldoende wanneer de muiswheel daarna de camera weer rond een andere target schaalt. Daarom schaalt V15 perspective- en orthographic-zoom nu rond dezelfde actieve pivot. Het geselecteerde onderdeel blijft daarmee visueel de stabiele anchor tijdens rotate + zoom.

## 6. Selection hierarchy en assemblies

CWS bewaart de gekozen selection level als sessiestate. Een tijdelijke `Alt+Click` kan object/assembly-selectie omkeren zonder de persistente mode te wijzigen. Een assemblyselectie blijft semantisch één assembly, terwijl de renderer alle renderbare descendants highlight. Orbit gebruikt de gecombineerde displayed bounds van die descendants.

## 7. Tool capture

Normale part/assembly-picking en tool-picking zijn nu expliciet gescheiden. Tijdens een measurement gebruikt de viewer `probe_at` voor wereldpositie/normal/evidence en niet de normale `pick_at`-route die semantic selection zou muteren. Area selection heeft eveneens een eigen capture pad. Dit voorkomt dat meten, zoomen of navigeren onverwacht het actieve onderdeel verandert.

## 8. Regression gates

De T3 Windows gate bevat nu vier expliciete lagen:

- deterministic navigation contract;
- interaction foundation regressions;
- selected-object orbit/zoom parity;
- complete desktop input contract.

Belangrijke vaste regressies omvatten selectiecentrum, assemblycentrum, multiselect, exploded display position, picked-point fallback, perspective/orthographic pivot-zoom, saved-view restore, workspace restore, depth-aware pan, hidden/ghost hit rejection, tool pick isolation en shortcut wiring.

De standalone Windows-build herhaalt deze handlingtests vóór PyInstaller en vereist daarna dezelfde handlingcertificaten opnieuw in de **frozen EXE**, portable ZIP en daadwerkelijk geïnstalleerde applicatie. Het release-manifest mag de handlingvelden uitsluitend op `true` zetten nadat al deze stappen groen zijn.

## 9. Wat bewust niet wordt gekopieerd

Niet overgenomen worden Trimble broncode, DLL-implementaties, iconen, merkassets, credentials, private endpoints, telemetry of cloudservicegedrag. Het gekopieerde doel is de **bedieningslogica die de gebruiker ervaart**. CWS blijft een zelfstandig product met eigen code en visuele identiteit.

## 10. Acceptance voor deze handlingbasis

Deze basis is pas releasewaardig wanneer **dezelfde exacte source commit**:

1. T3 handling gate groen heeft op Windows x64;
2. T4/T5/T6/T7/T8 regressies groen houdt;
3. standalone PyInstaller build groen heeft;
4. frozen packaged self-test de handlingcertificaten bevestigt;
5. packaged GUI, portable, installer, installed-without-external-Python en uninstall groen zijn;
6. SHA-256 release-manifest is opgebouwd;
7. de publish-workflow daarnaast een onafhankelijke **exact-SHA T3 handling gate**, T6 gate en T8 gate vindt;
8. pas daarna als immutable GitHub prerelease wordt gepubliceerd.

Een ChatGPT/sandbox-upload is geen officiële release-route.

## 11. Release-proof velden

Een geldige V15 release moet in de frozen self-test en/of het release-manifest expliciet aantonen:

- `trimble_style_handling_contract_certified = true`;
- `selected_object_orbit_pivot_certified = true`;
- `active_pivot_zoom_certified = true`;
- `t3_navigation_certified = true`;
- `production_marking_released = false` zolang de latere productievalidatie niet is afgerond;
- `production_machine_transfer_allowed = false` zolang geen gevalideerde machine/postprocessorroute is vrijgegeven.
