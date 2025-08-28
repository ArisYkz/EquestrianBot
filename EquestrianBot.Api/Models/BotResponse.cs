namespace EquestrianBot.Api.Models;

/// <summary>
/// Response returned to the frontend chatbot.
/// Wraps both baseline and RAG answers.
/// </summary>
public sealed class BotResponse
{
    public string Answer { get; set; } = string.Empty;
    public string StrategyUsed { get; set; } = "rag";
    public long LatencyMs { get; set; }

    public List<SourceCitation> Sources { get; set; } = new();

    public sealed class SourceCitation
    {
        public string? Id { get; set; }
        public string? Title { get; set; }
        public string? Url { get; set; }
        public double? Score { get; set; }
        public Dictionary<string, object>? Attributes { get; set; }
    }
}
