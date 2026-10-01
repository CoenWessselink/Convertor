# API & Authorization Contract

API /api/v1 via localhost loopback met per-session token. Default deny. Model identity verplicht voor mutaties. BUILD_PLAN is expliciet en iedere canonical occurrence heeft één eindstatus. Writes zijn idempotente upserts in transactions met append-only journal. Save→reopen→readback is verplicht persistentiebewijs.

Authorization gates: CAPABILITY → ACTOR AUTHORITY → EVIDENCE AUTHORITY → RUN/MODE AUTHORITY. Levels L0 READ_ONLY, L1 REVERSIBLE_UI, L2 CWS_MANAGED_REVERSIBLE, L3 ENGINEERING_DECISION, L4 PRODUCTION_CRITICAL, L5 AUTHORITY_CHANGE. GPT mag L0–L2 binnen approved authority aanvragen; L3 vereist human/reviewer; L4 production authority; L5 governance. Geen force override v0.1. Authority Manifest runtime read-only.