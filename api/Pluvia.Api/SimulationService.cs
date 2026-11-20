using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Nodes;
using static Pluvia.Api.Database;

namespace Pluvia.Api;

public sealed class SimulationService(Database database, PythonEngine engine, string root)
{
    public JsonObject Manifest { get; } = JsonNode.Parse(File.ReadAllText(Path.Combine(root, "data/pilot-v1/manifest.json")))!.AsObject();
    public JsonObject Geo { get; } = JsonNode.Parse(File.ReadAllText(Path.Combine(root, "data/pilot-v1/cells.geojson")))!.AsObject();
    private static void Access(Account user, object? owner) { if (user.Role != "admin" && (owner is null || Convert.ToInt64(owner) != user.Id)) throw new ApiError(404, "Registro no encontrado."); }
    public object Territory() => new { manifest = Manifest, geojson = Geo, leaflet_local = new[] { "leaflet.js", "leaflet.css" }.All(f => File.Exists(Path.Combine(root, "flood/static/vendor/leaflet", f))) };
    public object Scenarios(Account user)
    {
        using var db = database.Open(); return Query(db, "SELECT * FROM scenarios WHERE owner_id=$p0 OR $p1='admin' ORDER BY updated_at DESC LIMIT 100", user.Id, user.Role)
            .Select(r => new { id = r["id"], name = r["name"], owner_id = r["owner_id"], parameters = JsonNode.Parse((string)r["parameters"]!), created_at = r["created_at"], updated_at = r["updated_at"] });
    }
    public string SaveScenario(Account user, ScenarioRequest request, string? id = null)
    {
        if (request.Parameters is null || string.IsNullOrWhiteSpace(request.Name) || request.Name.Length > 100) throw new ApiError(400, "Indica un nombre de hasta 100 caracteres y los parámetros.");
        request.Parameters.Validate(); using var db = database.Open(); using var tx = db.BeginTransaction(); var now = DateTime.UtcNow.ToString("O");
        if (id is null) { id = Guid.NewGuid().ToString("N"); Execute(db, "INSERT INTO scenarios VALUES($p0,$p1,$p2,$p3,$p4,$p4)", id, user.Id, request.Name.Trim(), JsonDefaults.Encode(request.Parameters), now); }
        else { var row = Query(db, "SELECT * FROM scenarios WHERE id=$p0", id).FirstOrDefault() ?? throw new ApiError(404, "Escenario no encontrado."); Access(user, row["owner_id"]); Execute(db, "UPDATE scenarios SET name=$p0,parameters=$p1,updated_at=$p2 WHERE id=$p3", request.Name.Trim(), JsonDefaults.Encode(request.Parameters), now, id); }
        tx.Commit(); return id;
    }
    public async Task<JsonObject> Run(Account user, ScenarioInput? input, string? scenarioId, CancellationToken cancellation)
    {
        if (scenarioId is not null) { using var read = database.Open(); var row = Query(read, "SELECT * FROM scenarios WHERE id=$p0", scenarioId).FirstOrDefault() ?? throw new ApiError(404, "Escenario no encontrado."); Access(user, row["owner_id"]); input = JsonSerializer.Deserialize<ScenarioInput>((string)row["parameters"]!, JsonDefaults.Options)!; }
        if (input is null) throw new ApiError(400, "Faltan los parámetros."); input.Validate();
        scenarioId ??= SaveScenario(user, new("Simulación " + DateTime.Now.ToString("g"), input));
        var id = Guid.NewGuid().ToString("N"); var created = DateTime.UtcNow.ToString("O");
        using (var db = database.Open()) Execute(db, "INSERT INTO simulations VALUES($p0,$p1,$p2,$p3,'running',$p4,NULL)", id, scenarioId, user.Id, created, JsonDefaults.Encode(input));
        try
        {
            var watch = Stopwatch.StartNew(); var data = await engine.Call(new { scenario = input }, cancellation); watch.Stop();
            var peak = new List<double>(); var indices = new List<double>();
            foreach (var feature in Geo["features"]!.AsArray())
            { var p = feature!["properties"]!; if (p["report"]!.GetValue<bool>()) { int r = p["row"]!.GetValue<int>(), c = p["col"]!.GetValue<int>(); peak.Add(data["maximum_mm"]![r]![c]!.GetValue<double>()); indices.Add(data["index"]![r]![c]!.GetValue<double>()); } }
            data["run_id"] = id; data["scenario_id"] = scenarioId; data["owner_id"] = user.Id; data["owner_username"] = user.Username;
            data["created_at"] = created; data["scenario"] = JsonSerializer.SerializeToNode(input, JsonDefaults.Options); data["elapsed_s"] = watch.Elapsed.TotalSeconds;
            data["territory_version"] = Manifest["version"]!.DeepClone(); data["engine_version"] = "balance-d4-0.1.0"; data["index_version"] = "max-mm-linear-100-v1";
            data["rain_pattern"] = "constant"; data["boundary"] = "closed"; data["mobility_m2_s"] = 20; data["window"] = "duración de lluvia; sin recesión"; data["seed"] = null; data["area"] = "zona piloto fija, reporte central de 16 km²";
            data["summary"] = JsonSerializer.SerializeToNode(new { max_mm = peak.Max(), mean_max_mm = peak.Average(), mean_index = indices.Average(), category_area_km2 = new { baja = indices.Count(n => n < 25) * .0625, media = indices.Count(n => n >= 25 && n < 50) * .0625, alta = indices.Count(n => n >= 50 && n < 75) * .0625, muy_alta = indices.Count(n => n >= 75) * .0625 } });
            data["sources"] = Manifest["sources"]!.DeepClone(); data["warnings"] = Manifest["warnings"]!.DeepClone(); ValidateResult(data);
            using var db = database.Open(); using var tx = db.BeginTransaction(); Execute(db, "INSERT INTO results VALUES($p0,$p1)", id, data.ToJsonString()); Execute(db, "UPDATE simulations SET status='completed' WHERE id=$p0", id); tx.Commit(); return data;
        }
        catch (Exception)
        { using var db = database.Open(); Execute(db, "UPDATE simulations SET status='failed',error=$p0 WHERE id=$p1", "El cálculo no se completó. Puedes volver a intentarlo.", id); throw; }
    }
    public object History(Account user, bool warnings, string? status = null)
    {
        if (status is not null && status is not ("running" or "completed" or "failed")) throw new ApiError(400, "Estado inválido.");
        using var db = database.Open();
        var rows = Query(db, "SELECT s.*,u.username,r.payload FROM simulations s LEFT JOIN users u ON s.owner_id=u.id LEFT JOIN results r ON s.id=r.simulation_id WHERE (s.owner_id=$p0 OR $p1='admin') AND ($p2 IS NULL OR s.status=$p2) ORDER BY s.created_at DESC LIMIT 100", user.Id, user.Role, status);
        var runs = rows.Select(r => new { run_id = r["id"], scenario_id = r["scenario_id"], created_at = r["created_at"], scenario = JsonNode.Parse((string)r["parameters"]!), status = r["status"], error = r["error"], owner_username = user.Role == "admin" ? r["username"] ?? "Sin propietario" : null, elapsed_s = r["payload"] is string payload ? JsonNode.Parse(payload)!["elapsed_s"]!.GetValue<double>() : 0 }).ToArray();
        if (warnings)
        {
            var skipped = user.Role == "admin" ? Query(db, "SELECT value FROM metadata WHERE key='legacy_skipped_files'").FirstOrDefault() : null;
            return new { runs, warnings = skipped is null ? new JsonArray() : JsonNode.Parse((string)skipped["value"]!) };
        }
        return runs;
    }
    public object Get(Account user, string id)
    {
        using var db = database.Open(); var row = Query(db, "SELECT s.*,r.payload FROM simulations s LEFT JOIN results r ON r.simulation_id=s.id WHERE s.id=$p0", id).FirstOrDefault() ?? throw new ApiError(404, "Ejecución no encontrada."); Access(user, row["owner_id"]);
        if (row["payload"] is string result) return JsonNode.Parse(result)!;
        return new { run_id = id, status = row["status"], error = row["error"], scenario = JsonNode.Parse((string)row["parameters"]!) };
    }
    public static void ValidateResult(JsonObject data)
    {
        if (!Guid.TryParseExact(data["run_id"]!.GetValue<string>(), "N", out _)) throw new ApiError(400, "Identificador inválido.");
        if (data["owner_id"] is not null) _ = data["owner_id"]!.GetValue<long>();
        var config = data["scenario"]!.Deserialize<ScenarioInput>(JsonDefaults.Options)!; config.Validate();
        _ = DateTimeOffset.Parse(data["created_at"]!.GetValue<string>());
        foreach (var key in new[] { "territory_version", "engine_version", "index_version" }) if (string.IsNullOrWhiteSpace(data[key]!.GetValue<string>())) throw new ApiError(400, "Versión ausente.");
        foreach (var key in new[] { "maximum_mm", "final_mm", "index" })
        { var matrix = data[key]!.AsArray(); if (matrix.Count != 24 || matrix.Any(r => r!.AsArray().Count != 24 || r.AsArray().Any(v => !double.IsFinite(v!.GetValue<double>())))) throw new ApiError(400, "Matriz de resultado inválida."); }
        foreach (var key in new[] { "max_mm", "mean_index" }) if (!double.IsFinite(data["summary"]![key]!.GetValue<double>())) throw new ApiError(400, "Resumen inválido.");
        if (!double.IsFinite(data["elapsed_s"]!.GetValue<double>()) || data["elapsed_s"]!.GetValue<double>() < 0 || data["ledger"]!.AsArray().Count == 0) throw new ApiError(400, "Resultado incompleto.");
        if (!double.IsFinite(data["tolerance_m3"]!.GetValue<double>())) throw new ApiError(400, "Tolerancia inválida.");
        foreach (var key in new[] { "baja", "media", "alta", "muy_alta" })
            if (!double.IsFinite(data["summary"]!["category_area_km2"]![key]!.GetValue<double>())) throw new ApiError(400, "Categoría inválida.");
        foreach (var key in new[] { "rain_m3", "infiltration_m3", "drainage_m3", "stored_m3", "residual_m3" })
            if (!double.IsFinite(data["ledger"]!.AsArray().Last()![key]!.GetValue<double>())) throw new ApiError(400, "Balance inválido.");
    }
}
