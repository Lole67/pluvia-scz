using Microsoft.EntityFrameworkCore;
using Pluvia.Api.Data;
using Microsoft.AspNetCore.Mvc;
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
        builder.Services.AddDbContext<PluviaDbContext>(options => options.UseSqlite(new Microsoft.Data.Sqlite.SqliteConnectionStringBuilder { DataSource = Path.Combine(data, "pluvia.sqlite3"), ForeignKeys = true, DefaultTimeout = 15 }.ToString()));
        builder.Services.AddControllers().AddApplicationPart(typeof(ApiHost).Assembly).AddJsonOptions(o => o.JsonSerializerOptions.NumberHandling = System.Text.Json.Serialization.JsonNumberHandling.Strict);
        builder.Services.Configure<ApiBehaviorOptions>(o => o.InvalidModelStateResponseFactory = _ => new BadRequestObjectResult(new ErrorResponse("Solicitud inválida. Revisa los campos obligatorios y los tipos de datos.")));
        builder.Services.AddSingleton(new PythonEngine(root));
        builder.Services.AddSingleton<AccountsService>();
        builder.Services.AddScoped(s => new SimulationService(s.GetRequiredService<PluviaDbContext>(), s.GetRequiredService<PythonEngine>(), root));
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
        if (args.Contains("--migrate-only")) return null;
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
            else if (context.Request.Path.StartsWithSegments("/static") ||
                     context.Request.Path.Value is "/" or "/login" or "/account" or "/admin/users")
                context.Response.Headers.CacheControl = "no-cache";
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
        app.MapControllers();
        foreach (var path in new[] { "/", "/login", "/account", "/admin/users" })
            app.MapGet(path, () => Results.File(Path.Combine(root, "web", path == "/" ? "index.html" : "account.html"), "text/html")).ExcludeFromDescription();
        return app;
    }
}
