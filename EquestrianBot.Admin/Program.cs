using EquestrianBot.Admin;

var builder = WebApplication.CreateBuilder(args);

// Configure Razor components with interactive server mode.
builder.Services.AddRazorComponents().AddInteractiveServerComponents();

// Register HttpClient so you can call your API from Blazor components.
builder.Services.AddHttpClient();

var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseStaticFiles();
app.UseAntiforgery();

// Map the root component and enable server interactivity
app.MapRazorComponents<App>().AddInteractiveServerRenderMode();

app.Run();
