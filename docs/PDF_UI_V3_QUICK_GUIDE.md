# PDF / Tekening — korte gebruikershandleiding

Open een project in de bestaande CWS Convertor-app en kies **PDF / Tekening**.
Selecteer links het gewenste onderdeel of de assembly. Kies formaat A4–A0,
oriëntatie en schaal. Een vaste schaal die niet past wordt geweigerd: kies een
kleinere tekening (grotere schaalnoemer), groter papier of **Auto**.

**Maat toevoegen.** Kies Horizontaal, Verticaal, Uitgelijnd of een andere maattool.
Stel het snapfilter in. Beweeg naar een echt geometriepunt en controleer de
hoverinformatie. Tab wisselt tussen overlappende snapkandidaten. Klik de benodigde
ankerpunten, controleer de preview en klik de plaats voor maatlijn/tekst.

**Selecteren en eigenschappen.** Kies Selecteer en klik een maatlijn, tekst of grip,
of selecteer het maatobject in de lijst. Bewerk velden in de rechter inspecteur.
Enter bevestigt een tekst-/numeriek veld. Gemengde selecties tonen verschillende
waarden; alleen het werkelijk gewijzigde veld wordt op alle geselecteerde maten
gezet. De berekende waarde blijft geometrisch; een tekstoverride vraagt een reden.

**Verplaatsen.** Selecteer de maat, kies Maatlijn of Maattekst en klik de nieuwe
positie in de tekening. Opnieuw ankeren gebruikt nieuwe echte geometriepunten;
de maat houdt zijn stabiele ID. Stijlwijzigingen die afwijken van de standaard
kunnen checkergoedkeuring vereisen voordat vrijgave mogelijk is.

**Verbergen, verwijderen en herstellen.** Toon/verberg bewaart het maatobject.
Verwijder wist de geselecteerde maat of multiselectie via de bestaande transactie.
Undo en Redo herstellen of herhalen de bewerking, inclusief eigenschappen en audit.
Gebruik een nieuwe revisie om vrijgegeven maatvoering te wijzigen; read-only en
released documenten mogen niet rechtstreeks worden gemuteerd.

**Opslaan en heropenen.** Ctrl+S slaat het bestaande `.cwscproj` op. De maatdocumenten
horen bij de gekozen entity; controleer dezelfde entity na heropening. De modelboom,
revisies en de inspecteur tonen de werkelijk opgeslagen inhoud en status.

**Linter en vrijgave.** Open de Linter-tab voor afzonderlijke problemen. De onderste
regel vat de melding samen; de volledige tekst is bereikbaar als tooltip. Vrijgeven
controleert de actuele tekening opnieuw. Een lege cache of ontbrekend bewijs kan
geen groen licht geven. Eerst zijn de canonieke bron, geometrie, roundtrips,
productiematen, toegestane rol en eventuele stijlgoedkeuring nodig.

**PDF.** PDF exporteren maakt de tekening; Trusted PDF vraagt aantoonbaar actuele
canonieke onderdeelgegevens. Een review-assembly wordt niet heimelijk vervangen
door één onderdeel om deze eis te omzeilen. Voor een externe PDF blijft de bestaande
PDF-analyse afzonderlijk beschikbaar. Een softwaretest-PASS is geen productievrijgave.
