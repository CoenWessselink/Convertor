# CWS Tekla Bridge v0.1 — Masterprompt
Deze masterprompt bundelt de eerder vastgelegde product-, UI-, engine-, recognition-, materiaal-, verbinding-, API-, review- en autorisatie-eisen.

## Product en UI
Windows x64. Gebruiker → GPT → CWS Orchestrator → CWS Tekla Bridge → Tekla Open API. Geen nieuwe grote Convertor, geen tweede Tekla en geen zware eigen 3D-app. Tekla blijft primaire 3D-omgeving. UI is leidend: licht, compact en rustig.
Schermen: Start/Verbinding; Taak; Scope; Uitvoering; Verbindingen; Samenvatting; Logboek; Resultaat; Review; Instellingen; Help.
Taken: model opbouwen, revisie, aanvullen, controleren, verbindingen, details, herstellen. Scope: geheel, Tekla-selectie, fase, merken, gewijzigd, review. Modes: AUTO, PROPOSE, CHECK_ONLY.

## One-round
SOURCE FREEZE → PREPROCESS → SOURCE IDENTITY → MULTI-EVIDENCE RECOGNITION → CLASSIFY → MATERIAL → PROFILE → GEOMETRY → CALIBRATION → BUILD_PLAN → TEKLA UPSERT → CONNECTIONS indien gevraagd → PERSIST → SAVE → REOPEN → READBACK → SELF-HEAL → FINAL AUDIT → RELEASE GATES.
Zelfde bron/status/opdracht opnieuw = 0 duplicaten, 0 ongewenste nieuwe objecten, 0 onbedoelde wijzigingen.

## Canonical model
Eén SteelModel/Project Model voor source, BOM, viewer, Tekla, validation en production. Canonical occurrence identity blijft leidend. Canonical count en physical Tekla part count zijn verschillende grootheden.

## Recognition
Multi-evidence, heen en terug: source metadata, catalogus, extrusie, doorsnede, bbox/volume/area/solid count/thickness/radii/topology, exacte BRep/OCCT en deterministic rebuild/equivalence. Source confidence is niet profile confidence. Conflict = REVIEW_REQUIRED.

## Materiaal
Raw bron/provenance en normalized waarde apart. Alleen expliciete actuele bron of APPROVED authority-normalisatie/alias mag productie-authority geven. S275JR blijft S275JR. MaterialDatabase-default S355JR is nooit productiewaarheid. Geen afleiding uit objectklasse, profiel, buurpart, meerderheid of GPT.

## Verbindingen
parts → main/secondary → profielen/positie/hoek/afstand/orientatie → detail/projectdetail → bewezen family → component/macro+attributes → resultaat → platen/bouten/lassen/cuts/clash → AUTO/PROPOSE/BLOCKED.
AUTO alleen APPROVED authority + fingerprint match + bewezen attributes + validation. Manual bestaande verbindingen standaard behouden.

## GitHub authority en synchronisatie
Niet automatisch main/branchnaam/hoogste versie. Authority per component = file SHA + commit + schema + tests + runtimebewijs + referentiemodel + bewijsstatus. Praktijkles ↔ regressietest ↔ Authority Manifest ↔ code blijft permanent gesynchroniseerd.

## Release
API-ok, insert, save of visueel goed model is geen PASS. Save→reopen→readback is persistentiebewijs. Eindstatus: RELEASED, COMPLETE_GEOMETRY_WITH_BLOCKS, BLOCKED_REVIEW_REQUIRED of FAILED.
Zie 02_API_Authorization_Contract.md en 03_Opdrachtprompt_Bouwfasen.md voor het uitvoerbare contract.
