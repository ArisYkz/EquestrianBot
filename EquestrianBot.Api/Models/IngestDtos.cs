namespace EquestrianBot.Api.Models;

public sealed class IngestRequest
{
    public required string TenantId { get; init; }
    public required string DatasetType { get; init; } // "faq" | "products"
    public required List<Document> Documents { get; init; }
}

public sealed class IngestResponse
{
    public required string Status { get; init; }
    public int Count { get; init; }
}
