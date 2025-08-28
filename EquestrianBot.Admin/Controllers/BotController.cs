using Microsoft.AspNetCore.Mvc;
using System.Net.Http.Json;

namespace EquestrianBot.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class BotController : ControllerBase
{
    private readonly IHttpClientFactory _httpClientFactory;

    public BotController(IHttpClientFactory httpClientFactory)
    {
        _httpClientFactory = httpClientFactory;
    }

    [HttpPost]
    public async Task<ActionResult<BotResp>> Post([FromBody] BotReq req, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(req.tenantId) || string.IsNullOrWhiteSpace(req.query))
            return BadRequest("Missing tenantId or query.");

        var sidecar = _httpClientFactory.CreateClient("Sidecar");
        var payload = new { tenant_id = req.tenantId, query = req.query, top_k = 3 };
        var resp = await sidecar.PostAsJsonAsync("/query", payload, ct);
        if (!resp.IsSuccessStatusCode)
        {
            return StatusCode((int)resp.StatusCode, new { error = "sidecar_query_failed" });
        }

        var dto = await resp.Content.ReadFromJsonAsync<SideResp>(cancellationToken: ct) ?? new();
        return Ok(new BotResp { answer = dto.answer ?? "I don’t know." });
    }

    public class BotReq { public string tenantId { get; set; } = ""; public string query { get; set; } = ""; }
    public class BotResp { public string answer { get; set; } = ""; }
    private class SideResp { public string? answer { get; set; } }
}
