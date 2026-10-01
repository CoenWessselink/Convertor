using System;
using System.Collections.Generic;
using System.Linq;
using Cws.TeklaBridge.Core;

namespace Cws.TeklaBridge.Native
{
    public sealed class NativeOperationBlockedException : InvalidOperationException
    {
        public string Code { get; }
        public NativeOperationBlockedException(string code, string message) : base(code + ": " + message) { Code = code; }
    }

    public static class NativeGuards
    {
        public const string Owner = "CWS_TEKLA_BRIDGE";
        public static readonly string[] OwnershipUdas = { "CWS_OWNER", "CWS_CANONICAL_ID", "CWS_SOURCE_ID", "CWS_SOURCE_REV", "CWS_PHYSICAL_ROLE", "CWS_SCHEMA" };
        public static bool IsOwned(CanonicalPart part) => part != null && part.Managed && part.Udas != null &&
            Exact(part.Udas,"CWS_OWNER",Owner) && Exact(part.Udas,"CWS_SCHEMA","1.0") &&
            Exact(part.Udas,"CWS_CANONICAL_ID",part.CanonicalId) && Exact(part.Udas,"CWS_SOURCE_ID",part.SourceId) &&
            Exact(part.Udas,"CWS_SOURCE_REV",part.SourceRevision) && Exact(part.Udas,"CWS_PHYSICAL_ROLE",part.PhysicalRole) &&
            !String.IsNullOrWhiteSpace(part.CanonicalId) && !String.IsNullOrWhiteSpace(part.SourceId) && !String.IsNullOrWhiteSpace(part.SourceRevision);
        public static void Protect(CanonicalPart actual, CanonicalPart desired)
        {
            if (!IsOwned(actual) || actual.ManualDownstream) Block("OWNERSHIP_PROTECTED", "Native part is manual, unknown, or has downstream objects; no mutation.");
            if (desired == null || !String.Equals(actual.Key, desired.Key, StringComparison.Ordinal) ||
                !String.Equals(actual.SourceId, desired.SourceId, StringComparison.Ordinal))
                Block("CANONICAL_IDENTITY_MISMATCH", "Source/canonical identity cannot be reassigned.");
        }
        public static void ValidateSimplePayload(CanonicalPart part)
        {
            if (part == null || String.IsNullOrWhiteSpace(part.CanonicalId) || String.IsNullOrWhiteSpace(part.SourceId) ||
                String.IsNullOrWhiteSpace(part.SourceRevision) || String.IsNullOrWhiteSpace(part.PhysicalRole)) Block("SOURCE_IDENTITY_MISSING", "Explicit canonical/source/revision/role required.");
            if (!new[]{"BEAM","POLYBEAM","PLATE"}.Contains(part.Kind)) Block("KIND_NOT_SUPPORTED", "Only native simple beam, polybeam and contour plate candidates exist.");
            if (String.IsNullOrWhiteSpace(part.Profile) || String.IsNullOrWhiteSpace(part.Material) || String.IsNullOrWhiteSpace(part.MaterialRaw))
                Block("CATALOG_VALUE_MISSING", "No material/profile fallback or inference is permitted.");
            if (!String.Equals(part.MaterialRaw,part.Material,StringComparison.Ordinal)) Block("MATERIAL_ALIAS_UNPROVEN", "No value-bound alias authority exists; raw and resolved material must remain exact.");
            if (part.Points == null || part.Points.Any(p => p == null || !Finite(p.X) || !Finite(p.Y) || !Finite(p.Z)))
                Block("GEOMETRY_INVALID", "All explicit points must be finite.");
            int min = part.Kind == "PLATE" ? 3 : 2;
            if (part.Points.Count < min || part.Kind == "BEAM" && part.Points.Count != 2) Block("GEOMETRY_INVALID", "Wrong point count for native kind.");
            if (part.Points.Zip(part.Points.Skip(1),(a,b)=>a.X==b.X && a.Y==b.Y && a.Z==b.Z).Any(x=>x)) Block("GEOMETRY_INVALID", "Consecutive points coincide.");
            if (part.Udas == null || !Exact(part.Udas,"NATIVE_FEATURE_POLICY","EXPLICIT_NO_MANUFACTURING_FEATURES") ||
                !Exact(part.Udas,"NATIVE_GEOMETRY_POLICY","LINEAR_NO_CHAMFERS"))
                Block("MANUFACTURING_NOT_SUPPORTED", "Feature writes are unsupported; explicit no-features and linear-contour policies required.");
        }
        public static void ValidateCatalog(CanonicalPart part, Dictionary<string,List<string>> catalogs)
        {
            if (catalogs == null || !catalogs.TryGetValue("profiles",out var p) || !p.Contains(part.Profile,StringComparer.Ordinal))
                Block("PROFILE_NOT_IN_EXACT_CATALOG", "Exact profile must exist in connected Tekla catalog.");
            if (!catalogs.TryGetValue("materials",out var m) || !m.Contains(part.Material,StringComparer.Ordinal))
                Block("MATERIAL_NOT_IN_EXACT_CATALOG", "Exact material must exist; S275JR is retained and no S355JR default is used.");
        }
        public static bool Finite(double value) => !Double.IsNaN(value) && !Double.IsInfinity(value);
        public static void Block(string code,string message) => throw new NativeOperationBlockedException(code,message);
        public static bool Exact(IDictionary<string,string> values,string key,string expected) => expected != null && values.TryGetValue(key,out var actual) && String.Equals(actual,expected,StringComparison.Ordinal);
    }
}
