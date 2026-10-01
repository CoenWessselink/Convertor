using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

namespace Cws.TeklaBridge.Core
{
    public sealed class JournalEntry
    {
        public long Sequence { get; set; }
        public string TimestampUtc { get; set; }
        public string RequestId { get; set; }
        public string RunId { get; set; }
        public string OperationId { get; set; }
        public string PlanHash { get; set; }
        public string ContextHash { get; set; }
        public string MatrixVersion { get; set; }
        public string SourceRevision { get; set; }
        public string ScopeHash { get; set; }
        public string ModelKey { get; set; }
        public string Kind { get; set; }
        public string Key { get; set; }
        public string Message { get; set; }
        public CanonicalPart Before { get; set; }
        public CanonicalPart After { get; set; }
        public AdapterSnapshot Snapshot { get; set; }
        public RunResult Result { get; set; }
    }

    /// <summary>Append-only local write-ahead journal. Corruption and incomplete transactions fail closed.</summary>
    public sealed class JournalStore
    {
        private readonly string directory;
        private readonly string journalPath;
        private readonly object gate = new object();
        public string DirectoryPath { get { return directory; } }
        public JournalStore(string directory)
        {
            if (String.IsNullOrWhiteSpace(directory)) throw new ArgumentException("Journal directory required.");
            this.directory = Path.GetFullPath(directory);
            System.IO.Directory.CreateDirectory(this.directory);
            journalPath = Path.Combine(this.directory, "transactions.jsonl");
            ReadAll(); // Detect pre-existing corrupted evidence before any new write.
        }

        public IDisposable AcquireExclusive()
        {
            return new FileStream(Path.Combine(directory, "transaction.lock"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
        }

        public void Append(JournalEntry entry)
        {
            if (entry == null || String.IsNullOrWhiteSpace(entry.Kind) || String.IsNullOrWhiteSpace(entry.RunId)) throw new ArgumentException("Journal entry kind and run required.");
            lock (gate)
            {
                var history = ReadAll();
                entry.Sequence = history.Count == 0 ? 1 : history[history.Count - 1].Sequence + 1;
                entry.TimestampUtc = DateTime.UtcNow.ToString("O");
                var bytes = Encoding.UTF8.GetBytes(Newtonsoft.Json.Linq.JToken.Parse(JsonUtil.Serialize(entry)).ToString(Newtonsoft.Json.Formatting.None) + "\n");
                using (var stream = new FileStream(journalPath, FileMode.Append, FileAccess.Write, FileShare.Read, 4096, FileOptions.WriteThrough))
                {
                    stream.Write(bytes, 0, bytes.Length);
                    stream.Flush(true); // Intent reaches disk before native mutation begins.
                }
            }
        }

        public List<JournalEntry> ReadAll()
        {
            lock (gate)
            {
                var entries = new List<JournalEntry>();
                if (!File.Exists(journalPath)) return entries;
                foreach (var line in File.ReadLines(journalPath, Encoding.UTF8))
                {
                    if (String.IsNullOrWhiteSpace(line)) throw new InvalidDataException("JOURNAL_CORRUPT: blank/truncated journal record.");
                    JournalEntry entry;
                    try { entry = JsonUtil.Deserialize<JournalEntry>(line); }
                    catch (Exception ex) { throw new InvalidDataException("JOURNAL_CORRUPT: cannot parse complete journal record.", ex); }
                    if (entry == null || entry.Sequence != entries.Count + 1 || String.IsNullOrWhiteSpace(entry.RunId) || String.IsNullOrWhiteSpace(entry.Kind))
                        throw new InvalidDataException("JOURNAL_CORRUPT: invalid journal sequence/identity.");
                    entries.Add(entry);
                }
                return entries;
            }
        }

        public List<JournalEntry> Unfinished()
        {
            var terminal = new[] { "COMMITTED", "ROLLED_BACK", "ABORTED_CLEAN" };
            return ReadAll().GroupBy(x => x.RunId, StringComparer.Ordinal)
                .Where(g => g.Any(x => x.Kind == "BEGIN") && !g.Any(x => terminal.Contains(x.Kind)))
                .Select(g => g.First(x => x.Kind == "BEGIN")).ToList();
        }

        public JournalEntry FindRequest(string requestId)
        {
            return ReadAll().FirstOrDefault(x => x.Kind == "BEGIN" && x.RequestId == requestId);
        }

        public RunResult CompletedResult(string requestId)
        {
            return ReadAll().LastOrDefault(x => x.RequestId == requestId && x.Result != null && new[] { "COMMITTED", "ROLLED_BACK", "ABORTED_CLEAN" }.Contains(x.Kind))?.Result;
        }
    }
}
