using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading.Tasks;
using Cws.TeklaBridge.Core;
using Newtonsoft.Json.Linq;

namespace Cws.TeklaBridge.Tests
{
    public static class ApiTests
    {
        private static string Send(ApiServer server, string request)
        {
            using (var client = new TcpClient())
            {
                client.ReceiveTimeout = 10000; client.SendTimeout = 10000;
                client.Connect("127.0.0.1", server.BaseUri.Port);
                using (var stream = client.GetStream())
                {
                    byte[] bytes = Encoding.UTF8.GetBytes(request); stream.Write(bytes, 0, bytes.Length);
                    using (var reader = new StreamReader(stream)) return reader.ReadToEnd();
                }
            }
        }
        private static string Request(ApiServer server, string path = "health", string extra = "", string body = null, bool authenticated = true)
        {
            string method = body == null ? "GET" : "POST";
            return method + " /api/v1/" + path + " HTTP/1.1\r\nHost: " + server.BaseUri.Authority + "\r\n" +
                (authenticated ? "Authorization: Bearer " + server.SessionToken + "\r\n" : "") + extra +
                (body == null ? "" : "Content-Type: application/json\r\nContent-Length: " + Encoding.UTF8.GetByteCount(body) + "\r\n") + "\r\n" + (body ?? "");
        }
        public static void Run(TestSuite t)
        {
            t.Check("Core plan statistics distinguish canonical physical roles and expected removals", () =>
            {
                var plan = new BuildPlan { Items = new List<PlanItem> {
                    new PlanItem { Key = "one:PRIMARY", Status = "CREATE", After = new CanonicalPart { CanonicalId = "one", PhysicalRole = "PRIMARY" } },
                    new PlanItem { Key = "one:PLATE", Status = "CREATE", After = new CanonicalPart { CanonicalId = "one", PhysicalRole = "PLATE" } },
                    new PlanItem { Key = "old:PRIMARY", Status = "REMOVE", Before = new CanonicalPart { CanonicalId = "old", PhysicalRole = "PRIMARY" } }
                } };
                var count = PlanStatisticsService.Count(plan);
                t.Equal(2, count.ScopedCanonicalCount); t.Equal(3, count.PlannedPhysicalRoleCount);
                t.Equal(1, count.ExpectedCanonicalCount); t.Equal(2, count.ExpectedPhysicalCount); t.Equal(1, count.StatusCounts["REMOVE"]);
            });
            t.Check("API authenticated loopback health and session token rotation", () =>
            {
                using (var server = new ApiServer(req => Task.FromResult(ApiResponse.Ok(new { ok = true, path = req.Path }))))
                {
                    server.Start(); t.Equal("127.0.0.1", server.BaseUri.Host); string token = server.SessionToken;
                    t.True(Send(server, Request(server)).StartsWith("HTTP/1.1 200"));
                    t.True(Send(server, Request(server, authenticated: false)).StartsWith("HTTP/1.1 401"));
                    t.Equal(1L, server.AuthenticatedRequestCount); server.Dispose(); server.Start(); t.True(token != server.SessionToken);
                }
            });
            t.Check("API hostile origins Host spoofing malformed lengths and chunked rejected before dispatch", () =>
            {
                int calls = 0;
                using (var server = new ApiServer(req => { calls++; return Task.FromResult(ApiResponse.Ok(new { ok = true })); }))
                {
                    server.Start();
                    t.True(Send(server, Request(server, extra: "Origin: https://attacker.invalid\r\n")).StartsWith("HTTP/1.1 403"));
                    t.True(Send(server, Request(server).Replace("Host: " + server.BaseUri.Authority, "Host: attacker.invalid")).StartsWith("HTTP/1.1 403"));
                    t.True(Send(server, Request(server, extra: "Transfer-Encoding: chunked\r\n")).StartsWith("HTTP/1.1 400"));
                    t.True(Send(server, Request(server, extra: "Content-Length: -1\r\n")).StartsWith("HTTP/1.1 400"));
                    t.True(Send(server, Request(server, extra: "Content-Length: 9999999999\r\n")).StartsWith("HTTP/1.1 413"));
                    t.True(Send(server, Request(server, extra: "Content-Length: 0\r\nContent-Length: 0\r\n")).StartsWith("HTTP/1.1 400"));
                    t.True(Send(server, Request(server, extra: "X-Huge: " + new string('a', ApiServer.MaximumHeaderBytes) + "\r\n")).StartsWith("HTTP/1.1 431"));
                    t.Equal(0, calls);
                }
            });
            t.Check("API bounded slow body timeout", () =>
            {
                int calls = 0;
                using (var server = new ApiServer(req => { calls++; return Task.FromResult(ApiResponse.Ok(new { ok = true })); }, readTimeoutMilliseconds: 200))
                {
                    server.Start(); string request = Request(server, "build-plan", body: "{}").Replace("Content-Length: 2", "Content-Length: 10");
                    t.True(Send(server, request).StartsWith("HTTP/1.1 408")); t.Equal(0, calls);
                }
            });
            t.Check("API HTTP principal cannot spoof reviewer or confirmation and exact model revision required", () =>
            {
                string dir = Path.Combine(Path.GetTempPath(), "cws-api-" + Guid.NewGuid().ToString("N"));
                try
                {
                    var adapter = new ApiTestAdapter(); var review = new ReviewService(new ReviewStore(Path.Combine(dir, "review")));
                    var dispatcher = new ApiDispatcher(adapter, new AuthorizationService(), new JournalStore(dir)) { Review = review };
                    using (var server = new ApiServer(dispatcher.HandleNetwork))
                    {
                        server.Start();
                        string spoof = "{\"Context\":{\"Actor\":\"AUTHORIZED_REVIEWER\"}}";
                        t.True(Send(server, Request(server, "review/resolve", body: spoof)).Contains("PRINCIPAL_MISMATCH"));
                        t.True(Send(server, Request(server, "review/resolve", body: "{\"Context\":{\"Actor\":\"GPT\",\"ConfirmationToken\":\"stolen\"}}")).Contains("HUMAN_CONFIRMATION_LOCAL_ONLY"));
                        var context = new RequestContext { Actor = "GPT", Mode = "CHECK_ONLY", ExpectedModel = adapter.GetIdentity(), Scope = new ScopeSpec() };
                        context.ExpectedModel.Revision = "other";
                        t.True(Send(server, Request(server, "build-plan", body: JsonUtil.Serialize(new { Context = context, Source = new SteelModel() }))).Contains("MODEL_IDENTITY_MISMATCH"));
                        t.True(Send(server, Request(server, "unknown")).Contains("ENDPOINT_NOT_MATRIXED"));
                        t.True(Send(server, Request(server, "build-plan")).StartsWith("HTTP/1.1 405"), "Matrix explicitly requires POST");
                        t.True(Send(server, Request(server, "health", body: "{}")).StartsWith("HTTP/1.1 405"), "Matrix explicitly requires GET");
                        t.True(Send(server, Request(server, "build-plan", body: "{\"Context\":{},\"Context\":{}}")).Contains("INVALID_JSON"));
                        string matrixResponse = Send(server, Request(server, "authorization/matrix"));
                        var matrixPayload = JObject.Parse(matrixResponse.Substring(matrixResponse.IndexOf("\r\n\r\n", StringComparison.Ordinal) + 4));
                        t.Equal(JsonUtil.Hash(new AuthorizationMatrix().Export()), JsonUtil.Hash(matrixPayload["matrix"]), "API matrix matches canonical machine-readable export");
                        string response = Send(server, Request(server, "session"));
                        t.True(response.Contains("GPT")); t.True(!response.Contains(server.SessionToken));
                        var validContext = new RequestContext { Actor = "GPT", Mode = "CHECK_ONLY", ExpectedModel = adapter.GetIdentity(), Scope = new ScopeSpec() };
                        var source = new SteelModel { SourceId = "api-source", SourceRevision = "1", SourceSha256 = JsonUtil.HashText("api-fixture"), Parts = new List<CanonicalPart>() };
                        var stale = review.Propose(new ReviewProposal { Model = adapter.GetIdentity(), Scope = new ScopeSpec(), SourceId = "api-source", SourceRevision = "old", CanonicalId = "p1", PhysicalRole = "PRIMARY", Field = "Material", OldValue = "UNKNOWN", NewValue = "S235JR", Actor = "USER", Reason = "Old source proposal", EvidenceIds = new List<string> { "fixture" } });
                        var localReview = review.CreateTrustedLocalUi("USER"); var confirmation = localReview.CreateChallenge(stale.ProposalId, adapter.GetIdentity(), new ScopeSpec(), "old");
                        var humanResolution = localReview.Confirm(stale.ProposalId, confirmation.Token, adapter.GetIdentity(), new ScopeSpec(), "old", "Local old source decision", new[] { "fixture" });
                        string made = Send(server, Request(server, "build-plan", body: JsonUtil.Serialize(new { Context = validContext, Source = source })));
                        var payload = JObject.Parse(made.Substring(made.IndexOf("\r\n\r\n", StringComparison.Ordinal) + 4));
                        string hash = payload["plan"]?.Value<string>("PlanHash"); t.True(hash != null, made);
                        t.Equal("PROJECT_CONFIRMED", review.History().Resolutions.Find(x => x.ResolutionId == humanResolution.ResolutionId).Status, "Untrusted HTTP source revision must not supersede real local decisions");
                        validContext.PlanHash = hash;
                        string readback = Send(server, Request(server, "readback", body: JsonUtil.Serialize(new { Context = validContext, PlanHash = hash })));
                        t.True(readback.StartsWith("HTTP/1.1 200"), readback); t.True(readback.Contains("false"));
                        t.Equal(0, adapter.ReopenCalls, "L0 readback must not close/reopen model");
                        adapter.Capabilities.Values["model.identity"] = false; int identityReads = adapter.IdentityReads;
                        t.True(Send(server, Request(server, "model/identity")).Contains("CAPABILITY_NOT_SUPPORTED"));
                        t.Equal(identityReads, adapter.IdentityReads, "Unsupported capability denied before native model read");
                        t.Equal(0, adapter.Mutations);
                    }
                }
                finally { if (Directory.Exists(dir)) Directory.Delete(dir, true); }
            });
        }
        private sealed class ApiTestAdapter : IModelAdapter
        {
            public int Mutations;
            public int ReopenCalls;
            public int IdentityReads;
            public string AdapterName => "TEST_FIXTURE_HTTP_SECURITY";
            public bool IsFixture => true;
            public CapabilitySet Capabilities { get; } = new CapabilitySet { Values = new Dictionary<string, bool> { ["model.read"] = true, ["model.identity"] = true, ["plan.create"] = true, ["plan.validate"] = true } };
            public ModelIdentity GetIdentity() { IdentityReads++; return new ModelIdentity { ModelId = "fixture", ModelPath = "/fixture/model", ModelName = "Fixture", TeklaVersion = "TEST", Revision = "1" }; }
            public List<CanonicalPart> ReadParts() => new List<CanonicalPart>();
            public List<string> GetSelection() => new List<string>();
            public void SetSelection(List<string> ids) { Mutations++; }
            public Dictionary<string, List<string>> ReadCatalogs() => new Dictionary<string, List<string>>();
            public void Upsert(CanonicalPart part) { Mutations++; }
            public void Remove(CanonicalPart part) { Mutations++; }
            public void Save() { Mutations++; }
            public AdapterSnapshot ReopenAndReadback() { ReopenCalls++; throw new NotSupportedException(); }
        }
    }
}
