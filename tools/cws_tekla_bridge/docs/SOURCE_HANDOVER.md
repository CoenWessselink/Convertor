# Bronoverdracht en eenmalige uitvoering
De bestaande Convertor levert zijn SteelModel 1.0-snapshot met de bestaande CLI `project-export-steel-model`. De bridge maakt geen tweede Convertor. De snapshot is een gecontroleerde overdracht voor lezen en review.

`python tools/cws_tekla_bridge/scripts/import_steel_model.py snapshot.json handover.json --repo .`

De importer gebruikt de bestaande SteelModelSnapshot-validator, controleert de snapshot-hash en bronverwijzingen, bewaart occurrence-identiteiten, expliciete bronwaarden en plaatsing als provenance. De hash van het volledige ingelezen bestand wordt apart vastgelegd. Het snapshot bevat geen volledige BRep, contouren en productiekenmerken. Daarom worden daaruit geen liggers of punten afgeleid; alle onderdelen blijven REVIEW_REQUIRED. Een materiaalwaarde uit display_properties is geen materiaalautoriteit. S275JR blijft als bronwaarde bewaard.

De Windows-bridge accepteert daarnaast het stricte `SteelModel`-JSON uit `schemas`. Een volledig canoniek bronpakket moet expliciete punten, fysieke rollen en afzonderlijk bewezen profiel-, materiaal- en geometrieautoriteit bevatten. Die evidence wordt gecontroleerd tegen het onveranderlijke Authority Manifest; een `Status=APPROVED` uit het bronbestand verleent zelf geen bevoegdheid.

`SourceFreezeService` bewaart een immutable kopie en de SHA van de canonical snapshot. Wanneer het originele IFC/STEP-bestand wordt meegegeven, controleert het ook de opgegeven bronhash tegen echte bytes. Zonder origineel is original provenance onbewezen. De UI controleert vóór planning/uitvoering dat de ingelezen canonical snapshot niet is gewijzigd. Iedere source wijziging vereist een nieuwe freeze en plan.

Herkenning scheidt bronconfidence van profielconfidence. Tegenstrijdig metadata/catalogus/BRep/rebuild-bewijs leidt tot review, ook bij een meerderheid. Overeenstemmend bewijs levert een kandidaat en geen productieautoriteit. Native shapes, gaten, bouten, lassen en cuts blijven geblokkeerd zolang de eigen feature/readback-gates niet bewezen zijn.
