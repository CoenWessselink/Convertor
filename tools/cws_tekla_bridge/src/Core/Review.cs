using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using Newtonsoft.Json;

namespace Cws.TeklaBridge.Core
{
    public sealed class ReviewProposal
    {
        public string ProposalId { get; set; }
        public ModelIdentity Model { get; set; }
        public ScopeSpec Scope { get; set; }
        public string SourceId { get; set; }
        public string SourceRevision { get; set; }
        public string CanonicalId { get; set; }
        public string PhysicalRole { get; set; }
        public string Field { get; set; }
        public string OldValue { get; set; }
        public string NewValue { get; set; }
        public string Actor { get; set; }
        public string Reason { get; set; }
        public List<string> EvidenceIds { get; set; } = new List<string>();
        public string OperationHash { get; set; }
        public string Status { get; set; } = "PROPOSED";
        public DateTime CreatedUtc { get; set; }
    }

    public sealed class ReviewResolution
    {
        public string ResolutionId { get; set; }
        public string ProposalId { get; set; }
        public ModelIdentity Model { get; set; }
        public ScopeSpec Scope { get; set; }
        public string SourceId { get; set; }
        public string SourceRevision { get; set; }
        public string CanonicalId { get; set; }
        public string PhysicalRole { get; set; }
        public string Field { get; set; }
        public string OldValue { get; set; }
        public string NewValue { get; set; }
        public string Actor { get; set; }
        public string Reason { get; set; }
        public List<string> EvidenceIds { get; set; } = new List<string>();
        public string OperationHash { get; set; }
        public string Status { get; set; } = "PROJECT_CONFIRMED";
        public DateTime ConfirmedUtc { get; set; }
        public List<string> Invalidations { get; set; } = new List<string>();
    }

    public sealed class ReviewChallenge
    {
        public string Token { get; set; }
        public string ProposalId { get; set; }
        public string BindingHash { get; set; }
        public DateTime ExpiresUtc { get; set; }
    }

    internal sealed class StoredChallenge
    {
        public string TokenHash { get; set; }
        public string ProposalId { get; set; }
        public string BindingHash { get; set; }
        public string Actor { get; set; }
        public string ModelKey { get; set; }
        public string SourceRevision { get; set; }
        public DateTime ExpiresUtc { get; set; }
        public DateTime? ConsumedUtc { get; set; }
        public string Status { get; set; } = "ISSUED";
    }

    public sealed class ReviewHistory
    {
        public int SchemaVersion { get; set; } = 1;
        public List<ReviewProposal> Proposals { get; set; } = new List<ReviewProposal>();
        public List<ReviewResolution> Resolutions { get; set; } = new List<ReviewResolution>();
        internal List<StoredChallenge> Challenges { get; set; } = new List<StoredChallenge>();
    }

    internal sealed class ReviewDatabase
    {
        public int SchemaVersion { get; set; } = 1;
        public List<ReviewProposal> Proposals { get; set; } = new List<ReviewProposal>();
        public List<ReviewResolution> Resolutions { get; set; } = new List<ReviewResolution>();
        public List<StoredChallenge> Challenges { get; set; } = new List<StoredChallenge>();
    }

    // The store serializes each read-modify-write while retaining a file lease. A
    // process crash before replacement leaves the prior complete database intact.
    public sealed class ReviewStore
    {
        private readonly string path;
        private readonly string leasePath;
        public ReviewStore(string directory)
        {
            if (string.IsNullOrWhiteSpace(directory)) throw new ArgumentException("Review directory required.");
            Directory.CreateDirectory(directory);
            path = Path.Combine(directory, "review-store.json");
            leasePath = Path.Combine(directory, "review-store.lock");
        }
        internal T Update<T>(Func<ReviewDatabase, T> update)
        {
            using (var lease = new FileStream(leasePath, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None))
            {
                var db = File.Exists(path) ? JsonConvert.DeserializeObject<ReviewDatabase>(File.ReadAllText(path)) : new ReviewDatabase();
                if (db == null || db.SchemaVersion != 1 || db.Proposals == null || db.Resolutions == null || db.Challenges == null)
                    throw new InvalidDataException("Corrupt or unsupported review store; fail closed.");
                T result = update(db);
                string temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
                try
                {
                    using (var f = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                    using (var w = new StreamWriter(f))
                    {
                        w.Write(JsonConvert.SerializeObject(db, Formatting.Indented));
                        w.Flush(); f.Flush(true);
                    }
                    if (File.Exists(path)) File.Replace(temporary, path, null);
                    else File.Move(temporary, path);
                }
                finally { if (File.Exists(temporary)) File.Delete(temporary); }
                return result;
            }
        }
        public ReviewHistory History()
        {
            return Update(db => new ReviewHistory
            {
                Proposals = JsonUtil.Clone(db.Proposals),
                Resolutions = JsonUtil.Clone(db.Resolutions)
            });
        }
    }

