using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;
using Cws.TeklaBridge.Core;
namespace Cws.TeklaBridge.Windows
{
    internal sealed class ReviewConfirmationForm : Form
    {
        private readonly TextBox reason = new TextBox { Multiline = true, Dock = DockStyle.Fill };
        private readonly TextBox evidence = new TextBox { Dock = DockStyle.Fill };
        public string Reason => reason.Text.Trim();
        public IEnumerable<string> EvidenceIds => evidence.Text.Split(',').Select(x => x.Trim()).Where(x => x.Length > 0).Distinct();
        public ReviewConfirmationForm(ReviewProposal proposal, ModelIdentity model, string sourceRevision)
        {
            Text = "Lokaal projectbesluit bevestigen"; Size = new Size(650, 470); StartPosition = FormStartPosition.CenterParent; MinimizeBox = false; MaximizeBox = false;
            Font = new Font("Segoe UI", 10); BackColor = Color.White;
            var layout = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(16), ColumnCount = 1, RowCount = 7 };
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 150)); layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 26)); layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100)); layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 26)); layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 35)); layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 24)); layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 42));
            layout.Controls.Add(new Label { Dock = DockStyle.Fill, Text = "Onderdeel: " + proposal.CanonicalId + ":" + proposal.PhysicalRole + "\nVeld: " + proposal.Field + "\nVan: " + proposal.OldValue + "\nNaar: " + proposal.NewValue + "\nModel: " + model.ModelName + " · revisie " + model.Revision + "\nBronrevisie: " + sourceRevision + "\nScope: " + proposal.Scope.Kind + " · " + String.Join(", ", proposal.Scope.Values) });
            layout.Controls.Add(new Label { Text = "Reden van dit projectbesluit", Dock = DockStyle.Fill }); layout.Controls.Add(reason);
            layout.Controls.Add(new Label { Text = "Bewijs-ID(s), kommagescheiden", Dock = DockStyle.Fill }); layout.Controls.Add(evidence);
            layout.Controls.Add(new Label { Text = "Geldt uitsluitend voor deze bronrevisie, scope en model. Geen globale authority.", Dock = DockStyle.Fill, ForeColor = Color.DarkGoldenrod });
            var bar = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.RightToLeft };
            var approve = new Button { Text = "Projectbesluit bevestigen", Width = 205, Height = 32 };
            approve.Click += (s, e) => { if (Reason.Length == 0 || !EvidenceIds.Any()) { MessageBox.Show(this, "Reden en minimaal één bewijs-ID zijn vereist."); return; } DialogResult = DialogResult.OK; Close(); };
            bar.Controls.Add(approve); bar.Controls.Add(new Button { Text = "Annuleren", DialogResult = DialogResult.Cancel, Width = 110, Height = 32 }); layout.Controls.Add(bar); Controls.Add(layout);
        }
    }
}
