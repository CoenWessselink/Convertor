using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Cws.TeklaBridge.Core;
namespace Cws.TeklaBridge.Tests {
 public sealed class TestResult { public string Name {get;set;} public string Status {get;set;} public string Error {get;set;} }
 public sealed class TestSuite {
  public readonly List<TestResult> Results = new List<TestResult>();
  public void Check(string name,Action test) { try {test();Results.Add(new TestResult{Name=name,Status="PASS"});Console.WriteLine("PASS "+name);} catch(Exception ex) {Results.Add(new TestResult{Name=name,Status="FAIL",Error=ex.ToString()});Console.WriteLine("FAIL "+name+": "+ex.Message);} }
  public void True(bool value,string message="assertion failed") {if(!value) throw new Exception(message);}
  public void Equal<T>(T expected,T actual,string message="values differ") {if(!EqualityComparer<T>.Default.Equals(expected,actual)) throw new Exception(message+" expected="+expected+" actual="+actual);}
  public void Throws<T>(Action action,string message="expected exception") where T:Exception {try{action();}catch(T){return;}throw new Exception(message+" "+typeof(T).Name);}
 }
 public static class Program {
  public static int Main(string[] args) {
   if(args.Length>0 && args[0]=="--corpus") {
    if(args.Length!=3){Console.WriteLine("Usage: --corpus manifest.json report.json");return 3;}
    var corpus=new CorpusAnalyzer().Run(args[1]);
    Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(args[2])));
    File.WriteAllText(args[2],JsonUtil.Serialize(corpus));
    Console.WriteLine("CORPUS "+corpus.Status+" "+corpus.AnalyzedCaseCount+"/"+corpus.TargetModelCount+" analyzed; "+corpus.RuntimePassedCaseCount+" runtime gates passed");
    return corpus.Status=="PASS"?0:2;
   }
   var suite=new TestSuite();
   foreach(var type in Assembly.GetExecutingAssembly().GetTypes().Where(t=>t.Name.EndsWith("Tests") && t.GetMethod("Run",new[]{typeof(TestSuite)})!=null).OrderBy(t=>t.Name)) type.GetMethod("Run").Invoke(null,new object[]{suite});
   var report=new {SchemaVersion="1.0",SourceVersion=typeof(Program).Assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion,RecordedAtUtc=DateTime.UtcNow.ToString("o"),Environment=System.Runtime.InteropServices.RuntimeInformation.IsOSPlatform(System.Runtime.InteropServices.OSPlatform.Windows)?"WINDOWS_NET8_TEST_FIXTURE":"LINUX_NET8_TEST_FIXTURE",TestCount=suite.Results.Count,Passed=suite.Results.Count(x=>x.Status=="PASS"),Failed=suite.Results.Count(x=>x.Status!="PASS"),WindowsRuntime="NOT_RUN",TeklaRuntime="NOT_RUN",Results=suite.Results};
   string output=args.Length>0?args[0]:"evidence/latest-tests.json"; var directory=Path.GetDirectoryName(Path.GetFullPath(output));Directory.CreateDirectory(directory);File.WriteAllText(output,JsonUtil.Serialize(report));
   Console.WriteLine("RESULT "+report.Passed+"/"+report.TestCount+" passed; Windows/Tekla NOT_RUN");
   return report.TestCount==0 || report.Failed>0?1:0;
  }
 }
}
