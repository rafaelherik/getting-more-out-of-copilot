try:
    from agent_framework.foundry import FoundryChatClient
except Exception:  # pragma: no cover
    FoundryChatClient = None

from azure.identity import AzureCliCredential


class MicrosoftAgentRuntime:
    def __init__(self, project_endpoint: str, model: str) -> None:
        if FoundryChatClient is None:
            raise RuntimeError("agent-framework FoundryChatClient is unavailable")
        credential = AzureCliCredential()
        self.client = FoundryChatClient(
            project_endpoint=project_endpoint,
            model=model,
            credential=credential,
        )

    async def complete_async(self, prompt: str) -> str:
        agent = self.client.as_agent(
            name="RuntimeDiagnosticsAgent",
            instructions="Return strict format: hypothesis=<text>;confidence=<0-1>",
        )
        result = await agent.run(prompt)
        return str(result)

    async def aclose(self) -> None:
        close = getattr(self.client, "close", None)
        if callable(close):
            maybe = close()
            if hasattr(maybe, "__await__"):
                await maybe
