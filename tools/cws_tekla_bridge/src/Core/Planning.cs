using System;
using System.Collections.Generic;
using System.Linq;

namespace Cws.TeklaBridge.Core
{
    public sealed class PlanService
    {
        private readonly AuthorityService authority;
        public PlanService(AuthorityService authority = null) { this.authority = authority ?? new AuthorityService(); }
        public BuildPlan Create(SteelModel source, List<CanonicalPart> actual, ModelIdentity identity, ScopeSpec scope)
        {
            if (source == null || identity == null || scope == null) throw new ArgumentNullException("source/model/scope");
            if (String.IsNullOrWhiteSpace(source.SourceId) || String.IsNullOrWhiteSpace(source.SourceRevision) || String.IsNullOrWhiteSpace(source.SourceSha256))
                throw new ArgumentException("Explicit source identity, revision and SHA-256 are required.");
            ValidateScope(scope);
            var frozenScope = JsonUtil.Clone(scope);
            frozenScope.Values = (frozenScope.Values ?? new List<string>()).Distinct(StringComparer.Ordinal).OrderBy(x => x, StringComparer.Ordinal).ToList();
            var plan = new BuildPlan {
                Model = JsonUtil.Clone(identity), SourceId = source.SourceId, SourceRevision = source.SourceRevision,
                PreviousSourceRevision = source.PreviousSourceRevision, SourceSha256 = source.SourceSha256,
                Scope = frozenScope, ExplicitRemovals = (source.ExplicitRemovals ?? new List<string>()).Distinct(StringComparer.Ordinal).OrderBy(x => x, StringComparer.Ordinal).ToList(), Items = new List<PlanItem>()
            };
            var sourceParts = source.Parts ?? new List<CanonicalPart>();
            var actualParts = actual ?? new List<CanonicalPart>();
            if (sourceParts.Any(x => x == null) || actualParts.Any(x => x == null)) throw new ArgumentException("Null part records are forbidden.");
            var sourceGroups = sourceParts.GroupBy(PartIdentity.Key).ToDictionary(g => g.Key, g => g.ToList(), StringComparer.Ordinal);
            var actualGroups = actualParts.GroupBy(PartIdentity.Key).ToDictionary(g => g.Key, g => g.ToList(), StringComparer.Ordinal);
            foreach (var part in sourceParts.OrderBy(PartIdentity.Key, StringComparer.Ordinal).ThenBy(PartIdentity.ContentHash, StringComparer.Ordinal))
            {
                var key = PartIdentity.Key(part);
                List<CanonicalPart> candidates; actualGroups.TryGetValue(key, out candidates);
                var before = candidates == null ? null : candidates[0];
                if (!Matches(frozenScope, part, before)) continue;
                var after = JsonUtil.Clone(part);
                after.Managed = true;
                // Native identity belongs to the model adapter, never to an imported source file.
                after.NativeId = before == null ? null : before.NativeId;
                after.ManualDownstream = before != null && before.ManualDownstream;
                string status, reason;
                var sourceProblem = SourceProblem(part, source);
                var authorityProblems = authority.ValidateCanonicalPart(part, authority.IsFixture);
                if (authorityProblems.Count != 0) sourceProblem = authorityProblems[0].Code;
                if (sourceGroups[key].Count > 1 || String.IsNullOrEmpty(key)) { status = "BLOCK"; reason = "DUPLICATE_OR_MISSING_CANONICAL_ROLE"; }
                else if (candidates != null && candidates.Count > 1) { status = "BLOCK"; reason = "DUPLICATE_NATIVE_CANONICAL_ROLE"; }
                else if (sourceProblem != null) { status = "REVIEW"; reason = sourceProblem; }
                else if (before != null && (!before.Managed || before.SourceId != source.SourceId)) { status = "BLOCK"; reason = "MANUAL_OR_UNKNOWN_ORIGIN_KEEP"; }
                else if (before != null && before.ManualDownstream && PartIdentity.PersistentHash(before) != PartIdentity.PersistentHash(after)) { status = "BLOCK"; reason = "MANUAL_DOWNSTREAM_KEEP"; }
                else if (before == null) { status = "CREATE"; reason = "Source occurrence absent."; }
                else if (PartIdentity.PersistentHash(before) == PartIdentity.PersistentHash(after)) { status = "KEEP"; reason = "Source and persisted state identical."; }
                else if (String.IsNullOrWhiteSpace(source.PreviousSourceRevision) || before.SourceRevision != source.PreviousSourceRevision) { status = "BLOCK"; reason = "PREVIOUS_SOURCE_REVISION_NOT_PROVEN"; }
                else { status = "UPDATE"; reason = "Explicit source revision delta."; }
                plan.Items.Add(new PlanItem { Key = key, Status = status, Before = JsonUtil.Clone(before), After = after, Reason = reason });
            }
            var removals = new HashSet<string>(source.ExplicitRemovals ?? new List<string>(), StringComparer.Ordinal);
            foreach (var part in actualParts.OrderBy(PartIdentity.Key, StringComparer.Ordinal).ThenBy(x => x.NativeId, StringComparer.Ordinal))
            {
                var key = PartIdentity.Key(part);
                if (sourceGroups.ContainsKey(key) || !Matches(frozenScope, part, part)) continue;
                string status = "KEEP", reason = "Existing object preserved.";
                if (removals.Contains(key))
                {
                    if (!part.Managed || part.SourceId != source.SourceId || part.ManualDownstream || actualGroups[key].Count != 1 ||
                        String.IsNullOrWhiteSpace(source.PreviousSourceRevision) || part.SourceRevision != source.PreviousSourceRevision || String.IsNullOrWhiteSpace(part.NativeId))
                    { status = "BLOCK"; reason = "REMOVE_OWNERSHIP_REVISION_OR_DOWNSTREAM_NOT_PROVEN"; }
                    else { status = "REMOVE"; reason = "Explicit removal, managed source identity and previous revision proven."; }
                }
                else if (part.Managed && part.SourceId == source.SourceId) { status = "BLOCK"; reason = "SOURCE_ABSENCE_IS_NOT_REMOVE_AUTHORITY"; }
                plan.Items.Add(new PlanItem { Key = key, Status = status, Before = JsonUtil.Clone(part), After = status == "REMOVE" ? null : JsonUtil.Clone(part), Reason = reason });
            }
            foreach (var absentRemoval in removals.Where(k => !actualGroups.ContainsKey(k)).OrderBy(x => x, StringComparer.Ordinal))
                plan.Items.Add(new PlanItem { Key = absentRemoval, Status = "BLOCK", Reason = "REMOVE_TARGET_ABSENT_OR_OUTSIDE_MODEL" });
            plan.Items = plan.Items.OrderBy(x => x.Key, StringComparer.Ordinal).ThenBy(x => x.Status, StringComparer.Ordinal).ThenBy(x => x.Reason, StringComparer.Ordinal).ToList();
            plan.PlanId = JsonUtil.Hash(new { plan.Model, plan.SourceId, plan.SourceRevision, plan.SourceSha256, plan.PreviousSourceRevision, plan.ExplicitRemovals, plan.Scope, plan.Items });
            plan.PlanHash = ComputeHash(plan);
            return plan;
        }

