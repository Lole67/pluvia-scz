using System.Text.Json.Serialization;
namespace Pluvia.Api;

[JsonUnmappedMemberHandling(JsonUnmappedMemberHandling.Disallow)]
public record ScenarioInput([property: JsonRequired] double Rain_mm, [property: JsonRequired] double Duration_h, [property: JsonRequired] double Saturation, [property: JsonRequired] double Drainage_mmh, [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] double[]? Rain_profile = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] double[][]? Report_polygon = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] double[][]? Drain_polygon = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] double? Local_mmh = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] bool? Prefer_ml = null)
{
    private static void ValidatePolygon(double[][]? p)
    {
        if (p is null) return;
        if (p.Length is < 3 or > 80 || p.Any(v => v is null || v.Length != 2 || v.Any(n => !double.IsFinite(n) || n < 0 || n > 24)))
            throw new ApiError(400, "Dibuja entre 3 y 80 vértices dentro de la malla piloto.");
        static double Cross(double[] a,double[] b,double[] c) =>
            (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
        double area=0;
        for (int i=0;i<p.Length;i++)
        {
            var a=p[i]; var b=p[(i+1)%p.Length];
            if (a.SequenceEqual(b)) throw new ApiError(400,"Hay vértices repetidos.");
            area+=a[0]*b[1]-a[1]*b[0];
            for(int j=i+2;j<p.Length;j++)
            {
                if(i==0 && j==p.Length-1) continue;
                var c=p[j]; var d=p[(j+1)%p.Length];
                bool overlap=Enumerable.Range(0,2).All(k=>Math.Max(Math.Min(a[k],b[k]),Math.Min(c[k],d[k]))<=Math.Min(Math.Max(a[k],b[k]),Math.Max(c[k],d[k])));
                if(overlap && Cross(a,b,c)*Cross(a,b,d)<=0 && Cross(c,d,a)*Cross(c,d,b)<=0)
                    throw new ApiError(400,"El polígono se cruza. Revisa los vértices.");
            }
        }
        if(Math.Abs(area)<0.000001) throw new ApiError(400,"El área dibujada es demasiado pequeña.");
    }
    public void Validate()
    {
        ValidatePolygon(Report_polygon);
        ValidatePolygon(Drain_polygon);
        if ((Drain_polygon is null) != (Local_mmh is null) || Local_mmh is < 0 or > 100)
            throw new ApiError(400, "Indica un polígono de drenaje y una tasa local entre 0 y 100 mm/h.");
        if (Rain_profile is not null && (Rain_profile.Length is < 1 or > 48 ||
            Rain_profile.Any(w => !double.IsFinite(w) || w < 0 || w > 100) || Math.Abs(Rain_profile.Sum() - 100) > 1e-6))
            throw new ApiError(400, "El perfil requiere de 1 a 48 porcentajes que sumen 100.");
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
