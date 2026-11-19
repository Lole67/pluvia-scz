using Microsoft.AspNetCore.Identity;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using static Pluvia.Api.Database;

namespace Pluvia.Api;

public sealed class AccountsService(Database database, PythonEngine engine)
{
    private readonly PasswordHasher<string> hasher = new();
    public static string Hash(string value) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
    private static long Now => DateTimeOffset.UtcNow.ToUnixTimeSeconds();
    public static Account Current(HttpContext context, bool admin = false)
    {
        if (context.Items["account"] is not Account account) throw new ApiError(401, "Inicia sesión para continuar.");
        if (admin && account.Role != "admin") throw new ApiError(403, "Se requiere una cuenta administradora.");
        return account;
    }
    public Account? FindSession(string token)
    {
        using var db = database.Open();
        var row = Query(db, "SELECT u.id,u.username,u.name,u.role FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token_hash=$p0 AND s.expires>$p1 AND u.active=1", Hash(token), Now).FirstOrDefault();
        return row is null ? null : new(Convert.ToInt64(row["id"]), (string)row["username"]!, (string)row["name"]!, (string)row["role"]!);
    }
    public static void ValidatePassword(string password)
    { if (password is null || password.Length is < 12 or > 128) throw new ApiError(400, "La contraseña debe tener de 12 a 128 caracteres."); }
    public static void ValidateRole(string role)
    { if (role is not ("admin" or "client")) throw new ApiError(400, "Rol inválido."); }
    public long Create(UserRequest request)
    {
        ValidatePassword(request.Password); ValidateRole(request.Role);
        var username = request.Username?.Trim().ToLowerInvariant() ?? ""; var name = request.Name?.Trim() ?? "";
        if (!Regex.IsMatch(username, @"^[a-z0-9_.-]{3,40}$") || name.Length is < 1 or > 80) throw new ApiError(400, "Revisa el usuario (3–40 caracteres) y el nombre (1–80).");
        using var db = database.Open();
        try { Execute(db, "INSERT INTO users(username,name,password_hash,role) VALUES($p0,$p1,$p2,$p3)", username, name, hasher.HashPassword(username, request.Password), request.Role); }
        catch (Microsoft.Data.Sqlite.SqliteException e) when (e.SqliteErrorCode == 19) { throw new ApiError(409, "El usuario ya existe."); }
        return Convert.ToInt64(Query(db, "SELECT id FROM users WHERE username=$p0", username)[0]["id"]);
    }
    public async Task<bool> Verify(string hash, string username, string password)
    {
        if (password is null || password.Length > 128) return false;
        if (hash.StartsWith("scrypt:") || hash.StartsWith("pbkdf2:"))
            return (await engine.Call(new { operation = "verify_legacy_password", hash, password }))["valid"]!.GetValue<bool>();
        return hasher.VerifyHashedPassword(username, hash, password) != PasswordVerificationResult.Failed;
    }
    public async Task<object> Login(LoginRequest request, string ip)
    {
        if (request.Username is null || request.Password is null || request.Username.Length > 40 || request.Password.Length > 128) throw new ApiError(401, "Credenciales inválidas.");
        using var db = database.Open();
        using (var tx = db.BeginTransaction())
        {
            Execute(db, "DELETE FROM attempts WHERE at<$p0", Now - 900);
            if (Convert.ToInt64(Query(db, "SELECT COUNT(*) AS n FROM attempts WHERE ip=$p0", ip)[0]["n"]) >= 10) throw new ApiError(429, "Demasiados intentos. Espera 15 minutos.");
            Execute(db, "INSERT INTO attempts VALUES($p0,$p1)", ip, Now); tx.Commit();
        }
        var username = request.Username.Trim().ToLowerInvariant();
        var user = Query(db, "SELECT * FROM users WHERE username=$p0", username).FirstOrDefault();
        if (user is null) { hasher.HashPassword("dummy", request.Password); throw new ApiError(401, "Usuario o contraseña incorrectos, o cuenta desactivada."); }
        if (!await Verify((string)user["password_hash"]!, username, request.Password) || Convert.ToInt64(user["active"]) != 1) throw new ApiError(401, "Usuario o contraseña incorrectos, o cuenta desactivada.");
        var token = Convert.ToHexString(RandomNumberGenerator.GetBytes(32)); var expires = Now + 8 * 3600;
        using (var tx = db.BeginTransaction())
        {
            var fresh = Query(db, "SELECT * FROM users WHERE id=$p0", user["id"])[0];
            if (Convert.ToInt64(fresh["active"]) != 1 || !Equals(fresh["password_hash"], user["password_hash"]) || !Equals(fresh["role"], user["role"])) throw new ApiError(401, "La cuenta cambió. Vuelve a ingresar.");
            if (((string)user["password_hash"]!).Contains(':')) Execute(db, "UPDATE users SET password_hash=$p0 WHERE id=$p1", hasher.HashPassword(username, request.Password), user["id"]);
            Execute(db, "DELETE FROM attempts WHERE ip=$p0", ip); Execute(db, "DELETE FROM sessions WHERE expires<=$p0", Now);
            Execute(db, "INSERT INTO sessions VALUES($p0,$p1,$p2)", Hash(token), user["id"], expires); tx.Commit();
        }
        return new { token, expires_at = DateTimeOffset.FromUnixTimeSeconds(expires), user = new Account(Convert.ToInt64(user["id"]), username, (string)user["name"]!, (string)user["role"]!) };
    }
    public void Logout(string token) { using var db = database.Open(); Execute(db, "DELETE FROM sessions WHERE token_hash=$p0", Hash(token)); }
    public object List() { using var db = database.Open(); return Query(db, "SELECT id,username,name,role,active FROM users ORDER BY username"); }
    public void Update(long id, UserUpdate request)
    {
        ValidateRole(request.Role); if (!string.IsNullOrEmpty(request.Password)) ValidatePassword(request.Password);
        using var db = database.Open(); using var tx = db.BeginTransaction();
        var user = Query(db, "SELECT * FROM users WHERE id=$p0", id).FirstOrDefault() ?? throw new ApiError(404, "Cuenta no encontrada.");
        if ((string)user["role"]! == "admin" && Convert.ToInt64(user["active"]) == 1 && (!request.Active || request.Role != "admin") && Convert.ToInt64(Query(db, "SELECT COUNT(*) AS n FROM users WHERE role='admin' AND active=1")[0]["n"]) <= 1) throw new ApiError(400, "Debe quedar un administrador activo.");
        var changed = !Equals(user["role"], request.Role) || Convert.ToInt64(user["active"]) != (request.Active ? 1 : 0) || !string.IsNullOrEmpty(request.Password);
        Execute(db, "UPDATE users SET role=$p0,active=$p1 WHERE id=$p2", request.Role, request.Active, id);
        if (!string.IsNullOrEmpty(request.Password)) Execute(db, "UPDATE users SET password_hash=$p0 WHERE id=$p1", hasher.HashPassword((string)user["username"]!, request.Password), id);
        if (changed) Execute(db, "DELETE FROM sessions WHERE user_id=$p0", id); tx.Commit();
    }
    public async Task ChangePassword(Account user, PasswordRequest request)
    {
        ValidatePassword(request.Password);
        if (request.Password != request.Confirmation) throw new ApiError(400, "Las contraseñas no coinciden.");
        using var db = database.Open(); var old = (string)Query(db, "SELECT password_hash FROM users WHERE id=$p0", user.Id)[0]["password_hash"]!;
        if (!await Verify(old, user.Username, request.CurrentPassword)) throw new ApiError(400, "Contraseña actual incorrecta.");
        using var tx = db.BeginTransaction();
        if (Execute(db, "UPDATE users SET password_hash=$p0 WHERE id=$p1 AND password_hash=$p2", hasher.HashPassword(user.Username, request.Password), user.Id, old) != 1) throw new ApiError(409, "La cuenta cambió. Vuelve a ingresar.");
        Execute(db, "DELETE FROM sessions WHERE user_id=$p0", user.Id); tx.Commit();
    }
    public void Bootstrap()
    {
        using var db = database.Open(); if (Query(db, "SELECT id FROM users LIMIT 1").Count > 0) return;
        Console.WriteLine("Pluvia SCZ: crea la primera cuenta administradora.");
        while (true)
        {
            Console.Write("Usuario: "); var username = Console.ReadLine() ?? throw new InvalidOperationException("Se requiere configurar el administrador en una terminal.");
            Console.Write("Nombre: "); var name = Console.ReadLine() ?? "";
            Console.Write("Contraseña (12–128 caracteres): "); var password = ReadPassword();
            Console.Write("Repite la contraseña: "); var confirmation = ReadPassword();
            try { if (password != confirmation) throw new ApiError(400, "Las contraseñas no coinciden."); Create(new(username, name, password, "admin")); return; }
            catch (ApiError e) { Console.WriteLine(e.Message); }
        }
    }
    public static string ReadPassword()
    {
        if (Console.IsInputRedirected) return Console.ReadLine() ?? "";
        var text = new StringBuilder(); ConsoleKeyInfo key;
        while ((key = Console.ReadKey(true)).Key != ConsoleKey.Enter) { if (key.Key == ConsoleKey.Backspace && text.Length > 0) text.Length--; else if (!char.IsControl(key.KeyChar)) text.Append(key.KeyChar); }
        Console.WriteLine(); return text.ToString();
    }
}
