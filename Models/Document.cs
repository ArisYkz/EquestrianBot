namespace EquestrianBot.Api.Models;

public sealed class Document
{
    public required string Id { get; init; }
    public string? Title { get; init; }
    public string? Question { get; init; }     // for FAQs
    public string? Answer { get; init; }       // for FAQs
    public string? Url { get; init; }          // kb link / product page
    public Dictionary<string, object>? Metadata { get; init; } // arbitrary
    public List<string>? Tags { get; init; }
    public Dictionary<string, object>? Attributes { get; init; } // for products
}
