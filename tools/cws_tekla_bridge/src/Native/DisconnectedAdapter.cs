using System.Collections.Generic;
using Cws.TeklaBridge.Core;

namespace Cws.TeklaBridge.Native
{
    // Production UI's disconnected state. Never a fixture and never an empty real model.
    public sealed class DisconnectedAdapter : IModelAdapter
    {
        public string Reason { get; }
        public DisconnectedAdapter(string reason = null) { Reason = reason ?? "No verified Windows x64 Tekla session configured."; }
        public string AdapterName => "TEKLA_DISCONNECTED";
        public bool IsFixture => false;
        public CapabilitySet Capabilities => new CapabilitySet();
        private NativeOperationBlockedException Block() => new NativeOperationBlockedException("TEKLA_DISCONNECTED",Reason);
        public ModelIdentity GetIdentity() => throw Block();
        public List<CanonicalPart> ReadParts() => throw Block();
        public List<string> GetSelection() => throw Block();
        public void SetSelection(List<string> ids) => throw Block();
        public Dictionary<string,List<string>> ReadCatalogs() => throw Block();
        public void Upsert(CanonicalPart part) => throw Block();
        public void Remove(CanonicalPart part) => throw Block();
        public void Save() => throw Block();
        public AdapterSnapshot ReopenAndReadback() => throw Block();
    }
}