        public List<AuditIssue> Validate(BuildPlan plan, RequestContext context, IModelAdapter adapter)
        {
            var issues = new List<AuditIssue>();
            if (plan == null || context == null || adapter == null) { issues.Add(Issue("INVALID_CONTEXT", "Plan, context and adapter required.")); return issues; }
            if (String.IsNullOrWhiteSpace(plan.PlanHash) || plan.PlanHash != ComputeHash(plan) || context.PlanHash != plan.PlanHash)
                issues.Add(Issue("PLAN_HASH_MISMATCH", "Protected plan changed or request hash differs."));
            if (!PartIdentity.SameIdentity(plan.Model, context.ExpectedModel) || !PartIdentity.SameIdentity(plan.Model, adapter.GetIdentity()))
                issues.Add(Issue("MODEL_IDENTITY_MISMATCH", "Model identity/revision changed after plan freeze."));
            if (String.IsNullOrWhiteSpace(plan.SourceRevision) || context.SourceRevision != plan.SourceRevision)
                issues.Add(Issue("SOURCE_REVISION_MISMATCH", "Explicit frozen source revision does not match request."));
            if (context.Scope == null || JsonUtil.Hash(context.Scope) != JsonUtil.Hash(plan.Scope)) issues.Add(Issue("SCOPE_MISMATCH", "Exact scope differs from protected plan."));
            if (String.IsNullOrWhiteSpace(context.RequestId) || String.IsNullOrWhiteSpace(context.RunId) || String.IsNullOrWhiteSpace(context.OperationId))
                issues.Add(Issue("REQUEST_IDS_REQUIRED", "Request, run and operation IDs are mandatory."));
            if (!AuthorityService.IsSha256(plan.SourceSha256) || String.IsNullOrWhiteSpace(plan.SourceId)) issues.Add(Issue("SOURCE_FREEZE_INVALID", "Frozen source SHA and identity required."));
            try { ValidateScope(plan.Scope); } catch (ArgumentException) { issues.Add(Issue("PLAN_SCOPE_INVALID", "Plan scope is invalid.")); }
            if (plan.Model == null || !plan.Model.IsComplete) issues.Add(Issue("MODEL_IDENTITY_REQUIRED", "Complete model identity required."));
            if (plan.Items == null || plan.Items.Any(x => x == null)) { issues.Add(Issue("PLAN_ITEMS_INVALID", "Null plan items are forbidden.")); return issues; }
            foreach (var duplicate in plan.Items.GroupBy(x => x.Key).Where(g => g.Count() > 1 && g.Any(x => new[] { "CREATE", "UPDATE", "REMOVE", "REPAIR" }.Contains(x.Status)))) issues.Add(Issue("DUPLICATE_MUTATION_KEY", "Mutating canonical physical role appears more than once.", duplicate.Key));
            var actual = adapter.ReadParts() ?? new List<CanonicalPart>();
            if (plan.Items.Any(x => new[] { "CREATE", "UPDATE", "REMOVE", "REPAIR" }.Contains(x.Status)))
                foreach (var duplicate in actual.Where(x => !String.IsNullOrWhiteSpace(x.NativeId)).GroupBy(x => x.NativeId, StringComparer.Ordinal).Where(g => g.Count() > 1)) issues.Add(Issue("DUPLICATE_NATIVE_ID", "Native identity maps to multiple physical records.", duplicate.Key));
            var grouped = actual.GroupBy(PartIdentity.Key).ToDictionary(g => g.Key, g => g.ToList(), StringComparer.Ordinal);
            foreach (var item in plan.Items ?? new List<PlanItem>())
            {
                if (!new[] { "CREATE", "UPDATE", "KEEP", "REMOVE", "BLOCK", "REVIEW", "REPAIR" }.Contains(item.Status))
                    issues.Add(Issue("UNKNOWN_PLAN_STATUS", "Unknown plan status.", item.Key));
                var mutation = new[] { "CREATE", "UPDATE", "REMOVE", "REPAIR" }.Contains(item.Status);
                if (mutation)
                {
                    var scopePart = item.After ?? item.Before;
                    if (!Matches(plan.Scope, scopePart, item.Before)) issues.Add(Issue("PLAN_ITEM_OUTSIDE_SCOPE", "Mutation exceeds frozen scope.", item.Key));
                    if (item.Status == "REMOVE" && !(plan.ExplicitRemovals ?? new List<string>()).Contains(item.Key, StringComparer.Ordinal)) issues.Add(Issue("REMOVE_NOT_EXPLICIT", "Remove key lacks explicit frozen source removal instruction.", item.Key));
                    if (item.After != null)
                    {
                        if (item.After.SourceId != plan.SourceId || item.After.SourceRevision != plan.SourceRevision || !item.After.Managed || item.After.ManualDownstream) issues.Add(Issue("PLAN_AFTER_SOURCE_IDENTITY_CONFLICT", "After-state differs from frozen managed source identity/revision.", item.Key));
                        if (item.Status == "CREATE" && !String.IsNullOrEmpty(item.After.NativeId)) issues.Add(Issue("CREATE_NATIVE_ID_FORBIDDEN", "Create cannot supply preexisting native identity.", item.Key));
                        if (item.Status == "UPDATE" && item.After.NativeId != item.Before?.NativeId) issues.Add(Issue("UPDATE_NATIVE_ID_MISMATCH", "Update must preserve exact existing native identity.", item.Key));
                        issues.AddRange(authority.ValidateCanonicalPart(item.After, adapter.IsFixture));
                    }
                }
                List<CanonicalPart> matches; grouped.TryGetValue(item.Key ?? String.Empty, out matches);
                if (item.Status == "CREATE" && matches != null) issues.Add(Issue("CREATE_TARGET_EXISTS", "Create target already exists.", item.Key));
                if (item.Before != null && (matches == null || matches.Count != 1 || PartIdentity.PersistentHash(matches[0]) != PartIdentity.PersistentHash(item.Before) || matches[0].NativeId != item.Before.NativeId))
                    issues.Add(Issue("STALE_BEFORE_STATE", "Actual before-state changed since planning.", item.Key));
                if (item.Status == "UPDATE" || item.Status == "REMOVE" || item.Status == "REPAIR")
                {
                    if (item.Before == null || !item.Before.Managed || item.Before.SourceId != plan.SourceId || item.Before.ManualDownstream || String.IsNullOrWhiteSpace(item.Before.NativeId))
                        issues.Add(Issue("UNSAFE_MANAGED_MUTATION", "Ownership and downstream safety not proven.", item.Key));
                    if (item.Status != "REPAIR" && (String.IsNullOrWhiteSpace(plan.PreviousSourceRevision) || item.Before == null || item.Before.SourceRevision != plan.PreviousSourceRevision))
                        issues.Add(Issue("PREVIOUS_REVISION_MISMATCH", "Previous source revision is required for destructive effects.", item.Key));
                }
                if ((item.Status == "CREATE" || item.Status == "UPDATE" || item.Status == "REPAIR") && (item.After == null || item.Key != PartIdentity.Key(item.After)))
                    issues.Add(Issue("PLAN_TARGET_IDENTITY_MISMATCH", "Canonical and physical role must match item key.", item.Key));
                if ((item.Status == "CREATE" || item.Status == "UPDATE" || item.Status == "REPAIR") && !adapter.Capabilities.Supports("part.upsert"))
                    issues.Add(Issue("CAPABILITY_NOT_SUPPORTED", "Adapter does not support upsert.", item.Key));
                if (item.Status == "REMOVE" && !adapter.Capabilities.Supports("part.remove")) issues.Add(Issue("CAPABILITY_NOT_SUPPORTED", "Adapter does not support explicit remove.", item.Key));
            }
            return issues;
        }

