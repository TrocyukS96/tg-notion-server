from notion_client import AsyncClient

from app.services.notion_client import NotionClient, create_notion_client

STATUS_COLORS = (
    "default",
    "gray",
    "brown",
    "orange",
    "yellow",
    "green",
    "blue",
    "purple",
    "pink",
    "red",
)


def get_notion_client(access_token: str) -> NotionClient:
    return create_notion_client(access_token)


def _build_status_options(columns: list[str]) -> list[dict[str, str]]:
    return [
        {"name": column, "color": STATUS_COLORS[index % len(STATUS_COLORS)]}
        for index, column in enumerate(columns)
    ]


async def _get_personal_page_id(client: NotionClient) -> str | None:
    response = await client.http.get("/users/me")
    response.raise_for_status()
    data = response.json()
    return data.get("personal_page_id")


async def search_databases(query: str, access_token: str) -> list[dict]:
    """Ищет базы данных в Notion по названию"""
    client = AsyncClient(auth=access_token)
    try:
        response = await client.search(
            query=query,
            filter={"property": "object", "value": "data_source"},
        )
        results = response.get("results", [])

        formatted = []
        for db in results:
            title = db.get("title", [])
            title_text = (
                "".join(t.get("plain_text", "") for t in title)
                if title
                else "Без названия"
            )
            formatted.append(
                {
                    "id": db.get("id"),
                    "title": title_text,
                    "url": db.get("url"),
                }
            )
        return formatted
    except Exception as e:
        raise Exception(f"Notion API error: {e}") from e
    finally:
        await client.aclose()


async def create_database(title: str, columns: list[str], access_token: str) -> dict:
    async with get_notion_client(access_token) as client:
        personal_page_id = await _get_personal_page_id(client)

        if personal_page_id:
            parent = {"type": "page_id", "page_id": personal_page_id}
        else:
            parent = {"type": "workspace", "workspace": True}

        response = await client.http.post(
            "/databases",
            json={
                "parent": parent,
                "title": [{"type": "text", "text": {"content": title}}],
                "properties": {
                    "Name": {"title": {}},
                    "Status": {
                        "select": {
                            "options": _build_status_options(columns),
                        }
                    },
                },
            },
        )

    response.raise_for_status()
    return response.json()


STATUS_PROPERTY = "Status"
STATUS_PROPERTY_NAMES = ("Status", "Статус")
TITLE_PROPERTY = "Name"
DESCRIPTION_PROPERTY = "Description"
DUE_DATE_PROPERTIES = ("Due date", "Due Date")


def _find_title_property_name(properties: dict) -> str:
    title_property = properties.get(TITLE_PROPERTY)
    if title_property and title_property.get("type") == "title":
        return TITLE_PROPERTY

    for name, property_value in properties.items():
        if property_value.get("type") == "title":
            return name

    return TITLE_PROPERTY


def _find_status_property(properties: dict) -> tuple[str, dict] | None:
    for name in STATUS_PROPERTY_NAMES:
        property_value = properties.get(name)
        if property_value and property_value.get("type") in ("select", "status"):
            return name, property_value

    for name, property_value in properties.items():
        if property_value.get("type") in ("select", "status"):
            return name, property_value

    return None


def _extract_status_options(property_schema: dict) -> list[str]:
    property_type = property_schema.get("type")
    if property_type == "select":
        options = property_schema.get("select", {}).get("options", [])
    elif property_type == "status":
        options = property_schema.get("status", {}).get("options", [])
    else:
        return []

    return [option["name"] for option in options if option.get("name")]


def _parse_status_value(property_value: dict) -> str | None:
    property_type = property_value.get("type")
    if property_type == "select":
        select_value = property_value.get("select")
        return select_value.get("name") if select_value else None

    if property_type == "status":
        status_value = property_value.get("status")
        return status_value.get("name") if status_value else None

    return None


def _parse_title(properties: dict) -> str:
    name_property = properties.get(TITLE_PROPERTY)
    if name_property and name_property.get("type") == "title":
        return "".join(item.get("plain_text", "") for item in name_property.get("title", []))

    for property_value in properties.values():
        if property_value.get("type") == "title":
            return "".join(
                item.get("plain_text", "") for item in property_value.get("title", [])
            )

    return ""


def _parse_status(properties: dict) -> str | None:
    for name in STATUS_PROPERTY_NAMES:
        status_property = properties.get(name)
        if status_property:
            status = _parse_status_value(status_property)
            if status:
                return status

    for status_property in properties.values():
        if status_property.get("type") in ("select", "status"):
            status = _parse_status_value(status_property)
            if status:
                return status

    return None


def _parse_rich_text(property_value: dict) -> str:
    rich_text = property_value.get("rich_text", [])
    return "".join(item.get("plain_text", "") for item in rich_text)


def _parse_description(properties: dict) -> str:
    description_property = properties.get(DESCRIPTION_PROPERTY)
    if description_property and description_property.get("type") == "rich_text":
        return _parse_rich_text(description_property)
    return ""


def _parse_due_date(properties: dict) -> str | None:
    for property_name in DUE_DATE_PROPERTIES:
        due_date_property = properties.get(property_name)
        if due_date_property and due_date_property.get("type") == "date":
            date_value = due_date_property.get("date")
            return date_value.get("start") if date_value else None

    for property_value in properties.values():
        if property_value.get("type") == "date":
            date_value = property_value.get("date")
            return date_value.get("start") if date_value else None

    return None


