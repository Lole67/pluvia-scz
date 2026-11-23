namespace Pluvia.Api.Entities;

public sealed class UserEntity
{
    public long Id { get; set; }
    public string Username { get; set; } = "";
    public string Name { get; set; } = "";
    public string PasswordHash { get; set; } = "";
    public string Role { get; set; } = "client";
    public bool Active { get; set; } = true;
}
public sealed class ScenarioEntity
{
    public string Id { get; set; } = "";
    public long? OwnerId { get; set; }
    public UserEntity? Owner { get; set; }
    public string Name { get; set; } = "";
    public string Parameters { get; set; } = "";
    public string CreatedAt { get; set; } = "";
    public string UpdatedAt { get; set; } = "";
    public ICollection<SimulationEntity> Simulations { get; set; } = new List<SimulationEntity>();
}
public sealed class SimulationEntity
{
    public string Id { get; set; } = "";
    public string? ScenarioId { get; set; }
    public ScenarioEntity? Scenario { get; set; }
    public long? OwnerId { get; set; }
    public UserEntity? Owner { get; set; }
    public string CreatedAt { get; set; } = "";
    public string Status { get; set; } = "running";
    public string Parameters { get; set; } = "";
    public string? Error { get; set; }
    public ResultEntity? Result { get; set; }
}
public sealed class ResultEntity
{
    public string SimulationId { get; set; } = "";
    public SimulationEntity Simulation { get; set; } = null!;
    public string Payload { get; set; } = "";
}
public sealed class SessionEntity
{
    public string TokenHash { get; set; } = "";
    public long UserId { get; set; }
    public UserEntity User { get; set; } = null!;
    public long Expires { get; set; }
}
public sealed class MetadataEntity
{
    public string Key { get; set; } = "";
    public string Value { get; set; } = "";
}
