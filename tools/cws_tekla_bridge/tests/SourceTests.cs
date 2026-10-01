using System;
using System.Collections.Generic;
using System.IO;
using Cws.TeklaBridge.Core;
using Newtonsoft.Json;
namespace Cws.TeklaBridge.Tests {
 public static class SourceTests {
  public static void Run(TestSuite t) {
   var dir=Path.Combine(Path.GetTempPath(),"cws-source-"+Guid.NewGuid()); Directory.CreateDirectory(dir);
   try {
    string original=Path.Combine(dir,"original.ifc");File.WriteAllText(original,"explicit-source");var sha=JsonUtil.HashBytes(File.ReadAllBytes(original));
    var part=new CanonicalPart{CanonicalId="occ1",SourceId="source",SourceRevision="R1",PhysicalRole="PRIMARY",Kind="BEAM",Profile="IPE160",MaterialRaw="S275JR",Material="S275JR",Points=new List<Vec3>{new Vec3(0,0,0),new Vec3(1000,0,0)}};
    var model=new SteelModel{SourceId="source",SourceRevision="R1",SourceSha256=sha,Parts=new List<CanonicalPart>{part}};var path=Path.Combine(dir,"snapshot.json");File.WriteAllText(path,JsonUtil.Serialize(model));
    t.Check("source freeze separates canonical payload and original provenance",()=>{var f=SourceFreezeService.LoadCanonical(path,original);t.True(f.OriginalBytesVerified);t.Equal(sha,f.OriginalSha256);t.Equal("S275JR",f.GetModel().Parts[0].Material);});
    t.Check("frozen source immutable returned clone",()=>{var f=SourceFreezeService.LoadCanonical(path);f.GetModel().Parts[0].Material="S355JR";t.Equal("S275JR",f.GetModel().Parts[0].Material);t.True(!f.OriginalBytesVerified);});
    t.Check("freeze detects changed canonical source",()=>{var f=SourceFreezeService.LoadCanonical(path);File.AppendAllText(path," ");t.Throws<InvalidOperationException>(()=>f.VerifyUnchanged());File.WriteAllText(path,JsonUtil.Serialize(model));});
    t.Check("freeze detects changed original artifact",()=>{var f=SourceFreezeService.LoadCanonical(path,original);File.AppendAllText(original,"drift");t.Throws<InvalidOperationException>(()=>f.VerifyUnchanged());File.WriteAllText(original,"explicit-source");});
    t.Check("source hash mismatch rejected",()=>{model.SourceSha256=new string('a',64);File.WriteAllText(path,JsonUtil.Serialize(model));t.Throws<InvalidDataException>(()=>SourceFreezeService.LoadCanonical(path,original));model.SourceSha256=sha;File.WriteAllText(path,JsonUtil.Serialize(model));});
    t.Check("source duplicate roles rejected",()=>{model.Parts.Add(JsonUtil.Clone(part));File.WriteAllText(path,JsonUtil.Serialize(model));t.Throws<InvalidDataException>(()=>SourceFreezeService.LoadCanonical(path));model.Parts.RemoveAt(1);File.WriteAllText(path,JsonUtil.Serialize(model));});
    t.Check("source declared schema required",()=>{File.WriteAllText(path,JsonUtil.Serialize(model).Replace("\"SchemaVersion\": \"1.0\",", ""));t.Throws<JsonSerializationException>(()=>SourceFreezeService.LoadCanonical(path));});
    t.Check("recognition profile conflict has no majority fallback",()=>{var result=RecognitionService.Evaluate(new[]{Obs("SOURCE_METADATA","IPE160",sha),Obs("CATALOG","HEA160",sha),Obs("BREP","IPE160",sha)},sha);t.Equal("REVIEW_REQUIRED",result.Status);t.True(result.Candidate==null);});
    t.Check("source confidence is not profile confidence",()=>{var a=Obs("SOURCE_METADATA","IPE160",sha);a.SourceConfidence=1;a.ProfileConfidence=0;var result=RecognitionService.Evaluate(new[]{a},sha);t.Equal("REVIEW_REQUIRED",result.Status);});
    t.Check("recognition exact evidence remains candidate without authority",()=>{var a=Obs("DETERMINISTIC_REBUILD","IPE160",sha);a.ExactEquivalenceProven=true;var result=RecognitionService.Evaluate(new[]{Obs("SOURCE_METADATA","IPE160",sha),a},sha);t.Equal("CANDIDATE_EVIDENCE_MATCH",result.Status);t.True(result.Reasons.Contains("PRODUCTION_AUTHORITY_STILL_REQUIRED"));});
    t.Check("recognition stale evidence blocked",()=>t.Equal("REVIEW_REQUIRED",RecognitionService.Evaluate(new[]{Obs("CATALOG","IPE160",new string('b',64))},sha).Status));
   } finally {Directory.Delete(dir,true);}
  }
  private static ProfileObservation Obs(string method,string candidate,string sha)=>new ProfileObservation{Method=method,Candidate=candidate,SourceConfidence=1,ProfileConfidence=1,SourceSha256=sha};
 }
}
