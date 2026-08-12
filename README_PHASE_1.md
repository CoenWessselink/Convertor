# CONVERTOR Phase 1 Stabilized Build

Dit pakket is opnieuw opgebouwd uit de werkelijk geuploade bronzips in deze chat.

Inhoud:
- Convertor-app: bron uit `CONVERTOR_PHASE_D_BUILD (1).zip`, opgeschoond zonder `node_modules`
- Convertor-Api: bron uit `CONVERTOR_PHASE1_BUILD.zip`, aangevuld met fase-1 compatibiliteitsfixes

Aangebracht in deze regeneratie:
- geen `node_modules` in de zip
- API alias `/auth/*` naast `/api/auth/*`
- demo account wordt automatisch aangemaakt bij serverstart
- `.env.example` voor app wijst naar `http://localhost:4000`

Demo login:
- tenant: demo
- email: admin@demo.com
- wachtwoord: Admin123!
