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
    return "COMPLETE" if str(value).upper()==expected else ("FAILED" if str(value).upper() in {"FAIL","FAILED","NOT_READY"} else "NOT_PROVEN")

def main()->int:
    try:commits=subprocess.check_output(["git","log","-5","--pretty=%h %s"],cwd=ROOT,text=True).strip().replace("\n","<br>")
    except Exception:commits="NOT_PROVEN"
    fresh=status("validation/final_gap_closure/RESULTS.json")
    rows=[
        ("Viewer basis en Trimble-functies","Permanente ViewerHost, selectie/meten/doorsnede","cws_viewer en geïntegreerde Viewer workspace","viewer- en parity-smokes","PARTIAL"),
        ("Loader Engine V2","Workerpool, priority, Cache V2, uploadbudget/governor","Batchcoördinator, brongegroepeerde workers en sessiecache","final_gap_closure plus viewer closeout","COMPLETE" if fresh=="COMPLETE" else "NOT_PROVEN"),
        ("HVPC 3-5 seconden","Volledig exact model binnen doel","Nieuwe batchroute aanwezig; hermeting vereist","cold/warm/same-session benchmark",status("validation/viewer_performance_closeout/FINAL_ACCEPTANCE_REPORT.json")),
        ("10 minuten Viewer soak","Geen stall >100 ms en geen lekken","Historische run had 15 stalls boven 100 ms","PHASE_2_REAL_BENCHMARKS.json","FAILED"),
        ("Same-machine Trimble","Gepaarde observatie op dezelfde IFC en machine","Trimble aanwezig; gepaarde run vereist","TRIMBLE_SAME_MACHINE_COMPARISON.json",status("validation/viewer_performance_closeout/TRIMBLE_SAME_MACHINE_COMPARISON.json")),
        ("UI Master V5/V5.1/V5.2","5 domeinen, 25 taakschermen, industrieel donker ontwerp","Concrete project-, plaat-, print- en maakbaarheidspanelen plus bestaande werkruimten","desktop visuele audit vereist","PARTIAL"),
        ("BOM, machines en optimalisatie","BOM, routing, profiel- en plaatnesting","Bestaande kernen plus MachineRoutingService en plaatpaneel","phase2 plus final_gap_closure","PARTIAL"),
        ("Bewerken en scribing","Alle maakbewerkingen en markeringen","Part Workbench en M18 scribing geïntegreerd","phase2/phase3 smokes","COMPLETE"),
        ("Converteren IFC/STEP/NC","Exact en zonder Part Workbench-afhankelijkheid","Native IFC/STEP BREP-export en hashherstel","roundtrip-hermeting vereist","PARTIAL"),
        ("Tekeningen en PDF","Vectorprojectie, maten en PDF","DrawingProjectionModel plus vector-native PDF","final_gap_closure","COMPLETE" if fresh=="COMPLETE" else "NOT_PROVEN"),
        ("Print Center en uitvoer","Eén DocumentOutputService","DocumentOutputService plus concreet Print Center","final_gap_closure","COMPLETE" if fresh=="COMPLETE" else "NOT_PROVEN"),
        ("Manufacturing Geometry Interpreter V2","Profielherkenning en onafhankelijke BREP-proof","Fase 1 aanwezig; oude corpusgate faalde veilige ambiguïteiten","FINAL_ACCEPTANCE_REPORT.json",status("validation/manufacturing_interpreter/FINAL_ACCEPTANCE_REPORT.json")),
        ("Release en installer","Nieuwe EXE, portable en installer met packaged bewijs","Na bron- en desktopgates opnieuw bouwen","packaged/installer acceptance","NOT_PROVEN"),
    ]
    lines=["# QUEUE COMPLETION MATRIX","","Gereconstrueerd uit prompts, overdrachten, broncode, git-history en echte validatiebestanden. Niet uitgevoerde externe proeven zijn niet groen gemaakt.","",f"Recente commits: {commits}","","| Opdracht/milestone | Verwacht resultaat | Gevonden implementatie | Relevante tests | Status |","|---|---|---|---|---|"]
    lines.extend("| "+" | ".join(str(value).replace("|","\\|") for value in row)+" |" for row in rows);lines += ["","## Gate","","De finale onafhankelijke audit en release-candidate gate blijven gesloten zolang HVPC, de 10-minuten-soak, dezelfde-machine Trimble-vergelijking, visuele desktopacceptatie en installeracceptatie niet aantoonbaar groen zijn.",""]
    (ROOT/"QUEUE_COMPLETION_MATRIX.md").write_text("\n".join(lines),encoding="utf-8");return 0

if __name__=="__main__":raise SystemExit(main())
