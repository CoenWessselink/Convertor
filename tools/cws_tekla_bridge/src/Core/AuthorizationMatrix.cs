using System;
using System.Collections.Generic;
using System.Linq;

namespace Cws.TeklaBridge.Core
{
    public sealed class EndpointPolicy
    {
        public string Endpoint { get; set; }
        public string Level { get; set; }
        public string Capability { get; set; }
        public bool Mutation { get; set; }
        public bool RequiresModel { get; set; }
        public bool RequiresEvidence { get; set; }
        public bool RequiresHumanConfirmation { get; set; }
        public bool RuntimeForbidden { get; set; }
        public string EvidenceComponent { get; set; }
        public List<string> Actors { get; set; } = new List<string>();
        public List<string> Modes { get; set; } = new List<string>();
        public List<string> Methods { get; set; } = new List<string>();
    }

    public sealed class AuthorizationMatrix
    {
        public const string CurrentVersion = "1.0.0";
        public string Version { get; private set; } = CurrentVersion;
        private readonly Dictionary<string, EndpointPolicy> policies;
        public static readonly string[] Actors = { "SYSTEM", "GPT", "CWS_ENGINE", "USER", "AUTHORIZED_REVIEWER", "ADMIN", "CODEX_DEV" };
        public static readonly string[] Modes = { "AUTO", "PROPOSE", "CHECK_ONLY" };
        public static readonly string[] Scopes = { "ALL", "SELECTION", "PHASE", "MARKS", "CHANGED", "REVIEW" };
        public AuthorizationMatrix()
        {
            policies = new Dictionary<string, EndpointPolicy>(StringComparer.Ordinal);
            Read("health", "bridge.health"); Read("capabilities", "bridge.capabilities"); Read("session", "bridge.session");
            Read("model/identity", "model.identity", true); Read("model/stats", "model.read", true);
            Read("selection", "selection.read", true); Read("selection/read", "selection.read", true);
            Ui("selection/set", "selection.set");
            foreach (var name in new[] { "profiles", "materials", "components", "shapes" }) Read("catalogs/" + name, "catalog." + name, true);
            foreach (var name in new[] { "objects", "parts", "assemblies" }) Read(name, "model.read", true);
            Read("geometry/summary", "geometry.read", true); Read("geometry/compare", "geometry.compare", true);
            Read("build-plan", "plan.create", true); Read("build-plan/validate", "plan.validate", true);
            Write("build-plan/execute", "plan.execute", "native.write");
            foreach (var name in new[] { "beam", "polybeam", "plate", "shape" }) Write(name + "/upsert", "part.upsert", "native." + name);
            Write("part/remove", "part.remove", "native.remove");
            foreach (var name in new[] { "cut", "fitting", "hole", "bolt", "weld" }) Write(name + "/upsert", "feature." + name, "native." + name);
            Write("uda/set", "uda.write", "native.uda");
            Read("connections/inspect", "connection.read", true); Read("connections/candidates", "connection.read", true);
            Read("connections/propose", "connection.read", true);
            Write("connections/apply", "connection.apply", "connection.family");
            Read("connections/validate", "connection.read", true);
            Write("connections/reconcile", "connection.reconcile", "connection.family");
            Write("transactions/begin", "transaction.write", "native.transaction");
            Write("transactions/commit", "transaction.write", "native.transaction");
            Read("transactions/journal", "journal.read");
            Write("save", "persist.save", "native.persistence"); Write("reopen", "persist.reopen", "native.persistence");
            Read("readback", "model.read", true); Write("self-heal", "repair.safe", "native.repair");
            Read("audit/final", "model.read", true); Read("runs", "runs.read"); Read("runs/events", "runs.read");
            Read("review/history", "review.read"); Proposal("review/propose", "review.propose");
            Human("review/resolve", "review.resolve", "L3", "project.resolution", new[] { "USER", "AUTHORIZED_REVIEWER" });
            Human("production/number", "production.number", "L4", "production.number", new[] { "AUTHORIZED_REVIEWER" });
            Human("production/nc", "production.nc", "L4", "production.nc", new[] { "AUTHORIZED_REVIEWER" });
            Proposal("authority/propose", "authority.propose"); Read("authority/manifest", "authority.read");
            Human("authority/promote", "authority.promote", "L5", "authority.governance", new[] { "ADMIN", "CODEX_DEV" });
            policies["authority/promote"].RuntimeForbidden = true;
            Read("authorization/matrix", "authorization.read");
        }
        public EndpointPolicy Find(string endpoint)
        {
            var normalized = NormalizeEndpoint(endpoint);
            return normalized != null && policies.TryGetValue(normalized, out var policy) ? JsonUtil.Clone(policy) : null;
        }
        public IReadOnlyList<EndpointPolicy> Endpoints => policies.Values.OrderBy(p => p.Endpoint, StringComparer.Ordinal).Select(JsonUtil.Clone).ToList().AsReadOnly();
        public object Export() => new { schemaVersion = "1.0", version = Version, defaultDeny = true, gates = new[] { "CAPABILITY", "ACTOR_AUTHORITY", "EVIDENCE_AUTHORITY", "RUN_MODE_AUTHORITY" }, endpoints = Endpoints };
        public static string NormalizeEndpoint(string endpoint)
        {
            if (String.IsNullOrEmpty(endpoint)) return null;
            if (endpoint.StartsWith("/api/v1/", StringComparison.Ordinal)) endpoint = endpoint.Substring(8);
            // Exact route matching: no percent decoding, dot segments, slashes or case aliases.
            return endpoint.Length > 0 && endpoint[0] != '/' && endpoint.IndexOf('?') < 0 && endpoint.IndexOf('#') < 0 ? endpoint : null;
        }
        private void Add(EndpointPolicy policy)
        {
            if (policies.ContainsKey(policy.Endpoint)) throw new InvalidOperationException("Duplicate matrix endpoint.");
            bool post = policy.Mutation || policy.Endpoint == "build-plan" || policy.Endpoint == "build-plan/validate" ||
                policy.Endpoint == "readback" || policy.Endpoint == "geometry/compare" || policy.Endpoint.EndsWith("/propose", StringComparison.Ordinal);
            policy.Methods = new List<string> { post ? "POST" : "GET" };
            policies.Add(policy.Endpoint, policy);
        }
        private void Read(string endpoint, string capability, bool model = false) => Add(new EndpointPolicy
        { Endpoint = endpoint, Level = "L0", Capability = capability, RequiresModel = model, Actors = Actors.Where(a => a != "CODEX_DEV").ToList(), Modes = Modes.ToList() });
        private void Ui(string endpoint, string capability) => Add(new EndpointPolicy
        { Endpoint = endpoint, Level = "L1", Capability = capability, Mutation = true, RequiresModel = true, Actors = Actors.Where(a => a != "CODEX_DEV").ToList(), Modes = Modes.ToList() });
        private void Proposal(string endpoint, string capability) => Add(new EndpointPolicy
        { Endpoint = endpoint, Level = "L1", Capability = capability, Actors = Actors.Where(a => a != "CODEX_DEV").ToList(), Modes = new List<string> { "AUTO", "PROPOSE" } });
        private void Write(string endpoint, string capability, string evidence) => Add(new EndpointPolicy
        { Endpoint = endpoint, Level = "L2", Capability = capability, Mutation = true, RequiresModel = true, RequiresEvidence = true, EvidenceComponent = evidence, Actors = Actors.Where(a => a != "CODEX_DEV").ToList(), Modes = new List<string> { "AUTO" } });
        private void Human(string endpoint, string capability, string level, string evidence, IEnumerable<string> actors) => Add(new EndpointPolicy
        { Endpoint = endpoint, Level = level, Capability = capability, Mutation = true, RequiresModel = true, RequiresEvidence = true, RequiresHumanConfirmation = true, EvidenceComponent = evidence, Actors = actors.ToList(), Modes = new List<string> { "AUTO" } });
    }
}
