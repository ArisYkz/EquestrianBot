using System.Net.Http.Json;
using EquestrianBot.Api.Models;

namespace EquestrianBot.Api.Clients;

public sealed class SidecarClient
{
    private readonly HttpClient _http;

    public SidecarClient(HttpClient http) => _http = http;

    public async Task<BotResponse> QueryRagAsync(string tenantId, string query, int topK = 4, CancellationToken ct = default)
    {
        var payload = new { tenant_id = tenantId, query = query, top_k = topK };

        using var resp = await _http.PostAsJsonAsync("/query", payload, ct);
        resp.EnsureSuccessStatusCode();

        var dto = await resp.Content.ReadFromJsonAsync<SidecarQueryResponse>(cancellationToken: ct)
                  ?? throw new InvalidOperationException("Sidecar returned empty body");

        return new BotResponse
        {
            Answer = dto.answer ?? "I don’t know.",
            StrategyUsed = dto.strategy ?? "rag",
            LatencyMs = dto.latency_ms,
            Sources = dto.context?.Select(c => new BotResponse.SourceCitation
            {
                Id = c.id,
                Title = c.title,
                Url = c.url,
                Score = c.score,
                Attributes = c.attributes
            }).ToList() ?? new()
        };
    }

    public async Task<IngestResponse> IngestAsync(IngestRequest req, CancellationToken ct = default)
    {
        var payload = new
        {
            tenant_id = req.TenantId,
            dataset_type = req.DatasetType,
            documents = req.Documents
        };

        using var resp = await _http.PostAsJsonAsync("/ingest", payload, ct);
        resp.EnsureSuccessStatusCode();

        var dto = await resp.Content.ReadFromJsonAsync<IngestResponse>(cancellationToken: ct)
                  ?? throw new InvalidOperationException("Sidecar returned empty body");

        return dto;
    }

    public async Task<List<Dictionary<string, object>>> ListDocsAsync(string tenantId, CancellationToken ct = default)
{
    using var resp = await _http.GetAsync($"/list/{tenantId}", ct);
    resp.EnsureSuccessStatusCode();

    var docs = await resp.Content.ReadFromJsonAsync<List<Dictionary<string, object>>>(cancellationToken: ct);
    return docs ?? new List<Dictionary<string, object>>();
}

    private sealed class SidecarQueryResponse
    {
        public string? answer { get; init; }
        public string? strategy { get; init; }
        public long latency_ms { get; init; }
        public List<ContextDoc>? context { get; init; }

        public sealed class ContextDoc
        {
            public string? id { get; init; }
            public string? title { get; init; }
            public string? url { get; init; }
            public double? score { get; init; }
            public Dictionary<string, object>? attributes { get; init; }
        }
    }
    public async Task DeleteTenantAsync(string tenantId, CancellationToken ct = default)
    {
        using var resp = await _http.DeleteAsync($"/delete/{tenantId}", ct);
        resp.EnsureSuccessStatusCode();
    }

    public async Task DeleteDocAsync(string tenantId, string docId, CancellationToken ct = default)
    {
        using var resp = await _http.DeleteAsync($"/delete/{tenantId}/{docId}", ct);
        resp.EnsureSuccessStatusCode();
    }

}
