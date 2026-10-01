using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using Newtonsoft.Json.Linq;

namespace Cws.TeklaBridge.Core
{
    public sealed class JointGeometry
    {
        public Vec3 ContactPoint { get; set; }
        public Vec3 MainDirection { get; set; }
        public Vec3 SecondaryDirection { get; set; }
        public double AngleDegrees { get; set; }
        public double GapMillimetres { get; set; }
        public string Orientation { get; set; }
        public string GeometryEvidenceId { get; set; }
    }
    public sealed class ConnectionJoint
    {
        public ModelIdentity Model { get; set; }
        public string SourceRevision { get; set; }
        public CanonicalPart Main { get; set; }
        public List<CanonicalPart> Secondary { get; set; } = new List<CanonicalPart>();
        public JointGeometry Geometry { get; set; }
        public string DetailId { get; set; }
        public string DetailSha256 { get; set; }
        public string AttributesSha256 { get; set; }
        public string AttributesSemanticHash { get; set; }
    }
    public sealed class ExistingConnection
    {
        public string NativeId { get; set; }
        public bool Managed { get; set; }
        public string Origin { get; set; }
        public string Fingerprint { get; set; }
        public string FamilyId { get; set; }
        public bool ManualDownstream { get; set; }
    }
    public sealed class ConnectionFamily
    {
        public string FamilyId { get; set; }
        public string BindingArtifactId { get; set; }
        public string ComponentId { get; set; }
        public string ComponentSourceSha256 { get; set; }
        public string AttributesSha256 { get; set; }
        public string AttributesSemanticHash { get; set; }
        public Dictionary<string, string> Attributes { get; set; } = new Dictionary<string, string>();
        public string DetailId { get; set; }
        public string DetailSha256 { get; set; }
        public List<string> ApprovedFingerprints { get; set; } = new List<string>();
        public EvidenceRecord Authority { get; set; }
    }
    public sealed class ConnectionValidationProof
    {
        public string JointFingerprint { get; set; }
        public string BindingArtifactId { get; set; }
        public string FamilyId { get; set; }
        public string ComponentSourceSha256 { get; set; }
        public string AttributesSha256 { get; set; }
        public string DetailSha256 { get; set; }
        public string ResultHash { get; set; }
        public bool PlatesValidated { get; set; }
        public bool BoltsValidated { get; set; }
        public bool WeldsValidated { get; set; }
        public bool CutsValidated { get; set; }
        public bool DetailValidated { get; set; }
        public EvidenceRecord RuntimeEvidence { get; set; }
    }
    public sealed class ConnectionClashProof
    {
        public string BindingArtifactId { get; set; }
        public string JointFingerprint { get; set; }
        public string ResultHash { get; set; }
        public bool NoClashes { get; set; }
        public string ToleranceVersion { get; set; }
        public EvidenceRecord RuntimeEvidence { get; set; }
    }
    public sealed class ConnectionCandidate
    {
        public string Status { get; set; }
        public string Reason { get; set; }
        public string JointFingerprint { get; set; }
        public string BindingArtifactId { get; set; }
        public string FamilyId { get; set; }
        public string ExistingNativeId { get; set; }
        // AUTO_READY is an authority decision, never an insert/save/readback result.
        public bool NativeApplyImplemented { get; set; }
    }
    public sealed class ParsedConnectionAttributes
    {
        public string SourcePath { get; set; }
        public string SourceSha256 { get; set; }
        public string SemanticHash { get; set; }
        public Dictionary<string, string> Values { get; set; } = new Dictionary<string, string>(StringComparer.Ordinal);
    }

