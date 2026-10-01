using System;
using System.Collections.Generic;
using System.Linq;

namespace Cws.TeklaBridge.Core
{
    public sealed class TrustedPrincipal
    {
        public string Identity { get; }
        public string Actor { get; }
        public string SessionId { get; }
        public bool IsHuman { get; }
        public bool Engineering { get; }
        public bool Production { get; }
        public bool Governance { get; }
        private TrustedPrincipal(string identity, string actor, string session, bool human, bool engineering, bool production, bool governance)
        { Identity = identity; Actor = actor; SessionId = session; IsHuman = human; Engineering = engineering; Production = production; Governance = governance; }
        public static TrustedPrincipal ForAutomation(string actor, string sessionId)
        {
            if (actor != "GPT" && actor != "SYSTEM" && actor != "CWS_ENGINE") throw new ArgumentException("Automation role is not a human identity.");
            if (String.IsNullOrWhiteSpace(sessionId)) throw new ArgumentException("Session identity is required.");
            return new TrustedPrincipal(actor, actor, sessionId, false, false, false, false);
        }
        // This factory is for the in-process, trusted local UI. No HTTP handler exposes it.
        public static TrustedPrincipal FromLocalHuman(string identity, string actor, string sessionId, bool engineering = false, bool production = false, bool governance = false)
        {
            if (!new[] { "USER", "AUTHORIZED_REVIEWER", "ADMIN", "CODEX_DEV" }.Contains(actor, StringComparer.Ordinal)) throw new ArgumentException("Unknown local role.");
            if (String.IsNullOrWhiteSpace(identity) || String.IsNullOrWhiteSpace(sessionId)) throw new ArgumentException("Human and session identity are required.");
            return new TrustedPrincipal(identity, actor, sessionId, true, engineering, production, governance);
        }
    }

    public sealed class AuthorizationDecision
    {
        public bool Allowed { get; set; }
        public string Code { get; set; }
        public string Reason { get; set; }
        public string Gate { get; set; }
        public string MatrixVersion { get; set; }
    }

    public sealed class AuthorizationService
    {
        public AuthorizationMatrix Matrix { get; }
        public AuthorityService Authority { get; }
        public Func<string, RequestContext, bool> ConfirmationValidator { get; set; }
        public AuthorizationService(AuthorizationMatrix matrix = null, AuthorityService authority = null)
        { Matrix = matrix ?? new AuthorizationMatrix(); Authority = authority ?? new AuthorityService(); }

