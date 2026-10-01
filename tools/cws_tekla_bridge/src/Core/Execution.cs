using System;
using System.Collections.Generic;
using System.Linq;

namespace Cws.TeklaBridge.Core
{
    public sealed class ExecutionService
    {
        private readonly IModelAdapter adapter;
        private readonly AuthorizationService auth;
        private readonly JournalStore journal;
        public ExecutionService(IModelAdapter adapter, AuthorizationService auth, JournalStore journal)
        { this.adapter = adapter ?? throw new ArgumentNullException(nameof(adapter)); this.auth = auth ?? throw new ArgumentNullException(nameof(auth)); this.journal = journal ?? throw new ArgumentNullException(nameof(journal)); }

        public RunResult Execute(BuildPlan submittedPlan, RequestContext submittedContext)
        {
            if (submittedPlan == null || submittedContext == null) return Failure(submittedContext?.RunId, submittedPlan?.PlanHash, "INVALID_CONTEXT");
            // Detach mutable caller objects before checking authorization or touching the model.
            var plan = JsonUtil.Clone(submittedPlan);
            var context = JsonUtil.Clone(submittedContext);
            context.Principal = submittedContext.Principal; context.SessionId = submittedContext.SessionId;
            var fingerprint = JsonUtil.Hash(new { context.RequestId, context.RunId, context.OperationId, context.Actor, context.Mode, context.Scope, context.ExpectedModel, context.SourceRevision, context.DryRun, context.PlanHash, context.SessionId });
            try
            {
                using (journal.AcquireExclusive())
                {
                    if (String.IsNullOrWhiteSpace(plan.PlanHash) || plan.PlanHash != PlanService.ComputeHash(plan) || context.PlanHash != plan.PlanHash) return Failure(context.RunId, plan.PlanHash, "PLAN_HASH_MISMATCH");
                    var previous = journal.FindRequest(context.RequestId);
                    if (previous != null)
                    {
                        if (previous.ContextHash != fingerprint || previous.PlanHash != plan.PlanHash) return Failure(context.RunId, plan.PlanHash, "IDEMPOTENCY_KEY_CONFLICT");
                        var result = journal.CompletedResult(context.RequestId);
                        if (result == null) return Failure(context.RunId, plan.PlanHash, "RECOVERY_REQUIRED_INCOMPLETE_REQUEST");
                        var committed = journal.ReadAll().LastOrDefault(x => x.RequestId == context.RequestId && x.Kind == "COMMITTED");
                        if (committed != null && (committed.Snapshot == null || !PartIdentity.SameIdentity(committed.Snapshot.Identity, adapter.GetIdentity()) || SnapshotHash(committed.Snapshot.Parts) != SnapshotHash(adapter.ReadParts())))
                            return Failure(context.RunId, plan.PlanHash, "IDEMPOTENT_REPLAY_STATE_CHANGED");
                        var replay = JsonUtil.Clone(result);
                        replay.Events.Add("IDEMPOTENT_REPLAY: original recorded result; no mutation or new release evidence.");
                        return replay;
                    }
                    if (journal.Unfinished().Count != 0) return Failure(context.RunId, plan.PlanHash, "RECOVERY_REQUIRED_INCOMPLETE_TRANSACTION");
                    if (journal.ReadAll().Any(x => x.RunId == context.RunId || x.OperationId == context.OperationId)) return Failure(context.RunId, plan.PlanHash, "RUN_OR_OPERATION_ID_REUSED");
                    var validation = new PlanService(auth.Authority).Validate(plan, context, adapter);
                    if (validation.Count != 0) return FailedAudit(context.RunId, plan.PlanHash, validation);
                    if (context.DryRun || context.Mode == "CHECK_ONLY" || context.Mode == "PROPOSE")
                    {
                        var modeAuth = auth.Authorize("build-plan/validate", context, adapter.Capabilities);
                        if (!modeAuth.Allowed) return Failure(context.RunId, plan.PlanHash, modeAuth.Code);
                        return new RunResult { RunId = context.RunId, Status = "PREPARED", PlanHash = plan.PlanHash,
                            CanonicalCount = Expected(plan).Select(p => p.CanonicalId).Distinct(StringComparer.Ordinal).Count(), PhysicalCount = Expected(plan).Count,
                            Events = new List<string> { "Validated immutable plan; no writes or persistence/release evidence." } };
                    }
                    var writes = plan.Items.Where(x => x.Status == "CREATE" || x.Status == "UPDATE" || x.Status == "REMOVE" || x.Status == "REPAIR").ToList();
                    var authChecks = new List<string> { "build-plan/execute", "transactions/begin", "transactions/commit", "save", "reopen" };
                    foreach (var item in writes)
                    {
                        if (item.Status == "REPAIR") return Failure(context.RunId, plan.PlanHash, "REPAIR_PLAN_NOT_EXTERNALLY_EXECUTABLE");
                        authChecks.Add(item.Status == "REMOVE" ? "part/remove" : (item.After.Kind ?? "").ToLowerInvariant() + "/upsert");
                        if (item.After != null)
                        {
                            var partProof = auth.Authority.ValidateCanonicalPart(item.After, adapter.IsFixture);
                            if (partProof.Count != 0) return FailedAudit(context.RunId, plan.PlanHash, partProof);
                        }
                    }
                    foreach (var endpoint in authChecks.Distinct(StringComparer.Ordinal))
                    {
                        var decision = auth.Authorize(endpoint, context, adapter.Capabilities, EvidenceFor(endpoint));
                        if (!decision.Allowed) return Failure(context.RunId, plan.PlanHash, endpoint + ":" + decision.Code);
                    }
                    if (adapter.IsFixture != auth.Authority.IsFixture) return Failure(context.RunId, plan.PlanHash, "FIXTURE_AUTHORITY_ADAPTER_MISMATCH");
                    var before = new AdapterSnapshot { Identity = adapter.GetIdentity(), Parts = adapter.ReadParts(), IsFixture = adapter.IsFixture };
                    var run = new RunResult { RunId = context.RunId, PlanHash = plan.PlanHash, Status = "RUNNING" };
                    journal.Append(Entry("BEGIN", plan, context, fingerprint, snapshot: before));
                    var checkpoint = JsonUtil.Clone(before);
                    try
                    {
                        foreach (var item in writes)
                        {
                            // Recheck model identity and exact frozen before-state immediately before each write.
                            var currentIdentity = adapter.GetIdentity();
                            var currentParts = adapter.ReadParts();
                            if (!PartIdentity.SameIdentity(currentIdentity, checkpoint.Identity) || SnapshotHash(currentParts) != SnapshotHash(checkpoint.Parts)) throw new InvalidOperationException("MODEL_STATE_CHANGED_DURING_RUN");
                            var observed = currentParts.Where(p => PartIdentity.Key(p) == item.Key).ToList();
                            if (item.Before == null ? observed.Count != 0 : observed.Count != 1 || PartIdentity.PersistentHash(observed[0]) != PartIdentity.PersistentHash(item.Before) || observed[0].NativeId != item.Before.NativeId)
                                throw new InvalidOperationException("BEFORE_STATE_CHANGED_DURING_RUN");
                            journal.Append(Entry("WRITE_INTENT", plan, context, fingerprint, item));
                            if (item.Status == "REMOVE") adapter.Remove(JsonUtil.Clone(item.Before)); else adapter.Upsert(JsonUtil.Clone(item.After));
                            run.Mutations++;
                            var afterParts = adapter.ReadParts();
                            var afterIdentity = adapter.GetIdentity();
                            if (afterParts.Where(p => !String.IsNullOrWhiteSpace(p.NativeId)).GroupBy(p => p.NativeId, StringComparer.Ordinal).Any(g => g.Count() > 1)) throw new InvalidOperationException("DUPLICATE_NATIVE_ID_AFTER_WRITE");
                            var predicted = JsonUtil.Clone(checkpoint.Parts);
                            predicted.RemoveAll(p => PartIdentity.Key(p) == item.Key);
                            var afterTarget = afterParts.Where(p => PartIdentity.Key(p) == item.Key).ToList();
                            if (item.Status == "REMOVE" ? afterTarget.Count != 0 : afterTarget.Count != 1 || String.IsNullOrWhiteSpace(afterTarget[0].NativeId) || PartIdentity.PersistentHash(afterTarget[0]) != PartIdentity.PersistentHash(item.After))
                                throw new InvalidOperationException("WRITE_RESULT_NOT_EXACT_PLANNED_DELTA");
                            if (item.Status != "REMOVE") predicted.Add(afterTarget[0]);
                            if (!SameModelWithoutRevision(checkpoint.Identity, afterIdentity) || SnapshotHash(predicted) != SnapshotHash(afterParts)) throw new InvalidOperationException("UNPLANNED_SIDE_EFFECT_DURING_WRITE");
                            checkpoint = new AdapterSnapshot { Identity = afterIdentity, Parts = afterParts, IsFixture = adapter.IsFixture };
                            journal.Append(Entry("WRITE_APPLIED", plan, context, fingerprint, item, snapshot: checkpoint));
                        }
                        journal.Append(Entry("SAVE_INTENT", plan, context, fingerprint));
                        adapter.Save();
                        journal.Append(Entry("SAVE_COMPLETED", plan, context, fingerprint));
                        var snapshot = adapter.ReopenAndReadback();
                        journal.Append(Entry("REOPEN_READBACK", plan, context, fingerprint, snapshot: snapshot));
                        var audit = new ReadbackService().Compare(plan, snapshot, HasVerifiedPersistence(snapshot));
                        var repairCounts = new Dictionary<string,int>(StringComparer.Ordinal);
                        for (var cycle = 0; cycle < 2 && audit.Status == "REPAIRABLE_DELTA"; cycle++)
                        {
                            var repairAdapter = adapter as IMetadataRepairAdapter;
                            var decision = auth.Authorize("self-heal", context, adapter.Capabilities, EvidenceFor("self-heal"));
                            if (repairAdapter == null || !adapter.Capabilities.Supports("part.safe-metadata-repair") || !decision.Allowed) break;
                            var repairIssues = audit.Issues.Where(i => i.Repairable).GroupBy(i => i.Key).ToList();
                            if (audit.Issues.Any(i => !i.Repairable && i.Code != "FIXTURE_NOT_RUNTIME_PROOF")) break;
                            foreach (var issueGroup in repairIssues)
                            {
                                int used; repairCounts.TryGetValue(issueGroup.Key, out used);
                                if (used >= 2) continue;
                                var expected = Expected(plan).Single(p => PartIdentity.Key(p) == issueGroup.Key);
                                if (!expected.Managed || expected.ManualDownstream || auth.Authority.ValidateCanonicalPart(expected, adapter.IsFixture).Count != 0) throw new InvalidOperationException("SAFE_REPAIR_AUTHORITY_LOST");
                                journal.Append(Entry("REPAIR_INTENT", plan, context, fingerprint, new PlanItem { Key = issueGroup.Key, Status = "REPAIR", After = expected }));
                                repairAdapter.RepairMetadata(JsonUtil.Clone(expected), ReadbackService.SafeMetadataKeys.ToList());
                                repairCounts[issueGroup.Key] = used + 1;
                                run.Mutations++;
                                journal.Append(Entry("REPAIR_APPLIED", plan, context, fingerprint));
                            }
                            journal.Append(Entry("SAVE_INTENT", plan, context, fingerprint));
                            adapter.Save(); snapshot = adapter.ReopenAndReadback(); audit = new ReadbackService().Compare(plan, snapshot, HasVerifiedPersistence(snapshot));
                            journal.Append(Entry("REPAIR_REAUDIT", plan, context, fingerprint, snapshot: snapshot));
                        }
                        run.Audit = audit; run.CanonicalCount = audit.CanonicalCount; run.PhysicalCount = audit.PhysicalCount;
                        if (audit.Status == "PASS" && audit.PersistenceProven && !adapter.IsFixture) run.Status = "RELEASED";
                        else if (audit.Status == "PASS" && adapter.IsFixture) run.Status = "TEST_FIXTURE_PASS";
                        else if (audit.Status == "PASS_WITH_BLOCKS") run.Status = "COMPLETE_GEOMETRY_WITH_BLOCKS";
                        else if (audit.Status == "REPAIRABLE_DELTA" || audit.Status == "REVIEW_REQUIRED") run.Status = "BLOCKED_REVIEW_REQUIRED";
                        else run.Status = "FAILED";
                        run.Events.Add("Matrix " + auth.Matrix.Version + "; save/reopen/readback " + audit.Status + "; fixture=" + adapter.IsFixture);
                        if (audit.Status == "FAILED") throw new ReadbackFailureException(run);
                        journal.Append(Entry("COMMITTED", plan, context, fingerprint, snapshot: snapshot, result: run));
                        return run;
                    }
                    catch (Exception error)
                    {
                        var readbackFailure = error as ReadbackFailureException;
                        if (readbackFailure != null) run = readbackFailure.Result;
                        run.Status = "FAILED"; run.Events.Add(error.GetType().Name + ":" + error.Message);
                        journal.Append(Entry("FAILURE", plan, context, fingerprint, result: run));
                        bool compensated = false;
                        var compensating = adapter as ICompensatingModelAdapter;
                        if (compensating != null && adapter.IsFixture && adapter.Capabilities.Supports("transaction.compensate"))
                        {
                            journal.Append(Entry("COMPENSATE_INTENT", plan, context, fingerprint, snapshot: before));
                            try
                            {
                                compensated = compensating.RestoreSnapshot(before) && SnapshotHash(adapter.ReadParts()) == SnapshotHash(before.Parts);
                            }
                            catch (Exception ex) { run.Events.Add("Compensation failed: " + ex.Message); }
                        }
                        run.Events.Add(compensated ? "COMPENSATION_PROVEN: pre-run physical state restored." : "RECOVERY_REQUIRED: uncertain native state; subsequent writes blocked.");
                        journal.Append(Entry(compensated ? "ROLLED_BACK" : "RECOVERY_REQUIRED", plan, context, fingerprint, result: run));
                        return run;
                    }
                }
            }
            catch (Exception ex) { return Failure(context.RunId, plan.PlanHash, "JOURNAL_OR_ADAPTER_UNAVAILABLE:" + ex.GetType().Name + ":" + ex.Message); }
        }

