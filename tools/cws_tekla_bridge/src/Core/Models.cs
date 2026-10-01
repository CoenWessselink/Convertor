using System;
using System.Collections.Generic;
using Newtonsoft.Json;

namespace Cws.TeklaBridge.Core
{
    public sealed class Vec3
    {
        public double X { get; set; }
        public double Y { get; set; }
        public double Z { get; set; }
        public Vec3() { }
        public Vec3(double x, double y, double z) { X = x; Y = y; Z = z; }
    }

    public sealed class ScopeSpec
    {
        public string Kind { get; set; } = "ALL";
        public List<string> Values { get; set; } = new List<string>();
        [JsonIgnore] public string Hash => JsonUtil.Hash(this);
    }

    public sealed class ModelIdentity
    {
        public string ModelId { get; set; }
        public string ModelPath { get; set; }
        public string ModelName { get; set; }
        public string TeklaVersion { get; set; }
        public string Revision { get; set; }
        [JsonIgnore] public string Key => JsonUtil.Hash(new { ModelId, ModelPath, TeklaVersion });
        public bool ExactlyEquals(ModelIdentity other) => other != null &&
            String.Equals(ModelId, other.ModelId, StringComparison.Ordinal) &&
            String.Equals(ModelPath, other.ModelPath, StringComparison.Ordinal) &&
            String.Equals(ModelName, other.ModelName, StringComparison.Ordinal) &&
            String.Equals(TeklaVersion, other.TeklaVersion, StringComparison.Ordinal) &&
            String.Equals(Revision, other.Revision, StringComparison.Ordinal);
        [JsonIgnore] public bool IsComplete => !String.IsNullOrWhiteSpace(ModelId) && !String.IsNullOrWhiteSpace(ModelPath) &&
            !String.IsNullOrWhiteSpace(TeklaVersion) && !String.IsNullOrWhiteSpace(Revision);
    }

    public sealed class EvidenceRecord
    {
        public string Status { get; set; }
        public string Component { get; set; }
        public string SourceSha256 { get; set; }
        public string Commit { get; set; }
        public string SchemaVersion { get; set; }
        public bool TestsPassed { get; set; }
        public bool RuntimePassed { get; set; }
        public string ReferenceModel { get; set; }
        public List<string> EvidenceIds { get; set; } = new List<string>();
    }

    public sealed class CanonicalPart
    {
        public string CanonicalId { get; set; }
        public string SourceId { get; set; }
        public string SourceRevision { get; set; }
        public string PhysicalRole { get; set; } = "PRIMARY";
        public string Kind { get; set; }
        public string Profile { get; set; }
        public string MaterialRaw { get; set; }
        public string Material { get; set; }
        public EvidenceRecord MaterialAuthority { get; set; }
        public EvidenceRecord ProfileAuthority { get; set; }
        public EvidenceRecord GeometryAuthority { get; set; }
        public string GeometryHash { get; set; }
        public string ManufacturingHash { get; set; }
        public List<Vec3> Points { get; set; } = new List<Vec3>();
        public string Phase { get; set; }
        public string Mark { get; set; }
        public Dictionary<string, string> Udas { get; set; } = new Dictionary<string, string>(StringComparer.Ordinal);
        public bool Managed { get; set; }
        public bool ManualDownstream { get; set; }
        public string NativeId { get; set; }
        [JsonIgnore] public string Key => (CanonicalId ?? "").Length + ":" + (CanonicalId ?? "") + ":" + (PhysicalRole ?? "").Length + ":" + (PhysicalRole ?? "");
    }

    public sealed class SteelModel
    {
        [JsonProperty(Required = Required.Always)]
        public string SchemaVersion { get; set; } = "1.0";
        public string SourceId { get; set; }
        public string SourceRevision { get; set; }
        public string SourceSha256 { get; set; }
        public string PreviousSourceRevision { get; set; }
        public List<string> ExplicitRemovals { get; set; } = new List<string>();
        public List<CanonicalPart> Parts { get; set; } = new List<CanonicalPart>();
    }

    public sealed class RequestContext
    {
        public string RequestId { get; set; }
        public string RunId { get; set; }
        public string OperationId { get; set; }
        public string Actor { get; set; }
        public string Mode { get; set; } = "CHECK_ONLY";
        public ScopeSpec Scope { get; set; } = new ScopeSpec();
        public ModelIdentity ExpectedModel { get; set; }
        public string SourceRevision { get; set; }
        public bool DryRun { get; set; }
        public string PlanHash { get; set; }
        public string ConfirmationToken { get; set; }
        // These claims are attached by the authenticated transport/local UI only.
        // They are deliberately excluded from request JSON and from clone.
        [JsonIgnore] public TrustedPrincipal Principal { get; set; }
        [JsonIgnore] public string SessionId { get; set; }
        [JsonIgnore] public string MatrixVersion { get; set; }
    }

    public sealed class CapabilitySet
    {
        public Dictionary<string, bool> Values { get; set; } = new Dictionary<string, bool>(StringComparer.Ordinal);
        public bool Supports(string name) => name != null && Values != null && Values.TryGetValue(name, out var supported) && supported;
    }

    public sealed class PlanItem
    {
        public string Status { get; set; }
        public string Key { get; set; }
        public CanonicalPart Before { get; set; }
        public CanonicalPart After { get; set; }
        public string Reason { get; set; }
    }

    public sealed class BuildPlan
    {
        public string PlanId { get; set; }
        public ModelIdentity Model { get; set; }
        public string SourceId { get; set; }
        public string SourceRevision { get; set; }
        public string PreviousSourceRevision { get; set; }
        public string SourceSha256 { get; set; }
        public ScopeSpec Scope { get; set; } = new ScopeSpec();
        public List<string> ExplicitRemovals { get; set; } = new List<string>();
        public List<PlanItem> Items { get; set; } = new List<PlanItem>();
        public string PlanHash { get; set; }
    }

    public sealed class AuditIssue
    {
        public string Code { get; set; }
        public string Key { get; set; }
        public string Message { get; set; }
        public bool Repairable { get; set; }
    }

    public sealed class AuditResult
    {
        public string Status { get; set; }
        public int CanonicalCount { get; set; }
        public int PhysicalCount { get; set; }
        public List<AuditIssue> Issues { get; set; } = new List<AuditIssue>();
        public bool PersistenceProven { get; set; }
    }

    public sealed class AdapterSnapshot
    {
        public ModelIdentity Identity { get; set; }
        public List<CanonicalPart> Parts { get; set; } = new List<CanonicalPart>();
        public string PersistenceProof { get; set; }
        public bool IsFixture { get; set; }
    }

    public sealed class RunResult
    {
        public string RunId { get; set; }
        public string Status { get; set; }
        public string PlanHash { get; set; }
        public int CanonicalCount { get; set; }
        public int PhysicalCount { get; set; }
        public int Mutations { get; set; }
        public AuditResult Audit { get; set; }
        public List<string> Events { get; set; } = new List<string>();
    }

    public interface IModelAdapter
    {
        string AdapterName { get; }
        bool IsFixture { get; }
        CapabilitySet Capabilities { get; }
        ModelIdentity GetIdentity();
        List<CanonicalPart> ReadParts();
        List<string> GetSelection();
        void SetSelection(List<string> ids);
        Dictionary<string, List<string>> ReadCatalogs();
        void Upsert(CanonicalPart part);
        void Remove(CanonicalPart part);
        void Save();
        AdapterSnapshot ReopenAndReadback();
    }
}
