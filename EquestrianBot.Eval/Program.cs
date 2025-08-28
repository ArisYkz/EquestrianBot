using System.Net.Http.Json;
using CsvHelper;
using System.Globalization;

// Define test queries
var testQueries = new List<(string TenantId, string Query)>
{
    ("tenantA", "How do I reset my password?"),
    ("tenantA", "How do I refund?"),
    ("tenantB", "Tell me about riding helmets"),
    ("tenantB", "How to reset password?"), // should fail in tenantB
};

// HttpClient
using var http = new HttpClient { BaseAddress = new Uri("http://localhost:5140") };

// Results container
var results = new List<ResultRow>();

foreach (var (tenantId, query) in testQueries)
{
    var payload = new { tenantId, query };

    try
    {
        var resp = await http.PostAsJsonAsync("/api/bot", payload);
        resp.EnsureSuccessStatusCode();

        var dto = await resp.Content.ReadFromJsonAsync<BotResponse>();

        results.Add(new ResultRow
        {
            TenantId = tenantId,
            Query = query,
            Answer = dto?.Answer ?? "N/A",
            Strategy = dto?.StrategyUsed ?? "unknown",
            LatencyMs = dto?.LatencyMs ?? -1,
            Sources = dto?.Sources != null
                ? string.Join(";", dto.Sources.Select(s => $"{s.Id}:{s.Url}({s.Score:F2})"))
                : ""
        });
    }
    catch (Exception ex)
    {
        results.Add(new ResultRow
        {
            TenantId = tenantId,
            Query = query,
            Answer = $"ERROR: {ex.Message}",
            Strategy = "error",
            LatencyMs = -1,
            Sources = ""
        });
    }
}

// Write CSV
using (var writer = new StreamWriter("results.csv"))
using (var csv = new CsvWriter(writer, CultureInfo.InvariantCulture))
{
    csv.WriteRecords(results);
}

Console.WriteLine("✅ Evaluation finished. Results saved to results.csv");

// ---------------- Models ----------------
public class BotResponse
{
    public string Answer { get; set; } = "";
    public string StrategyUsed { get; set; } = "";
    public long LatencyMs { get; set; }
    public List<SourceCitation>? Sources { get; set; }
}

public class SourceCitation
{
    public string Id { get; set; } = "";
    public string? Title { get; set; }
    public string? Url { get; set; }
    public double Score { get; set; }
    public object? Attributes { get; set; }
}

public class ResultRow
{
    public string TenantId { get; set; } = "";
    public string Query { get; set; } = "";
    public string Answer { get; set; } = "";
    public string Strategy { get; set; } = "";
    public long LatencyMs { get; set; }
    public string Sources { get; set; } = "";
}
