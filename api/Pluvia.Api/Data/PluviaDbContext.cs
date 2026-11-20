using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;
using Pluvia.Api.Entities;

namespace Pluvia.Api.Data;

public sealed class PluviaDbContext(DbContextOptions<PluviaDbContext> options) : DbContext(options)
{
    public DbSet<UserEntity> Users => Set<UserEntity>();
    public DbSet<ScenarioEntity> Scenarios => Set<ScenarioEntity>();
    public DbSet<SimulationEntity> Simulations => Set<SimulationEntity>();
    public DbSet<ResultEntity> Results => Set<ResultEntity>();
    public DbSet<SessionEntity> Sessions => Set<SessionEntity>();
    public DbSet<MetadataEntity> Metadata => Set<MetadataEntity>();

    protected override void OnModelCreating(ModelBuilder model)
    {
        model.Entity<UserEntity>(e =>
        {
            e.ToTable("users", t => t.HasCheckConstraint("CK_users_role", "role IN ('admin','client')"));
            e.HasKey(x => x.Id); e.HasIndex(x => x.Username).IsUnique();
            e.Property(x => x.PasswordHash).HasColumnName("password_hash");
            e.Property(x => x.Active).HasDefaultValue(true);
        });
        model.Entity<ScenarioEntity>(e =>
        {
            e.ToTable("scenarios"); e.HasKey(x => x.Id);
            e.Property(x => x.OwnerId).HasColumnName("owner_id");
            e.Property(x => x.CreatedAt).HasColumnName("created_at");
            e.Property(x => x.UpdatedAt).HasColumnName("updated_at");
            e.HasOne(x => x.Owner).WithMany().HasForeignKey(x => x.OwnerId).OnDelete(DeleteBehavior.Restrict);
        });
        model.Entity<SimulationEntity>(e =>
        {
            e.ToTable("simulations", t => t.HasCheckConstraint("CK_simulations_status", "status IN ('running','completed','failed')"));
            e.HasKey(x => x.Id);
            e.Property(x => x.ScenarioId).HasColumnName("scenario_id");
            e.Property(x => x.OwnerId).HasColumnName("owner_id");
            e.Property(x => x.CreatedAt).HasColumnName("created_at");
            e.HasIndex(x => new { x.OwnerId, x.CreatedAt }).HasDatabaseName("ix_runs_owner");
            e.HasOne(x => x.Owner).WithMany().HasForeignKey(x => x.OwnerId).OnDelete(DeleteBehavior.Restrict);
            e.HasOne(x => x.Scenario).WithMany(x => x.Simulations).HasForeignKey(x => x.ScenarioId).OnDelete(DeleteBehavior.Restrict);
        });
        model.Entity<ResultEntity>(e =>
        {
            e.ToTable("results"); e.HasKey(x => x.SimulationId);
            e.Property(x => x.SimulationId).HasColumnName("simulation_id");
            e.HasOne(x => x.Simulation).WithOne(x => x.Result).HasForeignKey<ResultEntity>(x => x.SimulationId).OnDelete(DeleteBehavior.Restrict);
        });
        model.Entity<SessionEntity>(e =>
        {
            e.ToTable("sessions"); e.HasKey(x => x.TokenHash);
            e.Property(x => x.TokenHash).HasColumnName("token_hash");
            e.Property(x => x.UserId).HasColumnName("user_id");
            e.HasOne(x => x.User).WithMany().HasForeignKey(x => x.UserId).OnDelete(DeleteBehavior.Restrict);
        });
        model.Entity<MetadataEntity>().ToTable("metadata").HasKey(x => x.Key);
        foreach (var entity in model.Model.GetEntityTypes())
            foreach (var property in entity.GetProperties())
                if (property.GetColumnName() == property.Name)
                    property.SetColumnName(property.Name.ToLowerInvariant());
    }
}

// Design-time creation never starts the server or requests administrator credentials.
public sealed class PluviaDbContextFactory : IDesignTimeDbContextFactory<PluviaDbContext>
{
    public PluviaDbContext CreateDbContext(string[] args)
    {
        var root = Environment.GetEnvironmentVariable("PLUVIA_ROOT") ?? Directory.GetCurrentDirectory();
        if (!Directory.Exists(Path.Combine(root, "data/pilot-v1"))) root = Path.GetFullPath(Path.Combine(root, "../.."));
        var data = Environment.GetEnvironmentVariable("PLUVIA_DATA") ?? Path.Combine(root, "data/private");
        Directory.CreateDirectory(data);
        return new(new DbContextOptionsBuilder<PluviaDbContext>().UseSqlite(
            new Microsoft.Data.Sqlite.SqliteConnectionStringBuilder { DataSource = Path.Combine(data, "pluvia.sqlite3"), ForeignKeys = true }.ToString()).Options);
    }
}
