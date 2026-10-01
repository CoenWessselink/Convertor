using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using Newtonsoft.Json.Linq;

namespace Cws.TeklaBridge.Core
{
    // Source freeze is a byte-level checkpoint. Declared raw-source provenance is
    // kept separate from the checked canonical snapshot and is never promoted.
    public sealed class FrozenSource
    {
        public string CanonicalPath { get; internal set; }
        public string PayloadSha256 { get; internal set; }
        public string OriginalSourcePath { get; internal set; }
        public string OriginalSha256 { get; internal set; }
        public bool OriginalBytesVerified { get; internal set; }
        private SteelModel snapshot;
        internal void SetModel(SteelModel value) { snapshot = JsonUtil.Clone(value); }
        public SteelModel GetModel() => JsonUtil.Clone(snapshot);
        public void VerifyUnchanged()
        {
            if (!File.Exists(CanonicalPath) || JsonUtil.HashBytes(File.ReadAllBytes(CanonicalPath)) != PayloadSha256)
                throw new InvalidOperationException("SOURCE_DRIFT: canonical source changed after freeze.");
            if (OriginalBytesVerified && (!File.Exists(OriginalSourcePath) || JsonUtil.HashBytes(File.ReadAllBytes(OriginalSourcePath)) != OriginalSha256))
                throw new InvalidOperationException("SOURCE_DRIFT: original artifact changed after freeze.");
        }
    }
    public static class SourceFreezeService
    {
        public const int MaxSnapshotBytes = 16 * 1024 * 1024;
        public static FrozenSource LoadCanonical(string path, string originalPath = null)
        {
            var fullPath = Path.GetFullPath(path);
            if (new FileInfo(fullPath).Length > MaxSnapshotBytes) throw new InvalidDataException("Canonical snapshot exceeds limit.");
            var bytes = File.ReadAllBytes(fullPath);
            var text = new UTF8Encoding(false, true).GetString(bytes);
            if (text.Length > 0 && text[0] == '\uFEFF') text = text.Substring(1);
            var model = JsonUtil.Deserialize<SteelModel>(text);
            var root = JObject.Parse(text);
            foreach (var name in new[] { "SchemaVersion", "SourceId", "SourceRevision", "SourceSha256", "Parts" })
                if (root.Property(name, StringComparison.Ordinal) == null) throw new InvalidDataException("Missing source field " + name);
            if (model == null || model.SchemaVersion != "1.0" || String.IsNullOrWhiteSpace(model.SourceId) || String.IsNullOrWhiteSpace(model.SourceRevision) || !IsSha256(model.SourceSha256) || model.Parts == null)
                throw new InvalidDataException("Invalid canonical source envelope.");
            if (model.Parts.Any(p => p == null || String.IsNullOrWhiteSpace(p.CanonicalId) || String.IsNullOrWhiteSpace(p.PhysicalRole) || p.SourceId != model.SourceId || p.SourceRevision != model.SourceRevision))
                throw new InvalidDataException("Source occurrence identity/revision is incomplete or mismatched.");
            if (model.Parts.GroupBy(p => p.Key, StringComparer.Ordinal).Any(g => g.Count() != 1)) throw new InvalidDataException("Duplicate canonical physical-role identity.");
            // Reject non-finite coordinates at the ingestion boundary.
            JsonUtil.Hash(model);
            var frozen = new FrozenSource { CanonicalPath = fullPath, PayloadSha256 = JsonUtil.HashBytes(bytes) };
            if (originalPath != null)
            {
                frozen.OriginalSourcePath = Path.GetFullPath(originalPath);
                frozen.OriginalSha256 = JsonUtil.HashBytes(File.ReadAllBytes(frozen.OriginalSourcePath));
                if (!String.Equals(frozen.OriginalSha256, model.SourceSha256, StringComparison.Ordinal)) throw new InvalidDataException("SOURCE_HASH_MISMATCH: declared original provenance does not match bytes.");
                frozen.OriginalBytesVerified = true;
            }
            frozen.SetModel(model); frozen.VerifyUnchanged(); return frozen;
        }
        public static bool IsSha256(string value) => value != null && value.Length == 64 && value.All(c => c >= '0' && c <= '9' || c >= 'a' && c <= 'f');
    }

    public sealed class ProfileObservation
    {
        public string Method { get; set; }
        public string Candidate { get; set; }
        public double SourceConfidence { get; set; }
        public double ProfileConfidence { get; set; }
        public bool ExactEquivalenceProven { get; set; }
        public string SourceSha256 { get; set; }
    }
    public sealed class RecognitionDecision
    {
        public string Status { get; set; }
        public string Candidate { get; set; }
        public List<string> Reasons { get; set; } = new List<string>();
    }
    public static class RecognitionService
    {
        private static readonly HashSet<string> KnownMethods = new HashSet<string>(StringComparer.Ordinal) { "SOURCE_METADATA", "CATALOG", "EXTRUSION", "CROSS_SECTION", "BREP", "DETERMINISTIC_REBUILD" };
        // Consensus is only a candidate. Runtime/manufacturing authority remains
        // a separate immutable manifest gate, never confidence or a majority vote.
        public static RecognitionDecision Evaluate(IEnumerable<ProfileObservation> observations, string sourceSha256)
        {
            var result = new RecognitionDecision { Status = "REVIEW_REQUIRED" };
            var items = observations == null ? new List<ProfileObservation>() : observations.ToList();
            if (!SourceFreezeService.IsSha256(sourceSha256) || items.Count == 0) { result.Reasons.Add("MISSING_SOURCE_EVIDENCE"); return result; }
            if (items.Any(o => o == null || !KnownMethods.Contains(o.Method ?? "") || String.IsNullOrWhiteSpace(o.Candidate) || o.SourceSha256 != sourceSha256 || Double.IsNaN(o.SourceConfidence) || Double.IsNaN(o.ProfileConfidence) || o.SourceConfidence < 0 || o.SourceConfidence > 1 || o.ProfileConfidence < 0 || o.ProfileConfidence > 1))
            { result.Reasons.Add("INVALID_OR_STALE_EVIDENCE"); return result; }
            var candidates = items.Select(o => o.Candidate).Distinct(StringComparer.Ordinal).ToList();
            if (candidates.Count != 1) { result.Reasons.Add("PROFILE_SOURCE_CONFLICT"); return result; }
            result.Candidate = candidates[0];
            if (items.Select(o => o.Method).Distinct().Count() < 2) result.Reasons.Add("MULTI_EVIDENCE_MISSING");
            if (!items.Any(o => (o.Method == "BREP" || o.Method == "DETERMINISTIC_REBUILD") && o.ExactEquivalenceProven)) result.Reasons.Add("EXACT_EQUIVALENCE_MISSING");
            if (result.Reasons.Count == 0) { result.Status = "CANDIDATE_EVIDENCE_MATCH"; result.Reasons.Add("PRODUCTION_AUTHORITY_STILL_REQUIRED"); }
            return result;
        }
    }
}
