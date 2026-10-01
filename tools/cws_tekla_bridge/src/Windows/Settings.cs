using System;
using System.IO;
using Cws.TeklaBridge.Core;
namespace Cws.TeklaBridge.Windows
{
    public sealed class BridgeSettings
    {
        public string ExpectedTeklaVersion { get; set; } = "";
        public string LastCanonicalPath { get; set; } = "";
        public string Mode { get; set; } = "PROPOSE";
        public static string WorkDirectory => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "CWS", "TeklaBridge");
        public static BridgeSettings Load()
        {
            string path = Path.Combine(WorkDirectory, "settings.json");
            if (!File.Exists(path)) return new BridgeSettings();
            return JsonUtil.Deserialize<BridgeSettings>(File.ReadAllText(path)) ?? new BridgeSettings();
        }
        public void Save()
        {
            Directory.CreateDirectory(WorkDirectory); string path = Path.Combine(WorkDirectory, "settings.json");
            string temp = path + ".tmp"; File.WriteAllText(temp, JsonUtil.Serialize(this));
            if (File.Exists(path)) File.Replace(temp, path, null); else File.Move(temp, path);
        }
    }
}
