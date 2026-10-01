using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using Newtonsoft.Json;

namespace Cws.TeklaBridge.Core
{
    public sealed class EvidenceArtifact
    {
        public string Id { get; set; }
        public string Kind { get; set; }
        public string Path { get; set; }
        public string Sha256 { get; set; }
    }
    public sealed class AuthorityEntry
    {
        public string SourcePath { get; set; }
        public EvidenceRecord Evidence { get; set; }
        public List<EvidenceArtifact> Artifacts { get; set; } = new List<EvidenceArtifact>();
    }
    public sealed class AuthorityManifest
    {
        [JsonProperty(Required = Required.Always)]
        public string SchemaVersion { get; set; } = "1.0";
        [JsonProperty(Required = Required.Always)]
        public string Version { get; set; } = "1.0.0";
        public string Commit { get; set; }
        public string RuntimePolicy { get; set; } = "READ_ONLY";
        public List<AuthorityEntry> Entries { get; set; } = new List<AuthorityEntry>();
    }

    public sealed class AuthorityService
    {
        private readonly AuthorityManifest manifest;
        private readonly string proofRoot;
        private readonly string expectedCommit;
        public bool IsFixture { get; }
        public AuthorityService()
        { manifest = new AuthorityManifest(); }
        private AuthorityService(AuthorityManifest frozen, string root, string commit, bool fixture)
        { manifest = JsonUtil.Clone(frozen); proofRoot = root; expectedCommit = commit; IsFixture = fixture; }
        public AuthorityManifest Snapshot() => JsonUtil.Clone(manifest);
        public static AuthorityService Load(string manifestPath, string proofRoot, string expectedCommit)
        {
            if (String.IsNullOrWhiteSpace(manifestPath) || String.IsNullOrWhiteSpace(proofRoot) || !IsCommit(expectedCommit)) throw new ArgumentException("Manifest, proof root and frozen commit are required.");
            var parsed = JsonUtil.Deserialize<AuthorityManifest>(File.ReadAllText(manifestPath));
            if (parsed == null || parsed.SchemaVersion != "1.0" || parsed.RuntimePolicy != "READ_ONLY" || parsed.Entries == null || parsed.Commit != expectedCommit)
                throw new InvalidDataException("Authority manifest schema, commit or runtime policy is invalid.");
            if (parsed.Entries.Any(e => e == null || e.Evidence == null) || parsed.Entries.Select(e => e.Evidence.Component).Distinct(StringComparer.Ordinal).Count() != parsed.Entries.Count)
                throw new InvalidDataException("Authority components must be unique and explicit.");
            return new AuthorityService(parsed, System.IO.Path.GetFullPath(proofRoot), expectedCommit, false);
        }
        // The fixture authority is intentionally unavailable through manifest loading or HTTP.
        // Its TEST_FIXTURE records can never satisfy production or native component authority.
        public static AuthorityService CreateFixtureAuthority() => new AuthorityService(new AuthorityManifest(), null, null, true);
        public EvidenceRecord FixtureEvidence(string component)
        {
            if (!IsFixture || String.IsNullOrWhiteSpace(component) || !component.StartsWith("fixture.", StringComparison.Ordinal)) throw new InvalidOperationException("Fixture evidence requires a fixture-only authority and component.");
            return new EvidenceRecord { Status = "TEST_FIXTURE", Component = component, SourceSha256 = JsonUtil.HashText("fixture-source:" + component), Commit = "TEST_FIXTURE", SchemaVersion = "1.0", TestsPassed = true, RuntimePassed = false, ReferenceModel = "TEST_FIXTURE_ONLY", EvidenceIds = new List<string> { "fixture-test:" + component } };
        }
        public bool IsApproved(EvidenceRecord supplied, string component = null)
        {
            if (supplied == null) return false;
            if (IsFixture)
            {
                if (supplied.Component == null || !supplied.Component.StartsWith("fixture.", StringComparison.Ordinal)) return false;
                if (component != null && component.StartsWith("fixture.", StringComparison.Ordinal) && component != supplied.Component) return false;
                // A fixture cannot impersonate engineering, production or governance proof.
                if (component != null && !(component.StartsWith("native.", StringComparison.Ordinal) || component.StartsWith("fixture.", StringComparison.Ordinal))) return false;
                if (component != null && component.StartsWith("native.", StringComparison.Ordinal) && supplied.Component != "fixture.execution") return false;
                return JsonUtil.Hash(supplied) == JsonUtil.Hash(FixtureEvidence(supplied.Component));
            }
            if (!HasCompleteProof(supplied) || (component != null && supplied.Component != component) || manifest.RuntimePolicy != "READ_ONLY") return false;
            var entry = manifest.Entries.SingleOrDefault(e => e.Evidence.Component == supplied.Component);
            if (entry == null || JsonUtil.Hash(entry.Evidence) != JsonUtil.Hash(supplied)) return false;
            if (supplied.Commit != expectedCommit || manifest.Commit != expectedCommit) return false;
            try
            {
                if (!MatchesFile(entry.SourcePath, supplied.SourceSha256)) return false;
                if (entry.Artifacts == null || entry.Artifacts.Any(a => a == null) || entry.Artifacts.Select(a => a.Id).Distinct(StringComparer.Ordinal).Count() != entry.Artifacts.Count) return false;
                if (!new[] { "TESTS", "RUNTIME", "REFERENCE_MODEL" }.All(kind => entry.Artifacts.Any(a => a.Kind == kind))) return false;
                if (!supplied.EvidenceIds.OrderBy(x => x, StringComparer.Ordinal).SequenceEqual(entry.Artifacts.Select(a => a.Id).OrderBy(x => x, StringComparer.Ordinal), StringComparer.Ordinal)) return false;
                if (entry.Artifacts.Any(a => String.IsNullOrWhiteSpace(a.Id) || !MatchesFile(a.Path, a.Sha256))) return false;
                return entry.Artifacts.Any(a => a.Kind == "REFERENCE_MODEL" && a.Id == supplied.ReferenceModel);
            }
            catch (IOException) { return false; }
            catch (UnauthorizedAccessException) { return false; }
            catch (ArgumentException) { return false; }
        }
        public List<AuditIssue> ValidateCanonicalPart(CanonicalPart part, bool fixture = false)
        {
            var issues = new List<AuditIssue>();
            if (part == null) { issues.Add(Issue("PART_REQUIRED", null, "Canonical part is absent.")); return issues; }
            if (String.IsNullOrWhiteSpace(part.CanonicalId) || String.IsNullOrWhiteSpace(part.PhysicalRole) || String.IsNullOrWhiteSpace(part.SourceId) || String.IsNullOrWhiteSpace(part.SourceRevision)) issues.Add(Issue("CANONICAL_IDENTITY_REQUIRED", part.Key, "Canonical occurrence, physical role and source identity are required."));
            if (!new[] { "BEAM", "POLYBEAM", "PLATE", "SHAPE" }.Contains(part.Kind, StringComparer.Ordinal)) issues.Add(Issue("PART_KIND_UNKNOWN", part.Key, "Unknown canonical kind."));
            if (String.IsNullOrWhiteSpace(part.MaterialRaw) || String.IsNullOrWhiteSpace(part.Material)) issues.Add(Issue("MATERIAL_UNKNOWN", part.Key, "Explicit raw source material and resolved value are required."));
            else if (!String.Equals(part.MaterialRaw, part.Material, StringComparison.Ordinal)) issues.Add(Issue("MATERIAL_ALIAS_UNPROVEN", part.Key, "Raw and resolved material differ; no value-bound alias proof is implemented in this build."));
            if (String.IsNullOrWhiteSpace(part.Profile)) issues.Add(Issue("PROFILE_UNKNOWN", part.Key, "Explicit resolved profile is required."));
            var prefix = fixture && IsFixture ? "fixture." : "source.";
            if (!IsApproved(part.MaterialAuthority, prefix + "material")) issues.Add(Issue("MATERIAL_AUTHORITY_REQUIRED", part.Key, "Material lacks immutable source or normalization proof."));
            if (!IsApproved(part.ProfileAuthority, prefix + "profile")) issues.Add(Issue("PROFILE_AUTHORITY_REQUIRED", part.Key, "Profile lacks immutable source or recognition proof."));
            if (!IsApproved(part.GeometryAuthority, prefix + "geometry")) issues.Add(Issue("GEOMETRY_AUTHORITY_REQUIRED", part.Key, "Geometry lacks immutable equivalence proof."));
            if (!IsSha256(part.GeometryHash) || !IsSha256(part.ManufacturingHash)) issues.Add(Issue("CANONICAL_HASH_REQUIRED", part.Key, "Geometry and manufacturing SHA-256 values are required."));
            if (part.Points == null || part.Points.Count == 0 || part.Points.Any(p => p == null || !Finite(p.X) || !Finite(p.Y) || !Finite(p.Z))) issues.Add(Issue("GEOMETRY_INVALID", part.Key, "Finite explicit geometry points are required."));
            return issues;
        }
        public static bool HasCompleteProof(EvidenceRecord evidence) => evidence != null && evidence.Status == "APPROVED" &&
            !String.IsNullOrWhiteSpace(evidence.Component) && IsSha256(evidence.SourceSha256) && IsCommit(evidence.Commit) && evidence.SchemaVersion == "1.0" &&
            evidence.TestsPassed && evidence.RuntimePassed && !String.IsNullOrWhiteSpace(evidence.ReferenceModel) && evidence.EvidenceIds != null &&
            evidence.EvidenceIds.Count >= 3 && evidence.EvidenceIds.All(id => !String.IsNullOrWhiteSpace(id)) && evidence.EvidenceIds.Distinct(StringComparer.Ordinal).Count() == evidence.EvidenceIds.Count;
        public static bool IsSha256(string value) => value != null && Regex.IsMatch(value, "\\A[0-9a-f]{64}\\z", RegexOptions.CultureInvariant);
        private static bool IsCommit(string value) => value != null && Regex.IsMatch(value, "\\A[0-9a-f]{40,64}\\z", RegexOptions.CultureInvariant);
        private static bool Finite(double value) => !Double.IsNaN(value) && !Double.IsInfinity(value);
        private static AuditIssue Issue(string code, string key, string message) => new AuditIssue { Code = code, Key = key, Message = message, Repairable = false };
        private bool MatchesFile(string relativePath, string sha)
        {
            if (!IsSha256(sha) || String.IsNullOrWhiteSpace(relativePath) || System.IO.Path.IsPathRooted(relativePath) || relativePath.IndexOf(':') >= 0) return false;
            var absolute = System.IO.Path.GetFullPath(System.IO.Path.Combine(proofRoot, relativePath));
            var boundary = proofRoot.TrimEnd(System.IO.Path.DirectorySeparatorChar, System.IO.Path.AltDirectorySeparatorChar) + System.IO.Path.DirectorySeparatorChar;
            if (!absolute.StartsWith(boundary, StringComparison.Ordinal)) return false;
            // A symlink could escape the frozen proof directory; reject reparse points along the path.
            var cursor = new FileInfo(absolute);
            if (!cursor.Exists || (cursor.Attributes & FileAttributes.ReparsePoint) != 0) return false;
            for (var dir = cursor.Directory; dir != null && dir.FullName.StartsWith(boundary, StringComparison.Ordinal); dir = dir.Parent)
                if ((dir.Attributes & FileAttributes.ReparsePoint) != 0) return false;
            return JsonUtil.HashBytes(File.ReadAllBytes(absolute)) == sha;
        }
    }
}
