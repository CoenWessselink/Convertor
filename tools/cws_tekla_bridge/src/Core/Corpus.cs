using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace Cws.TeklaBridge.Core
{
    public sealed class CorpusManifest
    {
        public string SchemaVersion { get; set; } = "1.0";
        public int TargetModelCount { get; set; } = 20;
        public List<CorpusCase> Cases { get; set; } = new List<CorpusCase>();
    }
    public sealed class CorpusCase
    {
        public string CaseId { get; set; }
        public string ReferenceModel { get; set; }
        public string BindingArtifactId { get; set; }
        public bool HardGate { get; set; }
        public string SourcePath { get; set; }
        public string SourceFileSha256 { get; set; }
        public string SnapshotPath { get; set; }
        public string SnapshotFileSha256 { get; set; }
        public string BeforeSourcePath { get; set; }
        public string BeforeSourceFileSha256 { get; set; }
        public EvidenceRecord RuntimeEvidence { get; set; }
    }
    public sealed class CorpusCaseResult
    {
        public string CaseId { get; set; }
        public string ReferenceModel { get; set; }
        public string Status { get; set; }
        public bool HardGate { get; set; }
        public int CanonicalCount { get; set; }
        public int PhysicalCount { get; set; }
        public List<string> Profiles { get; set; } = new List<string>();
        public List<string> Materials { get; set; } = new List<string>();
        public List<string> Kinds { get; set; } = new List<string>();
        public List<AuditIssue> Issues { get; set; } = new List<AuditIssue>();
        public Dictionary<string, int> RevisionCounts { get; set; } = new Dictionary<string, int>();
    }
    public sealed class CorpusReport
    {
        public string SchemaVersion { get; set; } = "1.0";
        public string Status { get; set; }
        public int TargetModelCount { get; set; }
        public int SuppliedCaseCount { get; set; }
        public int AnalyzedCaseCount { get; set; }
        public int RuntimePassedCaseCount { get; set; }
        public bool CorpusComplete { get; set; }
        public List<CorpusCaseResult> Cases { get; set; } = new List<CorpusCaseResult>();
        public List<string> Limitations { get; set; } = new List<string>();
    }

    // Consumes explicit frozen canonical sources and persisted adapter snapshots,
    // not IFC guesses, placeholder models, or a counter relabeled as runtime proof.
    public sealed class CorpusAnalyzer
    {
        private readonly AuthorityService authority;
        public CorpusAnalyzer(AuthorityService authority = null) { this.authority = authority ?? new AuthorityService(); }
        public CorpusReport Run(string manifestPath)
        {
            var manifest = JsonUtil.Deserialize<CorpusManifest>(File.ReadAllText(manifestPath));
            if (manifest == null || manifest.SchemaVersion != "1.0" || manifest.TargetModelCount <= 0 || manifest.Cases == null
                || manifest.Cases.Any(c => c == null || string.IsNullOrWhiteSpace(c.CaseId))
                || manifest.Cases.Select(c => c.CaseId).Distinct(StringComparer.Ordinal).Count() != manifest.Cases.Count)
                throw new InvalidDataException("Corpus manifest schema/count/case identity is invalid.");
            string root = Path.GetDirectoryName(Path.GetFullPath(manifestPath));
            var report = new CorpusReport { TargetModelCount = manifest.TargetModelCount, SuppliedCaseCount = manifest.Cases.Count };
            foreach (var c in manifest.Cases) report.Cases.Add(Analyze(root, c));
            report.AnalyzedCaseCount = report.Cases.Count(c => c.Status != "NOT_RUN");
            report.RuntimePassedCaseCount = report.Cases.Count(c => c.Status == "PASS");
            report.CorpusComplete = report.Cases.Count >= report.TargetModelCount && report.Cases.All(c => c.Status == "PASS")
                && report.Cases.Count(c => c.HardGate && c.Status == "PASS") >= Math.Min(5, report.TargetModelCount);
            report.Status = report.CorpusComplete ? "PASS" : report.AnalyzedCaseCount == 0 ? "NOT_RUN" : "INCOMPLETE";
            if (report.Cases.Count < report.TargetModelCount) report.Limitations.Add("Only " + report.Cases.Count + " case descriptors supplied for target " + report.TargetModelCount + "; no synthetic cases were created.");
            if (!report.CorpusComplete) report.Limitations.Add("Runtime completeness requires real reference snapshots, approved immutable evidence and hard regression gates.");
            return report;
        }
        private CorpusCaseResult Analyze(string root, CorpusCase c)
        {
            var result = new CorpusCaseResult { CaseId = c.CaseId, ReferenceModel = c.ReferenceModel, HardGate = c.HardGate, Status = "NOT_RUN" };
            if (string.IsNullOrWhiteSpace(c.ReferenceModel) || string.IsNullOrWhiteSpace(c.SourcePath) || string.IsNullOrWhiteSpace(c.SnapshotPath))
            { result.Issues.Add(Issue("CORPUS_INPUT_MISSING", "Explicit real source, snapshot and reference model must be supplied.")); return result; }
            try
            {
                string sourcePath = ResolvePath(root, c.SourcePath), snapshotPath = ResolvePath(root, c.SnapshotPath);
                if (!File.Exists(sourcePath) || !File.Exists(snapshotPath))
                { result.Issues.Add(Issue("CORPUS_INPUT_MISSING", "Source or persisted snapshot file is absent.")); return result; }
                if (!Matches(sourcePath, c.SourceFileSha256) || !Matches(snapshotPath, c.SnapshotFileSha256))
                { result.Status = "FAILED"; result.Issues.Add(Issue("CORPUS_HASH_MISMATCH", "Frozen input SHA-256 does not match file bytes.")); return result; }
                var source = JsonUtil.Deserialize<SteelModel>(File.ReadAllText(sourcePath));
                var snapshot = JsonUtil.Deserialize<AdapterSnapshot>(File.ReadAllText(snapshotPath));
                if (source == null || source.Parts == null || source.SchemaVersion != "1.0" || string.IsNullOrWhiteSpace(source.SourceId)
                    || string.IsNullOrWhiteSpace(source.SourceRevision) || snapshot == null || snapshot.Parts == null || snapshot.Identity == null || !snapshot.Identity.IsComplete)
                    throw new InvalidDataException("Source/snapshot identity, schema or parts are incomplete.");
                result.CanonicalCount = source.Parts.Where(p => p != null).Select(p => p.CanonicalId).Distinct(StringComparer.Ordinal).Count();
                result.PhysicalCount = snapshot.Parts.Count;
                result.Profiles = source.Parts.Where(p => p != null && !string.IsNullOrWhiteSpace(p.Profile)).Select(p => p.Profile).Distinct().OrderBy(s => s, StringComparer.Ordinal).ToList();
                result.Materials = source.Parts.Where(p => p != null && !string.IsNullOrWhiteSpace(p.Material)).Select(p => p.Material).Distinct().OrderBy(s => s, StringComparer.Ordinal).ToList();
                result.Kinds = source.Parts.Where(p => p != null && !string.IsNullOrWhiteSpace(p.Kind)).Select(p => p.Kind).Distinct().OrderBy(s => s, StringComparer.Ordinal).ToList();
                Compare(source, snapshot, result.Issues);
                if (!string.IsNullOrWhiteSpace(c.BeforeSourcePath))
                {
                    var beforePath = ResolvePath(root, c.BeforeSourcePath);
                    if (!File.Exists(beforePath) || !Matches(beforePath, c.BeforeSourceFileSha256))
                        result.Issues.Add(Issue("REVISION_INPUT_MISSING", "Before source file is missing or not SHA-frozen."));
                    else result.RevisionCounts = RevisionCounts(JsonUtil.Deserialize<SteelModel>(File.ReadAllText(beforePath)), source);
                }
                bool runtime = !snapshot.IsFixture && !string.IsNullOrWhiteSpace(snapshot.PersistenceProof)
                    && c.RuntimeEvidence != null && c.RuntimeEvidence.ReferenceModel == c.ReferenceModel
                    && authority.IsApproved(c.RuntimeEvidence, "corpus.runtime:" + c.CaseId) && BoundRuntime(c, snapshot);
                if (runtime) foreach (var part in source.Parts) result.Issues.AddRange(authority.ValidateCanonicalPart(part));
                if (!runtime) result.Issues.Add(Issue("RUNTIME_PROOF_REQUIRED", "Headless/fixture snapshot cannot prove native save/reopen/reference persistence."));
                result.Status = result.Issues.Any(i => i.Code != "RUNTIME_PROOF_REQUIRED") ? "FAILED" : runtime ? "PASS" : "ANALYZED_NO_RUNTIME_PROOF";
            }
            catch (Exception e) when (e is IOException || e is UnauthorizedAccessException || e is ArgumentException
                || e is Newtonsoft.Json.JsonException || e is InvalidDataException)
            { result.Status = "FAILED"; result.Issues.Add(Issue("CORPUS_INPUT_INVALID", e.Message)); }
            return result;
        }
        public static string CaseBindingJson(CorpusCase c, AdapterSnapshot snapshot) => JsonUtil.Serialize(new
        { Schema = "corpus-case-proof/1.0", c.CaseId, c.ReferenceModel, c.SourceFileSha256, c.SnapshotFileSha256,
            c.BeforeSourceFileSha256, snapshot.Identity, snapshot.PersistenceProof, snapshot.IsFixture });
        private bool BoundRuntime(CorpusCase c, AdapterSnapshot snapshot)
        {
            if (string.IsNullOrWhiteSpace(c.BindingArtifactId)) return false;
            string hash = JsonUtil.HashText(CaseBindingJson(c, snapshot));
            var entry = authority.Snapshot().Entries.SingleOrDefault(e => e.Evidence.Component == "corpus.runtime:" + c.CaseId);
            return entry != null && entry.Artifacts.Count(a => a.Id == c.BindingArtifactId && a.Kind == "CORPUS_CASE_PROOF" && a.Sha256 == hash) == 1;
        }
        private static void Compare(SteelModel source, AdapterSnapshot snapshot, List<AuditIssue> issues)
        {
            if (source.Parts.Any(p => p == null) || snapshot.Parts.Any(p => p == null))
            { issues.Add(Issue("CORPUS_PART_NULL", "Null part in source/snapshot.")); return; }
            var expected = source.Parts.GroupBy(Key).ToDictionary(g => g.Key, g => g.ToList());
            var actual = snapshot.Parts.GroupBy(Key).ToDictionary(g => g.Key, g => g.ToList());
            foreach (var item in expected)
            {
                if (item.Value.Count != 1) issues.Add(Issue("CANONICAL_DUPLICATE", item.Key));
                if (!actual.TryGetValue(item.Key, out var observed)) { issues.Add(Issue("PART_MISSING", item.Key)); continue; }
                if (observed.Count != 1) { issues.Add(Issue("PHYSICAL_DUPLICATE", item.Key)); continue; }
                var a = item.Value[0]; var b = observed[0];
                if (a.SourceId != source.SourceId || a.SourceRevision != source.SourceRevision || string.IsNullOrWhiteSpace(a.CanonicalId)
                    || string.IsNullOrWhiteSpace(a.MaterialRaw) || string.IsNullOrWhiteSpace(a.Material) || string.IsNullOrWhiteSpace(a.Profile)
                    || !AuthorityService.IsSha256(a.GeometryHash) || !AuthorityService.IsSha256(a.ManufacturingHash)
                    || a.Points == null || a.Points.Count == 0 || a.Points.Any(p => p == null || Double.IsNaN(p.X) || Double.IsNaN(p.Y) || Double.IsNaN(p.Z)
                        || Double.IsInfinity(p.X) || Double.IsInfinity(p.Y) || Double.IsInfinity(p.Z)))
                    issues.Add(Issue("SOURCE_INTENT_INCOMPLETE", item.Key));
                if (JsonUtil.Hash(Comparable(a)) != JsonUtil.Hash(Comparable(b))) issues.Add(Issue("READBACK_DELTA", item.Key));
            }
            foreach (var item in actual.Keys.Where(k => !expected.ContainsKey(k))) issues.Add(Issue("UNEXPECTED_PART", item));
        }
        private static object Comparable(CanonicalPart p) => new { p.CanonicalId, p.PhysicalRole, p.SourceId, p.SourceRevision,
            p.Kind, p.Profile, p.MaterialRaw, p.Material, p.GeometryHash, p.ManufacturingHash, p.Points, p.Phase, p.Mark, p.Udas };
        private static string Key(CanonicalPart p) => JsonUtil.Hash(new { p.CanonicalId, p.PhysicalRole });
        private static Dictionary<string, int> RevisionCounts(SteelModel before, SteelModel after)
        {
            if (before == null || before.Parts == null || before.Parts.Any(p => p == null) || before.SourceId != after.SourceId)
                throw new InvalidDataException("Revision pair must share an explicit source identity.");
            var counts = new Dictionary<string, int> { ["UNCHANGED"] = 0, ["CHANGED"] = 0, ["ADDED"] = 0, ["REMOVED"] = 0, ["CONFLICTED"] = 0 };
            var old = before.Parts.GroupBy(Key).ToDictionary(g => g.Key, g => g.ToList());
            var current = after.Parts.GroupBy(Key).ToDictionary(g => g.Key, g => g.ToList());
            foreach (var key in old.Keys.Union(current.Keys))
            {
                old.TryGetValue(key, out var a); current.TryGetValue(key, out var b);
                string status = a != null && a.Count != 1 || b != null && b.Count != 1 ? "CONFLICTED" : a == null ? "ADDED"
                    : b == null ? "REMOVED" : JsonUtil.Hash(RevisionComparable(a[0])) == JsonUtil.Hash(RevisionComparable(b[0])) ? "UNCHANGED" : "CHANGED";
                counts[status]++;
            }
            return counts;
        }
        private static object RevisionComparable(CanonicalPart p) => new { p.CanonicalId, p.PhysicalRole, p.SourceId, p.Kind, p.Profile,
            p.MaterialRaw, p.Material, p.GeometryHash, p.ManufacturingHash, p.Points, p.Phase, p.Mark, p.Udas };
        private static string ResolvePath(string root, string relative)
        {
            if (Path.IsPathRooted(relative) || relative.IndexOf(':') >= 0) throw new InvalidDataException("Corpus paths must be local relative data paths.");
            string path = Path.GetFullPath(Path.Combine(root, relative));
            string boundary = root.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar) + Path.DirectorySeparatorChar;
            if (!path.StartsWith(boundary, StringComparison.Ordinal)) throw new InvalidDataException("Corpus input escapes manifest directory.");
            if (File.Exists(path) && (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0) throw new InvalidDataException("Linked corpus data is not accepted.");
            for (var directory = new DirectoryInfo(Path.GetDirectoryName(path)); directory != null && directory.FullName.StartsWith(boundary, StringComparison.Ordinal); directory = directory.Parent)
                if (directory.Exists && (directory.Attributes & FileAttributes.ReparsePoint) != 0) throw new InvalidDataException("Linked corpus directory is not accepted.");
            return path;
        }
        private static bool Matches(string path, string sha) => AuthorityService.IsSha256(sha) && JsonUtil.HashBytes(File.ReadAllBytes(path)) == sha;
        private static AuditIssue Issue(string code, string message) => new AuditIssue { Code = code, Message = message, Repairable = false };
    }
}
