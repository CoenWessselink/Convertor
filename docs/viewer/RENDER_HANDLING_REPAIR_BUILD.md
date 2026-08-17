# CWS Viewer — Rendering & Handling Repair Build

Scope for the single post-Phase-2 repair build requested after visual comparison with the supplied reference screenshots and current Trimble Connect help.

Acceptance gates:

1. No tessellation-triangle diagonals in normal shaded model display.
2. Shaded+edges may show only boundary/sharp feature edges, never every triangle edge.
3. Mouse-wheel zoom anchors to the model point below the mouse cursor; fallback is the active orbit target only when no model point is available.
4. One standard 120-unit wheel notch is a small deterministic zoom step.
5. Rotate/select cursor is an arrow; Pan is the only hand cursor and closes while dragging.
6. Large-model orbit/pan/zoom remains event-coalesced and does not rebuild scene geometry.
7. Renderer uses hard-edge-aware normals, multisample antialiasing, FXAA when available and depth peeling on the interactive GPU path.
8. Default model display is clean shaded rendering with improved lighting; feature edges are optional rather than forced.
9. Selection overlay must not reveal triangulation edges.
10. Existing selected-object orbit pivot, tool capture, review, coordination and production fail-closed contracts remain green.

Trimble is used only as a behavioural reference. No proprietary source, binaries, assets or implementation are copied into CWS.
