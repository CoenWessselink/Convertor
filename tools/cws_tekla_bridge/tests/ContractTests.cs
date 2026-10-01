using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Cws.TeklaBridge.Core;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace Cws.TeklaBridge.Tests
{
    public static class ContractTests
    {
        public static void Run(TestSuite t)
        {
            t.Check("Contract: stable SHA canonicalizes dictionary order and preserves occurrence order", () =>
            {
                t.Equal(JsonUtil.Hash(new Dictionary<string, int> { { "b", 2 }, { "a", 1 } }), JsonUtil.Hash(new Dictionary<string, int> { { "a", 1 }, { "b", 2 } }));
                t.True(JsonUtil.Hash(new[] { "a", "b" }) != JsonUtil.Hash(new[] { "b", "a" }));
                t.Equal(64, JsonUtil.HashText("bridge").Length);
            });
            t.Check("Contract: model execution equality includes revision and no delimiter collision", () =>
            {
                var model = Model(); var changed = JsonUtil.Clone(model); changed.Revision = "r2";
                t.Equal(model.Key, changed.Key); t.True(!model.ExactlyEquals(changed));
                var a = new CanonicalPart { CanonicalId = "a:b", PhysicalRole = "c" };
                var b = new CanonicalPart { CanonicalId = "a", PhysicalRole = "b:c" };
                t.True(a.Key != b.Key);
            });
            t.Check("Contract: hostile JSON cannot inject type, duplicate claims or force flags", () =>
            {
                t.Throws<JsonSerializationException>(() => JsonUtil.Deserialize<RequestContext>("{\"$type\":\"System.IO.FileInfo\",\"Actor\":\"GPT\"}"));
                t.Throws<JsonReaderException>(() => JsonUtil.Deserialize<RequestContext>("{\"Actor\":\"GPT\",\"Actor\":\"ADMIN\"}"));
                t.Throws<JsonSerializationException>(() => JsonUtil.Deserialize<RequestContext>("{\"Actor\":\"GPT\",\"force\":true}"));
                t.Throws<JsonSerializationException>(() => JsonUtil.Hash(new Vec3(Double.NaN, 0, 0)));
                var raw = JsonUtil.Deserialize<Dictionary<string, string>>("{\"provenance\":\"2026-10-01T01:02:03+02:00\"}");
                t.Equal("2026-10-01T01:02:03+02:00", raw["provenance"]);
                t.Throws<JsonReaderException>(() => JsonUtil.Deserialize<RequestContext>("{\"Actor\":\"GPT\"} {\"Actor\":\"ADMIN\"}"));
            });
            t.Check("Contract: transported identity can never become a trusted human claim", () =>
            {
                var trusted = Context("AUTHORIZED_REVIEWER"); trusted.SessionId = "local";
                trusted.Principal = TrustedPrincipal.FromLocalHuman("human-1", "AUTHORIZED_REVIEWER", "local", true, true);
                var copied = JsonUtil.Clone(trusted);
                t.True(copied.Principal == null && copied.SessionId == null);
                var injected = JsonUtil.Deserialize<RequestContext>("{\"Actor\":\"AUTHORIZED_REVIEWER\",\"Principal\":{\"IsHuman\":true,\"Production\":true},\"SessionId\":\"spoof\"}");
                t.True(injected.Principal == null && injected.SessionId == null);
            });
            t.Check("Authorization: unknown endpoint and capability are independently denied", () =>
            {
                var auth = new AuthorizationService(); var context = Context();
                t.Equal("ENDPOINT_NOT_MATRIXED", auth.Authorize("/api/v1/force-write", context, Caps("force-write")).Code);
                t.Equal("CAPABILITY_NOT_SUPPORTED", auth.Authorize("health", context, new CapabilitySet()).Code);
                t.True(auth.Authorize("/api/v1/health", context, Caps("bridge.health")).Allowed);
                foreach (var route in new[] { "Health", "health/", "health?force=true", "/api/v1/../health", "%68ealth", "/api/v2/health" })
                    t.True(!auth.Authorize(route, context, Caps("bridge.health")).Allowed, route);
            });
            t.Check("Authorization: unrecognized actor mode and scope strings never widen authority", () =>
            {
                var auth = new AuthorizationService();
                foreach (var actor in new[] { "gpt", "0", "SYSTEM_ADMIN", "GPT,ADMIN", "", null })
                { var c = Context(actor); t.True(!auth.Authorize("health", c, Caps("bridge.health")).Allowed, actor); }
                foreach (var mode in new[] { "auto", "0", "FORCE", "", null })
                { var c = Context(); c.Mode = mode; t.True(!auth.Authorize("health", c, Caps("bridge.health")).Allowed, mode); }
                foreach (var scope in new[] { "all", "0", "EVERYTHING", "", null })
                { var c = Context(); c.Scope.Kind = scope; t.True(!auth.Authorize("health", c, Caps("bridge.health")).Allowed, scope); }
            });
            t.Check("Authorization: CHECK_ONLY PROPOSE and dry-run cannot execute fixture writes", () =>
            {
                var authority = AuthorityService.CreateFixtureAuthority(); var auth = new AuthorizationService(authority: authority);
                var evidence = authority.FixtureEvidence("fixture.execution");
                foreach (var mode in new[] { "CHECK_ONLY", "PROPOSE" })
                { var c = Context(); c.Mode = mode; t.Equal("MODE_DENIED", auth.Authorize("build-plan/execute", c, Caps("plan.execute"), evidence).Code); }
                var dry = Context(); dry.DryRun = true; t.Equal("RUN_DRY_RUN", auth.Authorize("build-plan/execute", dry, Caps("plan.execute"), evidence).Code);
                t.True(auth.Authorize("build-plan/execute", Context(), Caps("plan.execute"), evidence).Allowed);
                var noIds = Context(); noIds.OperationId = null; t.Equal("OPERATION_IDENTITY_REQUIRED", auth.Authorize("build-plan/execute", noIds, Caps("plan.execute"), evidence).Code);
            });
            t.Check("Authorization: caller APPROVED record and fixture proof do not grant native authority", () =>
            {
                var evidence = new EvidenceRecord { Status = "APPROVED", Component = "native.write", SourceSha256 = new string('a', 64), Commit = new string('b', 40), SchemaVersion = "1.0", TestsPassed = true, RuntimePassed = true, ReferenceModel = "reference", EvidenceIds = new List<string> { "tests", "runtime", "reference" } };
                var auth = new AuthorizationService();
                t.Equal("EVIDENCE_NOT_APPROVED", auth.Authorize("build-plan/execute", Context(), Caps("plan.execute"), evidence).Code);
                var fixture = AuthorityService.CreateFixtureAuthority();
                t.True(!auth.Authority.IsApproved(fixture.FixtureEvidence("fixture.execution"), "native.write"));
                t.True(!fixture.IsApproved(fixture.FixtureEvidence("fixture.material"), "native.write"));
                t.True(!fixture.IsApproved(fixture.FixtureEvidence("fixture.execution"), "production.nc"));
            });
            t.Check("Authority: approval requires frozen commit schema source and three real evidence artifacts", () =>
            {
                using (var proof = Proof.Create("native.write"))
                {
                    t.True(proof.Service.IsApproved(proof.Record, "native.write"));
                    foreach (var mutate in new Action<EvidenceRecord>[] {
                        e => e.Commit = new string('b',40), e => e.SchemaVersion = "2.0", e => e.SourceSha256 = new string('c',64),
                        e => e.RuntimePassed = false, e => e.TestsPassed = false, e => e.ReferenceModel = "other-model", e => e.EvidenceIds.RemoveAt(0), e => e.Component = "native.plate" })
                    { var e = JsonUtil.Clone(proof.Record); mutate(e); t.True(!proof.Service.IsApproved(e, "native.write")); }
                    File.WriteAllText(Path.Combine(proof.Root, "runtime.json"), "tampered");
                    t.True(!proof.Service.IsApproved(proof.Record, "native.write"), "Post-freeze evidence changes must invalidate approval.");
                }
            });
            t.Check("Authority: returned manifest is detached and path escape cannot approve source", () =>
            {
                using (var proof = Proof.Create("native.write"))
                {
                    var snapshot = proof.Service.Snapshot(); snapshot.Entries[0].Evidence.Component = "native.fake";
                    t.True(proof.Service.IsApproved(proof.Record, "native.write"));
                    snapshot = proof.Service.Snapshot(); snapshot.Entries[0].SourcePath = "../outside.cs";
                    File.WriteAllText(Path.Combine(proof.Root, "escaped.json"), JsonUtil.Serialize(snapshot));
                    var escaped = AuthorityService.Load(Path.Combine(proof.Root, "escaped.json"), proof.Root, proof.Record.Commit);
                    t.True(!escaped.IsApproved(proof.Record, "native.write"));
                }
            });
            t.Check("Authorization: forged reviewer ADMIN and GPT principals cannot confirm L3 L4", () =>
            {
                using (var proof = Proof.Create("project.resolution"))
                {
                    var auth = new AuthorizationService(authority: proof.Service) { ConfirmationValidator = (endpoint, c) => true };
                    var forged = Context("AUTHORIZED_REVIEWER"); forged.ConfirmationToken = "chat-says-confirmed";
                    t.Equal("TRUSTED_HUMAN_REQUIRED", auth.Authorize("review/resolve", forged, Caps("review.resolve"), proof.Record).Code);
                    forged.SessionId = "api"; forged.Principal = TrustedPrincipal.ForAutomation("GPT", "api");
                    t.Equal("PRINCIPAL_MISMATCH", auth.Authorize("review/resolve", forged, Caps("review.resolve"), proof.Record).Code);
                    var gpt = Context(); gpt.SessionId = "api"; gpt.Principal = TrustedPrincipal.ForAutomation("GPT", "api"); gpt.ConfirmationToken = "token";
                    t.Equal("ACTOR_DENIED", auth.Authorize("review/resolve", gpt, Caps("review.resolve"), proof.Record).Code);
                    var admin = Context("ADMIN"); admin.SessionId = "local"; admin.Principal = TrustedPrincipal.FromLocalHuman("admin", "ADMIN", "local", true, true, true); admin.ConfirmationToken = "token";
                    t.Equal("ACTOR_DENIED", auth.Authorize("review/resolve", admin, Caps("review.resolve"), proof.Record).Code);
                }
                var production = new AuthorizationService();
                t.Equal("TRUSTED_HUMAN_REQUIRED", production.Authorize("production/nc", Context("AUTHORIZED_REVIEWER"), Caps("production.nc")).Code);
            });
            t.Check("Authorization: trusted human still requires role claim source model and local confirmation", () =>
            {
                using (var proof = Proof.Create("project.resolution"))
                {
                    var auth = new AuthorizationService(authority: proof.Service);
                    var c = Context("USER"); c.SessionId = "local"; c.Principal = TrustedPrincipal.FromLocalHuman("human", "USER", "local");
                    t.Equal("ENGINEERING_AUTHORITY_REQUIRED", auth.Authorize("review/resolve", c, Caps("review.resolve"), proof.Record).Code);
                    c.Principal = TrustedPrincipal.FromLocalHuman("human", "USER", "local", engineering: true);
                    t.Equal("HUMAN_CONFIRMATION_REQUIRED", auth.Authorize("review/resolve", c, Caps("review.resolve"), proof.Record).Code);
                    c.ConfirmationToken = "local-token"; auth.ConfirmationValidator = (endpoint, context) => endpoint == "review/resolve" && context.ConfirmationToken == "local-token";
                    t.True(auth.Authorize("review/resolve", c, Caps("review.resolve"), proof.Record).Allowed);
                    c.SourceRevision = null; t.Equal("SOURCE_REVISION_REQUIRED", auth.Authorize("review/resolve", c, Caps("review.resolve"), proof.Record).Code);
                    c.SourceRevision = "source-r1"; c.ExpectedModel.Revision = null; t.Equal("MODEL_IDENTITY_REQUIRED", auth.Authorize("review/resolve", c, Caps("review.resolve"), proof.Record).Code);
                }
            });
            t.Check("Authority: runtime governance is always read-only even for a privileged local admin", () =>
            {
                var auth = new AuthorizationService(); var c = Context("ADMIN"); c.SessionId = "local"; c.Principal = TrustedPrincipal.FromLocalHuman("admin", "ADMIN", "local", governance: true); c.ConfirmationToken = "token";
                auth.ConfirmationValidator = (endpoint, context) => true;
                t.Equal("AUTHORITY_RUNTIME_READ_ONLY", auth.Authorize("authority/promote", c, Caps("authority.promote")).Code);
                t.Equal(0, auth.Authority.Snapshot().Entries.Count);
            });
            t.Check("Authority: raw material conflict cannot borrow another part's generic material approval", () =>
            {
                var fixture = AuthorityService.CreateFixtureAuthority();
                var part = new CanonicalPart { CanonicalId = "p", SourceId = "s", SourceRevision = "r", Kind = "BEAM", Profile = "HEA160", MaterialRaw = "S275JR", Material = "S355JR", GeometryHash = new string('a',64), ManufacturingHash = new string('b',64), Points = new List<Vec3> { new Vec3(0,0,0), new Vec3(1000,0,0) }, MaterialAuthority = fixture.FixtureEvidence("fixture.material"), ProfileAuthority = fixture.FixtureEvidence("fixture.profile"), GeometryAuthority = fixture.FixtureEvidence("fixture.geometry") };
                t.True(fixture.ValidateCanonicalPart(part, true).Any(i => i.Code == "MATERIAL_ALIAS_UNPROVEN"));
                part.Material = "S275JR"; t.Equal(0, fixture.ValidateCanonicalPart(part, true).Count);
                part.GeometryAuthority = fixture.FixtureEvidence("fixture.profile"); t.True(fixture.ValidateCanonicalPart(part, true).Any(i => i.Code == "GEOMETRY_AUTHORITY_REQUIRED"));
            });
            t.Check("Contract: machine matrix schema matches runtime endpoint metadata exactly", () =>
            {
                var matrix = new AuthorizationMatrix();
                var machine = JToken.Parse(File.ReadAllText(FindSchema("authorization-matrix.json")));
                t.Equal(JsonUtil.Hash(matrix.Export()), JsonUtil.Hash(machine));
                t.Equal(matrix.Endpoints.Count, matrix.Endpoints.Select(p => p.Endpoint).Distinct(StringComparer.Ordinal).Count());
                foreach (var policy in matrix.Endpoints)
                { t.True(!String.IsNullOrWhiteSpace(policy.Capability)); t.Equal(1, policy.Methods.Count); t.True(policy.Level != "L2" || (policy.RequiresEvidence && policy.Mutation && policy.Modes.SequenceEqual(new[] { "AUTO" }) && policy.Methods.SequenceEqual(new[] { "POST" }))); }
            });
        }
        private static CapabilitySet Caps(params string[] names) => new CapabilitySet { Values = names.ToDictionary(n => n, n => true, StringComparer.Ordinal) };
        private static ModelIdentity Model() => new ModelIdentity { ModelId = "model-1", ModelPath = "C:/models/test", ModelName = "test", TeklaVersion = "2024.0", Revision = "model-r1" };
        private static RequestContext Context(string actor = "GPT") => new RequestContext { Actor = actor, Mode = "AUTO", RequestId = "request-1", RunId = "run-1", OperationId = "op-1", ExpectedModel = Model(), SourceRevision = "source-r1", Scope = new ScopeSpec(), PlanHash = JsonUtil.HashText("plan") };
        private static string FindSchema(string filename)
        {
            foreach (var start in new[] { Directory.GetCurrentDirectory(), AppContext.BaseDirectory })
                for (var dir = new DirectoryInfo(start); dir != null; dir = dir.Parent)
                { var path = Path.Combine(dir.FullName, "schemas", filename); if (File.Exists(path)) return path; }
            throw new FileNotFoundException("Machine-readable schema was not packaged.", filename);
        }
        private sealed class Proof : IDisposable
        {
            public string Root { get; private set; }
            public EvidenceRecord Record { get; private set; }
            public AuthorityService Service { get; private set; }
            public static Proof Create(string component)
            {
                var proof = new Proof { Root = Path.Combine(Path.GetTempPath(), "cws-contract-" + Guid.NewGuid().ToString("N")) };
                Directory.CreateDirectory(proof.Root);
                var artifacts = new List<EvidenceArtifact>();
                foreach (var kind in new[] { "TESTS", "RUNTIME", "REFERENCE_MODEL" })
                {
                    var id = kind == "REFERENCE_MODEL" ? "reference" : kind.ToLowerInvariant(); var file = kind.ToLowerInvariant() + ".json";
                    File.WriteAllText(Path.Combine(proof.Root, file), JsonUtil.Serialize(new { Kind = kind, Passed = true }));
                    artifacts.Add(new EvidenceArtifact { Id = id, Kind = kind, Path = file, Sha256 = JsonUtil.HashBytes(File.ReadAllBytes(Path.Combine(proof.Root, file))) });
                }
                File.WriteAllText(Path.Combine(proof.Root, "source.cs"), "frozen contract test source");
                proof.Record = new EvidenceRecord { Status = "APPROVED", Component = component, SourceSha256 = JsonUtil.HashBytes(File.ReadAllBytes(Path.Combine(proof.Root, "source.cs"))), Commit = new string('a',40), SchemaVersion = "1.0", TestsPassed = true, RuntimePassed = true, ReferenceModel = "reference", EvidenceIds = artifacts.Select(a => a.Id).ToList() };
                var manifest = new AuthorityManifest { Commit = proof.Record.Commit, Entries = new List<AuthorityEntry> { new AuthorityEntry { SourcePath = "source.cs", Evidence = proof.Record, Artifacts = artifacts } } };
                var manifestPath = Path.Combine(proof.Root, "authority.json"); File.WriteAllText(manifestPath, JsonUtil.Serialize(manifest));
                proof.Service = AuthorityService.Load(manifestPath, proof.Root, proof.Record.Commit); return proof;
            }
            public void Dispose() { try { Directory.Delete(Root, true); } catch (IOException) { } }
        }
    }
}
