using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Pluvia.Api.Data.Migrations
{
    /// <inheritdoc />
    public partial class InitialSqlite : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // Establishes the schema for fresh installations and adopts the existing
            // SQLite schema without rebuilding tables or replacing rows.
            migrationBuilder.Sql("""
            CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE NOT NULL,name TEXT NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('admin','client')),active INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),expires INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS attempts(ip TEXT NOT NULL,at INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS ix_attempts ON attempts(ip,at);
            CREATE TABLE IF NOT EXISTS scenarios(id TEXT PRIMARY KEY,owner_id INTEGER REFERENCES users(id),name TEXT NOT NULL,parameters TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS simulations(id TEXT PRIMARY KEY,scenario_id TEXT NOT NULL REFERENCES scenarios(id),owner_id INTEGER REFERENCES users(id),created_at TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('running','completed','failed')),parameters TEXT NOT NULL,error TEXT);
            CREATE TABLE IF NOT EXISTS results(simulation_id TEXT PRIMARY KEY REFERENCES simulations(id),payload TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS ix_runs_owner ON simulations(owner_id,created_at);
            CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE UNIQUE INDEX IF NOT EXISTS IX_users_username ON users(username);
            CREATE INDEX IF NOT EXISTS IX_scenarios_owner_id ON scenarios(owner_id);
            CREATE INDEX IF NOT EXISTS IX_sessions_user_id ON sessions(user_id);
            CREATE INDEX IF NOT EXISTS IX_simulations_scenario_id ON simulations(scenario_id);
            """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("DROP TABLE IF EXISTS attempts;");
            migrationBuilder.DropTable(
                name: "metadata");

            migrationBuilder.DropTable(
                name: "results");

            migrationBuilder.DropTable(
                name: "sessions");

            migrationBuilder.DropTable(
                name: "simulations");

            migrationBuilder.DropTable(
                name: "scenarios");

            migrationBuilder.DropTable(
                name: "users");
        }
    }
}
