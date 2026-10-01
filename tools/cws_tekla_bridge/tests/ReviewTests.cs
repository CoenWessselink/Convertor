using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Cws.TeklaBridge.Core;

namespace Cws.TeklaBridge.Tests
{
    public static class ReviewTests
    {
        public static void Run(TestSuite t)
        {
            t.Check("review.local-only human challenge rejects GPT role", () => WithReview((s, m, scope) =>
                t.Throws<UnauthorizedAccessException>(() => s.CreateTrustedLocalUi("GPT"))));
            t.Check("review.challenge is single-use and survives store reload", () => WithReview((s, m, scope) =>
            {
                var p = s.Propose(Proposal(m, scope)); var ui = s.CreateTrustedLocalUi("USER");
                var c = ui.CreateChallenge(p.ProposalId, m, scope, "r1");
                var r = ui.Confirm(p.ProposalId, c.Token, m, scope, "r1", "Checked source certificate", new[] { "certificate:part-a" });
                t.Equal("PROJECT_CONFIRMED", r.Status);
                t.Throws<UnauthorizedAccessException>(() => ui.Confirm(p.ProposalId, c.Token, m, scope, "r1", "again", new[] { "proof" }));
                t.Equal(1, s.History().Resolutions.Count);
                t.Equal("USER", s.History().Resolutions[0].Actor);
            }));
            t.Check("review.expired challenge cannot resolve", () =>
            {
                string dir = Temp(); DateTime now = new DateTime(2026, 10, 1, 20, 0, 0, DateTimeKind.Utc);
                try
                {
                    var s = new ReviewService(new ReviewStore(dir), () => now); var m = Model(); var scope = new ScopeSpec();
                    var p = s.Propose(Proposal(m, scope)); var ui = s.CreateTrustedLocalUi("USER"); var c = ui.CreateChallenge(p.ProposalId, m, scope, "r1");
                    now = now.AddMinutes(3);
                    t.Throws<UnauthorizedAccessException>(() => ui.Confirm(p.ProposalId, c.Token, m, scope, "r1", "expired", new[] { "proof" }));
                    t.Equal(0, s.History().Resolutions.Count);
                }
                finally { Directory.Delete(dir, true); }
            });
            t.Check("review.challenge rejects changed scope model and source", () => WithReview((s, m, scope) =>
            {
                var p = s.Propose(Proposal(m, scope)); var ui = s.CreateTrustedLocalUi("USER"); var c = ui.CreateChallenge(p.ProposalId, m, scope, "r1");
                var other = JsonUtil.Clone(m); other.Revision = "model-r2";
                t.Throws<UnauthorizedAccessException>(() => ui.Confirm(p.ProposalId, c.Token, other, scope, "r1", "stale model", new[] { "proof" }));
                t.Throws<UnauthorizedAccessException>(() => ui.Confirm(p.ProposalId, c.Token, m, new ScopeSpec { Kind = "MARKS", Values = new List<string> { "B" } }, "r1", "scope", new[] { "proof" }));
                t.Throws<UnauthorizedAccessException>(() => ui.Confirm(p.ProposalId, c.Token, m, scope, "r2", "source", new[] { "proof" }));
            }));
            t.Check("review.source change supersedes proposal resolution and challenge", () => WithReview((s, m, scope) =>
            {
                var p = s.Propose(Proposal(m, scope)); var ui = s.CreateTrustedLocalUi("USER"); var c = ui.CreateChallenge(p.ProposalId, m, scope, "r1");
                t.Equal(1, s.SupersedeSource(m, "source", "r2"));
                t.Equal("SUPERSEDED", s.History().Proposals[0].Status);
                t.Throws<UnauthorizedAccessException>(() => ui.Confirm(p.ProposalId, c.Token, m, scope, "r1", "stale", new[] { "proof" }));
            }));
            t.Check("review.project resolution cannot cross part or promote authority", () => WithReview((s, m, scope) =>
            {
                var p = s.Propose(Proposal(m, scope)); var ui = s.CreateTrustedLocalUi("USER"); var c = ui.CreateChallenge(p.ProposalId, m, scope, "r1");
                var r = ui.Confirm(p.ProposalId, c.Token, m, scope, "r1", "certificate", new[] { "proof-a" });
                var a = Part("A"); var b = Part("B");
                var updated = s.ApplyProjectResolution(r.ResolutionId, a, m, scope, "r1");
                t.Equal("S355JR", updated.Material); t.Equal("S235JR", a.Material); t.True(updated.MaterialAuthority == null);
                t.Throws<UnauthorizedAccessException>(() => s.ApplyProjectResolution(r.ResolutionId, b, m, scope, "r1"));
                s.SupersedeSource(m, "source", "r2");
                t.Throws<UnauthorizedAccessException>(() => s.ApplyProjectResolution(r.ResolutionId, a, m, scope, "r1"));
            }));
            t.Check("review.operation confirmation rejects actor spoof and JSON principal", () => WithReview((s, m, scope) =>
            {
                var c = Context(m, scope); var ui = s.CreateTrustedLocalUi("USER");
                var wire = JsonUtil.Deserialize<RequestContext>(JsonUtil.Serialize(c));
                t.True(wire.Principal == null && wire.SessionId == null);
                t.Throws<UnauthorizedAccessException>(() => ui.CreateOperationChallenge("review/resolve", wire));
                t.True(!s.ConsumeOperationConfirmation("review/resolve", wire));
            }));
            t.Check("review.operation challenge binds operation session and consumes once", () =>
            {
                string dir = Temp();
                try
                {
                    var service = new ReviewService(new ReviewStore(dir)); var c = Context(Model(), new ScopeSpec());
                    var token = service.CreateTrustedLocalUi("USER").CreateOperationChallenge("review/resolve", c);
                    c.ConfirmationToken = token.Token;
                    c.PlanHash = JsonUtil.HashText("other-operation"); t.True(!service.ConsumeOperationConfirmation("review/resolve", c));
                    c.PlanHash = JsonUtil.HashText("operation"); t.True(!service.ConsumeOperationConfirmation("connection/apply", c));
                    var restarted = new ReviewService(new ReviewStore(dir));
                    t.True(restarted.ConsumeOperationConfirmation("/api/v1/review/resolve", c));
                    t.True(!service.ConsumeOperationConfirmation("review/resolve", c));
                }
                finally { Directory.Delete(dir, true); }
            });
            t.Check("review.operation challenge invalidated by source supersede", () => WithReview((s, m, scope) =>
            {
                var ctx = Context(m, scope); var challenge = s.CreateTrustedLocalUi("USER").CreateOperationChallenge("review/resolve", ctx);
                ctx.ConfirmationToken = challenge.Token; s.SupersedeSource(m, "source", "r2");
                t.True(!s.ConsumeOperationConfirmation("review/resolve", ctx));
            }));
            t.Check("connections.manual and unknown-origin existing connections remain KEEP", () =>
            {
                var svc = new ConnectionService();
                t.Equal("KEEP", svc.Evaluate(null, null, "AUTO", new ExistingConnection { NativeId = "manual", Managed = false, Origin = "MANUAL" }).Status);
                t.Equal("KEEP", svc.Evaluate(null, null, "AUTO", new ExistingConnection { NativeId = "unknown", Managed = true, Origin = "UNKNOWN" }).Status);
            });
            t.Check("connections.fingerprint changes with geometry material detail attributes orientation", () =>
            {
                var svc = new ConnectionService(); var j = Joint(); string fingerprint = svc.Fingerprint(j);
                var changed = JsonUtil.Clone(j); changed.Secondary[0].Points[0].X += 1; t.True(fingerprint != svc.Fingerprint(changed));
                changed = JsonUtil.Clone(j); changed.Main.Material = "S355JR"; t.True(fingerprint != svc.Fingerprint(changed));
                changed = JsonUtil.Clone(j); changed.Geometry.Orientation = "reversed"; t.True(fingerprint != svc.Fingerprint(changed));
                changed = JsonUtil.Clone(j); changed.DetailSha256 = JsonUtil.HashText("changed detail"); t.True(fingerprint != svc.Fingerprint(changed));
                changed = JsonUtil.Clone(j); changed.AttributesSha256 = JsonUtil.HashText("changed attrs"); t.True(fingerprint != svc.Fingerprint(changed));
            });
            t.Check("connections.secondary order is deterministic but main role differs", () =>
            {
                var svc = new ConnectionService(); var j = Joint(); j.Secondary.Add(Part("C"));
                var changed = JsonUtil.Clone(j); changed.Secondary.Reverse(); t.Equal(svc.Fingerprint(j), svc.Fingerprint(changed));
                var main = changed.Main; changed.Main = changed.Secondary[0]; changed.Secondary[0] = main;
                t.True(svc.Fingerprint(j) != svc.Fingerprint(changed));
            });
            t.Check("connections.unknown material geometry and revision are BLOCKED", () =>
            {
                var svc = new ConnectionService(); var j = Joint(); j.Main.Material = null; t.Equal("BLOCKED", svc.Evaluate(j, null, "AUTO").Status);
                j = Joint(); j.Geometry = null; t.Equal("BLOCKED", svc.Evaluate(j, null, "AUTO").Status);
                j = Joint(); j.Secondary[0].SourceRevision = "r0"; t.Equal("BLOCKED", svc.Evaluate(j, null, "AUTO").Status);
            });
            t.Check("connections.unproven family and forged APPROVED metadata cannot AUTO", () =>
            {
                var svc = new ConnectionService(); var j = Joint(); t.Equal("PROPOSE", svc.Evaluate(j, null, "AUTO").Status);
                var attrs = new Dictionary<string, string> { ["bolt_diameter"] = "20" };
                j.AttributesSemanticHash = JsonUtil.Hash(attrs);
                var family = new ConnectionFamily { FamilyId = "F1", ComponentId = "144", ComponentSourceSha256 = JsonUtil.HashText("component"),
                    Attributes = attrs, AttributesSemanticHash = j.AttributesSemanticHash, AttributesSha256 = j.AttributesSha256,
                    DetailId = j.DetailId, DetailSha256 = j.DetailSha256, ApprovedFingerprints = new List<string> { svc.Fingerprint(j) },
                    Authority = CompleteEvidence("connection.family", JsonUtil.HashText("component")) };
                t.Equal("BLOCKED", svc.Evaluate(j, new[] { family }, "AUTO").Status);
                family.Authority.RuntimePassed = false; t.Equal("BLOCKED", svc.Evaluate(j, new[] { family }, "AUTO").Status);
            });
            t.Check("connections.AUTO requires immutable runtime and clash proofs even for exact approved family", () =>
            {
                string dir = Temp();
                try
                {
                    var j = Joint(); var attrs = new Dictionary<string, string> { ["bolt_diameter"] = "20" }; j.AttributesSemanticHash = JsonUtil.Hash(attrs);
                    File.WriteAllText(Path.Combine(dir, "component.txt"), "synthetic authority unit-test component");
                    File.WriteAllText(Path.Combine(dir, "tests.txt"), "unit-test authority artifact; not real runtime proof");
                    File.WriteAllText(Path.Combine(dir, "runtime.txt"), "synthetic gate validation record");
                    File.WriteAllText(Path.Combine(dir, "reference.json"), "synthetic reference for gate unit tests only");
                    string sha = JsonUtil.HashBytes(File.ReadAllBytes(Path.Combine(dir, "component.txt")));
                    var manifest = new AuthorityManifest { Commit = new string('a', 40) };
                    foreach (var component in new[] { "connection.family", "source.profile", "source.material", "source.geometry", "connection.validation", "connection.clash" })
                    {
                        var record = CompleteEvidence(component, sha);
                        manifest.Entries.Add(new AuthorityEntry { SourcePath = "component.txt", Evidence = record, Artifacts = new List<EvidenceArtifact> {
                            new EvidenceArtifact { Id = "tests", Kind = "TESTS", Path = "tests.txt", Sha256 = JsonUtil.HashBytes(File.ReadAllBytes(Path.Combine(dir, "tests.txt"))) },
                            new EvidenceArtifact { Id = "runtime", Kind = "RUNTIME", Path = "runtime.txt", Sha256 = JsonUtil.HashBytes(File.ReadAllBytes(Path.Combine(dir, "runtime.txt"))) },
                            new EvidenceArtifact { Id = "reference", Kind = "REFERENCE_MODEL", Path = "reference.json", Sha256 = JsonUtil.HashBytes(File.ReadAllBytes(Path.Combine(dir, "reference.json"))) } } });
                    }
                    string path = Path.Combine(dir, "manifest.json"); File.WriteAllText(path, JsonUtil.Serialize(manifest));
                    var svc = new ConnectionService(AuthorityService.Load(path, dir, manifest.Commit));
                    foreach (var p in new[] { j.Main }.Concat(j.Secondary)) { p.ProfileAuthority = CompleteEvidence("source.profile", sha); p.MaterialAuthority = CompleteEvidence("source.material", sha); p.GeometryAuthority = CompleteEvidence("source.geometry", sha); }
                    var fingerprint = svc.Fingerprint(j);
                    var family = new ConnectionFamily { FamilyId = "F1", BindingArtifactId = "family-spec", ComponentId = "144", ComponentSourceSha256 = sha,
                        Attributes = attrs, AttributesSemanticHash = j.AttributesSemanticHash, AttributesSha256 = j.AttributesSha256,
                        DetailId = j.DetailId, DetailSha256 = j.DetailSha256, ApprovedFingerprints = new List<string> { fingerprint }, Authority = CompleteEvidence("connection.family", sha) };
                    var validation = new ConnectionValidationProof { JointFingerprint = fingerprint, BindingArtifactId = "validation-proof", FamilyId = "F1", ComponentSourceSha256 = sha,
                        AttributesSha256 = j.AttributesSha256, DetailSha256 = j.DetailSha256, ResultHash = JsonUtil.HashText("features"),
                        PlatesValidated = true, BoltsValidated = true, WeldsValidated = true, CutsValidated = true, DetailValidated = true,
                        RuntimeEvidence = CompleteEvidence("connection.validation", sha) };
                    var clash = new ConnectionClashProof { BindingArtifactId = "clash-proof", JointFingerprint = fingerprint, ResultHash = validation.ResultHash, NoClashes = true, ToleranceVersion = "test-only/1", RuntimeEvidence = CompleteEvidence("connection.clash", sha) };
                    BindProof(dir, manifest, family.Authority, "CONNECTION_FAMILY_SPEC", family.BindingArtifactId, ConnectionService.FamilyBindingJson(family));
                    BindProof(dir, manifest, validation.RuntimeEvidence, "CONNECTION_VALIDATION", validation.BindingArtifactId, ConnectionService.ValidationBindingJson(validation));
                    BindProof(dir, manifest, clash.RuntimeEvidence, "CONNECTION_CLASH", clash.BindingArtifactId, ConnectionService.ClashBindingJson(clash));
                    File.WriteAllText(path, JsonUtil.Serialize(manifest)); svc = new ConnectionService(AuthorityService.Load(path, dir, manifest.Commit));
                    t.Equal("BLOCKED", svc.Evaluate(j, new[] { family }, "AUTO", validation: validation).Status);
                    t.Equal("BLOCKED", svc.Evaluate(j, new[] { family }, "AUTO", clash: clash).Status);
                    t.Equal("AUTO_READY", svc.Evaluate(j, new[] { family }, "AUTO", validation: validation, clash: clash).Status);
                    t.True(!svc.Evaluate(j, new[] { family }, "AUTO", validation: validation, clash: clash).NativeApplyImplemented);
                    var forged = JsonUtil.Clone(family); forged.Authority = CompleteEvidence("source.profile", sha);
                    t.Equal("BLOCKED", svc.Evaluate(j, new[] { forged }, "AUTO", validation: validation, clash: clash).Status);
                    forged = JsonUtil.Clone(family); forged.Attributes["bolt_diameter"] = "16"; forged.AttributesSemanticHash = JsonUtil.Hash(forged.Attributes);
                    var changedJoint = JsonUtil.Clone(j); changedJoint.AttributesSemanticHash = forged.AttributesSemanticHash;
                    forged.ApprovedFingerprints = new List<string> { svc.Fingerprint(changedJoint) };
                    t.Equal("BLOCKED", svc.Evaluate(changedJoint, new[] { forged }, "AUTO", validation: validation, clash: clash).Status);
                    clash.NoClashes = false; t.Equal("BLOCKED", svc.Evaluate(j, new[] { family }, "AUTO", validation: validation, clash: clash).Status);
                    clash.NoClashes = true; validation.BoltsValidated = false; t.Equal("BLOCKED", svc.Evaluate(j, new[] { family }, "AUTO", validation: validation, clash: clash).Status);
                }
                finally { Directory.Delete(dir, true); }
            });
            t.Check("connections.attribute files parse only data and reject duplicate executable", () =>
            {
                var parsed = ConnectionAttributeReader.Parse("bolt_diameter 20\nplate_thickness 12\nscript $(never execute)\n");
                t.Equal("20", parsed.Values["bolt_diameter"]); t.Equal("$(never execute)", parsed.Values["script"]);
                t.Throws<InvalidDataException>(() => ConnectionAttributeReader.Parse("x 1\nx 2"));
                t.Throws<InvalidDataException>(() => ConnectionAttributeReader.ReadDataFile("macro.cs"));
            });
            t.Check("corpus.missing real source model stays NOT_RUN and target is not fabricated", () =>
            {
                string dir = Temp();
                try
                {
                    var manifest = new CorpusManifest { Cases = new List<CorpusCase> { new CorpusCase { CaseId = "koraal", ReferenceModel = "Het Koraal", HardGate = true } } };
                    string path = Path.Combine(dir, "manifest.json"); File.WriteAllText(path, JsonUtil.Serialize(manifest));
                    var report = new CorpusAnalyzer().Run(path); t.Equal("NOT_RUN", report.Status); t.Equal(1, report.SuppliedCaseCount); t.Equal(0, report.AnalyzedCaseCount); t.True(!report.CorpusComplete);
                }
                finally { Directory.Delete(dir, true); }
            });
            t.Check("corpus.actual frozen fixture snapshot analyzed without claiming runtime PASS", () =>
            {
                string dir = Temp();
                try
                {
                    var source = new SteelModel { SourceId = "source", SourceRevision = "r1", SourceSha256 = JsonUtil.HashText("source"), Parts = new List<CanonicalPart> { Part("A") } };
                    var snapshot = new AdapterSnapshot { Identity = Model(), IsFixture = true, PersistenceProof = "fixture only", Parts = JsonUtil.Clone(source.Parts) };
                    var c = FrozenCase(dir, source, snapshot);
                    string path = Path.Combine(dir, "manifest.json"); File.WriteAllText(path, JsonUtil.Serialize(new CorpusManifest { Cases = new List<CorpusCase> { c } }));
                    var result = new CorpusAnalyzer().Run(path); t.Equal("ANALYZED_NO_RUNTIME_PROOF", result.Cases[0].Status); t.Equal(1, result.AnalyzedCaseCount); t.Equal(0, result.RuntimePassedCaseCount); t.True(!result.CorpusComplete);
                    snapshot.Parts[0].Material = "S355JR"; File.WriteAllText(Path.Combine(dir, "snapshot.json"), JsonUtil.Serialize(snapshot));
                    c.SnapshotFileSha256 = JsonUtil.HashBytes(File.ReadAllBytes(Path.Combine(dir, "snapshot.json")));
                    File.WriteAllText(path, JsonUtil.Serialize(new CorpusManifest { Cases = new List<CorpusCase> { c } }));
                    t.Equal("FAILED", new CorpusAnalyzer().Run(path).Cases[0].Status);
                }
                finally { Directory.Delete(dir, true); }
            });
            t.Check("corpus.frozen SHA mismatch and escaped data path are FAILED", () =>
            {
                string dir = Temp();
                try
                {
                    var source = new SteelModel { SourceId = "source", SourceRevision = "r1", Parts = new List<CanonicalPart> { Part("A") } };
                    var snapshot = new AdapterSnapshot { Identity = Model(), Parts = source.Parts, IsFixture = true };
                    var c = FrozenCase(dir, source, snapshot); c.SourceFileSha256 = JsonUtil.HashText("wrong");
                    string path = Path.Combine(dir, "manifest.json"); File.WriteAllText(path, JsonUtil.Serialize(new CorpusManifest { Cases = new List<CorpusCase> { c } }));
                    t.Equal("FAILED", new CorpusAnalyzer().Run(path).Cases[0].Status);
                    c.SourcePath = "../escape.json"; File.WriteAllText(path, JsonUtil.Serialize(new CorpusManifest { Cases = new List<CorpusCase> { c } }));
                    t.Equal("FAILED", new CorpusAnalyzer().Run(path).Cases[0].Status);
                }
                finally { Directory.Delete(dir, true); }
            });
        }
        private static void BindProof(string dir, AuthorityManifest manifest, EvidenceRecord record, string kind, string id, string json)
        {
            string file = id + ".json"; File.WriteAllText(Path.Combine(dir, file), json);
            var entry = manifest.Entries.Single(e => e.Evidence.Component == record.Component);
            record.EvidenceIds.Add(id); entry.Evidence = JsonUtil.Clone(record);
            entry.Artifacts.Add(new EvidenceArtifact { Id = id, Kind = kind, Path = file, Sha256 = JsonUtil.HashText(json) });
        }
        private static CorpusCase FrozenCase(string dir, SteelModel source, AdapterSnapshot snapshot)
        {
            File.WriteAllText(Path.Combine(dir, "source.json"), JsonUtil.Serialize(source)); File.WriteAllText(Path.Combine(dir, "snapshot.json"), JsonUtil.Serialize(snapshot));
            return new CorpusCase { CaseId = "actual-fixture", ReferenceModel = "fixture", SourcePath = "source.json", SnapshotPath = "snapshot.json",
                SourceFileSha256 = JsonUtil.HashBytes(File.ReadAllBytes(Path.Combine(dir, "source.json"))), SnapshotFileSha256 = JsonUtil.HashBytes(File.ReadAllBytes(Path.Combine(dir, "snapshot.json"))) };
        }
        private static ReviewProposal Proposal(ModelIdentity model, ScopeSpec scope) => new ReviewProposal { Model = model, Scope = scope, SourceId = "source", SourceRevision = "r1",
            CanonicalId = "A", PhysicalRole = "PRIMARY", Field = "Material", OldValue = "S235JR", NewValue = "S355JR", Actor = "GPT", Reason = "Source conflict needs human review", EvidenceIds = new List<string> { "source:certificate" } };
        private static CanonicalPart Part(string id) => new CanonicalPart { CanonicalId = id, SourceId = "source", SourceRevision = "r1", Kind = "BEAM", PhysicalRole = "PRIMARY",
            Profile = "HEA200", MaterialRaw = "S235JR", Material = "S235JR", GeometryHash = JsonUtil.HashText("geometry:" + id), ManufacturingHash = JsonUtil.HashText("manufacturing:" + id),
            Points = new List<Vec3> { new Vec3(0, 0, 0), new Vec3(1000, 0, 0) }, Managed = true };
        private static ConnectionJoint Joint() => new ConnectionJoint { Model = Model(), SourceRevision = "r1", Main = Part("A"), Secondary = new List<CanonicalPart> { Part("B") },
            DetailId = "D01", DetailSha256 = JsonUtil.HashText("detail"), AttributesSha256 = JsonUtil.HashText("attributes"), AttributesSemanticHash = JsonUtil.HashText("semantic"),
            Geometry = new JointGeometry { ContactPoint = new Vec3(0, 0, 0), MainDirection = new Vec3(1, 0, 0), SecondaryDirection = new Vec3(0, 0, 1),
                AngleDegrees = 90, GapMillimetres = 0, Orientation = "main-positive-secondary-top", GeometryEvidenceId = "joint-geometry-a" } };
        private static ModelIdentity Model() => new ModelIdentity { ModelId = "model", ModelName = "model", ModelPath = "C:/Models/model", TeklaVersion = "2024.0", Revision = "model-r1" };
        private static EvidenceRecord CompleteEvidence(string component, string sha) => new EvidenceRecord { Status = "APPROVED", Component = component, SourceSha256 = sha,
            Commit = new string('a', 40), SchemaVersion = "1.0", TestsPassed = true, RuntimePassed = true, ReferenceModel = "reference", EvidenceIds = new List<string> { "tests", "runtime", "reference" } };
        private static RequestContext Context(ModelIdentity model, ScopeSpec scope) => new RequestContext { Actor = "USER", Principal = TrustedPrincipal.FromLocalHuman("local-user", "USER", "session", engineering: true),
            SessionId = "session", ExpectedModel = model, Scope = scope, SourceRevision = "r1", PlanHash = JsonUtil.HashText("operation"), RequestId = "request", RunId = "run", OperationId = "operation", Mode = "AUTO" };
        private static string Temp() { string p = Path.Combine(Path.GetTempPath(), "cws-review-" + Guid.NewGuid().ToString("N")); Directory.CreateDirectory(p); return p; }
        private static void WithReview(Action<ReviewService, ModelIdentity, ScopeSpec> action)
        { string dir = Temp(); try { action(new ReviewService(new ReviewStore(dir)), Model(), new ScopeSpec()); } finally { Directory.Delete(dir, true); } }
    }
}
