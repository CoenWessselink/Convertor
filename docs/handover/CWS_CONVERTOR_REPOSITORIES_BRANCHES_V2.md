# CWS Convertor - repositories en branches

## Hoofdrepository

- Repository: `https://github.com/CoenWessselink/Convertor`
- Actuele branch: `agent/cws-product-ui-reintegration-v1`
- Actuele branch-URL: `https://github.com/CoenWessselink/Convertor/tree/agent/cws-product-ui-reintegration-v1`
- Basisbranch: `feature/unified-u4-production-workflow-exe`
- Basis-URL: `https://github.com/CoenWessselink/Convertor/tree/feature/unified-u4-production-workflow-exe`

## Referentiebranches

- Viewer V15 / Trimble-parity: `feature/trimble-parity-v15`
- URL: `https://github.com/CoenWessselink/Convertor/tree/feature/trimble-parity-v15`
- Geintegreerde Viewer V15 + Scribing M18: `feature/unified-v15-scribing-m18`
- URL: `https://github.com/CoenWessselink/Convertor/tree/feature/unified-v15-scribing-m18`

## Frozen bronnen zonder aparte repositorywaarheid

- Profile Nesting 0.8.12: meegeleverde ZIP-overdracht.
- Originele Scribing M18 0.8.30: meegeleverde ZIP-overdracht.
- Viewer V15 diagnostiek/installer: meegeleverde ZIP-overdrachten.

Deze ZIP-bestanden zijn referentiemateriaal en worden niet naar de publieke Git-repository gepusht.

## Toegang

De repository-URL en branches zijn in het pakket vastgelegd. Werkelijke lees- of schrijfrechten volgen uit de GitHub-accountrechten van de gebruiker. Er worden geen credentials in prompts of manifests opgeslagen.

```powershell
git clone https://github.com/CoenWessselink/Convertor.git
Set-Location Convertor
git fetch origin
git switch --track origin/agent/cws-product-ui-reintegration-v1
```

Voor push-rechten moet Git Credential Manager, SSH of een andere door de gebruiker beheerde GitHub-authenticatie actief zijn.

## Exacte snapshot

De exacte branch, commit, remote en aanmaaktijd staan in `09_MANIFESTS/BRANCH_SNAPSHOT.txt`. Het bronarchief in `01_SOURCE` is met `git archive` van die commit gemaakt.
