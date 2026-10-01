# Review, verbindingen en modelcorpus

Deze onderdelen zitten in dezelfde Core-build. De uitgevoerde regressies zijn headless contracttests. Native verbindingen aanbrengen, clashcontrole in Tekla en het 20-modelcorpus hebben nog geen daadwerkelijk Windows/Tekla-runtimebewijs.

## Projectreview

`ReviewService.Propose` bevriest één voorstel voor één brononderdeel en physical role. Oud/nieuw, bronrevisie, volledig model, scope, reden, bewijsverwijzingen en operation hash worden bewaard. Een projectbeslissing wijzigt nooit een globale authority, materiaaltabel, profielalias of ander onderdeel.

De WinForms-host beschikt over `CreateTrustedLocalUi`. Alleen lokale UI-events mogen deze facade gebruiken. HTTP en GPT beschikken uitsluitend over voorstellen en geschiedenis: geen challenge-uitgifte of menselijke bevestiging. De autorisatiematrix en `TrustedPrincipal` blokkeren een verzonden `Actor=USER` of `Actor=AUTHORIZED_REVIEWER` als bewijs van menselijke identiteit; principal en session komen niet uit JSON.

Een challenge bevat een cryptografisch willekeurige token van 256 bits. De store bewaart uitsluitend de SHA-256 daarvan, de binding, vervaltijd en consumptie. De standaardlevensduur is twee minuten, de maximale vijf minuten. Een challenge is gebonden aan model, scope, bronrevisie, actor en de beoordeelde operation hash. Operation challenges binden daarnaast lokale identiteit, sessie, endpoint, request/run/operation IDs, mode en dry-run. De bestandlease serialiseert wijzigingen; een atomische bestandvervanging voorkomt gedeeltelijke database-inhoud. Herstarten herstelt de challenge-status en geeft geen nieuw gebruiksrecht.

Voor `AuthorizationService.ConfirmationValidator` gebruikt de host `ReviewService.ConsumeOperationConfirmation`. Deze callback consumeert de token pas nadat de overige autorisatiegates zijn gepasseerd. Er bestaat geen HTTP-functie die een trusted UI-facade maakt.

`SupersedeSource` maakt oude voorstellen, besluiten en challenges ongeldig. `ApplyProjectResolution` vereist hetzelfde onderdeel, physical role, bron, revisie, model, scope en ongewijzigde oude veldwaarde. Een gewijzigde materiaal-, profiel- of geometriewaarde verliest bestaande authority; aanvullende actuele bron- of projectbewijzen zijn vereist voordat de build-engine productieautoriteit kan erkennen. De resolution retourneert invalidations voor BUILD_PLAN, CONNECTION_FINGERPRINT, READBACK en FINAL_AUDIT. Er volgt altijd een nieuw gevalideerd plan en native save/reopen/readback voordat enige release mogelijk is.

## Verbindingen

De fingerprint verwerkt expliciete main/secondary identiteit, physical role, bron/revisie, profiel, raw/normalized materiaal, punten, geometry/manufacturing hashes, fase/merk, contactpunt, richtingen, hoek, spleet, oriëntatie, detail en attribuut-SHA's. Secondary-volgorde is deterministisch; het wijzigen van main/secondary blijft betekenisvol. Ontbrekende, ongeldige of stale gegevens blokkeren. Er is geen engineering-afleiding uit naburige profielen of meerderheid.

Bestaande manual, onbekende origin of manual-downstream verbindingen krijgen KEEP. Een onbekende bewezen family-match blijft PROPOSE. AUTO vereist precies één APPROVED family met dezelfde fingerprint, componentbron, detail en attributen. Een JSON-record met `Status=APPROVED` is geen authority: `AuthorityService` controleert de ingevroren manifestversie, commit en echte bewijsbestanden. De authority-components zijn exact `connection.family`, `connection.validation` en `connection.clash`.

De goedgekeurde inhoud is ook gebonden aan immutable artefacts. `FamilyBindingJson` moet als bytes in een `CONNECTION_FAMILY_SPEC` artifact zijn bewaard; `ValidationBindingJson` in `CONNECTION_VALIDATION`; `ClashBindingJson` in `CONNECTION_CLASH`. De bijbehorende `BindingArtifactId` en SHA moeten met het goedgekeurde manifest overeenkomen. De family-binding omvat de gehele applicability/fingerprintlijst en attributen. De validation-binding omvat joint/result, detail, component, platen/bouten/lassen/cuts en hun validatie. De clash-binding omvat hetzelfde joint/result, toleranties en het clashresultaat. Caller-supplied applicability of generiek bewijs van een ander component kan deze gate niet omzeilen.

`AUTO_READY` beschrijft uitsluitend deze authoritygates. `NativeApplyImplemented=false` blijft zichtbaar. De huidige adapter biedt geen connection apply/save/reopen/readback-gate. Het resultaat is dus geen aangebrachte verbinding, clashvrij model of functionele fase-8 PASS.

`ConnectionAttributeReader` leest UTF-8 tekst of JSON-scalar attributen als data. Duplicaten, executable bestandstypen, onverwachte lijnen en bestanden groter dan 1 MiB worden geweigerd. Er wordt geen macro, script, shell of DLL uit de TS-map uitgevoerd.

## Corpus

`corpus/manifest.json` bevat het echte doel van twintig representatieve modellen en één nog ontbrekende referentiecase Het Koraal. Hij heeft geen verzonnen snapshots of twintig hernoemde fixtures. `NOT_RUN` betekent ontbrekende bron/snapshot/reference-input; `ANALYZED_NO_RUNTIME_PROOF` betekent dat data is vergeleken zonder bewezen native persistence; `FAILED` betekent dat inputs, hashes of readback afwijken.

Voeg voor iedere werkelijke case toe: CaseId, ReferenceModel, HardGate, relatieve SourcePath, SourceFileSha256, SnapshotPath, SnapshotFileSha256 en optioneel BeforeSourcePath plus SHA voor revisieparen. Paden blijven onder de manifestdirectory; symlinks en pad-escapes worden geweigerd. De analyzer leest canonical SteelModel JSON en echte AdapterSnapshot JSON. IFC-bronbestanden mogen als provenance bewaard worden maar worden hier niet geraden of als snapshots behandeld.

Een runtime PASS vereist een niet-fixture snapshot, persistencerecord, passend goedgekeurd `corpus.runtime:<CaseId>`-bewijs en een `CORPUS_CASE_PROOF` artefact met exact de bytes uit `CorpusAnalyzer.CaseBindingJson(case,snapshot)`. Deze binding bevat bron-, snapshot- en revisie-SHA, model identity en persistencebewijs. Het source model moet tevens goedgekeurde materiaal-, profiel- en geometrieauthority hebben. Eén algemeen runtimebewijs kan geen caller-supplied snapshots goedkeuren.

Een compleet corpus vereist minimaal het opgegeven echte case-aantal, elke case PASS en circa vijf hard gates. Missing/reference-tests worden nooit overgeslagen en als PASS geteld.
