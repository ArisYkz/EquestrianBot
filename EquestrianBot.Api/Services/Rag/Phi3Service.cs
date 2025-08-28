using EquestrianBot.Api.Clients;
using EquestrianBot.Api.Models;

namespace EquestrianBot.Api.Services.Rag;

public sealed class Phi3Service : IPhi3Service
{
    private readonly SidecarClient _sidecar;

    public Phi3Service(SidecarClient sidecar) => _sidecar = sidecar;

    public Task<BotResponse> AskAsync(string tenantId, string query, CancellationToken ct = default)
        => _sidecar.QueryRagAsync(tenantId, query, 4, ct);

    public Task<IngestResponse> IngestAsync(IngestRequest request, CancellationToken ct = default)
        => _sidecar.IngestAsync(request, ct);

    public Task<List<Dictionary<string, object>>> ListDocsAsync(string tenantId, CancellationToken ct = default)
        => _sidecar.ListDocsAsync(tenantId, ct);

    public Task DeleteTenantAsync(string tenantId, CancellationToken ct = default)
        => _sidecar.DeleteTenantAsync(tenantId, ct);

    public Task DeleteDocAsync(string tenantId, string docId, CancellationToken ct = default)
        => _sidecar.DeleteDocAsync(tenantId, docId, ct);
}
