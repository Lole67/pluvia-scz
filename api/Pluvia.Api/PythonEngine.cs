using System.Diagnostics;
using System.Text.Json.Nodes;

namespace Pluvia.Api;

public sealed class PythonEngine(string root)
{
    private readonly SemaphoreSlim slots = new(2);
    public async Task<JsonObject> Call(object payload, CancellationToken cancellation = default)
    {
        await slots.WaitAsync(cancellation);
        try
        {
            var configured = Environment.GetEnvironmentVariable("PLUVIA_PYTHON");
            var relative = OperatingSystem.IsWindows() ? "Scripts/python.exe" : "bin/python";
            var python = configured ?? new[] { Path.Combine(root, ".venv", relative), Path.Combine(root, "..", ".venv", relative) }.FirstOrDefault(File.Exists);
            if (python is null) throw new ApiError(503, "No se encontró Python. Instala las dependencias o configura PLUVIA_PYTHON.");
            var info = new ProcessStartInfo(python)
            {
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
                WorkingDirectory = root
            };
            info.ArgumentList.Add(Path.Combine(root, "scripts/engine_bridge.py"));
            info.Environment["PYTHONIOENCODING"] = "utf-8";
            using var process = Process.Start(info) ?? throw new ApiError(503, "No se pudo iniciar el motor.");
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellation);
            timeout.CancelAfter(TimeSpan.FromMinutes(3));
            try
            {
                var output = process.StandardOutput.ReadToEndAsync(timeout.Token);
                var error = process.StandardError.ReadToEndAsync(timeout.Token);
                await process.StandardInput.WriteAsync(JsonDefaults.Encode(payload));
                process.StandardInput.Close();
                await process.WaitForExitAsync(timeout.Token);
                var text = await output; await error;
                if (process.ExitCode != 0) throw new ApiError(503, "El motor no pudo completar la operación. Comprueba Python y los datos del terreno.");
                return JsonNode.Parse(text)?.AsObject() ?? throw new ApiError(503, "Respuesta inválida del motor.");
            }
            catch (OperationCanceledException)
            {
                if (!process.HasExited) process.Kill(entireProcessTree: true);
                throw new ApiError(503, "El cálculo fue cancelado o superó el tiempo máximo.");
            }
        }
        finally { slots.Release(); }
    }
}
