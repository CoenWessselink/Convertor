using System;
using System.Collections.Generic;
using System.Linq;
namespace Cws.TeklaBridge.Core
{
    public sealed class PlanStatistics
    {
        public int ItemCount { get; set; }
        public int ScopedCanonicalCount { get; set; }
        public int PlannedPhysicalRoleCount { get; set; }
        public int ExpectedCanonicalCount { get; set; }
        public int ExpectedPhysicalCount { get; set; }
        public Dictionary<string,int> StatusCounts { get; set; }
        public string Domain { get; set; } = "SCOPED_BUILD_PLAN_NOT_ACTUAL_NATIVE_COUNT";
    }
    public static class PlanStatisticsService
    {
        public static PlanStatistics Count(BuildPlan plan)
        {
            if (plan == null || plan.Items == null) throw new ArgumentException("Build-plan required.");
            var scoped = plan.Items.Select(x => x.After ?? x.Before).Where(x => x != null).ToList();
            var expected = ExpectedParts(plan);
            return new PlanStatistics {
                ItemCount = plan.Items.Count,
                ScopedCanonicalCount = scoped.Select(x => x.CanonicalId).Where(x => !String.IsNullOrWhiteSpace(x)).Distinct(StringComparer.Ordinal).Count(),
                PlannedPhysicalRoleCount = plan.Items.Select(x => x.Key).Where(x => !String.IsNullOrWhiteSpace(x)).Distinct(StringComparer.Ordinal).Count(),
                ExpectedCanonicalCount = expected.Select(x => x.CanonicalId).Distinct(StringComparer.Ordinal).Count(),
                ExpectedPhysicalCount = expected.Count,
                StatusCounts = plan.Items.GroupBy(x => x.Status ?? "UNKNOWN", StringComparer.Ordinal).ToDictionary(x => x.Key, x => x.Count(), StringComparer.Ordinal)
            };
        }
        public static List<CanonicalPart> ExpectedParts(BuildPlan plan) => plan.Items.Where(x => x.Status != "REMOVE").Select(x => x.Status == "BLOCK" || x.Status == "REVIEW" ? x.Before : x.After ?? x.Before).Where(x => x != null).ToList();
    }
}
