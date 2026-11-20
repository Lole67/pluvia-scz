using System.Text.Json;
using System.Text.Json.Serialization;

namespace Pluvia.Api;

public sealed class ApiError(int status, string message) : Exception(message)
{
    public int Status { get; } = status;
}

public static class JsonDefaults
{
    public static readonly JsonSerializerOptions Options = new(JsonSerializerDefaults.Web) { NumberHandling = JsonNumberHandling.Strict };
    public static string Encode<T>(T value) => JsonSerializer.Serialize(value, Options);
}
