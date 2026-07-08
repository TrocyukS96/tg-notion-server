import httpx

NOTION_API_BASE_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
NOTION_TIMEOUT = 30.0


class NotionClient:
    def __init__(self, access_token: str) -> None:
        self._access_token = access_token
        self._client = httpx.AsyncClient(
            base_url=NOTION_API_BASE_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
            timeout=NOTION_TIMEOUT,
        )

    @property
    def http(self) -> httpx.AsyncClient:
        return self._client

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "NotionClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()


def create_notion_client(access_token: str) -> NotionClient:
    if not access_token:
        raise ValueError("Notion access token is required")
    return NotionClient(access_token)