def _parse_task(page: dict) -> dict[str, str | None]:
    properties = page.get("properties", {})
    return {
        "id": page.get("id"),
        "title": _parse_title(properties) or "Без названия",
        "description": _parse_description(properties),
        "status": _parse_status(properties) or "Без статуса",
        "due_date": _parse_due_date(properties),
        "url": page.get("url"),
    }


def _format_existing_select_options(options: list[dict]) -> list[dict[str, str]]:
    return [{"id": option["id"], "name": option["name"]} for option in options]


def _build_task_properties(
    title: str,
    column: str,
    due_date: str | None,
    schema_properties: dict,
) -> dict:
    title_property_name = _find_title_property_name(schema_properties)
    properties: dict = {
        title_property_name: {
            "title": [{"type": "text", "text": {"content": title}}],
        },
    }

    if column:
        status_info = _find_status_property(schema_properties)
        if status_info:
            status_name, status_schema = status_info
            if status_schema.get("type") == "status":
                properties[status_name] = {"status": {"name": column}}
            else:
                properties[status_name] = {"select": {"name": column}}

    if due_date:
        for date_name in DUE_DATE_PROPERTIES:
            date_property = schema_properties.get(date_name)
            if date_property and date_property.get("type") == "date":
                properties[date_name] = {"date": {"start": due_date}}
                break
        else:
            for name, property_value in schema_properties.items():
                if property_value.get("type") == "date":
                    properties[name] = {"date": {"start": due_date}}
                    break

    return properties


def _build_description_blocks(description: str) -> list[dict]:
    return [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": description}}],
            },
        }
    ]


async def add_column_to_database(
    database_id: str,
    new_column: str,
    access_token: str,
) -> dict:
    async with get_notion_client(access_token) as client:
        get_response = await client.http.get(f"/databases/{database_id}")
        get_response.raise_for_status()
        database = get_response.json()

        status_property = database["properties"].get(STATUS_PROPERTY)
        if not status_property or status_property.get("type") != "select":
            raise ValueError("Status select property not found")

        existing_options = status_property["select"]["options"]
        if any(option["name"] == new_column for option in existing_options):
            raise ValueError(f"Column '{new_column}' already exists")

        updated_options = _format_existing_select_options(existing_options)
        updated_options.append(
            {
                "name": new_column,
                "color": STATUS_COLORS[len(existing_options) % len(STATUS_COLORS)],
            }
        )

        patch_response = await client.http.patch(
            f"/databases/{database_id}",
            json={
                "properties": {
                    STATUS_PROPERTY: {
                        "select": {
                            "options": updated_options,
                        }
                    }
                }
            },
        )

    patch_response.raise_for_status()
    return patch_response.json()


async def get_tasks(database_id: str, access_token: str) -> list[dict]:
    """Получает все задачи из базы данных Notion"""
    tasks: list[dict] = []
    start_cursor: str | None = None
    client = AsyncClient(auth=access_token)
    try:
        while True:
            params: dict[str, object] = {
                "data_source_id": database_id,
                "page_size": 100,
            }
            if start_cursor:
                params["start_cursor"] = start_cursor

            response = await client.data_sources.query(**params)

            for page in response.get("results", []):
                tasks.append(_parse_task(page))

            if not response.get("has_more"):
                break

            start_cursor = response.get("next_cursor")

        return tasks
    except Exception as e:
        raise Exception(f"Notion API error: {e}") from e
    finally:
        await client.aclose()


async def get_database_columns(data_source_id: str, access_token: str) -> list[str]:
    """Получает список колонок (статусов) из data source Notion"""
    client = AsyncClient(auth=access_token)
    try:
        data_source = await client.data_sources.retrieve(data_source_id=data_source_id)
        status_info = _find_status_property(data_source.get("properties", {}))
        if not status_info:
            return []

        _, status_property = status_info
        return _extract_status_options(status_property)
    except Exception as e:
        raise Exception(f"Notion API error: {e}") from e
    finally:
        await client.aclose()


async def create_task(
    database_id: str,
    title: str,
    description: str,
    status: str,
    due_date: str | None,
    access_token: str,
) -> str:
    client = AsyncClient(auth=access_token)
    try:
        data_source = await client.data_sources.retrieve(data_source_id=database_id)
        schema_properties = data_source.get("properties", {})

        payload: dict = {
            "parent": {
                "type": "data_source_id",
                "data_source_id": database_id,
            },
            "properties": _build_task_properties(
                title,
                status,
                due_date,
                schema_properties,
            ),
        }

        if description:
            payload["children"] = _build_description_blocks(description)

        page = await client.pages.create(**payload)
        return page.get("id", "")
    except Exception as e:
        raise Exception(f"Notion API error: {e}") from e
    finally:
        await client.aclose()


async def update_task_status(
    task_id: str,
    new_status: str,
    access_token: str,
) -> dict:
    async with get_notion_client(access_token) as client:
        response = await client.http.patch(
            f"/pages/{task_id}",
            json={
                "properties": {
                    STATUS_PROPERTY: {
                        "select": {"name": new_status},
                    }
                }
            },
        )

    response.raise_for_status()
    return response.json()