        public AuthorizationDecision Authorize(string endpoint, RequestContext context, CapabilitySet capabilities, EvidenceRecord evidence = null)
        {
            var policy = Matrix.Find(endpoint);
            if (policy == null) return Deny("CAPABILITY", "ENDPOINT_NOT_MATRIXED", "The exact endpoint has no versioned authorization policy.");
            if (context == null) return Deny("ACTOR_AUTHORITY", "CONTEXT_REQUIRED", "A request context is required.");
            context.MatrixVersion = Matrix.Version;
            if (capabilities == null || !capabilities.Supports(policy.Capability)) return Deny("CAPABILITY", "CAPABILITY_NOT_SUPPORTED", "Required capability is unavailable: " + policy.Capability);
            if (!AuthorizationMatrix.Actors.Contains(context.Actor, StringComparer.Ordinal)) return Deny("ACTOR_AUTHORITY", "ACTOR_UNKNOWN", "Unknown actor.");
            if (!policy.Actors.Contains(context.Actor, StringComparer.Ordinal)) return Deny("ACTOR_AUTHORITY", "ACTOR_DENIED", "Actor lacks authority for this level.");
            var principal = context.Principal;
            if (principal != null && (!String.Equals(principal.Actor, context.Actor, StringComparison.Ordinal) || !String.Equals(principal.SessionId, context.SessionId, StringComparison.Ordinal)))
                return Deny("ACTOR_AUTHORITY", "PRINCIPAL_MISMATCH", "Actor and session do not match authenticated claims.");
            if (policy.Level == "L3" || policy.Level == "L4" || policy.Level == "L5")
            {
                if (principal == null || !principal.IsHuman) return Deny("ACTOR_AUTHORITY", "TRUSTED_HUMAN_REQUIRED", "A trusted local human identity is required; caller Actor is not proof.");
                if (policy.Level == "L3" && !principal.Engineering) return Deny("ACTOR_AUTHORITY", "ENGINEERING_AUTHORITY_REQUIRED", "Engineering review authority is required.");
                if (policy.Level == "L4" && !principal.Production) return Deny("ACTOR_AUTHORITY", "PRODUCTION_AUTHORITY_REQUIRED", "Production authority is required.");
                if (policy.Level == "L5" && !principal.Governance) return Deny("ACTOR_AUTHORITY", "GOVERNANCE_AUTHORITY_REQUIRED", "Governance authority is required.");
            }
            if (policy.RuntimeForbidden) return Deny("EVIDENCE_AUTHORITY", "AUTHORITY_RUNTIME_READ_ONLY", "Authority promotion is a versioned development workflow; the runtime manifest is immutable.");
            if (policy.RequiresEvidence && !Authority.IsApproved(evidence, policy.EvidenceComponent))
                return Deny("EVIDENCE_AUTHORITY", "EVIDENCE_NOT_APPROVED", "Evidence is absent, mismatched or unsupported by the immutable authority manifest.");
            if (!AuthorizationMatrix.Modes.Contains(context.Mode, StringComparer.Ordinal)) return Deny("RUN_MODE_AUTHORITY", "MODE_UNKNOWN", "Unknown execution mode.");
            if (context.Scope == null || !AuthorizationMatrix.Scopes.Contains(context.Scope.Kind, StringComparer.Ordinal) || context.Scope.Values == null || context.Scope.Values.Any(String.IsNullOrWhiteSpace))
                return Deny("RUN_MODE_AUTHORITY", "SCOPE_INVALID", "Scope kind or values are invalid.");
            if (context.Scope.Kind != "ALL" && context.Scope.Kind != "SELECTION" && context.Scope.Kind != "CHANGED" && context.Scope.Kind != "REVIEW" && context.Scope.Values.Count == 0)
                return Deny("RUN_MODE_AUTHORITY", "SCOPE_EMPTY", "A phase or marks scope requires explicit values.");
            if (!policy.Modes.Contains(context.Mode, StringComparer.Ordinal)) return Deny("RUN_MODE_AUTHORITY", "MODE_DENIED", "The mode does not permit this endpoint.");
            if (policy.RequiresModel && (context.ExpectedModel == null || !context.ExpectedModel.IsComplete)) return Deny("RUN_MODE_AUTHORITY", "MODEL_IDENTITY_REQUIRED", "Complete expected model identity is required.");
            if (policy.Mutation && (String.IsNullOrWhiteSpace(context.RequestId) || String.IsNullOrWhiteSpace(context.RunId) || String.IsNullOrWhiteSpace(context.OperationId)))
                return Deny("RUN_MODE_AUTHORITY", "OPERATION_IDENTITY_REQUIRED", "Mutation requires request, run and operation IDs.");
            if (policy.Mutation && context.DryRun) return Deny("RUN_MODE_AUTHORITY", "RUN_DRY_RUN", "Dry-run requests cannot mutate.");
            if (policy.Level != "L0" && policy.Level != "L1" && String.IsNullOrWhiteSpace(context.SourceRevision)) return Deny("RUN_MODE_AUTHORITY", "SOURCE_REVISION_REQUIRED", "Source revision is required.");
            if (policy.RequiresHumanConfirmation && (String.IsNullOrWhiteSpace(context.ConfirmationToken) || ConfirmationValidator == null || !ConfirmationValidator(policy.Endpoint, context)))
                return Deny("RUN_MODE_AUTHORITY", "HUMAN_CONFIRMATION_REQUIRED", "A valid, bound, short-lived local confirmation is required.");
            return new AuthorizationDecision { Allowed = true, Code = "AUTHORIZED", Reason = "All four gates passed.", Gate = "COMPLETE", MatrixVersion = Matrix.Version };
        }
        private AuthorizationDecision Deny(string gate, string code, string reason) => new AuthorizationDecision { Allowed = false, Gate = gate, Code = code, Reason = reason, MatrixVersion = Matrix.Version };
    }
}
