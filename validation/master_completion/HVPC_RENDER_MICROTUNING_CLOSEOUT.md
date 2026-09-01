# HVPC Render Microtuning Closeout

Status: **PARTIAL**

De verse Qt/VTK-run rendert 5.725 fysieke nodes uit 1.496 exacte resources. 2x MSAA zonder FXAA is de beste geaccepteerde balans, maar haalt met `50,66 ms p95` en `20,39 FPS` de 30-FPS-poort niet.

Een globale quadric-LOD haalde `63,93 FPS`, maar veroorzaakte een eerste-interactieblokkade van `32,12 s` en verloor celkleuren. Een feature-outline-LOD haalde `26,15 FPS`, maar de eerste opbouw duurde `10,59 s`. Beide routes zijn daarom verworpen en niet in de productbackend opgenomen.

De blijvende oplossing vereist een vooraf berekende of asynchroon gegenereerde gesloten-oppervlak-LOD die zowel de first-frame-gate als `p95 <= 33 ms` haalt zonder objecten, kleuren of profielvormen te verliezen.
