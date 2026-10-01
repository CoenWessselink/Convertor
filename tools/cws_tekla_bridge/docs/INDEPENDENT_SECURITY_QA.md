# Independent authorization and execution review

The independent preflight/source agent reviewed the assembled Bridge core, HTTP dispatcher, native guards, persistence, transaction journal, review challenges and connection evidence. This is a source/contract assessment. Genuine Windows/Tekla runtime, reference models, manufacturing readback and production release remain separate open gates.

## Corrections arising from review

| Finding | Correction checked in the final candidate source |
|---|---|
| L0 HTTP readback invoked native close/reopen, which could exceed CHECK_ONLY authority. | HTTP readback now reads current identity/parts only and provides no persistence proof. Native lifecycle remains separately gated. |
| Each batch write compared native revision to the original plan, so the first legitimate write invalidated the second. | Execution checks complete current state against a checkpoint; accepts only the planned target delta; records the resulting identity/state before continuing. A changing-revision fixture regression covers multiple writes. |
| Recomputed plan hashes could conceal out-of-scope/source-conflicting mutation targets. | Plan validation independently checks scope, source/revision, managed ownership, native identity, explicit removal and before-state; source material/profile/geometry authority is revalidated. |
| Live compensation alone could be mistaken for durable native rollback. | Clean compensation terminal is restricted to explicit fixtures. Nonfixture uncertainty remains RECOVERY_REQUIRED and blocks following writes; native durable compensation needs its own implementation/evidence. |
| Uploaded persistence text alone could imply persistent native success. | Public readback does not trust proof strings; execution requires a genuine adapter lifecycle verifier before persistent release evidence. Fixtures never establish production persistence. |
| General component authority and caller-provided connection fingerprints could be reused to claim connection approval. | Family, validation and clash records each require their exact component plus immutable semantic artifact binding, including applicability/attributes/detail, result features and clash tolerance. Native apply remains unimplemented. |
| Native adapter could receive differing raw/resolved material even though core rejected that alias. | Native guard also requires exact equality; S275JR→S355JR is explicitly rejected. |
| Duplicate blocked plan keys could inflate physical counts for one actual part. | Actual physical groups are counted once per canonical-role key; duplicate native parts remain individually counted and reported. |

The source importer additionally keeps original raw material separate from grade, flags conflicts, retains source provenance and leaves geometry/native authority absent. Its eight Python integration tests cover identity, S275JR, missing material, conflict, source/snapshot tamper, units and nonmutating deterministic loading.

## Boundaries checked

- HTTP authenticates a loopback session token and assigns GPT claims server-side; JSON actors/human-token claims cannot grant reviewer, production or governance authority.
- Trusted local operation challenges bind model/revision, scope, source revision, actor/session/human identity, plan and operation/run/request IDs. Challenges expire and consume atomically; source changes supersede stale decisions. A project decision does not modify the global authority manifest.
- Native reader leaves manufacturing hashes absent until independently proved; it does not treat stored UDA hashes as actual feature readback.
- Write intents flush to the append-only journal before mutation. Incomplete/corrupt journal state fails closed; uncertain native state does not silently rejoin a baseline.
- The Windows host uses genuine native/disconnected adapters. No memory fixture is selected by production UI, and normal local USER context receives no production/governance role grant.

Read-contract and fixture evidence does not close Windows start, real Tekla model, save/reopen, Het Koraal, supplied 20-model corpus, native connection/feature/clash, numbering or installer runtime gates. The independent final test execution is recorded separately in `evidence/authority-qa-tests.json` when the exact final assembled binaries are available.
