using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace Cws.TeklaBridge.Core
{
    public sealed class ApiRequest
    {
        public string Method { get; set; }
        public string Path { get; set; }
        public string Body { get; set; }
        public string RequestId { get; set; }
    }
    public sealed class ApiResponse
    {
        public int StatusCode { get; set; }
        public object Body { get; set; }
        public static ApiResponse Ok(object body) { return new ApiResponse { StatusCode = 200, Body = body }; }
        public static ApiResponse Error(int status, string code, string reason) { return new ApiResponse { StatusCode = status, Body = new { ok = false, code, reason } }; }
    }

    /// <summary>Small HTTP/1.1 loopback transport. One request per connection, no browser origins or ambient authentication.</summary>
    public sealed class ApiServer : IDisposable
    {
        public const int MaximumHeaderBytes = 16384;
        public const int MaximumBodyBytes = 1024 * 1024;
        private readonly Func<ApiRequest, Task<ApiResponse>> handler;
        private readonly int requestedPort;
        private readonly int readTimeoutMilliseconds;
        private readonly ConcurrentDictionary<TcpClient, byte> clients = new ConcurrentDictionary<TcpClient, byte>();
        private readonly SemaphoreSlim slots = new SemaphoreSlim(8, 8);
        private TcpListener listener;
        private CancellationTokenSource stopping;
        private string sessionToken;
        private long authenticatedCount;
        public Uri BaseUri { get; private set; }
        /// <summary>Only share through an explicit local UI action. Never log or write to an unprotected session file.</summary>
        public string SessionToken { get { return sessionToken; } }
        public long AuthenticatedRequestCount { get { return Interlocked.Read(ref authenticatedCount); } }
        public bool Running { get { return listener != null && stopping != null && !stopping.IsCancellationRequested; } }
        public ApiServer(Func<ApiRequest, Task<ApiResponse>> handler, int port = 0, int readTimeoutMilliseconds = 5000)
        {
            this.handler = handler ?? throw new ArgumentNullException(nameof(handler));
            if (port < 0 || port > 65535) throw new ArgumentOutOfRangeException(nameof(port));
            if (readTimeoutMilliseconds < 100 || readTimeoutMilliseconds > 30000) throw new ArgumentOutOfRangeException(nameof(readTimeoutMilliseconds));
            requestedPort = port; this.readTimeoutMilliseconds = readTimeoutMilliseconds;
        }
        public void Start()
        {
            if (Running) throw new InvalidOperationException("API_ALREADY_RUNNING");
            byte[] bytes = new byte[32]; using (var crypto = RandomNumberGenerator.Create()) crypto.GetBytes(bytes);
            sessionToken = Convert.ToBase64String(bytes);
            stopping = new CancellationTokenSource();
            listener = new TcpListener(IPAddress.Loopback, requestedPort); listener.Start(16);
            BaseUri = new Uri("http://127.0.0.1:" + ((IPEndPoint)listener.LocalEndpoint).Port + "/");
            _ = AcceptLoop(stopping.Token);
        }
        private async Task AcceptLoop(CancellationToken stop)
        {
            while (!stop.IsCancellationRequested)
            {
                TcpClient client;
                try { client = await listener.AcceptTcpClientAsync().ConfigureAwait(false); }
                catch (Exception) { if (stop.IsCancellationRequested) return; continue; }
                if (!slots.Wait(0)) { client.Dispose(); continue; }
                clients.TryAdd(client, 0);
                _ = Process(client, stop);
            }
        }
        private async Task Process(TcpClient client, CancellationToken stop)
        {
            using (client)
            {
                try
                {
                    client.NoDelay = true;
                    using (var stream = client.GetStream())
                    {
                        var reading = ReadRequest(stream);
                        var completed = await Task.WhenAny(reading, Task.Delay(readTimeoutMilliseconds, stop)).ConfigureAwait(false);
                        if (completed != reading)
                        {
                            await WriteResponse(stream, ApiResponse.Error(408, "REQUEST_TIMEOUT", "Request niet tijdig ontvangen.")).ConfigureAwait(false);
                            client.Close();
                            try { await reading.ConfigureAwait(false); } catch (Exception) { }
                            return;
                        }
                        var parsed = await reading.ConfigureAwait(false);
                        ApiResponse response;
                        if (parsed.Error != null) response = parsed.Error;
                        else
                        {
                            Interlocked.Increment(ref authenticatedCount);
                            try { response = await handler(parsed.Request).ConfigureAwait(false); }
                            catch (Exception) { response = ApiResponse.Error(500, "INTERNAL_ERROR", "Request mislukt. Bekijk het lokale logboek."); }
                        }
                        await WriteResponse(stream, response).ConfigureAwait(false);
                    }
                }
                catch (Exception) { /* Closed, malformed or disconnected clients receive no model access. */ }
                finally { clients.TryRemove(client, out _); slots.Release(); }
            }
        }
        private sealed class Parsed { public ApiRequest Request; public ApiResponse Error; }
        private async Task<Parsed> ReadRequest(NetworkStream stream)
        {
            var header = new MemoryStream(); byte[] one = new byte[1]; int matched = 0;
            byte[] end = { 13, 10, 13, 10 };
            while (matched != 4)
            {
                if (header.Length >= MaximumHeaderBytes) return Fail(431, "HEADER_TOO_LARGE");
                if (await stream.ReadAsync(one, 0, 1).ConfigureAwait(false) != 1) return Fail(400, "INCOMPLETE_HEADER");
                byte b = one[0]; if (b > 127 || b == 0) return Fail(400, "INVALID_HEADER");
                header.WriteByte(b); matched = b == end[matched] ? matched + 1 : (b == 13 ? 1 : 0);
            }
            string[] lines = Encoding.ASCII.GetString(header.ToArray()).Split(new[] { "\r\n" }, StringSplitOptions.None);
            string[] first = lines[0].Split(' ');
            if (first.Length != 3 || first[2] != "HTTP/1.1" || (first[0] != "GET" && first[0] != "POST")) return Fail(400, "INVALID_REQUEST_LINE");
            if (!first[1].StartsWith("/api/v1/", StringComparison.Ordinal) || first[1].IndexOfAny(new[] { '#', '?', '\\', '%' }) >= 0 || first[1].Contains("//")) return Fail(400, "INVALID_PATH");
            foreach (char c in first[1]) if (!(c >= 'a' && c <= 'z' || c >= '0' && c <= '9' || c == '/' || c == '-')) return Fail(400, "INVALID_PATH");
            var headers = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            for (int i = 1; i < lines.Length - 2; i++)
            {
                int colon = lines[i].IndexOf(':');
                if (colon <= 0 || lines[i].Length == 0 || Char.IsWhiteSpace(lines[i][0])) return Fail(400, "INVALID_HEADER");
                string key = lines[i].Substring(0, colon);
                foreach (char c in key) if (!(Char.IsLetterOrDigit(c) || c == '-')) return Fail(400, "INVALID_HEADER");
                if (headers.ContainsKey(key)) return Fail(400, "DUPLICATE_HEADER");
                string rawValue = lines[i].Substring(colon + 1);
                foreach (char c in rawValue) if (c < 32 && c != '\t' || c == 127) return Fail(400, "INVALID_HEADER");
                headers.Add(key, rawValue.Trim());
            }
            string value;
            if (!headers.TryGetValue("Host", out value) || value != BaseUri.Authority) return Fail(403, "HOST_DENIED");
            if (headers.ContainsKey("Origin") || headers.ContainsKey("Referer")) return Fail(403, "BROWSER_ORIGIN_DENIED");
            if (headers.ContainsKey("Transfer-Encoding") || headers.ContainsKey("Expect")) return Fail(400, "TRANSFER_MODE_DENIED");
            if (!headers.TryGetValue("Authorization", out value) || !SecretEquals(value, "Bearer " + sessionToken)) return Fail(401, "SESSION_REQUIRED");
            int length = 0;
            if (headers.TryGetValue("Content-Length", out value))
            {
                if (value.Length == 0 || value.Length > 10) return Fail(400, "INVALID_CONTENT_LENGTH");
                foreach (char c in value) if (c < '0' || c > '9') return Fail(400, "INVALID_CONTENT_LENGTH");
                if (!Int32.TryParse(value, NumberStyles.None, CultureInfo.InvariantCulture, out length)) return Fail(413, "BODY_TOO_LARGE");
            }
            else if (first[0] == "POST") return Fail(411, "CONTENT_LENGTH_REQUIRED");
            if (length > MaximumBodyBytes) return Fail(413, "BODY_TOO_LARGE");
            if (first[0] == "GET" && length != 0) return Fail(400, "GET_BODY_DENIED");
            if (length > 0 && (!headers.TryGetValue("Content-Type", out value) || (value != "application/json" && value != "application/json; charset=utf-8"))) return Fail(415, "JSON_REQUIRED");
            byte[] body = new byte[length]; int offset = 0;
            while (offset < length)
            {
                int n = await stream.ReadAsync(body, offset, length - offset).ConfigureAwait(false);
                if (n == 0) return Fail(400, "INCOMPLETE_BODY"); offset += n;
            }
            string text;
            try { text = new UTF8Encoding(false, true).GetString(body); } catch (DecoderFallbackException) { return Fail(400, "INVALID_UTF8"); }
            return new Parsed { Request = new ApiRequest { Method = first[0], Path = first[1], Body = text, RequestId = Guid.NewGuid().ToString("N") } };
        }
        private static bool SecretEquals(string value, string expected)
        {
            int diff = value.Length ^ expected.Length; int count = Math.Max(value.Length, expected.Length);
            for (int i = 0; i < count; i++) diff |= (i < value.Length ? value[i] : 0) ^ (i < expected.Length ? expected[i] : 0);
            return diff == 0;
        }
        private static Parsed Fail(int status, string code) { return new Parsed { Error = ApiResponse.Error(status, code, "HTTP-request geweigerd.") }; }
        private static async Task WriteResponse(NetworkStream stream, ApiResponse response)
        {
            if (response == null) response = ApiResponse.Error(500, "EMPTY_RESPONSE", "Geen resultaat.");
            byte[] body = Encoding.UTF8.GetBytes(JsonUtil.Serialize(response.Body));
            string phrase = response.StatusCode == 200 ? "OK" : "Rejected";
            byte[] head = Encoding.ASCII.GetBytes("HTTP/1.1 " + response.StatusCode + " " + phrase + "\r\nContent-Type: application/json; charset=utf-8\r\nContent-Length: " + body.Length + "\r\nConnection: close\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\n\r\n");
            await stream.WriteAsync(head, 0, head.Length).ConfigureAwait(false); await stream.WriteAsync(body, 0, body.Length).ConfigureAwait(false);
        }
        public void Dispose()
        {
            var cancel = stopping; if (cancel != null) cancel.Cancel();
            var active = listener; listener = null; if (active != null) active.Stop();
            foreach (var client in clients.Keys) client.Dispose();
            sessionToken = null;
        }
    }
}
