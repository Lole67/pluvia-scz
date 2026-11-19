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
}
