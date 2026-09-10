# CWS Convertor — PDF/UI V3 hervatting, 10 september 2026

## Bron en scope

Voortgebouwd op de bestaande `DrawingWorkspacePanel`, maatvoeringsmodellen en
productietekenketen van `e5c09f42fece5f7dbc84a9c2841ea1da96773846` op
`agent/cws-pdf-ui-v3-complete-20260909`. Geen vervangende applicatie en geen
integrale overname van een oudere UI-branch. De overige STEP-, IFC-, DXF-, BOM-,
nesting- en materiaalherkenningsimplementaties blijven intact.

De oorspronkelijke `CWS_CODEX_PDF_UI_INTEGRATIE_V3_2026-09-06(1)(1)(2).zip`
is niet beschikbaar in de hervatte werkomgeving. De repository bevat deze
bijlage niet. Volledige V3-eisendekking en referentiebeeldconformiteit zijn
**niet** bevestigd. Deze levering mag niet als 100% V3-acceptatie worden benoemd.

## Herstel in de bestaande applicatie

Directe Qt-inspecteurvelden voor tekst, prefix, suffix, toleranties, notitie,
zichtbaarheid, referentie/inspectiemaat, maatlijn-/tekstpositie en hoekmodus.
Gemengde selectie wijzigt uitsluitend het bewerkte veld. Een geometrische
tekstoverride behoudt de nominale bronmaat en vereist een reden; een opsteller
keurt de override niet automatisch goed. Verouderde focus-events zijn aan de
actieve document-/selectiecontext gebonden.

Assemblyroots zonder eigen mesh worden getekend uit hun afzonderlijk getransformeerde
componenten, inclusief geneste assemblies. Ontbrekende vereiste componenten en
cyclische/missende subassemblies blokkeren een onvolledig resultaat. Geen stille
terugval naar het hoofdonderdeel. De lokale assembly-BOM bevat de afstammelingen.

Een niet-passende vaste schaal wordt expliciet geweigerd. Een passende vaste
schaal blijft exact behouden. Ongeldige schaaltekst valt niet terug op Auto.
Bij een mislukte generatie verdwijnen de oude preview en een mogelijk oude
linterstatus. Auto blijft als bewuste gebruikerskeuze beschikbaar.

Bladformaat, oriëntatie, schaal, eenheid, aanzichten en maat-/detailopties worden
per tekening opgeslagen in het bestaande project. Dezelfde transacties dragen
undo/redo en de audit. Vrijgegeven revisies en alleen-lezenrollen blijven
vergrendeld. Validatie van een vrijgegeven revisie herschrijft deze niet.

## Bewijs en vrijgavebeperking

`--pdf-v3-evidence` bedient de bestaande Qt-werkplek met echte muis-/toetsgebeurtenissen,
maakt screenshots via `QMainWindow.grab`, schrijft/heropent een echt `.cwscproj`
en rendert een echte PDF. De input is een uitdrukkelijk **synthetische** assembly.
Dezelfde diagnose wordt door de installerketen uit het werkelijk geïnstalleerde
EXE uitgevoerd, zonder externe Python op PATH. Het bewijs bevat broncommit,
bronboom, executablehash en screenshot-hashes. Alleen een schoon bronresultaat
mag als definitief commitgebonden bronbewijs gelden.

De Windows-voortgang en uitkomst staan in de werkelijk uitgevoerde Actions-run;
dit document verklaart geen niet-uitgevoerde build succesvol. Installerpromotie
vereist nog altijd de bestaande kern-, volledige shard-, native herkennings-,
conversie-, installer-/herinstallatie-/deïnstallatietests, plus het geïnstalleerde
V3-bewijs. Er wordt geen oudere installer hernoemd of hergebruikt.

Geen fabricagevrijgave, machinekwalificatie, certificering, digitale ondertekening,
Windows 11/hardwareacceptatie of volledige visuele V3-acceptatie wordt hiermee
geclaimd. Lees ook het bestaande integratie- en herkenningsregister.

## Additional all-sheet scale verification

An adversarial native-BREP test exposed an existing schedule-sheet bug: a 1:2
main view could fit while section A-A silently shrank to approximately 1:3.344,
with the title block still declaring 1:2. The entire section cell is now included
in scale preflight. Native sections and mesh review projections both preserve
the stated global scale, or generation fails visibly; the direct native section
route also refuses an insufficient scale instead of clamping it.

Feature-detail views now choose a fitting independent scale and print that
actual scale next to each detail title, including overflow detail sheets.
Assembly components remain individually identified in those detail views.
`tests/drawing_v3_all_sheet_scale_smoke.py` adds six native regression tests for
these cases. This does not change the unavailable external V3 reference-image
conformity limitation above.
