using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Forms;
using Cws.TeklaBridge.Core;
using Cws.TeklaBridge.Native;
using Newtonsoft.Json.Linq;

namespace Cws.TeklaBridge.Windows
{
    public sealed class MainForm : Form
    {
        private static readonly Color Navy = Color.FromArgb(8, 37, 65), Blue = Color.FromArgb(0, 113, 240), Pale = Color.FromArgb(239, 247, 254);
        private readonly TabControl tabs = new TabControl { Dock = DockStyle.Fill };
        private readonly Label connection = new Label { AutoSize = true }, apiStatus = new Label { AutoSize = true }, sourceLabel = new Label { AutoSize = true }, resultLabel = new Label { AutoSize = true };
        private readonly TextBox log = new TextBox { Multiline = true, ReadOnly = true, ScrollBars = ScrollBars.Both, Dock = DockStyle.Fill, Font = new Font("Consolas", 10), WordWrap = false };
        private readonly TextBox summary = new TextBox { Multiline = true, ReadOnly = true, ScrollBars = ScrollBars.Vertical, Dock = DockStyle.Fill };
        private readonly DataGridView planGrid = Grid(), reviewGrid = Grid();
        private readonly ComboBox task = Combo(new[] { "Model opbouwen", "Revisie verwerken", "Model aanvullen", "Model controleren", "Verbindingen aanbrengen", "Details verwerken", "Herstellen" });
        private readonly ComboBox scope = Combo(new[] { "Hele model", "Huidige selectie in Tekla", "Fase", "Merk(en)", "Alleen gewijzigd", "Alleen review / geblokkeerd" });
        private readonly ComboBox mode = Combo(new[] { "Eerst voorstellen", "Alleen controleren", "Automatisch uitvoeren" });
        private readonly TextBox scopeValues = new TextBox { Width = 390 };
        private readonly TextBox expectedVersion = new TextBox { Width = 270 };
        private readonly Label actionState = new Label { AutoSize = true, MaximumSize = new Size(800, 0) };
        private readonly System.Windows.Forms.Timer statusTimer = new System.Windows.Forms.Timer { Interval = 1000 };
        private IModelAdapter adapter;
        private ApiDispatcher dispatcher;
        private ApiServer server;
        private readonly AuthorizationService auth = new AuthorizationService();
        private readonly JournalStore journal;
        private readonly ReviewService review;
        private BridgeSettings settings;
        private FrozenSource frozen;
        private BuildPlan currentPlan;
        private readonly string localSession = Guid.NewGuid().ToString("N");
        private readonly string workDirectory;
        public ApiServer Server => server;
        public int ScreenCount => tabs.TabPages.Count;
        public string AdapterName => adapter.AdapterName;
        public bool Fixture => adapter.IsFixture;
        public MainForm(bool smoke = false)
        {
            Text = "CWS | Tekla Bridge v0.1"; Size = new Size(1000, 760); MinimumSize = new Size(860, 650);
            StartPosition = FormStartPosition.CenterScreen; BackColor = Pale; Font = new Font("Segoe UI", 10); AutoScaleMode = AutoScaleMode.Dpi;
            workDirectory = smoke ? Path.Combine(Path.GetTempPath(), "CWS-Bridge-Smoke-" + Guid.NewGuid().ToString("N")) : BridgeSettings.WorkDirectory;
            Directory.CreateDirectory(workDirectory); journal = new JournalStore(Path.Combine(workDirectory, "journal")); review = new ReviewService(new ReviewStore(Path.Combine(workDirectory, "review")));
            try { settings = smoke ? new BridgeSettings() : BridgeSettings.Load(); } catch (Exception) { settings = new BridgeSettings(); }
            expectedVersion.Text = settings.ExpectedTeklaVersion; mode.SelectedIndex = settings.Mode == "CHECK_ONLY" ? 1 : settings.Mode == "AUTO" ? 2 : 0;
            var top = new Panel { Dock = DockStyle.Top, Height = 72, BackColor = Navy, Padding = new Padding(18, 12, 18, 8) };
            top.Controls.Add(new Label { Text = "CWS  |  Tekla Bridge v0.1", Dock = DockStyle.Top, ForeColor = Color.White, Font = new Font("Segoe UI", 20, FontStyle.Bold), Height = 34 });
            top.Controls.Add(new Label { Text = "Bouwen · Controleren · Verbinden   |   Tekla blijft de modelomgeving", Dock = DockStyle.Bottom, ForeColor = Color.LightSteelBlue, Height = 18 });
            var footer = new Label { Text = "CWS Engineering | v0.1  —  native runtime- en productieauthority vereist", Dock = DockStyle.Bottom, Height = 30, Padding = new Padding(12, 6, 0, 0), ForeColor = Navy };
            Controls.Add(tabs); Controls.Add(top); Controls.Add(footer); BuildPages();
            Shown += (s, e) => { ReplaceAdapter(new DisconnectedAdapter("Nog geen geverifieerde Tekla-sessie.")); statusTimer.Start(); Log("Bridge gestart. Geen Tekla-verbinding. Native writes zijn geblokkeerd zonder runtimebewijs."); };
            FormClosed += (s, e) => { statusTimer.Stop(); server?.Dispose(); if (smoke) try { Directory.Delete(workDirectory, true); } catch { } };
            statusTimer.Tick += (s, e) => RefreshStatus();
        }
        private static ComboBox Combo(string[] values) { var c = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Width = 410 }; c.Items.AddRange(values); c.SelectedIndex = 0; return c; }
        private static DataGridView Grid() { return new DataGridView { Dock = DockStyle.Fill, ReadOnly = true, AllowUserToAddRows = false, AllowUserToDeleteRows = false, AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill, BackgroundColor = Color.White, BorderStyle = BorderStyle.FixedSingle, SelectionMode = DataGridViewSelectionMode.FullRowSelect, MultiSelect = false, RowHeadersVisible = false }; }
        private FlowLayoutPanel Page(string title, string description)
        {
            var page = new TabPage(title) { BackColor = Pale, Padding = new Padding(16) }; tabs.TabPages.Add(page);
            var flow = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown, WrapContents = false, AutoScroll = true, Padding = new Padding(8), BackColor = Color.White };
            flow.Controls.Add(new Label { Text = title, AutoSize = true, Font = new Font("Segoe UI", 17, FontStyle.Bold), ForeColor = Navy, Margin = new Padding(6, 6, 6, 12) });
            flow.Controls.Add(new Label { Text = description, AutoSize = true, MaximumSize = new Size(840, 0), ForeColor = Navy, Margin = new Padding(6, 0, 6, 16) });
            page.Controls.Add(flow); return flow;
        }
        private static void Row(FlowLayoutPanel parent, string label, Control control)
        { parent.Controls.Add(new Label { Text = label, AutoSize = true, Margin = new Padding(6, 12, 6, 4), ForeColor = Navy }); control.Margin = new Padding(6, 4, 6, 8); parent.Controls.Add(control); }
        private Button Button(string label, Action action, bool enabled = true)
        {
            var b = new Button { Text = label, AutoSize = true, MinimumSize = new Size(180, 38), BackColor = Blue, ForeColor = Color.White, FlatStyle = FlatStyle.Flat, Margin = new Padding(6), Enabled = enabled };
            b.Click += (s, e) => Guard(action); return b;
        }
        private void BuildPages()
        {
            var start = Page("Start", "Controleer de echte verbinding, laad een canonical bron en maak een controleerbaar build-plan.");
            Row(start, "Tekla Structures", connection); Row(start, "Lokale API-sessie", apiStatus); Row(start, "Canonical bron", sourceLabel);
            start.Controls.Add(Button("Tekla verbinden", Connect)); start.Controls.Add(Button("Canonical JSON openen", ImportSource));
            start.Controls.Add(Button("API-sessie kopiëren", () => { if (server == null) throw new InvalidOperationException("API is nog niet gestart."); Clipboard.SetText(JsonUtil.Serialize(new { baseUrl = server.BaseUri.AbsoluteUri + "api/v1/", authorization = "Bearer " + server.SessionToken, actor = "GPT" })); Log("API-gegevens expliciet naar klembord gekopieerd; token blijft buiten log en bestanden."); }));
            var tasks = Page("Taak", "Taken werken vanuit dezelfde canonical bron en hetzelfde echte Tekla-model. Ontbrekende capabilities blijven zichtbaar geblokkeerd."); Row(tasks, "Taak kiezen", task);
            tasks.Controls.Add(Button("Volgende: scope", () => tabs.SelectedIndex = 2));
            var scopes = Page("Scope", "Beperk het plan tot onderdelen binnen een expliciete scope. Fasen en merken: kommagescheiden waarden."); Row(scopes, "Scope", scope); Row(scopes, "Fase(n) / merk(en) / canonical IDs", scopeValues);
            scopes.Controls.Add(Button("Tekla-selectie lezen", () => { var ids = adapter.GetSelection(); scope.SelectedIndex = 1; scopeValues.Text = String.Join(", ", ids); Log("Echte Tekla-selectie gelezen: " + ids.Count + " objecten."); }));
            scopes.Controls.Add(Button("Volgende: uitvoering", () => tabs.SelectedIndex = 3));
            var execution = Page("Uitvoering", "Voorstellen en controles wijzigen het model niet. AUTO vereist gevalideerde native capabilities en authority; onbekende engineering blijft review."); Row(execution, "Uitvoeringsniveau", mode);
            Row(execution, "Releasegate", actionState); execution.Controls.Add(Button("Build-plan maken", CreatePlan)); execution.Controls.Add(Button("Plan valideren", ValidatePlan)); execution.Controls.Add(Button("Gevalideerd plan uitvoeren", ExecutePlan));
            execution.Controls.Add(new Label { Text = "Nummering, NC en onbekende details: geblokkeerd totdat aparte productie- en runtimegates bewezen zijn.", AutoSize = true, MaximumSize = new Size(790, 0), ForeColor = Color.DarkGoldenrod });
            var connections = Page("Verbindingen", "Bestaande handmatige verbindingen behouden. Automatische toepassing is alleen mogelijk voor bewezen families, attributes, detail- en clashbewijs.");
            connections.Controls.Add(new Label { Text = "Status: analyse/voorstellen voorbereid; native connection-write en native readback niet vrijgegeven.", AutoSize = true, MaximumSize = new Size(780, 0) });
            connections.Controls.Add(Button("Authority en capabilities tonen", () => { summary.Text = JsonUtil.Serialize(new { Authority = auth.Authority.Snapshot(), Capabilities = adapter.Capabilities }); tabs.SelectedIndex = 5; }));
            connections.Controls.Add(Button("Verbinding automatisch aanbrengen (niet beschikbaar)", () => { }, false));
            var summaryPage = new TabPage("Samenvatting") { BackColor = Pale, Padding = new Padding(16) }; tabs.TabPages.Add(summaryPage); summaryPage.Controls.Add(planGrid);
            planGrid.Columns.Add("status", "Status"); planGrid.Columns.Add("key", "Canonical / fysieke rol"); planGrid.Columns.Add("reason", "Reden");
            var detailPanel = new Panel { Dock = DockStyle.Bottom, Height = 140 }; detailPanel.Controls.Add(summary); summaryPage.Controls.Add(detailPanel);
            var logs = new TabPage("Logboek") { BackColor = Pale, Padding = new Padding(16) }; logs.Controls.Add(log); tabs.TabPages.Add(logs);
            var results = Page("Resultaat", "Een HTTP-succes of insert is geen productie-PASS. Alleen echte save → reopen → readback kan persistentie aantonen."); Row(results, "Laatste resultaat", resultLabel);
            results.Controls.Add(Button("Resultaat exporteren JSON", () => ExportText(summary.Text, "CWS_Bridge_resultaat.json"))); results.Controls.Add(Button("Nieuwe taak", () => { currentPlan = null; planGrid.Rows.Clear(); summary.Clear(); resultLabel.Text = "Nog geen native uitvoering."; tabs.SelectedIndex = 1; }));
            var reviews = new TabPage("Review") { Padding = new Padding(16), BackColor = Pale }; tabs.TabPages.Add(reviews); reviews.Controls.Add(reviewGrid);
            reviewGrid.Columns.Add("id", "Voorstel"); reviewGrid.Columns.Add("part", "Onderdeel"); reviewGrid.Columns.Add("field", "Veld"); reviewGrid.Columns.Add("value", "Voorgesteld"); reviewGrid.Columns.Add("state", "Status");
            var bar = new FlowLayoutPanel { Dock = DockStyle.Bottom, Height = 108, FlowDirection = FlowDirection.LeftToRight };
            bar.Controls.Add(Button("Review vernieuwen", RefreshReview)); bar.Controls.Add(Button("Voorstel JSON toevoegen", ImportProposal)); bar.Controls.Add(Button("Lokaal projectbesluit bevestigen", ConfirmReview));
            bar.Controls.Add(new Label { Text = "Een besluit legt projectauthority vast. Bronupdate en native rebuild blijven afzonderlijke gates.", AutoSize = true, MaximumSize = new Size(780, 0) }); reviews.Controls.Add(bar);
            var options = Page("Instellingen", "Instellingen worden per Windows-gebruiker opgeslagen. API-tokens worden uitsluitend in geheugen gehouden."); Row(options, "Exacte geïnstalleerde Tekla-versie (bv. 2024.0)", expectedVersion);
            options.Controls.Add(Button("Instellingen opslaan", () => { settings.ExpectedTeklaVersion = expectedVersion.Text.Trim(); settings.Mode = CurrentMode(); settings.Save(); Log("Gebruikersinstellingen opgeslagen."); }));
            options.Controls.Add(Button("Capabilities inspecteren", () => { summary.Text = JsonUtil.Serialize(adapter.Capabilities); tabs.SelectedIndex = 5; }));
            var help = Page("Help", "CWS Tekla Bridge v0.1 — compacte Windows x64 bridge met fail-closed native authorisatie.");
            help.Controls.Add(new Label { Text = "1. Open het juiste model in Tekla en vul de exact geïnstalleerde versie in.\n2. Verbind, laad de canonical JSON-bron, kies scope en maak het plan.\n3. Controleer BLOCK/REVIEW en authority.\n4. Uitvoering blijft geblokkeerd zonder bewezen native persistence.\n\nDirecte IFC-herkenning, 20 echte corpusmodellen, native connections AUTO en productie-release zijn nog geen bewezen runtimefunctionaliteit.\nDe meegeleverde headless tests gebruiken fixtures en zijn geen bewijs van uw Tekla-model.", AutoSize = true, MaximumSize = new Size(800, 0), ForeColor = Navy });
        }
        private void Guard(Action action) { try { action(); } catch (Exception ex) { Log("Geblokkeerd: " + ex.Message); resultLabel.Text = "Geblokkeerd: " + ex.Message; MessageBox.Show(this, ex.Message, "Operatie geblokkeerd", MessageBoxButtons.OK, MessageBoxIcon.Information); } }
        private void ReplaceAdapter(IModelAdapter value)
        {
            server?.Dispose(); adapter = value; currentPlan = null;
            dispatcher = new ApiDispatcher(adapter, auth, journal) { Review = review, AuditMessage = Log };
            dispatcher.InvokeOnModelThread = operation =>
            {
                var done = new TaskCompletionSource<ApiResponse>();
                if (IsDisposed || !IsHandleCreated) { done.SetResult(ApiResponse.Error(503, "UI_UNAVAILABLE", "Bridge-interface is niet actief.")); return done.Task; }
                BeginInvoke(new Action(() => { try { done.SetResult(operation()); } catch (Exception ex) { done.SetException(ex); } })); return done.Task;
            };
            server = new ApiServer(dispatcher.HandleNetwork); server.Start(); RefreshStatus(); RefreshReview();
        }
        private void Connect()
        {
            if (String.IsNullOrWhiteSpace(expectedVersion.Text)) throw new InvalidOperationException("Vul eerst de exacte geïnstalleerde Tekla-versie in bij Instellingen.");
            if (NativeModelAdapter.TryConnect(new NativeAdapterOptions { ExpectedTeklaVersion = expectedVersion.Text.Trim(), Authority = auth.Authority }, out var native, out var reason))
            { ReplaceAdapter(native); Log("Echte Tekla-sessie geverifieerd: " + adapter.GetIdentity().ModelName); }
            else { ReplaceAdapter(new DisconnectedAdapter(reason)); Log("Tekla niet verbonden: " + reason); throw new InvalidOperationException(reason); }
        }
        private void RefreshStatus()
        {
            bool connected = adapter != null && !adapter.IsFixture && adapter.Capabilities.Supports("model.identity");
            string modelName = null;
            if (connected) try { modelName = adapter.GetIdentity().ModelName; } catch (Exception) { connected = false; }
            connection.Text = connected ? "Verbonden: " + modelName : "Niet verbonden — geen geverifieerde Tekla-sessie"; connection.ForeColor = connected ? Color.Green : Color.DarkGoldenrod;
            apiStatus.Text = server == null ? "Nog niet gestart" : "Loopback actief op " + server.BaseUri.Authority + " · " + server.AuthenticatedRequestCount + " geauthenticeerde requests · GPT-koppeling niet geverifieerd";
            sourceLabel.Text = frozen == null ? "Geen canonical bron geladen" : Path.GetFileName(frozen.CanonicalPath) + " · revisie " + frozen.GetModel().SourceRevision;
            actionState.Text = adapter != null && adapter.Capabilities.Supports("plan.execute") ? "Native uitvoering capability beschikbaar; alle verdere authoritygates blijven verplicht." : "Native uitvoering geblokkeerd: capability / runtimeauthority ontbreekt.";
            if (String.IsNullOrEmpty(resultLabel.Text)) resultLabel.Text = "Nog geen native uitvoering.";
        }
        private void ImportSource()
        {
            using (var file = new OpenFileDialog { Filter = "Canonical SteelModel (*.json)|*.json", CheckFileExists = true })
            {
                if (file.ShowDialog(this) != DialogResult.OK) return;
                frozen = SourceFreezeService.LoadCanonical(file.FileName); currentPlan = null; settings.LastCanonicalPath = file.FileName;
                Log("Canonical bron bevroren: " + Path.GetFileName(file.FileName) + " · payload SHA256 " + frozen.PayloadSha256 + " · originele bronbytes nog niet geverifieerd."); SupersedeReviewsForCurrentSource(); RefreshStatus();
            }
        }
        private void SupersedeReviewsForCurrentSource(ModelIdentity identity = null)
        {
            if (frozen == null || adapter == null || !adapter.Capabilities.Supports("model.identity")) return;
            var source = frozen.GetModel();
            int count = review.SupersedeSource(identity ?? adapter.GetIdentity(), source.SourceId, source.SourceRevision);
            RefreshReview(); if (count > 0) Log("Bronrevisie gewijzigd: " + count + " oude reviewbesluiten/voorstellen vervallen.");
        }
        private ScopeSpec CurrentScope()
        {
            string[] kinds = { "ALL", "SELECTION", "PHASE", "MARKS", "CHANGED", "REVIEW" };
            var result = new ScopeSpec { Kind = kinds[scope.SelectedIndex], Values = scopeValues.Text.Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries).Select(x => x.Trim()).Where(x => x.Length > 0).Distinct().ToList() };
            if (result.Kind == "SELECTION") result.Values = adapter.GetSelection(); return result;
        }
        private string CurrentMode() => mode.SelectedIndex == 1 ? "CHECK_ONLY" : mode.SelectedIndex == 2 ? "AUTO" : "PROPOSE";
        private RequestContext Context(BuildPlan plan = null)
        { return new RequestContext { Actor = "USER", Principal = TrustedPrincipal.FromLocalHuman(Environment.UserName, "USER", localSession), SessionId = localSession, RequestId = Guid.NewGuid().ToString("N"), RunId = Guid.NewGuid().ToString("N"), OperationId = Guid.NewGuid().ToString("N"), ExpectedModel = adapter.GetIdentity(), Scope = plan?.Scope ?? CurrentScope(), Mode = CurrentMode(), SourceRevision = frozen?.GetModel().SourceRevision, PlanHash = plan?.PlanHash }; }
        private void CreatePlan()
        {
            if (task.SelectedIndex >= 4) throw new NotSupportedException("Deze taak heeft nog geen bewezen native uitvoerbare implementatie.");
            if (frozen == null) throw new InvalidOperationException("Laad eerst een canonical JSON-bron."); frozen.VerifyUnchanged();
            var identity = adapter.GetIdentity(); SupersedeReviewsForCurrentSource(identity);
            currentPlan = new PlanService(auth.Authority).Create(frozen.GetModel(), adapter.ReadParts(), identity, CurrentScope());
            var statistics = PlanStatisticsService.Count(currentPlan);
            planGrid.Rows.Clear(); foreach (var item in currentPlan.Items) planGrid.Rows.Add(item.Status, item.Key, item.Reason);
            summary.Text = JsonUtil.Serialize(new { Taak = task.Text, Modus = CurrentMode(), Scope = currentPlan.Scope, currentPlan.PlanHash, Statistieken = statistics, Release = "NIET_UITGEVOERD" });
            Log("Build-plan gemaakt: " + statistics.ItemCount + " plan-items; geen modelwijziging."); tabs.SelectedIndex = 5;
        }
        private void ValidatePlan()
        {
            if (currentPlan == null) throw new InvalidOperationException("Maak eerst een plan."); frozen.VerifyUnchanged(); var issues = new PlanService(auth.Authority).Validate(currentPlan, Context(currentPlan), adapter);
            summary.Text = JsonUtil.Serialize(new { PlanHash = currentPlan.PlanHash, Issues = issues, Released = false });
            Log("Planvalidatie: " + issues.Count + " issues. Native persistentie nog niet bewezen."); tabs.SelectedIndex = 5;
        }
        private void ExecutePlan()
        {
            if (currentPlan == null) throw new InvalidOperationException("Maak eerst een plan."); frozen.VerifyUnchanged();
            var result = new ExecutionService(adapter, auth, journal).Execute(currentPlan, Context(currentPlan));
            summary.Text = JsonUtil.Serialize(result); resultLabel.Text = result.Status + " · " + result.Mutations + " mutaties · persistentie " + (result.Audit?.PersistenceProven == true ? "bewezen" : "niet bewezen");
            Log("Run " + result.RunId + ": " + result.Status); tabs.SelectedIndex = 7;
        }
        private void RefreshReview()
        { reviewGrid.Rows.Clear(); foreach (var p in review.History().Proposals) reviewGrid.Rows.Add(p.ProposalId, p.CanonicalId + ":" + p.PhysicalRole, p.Field, p.NewValue, p.Status); }
        private void ImportProposal()
        {
            using (var file = new OpenFileDialog { Filter = "ReviewProposal (*.json)|*.json", CheckFileExists = true })
            { if (file.ShowDialog(this) != DialogResult.OK) return; var p = JsonUtil.Deserialize<ReviewProposal>(File.ReadAllText(file.FileName)); p.Actor = "USER"; review.Propose(p); RefreshReview(); Log("Projectreviewvoorstel vastgelegd; geen modelwijziging."); }
        }
        private void ConfirmReview()
        {
            if (reviewGrid.SelectedRows.Count != 1 || frozen == null) throw new InvalidOperationException("Selecteer een voorstel en laad de actuele canonical bron.");
            frozen.VerifyUnchanged(); string id = Convert.ToString(reviewGrid.SelectedRows[0].Cells[0].Value);
            var proposal = review.History().Proposals.Single(x => x.ProposalId == id); var identity = adapter.GetIdentity(); var currentScope = CurrentScope(); var revision = frozen.GetModel().SourceRevision;
            using (var dialog = new ReviewConfirmationForm(proposal, identity, revision))
            {
                if (dialog.ShowDialog(this) != DialogResult.OK) return;
                var local = review.CreateTrustedLocalUi("USER"); var challenge = local.CreateChallenge(id, identity, currentScope, revision);
                var resolution = local.Confirm(id, challenge.Token, adapter.GetIdentity(), CurrentScope(), frozen.GetModel().SourceRevision, dialog.Reason, dialog.EvidenceIds);
                currentPlan = null; planGrid.Rows.Clear(); RefreshReview(); Log("Lokaal projectbesluit " + resolution.ResolutionId + " vastgelegd. Bronupdate en herplanning vereist; geen native wijziging.");
            }
        }
        private void ExportText(string text, string filename)
        { using (var save = new SaveFileDialog { Filter = "JSON (*.json)|*.json", FileName = filename }) if (save.ShowDialog(this) == DialogResult.OK) File.WriteAllText(save.FileName, text); }
        private void Log(string text)
        {
            if (InvokeRequired) { BeginInvoke(new Action(() => Log(text))); return; }
            string line = DateTime.Now.ToString("HH:mm:ss") + "  " + text; log.AppendText(line + Environment.NewLine);
            File.AppendAllText(Path.Combine(workDirectory, "bridge.log"), DateTime.UtcNow.ToString("o") + " " + text + Environment.NewLine);
        }
    }
}
