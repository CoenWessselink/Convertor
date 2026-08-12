# CONVERTOR FINAL 100 REBUILD

Deze build is opnieuw opgebouwd vanaf de echte broncode uit fase D en niet vanaf de eerdere kleine placeholder-zips.

## Wat is herbouwd
- rijkere dashboard-pagina met stats, recente jobs en directe viewer-route
- demo-sample flow: STEP / IFC / NC1 voorbeeldjob zonder eigen bestand
- verbeterde upload-pagina met duidelijke CTA's
- jobs-overzicht met zoeken, filteren en directe viewer-open knop
- uitgebreidere jobdetail-pagina
- zichtbare viewer-pagina met toolbar, metrics en DXF-download
- opgeschoonde sidebar en navigatie
- API endpoint `POST /jobs/demo-sample`

## Lokaal testen
1. API:
   - `cd Convertor-Api`
   - `copy .env.example .env`
   - `npm install`
   - `npm run seed`
   - `npm run dev`
2. App:
   - `cd Convertor-app`
   - `copy .env.example .env`
   - `npm install`
   - `npm run dev`
3. Login:
   - tenant `demo`
   - email `admin@demo.com`
   - wachtwoord `Admin123!`
4. Maak op dashboard of uploadpagina een demo-job aan en open daarna viewer.
