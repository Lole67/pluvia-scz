using Microsoft.AspNetCore.Mvc;

namespace Pluvia.Api.Controllers;

[ApiController]
[Route("api/territory")]
[Tags("Territorio")]
public sealed class TerritoryController(SimulationService service) : ControllerBase
{
    [HttpGet]
    [ProducesResponseType<TerritoryResponse>(200)]
    [ProducesResponseType<ErrorResponse>(401)]
    public IActionResult Get() { AccountsService.Current(HttpContext); return Ok(service.Territory()); }
}
