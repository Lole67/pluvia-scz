using Microsoft.AspNetCore.Mvc;

namespace Pluvia.Api.Controllers;

[ApiController]
[Produces("application/json")]
[Tags("Acceso y usuarios")]
[ProducesResponseType<ErrorResponse>(400)]
[ProducesResponseType<ErrorResponse>(401)]
public sealed class AccountsController(AccountsService accounts) : ControllerBase
{
    [HttpPost("api/auth/login")]
    [ProducesResponseType<LoginResponse>(200)]
    [ProducesResponseType<ErrorResponse>(429)]
    public async Task<IActionResult> Login(LoginRequest input) => Ok(await accounts.Login(input, HttpContext.Connection.RemoteIpAddress?.ToString() ?? "local"));

    [HttpGet("api/auth/me")]
    [ProducesResponseType<Account>(200)]
    public Account Me() => AccountsService.Current(HttpContext);

    [HttpPost("api/auth/logout")]
    [ProducesResponseType(204)]
    public IActionResult Logout()
    {
        AccountsService.Current(HttpContext);
        accounts.Logout(Request.Headers.Authorization.ToString()[7..]);
        return NoContent();
    }

    [HttpPost("api/auth/password")]
    [ProducesResponseType(204)]
    public async Task<IActionResult> Password(PasswordRequest input)
    {
        await accounts.ChangePassword(AccountsService.Current(HttpContext), input);
        return NoContent();
    }

    [HttpGet("api/users")]
    [ProducesResponseType<List<UserResponse>>(200)]
    [ProducesResponseType<ErrorResponse>(403)]
    public IActionResult Users() { AccountsService.Current(HttpContext, true); return Ok(accounts.List()); }

    [HttpPost("api/users")]
    [ProducesResponseType<UserIdResponse>(201)]
    [ProducesResponseType<ErrorResponse>(403)]
    [ProducesResponseType<ErrorResponse>(409)]
    public IActionResult CreateUser(UserRequest input)
    {
        AccountsService.Current(HttpContext, true);
        return Created("/api/users", new UserIdResponse(accounts.Create(input)));
    }

    [HttpPut("api/users/{id:long}")]
    [ProducesResponseType(204)]
    [ProducesResponseType<ErrorResponse>(403)]
    [ProducesResponseType<ErrorResponse>(404)]
    public IActionResult UpdateUser(long id, UserUpdate input)
    {
        AccountsService.Current(HttpContext, true); accounts.Update(id, input); return NoContent();
    }
}