    public sealed class ReviewService
    {
        private readonly ReviewStore store;
        private readonly Func<DateTime> utcNow;
        private static readonly HashSet<string> Fields = new HashSet<string>(StringComparer.Ordinal)
        { "Material", "Profile", "GeometryHash", "ManufacturingHash", "Phase", "Mark" };

        public ReviewService(ReviewStore store, Func<DateTime> utcNow = null)
        {
            this.store = store ?? throw new ArgumentNullException(nameof(store));
            this.utcNow = utcNow ?? (() => DateTime.UtcNow);
        }
        public ReviewHistory History() => store.History();
        public ReviewProposal Propose(ReviewProposal proposal)
        {
            ValidateProposal(proposal);
            var frozen = JsonUtil.Clone(proposal);
            frozen.ProposalId = Guid.NewGuid().ToString("N");
            frozen.Status = "PROPOSED";
            frozen.CreatedUtc = utcNow();
            frozen.OperationHash = ProposalHash(frozen);
            return store.Update(db => { db.Proposals.Add(frozen); return JsonUtil.Clone(frozen); });
        }
        // This facade is handed only to the in-process WinForms event handlers.
        // It is intentionally absent from API dispatch and serialized DTOs.
        public TrustedReviewUi CreateTrustedLocalUi(string humanActor)
        {
            if (humanActor != "USER" && humanActor != "AUTHORIZED_REVIEWER")
                throw new UnauthorizedAccessException("Human UI actor must be USER or AUTHORIZED_REVIEWER.");
            return new TrustedReviewUi(this, humanActor);
        }
        internal ReviewChallenge IssueLocalChallenge(string proposalId, string actor, ModelIdentity currentModel,
            ScopeSpec currentScope, string currentSourceRevision, TimeSpan lifetime)
        {
            if (lifetime <= TimeSpan.Zero || lifetime > TimeSpan.FromMinutes(5))
                throw new ArgumentOutOfRangeException(nameof(lifetime), "Human challenge lifetime must be <= five minutes.");
            string token;
            using (var rng = RandomNumberGenerator.Create())
            {
                byte[] bytes = new byte[32]; rng.GetBytes(bytes); token = Convert.ToBase64String(bytes);
            }
            return store.Update(db =>
            {
                var p = FindProposal(db, proposalId);
                EnsureCurrent(p, currentModel, currentScope, currentSourceRevision);
                var c = new StoredChallenge
                {
                    TokenHash = JsonUtil.HashText(token), ProposalId = p.ProposalId, Actor = actor,
                    BindingHash = BindingHash(p, actor), ModelKey = p.Model.Key, SourceRevision = p.SourceRevision, ExpiresUtc = utcNow().Add(lifetime)
                };
                db.Challenges.Add(c);
                return new ReviewChallenge { Token = token, ProposalId = p.ProposalId, BindingHash = c.BindingHash, ExpiresUtc = c.ExpiresUtc };
            });
        }
        internal ReviewResolution ConfirmLocal(string proposalId, string token, string actor,
            ModelIdentity currentModel, ScopeSpec currentScope, string currentSourceRevision,
            string reason, IEnumerable<string> evidenceIds)
        {
            if (string.IsNullOrWhiteSpace(token) || string.IsNullOrWhiteSpace(reason))
                throw new UnauthorizedAccessException("A challenge token and decision reason are required.");
            var evidence = (evidenceIds ?? Enumerable.Empty<string>()).Where(s => !string.IsNullOrWhiteSpace(s)).Distinct().ToList();
            if (evidence.Count == 0) throw new UnauthorizedAccessException("A project resolution requires explicit evidence.");
            return store.Update(db =>
            {
                var p = FindProposal(db, proposalId);
                EnsureCurrent(p, currentModel, currentScope, currentSourceRevision);
                var tokenHash = JsonUtil.HashText(token);
                var c = db.Challenges.SingleOrDefault(x => x.TokenHash == tokenHash && x.ProposalId == proposalId);
                if (c == null || c.Status != "ISSUED" || c.ConsumedUtc.HasValue || c.ExpiresUtc <= utcNow()
                    || c.Actor != actor || c.BindingHash != BindingHash(p, actor))
                    throw new UnauthorizedAccessException("Expired, consumed, stale or mismatched human challenge.");
                var result = new ReviewResolution
                {
                    ResolutionId = Guid.NewGuid().ToString("N"), ProposalId = proposalId,
                    Model = JsonUtil.Clone(p.Model), Scope = JsonUtil.Clone(p.Scope),
                    SourceId = p.SourceId, SourceRevision = p.SourceRevision, CanonicalId = p.CanonicalId,
                    PhysicalRole = p.PhysicalRole, Field = p.Field, OldValue = p.OldValue, NewValue = p.NewValue,
                    Actor = actor, Reason = reason, EvidenceIds = evidence, OperationHash = p.OperationHash,
                    ConfirmedUtc = utcNow(),
                    Invalidations = new List<string> { "BUILD_PLAN", "READBACK", "FINAL_AUDIT", "CONNECTION_FINGERPRINT" }
                };
                c.ConsumedUtc = result.ConfirmedUtc; c.Status = "CONSUMED";
                p.Status = "PROJECT_CONFIRMED"; db.Resolutions.Add(result);
                return JsonUtil.Clone(result);
            });
        }
        internal ReviewChallenge IssueOperationChallenge(string endpoint, RequestContext context, string actor, TimeSpan lifetime)
        {
            if (lifetime <= TimeSpan.Zero || lifetime > TimeSpan.FromMinutes(5)) throw new ArgumentOutOfRangeException(nameof(lifetime));
            if (!TrustedOperation(context, actor) || string.IsNullOrWhiteSpace(endpoint))
                throw new UnauthorizedAccessException("Only trusted local human UI may issue operation confirmations.");
            string token;
            using (var rng = RandomNumberGenerator.Create()) { byte[] bytes = new byte[32]; rng.GetBytes(bytes); token = Convert.ToBase64String(bytes); }
            var challenge = new StoredChallenge { TokenHash = JsonUtil.HashText(token), Actor = actor,
                ModelKey = context.ExpectedModel.Key, SourceRevision = context.SourceRevision,
                BindingHash = OperationBinding(endpoint, context), ExpiresUtc = utcNow().Add(lifetime) };
            return store.Update(db => { db.Challenges.Add(challenge); return new ReviewChallenge
                { Token = token, BindingHash = challenge.BindingHash, ExpiresUtc = challenge.ExpiresUtc }; });
        }
        // AuthorizationService calls this only after all other gates pass. The
        // persisted consume is atomic: retries/restarts cannot replay approval.
        public bool ConsumeOperationConfirmation(string endpoint, RequestContext context)
        {
            if (context == null || !TrustedOperation(context, context.Actor) || string.IsNullOrWhiteSpace(context.ConfirmationToken)) return false;
            return store.Update(db =>
            {
                var hash = JsonUtil.HashText(context.ConfirmationToken);
                var c = db.Challenges.SingleOrDefault(x => x.TokenHash == hash && x.ProposalId == null);
                if (c == null || c.Status != "ISSUED" || c.ConsumedUtc.HasValue || c.ExpiresUtc <= utcNow()
                    || c.Actor != context.Actor || c.BindingHash != OperationBinding(endpoint, context)) return false;
                c.Status = "CONSUMED"; c.ConsumedUtc = utcNow(); return true;
            });
        }
        private static bool TrustedOperation(RequestContext c, string actor) => c != null && c.Principal != null
            && c.Principal.IsHuman && c.Principal.Actor == actor && c.Actor == actor && !string.IsNullOrWhiteSpace(c.SessionId)
            && c.Principal.SessionId == c.SessionId && c.ExpectedModel != null && c.ExpectedModel.IsComplete
            && c.Scope != null && !string.IsNullOrWhiteSpace(c.SourceRevision) && !string.IsNullOrWhiteSpace(c.PlanHash)
            && !string.IsNullOrWhiteSpace(c.OperationId) && !string.IsNullOrWhiteSpace(c.RunId) && !string.IsNullOrWhiteSpace(c.RequestId);
        private static string OperationBinding(string endpoint, RequestContext c) => JsonUtil.Hash(new
        { Endpoint = endpoint != null && endpoint.StartsWith("/api/v1/", StringComparison.Ordinal) ? endpoint.Substring(8) : endpoint,
            c.ExpectedModel, ScopeHash = JsonUtil.Hash(c.Scope), c.SourceRevision, c.Actor, c.SessionId,
            PrincipalIdentity = c.Principal.Identity, c.PlanHash, c.OperationId, c.RunId, c.RequestId, c.Mode, c.DryRun });
        public int SupersedeSource(ModelIdentity model, string sourceId, string currentSourceRevision)
        {
            if (model == null || string.IsNullOrWhiteSpace(sourceId) || string.IsNullOrWhiteSpace(currentSourceRevision))
                throw new ArgumentException("Model and current source identity are required.");
            return store.Update(db =>
            {
                int changed = 0;
                foreach (var p in db.Proposals.Where(p => SameModel(p.Model, model, false) && p.SourceId == sourceId
                    && p.SourceRevision != currentSourceRevision && p.Status != "SUPERSEDED"))
                { p.Status = "SUPERSEDED"; changed++; }
                foreach (var r in db.Resolutions.Where(r => SameModel(r.Model, model, false) && r.SourceId == sourceId
                    && r.SourceRevision != currentSourceRevision)) r.Status = "SUPERSEDED";
                foreach (var c in db.Challenges.Where(c => db.Proposals.Any(p => p.ProposalId == c.ProposalId && p.Status == "SUPERSEDED")))
                    if (c.Status == "ISSUED") c.Status = "SUPERSEDED";
                foreach (var c in db.Challenges.Where(c => c.ModelKey == model.Key && c.SourceRevision != currentSourceRevision && c.Status == "ISSUED"))
                    c.Status = "SUPERSEDED";
                return changed;
            });
        }
        // Applying a confirmed project resolution requires an exact occurrence,
        // current value and current model/scope/revision. It never updates any
        // manifest, alias table, sibling occurrence, or global authority.
        public CanonicalPart ApplyProjectResolution(string resolutionId, CanonicalPart part,
            ModelIdentity model, ScopeSpec scope, string sourceRevision)
        {
            if (part == null) throw new ArgumentNullException(nameof(part));
            if (scope != null && ((scope.Kind == "PHASE" && (scope.Values == null || !scope.Values.Contains(part.Phase)))
                || (scope.Kind == "MARKS" && (scope.Values == null || !scope.Values.Contains(part.Mark)))))
                throw new UnauthorizedAccessException("Occurrence is outside the reviewed phase or marks scope.");
            return store.Update(db =>
            {
                var r = db.Resolutions.SingleOrDefault(x => x.ResolutionId == resolutionId);
                if (r == null || r.Status != "PROJECT_CONFIRMED" || !SameModel(r.Model, model, true)
                    || JsonUtil.Hash(r.Scope) != JsonUtil.Hash(scope) || r.SourceRevision != sourceRevision
                    || part.SourceId != r.SourceId || part.SourceRevision != r.SourceRevision
                    || part.CanonicalId != r.CanonicalId || part.PhysicalRole != r.PhysicalRole)
                    throw new UnauthorizedAccessException("Project resolution does not authorize this occurrence/model/revision/scope.");
                var updated = JsonUtil.Clone(part);
                string before = ReadField(updated, r.Field);
                if (before != r.OldValue) throw new InvalidOperationException("Current field no longer matches reviewed old value.");
                WriteField(updated, r.Field, r.NewValue);
                if (updated.Udas == null) updated.Udas = new Dictionary<string, string>();
                updated.Udas["CWS_PROJECT_RESOLUTION"] = r.ResolutionId;
                return updated;
            });
        }
        private static string ReadField(CanonicalPart p, string f)
        {
            switch (f) { case "Material": return p.Material; case "Profile": return p.Profile;
                case "GeometryHash": return p.GeometryHash; case "ManufacturingHash": return p.ManufacturingHash;
                case "Phase": return p.Phase; case "Mark": return p.Mark; default: throw new InvalidOperationException("Unsupported field."); }
        }
        private static void WriteField(CanonicalPart p, string f, string v)
        {
            switch (f) { case "Material": p.Material = v; p.MaterialAuthority = null; break;
                case "Profile": p.Profile = v; p.ProfileAuthority = null; break;
                case "GeometryHash": p.GeometryHash = v; p.GeometryAuthority = null; break;
                case "ManufacturingHash": p.ManufacturingHash = v; break; case "Phase": p.Phase = v; break;
                case "Mark": p.Mark = v; break; default: throw new InvalidOperationException("Unsupported field."); }
        }
        private static void ValidateProposal(ReviewProposal p)
        {
            if (p == null || p.Model == null || p.Scope == null || string.IsNullOrWhiteSpace(p.SourceId)
                || string.IsNullOrWhiteSpace(p.SourceRevision) || string.IsNullOrWhiteSpace(p.CanonicalId)
                || string.IsNullOrWhiteSpace(p.PhysicalRole) || !Fields.Contains(p.Field ?? "")
                || p.OldValue == p.NewValue || string.IsNullOrWhiteSpace(p.NewValue)
                || string.IsNullOrWhiteSpace(p.Actor) || string.IsNullOrWhiteSpace(p.Reason))
                throw new ArgumentException("Review proposal requires explicit occurrence, scope, source, field, old/new and reason.");
            if (string.IsNullOrWhiteSpace(p.Model.ModelId) || string.IsNullOrWhiteSpace(p.Model.ModelPath)
                || string.IsNullOrWhiteSpace(p.Model.TeklaVersion) || string.IsNullOrWhiteSpace(p.Model.Revision))
                throw new ArgumentException("Review model identity must include id/path/version/revision.");
        }
        private static ReviewProposal FindProposal(ReviewDatabase db, string id)
        {
            var p = db.Proposals.SingleOrDefault(x => x.ProposalId == id);
            if (p == null || p.Status != "PROPOSED") throw new UnauthorizedAccessException("Proposal is missing, confirmed or superseded.");
            if (p.OperationHash != ProposalHash(p)) throw new UnauthorizedAccessException("Reviewed operation has changed.");
            return p;
        }
        private static void EnsureCurrent(ReviewProposal p, ModelIdentity model, ScopeSpec scope, string sourceRevision)
        {
            if (!SameModel(p.Model, model, true) || scope == null || JsonUtil.Hash(p.Scope) != JsonUtil.Hash(scope)
                || p.SourceRevision != sourceRevision) throw new UnauthorizedAccessException("Stale model, scope or source revision.");
        }
        private static bool SameModel(ModelIdentity a, ModelIdentity b, bool revision)
        {
            return a != null && b != null && a.ModelId == b.ModelId && a.ModelPath == b.ModelPath && a.ModelName == b.ModelName
                && a.TeklaVersion == b.TeklaVersion && (!revision || a.Revision == b.Revision);
        }
        private static string ProposalHash(ReviewProposal p) => JsonUtil.Hash(new
        { p.Model, p.Scope, p.SourceId, p.SourceRevision, p.CanonicalId, p.PhysicalRole, p.Field, p.OldValue, p.NewValue, p.Reason, p.EvidenceIds });
        private static string BindingHash(ReviewProposal p, string actor) => JsonUtil.Hash(new
        { p.Model, ScopeHash = JsonUtil.Hash(p.Scope), p.SourceId, p.SourceRevision, Actor = actor, p.OperationHash });
    }

    public sealed class TrustedReviewUi
    {
        private readonly ReviewService service;
        private readonly string actor;
        internal TrustedReviewUi(ReviewService service, string actor) { this.service = service; this.actor = actor; }
        public ReviewChallenge CreateChallenge(string proposalId, ModelIdentity model, ScopeSpec scope,
            string sourceRevision, TimeSpan? lifetime = null)
            => service.IssueLocalChallenge(proposalId, actor, model, scope, sourceRevision, lifetime ?? TimeSpan.FromMinutes(2));
        public ReviewChallenge CreateOperationChallenge(string endpoint, RequestContext context, TimeSpan? lifetime = null)
            => service.IssueOperationChallenge(endpoint, context, actor, lifetime ?? TimeSpan.FromMinutes(2));
        public ReviewResolution Confirm(string proposalId, string token, ModelIdentity model, ScopeSpec scope,
            string sourceRevision, string reason, IEnumerable<string> evidenceIds)
            => service.ConfirmLocal(proposalId, token, actor, model, scope, sourceRevision, reason, evidenceIds);
    }
}