    public static class ConnectionAttributeReader
    {
        private static readonly Regex Key = new Regex(@"^[A-Za-z_][A-Za-z0-9_.-]{0,127}$", RegexOptions.CultureInvariant);
        private static readonly HashSet<string> ExecutableExtensions = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        { ".cs", ".dll", ".exe", ".bat", ".cmd", ".ps1", ".py", ".js", ".vbs", ".com" };
        public static ParsedConnectionAttributes ReadDataFile(string path)
        {
            if (ExecutableExtensions.Contains(Path.GetExtension(path)))
                throw new InvalidDataException("Macros/executables are not attribute data files.");
            byte[] bytes = File.ReadAllBytes(path);
            if (bytes.Length > 1024 * 1024) throw new InvalidDataException("Attribute file exceeds one MiB.");
            var encoding = new UTF8Encoding(false, true);
            var parsed = Parse(encoding.GetString(bytes).TrimStart('\uFEFF'));
            parsed.SourcePath = Path.GetFullPath(path); parsed.SourceSha256 = JsonUtil.HashBytes(bytes);
            return parsed;
        }
        public static ParsedConnectionAttributes Parse(string data)
        {
            if (data == null || data.Length > 1024 * 1024) throw new InvalidDataException("Missing or oversized attribute data.");
            var result = new ParsedConnectionAttributes { SourceSha256 = JsonUtil.HashText(data) };
            if (data.TrimStart().StartsWith("{", StringComparison.Ordinal))
            {
                var obj = JObject.Parse(data, new Newtonsoft.Json.Linq.JsonLoadSettings
                { DuplicatePropertyNameHandling = DuplicatePropertyNameHandling.Error });
                foreach (var p in obj.Properties())
                {
                    if (!(p.Value is JValue) || p.Value.Type == JTokenType.Null || p.Value.Type == JTokenType.Undefined)
                        throw new InvalidDataException("Attributes must be scalar data.");
                    Add(result.Values, p.Name, p.Value.ToString());
                }
            }
            else
            {
                using (var reader = new StringReader(data))
                {
                    string line;
                    while ((line = reader.ReadLine()) != null)
                    {
                        line = line.Trim();
                        if (line.Length == 0 || line.StartsWith("//") || line.StartsWith("#")) continue;
                        var m = Regex.Match(line, @"^([A-Za-z_][A-Za-z0-9_.-]*)\s+(.*)$", RegexOptions.CultureInvariant);
                        if (!m.Success) throw new InvalidDataException("Unsupported attribute line; no guessing.");
                        Add(result.Values, m.Groups[1].Value, m.Groups[2].Value.Trim());
                    }
                }
            }
            if (result.Values.Count == 0) throw new InvalidDataException("No explicit attributes supplied.");
            result.SemanticHash = JsonUtil.Hash(result.Values); return result;
        }
        private static void Add(Dictionary<string, string> values, string key, string value)
        {
            if (!Key.IsMatch(key) || values.ContainsKey(key)) throw new InvalidDataException("Invalid or duplicate attribute name.");
            values.Add(key, value);
        }
    }

