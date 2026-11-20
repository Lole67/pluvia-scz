using System.Text.Json.Serialization;
namespace Pluvia.Api;

[JsonUnmappedMemberHandling(JsonUnmappedMemberHandling.Disallow)]
public record ScenarioInput([property: JsonRequired] double Rain_mm, [property: JsonRequired] double Duration_h, [property: JsonRequired] double Saturation, [property: JsonRequired] double Drainage_mmh)
{
    public void Validate()
    {
        if (!double.IsFinite(Rain_mm) || Rain_mm < 0 || Rain_mm > 300 ||
            !double.IsFinite(Duration_h) || Duration_h < .1 || Duration_h > 24 ||
            !double.IsFinite(Saturation) || Saturation < 0 || Saturation > 1 ||
            !double.IsFinite(Drainage_mmh) || Drainage_mmh < 0 || Drainage_mmh > 100)
            throw new ApiError(400, "Revisa lluvia (0–300), duración (0,1–24), humedad (0–1) y drenaje (0–100).");
    }
}
[JsonUnmappedMemberHandling(JsonUnmappedMemberHandling.Disallow)]
public record ScenarioRequest([System.ComponentModel.DataAnnotations.Required, System.ComponentModel.DataAnnotations.StringLength(100)] string Name, [System.ComponentModel.DataAnnotations.Required] ScenarioInput Parameters);
public record SimulationRequest([System.ComponentModel.DataAnnotations.Required][property: JsonPropertyName("scenario_id")] string ScenarioId);
public record LoginRequest(string Username, string Password);
public record UserRequest(string Username, string Name, string Password, string Role);
public record UserUpdate([property: JsonRequired] string Role, [property: JsonRequired] bool Active, string? Password);
public record PasswordRequest(string CurrentPassword, string Password, string Confirmation);
public record Account(long Id, string Username, string Name, string Role);
