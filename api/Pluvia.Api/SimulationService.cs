using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.EntityFrameworkCore;
using Pluvia.Api.Data;
using Pluvia.Api.Entities;

namespace Pluvia.Api;

public sealed class SimulationService(PluviaDbContext database, PythonEngine engine, string root)
{
    public JsonObject Manifest { get; } = JsonNode.Parse(File.ReadAllText(Path.Combine(root, "data/pilot-v1/manifest.json")))!.AsObject();
    public JsonObject Geo { get; } = JsonNode.Parse(File.ReadAllText(Path.Combine(root, "data/pilot-v1/cells.geojson")))!.AsObject();
    private static void Access(Account user, object? owner) { if (user.Role != "admin" && (owner is null || Convert.ToInt64(owner) != user.Id)) throw new ApiError(404, "Registro no encontrado."); }
    public object Territory() => new { manifest = Manifest, geojson = Geo, leaflet_local = new[] { "leaflet.js", "leaflet.css" }.All(f => File.Exists(Path.Combine(root, "flood/static/vendor/leaflet", f))) };
    private IQueryable<ScenarioEntity> VisibleScenarios(Account user) => database.Scenarios.Where(s => s.OwnerId == user.Id || user.Role == "admin");
    private static ScenarioResponse ScenarioDto(ScenarioEntity s) => new(s.Id, s.Name, s.OwnerId, JsonSerializer.Deserialize<ScenarioInput>(s.Parameters, JsonDefaults.Options)!, s.CreatedAt, s.UpdatedAt);
    private async Task<ScenarioEntity> FindScenario(Account user, string id, CancellationToken cancellation = default) =>
        await VisibleScenarios(user).SingleOrDefaultAsync(s => s.Id == id, cancellation) ?? throw new ApiError(404, "Escenario no encontrado.");
    public async Task<List<ScenarioResponse>> Scenarios(Account user, CancellationToken cancellation = default) =>
        (await VisibleScenarios(user).AsNoTracking().OrderByDescending(s => s.UpdatedAt).Take(100).ToListAsync(cancellation)).Select(ScenarioDto).ToList();
    public async Task<ScenarioResponse> GetScenario(Account user, string id, CancellationToken cancellation = default) => ScenarioDto(await FindScenario(user, id, cancellation));
    public async Task<string> SaveScenario(Account user, ScenarioRequest request, string? id = null, CancellationToken cancellation = default)
    {
        if (request.Parameters is null || string.IsNullOrWhiteSpace(request.Name) || request.Name.Length > 100) throw new ApiError(400, "Indica un nombre de hasta 100 caracteres y los parámetros.");
        request.Parameters.Validate();
        var now = DateTime.UtcNow.ToString("O");
        var scenario = id is null ? new ScenarioEntity { Id = Guid.NewGuid().ToString("N"), OwnerId = user.Id, CreatedAt = now } : await FindScenario(user, id, cancellation);
        scenario.Name = request.Name.Trim(); scenario.Parameters = JsonDefaults.Encode(request.Parameters); scenario.UpdatedAt = now;
        if (id is null) database.Scenarios.Add(scenario);
        await database.SaveChangesAsync(cancellation);
        return scenario.Id;
    }
    public async Task DeleteScenario(Account user, string id, CancellationToken cancellation = default)
    {
        await using var transaction = await database.Database.BeginTransactionAsync(cancellation);
        var scenario = await FindScenario(user, id, cancellation);
        if (await database.Simulations.AnyAsync(s => s.ScenarioId == id, cancellation))
            throw new ApiError(409, "Este escenario tiene simulaciones. Se conserva para mantener el historial.");
        database.Scenarios.Remove(scenario);
        await database.SaveChangesAsync(cancellation);
        await transaction.CommitAsync(cancellation);
    }
    private static SimulationResponse RunDto(SimulationEntity s, Account user) => new(s.Id, s.ScenarioId, s.CreatedAt,
        JsonSerializer.Deserialize<ScenarioInput>(s.Parameters, JsonDefaults.Options)!, s.Status, s.Error,
        user.Role == "admin" ? s.Owner?.Username ?? "Sin propietario" : null,
        s.Result is null ? 0 : JsonNode.Parse(s.Result.Payload)!["elapsed_s"]!.GetValue<double>());
    private IQueryable<SimulationEntity> VisibleRuns(Account user) => database.Simulations.AsNoTracking().Include(s => s.Owner).Include(s => s.Result).Where(s => s.OwnerId == user.Id || user.Role == "admin");
    public async Task<List<SimulationResponse>> Related(Account user, string id, CancellationToken cancellation = default)
    {
        await FindScenario(user, id, cancellation);
        return (await VisibleRuns(user).Where(s => s.ScenarioId == id).OrderByDescending(s => s.CreatedAt).Take(100).ToListAsync(cancellation)).Select(s => RunDto(s, user)).ToList();
    }
    public async Task<JsonObject> Run(Account user, ScenarioInput? input, string? scenarioId, CancellationToken cancellation)
    {
        // Keep the scenario snapshot and its new execution consistent with concurrent edits/deletes.
        var id = Guid.NewGuid().ToString("N"); var created = DateTime.UtcNow.ToString("O");
        var execution = new SimulationEntity();
        await using (var transaction = await database.Database.BeginTransactionAsync(cancellation))
        {
            if (scenarioId is not null) input = (await GetScenario(user, scenarioId, cancellation)).Parameters;
            if (input is null) throw new ApiError(400, "Faltan los parámetros.");
            input.Validate();
            scenarioId ??= await SaveScenario(user, new("Simulación " + DateTime.Now.ToString("g"), input), cancellation: cancellation);
            execution = new SimulationEntity { Id = id, ScenarioId = scenarioId, OwnerId = user.Id, CreatedAt = created, Parameters = JsonDefaults.Encode(input), Status = "running" };
            database.Simulations.Add(execution);
            await database.SaveChangesAsync(cancellation);
            await transaction.CommitAsync(cancellation);
        }
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
            execution.Status = "completed";
            database.Results.Add(new ResultEntity { SimulationId = id, Payload = data.ToJsonString() });
            await database.SaveChangesAsync(cancellation);
            return data;
        }
        catch (Exception)
        {
            // A cancelled request must still leave an auditable failed execution.
            database.ChangeTracker.Clear();
            await database.Simulations.Where(s => s.Id == id).ExecuteUpdateAsync(set => set.SetProperty(s => s.Status, "failed").SetProperty(s => s.Error, "El cálculo no se completó. Puedes volver a intentarlo."));
            throw;
        }
    }
    public async Task<object> History(Account user, bool warnings, string? status = null)
    {
        if (status is not null && status is not ("running" or "completed" or "failed")) throw new ApiError(400, "Estado inválido.");
        var rows = await VisibleRuns(user).Where(s => status == null || s.Status == status).OrderByDescending(s => s.CreatedAt).Take(100).ToListAsync();
        var runs = rows.Select(s => RunDto(s, user)).ToList();
        if (!warnings) return runs;
        var skipped = user.Role == "admin" ? await database.Metadata.AsNoTracking().SingleOrDefaultAsync(m => m.Key == "legacy_skipped_files") : null;
        return new HistoryResponse(runs, skipped is null ? new JsonArray() : JsonNode.Parse(skipped.Value)!);
    }
    public async Task<object> Get(Account user, string id)
    {
        var execution = await VisibleRuns(user).SingleOrDefaultAsync(s => s.Id == id) ?? throw new ApiError(404, "Ejecución no encontrada.");
        if (execution.Result is not null) return JsonNode.Parse(execution.Result.Payload)!;
        return new { run_id = id, status = execution.Status, error = execution.Error, scenario = JsonNode.Parse(execution.Parameters) };
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
