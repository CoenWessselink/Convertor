# Phase 2 Acceptance

Deze fase is pas gereed verklaard nadat onderstaande controles groen waren:

## Build en test
- API `npm install` geslaagd
- API `npm run seed` geslaagd
- API `npm test` geslaagd
- App `npm install` geslaagd
- App `npm test` geslaagd
- App `npm run build` geslaagd

## Smoke flow
- `GET /health` werkt
- `POST /auth/login` werkt
- `GET /auth/me` werkt
- `POST /jobs/upload` werkt
- `GET /jobs` werkt
- `GET /jobs/:jobId` werkt
- `GET /jobs/:jobId/viewer` werkt
- `GET /jobs/:jobId/dxf` geeft 200 terug

## Fasegrens
Binnen deze fase zijn upload, jobs, detail, viewer en DXF-flow technisch aantoonbaar gesloten.
Browser-e2e met Playwright hoort bij de eindvrijgavefase.
