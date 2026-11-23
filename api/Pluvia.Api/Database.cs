using Microsoft.EntityFrameworkCore;
using Microsoft.Data.Sqlite;
using System.Text.Json.Nodes;

namespace Pluvia.Api;

public sealed class Database
{
    public string PathName { get; }
    public Database(string path)
    {
        SQLitePCL.Batteries_V2.Init();
        PathName = path;
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        using var db = Open();
        // Take a consistent SQLite backup before adopting an existing installation.
        var hasUsers = Query(db, "SELECT name FROM sqlite_master WHERE type='table' AND name='users'").Count > 0;
        var hasMigrations = Query(db, "SELECT name FROM sqlite_master WHERE type='table' AND name='__EFMigrationsHistory'").Count > 0;
        if (hasUsers && !hasMigrations)
        {
            var backupFolder = Path.Combine(Path.GetDirectoryName(path)!, "backups", "before-ef-" + DateTime.UtcNow.ToString("yyyyMMddTHHmmssfff"));
            Directory.CreateDirectory(backupFolder);
            using var copy = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = Path.Combine(backupFolder, "pluvia.sqlite3") }.ToString());
            copy.Open(); db.BackupDatabase(copy);
        }
        Execute(db, "PRAGMA journal_mode=WAL;");
        using var context = new Pluvia.Api.Data.PluviaDbContext(new Microsoft.EntityFrameworkCore.DbContextOptionsBuilder<Pluvia.Api.Data.PluviaDbContext>().UseSqlite(db).Options);
        context.Database.Migrate();
    }
    public SqliteConnection Open()
    {
        var db = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = PathName, ForeignKeys = true, DefaultTimeout = 15 }.ToString());
        db.Open(); return db;
    }
    public static SqliteCommand Command(SqliteConnection db, string sql, params object?[] values)
    {
        var cmd = db.CreateCommand(); cmd.CommandText = sql;
        for (var i = 0; i < values.Length; i++) cmd.Parameters.AddWithValue("$p" + i, values[i] ?? DBNull.Value);
        return cmd;
    }
    public static int Execute(SqliteConnection db, string sql, params object?[] values)
    { using var cmd = Command(db, sql, values); return cmd.ExecuteNonQuery(); }
    public static List<Dictionary<string, object?>> Query(SqliteConnection db, string sql, params object?[] values)
    {
        using var cmd = Command(db, sql, values); using var reader = cmd.ExecuteReader();
        var rows = new List<Dictionary<string, object?>>();
        while (reader.Read()) { var row = new Dictionary<string, object?>(); for (var i = 0; i < reader.FieldCount; i++) row[reader.GetName(i)] = reader.IsDBNull(i) ? null : reader.GetValue(i); rows.Add(row); }
        return rows;
    }
    public void ImportLegacy(string root)
    {
        using var db = Open();
        if (Query(db, "SELECT key FROM metadata WHERE key='legacy_import'").Count > 0) return;
        var legacyPath = System.IO.Path.Combine(root, "data/private/accounts.sqlite3");
        var files = Directory.Exists(System.IO.Path.Combine(root, "data/runs")) ? Directory.GetFiles(System.IO.Path.Combine(root, "data/runs"), "*.json") : [];
        var backup = System.IO.Path.Combine(System.IO.Path.GetDirectoryName(PathName)!, "backups", DateTime.UtcNow.ToString("yyyyMMddTHHmmssfff"));
        if (File.Exists(legacyPath) || files.Length > 0) Directory.CreateDirectory(backup);
        using var tx = db.BeginTransaction();
        if (File.Exists(legacyPath))
        {
            using var old = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = legacyPath, Mode = SqliteOpenMode.ReadOnly }.ToString()); old.Open();
            using (var copy = new SqliteConnection($"Data Source={System.IO.Path.Combine(backup, "accounts.sqlite3")}")) { copy.Open(); old.BackupDatabase(copy); }
            foreach (var u in Query(old, "SELECT id,username,name,password_hash,role,active FROM users"))
                Execute(db, "INSERT INTO users VALUES($p0,$p1,$p2,$p3,$p4,$p5)", u["id"], u["username"], u["name"], u["password_hash"], u["role"], u["active"]);
        }
        var skipped = new List<string>();
        foreach (var file in files)
        {
            File.Copy(file, System.IO.Path.Combine(backup, System.IO.Path.GetFileName(file)), false);
            JsonObject result;
            try { result = JsonNode.Parse(File.ReadAllText(file))!.AsObject(); SimulationService.ValidateResult(result); }
            catch (Exception e) when (e is System.Text.Json.JsonException or InvalidOperationException or NullReferenceException or FormatException or ApiError or OverflowException) { skipped.Add(System.IO.Path.GetFileName(file)); continue; }
            var id = result["run_id"]!.GetValue<string>();
            if (!file.EndsWith("_" + id + ".json", StringComparison.OrdinalIgnoreCase) || Query(db, "SELECT id FROM simulations WHERE id=$p0", id).Count > 0) { skipped.Add(System.IO.Path.GetFileName(file)); continue; }
            long? owner = result["owner_id"]?.GetValue<long>();
            if (owner is not null && Query(db, "SELECT id FROM users WHERE id=$p0", owner).Count == 0) owner = null;
            var scenarioId = Guid.NewGuid().ToString("N");
            result["scenario_id"] = scenarioId;
            result["owner_id"] = owner;
            var parameters = result["scenario"]!.ToJsonString(); var created = result["created_at"]!.GetValue<string>();
            Execute(db, "INSERT INTO scenarios VALUES($p0,$p1,$p2,$p3,$p4,$p4)", scenarioId, owner, "Importado", parameters, created);
            Execute(db, "INSERT INTO simulations(id,scenario_id,owner_id,created_at,status,parameters,error) VALUES($p0,$p1,$p2,$p3,'completed',$p4,NULL)", id, scenarioId, owner, created, parameters);
            Execute(db, "INSERT INTO results VALUES($p0,$p1)", id, result.ToJsonString());
        }
        Execute(db, "INSERT INTO metadata VALUES('legacy_import',$p0)", DateTime.UtcNow.ToString("O"));
        Execute(db, "INSERT INTO metadata VALUES('legacy_skipped',$p0)", skipped.Count.ToString());
        Execute(db, "INSERT INTO metadata VALUES('legacy_skipped_files',$p0)", JsonDefaults.Encode(skipped)); tx.Commit();
        Console.WriteLine($"Importación local finalizada. Archivos omitidos: {skipped.Count}. Originales conservados.");
    }
}
