# Derde partijen, toegang en herdistributie

## GitHub

Het pakket bevat publieke repository- en branch-URL's, maar geen GitHub-token of accountgegevens. Een nieuwe chat kan alleen pushen wanneer de gebruiker lokaal is aangemeld en schrijfrechten heeft.

## BIM Vision

De lokale BIM Vision-installatie wordt uitsluitend geinventariseerd met paden, versies, groottes en SHA256-hashes. De installatiebestanden worden niet gekopieerd naar dit pakket en niet naar GitHub gepusht. Dit voorkomt ongeoorloofde herdistributie en houdt het pakket beheersbaar.

## Trimble Connect

De door de gebruiker aangeleverde `Trimble Connect.zip` wordt als frozen referentie in het lokale overdrachtspakket opgenomen. Publiceer dit bestand niet automatisch. Gebruik Trimble Connect als interactie- en renderingreferentie, niet als bron voor ongeautoriseerd kopieren van code, assets of licentiegebonden componenten.

## Commerciele runtimes

MATLAB, commerciele solvers en externe databaseclients worden alleen toegevoegd wanneer een concrete codeafhankelijkheid, geldige licentie en redistributierecht bestaan. De actuele verified release heeft deze niet nodig.

## Persoons- en projectgegevens

Voorbeeldmodellen kunnen bedrijfs- of projectinformatie bevatten. Het pakket is lokaal bedoeld. Controleer toestemming en vertrouwelijkheid voordat bestanden naar een publieke repository, issue, chatdienst of derde partij worden geupload.
