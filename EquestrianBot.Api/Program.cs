using Microsoft.OpenApi.Models;

var builder = WebApplication.CreateBuilder(args);

// Controllers + Swagger
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo { Title = "EquestrianBot API", Version = "v1" });
});

// Allow calls from your Admin site (5096)
builder.Services.AddCors(o => o.AddPolicy("LocalDev", p =>
    p.WithOrigins("http://localhost:5096")
     .AllowAnyHeader()
     .AllowAnyMethod()));

// HttpClient to talk to the Python sidecar (8000)
builder.Services.AddHttpClient("Sidecar", client =>
{
    client.BaseAddress = new Uri("http://localhost:8000");
    client.Timeout = TimeSpan.FromSeconds(60);
});

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseCors("LocalDev");
app.UseRouting();
app.UseAuthorization();

app.MapControllers();
app.Run();
