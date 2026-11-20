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
        Execute(db, """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE NOT NULL,name TEXT NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('admin','client')),active INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),expires INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS attempts(ip TEXT NOT NULL,at INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS ix_attempts ON attempts(ip,at);
            CREATE TABLE IF NOT EXISTS scenarios(id TEXT PRIMARY KEY,owner_id INTEGER REFERENCES users(id),name TEXT NOT NULL,parameters TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS simulations(id TEXT PRIMARY KEY,scenario_id TEXT NOT NULL REFERENCES scenarios(id),owner_id INTEGER REFERENCES users(id),created_at TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('running','completed','failed')),parameters TEXT NOT NULL,error TEXT);
            CREATE TABLE IF NOT EXISTS results(simulation_id TEXT PRIMARY KEY REFERENCES simulations(id),payload TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS ix_runs_owner ON simulations(owner_id,created_at);
            CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            """);
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
            Execute(db, "INSERT INTO simulations VALUES($p0,$p1,$p2,$p3,'completed',$p4,NULL)", id, scenarioId, owner, created, parameters);
            Execute(db, "INSERT INTO results VALUES($p0,$p1)", id, result.ToJsonString());
        }
        Execute(db, "INSERT INTO metadata VALUES('legacy_import',$p0)", DateTime.UtcNow.ToString("O"));
        Execute(db, "INSERT INTO metadata VALUES('legacy_skipped',$p0)", skipped.Count.ToString());
        Execute(db, "INSERT INTO metadata VALUES('legacy_skipped_files',$p0)", JsonDefaults.Encode(skipped)); tx.Commit();
        Console.WriteLine($"Importación local finalizada. Archivos omitidos: {skipped.Count}. Originales conservados.");
    }
}
