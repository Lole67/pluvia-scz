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
        builder.Services.AddEndpointsApiExplorer();
        builder.Services.AddSwaggerGen(o =>
        {
            o.SwaggerDoc("v1", new OpenApiInfo { Title = "Pluvia SCZ API", Version = "v1", Description = "API de Pluvia SCZ. Persistencia local SQLite y contrato OpenAPI." });
            o.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme { Type = SecuritySchemeType.Http, Scheme = "bearer", Description = "Token de sesión devuelto por /api/auth/login" });
            o.AddSecurityRequirement(document => new OpenApiSecurityRequirement { [new OpenApiSecuritySchemeReference("Bearer", document)] = [] });
        });
        configure?.Invoke(builder);
        var app = builder.Build();
        var database = app.Services.GetRequiredService<Database>();
        if (args.Contains("--import-only")) return null;
        app.Use(async (context, next) =>
        {
            context.Response.Headers["Referrer-Policy"] = "strict-origin-when-cross-origin";
            context.Response.Headers["X-Content-Type-Options"] = "nosniff";
            context.Response.Headers["X-Frame-Options"] = "DENY";
            if (context.Request.Path.StartsWithSegments("/api")) context.Response.Headers.CacheControl = "no-store";
            try
            {
                await next();
            }
            catch (ApiError e) { context.Response.StatusCode = e.Status; await context.Response.WriteAsJsonAsync(new { error = e.Message }); }
            catch (BadHttpRequestException) { context.Response.StatusCode = 400; await context.Response.WriteAsJsonAsync(new { error = "Solicitud inválida. Revisa los campos y tipos de datos." }); }
            catch (Exception e) { app.Logger.LogError(e, "Error procesando la solicitud"); context.Response.StatusCode = 500; await context.Response.WriteAsJsonAsync(new { error = "No se pudo completar la operación." }); }
        });
        app.UseSwagger(); app.UseSwaggerUI(o => o.SwaggerEndpoint("/swagger/v1/swagger.json", "Pluvia SCZ v1"));
        app.MapGet("/api/health", () => new { status = "ok" }).WithTags("Sistema");
        return app;
    }
}
