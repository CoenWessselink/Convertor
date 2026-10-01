# Opdrachtprompt en bouwfasen

Werk uitsluitend op feature/cws-tekla-bridge-v0.1. Geen force push. UI klein en leidend. Iedere fase eindigt met tests en echt runtimebewijs op dezelfde commit.

0 Authority/preflight freeze.
1 Bridge skeleton + UI + Tekla connect/model identity.
2 Read-only model/catalog/geometry.
3 Transactional L2 writes + save/reopen/readback/idempotence.
4 One-round; Het Koraal harde gate.
5 20-model corpus en regressiematrix.
6 Revision/delta.
7 Connections read/propose.
8 Connections AUTO alleen approved families.
9 Review + human authorization.
10 Production hardening, roundtrip en commit-bound installer/release.

Iedere bug: oorzaak → algemene regel → testcase → Authority Manifest → code/werkwijze.