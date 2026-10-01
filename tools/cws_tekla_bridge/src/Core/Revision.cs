using System;
using System.Collections.Generic;
using System.Linq;

namespace Cws.TeklaBridge.Core
{
    public sealed class RevisionItem
    {
        public string Key { get; set; }
        public string Status { get; set; }
        public CanonicalPart Before { get; set; }
        public CanonicalPart After { get; set; }
        public string Reason { get; set; }
    }

    public sealed class RevisionResult
    {
        public string PreviousRevision { get; set; }
        public string SourceRevision { get; set; }
        public List<RevisionItem> Items { get; set; } = new List<RevisionItem>();
        public bool HasConflicts { get { return Items.Any(x => x.Status == "CONFLICTED"); } }
    }

    /// <summary>Revision comparison is diagnostic; absence alone never authorizes deletion.</summary>
    public static class RevisionService
    {
        public static RevisionResult Compare(SteelModel before, SteelModel after)
        {
            if (before == null || after == null) throw new ArgumentNullException("source");
            var result = new RevisionResult { PreviousRevision = before.SourceRevision, SourceRevision = after.SourceRevision };
            var oldGroups = (before.Parts ?? new List<CanonicalPart>()).GroupBy(PartIdentity.Key).ToDictionary(g => g.Key, g => g.ToList(), StringComparer.Ordinal);
            var newGroups = (after.Parts ?? new List<CanonicalPart>()).GroupBy(PartIdentity.Key).ToDictionary(g => g.Key, g => g.ToList(), StringComparer.Ordinal);
            foreach (var key in oldGroups.Keys.Union(newGroups.Keys).OrderBy(x => x, StringComparer.Ordinal))
            {
                List<CanonicalPart> oldParts, newParts;
                oldGroups.TryGetValue(key, out oldParts); newGroups.TryGetValue(key, out newParts);
                var oldPart = oldParts == null ? null : oldParts[0];
                var newPart = newParts == null ? null : newParts[0];
                var duplicate = (oldParts != null && oldParts.Count != 1) || (newParts != null && newParts.Count != 1);
                var conflict = duplicate || String.IsNullOrWhiteSpace(key) || before.SourceId != after.SourceId ||
                    (newPart != null && (newPart.SourceId != after.SourceId || newPart.SourceRevision != after.SourceRevision));
                var status = conflict ? "CONFLICTED" : oldPart == null ? "ADDED" : newPart == null ? "REMOVED" :
                    PartIdentity.ContentHash(oldPart) == PartIdentity.ContentHash(newPart) ? "UNCHANGED" : "CHANGED";
                result.Items.Add(new RevisionItem { Key = key, Status = status, Before = JsonUtil.Clone(oldPart), After = JsonUtil.Clone(newPart), Reason = conflict ? "Duplicate or inconsistent source identity." : null });
            }
            return result;
        }
    }

    public static class PartIdentity
    {
        public static string Key(CanonicalPart p)
        {
            if (p == null || String.IsNullOrWhiteSpace(p.CanonicalId) || String.IsNullOrWhiteSpace(p.PhysicalRole)) return String.Empty;
            // Length-prefix prevents collisions when source identities contain delimiters.
            return p.CanonicalId.Length + ":" + p.CanonicalId + ":" + p.PhysicalRole.Length + ":" + p.PhysicalRole;
        }

        public static string ContentHash(CanonicalPart p)
        {
            if (p == null) return null;
            return JsonUtil.Hash(new {
                p.CanonicalId, p.PhysicalRole, p.Kind, p.Profile, p.MaterialRaw, p.Material,
                p.GeometryHash, p.ManufacturingHash, p.Points, p.Phase, p.Mark,
                Udas = (p.Udas ?? new Dictionary<string,string>()).OrderBy(k => k.Key, StringComparer.Ordinal).ToArray()
            });
        }

        public static string PersistentHash(CanonicalPart p)
        {
            return p == null ? null : JsonUtil.Hash(new { Content = ContentHash(p), p.SourceId, p.SourceRevision, p.Managed, p.ManualDownstream });
        }

        public static bool SameIdentity(ModelIdentity a, ModelIdentity b)
        {
            return a != null && b != null && a.ModelId == b.ModelId && a.ModelPath == b.ModelPath &&
                a.ModelName == b.ModelName && a.TeklaVersion == b.TeklaVersion && a.Revision == b.Revision;
        }
    }
}
