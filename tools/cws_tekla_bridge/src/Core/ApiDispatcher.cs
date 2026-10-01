using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace Cws.TeklaBridge.Core
{
    /// <summary>The HTTP entry point always attaches an automation principal. JSON actor or human-token claims cannot elevate it.</summary>
    public sealed class ApiDispatcher
    {
        private readonly IModelAdapter adapter;
        private readonly AuthorizationService auth;
        private readonly JournalStore journal;
        private readonly Dictionary<string, BuildPlan> plans = new Dictionary<string, BuildPlan>(StringComparer.Ordinal);
        private readonly string sessionId = Guid.NewGuid().ToString("N");
        private readonly object sync = new object();
        public IModelAdapter Adapter { get { return adapter; } }
        public string AuthorityManifestJson { get; set; } = "{}";
        public ReviewService Review { get; set; }
        /// <summary>Host supplies a UI-thread invocation. It serializes all calls into the native API thread.</summary>
        public Func<Func<ApiResponse>, Task<ApiResponse>> InvokeOnModelThread { get; set; }
        public Action<string> AuditMessage { get; set; }
        public ApiDispatcher(IModelAdapter adapter, AuthorizationService auth, JournalStore journal)
        { this.adapter = adapter ?? throw new ArgumentNullException(nameof(adapter)); this.auth = auth ?? throw new ArgumentNullException(nameof(auth)); this.journal = journal ?? throw new ArgumentNullException(nameof(journal)); }
        public Task<ApiResponse> HandleNetwork(ApiRequest request)
        {
            if (InvokeOnModelThread != null) return InvokeOnModelThread(() => Dispatch(request, TrustedPrincipal.ForAutomation("GPT", sessionId), true));
            return Task.FromResult(Dispatch(request, TrustedPrincipal.ForAutomation("GPT", sessionId), true));
        }
        // This entry point is used only by trusted desktop code, never selected by any HTTP body, path or header.
        public ApiResponse HandleLocal(ApiRequest request, TrustedPrincipal localPrincipal)
        { return Dispatch(request, localPrincipal, false); }
        private ApiResponse Dispatch(ApiRequest request, TrustedPrincipal principal, bool network)
        {
            lock (sync)
            {
                try
                {
                    JObject body = ParseBody(request.Body);
                    var context = body["Context"] != null ? JsonUtil.Deserialize<RequestContext>(body["Context"].ToString(Formatting.None)) : new RequestContext();
                    if (network && !String.IsNullOrWhiteSpace(context.Actor) && context.Actor != "GPT") return ApiResponse.Error(403, "PRINCIPAL_MISMATCH", "De HTTP-sessie heeft uitsluitend GPT-bevoegdheden.");
                    if (network && !String.IsNullOrWhiteSpace(context.ConfirmationToken)) return ApiResponse.Error(403, "HUMAN_CONFIRMATION_LOCAL_ONLY", "Menselijke bevestiging kan uitsluitend in de lokale review-interface.");
                    context.Actor = network ? "GPT" : principal.Actor;
                    context.Principal = principal; context.SessionId = principal.SessionId;
                    if (String.IsNullOrWhiteSpace(context.RequestId)) context.RequestId = request.RequestId ?? Guid.NewGuid().ToString("N");
                    string route = request.Path.StartsWith("/api/v1/", StringComparison.Ordinal) ? request.Path.Substring(8) : "";
                    string endpoint = route == "selection" ? (request.Method == "GET" ? "selection/read" : "selection/set") : route;
                    var policy = auth.Matrix.Find(endpoint);
                    if (policy != null && !policy.Methods.Contains(request.Method, StringComparer.Ordinal)) return ApiResponse.Error(405, "METHOD_NOT_ALLOWED", "HTTP-methode niet toegestaan voor dit endpoint.");
                    var capabilities = EffectiveCapabilities();
                    if (request.Method == "GET" && policy?.RequiresModel == true && capabilities.Supports(policy.Capability)) context.ExpectedModel = adapter.GetIdentity();
                    var evidence = policy?.RequiresEvidence == true ? auth.Authority.Snapshot().Entries.FirstOrDefault(x => x.Evidence?.Component == policy.EvidenceComponent)?.Evidence : null;
                    var decision = auth.Authorize(endpoint, context, capabilities, evidence);
                    if (!decision.Allowed) return ApiResponse.Error(403, decision.Code, decision.Reason);
                    if (AuditMessage != null) AuditMessage("API " + request.Method + " " + route + " actor=" + context.Actor);
                    if (request.Method == "POST" && IsModelOperation(route))
                    {
                        if (context.ExpectedModel == null || !context.ExpectedModel.ExactlyEquals(adapter.GetIdentity())) return ApiResponse.Error(409, "MODEL_IDENTITY_MISMATCH", "Het verwachte model of de modelrevisie komt niet overeen.");
                    }
                    switch (route)
                    {
                        case "health": return ApiResponse.Ok(new { ok = true, transport = "LOOPBACK_TOKEN", adapter = adapter.AdapterName, nativeRuntime = !adapter.IsFixture && adapter.Capabilities.Supports("model.read"), fixture = adapter.IsFixture, released = false });
                        case "capabilities": return ApiResponse.Ok(new { ok = true, capabilities = EffectiveCapabilities(), nativeCapabilities = adapter.Capabilities, fixture = adapter.IsFixture });
                        case "session": return ApiResponse.Ok(new { ok = true, sessionId, actor = "GPT", humanConfirmation = "LOCAL_UI_ONLY", tokenStorage = "MEMORY_ONLY" });
                        case "authorization/matrix": return ApiResponse.Ok(new { ok = true, matrix = auth.Matrix.Export() });
                        case "authority/manifest": return ApiResponse.Ok(new { ok = true, manifest = auth.Authority.Snapshot(), mutable = false });
                        case "model/identity": return ApiResponse.Ok(new { ok = true, model = adapter.GetIdentity(), fixture = adapter.IsFixture });
                        case "model/stats":
                            var actual = adapter.ReadParts(); return ApiResponse.Ok(new { ok = true, physicalCount = actual.Count, canonicalCount = actual.Select(x => x.CanonicalId).Where(x => !String.IsNullOrWhiteSpace(x)).Distinct(StringComparer.Ordinal).Count(), fixture = adapter.IsFixture });
                        case "selection":
                            if (request.Method == "GET") return ApiResponse.Ok(new { ok = true, ids = adapter.GetSelection() });
                            var ids = (body["Ids"] == null ? null : JsonUtil.Deserialize<List<string>>(body["Ids"].ToString(Formatting.None))) ?? throw new ArgumentException("Ids is vereist.");
                            adapter.SetSelection(ids); return ApiResponse.Ok(new { ok = true, ids = adapter.GetSelection() });
                        case "catalogs/profiles": return Catalog("profiles");
                        case "catalogs/materials": return Catalog("materials");
                        case "catalogs/components": return Catalog("components");
                        case "catalogs/shapes": return Catalog("shapes");
                        case "objects": case "parts": return ApiResponse.Ok(new { ok = true, parts = adapter.ReadParts(), fixture = adapter.IsFixture });
                        case "build-plan":
                            var source = (body["Source"] == null ? null : JsonUtil.Deserialize<SteelModel>(body["Source"].ToString(Formatting.None))) ?? throw new ArgumentException("Source is vereist.");
                            var modelIdentity = adapter.GetIdentity();
                            var plan = new PlanService(auth.Authority).Create(source, adapter.ReadParts(), modelIdentity, context.Scope);
                            plans[plan.PlanHash] = JsonUtil.Clone(plan); return ApiResponse.Ok(new { ok = true, plan, statistics = PlanStatisticsService.Count(plan), released = false });
                        case "build-plan/validate":
                            var validated = LookupPlan(body, context); var issues = new PlanService(auth.Authority).Validate(validated, context, adapter);
                            return ApiResponse.Ok(new { ok = issues.Count == 0, issues, planHash = validated.PlanHash, released = false });
                        case "build-plan/execute":
                            var executing = LookupPlan(body, context); var run = new ExecutionService(adapter, auth, journal).Execute(executing, context);
                            return ApiResponse.Ok(new { ok = run.Status != "FAILED", run });
                        case "readback":
                            var expected = LookupPlan(body, context); var snapshot = new AdapterSnapshot { Identity = adapter.GetIdentity(), Parts = adapter.ReadParts(), PersistenceProof = null, IsFixture = adapter.IsFixture };
                            return ApiResponse.Ok(new { ok = true, audit = new ReadbackService().Compare(expected, snapshot), fixture = snapshot.IsFixture, persistenceProven = false });
                        case "runs": case "runs/events": case "transactions/journal": return ApiResponse.Ok(new { ok = true, entries = journal.ReadAll() });
                        case "review/history":
                            if (Review == null) return ApiResponse.Error(501, "REVIEW_UNAVAILABLE", "Review store niet geconfigureerd.");
                            return ApiResponse.Ok(new { ok = true, history = Review.History() });
                        case "review/propose":
                            if (Review == null) return ApiResponse.Error(501, "REVIEW_UNAVAILABLE", "Review store niet geconfigureerd.");
                            var proposal = (body["Proposal"] == null ? null : JsonUtil.Deserialize<ReviewProposal>(body["Proposal"].ToString(Formatting.None))) ?? throw new ArgumentException("Proposal is vereist.");
                            if (proposal.Actor != null && proposal.Actor != context.Actor) return ApiResponse.Error(403, "PRINCIPAL_MISMATCH", "Voorstelactor moet overeenkomen met de geauthenticeerde actor.");
                            proposal.Actor = context.Actor;
                            if (proposal.Model == null || !proposal.Model.ExactlyEquals(adapter.GetIdentity())) return ApiResponse.Error(409, "MODEL_IDENTITY_MISMATCH", "Reviewvoorstel hoort niet bij het actuele model.");
                            return ApiResponse.Ok(new { ok = true, proposal = Review.Propose(proposal), modelMutated = false });
                        default: return ApiResponse.Error(501, "NOT_IMPLEMENTED", "Deze endpointfamilie heeft nog geen bewezen uitvoerbare implementatie.");
                    }
                }
                catch (JsonException) { return ApiResponse.Error(400, "INVALID_JSON", "Ongeldige of te diepe JSON-body."); }
                catch (ArgumentException ex) { return ApiResponse.Error(400, "INVALID_REQUEST", ex.Message); }
                catch (InvalidOperationException ex) { return ApiResponse.Error(409, "OPERATION_BLOCKED", ex.Message); }
                catch (NotSupportedException ex) { return ApiResponse.Error(501, "NOT_SUPPORTED", ex.Message); }
                catch (Exception) { return ApiResponse.Error(500, "OPERATION_FAILED", "De operatie is mislukt. Bekijk het lokale logboek."); }
            }
        }
        private BuildPlan LookupPlan(JObject body, RequestContext context)
        {
            string hash = body.Value<string>("PlanHash") ?? context.PlanHash;
            if (String.IsNullOrWhiteSpace(hash) || !plans.TryGetValue(hash, out var plan)) throw new ArgumentException("Een build-plan uit deze sessie en de exacte PlanHash zijn vereist.");
            if (context.PlanHash != hash) throw new ArgumentException("Context.PlanHash moet exact overeenkomen.");
            return JsonUtil.Clone(plan);
        }
        private ApiResponse Catalog(string catalog)
        {
            var catalogs = adapter.ReadCatalogs(); if (!catalogs.TryGetValue(catalog, out var values)) return ApiResponse.Error(501, "CATALOG_NOT_SUPPORTED", "Catalogus is niet beschikbaar in deze adapter.");
            return ApiResponse.Ok(new { ok = true, values, fixture = adapter.IsFixture });
        }
        public CapabilitySet EffectiveCapabilities()
        {
            var result = JsonUtil.Clone(adapter.Capabilities);
            foreach (string name in new[] { "bridge.health", "bridge.capabilities", "bridge.session", "authorization.read", "authority.read", "journal.read", "runs.read" }) result.Values[name] = true;
            if (Review != null) { result.Values["review.read"] = true; result.Values["review.propose"] = true; }
            return result;
        }
        private static JObject ParseBody(string text)
        {
            if (String.IsNullOrWhiteSpace(text)) return new JObject();
            using (var input = new StringReader(text)) using (var reader = new JsonTextReader(input) { MaxDepth = 32, DateParseHandling = DateParseHandling.None })
            {
                var token = JToken.ReadFrom(reader, new JsonLoadSettings { DuplicatePropertyNameHandling = DuplicatePropertyNameHandling.Error, CommentHandling = CommentHandling.Ignore });
                if (!(token is JObject result)) throw new JsonException("JSON object required");
                if (reader.Read()) throw new JsonException("Trailing JSON not allowed"); return result;
            }
        }
        private static bool IsModelOperation(string route) { return route != "review/propose" && route != "authority/proposals"; }
    }
}
