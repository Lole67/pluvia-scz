using Pluvia.Api;
using Microsoft.Extensions.FileProviders;
using Microsoft.OpenApi;

namespace Pluvia.Api;

public static class ApiHost
{
    public static WebApplication? Build(string[] args, Action<WebApplicationBuilder>? configure = null)
    {
        var builder = WebApplication.CreateBuilder(args);
        var root = Path.GetFullPath(Environment.GetEnvironmentVariable("PLUVIA_ROOT") ?? Path.Combine(builder.Environment.ContentRootPath, "../.."));
        var data = Path.GetFullPath(Environment.GetEnvironmentVariable("PLUVIA_DATA") ?? Path.Combine(root, "data/private"));
        builder.WebHost.UseUrls(Environment.GetEnvironmentVariable("PLUVIA_URL") ?? "http://127.0.0.1:5050");
        builder.WebHost.ConfigureKestrel(o => o.Limits.MaxRequestBodySize = 16384);
        builder.Services.ConfigureHttpJsonOptions(o => o.SerializerOptions.NumberHandling = System.Text.Json.Serialization.JsonNumberHandling.Strict);
        builder.Services.Configure<RouteHandlerOptions>(o => o.ThrowOnBadRequest = true);
        builder.Services.AddSingleton(new Database(Path.Combine(data, "pluvia.sqlite3")));
        builder.Services.AddSingleton(new PythonEngine(root));
        builder.Services.AddSingleton<AccountsService>();
        builder.Services.AddSingleton(s => new SimulationService(s.GetRequiredService<Database>(), s.GetRequiredService<PythonEngine>(), root));
        builder.Services.AddEndpointsApiExplorer();
        builder.Services.AddSwaggerGen(o =>
        {
            o.SwaggerDoc("v1", new OpenApiInfo { Title = "Pluvia SCZ API", Version = "v1", Description = "Inicia sesión en POST /api/auth/login. Copia token y úsalo en Authorize. Los resultados se guardan en SQLite." });
            o.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme { Type = SecuritySchemeType.Http, Scheme = "bearer", Description = "Token de sesión devuelto por /api/auth/login" });
            o.AddSecurityRequirement(document => new OpenApiSecurityRequirement { [new OpenApiSecuritySchemeReference("Bearer", document)] = [] });
        });
        configure?.Invoke(builder);
        var app = builder.Build();
        var database = app.Services.GetRequiredService<Database>();
        if (Environment.GetEnvironmentVariable("PLUVIA_SKIP_IMPORT") != "1") database.ImportLegacy(root);
        if (args.Contains("--import-only")) return null;
        var accounts = app.Services.GetRequiredService<AccountsService>();
        if (args.Contains("--reset-password"))
        {
            Console.Write("Usuario: "); var username = Console.ReadLine();
            using var db = database.Open(); var user = Database.Query(db, "SELECT id,role FROM users WHERE username=$p0", username?.Trim().ToLowerInvariant()).FirstOrDefault() ?? throw new Exception("Cuenta no encontrada.");
            Console.Write("Nueva contraseña: "); var password = AccountsService.ReadPassword(); Console.Write("Confirmación: "); if (password != AccountsService.ReadPassword()) throw new Exception("No coinciden."); AccountsService.ValidatePassword(password); accounts.Update(Convert.ToInt64(user["id"]), new((string)user["role"]!, true, password)); Console.WriteLine("Contraseña actualizada."); return null;
        }
        accounts.Bootstrap();
        using (var db = database.Open()) Database.Execute(db, "UPDATE simulations SET status='failed',error='El servidor se detuvo antes de completar el cálculo.' WHERE status='running'");
        app.Use(async (context, next) =>
        {
            context.Response.Headers["Referrer-Policy"] = "strict-origin-when-cross-origin";
            context.Response.Headers["X-Content-Type-Options"] = "nosniff";
            context.Response.Headers["X-Frame-Options"] = "DENY";
            if (context.Request.Path.StartsWithSegments("/api")) context.Response.Headers.CacheControl = "no-store";
            try
            {
                var authorization = context.Request.Headers.Authorization.ToString();
                if (authorization.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase)) context.Items["account"] = accounts.FindSession(authorization[7..]);
                await next();
            }
            catch (ApiError e) { context.Response.StatusCode = e.Status; await context.Response.WriteAsJsonAsync(new { error = e.Message }); }
            catch (BadHttpRequestException) { context.Response.StatusCode = 400; await context.Response.WriteAsJsonAsync(new { error = "Solicitud inválida. Revisa los campos y tipos de datos." }); }
            catch (Exception e) { app.Logger.LogError(e, "Error procesando la solicitud"); context.Response.StatusCode = 500; await context.Response.WriteAsJsonAsync(new { error = "No se pudo completar la operación." }); }
        });
        app.UseSwagger(); app.UseSwaggerUI(o => o.SwaggerEndpoint("/swagger/v1/swagger.json", "Pluvia SCZ v1"));
        app.UseStaticFiles(new StaticFileOptions { FileProvider = new PhysicalFileProvider(Path.Combine(root, "flood/static")), RequestPath = "/static" });
        app.MapPost("/api/auth/login", async (LoginRequest input, HttpContext c) => await accounts.Login(input, c.Connection.RemoteIpAddress?.ToString() ?? "local")).WithTags("Acceso");
        app.MapGet("/api/auth/me", (HttpContext c) => AccountsService.Current(c)).WithTags("Acceso");
        app.MapPost("/api/auth/logout", (HttpContext c) => { AccountsService.Current(c); accounts.Logout(c.Request.Headers.Authorization.ToString()[7..]); return Results.NoContent(); }).WithTags("Acceso");
        app.MapPost("/api/auth/password", async (PasswordRequest input, HttpContext c) => { await accounts.ChangePassword(AccountsService.Current(c), input); return Results.NoContent(); }).WithTags("Acceso");
        app.MapGet("/api/users", (HttpContext c) => { AccountsService.Current(c, true); return accounts.List(); }).WithTags("Usuarios");
        app.MapPost("/api/users", (UserRequest input, HttpContext c) => { AccountsService.Current(c, true); return Results.Created("/api/users", new { id = accounts.Create(input) }); }).WithTags("Usuarios");
        app.MapPut("/api/users/{id:long}", (long id, UserUpdate input, HttpContext c) => { AccountsService.Current(c, true); accounts.Update(id, input); return Results.NoContent(); }).WithTags("Usuarios");
        app.MapGet("/api/territory", (SimulationService s, HttpContext c) => { AccountsService.Current(c); return s.Territory(); }).WithTags("Territorio");
        app.MapGet("/api/scenarios", (SimulationService s, HttpContext c) => s.Scenarios(AccountsService.Current(c))).WithTags("Escenarios");
        app.MapPost("/api/scenarios", (ScenarioRequest input, SimulationService s, HttpContext c) => Results.Created("/api/scenarios", new { id = s.SaveScenario(AccountsService.Current(c), input) })).WithTags("Escenarios");
        app.MapPut("/api/scenarios/{id}", (string id, ScenarioRequest input, SimulationService s, HttpContext c) => new { id = s.SaveScenario(AccountsService.Current(c), input, id) }).WithTags("Escenarios");
        app.MapPost("/api/scenarios/{id}/simulate", async (string id, SimulationService s, HttpContext c) => Results.Json(await s.Run(AccountsService.Current(c), null, id, c.RequestAborted), statusCode: 201)).WithTags("Simulaciones");
        app.MapPost("/api/simulate", async (ScenarioInput input, SimulationService s, HttpContext c) => Results.Json(await s.Run(AccountsService.Current(c), input, null, c.RequestAborted), statusCode: 201)).WithTags("Simulaciones");
        app.MapGet("/api/runs", (string? include_warnings, string? status, SimulationService s, HttpContext c) => s.History(AccountsService.Current(c), include_warnings == "1", status)).WithTags("Historial");
        app.MapGet("/api/runs/{id}", (string id, SimulationService s, HttpContext c) => s.Get(AccountsService.Current(c), id)).WithTags("Historial");
        foreach (var path in new[] { "/", "/login", "/account", "/admin/users" })
            app.MapGet(path, () => Results.File(Path.Combine(root, "web", path == "/" ? "index.html" : "account.html"), "text/html")).ExcludeFromDescription();
        return app;
    }
}
