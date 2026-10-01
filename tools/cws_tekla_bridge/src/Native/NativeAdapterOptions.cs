using System;
using System.Collections.Generic;
using Cws.TeklaBridge.Core;
namespace Cws.TeklaBridge.Native
{
    public sealed class NativeAdapterOptions
    {
        // Exact observed value from TeklaStructuresInfo.GetCurrentProgramVersion; no automatic year guess.
        public string ExpectedTeklaVersion { get; set; }
        public Dictionary<string,string> ExpectedAssemblySha256 { get; set; } = new Dictionary<string,string>(StringComparer.Ordinal);
        public AuthorityService Authority { get; set; }
        public Func<string,EvidenceRecord> RuntimeEvidence { get; set; }
    }
    public sealed class NativeCapabilityDetail
    {
        public string Name { get; set; }
        public bool Implemented { get; set; }
        public bool RuntimeProven { get; set; }
        public bool Enabled { get; set; }
        public string Reason { get; set; }
    }
    public sealed class NativeDiagnostics
    {
        public string AdapterName { get; set; }
        public string ActualTeklaVersion { get; set; }
        public string ActualTeklaBuild { get; set; }
        public string ReferenceApiVersion { get; set; }
        public string IdentityMethod { get; set; }
        public Dictionary<string,string> AssemblySha256 { get; set; }
        public List<NativeCapabilityDetail> Capabilities { get; set; }
        public List<string> Sources { get; set; }
    }
}
