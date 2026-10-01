using System;
using System.Collections.Generic;
using System.Linq;

namespace Cws.TeklaBridge.Core
{
    public sealed class ReadbackService
    {
        // This allowlist is deliberately metadata-only. Manufacturing or geometry proof never self-heals.
        public static readonly string[] SafeMetadataKeys = { "CWS_RUN_ID", "CWS_SCOPE_HASH" };

        public AuditResult Compare(BuildPlan plan, AdapterSnapshot snapshot) { return Compare(plan, snapshot, false); }

        internal AuditResult Compare(BuildPlan plan, AdapterSnapshot snapshot, bool persistenceTrusted)
        {
            if (plan == null || snapshot == null) throw new ArgumentNullException("plan/snapshot");
            var result = new AuditResult { Issues = new List<AuditIssue>(), PersistenceProven = persistenceTrusted && !snapshot.IsFixture && !String.IsNullOrWhiteSpace(snapshot.PersistenceProof) };
            if (snapshot.Identity == null || plan.Model == null || snapshot.Identity.ModelId != plan.Model.ModelId ||
                snapshot.Identity.ModelPath != plan.Model.ModelPath || snapshot.Identity.ModelName != plan.Model.ModelName ||
                snapshot.Identity.TeklaVersion != plan.Model.TeklaVersion || String.IsNullOrWhiteSpace(snapshot.Identity.Revision))
                result.Issues.Add(PlanService.Issue("READBACK_MODEL_IDENTITY_MISMATCH", "Reopened model identity differs from frozen model."));
            if (!snapshot.IsFixture && !persistenceTrusted) result.Issues.Add(PlanService.Issue("PERSISTENCE_LIFECYCLE_NOT_VERIFIED", "Uploaded proof text cannot establish a genuine save/reopen lifecycle."));
            if (String.IsNullOrWhiteSpace(snapshot.PersistenceProof)) result.Issues.Add(PlanService.Issue("PERSISTENCE_NOT_PROVEN", "Save/reopen evidence is missing."));
            if (snapshot.IsFixture) result.Issues.Add(PlanService.Issue("FIXTURE_NOT_RUNTIME_PROOF", "Fixture roundtrip cannot establish native persistence or production release."));
            var actual = snapshot.Parts ?? new List<CanonicalPart>();
            var groups = actual.GroupBy(PartIdentity.Key).ToDictionary(g => g.Key, g => g.ToList(), StringComparer.Ordinal);
            var items = plan.Items ?? new List<PlanItem>();
            var expectedKeys = new HashSet<string>(items.Select(x => x.Key), StringComparer.Ordinal);
            var scopeActual = new List<CanonicalPart>();
            var countedKeys = new HashSet<string>(StringComparer.Ordinal);
            foreach (var item in items)
            {
                List<CanonicalPart> matches; groups.TryGetValue(item.Key ?? String.Empty, out matches);
                if (matches != null && countedKeys.Add(item.Key) && ((item.After != null && item.After.SourceId == plan.SourceId) || (item.Before != null && item.Before.SourceId == plan.SourceId))) scopeActual.AddRange(matches);
                if (item.Status == "REMOVE")
                {
                    if (matches != null) result.Issues.Add(PlanService.Issue("REMOVE_PERSISTENCE_FAILED", "Explicitly removed occurrence remains after reopen.", item.Key));
                    continue;
                }
                if ((item.Status == "BLOCK" || item.Status == "REVIEW") && item.After != null && item.After.SourceId == plan.SourceId)
                {
                    if (matches == null || matches.Count == 0) result.Issues.Add(PlanService.Issue("UNBUILT_BLOCKED_OCCURRENCE", "Blocked source geometry is absent; completeness cannot be claimed.", item.Key));
                    else if (matches.Count == 1 && (String.IsNullOrWhiteSpace(item.After.GeometryHash) || item.After.GeometryHash != matches[0].GeometryHash || item.After.ManufacturingHash != matches[0].ManufacturingHash || JsonUtil.Hash(item.After.Points) != JsonUtil.Hash(matches[0].Points) || item.After.Kind != matches[0].Kind || item.After.Profile != matches[0].Profile))
                        result.Issues.Add(PlanService.Issue("BLOCKED_CANONICAL_GEOMETRY_DELTA", "Retained physical geometry differs from blocked current source target.", item.Key));
                }
                var expected = item.Status == "BLOCK" || item.Status == "REVIEW" ? item.Before : item.After ?? item.Before;
                if (expected == null) continue; // Unresolved source occurrence is represented by its plan block, never manufactured.
                if (matches == null || matches.Count == 0) { result.Issues.Add(PlanService.Issue("MISSING_PHYSICAL_ROLE", "Expected canonical physical role absent after reopen.", item.Key)); continue; }
                if (matches.Count != 1) { result.Issues.Add(PlanService.Issue("DUPLICATE_PHYSICAL_ROLE", "More than one physical part has this canonical role.", item.Key)); continue; }
                var observed = matches[0];
                if (item.Status == "KEEP" && (!expected.Managed || expected.SourceId != plan.SourceId))
                {
                    if (PartIdentity.PersistentHash(expected) != PartIdentity.PersistentHash(observed) || expected.NativeId != observed.NativeId)
                        result.Issues.Add(PlanService.Issue("MANUAL_PRESERVATION_MISMATCH", "Manual/other-source physical state changed against its exact baseline.", item.Key));
                }
                else ComparePart(expected, observed, item.Key, result.Issues);
            }
            foreach (var part in actual)
            {
                var key = PartIdentity.Key(part);
                if (String.IsNullOrEmpty(key) && part.Managed) result.Issues.Add(PlanService.Issue("ORPHAN_MANAGED_IDENTITY", "Managed object lacks canonical occurrence/role identity.", part.NativeId));
                if (!expectedKeys.Contains(key) && part.Managed && part.SourceId == plan.SourceId && PlanService.Matches(plan.Scope, part, part))
                    result.Issues.Add(PlanService.Issue("UNEXPECTED_MANAGED_OCCURRENCE", "Unexpected managed occurrence exists; automatic orphan deletion is forbidden.", key));
            }
            result.CanonicalCount = scopeActual.Select(x => x.CanonicalId).Where(x => !String.IsNullOrEmpty(x)).Distinct(StringComparer.Ordinal).Count();
            result.PhysicalCount = scopeActual.Count;
            var material = result.Issues.Where(x => x.Code != "FIXTURE_NOT_RUNTIME_PROOF").ToList();
            if (material.Any(x => !x.Repairable && x.Code != "UNBUILT_BLOCKED_OCCURRENCE" && x.Code != "BLOCKED_CANONICAL_GEOMETRY_DELTA")) result.Status = "FAILED";
            else if (material.Any(x => x.Code == "UNBUILT_BLOCKED_OCCURRENCE" || x.Code == "BLOCKED_CANONICAL_GEOMETRY_DELTA")) result.Status = "REVIEW_REQUIRED";
            else if (material.Count != 0) result.Status = "REPAIRABLE_DELTA";
            else if (items.Any(x => x.Status == "BLOCK" || x.Status == "REVIEW")) result.Status = "PASS_WITH_BLOCKS";
            else result.Status = "PASS";
            return result;
        }

