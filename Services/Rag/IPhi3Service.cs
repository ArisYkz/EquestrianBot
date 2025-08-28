using EquestrianBot.Api.Models;

namespace EquestrianBot.Api.Services.Rag;

public interface IPhi3Service
{
    Task<BotResponse> AskAsync(string tenantId, string query, CancellationToken ct = default);
    Task<IngestResponse> IngestAsync(IngestRequest request, CancellationToken ct = default);
    Task<List<Dictionary<string, object>>> ListDocsAsync(string tenantId, CancellationToken ct = default);

    // delete methods
    Task DeleteTenantAsync(string tenantId, CancellationToken ct = default);
    Task DeleteDocAsync(string tenantId, string docId, CancellationToken ct = default);
}
