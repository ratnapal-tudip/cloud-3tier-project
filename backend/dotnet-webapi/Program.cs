using System;
using System.Data;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.IdentityModel.Tokens;
using MySqlConnector;
using BCrypt.Net;

var builder = WebApplication.CreateBuilder(args);

// Clear default claim type mapping so 'sub' doesn't get converted to 'nameidentifier'
JwtSecurityTokenHandler.DefaultInboundClaimTypeMap.Clear();

// Read environment variables
var mysqlHost = Environment.GetEnvironmentVariable("MYSQL_HOST") ?? "localhost";
var mysqlPort = Environment.GetEnvironmentVariable("MYSQL_PORT") ?? "3306";
var mysqlUser = Environment.GetEnvironmentVariable("MYSQL_USER") ?? "root";
var mysqlPassword = Environment.GetEnvironmentVariable("MYSQL_PASSWORD") ?? "root";
var mysqlDatabase = Environment.GetEnvironmentVariable("MYSQL_DATABASE") ?? "cloud3tier";
var secretKey = Environment.GetEnvironmentVariable("SECRET_KEY") ?? "super-secret-dev-key-change-in-production";

var connectionString = $"Server={mysqlHost};Port={mysqlPort};User ID={mysqlUser};Password={mysqlPassword};Database={mysqlDatabase};Pooling=true;MaximumPoolSize=5;";

// Add CORS
builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        policy.AllowAnyOrigin().AllowAnyMethod().AllowAnyHeader();
    });
});

// Configure JWT Authentication
var key = Encoding.UTF8.GetBytes(secretKey);
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuerSigningKey = true,
            IssuerSigningKey = new SymmetricSecurityKey(key),
            ValidateIssuer = false,
            ValidateAudience = false,
            ValidateLifetime = true,
            ClockSkew = TimeSpan.Zero
        };
        options.Events = new JwtBearerEvents
        {
            OnChallenge = context =>
            {
                context.HandleResponse();
                context.Response.StatusCode = 401;
                context.Response.ContentType = "application/json";
                return context.Response.WriteAsJsonAsync(new { detail = "Invalid or expired token" });
            }
        };
    });

builder.Services.AddAuthorization();
builder.Services.AddTransient<MySqlConnection>(_ => new MySqlConnection(connectionString));

var app = builder.Build();

app.UseCors();

// Exception handling middleware to match FastAPI
app.Use(async (context, next) =>
{
    try
    {
        await next(context);
    }
    catch (Exception ex)
    {
        Console.WriteLine(ex);
        context.Response.StatusCode = 500;
        await context.Response.WriteAsJsonAsync(new { detail = "Internal server error" });
    }
});

// Use authentication and authorization
app.UseAuthentication();
app.UseAuthorization();

// Request logger middleware
app.Use(async (context, next) =>
{
    var watch = System.Diagnostics.Stopwatch.StartNew();
    await next(context);
    watch.Stop();
    Console.WriteLine($"[dotnet] {context.Request.Method} {context.Request.Path} {context.Response.StatusCode} {watch.ElapsedMilliseconds} ms");
});

// Models
string FormatDate(DateTime date) => date.ToString("yyyy-MM-ddTHH:mm:ss.fffZ");

app.MapGet("/", () => new { message = "Cloud 3-Tier API is running" });

app.MapGet("/health", () => new { status = "healthy", timestamp = DateTime.UtcNow.ToString("o"), version = "1.0.0", service = "dotnet-webapi" });

app.MapGet("/health/ready", async (MySqlConnection conn) =>
{
    try
    {
        await conn.OpenAsync();
        using var cmd = new MySqlCommand("SELECT 1", conn);
        await cmd.ExecuteScalarAsync();
        return Results.Ok(new { status = "healthy", timestamp = DateTime.UtcNow.ToString("o"), version = "1.0.0", service = "dotnet-webapi" });
    }
    catch
    {
        return Results.Json(new { detail = "Database not ready" }, statusCode: 503);
    }
});

app.MapGet("/health/live", () => new { message = "alive" });

app.MapPost("/api/auth/signup", async (SignupRequest req, MySqlConnection conn) =>
{
    if (string.IsNullOrEmpty(req.username)) return Results.Json(new { detail = "username is required" }, statusCode: 422);
    if (string.IsNullOrEmpty(req.email)) return Results.Json(new { detail = "email is required" }, statusCode: 422);
    if (string.IsNullOrEmpty(req.password)) return Results.Json(new { detail = "password is required" }, statusCode: 422);

    await conn.OpenAsync();

    using var checkUserCmd = new MySqlCommand("SELECT id FROM users WHERE username = @u", conn);
    checkUserCmd.Parameters.AddWithValue("@u", req.username);
    if (await checkUserCmd.ExecuteScalarAsync() != null)
        return Results.Json(new { detail = "Username already taken" }, statusCode: 400);

    using var checkEmailCmd = new MySqlCommand("SELECT id FROM users WHERE email = @e", conn);
    checkEmailCmd.Parameters.AddWithValue("@e", req.email);
    if (await checkEmailCmd.ExecuteScalarAsync() != null)
        return Results.Json(new { detail = "Email already registered" }, statusCode: 400);

    string hashed = BCrypt.Net.BCrypt.HashPassword(req.password, 12);
    
    using var insertCmd = new MySqlCommand("INSERT INTO users (username, email, hashed_password, full_name) VALUES (@u, @e, @p, @f)", conn);
    insertCmd.Parameters.AddWithValue("@u", req.username);
    insertCmd.Parameters.AddWithValue("@e", req.email);
    insertCmd.Parameters.AddWithValue("@p", hashed);
    insertCmd.Parameters.AddWithValue("@f", req.full_name ?? "");
    await insertCmd.ExecuteNonQueryAsync();

    long newId = insertCmd.LastInsertedId;

    using var getCmd = new MySqlCommand("SELECT * FROM users WHERE id = @id", conn);
    getCmd.Parameters.AddWithValue("@id", newId);
    using var reader = await getCmd.ExecuteReaderAsync();
    await reader.ReadAsync();

    var userRes = new
    {
        id = reader.GetInt32("id"),
        username = reader.GetString("username"),
        email = reader.GetString("email"),
        full_name = reader.IsDBNull(reader.GetOrdinal("full_name")) ? "" : reader.GetString("full_name"),
        created_at = FormatDate(reader.GetDateTime("created_at"))
    };

    return Results.Json(userRes, statusCode: 201);
});

