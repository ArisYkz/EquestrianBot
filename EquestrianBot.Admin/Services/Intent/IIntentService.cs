namespace EquestrianBot.Api.Services.Intent;

public interface IIntentService
{
    // Return null if no match; otherwise the baseline answer string.
    string? TryAnswer(string query);
}
