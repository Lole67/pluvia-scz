using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Pluvia.Api.Data.Migrations
{
    /// <inheritdoc />
    public partial class OptionalRunScenario : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AlterColumn<string>(
                name: "scenario_id",
                table: "simulations",
                type: "TEXT",
                nullable: true,
                oldClrType: typeof(string),
                oldType: "TEXT");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            // Older schemas require a parent for every execution.
            migrationBuilder.Sql("""
                CREATE TEMP TABLE rollback_scenarios AS
                    SELECT id AS run_id, lower(hex(randomblob(16))) AS scenario_id
                    FROM simulations WHERE scenario_id IS NULL;
                INSERT INTO scenarios(id, owner_id, name, parameters, created_at, updated_at)
                    SELECT r.scenario_id, s.owner_id, 'Simulación ' || s.created_at,
                           s.parameters, s.created_at, s.created_at
                    FROM simulations s JOIN rollback_scenarios r ON r.run_id = s.id;
                UPDATE simulations SET scenario_id = r.scenario_id
                    FROM rollback_scenarios r WHERE simulations.id = r.run_id;
                UPDATE results SET payload = json_set(payload, '$.scenario_id', r.scenario_id)
                    FROM rollback_scenarios r WHERE results.simulation_id = r.run_id;
                DROP TABLE rollback_scenarios;
                """);
            migrationBuilder.AlterColumn<string>(
                name: "scenario_id",
                table: "simulations",
                type: "TEXT",
                nullable: false,
                defaultValue: "",
                oldClrType: typeof(string),
                oldType: "TEXT",
                oldNullable: true);
        }
    }
}