        public static string ComputeHash(BuildPlan plan)
        {
            return JsonUtil.Hash(new { plan.PlanId, plan.Model, plan.SourceId, plan.SourceRevision, plan.PreviousSourceRevision, plan.SourceSha256, plan.ExplicitRemovals, plan.Scope, plan.Items });
        }

        public static bool Matches(ScopeSpec scope, CanonicalPart source, CanonicalPart actual)
        {
            if (scope == null || source == null) return false;
            var values = new HashSet<string>(scope.Values ?? new List<string>(), StringComparer.Ordinal);
            switch (scope.Kind)
            {
                case "ALL": return true;
                case "SELECTION": return values.Contains(source.CanonicalId ?? "") || values.Contains(PartIdentity.Key(source)) ||
                    (!String.IsNullOrEmpty(actual == null ? null : actual.NativeId) && values.Contains(actual.NativeId));
                case "PHASE": return values.Contains(source.Phase ?? "");
                case "MARKS": return values.Contains(source.Mark ?? "");
                case "CHANGED": return actual == null || source.SourceId != actual.SourceId || source.SourceRevision != actual.SourceRevision || PartIdentity.ContentHash(source) != PartIdentity.ContentHash(actual);
                case "REVIEW": return values.Contains(source.CanonicalId ?? "") || values.Contains(PartIdentity.Key(source));
                default: return false;
            }
        }

