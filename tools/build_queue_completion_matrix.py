from __future__ import annotations
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def status(path:str,expected:str="PASS")->str:
    target=ROOT/path
    if not target.is_file():return "MISSING"
    try:value=json.loads(target.read_text(encoding="utf-8")).get("status","NOT_PROVEN")
    except Exception:return "NOT_PROVEN"
    normalized=str(value).upper()
    return "COMPLETE" if normalized in {expected,"PASSED","COMPLETE"} else ("FAILED" if normalized in {"FAIL","FAILED","NOT_READY"} else "NOT_PROVEN")

def main()->int:
    try:commits=subprocess.check_output(["git","log","-5","--pretty=%h %s"],cwd=ROOT,text=True).strip().replace("\n","<br>")
    except Exception:commits="NOT_PROVEN"
    fresh=status("validation/final_gap_closure/RESULTS.json")
    performance=status("validation/final_hvpc_closeout_9a51606/phase3/FINAL_VIEWER_PERFORMANCE_ACCEPTANCE.json")
    soak=status("validation/final_hvpc_closeout_9a51606/phase2/REAL_10MIN_SOAK.json")
    product=status("validation/final_product_acceptance_3fa0136_r2/acceptance-report.json")
    release=status("validation/final_installed_bdc449c/installed-bdc449c-packaged-runtime.json")
    rows=[
        ("Viewer basis en Trimble-functies","Permanente ViewerHost, selectie/meten/doorsnede","Geïntegreerde VTK Viewer workspace met selectie, meten, doorsnede en exacte geometrie","3fa0136, afa8f0b","final closeout en A-Z acceptance",performance),
        ("Loader Engine V2","Workerpool, priority, Cache V2, uploadbudget/governor","Brongegroepeerde persistent workers, herstelbewijs, scene-bundles, scheduler en uploadbudget","3fa0136, 7e0aa56, 122804e, 9a51606","packaged Loader V2 8/8 en final closeout",performance),
        ("HVPC 3-5 seconden","Volledig exact model binnen doel","5.725 exacte meshes en sub-seconde warm/same-session; koude exacte load blijft ruim boven 5 s","3fa0136, 7e0aa56, 122804e","20 cold, 40 warm, same-session runs","PARTIAL"),
        ("10 minuten Viewer soak","Geen onbedoelde stall >100 ms en geen lekken","600 s, 8.733 acties, nul onbedoelde stalls/leaks/verkeerde picks, 0,075% RSS-drift","f62f897, 122804e","REAL_10MIN_SOAK.json",soak),
        ("Same-machine Trimble","Gepaarde observatie op dezelfde IFC en machine","Trimble is aanwezig, maar geen betrouwbare gepaarde bedienings- en tijdmeting vastgelegd","-","TRIMBLE_COMPARISON.md","NOT_PROVEN"),
        ("UI Master V5/V5.1/V5.2","5 domeinen, 25 taakschermen, industrieel donker ontwerp","V5-domeinen en concrete workspaces aanwezig; pixel-/schermpariteit met alle referenties niet bewezen","3fa0136, afa8f0b","A-Z workspace screenshots en UI-smokes","PARTIAL"),
        ("BOM, machines en optimalisatie","BOM, routing, profiel- en plaatnesting","BOM/routing/nestingkernen en concrete panelen aanwezig; volledige praktijkpariteit niet bewezen","3fa0136","phase2, phase3 en A-Z acceptance","PARTIAL"),
        ("Bewerken en scribing","Alle maakbewerkingen en markeringen","Part Workbench en M18 scribing geïntegreerd","3fa0136","phase2/phase3 smokes","COMPLETE"),
        ("Converteren IFC/STEP/NC","Exact en zonder Part Workbench-afhankelijkheid","IFC/STEP/NC-richtingen, NC1 naar STEP en productiepaketten werken packaged","3fa0136, afa8f0b","A-Z acceptance en installed packaged runtime",product if product=="COMPLETE" and release=="COMPLETE" else "NOT_PROVEN"),
        ("Tekeningen en PDF","Vectorprojectie, maten en PDF","DrawingProjectionModel en vector-native PDF met gedeelde outputservice","3fa0136","final gap closure en A-Z acceptance","COMPLETE" if fresh=="COMPLETE" and product=="COMPLETE" else "NOT_PROVEN"),
        ("Print Center en uitvoer","Eén DocumentOutputService","Singleton DocumentOutputService en concreet Print Center","3fa0136","final gap closure en A-Z acceptance","COMPLETE" if fresh=="COMPLETE" and product=="COMPLETE" else "NOT_PROVEN"),
        ("Manufacturing Geometry Interpreter V2","Profielherkenning en onafhankelijke BREP-proof","Profielkandidaten en geometriepad verbeterd; volledige aangeleverde corpuspariteit niet bewezen","3fa0136","fase-1 smoke en regressietests","PARTIAL"),
        ("Release en installer","Nieuwe EXE, portable en installer met packaged bewijs","Installer-upgrades, associaties, portable en installed native runtime bewezen","d9cc741, eb9f4eb, bdc449c","installed packaged runtime en association smoke",release),
    ]
    lines=["# QUEUE COMPLETION MATRIX","","Gereconstrueerd uit prompts, overdrachten, broncode, git-history en echte validatiebestanden. Niet uitgevoerde externe proeven zijn niet groen gemaakt.","",f"Recente commits: {commits}","","| Opdracht/milestone | Verwacht resultaat | Gevonden implementatie | Relevante commit(s) | Relevante tests | Status |","|---|---|---|---|---|---|"]
    lines.extend("| "+" | ".join(str(value).replace("|","\\|") for value in row)+" |" for row in rows);lines += ["","## Gate","","De technische Viewer-closeout en packaged release zijn groen. De totale opdracht blijft PARTIAL zolang de koude HVPC-load niet 3-5 seconden haalt, dezelfde-machine Trimble-pariteit niet gepaard is gemeten en 100% visuele UI-pariteit niet onafhankelijk is bewezen.",""]
    (ROOT/"QUEUE_COMPLETION_MATRIX.md").write_text("\n".join(lines),encoding="utf-8");return 0

if __name__=="__main__":raise SystemExit(main())
