# U2 Manufacturing / Scribing M1-M18 integration

## Contract

- Viewer V15 / current GitHub M1-M8 remain canonical.
- Frozen Scribing M18 is activated only for M9-M18 authority/evidence behaviour.
- The M18 runtime is checksum-bound to the supplied `0.8.30-beta-dev` source.
- M18 authority stores are not copied into a second project: they are live views of the same Project Model 2.25 compatibility envelope created in U1.
- Direct machine transfer and CWS machine observation remain blocked.

## Gate

The U2 CI gate must prove:

1. U0 baseline remains valid.
2. U1 Project Model 2.25 remains valid.
3. Viewer/current M1-M8 manufacturing regressions remain green.
4. All M9-M18 authority modules load from the checksum-bound runtime.
5. M11 and M18 execute against a unified empty/synthetic project without opening machine transfer.
6. M18 stores survive `.cwscproj` save/reopen through the same Project Model 2.25.

Status: **implementation in progress; CI decides completion**.
