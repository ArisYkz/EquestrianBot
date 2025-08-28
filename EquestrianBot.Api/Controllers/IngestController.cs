using Microsoft.AspNetCore.Mvc;
using System.Net.Http.Json;

namespace EquestrianBot.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class IngestController : ControllerBase
{
    private readonly IHttpClientFactory _httpClientFactory;
    // store ingested docs in memory for listing
    private static readonly Dictionary<string, List<Dictionary<string, object>>> Store = new();

    public IngestController(IHttpClientFactory httpClientFactory)
    {
        _httpClientFactory = httpClientFactory;
    }

    [HttpPost]
    public async Task<ActionResult<IngestResp>> Post([FromBody] IngestReq req, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(req.tenantId) || req.documents is null || req.documents.Count == 0)
            return BadRequest("Missing tenantId or documents.");

        // local store for listing
        if (!Store.ContainsKey(req.tenantId)) Store[req.tenantId] = new();
        Store[req.tenantId].AddRange(req.documents);

        // forward to sidecar
        var sidecar = _httpClientFactory.CreateClient("Sidecar");
        var payload = new { tenant_id = req.tenantId, dataset_type = req.datasetType, documents = req.documents };
        var resp = await sidecar.PostAsJsonAsync("/ingest", payload, ct);
        if (!resp.IsSuccessStatusCode)
        {
            return StatusCode((int)resp.StatusCode, new { error = "sidecar_ingest_failed" });
        }

        return Ok(new IngestResp { status = "ingested", count = Store[req.tenantId].Count });
    }

    [HttpGet("{tenantId}")]
    public ActionResult<List<Dictionary<string, object>>> Get(string tenantId)
    {
        return Store.TryGetValue(tenantId, out var docs) ? docs : new();
    }

    [HttpDelete("{tenantId}")]
    public IActionResult Delete(string tenantId)
    {
        Store.Remove(tenantId);
        return Ok(new { status = "deleted" });
    }

    public class IngestReq { public string tenantId { get; set; } = ""; public string datasetType { get; set; } = "faq"; public List<Dictionary<string, object>> documents { get; set; } = new(); }
    public class IngestResp { public string status { get; set; } = ""; public int count { get; set; } }
}
