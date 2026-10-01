using System;
using System.Linq;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace Cws.TeklaBridge.Core
{
    public static class JsonUtil
    {
        private static readonly JsonSerializerSettings Settings = new JsonSerializerSettings
        {
            TypeNameHandling = TypeNameHandling.None,
            MissingMemberHandling = MissingMemberHandling.Error,
            DateParseHandling = DateParseHandling.None,
            FloatParseHandling = FloatParseHandling.Double,
            MaxDepth = 64,
            Culture = System.Globalization.CultureInfo.InvariantCulture
        };
        public static string Serialize(object value) => JsonConvert.SerializeObject(value, Formatting.Indented, Settings);
        public static T Deserialize<T>(string json)
        {
            if (json == null) throw new ArgumentNullException(nameof(json));
            // Duplicate keys and special metadata can otherwise disguise caller intent.
            JToken token;
            using (var input = new StringReader(json))
            using (var reader = new JsonTextReader(input) { DateParseHandling = DateParseHandling.None, FloatParseHandling = FloatParseHandling.Double, MaxDepth = 64 })
            {
                token = JToken.Load(reader, new JsonLoadSettings { DuplicatePropertyNameHandling = DuplicatePropertyNameHandling.Error });
                if (reader.Read()) throw new JsonReaderException("Additional JSON content is not permitted.");
            }
            RejectMetadata(token);
            using (var reader = token.CreateReader()) return JsonSerializer.Create(Settings).Deserialize<T>(reader);
        }
        public static T Clone<T>(T value) => Deserialize<T>(Serialize(value));
        public static string Hash(object value)
        {
            var serializer = JsonSerializer.Create(Settings);
            var token = value == null ? JValue.CreateNull() : JToken.FromObject(value, serializer);
            return HashText(Canonical(token).ToString(Formatting.None));
        }
        public static string HashText(string value)
        {
            if (value == null) throw new ArgumentNullException(nameof(value));
            using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(value))).Replace("-", "").ToLowerInvariant();
        }
        public static string HashBytes(byte[] value)
        {
            if (value == null) throw new ArgumentNullException(nameof(value));
            using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(value)).Replace("-", "").ToLowerInvariant();
        }
        private static JToken Canonical(JToken token)
        {
            if (token is JObject obj) return new JObject(obj.Properties().OrderBy(p => p.Name, StringComparer.Ordinal).Select(p => new JProperty(p.Name, Canonical(p.Value))));
            if (token is JArray array) return new JArray(array.Select(Canonical));
            if (token is JValue value && value.Type == JTokenType.Float && (Double.IsNaN(value.Value<double>()) || Double.IsInfinity(value.Value<double>())))
                throw new JsonSerializationException("Non-finite geometry values are not permitted.");
            return token.DeepClone();
        }
        private static void RejectMetadata(JToken token)
        {
            if (token is JObject obj)
            {
                foreach (var prop in obj.Properties())
                {
                    if (prop.Name == "$type" || prop.Name == "$ref" || prop.Name == "$id" || prop.Name == "$values")
                        throw new JsonSerializationException("JSON metadata is not permitted.");
                    RejectMetadata(prop.Value);
                }
            }
            else if (token is JArray array) foreach (var item in array) RejectMetadata(item);
        }
    }
}
