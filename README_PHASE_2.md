# CONVERTOR Phase 2 Core Flow Build

Deze fase bouwt door op fase 1 en levert de kernflow werkend op:
- upload
- jobs-overzicht
- jobdetail
- viewer
- DXF-download

Bronbasis:
- opgebouwd vanuit `CONVERTOR_PHASE_D_BUILD (1).zip`
- opgeschoond zonder `node_modules` in de opleverzip

Aangebracht in fase 2:
- app scripts hard gezet op `node node_modules/vite/bin/vite.js` voor stabiele lokale build
- api scripts hard gezet op `--env-file=.env` zodat lokale `.env` echt wordt geladen
- clean package zonder nested opleverzips en zonder buildvervuiling

Demo login:
- tenant: demo
- email: admin@demo.com
- wachtwoord: Admin123!