        private static void ComparePart(CanonicalPart expected, CanonicalPart actual, string key, List<AuditIssue> issues)
        {
            if (expected.SourceId != actual.SourceId || expected.SourceRevision != actual.SourceRevision || expected.CanonicalId != actual.CanonicalId || expected.PhysicalRole != actual.PhysicalRole)
                issues.Add(PlanService.Issue("SOURCE_IDENTITY_READBACK_MISMATCH", "Actual source/canonical/revision/physical identity differs.", key));
            if (expected.Kind != actual.Kind) issues.Add(PlanService.Issue("TYPE_READBACK_MISMATCH", "Actual Tekla part type differs.", key));
            if (expected.Profile != actual.Profile) issues.Add(PlanService.Issue("PROFILE_READBACK_MISMATCH", "Actual profile differs from canonical authority.", key));
            if (String.IsNullOrWhiteSpace(actual.MaterialRaw) || String.IsNullOrWhiteSpace(actual.Material) || expected.MaterialRaw != actual.MaterialRaw || expected.Material != actual.Material)
                issues.Add(PlanService.Issue("MATERIAL_READBACK_MISMATCH", "Raw and normalized material must remain separately exact.", key));
            if (String.IsNullOrWhiteSpace(expected.GeometryHash) || String.IsNullOrWhiteSpace(actual.GeometryHash) || expected.GeometryHash != actual.GeometryHash || JsonUtil.Hash(expected.Points) != JsonUtil.Hash(actual.Points))
                issues.Add(PlanService.Issue("GEOMETRY_READBACK_MISMATCH", "Independent geometry and placement evidence differs or is absent.", key));
            if (String.IsNullOrWhiteSpace(expected.ManufacturingHash) || String.IsNullOrWhiteSpace(actual.ManufacturingHash) || expected.ManufacturingHash != actual.ManufacturingHash)
                issues.Add(PlanService.Issue("MANUFACTURING_READBACK_MISMATCH", "Features/holes/bolts/welds manufacturing proof differs or is absent.", key));
            if (expected.Phase != actual.Phase || expected.Mark != actual.Mark) issues.Add(PlanService.Issue("PLACEMENT_PHASE_MARK_MISMATCH", "Phase or mark differs after reopen.", key));
            if (expected.Managed != actual.Managed || expected.ManualDownstream != actual.ManualDownstream) issues.Add(PlanService.Issue("OWNERSHIP_READBACK_MISMATCH", "Managed ownership/downstream provenance changed.", key));
            var expectedUdas = expected.Udas ?? new Dictionary<string,string>();
            var actualUdas = actual.Udas ?? new Dictionary<string,string>();
            foreach (var udaKey in expectedUdas.Keys.Union(actualUdas.Keys).OrderBy(x => x, StringComparer.Ordinal))
            {
                string ev, av; expectedUdas.TryGetValue(udaKey, out ev); actualUdas.TryGetValue(udaKey, out av);
                if (ev == av && expectedUdas.ContainsKey(udaKey) == actualUdas.ContainsKey(udaKey)) continue;
                var repairable = SafeMetadataKeys.Contains(udaKey) && expected.Managed && actual.Managed && !actual.ManualDownstream &&
                    !String.IsNullOrWhiteSpace(actual.NativeId) && expected.SourceId == actual.SourceId && expected.SourceRevision == actual.SourceRevision &&
                    expected.CanonicalId == actual.CanonicalId && expected.PhysicalRole == actual.PhysicalRole && expected.Kind == actual.Kind &&
                    expected.Profile == actual.Profile && expected.MaterialRaw == actual.MaterialRaw && expected.Material == actual.Material &&
                    !String.IsNullOrWhiteSpace(expected.GeometryHash) && expected.GeometryHash == actual.GeometryHash &&
                    !String.IsNullOrWhiteSpace(expected.ManufacturingHash) && expected.ManufacturingHash == actual.ManufacturingHash;
                issues.Add(PlanService.Issue("UDA_READBACK_MISMATCH", "UDA " + udaKey + " differs after reopen.", key, repairable));
            }
        }
    }

    public interface IPersistenceEvidenceVerifier
    {
        bool VerifyPersistenceEvidence(AdapterSnapshot snapshot);
    }

    public interface IMetadataRepairAdapter
    {
        void RepairMetadata(CanonicalPart expected, List<string> keys);
    }
}
