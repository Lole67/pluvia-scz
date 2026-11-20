using Microsoft.AspNetCore.Mvc;
using System.Text.Json.Nodes;

namespace Pluvia.Api.Controllers;

[ApiController]
[Produces("application/json")]
[Tags("Simulaciones e historial")]
[ProducesResponseType<ErrorResponse>(401)]
[ProducesResponseType<ErrorResponse>(400)]
public sealed class SimulationsController(SimulationService service) : ControllerBase
{
    private Account UserAccount => AccountsService.Current(HttpContext);

    [HttpPost("api/scenarios/{id}/simulate")]
    [ProducesResponseType<JsonObject>(201)]
    [ProducesResponseType<ErrorResponse>(404)]
    public async Task<IActionResult> SimulateSaved(string id) => CreatedResult(await service.Run(UserAccount, null, id, HttpContext.RequestAborted));

    [HttpPost("api/simulate")]
    [ProducesResponseType<JsonObject>(201)]
    public async Task<IActionResult> Simulate(ScenarioInput input) => CreatedResult(await service.Run(UserAccount, input, null, HttpContext.RequestAborted));

    [HttpPost("api/runs")]
    [ProducesResponseType<JsonObject>(201)]
    public async Task<IActionResult> Create(SimulationRequest input)
    {
        var account = UserAccount;
        try { return CreatedResult(await service.Run(account, null, input.ScenarioId, HttpContext.RequestAborted)); }
        catch (ApiError e) when (e.Status == 404) { throw new ApiError(400, "scenario_id debe referenciar un escenario accesible y existente."); }
    }

    private IActionResult CreatedResult(JsonObject result) => CreatedAtAction(nameof(Get), new { id = result["run_id"]!.GetValue<string>() }, result);

    [HttpGet("api/runs")]
    [ProducesResponseType<List<SimulationResponse>>(200)]
    public async Task<IActionResult> List([FromQuery] string? include_warnings, [FromQuery] string? status) =>
        Ok(await service.History(UserAccount, include_warnings == "1", status));

    [HttpGet("api/runs/{id}")]
    [ProducesResponseType<JsonObject>(200)]
    [ProducesResponseType<ErrorResponse>(404)]
    public async Task<IActionResult> Get(string id) => Ok(await service.Get(UserAccount, id));
}
