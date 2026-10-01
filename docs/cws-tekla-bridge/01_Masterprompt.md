# CWS Tekla Bridge v0.1 — Masterprompt

Windows x64. Gebruiker → GPT → CWS Orchestrator → CWS Tekla Bridge → Tekla Open API. Geen nieuwe grote Convertor of tweede Tekla. UI is leidend en klein. One-round: source freeze → recognition → classify → material/profile/geometry → BUILD_PLAN → Tekla UPSERT → save/reopen → readback → safe self-heal → final audit → release gates.

Canonical SteelModel is één waarheid voor source/BOM/viewer/Tekla/validation/production. Multi-evidence recognition gebruikt metadata, catalogus, extrusie, doorsnede, metrics, BRep/OCCT en deterministic rebuild. Source confidence is niet profile confidence. Materiaal blijft fail-closed; database-default S355JR is nooit productiewaarheid en S275JR blijft S275JR.

Verbindingen: AUTO alleen APPROVED authority + fingerprint match + bewezen component/attributes + validation; anders PROPOSE/BLOCKED. Manual bestaande verbindingen standaard behouden.

Volledige lokale specificaties staan in het startpakket; deze branch is de geïsoleerde implementatielijn.