using Microsoft.AspNetCore.Mvc;

namespace Pluvia.Api.Controllers;

[ApiController]
[Route("api/scenarios")]
[Produces("application/json")]
[ProducesResponseType<ErrorResponse>(401)]
[ProducesResponseType<ErrorResponse>(400)]
public sealed class ScenariosController(SimulationService service) : ControllerBase
{
    private Account UserAccount => AccountsService.Current(HttpContext);

    [HttpGet]
    [ProducesResponseType<List<ScenarioResponse>>(200)]
    public async Task<IActionResult> List(CancellationToken cancellation) => Ok(await service.Scenarios(UserAccount, cancellation));

    [HttpGet("{id}")]
    [ProducesResponseType<ScenarioResponse>(200)]
    [ProducesResponseType<ErrorResponse>(404)]
    public async Task<IActionResult> Get(string id, CancellationToken cancellation) => Ok(await service.GetScenario(UserAccount, id, cancellation));

    [HttpPost]
    [ProducesResponseType<IdResponse>(201)]
    public async Task<IActionResult> Create(ScenarioRequest input, CancellationToken cancellation)
    {
        var id = await service.SaveScenario(UserAccount, input, cancellation: cancellation);
        return CreatedAtAction(nameof(Get), new { id }, new IdResponse(id));
    }

    [HttpPut("{id}")]
    [ProducesResponseType<IdResponse>(200)]
    [ProducesResponseType<ErrorResponse>(404)]
    public async Task<IActionResult> Update(string id, ScenarioRequest input, CancellationToken cancellation) =>
        Ok(new IdResponse(await service.SaveScenario(UserAccount, input, id, cancellation)));

    [HttpDelete("{id}")]
    [ProducesResponseType(204)]
    [ProducesResponseType<ErrorResponse>(404)]
    [ProducesResponseType<ErrorResponse>(409)]
    public async Task<IActionResult> Delete(string id, CancellationToken cancellation)
    {
        await service.DeleteScenario(UserAccount, id, cancellation);
        return NoContent();
    }

    [HttpGet("{id}/simulations")]
    [ProducesResponseType<List<SimulationResponse>>(200)]
    [ProducesResponseType<ErrorResponse>(404)]
    public async Task<IActionResult> Simulations(string id, CancellationToken cancellation) =>
        Ok(await service.Related(UserAccount, id, cancellation));
}
