// In-memory transport for the real ASP.NET pipeline in restricted test environments.
// This executable is never used by run.py or the deployed application.
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.Http.Features;
using System.Text;
using System.Text.Json;
using Pluvia.Api;

Console.InputEncoding = Encoding.UTF8;
Console.OutputEncoding = Encoding.UTF8;
var output = Console.Out;
Console.SetOut(Console.Error);
var server = new MemoryServer();
await using var app = ApiHost.Build([], builder =>
{
    builder.Services.AddSingleton<IServer>(server);
    builder.Logging.ClearProviders();
    builder.Logging.AddConsole(options => options.LogToStandardErrorThreshold = LogLevel.Trace);
})!;
await app.StartAsync();
Console.SetOut(output);
Console.WriteLine("READY");
string? line;
while ((line = Console.ReadLine()) is not null)
{
    var input = JsonSerializer.Deserialize<Exchange>(line, JsonDefaults.Options)!;
    var response = await server.Send(input);
    Console.WriteLine(JsonDefaults.Encode(response));
}
await app.StopAsync();

record Exchange(string Method, string Path, string? Body, Dictionary<string, string> Headers);
record Reply(int Status, string Body, Dictionary<string, string> Headers);
sealed class BodyDetection(bool hasBody) : IHttpRequestBodyDetectionFeature { public bool CanHaveBody => hasBody; }
sealed class MemoryServer : IServer
{
    public IFeatureCollection Features { get; } = new FeatureCollection();
    private Func<IFeatureCollection, Task> dispatch = null!;
    public Task StartAsync<TContext>(IHttpApplication<TContext> application, CancellationToken cancellationToken) where TContext : notnull
    {
        dispatch = async features =>
        {
            var context = application.CreateContext(features);
            try { await application.ProcessRequestAsync(context); }
            finally { application.DisposeContext(context, null); }
        };
        return Task.CompletedTask;
    }
    public async Task<Reply> Send(Exchange exchange)
    {
        var uri = new Uri("http://localhost" + exchange.Path);
        var bytes = Encoding.UTF8.GetBytes(exchange.Body ?? "");
        var headers = new HeaderDictionary();
        foreach (var pair in exchange.Headers) headers[pair.Key] = pair.Value;
        if (exchange.Body is not null) headers.ContentLength = bytes.Length;
        var features = new FeatureCollection();
        features.Set<IHttpRequestFeature>(new HttpRequestFeature { Method = exchange.Method, Path = uri.AbsolutePath, QueryString = uri.Query, Scheme = "http", Protocol = "HTTP/1.1", Headers = headers, Body = new MemoryStream(bytes) });
        features.Set<IHttpRequestBodyDetectionFeature>(new BodyDetection(exchange.Body is not null));
        var response = new HttpResponseFeature { Body = new MemoryStream() };
        features.Set<IHttpResponseFeature>(response);
        var bodyFeature = new StreamResponseBodyFeature(response.Body);
        features.Set<IHttpResponseBodyFeature>(bodyFeature);
        await dispatch(features);
        await bodyFeature.CompleteAsync();
        response.Body.Position = 0;
        var body = await new StreamReader(response.Body).ReadToEndAsync();
        return new(response.StatusCode, body, response.Headers.ToDictionary(p => p.Key, p => p.Value.ToString()));
    }
    public Task StopAsync(CancellationToken cancellationToken) => Task.CompletedTask;
    public void Dispose() { }
}
