using System.Text.RegularExpressions;

namespace EquestrianBot.Api.Services.Intent;

public sealed class RegexIntentService : IIntentService
{
    private readonly List<(Regex Pattern, string Answer)> _rules = new()
    {
        (new Regex(@"\b(reset|forgot)\s+(my\s+)?password\b", RegexOptions.IgnoreCase), 
         "To reset your password, go to Settings → Security → Reset Password."),
        // Add more rules mapped to official FAQ snippets
    };

    public string? TryAnswer(string query)
    {
        foreach (var (pattern, answer) in _rules)
        {
            if (pattern.IsMatch(query)) return answer;
        }
        return null;
    }
}
