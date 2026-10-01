using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Cws.TeklaBridge.Core;

namespace Cws.TeklaBridge.Tests
{
    public static class EngineTests
    {
        public static void Run(TestSuite t)
        {
            t.Check("Engine deterministic plan and canonical/physical roles", () => {
                var authority = AuthorityService.CreateFixtureAuthority(); var source = Source(authority, "r1", Part(authority,"A"), Part(authority,"A","WEB"), Part(authority,"B"));
                var planner = new PlanService(authority); var first = planner.Create(source,new List<CanonicalPart>(),Identity(),new ScopeSpec());
                source.Parts.Reverse(); var second = planner.Create(source,new List<CanonicalPart>(),Identity(),new ScopeSpec());
                t.Equal(first.PlanHash,second.PlanHash); t.Equal(3,first.Items.Count); t.True(first.Items.All(x=>x.Status=="CREATE"));
                var adapter = new FixtureAdapter(Identity()); var run = Execute(first,adapter,authority);
                t.Equal("TEST_FIXTURE_PASS",run.Status); t.Equal(2,run.CanonicalCount); t.Equal(3,run.PhysicalCount); t.True(!run.Audit.PersistenceProven);
            });
            t.Check("Engine duplicate canonical role blocks", () => {
                var a=AuthorityService.CreateFixtureAuthority(); var p=Part(a,"A"); var plan=new PlanService(a).Create(Source(a,"r1",p,JsonUtil.Clone(p)),new List<CanonicalPart>(),Identity(),new ScopeSpec());
                t.Equal(2,plan.Items.Count); t.True(plan.Items.All(x=>x.Status=="BLOCK"));
            });
            t.Check("Engine duplicate native canonical role blocks", () => {
                var a=AuthorityService.CreateFixtureAuthority(); var p=Part(a,"A"); var q=JsonUtil.Clone(p);p.Managed=q.Managed=true;p.NativeId="N1";q.NativeId="N2";
                var plan=new PlanService(a).Create(Source(a,"r1",p),new List<CanonicalPart>{p,q},Identity(),new ScopeSpec()); t.Equal("BLOCK",plan.Items[0].Status);
            });
            t.Check("Engine source revision mismatch rejects part", () => {
                var a=AuthorityService.CreateFixtureAuthority(); var p=Part(a,"A");p.SourceRevision="stale";var plan=new PlanService(a).Create(Source(a,"r1",p),new List<CanonicalPart>(),Identity(),new ScopeSpec());t.Equal("REVIEW",plan.Items[0].Status);
            });
            t.Check("Engine material raw normalization conflict no fallback", () => {
                var a=AuthorityService.CreateFixtureAuthority(); var p=Part(a,"A");p.MaterialRaw="S275JR";p.Material="S355JR";var plan=new PlanService(a).Create(Source(a,"r1",p),new List<CanonicalPart>(),Identity(),new ScopeSpec());t.Equal("REVIEW",plan.Items[0].Status);t.Equal("S275JR",plan.Items[0].After.MaterialRaw);
            });
            t.Check("Engine unknown material blocks without fallback", () => {
                var a=AuthorityService.CreateFixtureAuthority(); var p=Part(a,"A");p.Material=null;var plan=new PlanService(a).Create(Source(a,"r1",p),new List<CanonicalPart>(),Identity(),new ScopeSpec());t.Equal("REVIEW",plan.Items[0].Status);t.True(plan.Items[0].After.Material==null);
            });
            t.Check("Engine fake approved authority cannot pass immutable manifest", () => {
                var a=AuthorityService.CreateFixtureAuthority();var p=Part(a,"A");p.GeometryAuthority.Status="APPROVED";var plan=new PlanService(a).Create(Source(a,"r1",p),new List<CanonicalPart>(),Identity(),new ScopeSpec());t.Equal("REVIEW",plan.Items[0].Status);
            });
            t.Check("Engine phase scope exact and empty scope rejected", () => {
                var a=AuthorityService.CreateFixtureAuthority();var p=Part(a,"A");p.Phase="1";var q=Part(a,"B");q.Phase="11";var planner=new PlanService(a);var plan=planner.Create(Source(a,"r1",p,q),new List<CanonicalPart>(),Identity(),new ScopeSpec{Kind="PHASE",Values=new List<string>{"1"}});t.Equal(1,plan.Items.Count);t.Equal(p.Key,plan.Items[0].Key);t.Throws<ArgumentException>(()=>planner.Create(Source(a,"r1",p),new List<CanonicalPart>(),Identity(),new ScopeSpec{Kind="PHASE"}));
            });
            t.Check("Engine native selection scope preserves unselected parts", () => {
                var a=AuthorityService.CreateFixtureAuthority();var p=Part(a,"A");p.Managed=true;p.NativeId="N1";var q=Part(a,"B");q.Managed=true;q.NativeId="N11";var plan=new PlanService(a).Create(Source(a,"r1",p,q),new List<CanonicalPart>{p,q},Identity(),new ScopeSpec{Kind="SELECTION",Values=new List<string>{"N1"}});t.Equal(1,plan.Items.Count);t.Equal(p.Key,plan.Items[0].Key);
            });
            t.Check("Engine no implicit delete and manual keep", () => {
                var a=AuthorityService.CreateFixtureAuthority();var managed=Part(a,"A");managed.Managed=true;managed.NativeId="N1";var manual=Part(a,"B");manual.Managed=false;manual.NativeId="N2";
                var plan=new PlanService(a).Create(Source(a,"r2"),new List<CanonicalPart>{managed,manual},Identity(),new ScopeSpec());t.Equal("BLOCK",plan.Items.Single(x=>x.Key==managed.Key).Status);t.Equal("KEEP",plan.Items.Single(x=>x.Key==manual.Key).Status);
            });
            t.Check("Engine explicit removal requires managed identity revision and no downstream", () => {
                var a=AuthorityService.CreateFixtureAuthority();var p=Part(a,"A");p.Managed=true;p.NativeId="N1";var source=Source(a,"r2");source.PreviousSourceRevision="r1";source.ExplicitRemovals.Add(p.Key);var planner=new PlanService(a);
                t.Equal("REMOVE",planner.Create(source,new List<CanonicalPart>{p},Identity(),new ScopeSpec()).Items[0].Status);p.ManualDownstream=true;t.Equal("BLOCK",planner.Create(source,new List<CanonicalPart>{p},Identity(),new ScopeSpec()).Items[0].Status);
            });
            t.Check("Engine explicit remove persists in fixture", () => {
                var a=AuthorityService.CreateFixtureAuthority();var p=Part(a,"A");p.Managed=true;p.NativeId="N1";var source=Source(a,"r2");source.PreviousSourceRevision="r1";source.ExplicitRemovals.Add(p.Key);var adapter=new FixtureAdapter(Identity(),new[]{p});var plan=new PlanService(a).Create(source,adapter.ReadParts(),Identity(),new ScopeSpec());var run=Execute(plan,adapter,a);t.Equal("TEST_FIXTURE_PASS",run.Status);t.Equal(0,adapter.ReadParts().Count);t.Equal(1,adapter.RemoveCalls);
            });
            t.Check("Engine stale protected plan rejects tampering", () => {
                var a=AuthorityService.CreateFixtureAuthority();var adapter=new FixtureAdapter(Identity());var plan=new PlanService(a).Create(Source(a,"r1",Part(a,"A")),adapter.ReadParts(),Identity(),new ScopeSpec());var ctx=Context(plan);plan.Items[0].After.Profile="HEA300";var run=Service(adapter,a).Execute(plan,ctx);t.Equal("BLOCKED_REVIEW_REQUIRED",run.Status);t.Equal(0,adapter.UpsertCalls);
            });
            t.Check("Engine stale model revision blocks zero writes", () => {
                var a=AuthorityService.CreateFixtureAuthority();var adapter=new FixtureAdapter(Identity());var plan=new PlanService(a).Create(Source(a,"r1",Part(a,"A")),adapter.ReadParts(),Identity(),new ScopeSpec());adapter.ChangeModelRevision("changed");var run=Execute(plan,adapter,a);t.True(run.Events.Contains("MODEL_IDENTITY_MISMATCH"));t.Equal(0,adapter.UpsertCalls);
            });
            t.Check("Engine exact scope hash rejects altered context", () => {
                var a=AuthorityService.CreateFixtureAuthority();var adapter=new FixtureAdapter(Identity());var plan=new PlanService(a).Create(Source(a,"r1",Part(a,"A")),adapter.ReadParts(),Identity(),new ScopeSpec());var ctx=Context(plan);ctx.Scope.Kind="CHANGED";var run=Service(adapter,a).Execute(plan,ctx);t.True(run.Events.Contains("SCOPE_MISMATCH"));t.Equal(0,adapter.UpsertCalls);
            });
            t.Check("Engine dry run and check mode never write", () => {
                var a=AuthorityService.CreateFixtureAuthority();var adapter=new FixtureAdapter(Identity());var plan=new PlanService(a).Create(Source(a,"r1",Part(a,"A")),adapter.ReadParts(),Identity(),new ScopeSpec());var ctx=Context(plan);ctx.DryRun=true;var run=Service(adapter,a).Execute(plan,ctx);t.Equal("PREPARED",run.Status);t.Equal(0,adapter.SaveCalls);t.Equal(0,adapter.UpsertCalls);
            });
            t.Check("Engine idempotency replay does not reapply", () => {
                var a=AuthorityService.CreateFixtureAuthority();var adapter=new FixtureAdapter(Identity());var plan=new PlanService(a).Create(Source(a,"r1",Part(a,"A")),adapter.ReadParts(),Identity(),new ScopeSpec());var context=Context(plan);var service=Service(adapter,a);var first=service.Execute(plan,context);var second=service.Execute(plan,context);t.Equal(first.Status,second.Status);t.Equal(1,adapter.UpsertCalls);t.Equal(1,adapter.SaveCalls);t.True(second.Events.Any(x=>x.StartsWith("IDEMPOTENT_REPLAY:")));
            });
            t.Check("Engine idempotency never lies about changed state", () => {
                var a=AuthorityService.CreateFixtureAuthority();var adapter=new FixtureAdapter(Identity());var plan=new PlanService(a).Create(Source(a,"r1",Part(a,"A")),adapter.ReadParts(),Identity(),new ScopeSpec());var context=Context(plan);var service=Service(adapter,a);service.Execute(plan,context);adapter.ChangeModelRevision("external-edit");var second=service.Execute(plan,context);t.Equal("BLOCKED_REVIEW_REQUIRED",second.Status);t.True(second.Events.Contains("IDEMPOTENT_REPLAY_STATE_CHANGED"));t.Equal(1,adapter.UpsertCalls);
            });
            t.Check("Engine reused request with altered operation rejected", () => {
                var a=AuthorityService.CreateFixtureAuthority();var adapter=new FixtureAdapter(Identity());var plan=new PlanService(a).Create(Source(a,"r1",Part(a,"A")),adapter.ReadParts(),Identity(),new ScopeSpec());var context=Context(plan);var service=Service(adapter,a);service.Execute(plan,context);context.OperationId="replacement";var second=service.Execute(plan,context);t.True(second.Events.Contains("IDEMPOTENCY_KEY_CONFLICT"));t.Equal(1,adapter.UpsertCalls);
            });
            t.Check("Engine second fresh identical source run produces zero mutations", () => {
                var a=AuthorityService.CreateFixtureAuthority();var adapter=new FixtureAdapter(Identity());var source=Source(a,"r1",Part(a,"A"));var planner=new PlanService(a);Execute(planner.Create(source,adapter.ReadParts(),Identity(),new ScopeSpec()),adapter,a);var secondPlan=planner.Create(source,adapter.ReadParts(),Identity(),new ScopeSpec());t.Equal("KEEP",secondPlan.Items[0].Status);var result=Execute(secondPlan,adapter,a);t.Equal(0,result.Mutations);t.Equal(1,adapter.ReadParts().Count);
            });
            t.Check("Engine partial write failure compensation proves restoration", () => {
                var a=AuthorityService.CreateFixtureAuthority();var adapter=new FixtureAdapter(Identity()){FailOnUpsertCall=2,FailAfterMutation=true};var plan=new PlanService(a).Create(Source(a,"r1",Part(a,"A"),Part(a,"B")),adapter.ReadParts(),Identity(),new ScopeSpec());var journal=Journal();var run=new ExecutionService(adapter,new AuthorizationService(authority:a),journal).Execute(plan,Context(plan));t.Equal("FAILED",run.Status);t.Equal(0,adapter.ReadParts().Count);t.Equal(0,journal.Unfinished().Count);t.True(journal.ReadAll().Any(x=>x.Kind=="WRITE_INTENT"));t.True(journal.ReadAll().Any(x=>x.Kind=="ROLLED_BACK"));
            });
            t.Check("Engine uncertain partial write blocks later crash recovery", () => {
                var a=AuthorityService.CreateFixtureAuthority();var adapter=new FixtureAdapter(Identity()){FailOnUpsertCall=1,FailAfterMutation=true,FailCompensation=true};var plan=new PlanService(a).Create(Source(a,"r1",Part(a,"A")),adapter.ReadParts(),Identity(),new ScopeSpec());var journal=Journal();var service=new ExecutionService(adapter,new AuthorizationService(authority:a),journal);var run=service.Execute(plan,Context(plan));t.Equal("FAILED",run.Status);t.Equal(1,journal.Unfinished().Count);var later=service.Execute(plan,Context(plan));t.True(later.Events.Contains("RECOVERY_REQUIRED_INCOMPLETE_TRANSACTION"));t.Equal(1,adapter.UpsertCalls);
            });
            t.Check("Engine persistence holes mismatch fails and rolls back", () => {
                var a=AuthorityService.CreateFixtureAuthority();var adapter=new FixtureAdapter(Identity()){OnReadback=parts=>parts[0].ManufacturingHash=JsonUtil.HashText("holes missing")};var plan=new PlanService(a).Create(Source(a,"r1",Part(a,"A")),adapter.ReadParts(),Identity(),new ScopeSpec());var run=Execute(plan,adapter,a);t.Equal("FAILED",run.Status);t.True(run.Audit.Issues.Any(x=>x.Code=="MANUFACTURING_READBACK_MISMATCH"));t.Equal(0,adapter.ReadParts().Count);t.Equal(0,adapter.RepairCalls);
            });
            t.Check("Engine absent manufacture proof never matches empty", () => {
                var a=AuthorityService.CreateFixtureAuthority();var p=Part(a,"A");var plan=new PlanService(a).Create(Source(a,"r1",p),new List<CanonicalPart>(),Identity(),new ScopeSpec());p.Managed=true;p.ManufacturingHash=null;plan.Items[0].After.ManufacturingHash=null;var audit=new ReadbackService().Compare(plan,new AdapterSnapshot{Identity=Identity(),Parts=new List<CanonicalPart>{p},PersistenceProof="fixture",IsFixture=true});t.Equal("FAILED",audit.Status);t.True(audit.Issues.Any(x=>x.Code=="MANUFACTURING_READBACK_MISMATCH"));
            });
            t.Check("Engine self heal limited to two proven metadata attempts", () => {
                var a=AuthorityService.CreateFixtureAuthority();var p=Part(a,"A");p.Udas["CWS_SCOPE_HASH"]="fixed";var adapter=new FixtureAdapter(Identity()){OnReadback=parts=>parts[0].Udas.Remove("CWS_SCOPE_HASH")};var plan=new PlanService(a).Create(Source(a,"r1",p),adapter.ReadParts(),Identity(),new ScopeSpec());var run=Execute(plan,adapter,a);t.Equal(2,adapter.RepairCalls);t.Equal("BLOCKED_REVIEW_REQUIRED",run.Status);t.True(run.Audit.Issues.Any(x=>x.Repairable));
            });
            t.Check("Engine corrupted journal blocks before writes", () => {
                var directory=Path.Combine(Path.GetTempPath(),"cws-engine-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(directory);File.WriteAllText(Path.Combine(directory,"transactions.jsonl"),"{truncated");t.Throws<InvalidDataException>(()=>new JournalStore(directory));
            });
            t.Check("Engine absent blocked source never claims complete geometry", () => {
                var a=AuthorityService.CreateFixtureAuthority();var p=Part(a,"A");p.Material=null;var adapter=new FixtureAdapter(Identity());var plan=new PlanService(a).Create(Source(a,"r1",p),adapter.ReadParts(),Identity(),new ScopeSpec());var run=Execute(plan,adapter,a);t.Equal("BLOCKED_REVIEW_REQUIRED",run.Status);t.Equal("REVIEW_REQUIRED",run.Audit.Status);t.Equal(0,adapter.UpsertCalls);t.Equal(0,run.PhysicalCount);
            });
            t.Check("Engine physical count never doubles a repeated BLOCK source role", () => {
                var a=AuthorityService.CreateFixtureAuthority();var p=Part(a,"A");p.Managed=true;p.NativeId="N1";var plan=new PlanService(a).Create(Source(a,"r1",JsonUtil.Clone(p),JsonUtil.Clone(p)),new List<CanonicalPart>{p},Identity(),new ScopeSpec());t.Equal(2,plan.Items.Count);var audit=new ReadbackService().Compare(plan,new AdapterSnapshot{Identity=Identity(),Parts=new List<CanonicalPart>{p},IsFixture=true,PersistenceProof="TEST_FIXTURE_ONLY"});t.Equal(1,audit.PhysicalCount);t.Equal(1,audit.CanonicalCount);
            });
            t.Check("Engine duplicated native identity across roles blocks mutation", () => {
                var a=AuthorityService.CreateFixtureAuthority();var p=Part(a,"manual-A");p.NativeId="N1";var q=Part(a,"manual-B");q.NativeId="N1";var adapter=new FixtureAdapter(Identity(),new[]{p,q});var plan=new PlanService(a).Create(Source(a,"r1",Part(a,"A")),adapter.ReadParts(),Identity(),new ScopeSpec());var run=Execute(plan,adapter,a);t.True(run.Events.Contains("DUPLICATE_NATIVE_ID"));t.Equal(0,adapter.UpsertCalls);
            });
            t.Check("Engine changed scope excludes semantically identical managed source", () => {
                var a=AuthorityService.CreateFixtureAuthority();var sourcePart=Part(a,"A");var actual=JsonUtil.Clone(sourcePart);actual.Managed=true;actual.NativeId="N1";var plan=new PlanService(a).Create(Source(a,"r1",sourcePart),new List<CanonicalPart>{actual},Identity(),new ScopeSpec{Kind="CHANGED"});t.Equal(0,plan.Items.Count);
            });
            t.Check("Engine manual native baseline retains unknown manufacturing without fabrication", () => {
                var a=AuthorityService.CreateFixtureAuthority();var manual=Part(a,"manual");manual.SourceId=null;manual.SourceRevision=null;manual.Managed=false;manual.NativeId="manual-id";manual.ManufacturingHash=null;manual.MaterialAuthority=null;var adapter=new FixtureAdapter(Identity(),new[]{manual});var plan=new PlanService(a).Create(Source(a,"r1",Part(a,"A")),adapter.ReadParts(),Identity(),new ScopeSpec());var run=Execute(plan,adapter,a);t.Equal("TEST_FIXTURE_PASS",run.Status);t.Equal(1,run.CanonicalCount);t.Equal(1,run.PhysicalCount);t.Equal(2,adapter.ReadParts().Count);t.True(adapter.ReadParts().Single(x=>x.NativeId=="manual-id").ManufacturingHash==null);
            });
            t.Check("Engine downstream manual work retained for unchanged source", () => {
                var a=AuthorityService.CreateFixtureAuthority();var p=Part(a,"A");var before=JsonUtil.Clone(p);before.Managed=true;before.ManualDownstream=true;before.NativeId="N1";var plan=new PlanService(a).Create(Source(a,"r1",p),new List<CanonicalPart>{before},Identity(),new ScopeSpec());t.Equal("KEEP",plan.Items[0].Status);t.True(plan.Items[0].After.ManualDownstream);
            });
            t.Check("Engine own revision advances across multiwrite plan", () => {
                var a=AuthorityService.CreateFixtureAuthority();var adapter=new FixtureAdapter(Identity()){RevisionTracksState=true};var plan=new PlanService(a).Create(Source(a,"r1",Part(a,"A"),Part(a,"B")),adapter.ReadParts(),adapter.GetIdentity(),new ScopeSpec());var run=Execute(plan,adapter,a);t.Equal("TEST_FIXTURE_PASS",run.Status);t.Equal(2,run.Mutations);t.Equal(2,adapter.ReadParts().Count);
            });
            t.Check("Engine own write cannot hide unrelated native state changes", () => {
                var a=AuthorityService.CreateFixtureAuthority();var manual=Part(a,"manual");manual.NativeId="manual-id";manual.Managed=false;var adapter=new FixtureAdapter(Identity(),new[]{manual}){RevisionTracksState=true,AfterUpsert=parts=>parts.Single(x=>x.CanonicalId=="manual").Profile="HEA300"};var plan=new PlanService(a).Create(Source(a,"r1",Part(a,"A"),Part(a,"B")),adapter.ReadParts(),adapter.GetIdentity(),new ScopeSpec());var run=Execute(plan,adapter,a);t.Equal("FAILED",run.Status);t.Equal(1,adapter.UpsertCalls);t.Equal("HEA200",adapter.ReadParts().Single().Profile);t.True(run.Events.Any(x=>x.Contains("UNPLANNED_SIDE_EFFECT")));
            });
            t.Check("Engine rehashed malicious plan cannot expand declared scope", () => {
                var a=AuthorityService.CreateFixtureAuthority();var adapter=new FixtureAdapter(Identity());var plan=new PlanService(a).Create(Source(a,"r1",Part(a,"A")),adapter.ReadParts(),Identity(),new ScopeSpec{Kind="PHASE",Values=new List<string>{"1"}});plan.Items[0].After.Phase="2";plan.PlanHash=PlanService.ComputeHash(plan);var run=Execute(plan,adapter,a);t.True(run.Events.Contains("PLAN_ITEM_OUTSIDE_SCOPE"));t.Equal(0,adapter.UpsertCalls);
            });
            t.Check("Engine rehashed malicious plan cannot create native identity", () => {
                var a=AuthorityService.CreateFixtureAuthority();var adapter=new FixtureAdapter(Identity());var plan=new PlanService(a).Create(Source(a,"r1",Part(a,"A")),adapter.ReadParts(),Identity(),new ScopeSpec());plan.Items[0].After.NativeId="existing-manual-id";plan.PlanHash=PlanService.ComputeHash(plan);var run=Execute(plan,adapter,a);t.True(run.Events.Contains("CREATE_NATIVE_ID_FORBIDDEN"));t.Equal(0,adapter.UpsertCalls);
            });
            t.Check("Engine rehashed malicious plan cannot borrow source revision", () => {
                var a=AuthorityService.CreateFixtureAuthority();var adapter=new FixtureAdapter(Identity());var plan=new PlanService(a).Create(Source(a,"r1",Part(a,"A")),adapter.ReadParts(),Identity(),new ScopeSpec());plan.Items[0].After.SourceRevision="r2";plan.PlanHash=PlanService.ComputeHash(plan);var run=Execute(plan,adapter,a);t.True(run.Events.Contains("PLAN_AFTER_SOURCE_IDENTITY_CONFLICT"));t.Equal(0,adapter.UpsertCalls);
            });
            t.Check("Engine rehashed REMOVE requires frozen explicit instruction", () => {
                var a=AuthorityService.CreateFixtureAuthority();var p=Part(a,"A");p.Managed=true;p.NativeId="N1";var source=Source(a,"r2");source.PreviousSourceRevision="r1";source.ExplicitRemovals.Add(p.Key);var adapter=new FixtureAdapter(Identity(),new[]{p});var plan=new PlanService(a).Create(source,adapter.ReadParts(),Identity(),new ScopeSpec());plan.ExplicitRemovals.Clear();plan.PlanHash=PlanService.ComputeHash(plan);var run=Execute(plan,adapter,a);t.True(run.Events.Contains("REMOVE_NOT_EXPLICIT"));t.Equal(0,adapter.RemoveCalls);
            });
            t.Check("Engine uploaded persistence proof cannot release", () => {
                var a=AuthorityService.CreateFixtureAuthority();var p=Part(a,"A");var plan=new PlanService(a).Create(Source(a,"r1",p),new List<CanonicalPart>(),Identity(),new ScopeSpec());var observed=JsonUtil.Clone(plan.Items[0].After);observed.NativeId="N1";var audit=new ReadbackService().Compare(plan,new AdapterSnapshot{Identity=Identity(),Parts=new List<CanonicalPart>{observed},IsFixture=false,PersistenceProof="NATIVE_MODELHANDLER_SAVE_CLOSE_OPEN_READBACK"});t.True(!audit.PersistenceProven);t.Equal("FAILED",audit.Status);t.True(audit.Issues.Any(x=>x.Code=="PERSISTENCE_LIFECYCLE_NOT_VERIFIED"));
            });
            t.Check("Engine journal permanently records matrix source scope identities", () => {
                var a=AuthorityService.CreateFixtureAuthority();var adapter=new FixtureAdapter(Identity());var plan=new PlanService(a).Create(Source(a,"r1",Part(a,"A")),adapter.ReadParts(),Identity(),new ScopeSpec());var journal=Journal();new ExecutionService(adapter,new AuthorizationService(authority:a),journal).Execute(plan,Context(plan));var begin=journal.ReadAll().First(x=>x.Kind=="BEGIN");t.Equal(AuthorizationMatrix.CurrentVersion,begin.MatrixVersion);t.Equal("r1",begin.SourceRevision);t.Equal(JsonUtil.Hash(plan.Scope),begin.ScopeHash);t.Equal(plan.Model.Key,begin.ModelKey);
            });
            t.Check("Engine revision diagnostics preserve physical roles and conflicts", () => {
                var a=AuthorityService.CreateFixtureAuthority();var p=Part(a,"A");var before=Source(a,"r1",p);var after=Source(a,"r2",JsonUtil.Clone(p),Part(a,"B"));after.Parts[0].SourceRevision="r2";after.Parts[1].SourceRevision="r2";var delta=RevisionService.Compare(before,after);t.Equal("UNCHANGED",delta.Items.Single(x=>x.Key==p.Key).Status);t.Equal("ADDED",delta.Items.Single(x=>x.Key!=p.Key).Status);after.Parts.Add(JsonUtil.Clone(after.Parts[0]));t.True(RevisionService.Compare(before,after).HasConflicts);
            });
        }
        private static ModelIdentity Identity() => new ModelIdentity{ModelId="fixture-model",ModelPath="/fixture/model",ModelName="Fixture",TeklaVersion="TEST_FIXTURE",Revision="model-r1"};
        private static CanonicalPart Part(AuthorityService authority,string id,string role="PRIMARY") => new CanonicalPart{CanonicalId=id,PhysicalRole=role,SourceId="source",SourceRevision="r1",Kind="BEAM",Profile="HEA200",MaterialRaw="S275JR",Material="S275JR",MaterialAuthority=authority.FixtureEvidence("fixture.material"),ProfileAuthority=authority.FixtureEvidence("fixture.profile"),GeometryAuthority=authority.FixtureEvidence("fixture.geometry"),GeometryHash=JsonUtil.HashText("geometry:"+id+":"+role),ManufacturingHash=JsonUtil.HashText("holes:2:"+id+":"+role),Points=new List<Vec3>{new Vec3(0,0,0),new Vec3(1000,0,0)},Phase="1",Mark=id};
        private static SteelModel Source(AuthorityService authority,string revision,params CanonicalPart[] parts) => new SteelModel{SourceId="source",SourceRevision=revision,SourceSha256=JsonUtil.HashText("source:"+revision),Parts=parts.ToList()};
        private static RequestContext Context(BuildPlan plan) => new RequestContext{RequestId=Guid.NewGuid().ToString("N"),RunId=Guid.NewGuid().ToString("N"),OperationId=Guid.NewGuid().ToString("N"),Actor="CWS_ENGINE",Mode="AUTO",Scope=JsonUtil.Clone(plan.Scope),ExpectedModel=JsonUtil.Clone(plan.Model),SourceRevision=plan.SourceRevision,PlanHash=plan.PlanHash};
        private static JournalStore Journal() => new JournalStore(Path.Combine(Path.GetTempPath(),"cws-engine-"+Guid.NewGuid().ToString("N")));
        private static ExecutionService Service(FixtureAdapter adapter,AuthorityService authority) => new ExecutionService(adapter,new AuthorizationService(authority:authority),Journal());
        private static RunResult Execute(BuildPlan plan,FixtureAdapter adapter,AuthorityService authority) => Service(adapter,authority).Execute(plan,Context(plan));
    }
}