    public sealed class ConnectionService
    {
        private readonly AuthorityService authority;
        public ConnectionService(AuthorityService authority = null) { this.authority = authority ?? new AuthorityService(); }
        public string Fingerprint(ConnectionJoint joint)
        {
            ValidateJoint(joint);
            var secondary = joint.Secondary.OrderBy(p => p.CanonicalId, StringComparer.Ordinal)
                .ThenBy(p => p.PhysicalRole, StringComparer.Ordinal).Select(PartFingerprint).ToList();
            return JsonUtil.Hash(new { Schema = "joint-fingerprint/1.0", joint.Model, joint.SourceRevision,
                Main = PartFingerprint(joint.Main), Secondary = secondary, joint.Geometry,
                joint.DetailId, joint.DetailSha256, joint.AttributesSha256, joint.AttributesSemanticHash });
        }
        public ConnectionCandidate Evaluate(ConnectionJoint joint, IEnumerable<ConnectionFamily> families,
            string mode, ExistingConnection existing = null, ConnectionValidationProof validation = null, ConnectionClashProof clash = null)
        {
            if (existing != null && (!existing.Managed || existing.Origin != "CWS" || existing.ManualDownstream))
                return new ConnectionCandidate { Status = "KEEP", Reason = "Existing manual or unknown-origin connection is preserved.",
                    ExistingNativeId = existing.NativeId, FamilyId = existing.FamilyId, JointFingerprint = existing.Fingerprint };
            string fingerprint;
            try { fingerprint = Fingerprint(joint); }
            catch (ArgumentException e) { return new ConnectionCandidate { Status = "BLOCKED", Reason = e.Message }; }
            var candidates = (families ?? Enumerable.Empty<ConnectionFamily>()).Where(f => f != null && f.ApprovedFingerprints != null
                && f.ApprovedFingerprints.Contains(fingerprint) && f.DetailId == joint.DetailId && f.DetailSha256 == joint.DetailSha256
                && f.AttributesSha256 == joint.AttributesSha256 && f.AttributesSemanticHash == joint.AttributesSemanticHash).ToList();
            if (candidates.Count != 1) return new ConnectionCandidate { Status = candidates.Count == 0 ? "PROPOSE" : "BLOCKED",
                Reason = candidates.Count == 0 ? "No exact proven family/attributes/detail/fingerprint match." : "Conflicting family applicability.",
                JointFingerprint = fingerprint };
            var family = candidates[0];
            var result = new ConnectionCandidate { FamilyId = family.FamilyId, JointFingerprint = fingerprint,
                ExistingNativeId = existing?.NativeId, NativeApplyImplemented = false };
            if (!authority.IsApproved(family.Authority, "connection.family") || !Approved(family.Authority)
                || !BoundArtifact(family.Authority, "CONNECTION_FAMILY_SPEC", family.BindingArtifactId, JsonUtil.HashText(FamilyBindingJson(family))) || !Sha(family.ComponentSourceSha256) || family.Authority.SourceSha256 != family.ComponentSourceSha256
                || string.IsNullOrWhiteSpace(family.ComponentId) || family.Attributes == null || family.Attributes.Count == 0
                || JsonUtil.Hash(family.Attributes) != family.AttributesSemanticHash)
            { result.Status = "BLOCKED"; result.Reason = "Family authority or component/attribute provenance is incomplete."; return result; }
            if (mode == "CHECK_ONLY" || mode == "PROPOSE")
            { result.Status = "PROPOSE"; result.Reason = "Exact proven family available for review; mode does not apply connections."; return result; }
            if (mode != "AUTO") { result.Status = "BLOCKED"; result.Reason = "Unknown connection mode."; return result; }
            if (new[] { joint.Main }.Concat(joint.Secondary).Any(p => authority.ValidateCanonicalPart(p).Count != 0)
                || !ValidRuntime(validation, family, fingerprint) || !ValidClash(clash, validation, fingerprint))
            { result.Status = "BLOCKED"; result.Reason = "AUTO requires exact runtime feature/detail validation and persisted clash proof."; return result; }
            // Native inserts are intentionally outside this service. The caller
            // must separately authorize/apply/save/reopen/readback through the
            // adapter; the current native adapter does not advertise that gate.
            result.Status = "AUTO_READY"; result.Reason = "Authority checks passed; native apply/persistence remains a separate gate.";
            return result;
        }
        public static string FamilyBindingJson(ConnectionFamily f) => CanonicalJson(new
        { Schema = "connection-family-proof/1.0", f.FamilyId, f.ComponentId, f.ComponentSourceSha256, f.AttributesSha256,
            f.AttributesSemanticHash, f.Attributes, f.DetailId, f.DetailSha256, f.ApprovedFingerprints });
        public static string ValidationBindingJson(ConnectionValidationProof p) => CanonicalJson(new
        { Schema = "connection-validation-proof/1.0", p.JointFingerprint, p.FamilyId, p.ComponentSourceSha256,
            p.AttributesSha256, p.DetailSha256, p.ResultHash, p.PlatesValidated, p.BoltsValidated,
            p.WeldsValidated, p.CutsValidated, p.DetailValidated });
        public static string ClashBindingJson(ConnectionClashProof c) => CanonicalJson(new
        { Schema = "connection-clash-proof/1.0", c.JointFingerprint, c.ResultHash, c.NoClashes, c.ToleranceVersion });
        private bool BoundArtifact(EvidenceRecord evidence, string kind, string id, string hash)
        {
            if (string.IsNullOrWhiteSpace(id) || evidence == null) return false;
            var entry = authority.Snapshot().Entries.SingleOrDefault(e => e.Evidence.Component == evidence.Component);
            return entry != null && entry.Artifacts != null && entry.Artifacts.Count(a => a.Id == id && a.Kind == kind && a.Sha256 == hash) == 1;
        }
        private static string CanonicalJson(object payload) => Canonical(JToken.FromObject(payload)).ToString(Newtonsoft.Json.Formatting.None);
        private static JToken Canonical(JToken t)
        {
            if (t is JObject o) return new JObject(o.Properties().OrderBy(p => p.Name, StringComparer.Ordinal).Select(p => new JProperty(p.Name, Canonical(p.Value))));
            if (t is JArray a) return new JArray(a.Select(Canonical));
            return t.DeepClone();
        }
        private static object PartFingerprint(CanonicalPart p) => new
        { p.CanonicalId, p.PhysicalRole, p.SourceId, p.SourceRevision, p.Kind, p.Profile, p.MaterialRaw, p.Material,
            p.GeometryHash, p.ManufacturingHash, p.Points, p.Phase, p.Mark };
        private static void ValidateJoint(ConnectionJoint j)
        {
            if (j == null || j.Model == null || !j.Model.IsComplete || string.IsNullOrWhiteSpace(j.SourceRevision)
                || j.Main == null || j.Secondary == null || j.Secondary.Count == 0 || j.Geometry == null)
                throw new ArgumentException("Joint requires explicit model, source revision, main/secondary and geometry.");
            var all = new[] { j.Main }.Concat(j.Secondary).ToList();
            var keys = new HashSet<string>(StringComparer.Ordinal);
            foreach (var p in all)
            {
                if (p == null || string.IsNullOrWhiteSpace(p.CanonicalId) || string.IsNullOrWhiteSpace(p.PhysicalRole)
                    || !keys.Add(JsonUtil.Hash(new { p.CanonicalId, p.PhysicalRole })) || string.IsNullOrWhiteSpace(p.SourceId)
                    || p.SourceRevision != j.SourceRevision || string.IsNullOrWhiteSpace(p.Profile)
                    || string.IsNullOrWhiteSpace(p.MaterialRaw) || string.IsNullOrWhiteSpace(p.Material)
                    || string.IsNullOrWhiteSpace(p.GeometryHash) || p.Points == null || p.Points.Count < 2
                    || p.Points.Any(v => !Finite(v)))
                    throw new ArgumentException("Unknown, duplicated or stale part/material/profile/geometry; cannot infer joint intent.");
            }
            var g = j.Geometry;
            if (!Finite(g.ContactPoint) || !Direction(g.MainDirection) || !Direction(g.SecondaryDirection)
                || !Finite(g.AngleDegrees) || g.AngleDegrees < 0 || g.AngleDegrees > 180
                || !Finite(g.GapMillimetres) || g.GapMillimetres < 0 || string.IsNullOrWhiteSpace(g.Orientation)
                || string.IsNullOrWhiteSpace(g.GeometryEvidenceId)) throw new ArgumentException("Explicit finite contact/orientation/angle/gap evidence required.");
            if (string.IsNullOrWhiteSpace(j.DetailId) || !Sha(j.DetailSha256) || !Sha(j.AttributesSha256)
                || !Sha(j.AttributesSemanticHash)) throw new ArgumentException("Detail and attributes SHA provenance required.");
        }
        private static bool Finite(double d) => !Double.IsNaN(d) && !Double.IsInfinity(d);
        private static bool Finite(Vec3 v) => v != null && Finite(v.X) && Finite(v.Y) && Finite(v.Z);
        private static bool Direction(Vec3 v) => Finite(v) && v.X * v.X + v.Y * v.Y + v.Z * v.Z > 0.000000001;
        private static bool Sha(string s) => s != null && Regex.IsMatch(s, "^[0-9a-fA-F]{64}$", RegexOptions.CultureInvariant);
        private static bool Approved(EvidenceRecord e) => e != null && e.Status == "APPROVED" && !string.IsNullOrWhiteSpace(e.Component)
            && Sha(e.SourceSha256) && !string.IsNullOrWhiteSpace(e.Commit) && !string.IsNullOrWhiteSpace(e.SchemaVersion)
            && e.TestsPassed && e.RuntimePassed && !string.IsNullOrWhiteSpace(e.ReferenceModel) && e.EvidenceIds != null && e.EvidenceIds.Count > 0;
        private bool ValidRuntime(ConnectionValidationProof p, ConnectionFamily f, string fingerprint) => p != null
            && p.JointFingerprint == fingerprint && p.FamilyId == f.FamilyId && p.ComponentSourceSha256 == f.ComponentSourceSha256
            && p.AttributesSha256 == f.AttributesSha256 && p.DetailSha256 == f.DetailSha256 && Sha(p.ResultHash)
            && p.PlatesValidated && p.BoltsValidated && p.WeldsValidated && p.CutsValidated && p.DetailValidated
            && Approved(p.RuntimeEvidence) && authority.IsApproved(p.RuntimeEvidence, "connection.validation")
            && BoundArtifact(p.RuntimeEvidence, "CONNECTION_VALIDATION", p.BindingArtifactId, JsonUtil.HashText(ValidationBindingJson(p)));
        private bool ValidClash(ConnectionClashProof c, ConnectionValidationProof p, string fingerprint) => c != null && p != null
            && c.JointFingerprint == fingerprint && c.ResultHash == p.ResultHash && c.NoClashes
            && !string.IsNullOrWhiteSpace(c.ToleranceVersion) && Approved(c.RuntimeEvidence) && authority.IsApproved(c.RuntimeEvidence, "connection.clash")
            && BoundArtifact(c.RuntimeEvidence, "CONNECTION_CLASH", c.BindingArtifactId, JsonUtil.HashText(ClashBindingJson(c)));
    }
}