// Support both form URL encoded and JSON body
app.MapPost("/api/auth/login", async (HttpContext context, MySqlConnection conn) =>
{
    string? username = null;
    string? password = null;

    if (context.Request.HasFormContentType)
    {
        var form = await context.Request.ReadFormAsync();
        username = form["username"].ToString();
        password = form["password"].ToString();
    }
    else if (context.Request.HasJsonContentType())
    {
        var json = await context.Request.ReadFromJsonAsync<LoginRequest>();
        if (json != null)
        {
            username = json.username;
            password = json.password;
        }
    }

    if (string.IsNullOrEmpty(username) || string.IsNullOrEmpty(password))
        return Results.Json(new { detail = "username and password are required" }, statusCode: 422);

    await conn.OpenAsync();
    using var cmd = new MySqlCommand("SELECT * FROM users WHERE username = @u", conn);
    cmd.Parameters.AddWithValue("@u", username);
    using var reader = await cmd.ExecuteReaderAsync();

    if (!await reader.ReadAsync() || !BCrypt.Net.BCrypt.Verify(password, reader.GetString("hashed_password")))
        return Results.Json(new { detail = "Incorrect username or password" }, statusCode: 401);

    var claims = new[] { new Claim("sub", reader.GetString("username")) };
    var tokenDescriptor = new SecurityTokenDescriptor
    {
        Subject = new ClaimsIdentity(claims),
        Expires = DateTime.UtcNow.AddMinutes(24 * 60),
        SigningCredentials = new SigningCredentials(new SymmetricSecurityKey(key), SecurityAlgorithms.HmacSha256Signature)
    };

    var tokenHandler = new JwtSecurityTokenHandler();
    var securityToken = tokenHandler.CreateToken(tokenDescriptor);
    var tokenString = tokenHandler.WriteToken(securityToken);

    return Results.Ok(new { access_token = tokenString, token_type = "bearer", username = reader.GetString("username"), message = "Login successful" });
});

app.MapGet("/api/me", async (HttpContext context, MySqlConnection conn) =>
{
    var username = context.User.FindFirst("sub")?.Value ?? context.User.FindFirst(ClaimTypes.NameIdentifier)?.Value;
    if (username == null) return Results.Json(new { detail = "Invalid or expired token" }, statusCode: 401);

    await conn.OpenAsync();
    using var cmd = new MySqlCommand("SELECT * FROM users WHERE username = @u", conn);
    cmd.Parameters.AddWithValue("@u", username);
    using var reader = await cmd.ExecuteReaderAsync();

    if (!await reader.ReadAsync()) return Results.Json(new { detail = "Invalid or expired token" }, statusCode: 401);

    var userRes = new
    {
        id = reader.GetInt32("id"),
        username = reader.GetString("username"),
        email = reader.GetString("email"),
        full_name = reader.IsDBNull(reader.GetOrdinal("full_name")) ? "" : reader.GetString("full_name"),
        created_at = FormatDate(reader.GetDateTime("created_at"))
    };

    return Results.Ok(userRes);
}).RequireAuthorization();

app.MapGet("/api/dashboard", async (HttpContext context, MySqlConnection conn) =>
{
    var username = context.User.FindFirst("sub")?.Value ?? context.User.FindFirst(ClaimTypes.NameIdentifier)?.Value;
    if (username == null) return Results.Json(new { detail = "Invalid or expired token" }, statusCode: 401);

    await conn.OpenAsync();
    using var cmd = new MySqlCommand("SELECT * FROM users WHERE username = @u", conn);
    cmd.Parameters.AddWithValue("@u", username);
    using var reader = await cmd.ExecuteReaderAsync();

    if (!await reader.ReadAsync()) return Results.Json(new { detail = "Invalid or expired token" }, statusCode: 401);

    var fn = reader.IsDBNull(reader.GetOrdinal("full_name")) ? "" : reader.GetString("full_name");
    var un = reader.GetString("username");
    var email = reader.GetString("email");
    var id = reader.GetInt32("id");

    return Results.Ok(new
    {
        message = $"Welcome back, {(string.IsNullOrEmpty(fn) ? un : fn)}!",
        user = new { id, username = un, email, full_name = fn },
        dashboard_data = new
        {
            total_projects = 3,
            recent_activity = "Deployed v1.0.0 to production",
            server_status = "All systems operational"
        }
    });
}).RequireAuthorization();

app.Run();

record SignupRequest(string username, string email, string password, string? full_name = "");
record LoginRequest(string username, string password);
