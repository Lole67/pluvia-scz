using Pluvia.Api;
Console.OutputEncoding = System.Text.Encoding.UTF8;
Console.InputEncoding = System.Text.Encoding.UTF8;
using var app = ApiHost.Build(args);
if (app is not null) await app.RunAsync();
