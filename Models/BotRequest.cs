namespace EquestrianBot.Api.Models;

/// <summary>
/// Request payload from the frontend chatbot.
/// </summary>
public sealed class BotRequest
{
    public string TenantId { get; set; } = string.Empty;
    public string Query { get; set; } = string.Empty;
}
