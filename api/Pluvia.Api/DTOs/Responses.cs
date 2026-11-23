namespace Pluvia.Api;

public record ErrorResponse(string Error);
public record LoginResponse(string Token, DateTimeOffset Expires_at, Account User);
public record UserResponse(long Id, string Username, string Name, string Role, long Active);
public record UserIdResponse(long Id);
public record TerritoryResponse(System.Text.Json.Nodes.JsonObject Manifest, System.Text.Json.Nodes.JsonObject Geojson, bool Leaflet_local,
    System.Text.Json.Nodes.JsonObject? Soilgrids);
public record IdResponse(string Id);
public record ScenarioResponse(string Id, string Name, long? Owner_id, ScenarioInput Parameters, string Created_at, string Updated_at);
public record SimulationResponse(string Run_id, string? Scenario_id, string Created_at, ScenarioInput Scenario, string Status, string? Error, string? Owner_username, double Elapsed_s);
public record HistoryResponse(IReadOnlyList<SimulationResponse> Runs, System.Text.Json.Nodes.JsonNode Warnings);
