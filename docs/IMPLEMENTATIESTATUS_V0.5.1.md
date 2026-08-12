# Implementatiestatus masterprompt - v0.5.1

## Samenvatting

v0.5.1 realiseert de veilige basisvolgorde uit de masterprompt: canoniek model, Trusted Converter PDF, deterministische externe vectoranalyse, menselijke review, begrensde AI, maatgrafiek en roundtripvalidatie. De bestaande NC1/STEP/IFC-kern is behouden.

## Gereed en getest

| Onderdeel | Status |
|---|---|
| Canoniek model schema 1.1 | Gereed |
| Converter-eigen IFC-payload en roundtrip | Gereed en 8/8 focusketens geslaagd |
| Trusted Converter PDF met embedded exact model | Gereed |
| NC1 -> Trusted PDF -> NC1 | 24/24 geslaagd |
| STEP -> Trusted PDF -> STEP | 19/19 geslaagd |
| Trusted PDF -> IFC | 2/2 focusgevallen geslaagd |
| Externe vector-PDF-classificatie en tekst/vector-extractie | Gereed voor huidige scope |
| Gesloten plaatcontour, ronde gaten en contourbogen | Gereed voor eenvoudige vectoriele platen/strips |
| Deterministische maatgrafiek | Gereed; validatie en tamperguard aanwezig |
| Interactieve review | Gereed voor velden, gaten en contourpunten |
| Reviewaudit en allow-list | Gereed |
| Lokale adviserende AI | Gereed |
| Optionele OpenAI Responses-provider | Gereed als expliciet ingeschakelde semantische provider |
| AI geometry-/machinecodeguard | Gereed |
| Gereviewde plaat -> NC1/STEP/semantisch IfcPlate/PDF | Geslaagd op synthetische LO4-keten |
| GUI en CLI PDF-routes | Gereed binnen huidige scope |
| Windows buildworkflow en Inno Setup-bron | Build-ready; niet in deze Linuxruntime uitgevoerd |

## Nog te bouwen in de juiste volgorde

1. Werkelijke LO4-binaire PDF als regressiebron testen.
2. Profiel- en meer-aanzichtreconstructie.
3. Uitgebreide hidden-line-, snede-, detail- en maatplaatsingsengine.
4. Productiebrede scan-/OCR-/foto-import.
5. Multi-part en grote-bestandenvalidatie.
6. Native Windows-build en schone-machine-acceptatie.
7. Materiaal-/onderdeeleditor met tabbladen voor algemene gegevens, extra informatie, bewerkingen, hoeken, gaten, coderingen, prijzen en bewerkingstijden.
8. Versleepbare/sorteerbare eigenschappenlijst en exportfuncties.
9. Projectopslag, licenties en online jobomgeving.

## Veiligheidsgrens

Geen van de resterende functies mag rechtstreeks NC1 of productiegeometrie uit vrije AI-uitvoer maken. Externe tekeningen blijven geblokkeerd totdat kritische geometrie deterministisch is vastgesteld of expliciet door een gebruiker is bevestigd en daarna de roundtripcontrole slaagt.
