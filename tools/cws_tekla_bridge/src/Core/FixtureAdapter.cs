using System;
using System.Collections.Generic;
using System.Linq;

namespace Cws.TeklaBridge.Core
{
    public interface ICompensatingModelAdapter
    {
        bool RestoreSnapshot(AdapterSnapshot before);
    }

    /// <summary>Explicit test double. It cannot establish native runtime evidence and is never selected by the host.</summary>
    public sealed class FixtureAdapter : IModelAdapter, IMetadataRepairAdapter, ICompensatingModelAdapter
    {
        private ModelIdentity identity;
        private List<CanonicalPart> parts;
        private List<CanonicalPart> saved;
        private List<string> selection = new List<string>();
        private int upserts;
        public string AdapterName { get { return "TEST_FIXTURE"; } }
        public bool IsFixture { get { return true; } }
        public CapabilitySet Capabilities { get; private set; }
        public int UpsertCalls { get { return upserts; } }
        public int RemoveCalls { get; private set; }
        public int SaveCalls { get; private set; }
        public int RepairCalls { get; private set; }
        public int FailOnUpsertCall { get; set; }
        public bool FailAfterMutation { get; set; }
        public bool FailSave { get; set; }
        public bool FailReopen { get; set; }
        public bool FailCompensation { get; set; }
        public bool RevisionTracksState { get; set; }
        public Action<List<CanonicalPart>> OnReadback { get; set; }
        public Action<List<CanonicalPart>> AfterUpsert { get; set; }

        public FixtureAdapter(ModelIdentity identity, IEnumerable<CanonicalPart> parts = null)
        {
            this.identity = JsonUtil.Clone(identity ?? throw new ArgumentNullException(nameof(identity)));
            this.parts = JsonUtil.Clone((parts ?? Enumerable.Empty<CanonicalPart>()).ToList());
            saved = JsonUtil.Clone(this.parts);
            Capabilities = new CapabilitySet();
            foreach (var capability in new[] { "plan.execute", "plan.validate", "part.upsert", "part.remove", "persist.save", "persist.reopen", "transaction.write", "transaction.compensate", "part.safe-metadata-repair", "repair.safe", "model.read", "selection.read", "selection.write", "catalog.read", "readback", "audit" }) Capabilities.Values[capability] = true;
        }
        public ModelIdentity GetIdentity() { var value = JsonUtil.Clone(identity); if (RevisionTracksState) value.Revision = JsonUtil.Hash(parts.OrderBy(PartIdentity.Key, StringComparer.Ordinal).ToList()); return value; }
        public List<CanonicalPart> ReadParts() { return JsonUtil.Clone(parts); }
        public List<string> GetSelection() { return new List<string>(selection); }
        public void SetSelection(List<string> ids)
        {
            if (ids == null || ids.Any(x => parts.All(p => p.NativeId != x))) throw new ArgumentException("Unknown fixture selection native ID.");
            selection = ids.Distinct(StringComparer.Ordinal).ToList();
        }
        public Dictionary<string,List<string>> ReadCatalogs()
        { return new Dictionary<string,List<string>> { ["profiles"] = parts.Select(p => p.Profile).Where(x => !String.IsNullOrEmpty(x)).Distinct().ToList(), ["materials"] = parts.Select(p => p.Material).Where(x => !String.IsNullOrEmpty(x)).Distinct().ToList(), ["components"] = new List<string>(), ["shapes"] = new List<string>() }; }
        public void Upsert(CanonicalPart part)
        {
            upserts++;
            if (FailOnUpsertCall == upserts && !FailAfterMutation) throw new InvalidOperationException("INJECTED_FIXTURE_UPSERT_FAILURE");
            if (part == null || String.IsNullOrEmpty(PartIdentity.Key(part))) throw new ArgumentException("Canonical role identity required.");
            var matches = parts.Where(p => PartIdentity.Key(p) == PartIdentity.Key(part)).ToList();
            if (matches.Count > 1) throw new InvalidOperationException("Duplicate fixture canonical role.");
            var clone = JsonUtil.Clone(part);
            if (matches.Count == 1)
            {
                if (!matches[0].Managed || matches[0].ManualDownstream) throw new InvalidOperationException("Manual fixture object protected.");
                clone.NativeId = matches[0].NativeId;
                parts[parts.IndexOf(matches[0])] = clone;
            }
            else { clone.NativeId = "fixture-" + JsonUtil.HashText(PartIdentity.Key(part)).Substring(0,16); parts.Add(clone); }
            AfterUpsert?.Invoke(parts);
            if (FailOnUpsertCall == upserts && FailAfterMutation) throw new InvalidOperationException("INJECTED_FIXTURE_POST_WRITE_FAILURE");
        }
        public void Remove(CanonicalPart part)
        {
            var target = parts.SingleOrDefault(p => PartIdentity.Key(p) == PartIdentity.Key(part));
            if (target == null) throw new InvalidOperationException("Remove target missing.");
            if (!target.Managed || target.ManualDownstream || target.NativeId != part.NativeId) throw new InvalidOperationException("Remove target provenance mismatch.");
            RemoveCalls++; parts.Remove(target);
        }
        public void Save()
        {
            SaveCalls++;
            if (FailSave) throw new InvalidOperationException("INJECTED_FIXTURE_SAVE_FAILURE");
            saved = JsonUtil.Clone(parts);
        }
        public AdapterSnapshot ReopenAndReadback()
        {
            if (FailReopen) throw new InvalidOperationException("INJECTED_FIXTURE_REOPEN_FAILURE");
            parts = JsonUtil.Clone(saved);
            var readback = JsonUtil.Clone(parts);
            OnReadback?.Invoke(readback);
            return new AdapterSnapshot { Identity = GetIdentity(), Parts = readback, IsFixture = true, PersistenceProof = "TEST_FIXTURE_SAVE_REOPEN:" + JsonUtil.Hash(saved) };
        }
        public void RepairMetadata(CanonicalPart expected, List<string> keys)
        {
            if (keys == null || keys.Any(k => !ReadbackService.SafeMetadataKeys.Contains(k))) throw new ArgumentException("Repair key is not immutable safe metadata.");
            var target = parts.Single(p => PartIdentity.Key(p) == PartIdentity.Key(expected));
            if (!target.Managed || target.ManualDownstream || PartIdentity.ContentHash(WithoutSafeMetadata(target)) != PartIdentity.ContentHash(WithoutSafeMetadata(expected))) throw new InvalidOperationException("Repair immutable preconditions changed.");
            foreach (var key in keys) { if (expected.Udas.ContainsKey(key)) target.Udas[key] = expected.Udas[key]; else target.Udas.Remove(key); }
            RepairCalls++;
        }
        private static CanonicalPart WithoutSafeMetadata(CanonicalPart part)
        { var clone = JsonUtil.Clone(part); foreach (var key in ReadbackService.SafeMetadataKeys) clone.Udas.Remove(key); return clone; }
        public bool RestoreSnapshot(AdapterSnapshot before)
        {
            if (FailCompensation || before == null || !before.IsFixture || !PartIdentity.SameIdentity(GetIdentity(), before.Identity) && !RevisionTracksState) return false;
            parts = JsonUtil.Clone(before.Parts); saved = JsonUtil.Clone(parts); return true;
        }
        public void ChangeModelRevision(string revision) { identity.Revision = revision; }
    }
}