        private bool HasVerifiedPersistence(AdapterSnapshot snapshot) => !adapter.IsFixture && (adapter as IPersistenceEvidenceVerifier)?.VerifyPersistenceEvidence(snapshot) == true;
        private static bool SameModelWithoutRevision(ModelIdentity a, ModelIdentity b) => a != null && b != null && a.ModelId == b.ModelId && a.ModelPath == b.ModelPath && a.ModelName == b.ModelName && a.TeklaVersion == b.TeklaVersion && !String.IsNullOrWhiteSpace(b.Revision);
        private EvidenceRecord EvidenceFor(string endpoint)
        {
            if (adapter.IsFixture && auth.Authority.IsFixture) return auth.Authority.FixtureEvidence("fixture.execution");
            var policy = auth.Matrix.Find(endpoint);
            return policy == null ? null : auth.Authority.Snapshot().Entries.FirstOrDefault(x => x.Evidence.Component == policy.EvidenceComponent)?.Evidence;
        }
        private static List<CanonicalPart> Expected(BuildPlan plan) => plan.Items.Where(x => x.Status != "REMOVE").Select(x => x.Status == "BLOCK" || x.Status == "REVIEW" ? x.Before : x.After ?? x.Before).Where(x => x != null).ToList();
        private static string SnapshotHash(List<CanonicalPart> parts) => JsonUtil.Hash((parts ?? new List<CanonicalPart>()).OrderBy(PartIdentity.Key, StringComparer.Ordinal).ThenBy(x => x.NativeId, StringComparer.Ordinal).Select(p => new { State = PartIdentity.PersistentHash(p), p.NativeId }).ToArray());
        private static RunResult Failure(string runId, string hash, string code) => new RunResult { RunId = runId, PlanHash = hash, Status = "BLOCKED_REVIEW_REQUIRED", Events = new List<string> { code } };
        private static RunResult FailedAudit(string runId, string hash, List<AuditIssue> issues) => new RunResult { RunId = runId, PlanHash = hash, Status = "BLOCKED_REVIEW_REQUIRED", Audit = new AuditResult { Status = "FAILED", Issues = issues }, Events = issues.Select(x => x.Code).ToList() };
        private static JournalEntry Entry(string kind, BuildPlan plan, RequestContext context, string fingerprint, PlanItem item = null, AdapterSnapshot snapshot = null, RunResult result = null)
        { return new JournalEntry { Kind = kind, RequestId = context.RequestId, RunId = context.RunId, OperationId = context.OperationId, PlanHash = plan.PlanHash, ContextHash = fingerprint, MatrixVersion = context.MatrixVersion, SourceRevision = plan.SourceRevision, ScopeHash = JsonUtil.Hash(plan.Scope), ModelKey = plan.Model.Key, Key = item?.Key, Before = JsonUtil.Clone(item?.Before), After = JsonUtil.Clone(item?.After), Snapshot = JsonUtil.Clone(snapshot), Result = JsonUtil.Clone(result) }; }
        private sealed class ReadbackFailureException : Exception
        { public RunResult Result { get; } public ReadbackFailureException(RunResult result) : base("READBACK_FAILED") { Result = result; } }
    }
}