        private static void ValidateScope(ScopeSpec scope)
        {
            if (!new[] { "ALL", "SELECTION", "PHASE", "MARKS", "CHANGED", "REVIEW" }.Contains(scope.Kind)) throw new ArgumentException("Unknown scope.");
            if (new[] { "SELECTION", "PHASE", "MARKS", "REVIEW" }.Contains(scope.Kind) && (scope.Values == null || scope.Values.Count == 0)) throw new ArgumentException("Explicit scope values are required.");
            if ((scope.Values ?? new List<string>()).Any(String.IsNullOrWhiteSpace)) throw new ArgumentException("Blank scope values are forbidden.");
        }

        private static string SourceProblem(CanonicalPart part, SteelModel source)
        {
            if (part.SourceId != source.SourceId || part.SourceRevision != source.SourceRevision) return "SOURCE_PART_REVISION_IDENTITY_CONFLICT";
            if (String.IsNullOrWhiteSpace(part.MaterialRaw) || String.IsNullOrWhiteSpace(part.Material)) return "MATERIAL_UNRESOLVED_NO_FALLBACK";
            if (String.IsNullOrWhiteSpace(part.Profile)) return "PROFILE_UNRESOLVED_NO_FALLBACK";
            if (String.IsNullOrWhiteSpace(part.GeometryHash) || String.IsNullOrWhiteSpace(part.ManufacturingHash)) return "GEOMETRY_OR_MANUFACTURING_PROOF_MISSING";
            if (part.Points == null || part.Points.Count == 0 || part.Points.Any(p => p == null || Double.IsNaN(p.X) || Double.IsInfinity(p.X) || Double.IsNaN(p.Y) || Double.IsInfinity(p.Y) || Double.IsNaN(p.Z) || Double.IsInfinity(p.Z))) return "GEOMETRY_NONFINITE_OR_MISSING";
            if (!new[] { "BEAM", "POLYBEAM", "PLATE", "SHAPE" }.Contains(part.Kind)) return "KIND_UNSUPPORTED";
            foreach (var authority in new[] { part.MaterialAuthority, part.ProfileAuthority, part.GeometryAuthority })
                if (authority == null || (authority.Status != "APPROVED" && authority.Status != "TEST_FIXTURE") || String.IsNullOrWhiteSpace(authority.SourceSha256)) return "COMPONENT_AUTHORITY_MISSING_OR_CONFLICTED";
            return null;
        }

        internal static AuditIssue Issue(string code, string message, string key = null, bool repairable = false)
        { return new AuditIssue { Code = code, Key = key, Message = message, Repairable = repairable }; }
    }
}
