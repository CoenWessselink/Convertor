using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Reflection;
using System.Net;
using System.Threading.Tasks;
using System.Windows.Forms;
using Cws.TeklaBridge.Core;
namespace Cws.TeklaBridge.Windows
{
    internal static class Program
    {
        [STAThread]
        private static void Main(string[] args)
        {
            Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
            bool smoke = args.Length == 2 && args[0] == "--smoke";
            using (var form = new MainForm(smoke))
            {
                if (smoke) form.Shown += async (s, e) =>
                {
                    string output = Path.GetFullPath(args[1]); Directory.CreateDirectory(output);
                    try
                    {
                        await Task.Delay(300);
                        var request = (HttpWebRequest)WebRequest.Create(new Uri(form.Server.BaseUri, "api/v1/health"));
                        request.Proxy = null; request.Headers[HttpRequestHeader.Authorization] = "Bearer " + form.Server.SessionToken;
                        string health;
                        using (var response = await request.GetResponseAsync()) using (var reader = new StreamReader(response.GetResponseStream())) health = await reader.ReadToEndAsync();
                        if (form.ScreenCount != 11 || form.Fixture || !health.Contains("ok")) throw new InvalidOperationException("Smoke contract failed.");
                        using (var bitmap = new Bitmap(form.Width, form.Height)) { form.DrawToBitmap(bitmap, form.ClientRectangle); bitmap.Save(Path.Combine(output, "Windows_Bridge_DISCONNECTED.png"), ImageFormat.Png); }
                        File.WriteAllText(Path.Combine(output, "windows-startup.json"), JsonUtil.Serialize(new { SchemaVersion = "1.0", SourceVersion = typeof(Program).Assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion, RecordedAtUtc = DateTime.UtcNow.ToString("o"), Status = "PASS_DISCONNECTED_UI_ONLY", OS = Environment.OSVersion.ToString(), X64 = Environment.Is64BitProcess, Screens = form.ScreenCount, Adapter = form.AdapterName, Fixture = form.Fixture, ApiHealth = JsonUtil.Deserialize<object>(health), ActiveTeklaGate = "NOT_RUN", NativeWrites = "NOT_RUN", ProductionRelease = "BLOCKED", Screenshot = "Windows_Bridge_DISCONNECTED.png" }));
                    }
                    catch (Exception ex)
                    { File.WriteAllText(Path.Combine(output, "windows-startup.json"), JsonUtil.Serialize(new { Status = "FAILED", Error = ex.ToString() })); Environment.ExitCode = 1; }
                    finally { form.Close(); }
                };
                Application.Run(form);
            }
        }
    }
}
