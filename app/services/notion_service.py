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


def _parse_data_source_title(data_source: dict) -> str:
    title = data_source.get("title", [])
    if isinstance(title, list):
        title_text = "".join(
            t.get("plain_text", "") for t in title if isinstance(t, dict)
        )
        return title_text or "Без названия"

    if isinstance(title, str) and title:
        return title

    return "Без названия"


async def get_data_source_info(data_source_id: str, access_token: str) -> dict:
    client = AsyncClient(auth=access_token)
    try:
        data_source = await client.data_sources.retrieve(data_source_id=data_source_id)
        return {
            "id": data_source.get("id", data_source_id),
            "title": _parse_data_source_title(data_source),
            "url": data_source.get("url"),
        }
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
                    ORDER_PROPERTY: {"number": {}},
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
ORDER_PROPERTY = "Order"
ORDER_PROPERTY_NAMES = (ORDER_PROPERTY, "Порядок", "Position")


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
    print(property_type, "property_type")
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


def _find_order_property_name(properties: dict) -> str | None:
    for name in ORDER_PROPERTY_NAMES:
        property_value = properties.get(name)
        if property_value and property_value.get("type") == "number":
            return name
    return None


def _parse_order(properties: dict) -> float | None:
    for name in ORDER_PROPERTY_NAMES:
        property_value = properties.get(name)
        if property_value and property_value.get("type") == "number":
            number_value = property_value.get("number")
            return number_value if number_value is not None else None
    return None


def _sort_tasks(tasks: list[dict]) -> list[dict]:
    def sort_key(task: dict) -> tuple:
        order = task.get("order")
        return (
            task.get("status") or "",
            order if order is not None else float("inf"),
            task.get("title") or "",
        )

    return sorted(tasks, key=sort_key)


def _parse_task(page: dict) -> dict[str, str | float | None]:
    properties = page.get("properties", {})
    return {
        "id": page.get("id"),
        "title": _parse_title(properties) or "Без названия",
        "description": _parse_description(properties),
        "status": _parse_status(properties) or "Без статуса",
        "due_date": _parse_due_date(properties),
        "order": _parse_order(properties),
        "url": page.get("url"),
    }


def _format_existing_select_options(options: list[dict]) -> list[dict]:
    formatted = []
    for option in options:
        item: dict = {"name": option["name"]}
        if option.get("id"):
            item["id"] = option["id"]
        if option.get("color"):
            item["color"] = option["color"]
        formatted.append(item)
    return formatted


def _find_description_property_name(properties: dict) -> str | None:
    for name in (DESCRIPTION_PROPERTY, "Description", "Описание"):
        property_value = properties.get(name)
        if property_value and property_value.get("type") == "rich_text":
            return name
    return None


def _find_date_property_name(properties: dict) -> str | None:
    for date_name in DUE_DATE_PROPERTIES:
        date_property = properties.get(date_name)
        if date_property and date_property.get("type") == "date":
            return date_name

    for name, property_value in properties.items():
        if property_value.get("type") == "date":
            return name

    return None


def _build_task_properties(
    title: str,
    column: str,
    due_date: str | None,
    schema_properties: dict,
    order: float | None = None,
    order_property_name: str | None = None,
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

    resolved_order_property = order_property_name or _find_order_property_name(
        schema_properties
    )
    if order is not None and resolved_order_property:
        properties[resolved_order_property] = {"number": order}

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


async def _update_status_options(
    data_source_id: str,
    access_token: str,
    updated_options: list[dict],
) -> dict:
    client = AsyncClient(auth=access_token)
    try:
        data_source = await client.data_sources.retrieve(data_source_id=data_source_id)
        status_info = _find_status_property(data_source.get("properties", {}))
        if not status_info:
            raise ValueError("Status property not found")

        status_name, status_schema = status_info
        property_type = status_schema.get("type")

        if property_type == "select":
            patch = {status_name: {"select": {"options": updated_options}}}
        elif property_type == "status":
            patch = {status_name: {"status": {"options": updated_options}}}
        else:
            raise ValueError("Unsupported status property type")

        return await client.data_sources.update(
            data_source_id=data_source_id,
            properties=patch,
        )
    except ValueError:
        raise
    except Exception as e:
        raise Exception(f"Notion API error: {e}") from e
    finally:
        await client.aclose()


async def add_column_to_database(
    data_source_id: str,
    new_column: str,
    access_token: str,
) -> dict:
    client = AsyncClient(auth=access_token)
    try:
        data_source = await client.data_sources.retrieve(data_source_id=data_source_id)
        status_info = _find_status_property(data_source.get("properties", {}))
        if not status_info:
            raise ValueError("Status property not found")

        _, status_schema = status_info
        property_type = status_schema.get("type")

        if property_type == "select":
            existing_options = status_schema.get("select", {}).get("options", [])
        elif property_type == "status":
            existing_options = status_schema.get("status", {}).get("options", [])
        else:
            raise ValueError("Unsupported status property type")

        if any(option.get("name") == new_column for option in existing_options):
            raise ValueError(f"Column '{new_column}' already exists")

        updated_options = _format_existing_select_options(existing_options)
        updated_options.append(
            {
                "name": new_column,
                "color": STATUS_COLORS[len(existing_options) % len(STATUS_COLORS)],
            }
        )

        return await _update_status_options(
            data_source_id,
            access_token,
            updated_options,
        )
    except ValueError:
        raise
    except Exception as e:
        raise Exception(f"Notion API error: {e}") from e
    finally:
        await client.aclose()


async def delete_column_from_database(
    data_source_id: str,
    column_title: str,
    access_token: str,
) -> dict:
    columns = await get_database_columns(data_source_id, access_token)
    if column_title not in columns:
        raise ValueError(f"Column '{column_title}' not found")

    if len(columns) <= 1:
        raise ValueError("Нельзя удалить последнюю колонку")

    fallback_status = next(column for column in columns if column != column_title)

    tasks = await get_tasks(data_source_id, access_token)
    for task in tasks:
        if task.get("status") == column_title:
            await update_task_status(task["id"], fallback_status, access_token)

    client = AsyncClient(auth=access_token)
    try:
        data_source = await client.data_sources.retrieve(data_source_id=data_source_id)
        status_info = _find_status_property(data_source.get("properties", {}))
        if not status_info:
            raise ValueError("Status property not found")

        _, status_schema = status_info
        property_type = status_schema.get("type")

        if property_type == "select":
            existing_options = status_schema.get("select", {}).get("options", [])
        elif property_type == "status":
            existing_options = status_schema.get("status", {}).get("options", [])
        else:
            raise ValueError("Unsupported status property type")

        updated_options = _format_existing_select_options(
            [option for option in existing_options if option.get("name") != column_title]
        )

        return await _update_status_options(
            data_source_id,
            access_token,
            updated_options,
        )
    except ValueError:
        raise
    except Exception as e:
        raise Exception(f"Notion API error: {e}") from e
    finally:
        await client.aclose()


async def ensure_order_property(data_source_id: str, access_token: str) -> str:
    client = AsyncClient(auth=access_token)
    try:
        data_source = await client.data_sources.retrieve(data_source_id=data_source_id)
        properties = data_source.get("properties", {})
        existing = _find_order_property_name(properties)
        if existing:
            return existing

        await client.data_sources.update(
            data_source_id=data_source_id,
            properties={ORDER_PROPERTY: {"number": {}}},
        )
        return ORDER_PROPERTY
    except Exception as e:
        raise Exception(f"Notion API error: {e}") from e
    finally:
        await client.aclose()


def _get_next_order_for_status(tasks: list[dict], status: str) -> float:
    status_tasks = [task for task in tasks if task.get("status") == status]
    if not status_tasks:
        return 0

    orders = [
        task["order"]
        for task in status_tasks
        if task.get("order") is not None
    ]
    if not orders:
        return float(len(status_tasks))

    return float(max(orders)) + 1


async def reorder_tasks(
    data_source_id: str,
    status: str,
    task_ids: list[str],
    access_token: str,
) -> None:
    if not task_ids:
        return

    order_property_name = await ensure_order_property(data_source_id, access_token)
    client = AsyncClient(auth=access_token)
    try:
        for index, task_id in enumerate(task_ids):
            page = await client.pages.retrieve(page_id=task_id)
            page_properties = page.get("properties", {})
            task_status = _parse_status(page_properties) or "Без статуса"
            if task_status != status:
                raise ValueError(f"Task '{task_id}' is not in column '{status}'")

            await client.pages.update(
                page_id=task_id,
                properties={order_property_name: {"number": index}},
            )
    except ValueError:
        raise
    except Exception as e:
        raise Exception(f"Notion API error: {e}") from e
    finally:
        await client.aclose()


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

        return _sort_tasks(tasks)
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
        order_property_name = _find_order_property_name(schema_properties)
        if not order_property_name:
            order_property_name = await ensure_order_property(database_id, access_token)
            data_source = await client.data_sources.retrieve(data_source_id=database_id)
            schema_properties = data_source.get("properties", {})

        existing_tasks = await get_tasks(database_id, access_token)
        next_order = _get_next_order_for_status(existing_tasks, status)

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
                order=next_order,
                order_property_name=order_property_name,
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
    return await update_task(
        task_id,
        access_token,
        status=new_status,
    )


async def _update_page_description_blocks(
    client: AsyncClient,
    page_id: str,
    description: str,
) -> None:
    blocks_response = await client.blocks.children.list(block_id=page_id)
    blocks = blocks_response.get("results", [])
    paragraph_blocks = [block for block in blocks if block.get("type") == "paragraph"]
    rich_text = (
        [{"type": "text", "text": {"content": description}}] if description else []
    )

    if paragraph_blocks:
        await client.blocks.update(
            block_id=paragraph_blocks[0]["id"],
            paragraph={"rich_text": rich_text},
        )
    elif description:
        await client.blocks.children.append(
            block_id=page_id,
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": rich_text},
                }
            ],
        )


async def update_task(
    task_id: str,
    access_token: str,
    *,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    due_date: str | None = None,
    clear_due_date: bool = False,
) -> dict:
    client = AsyncClient(auth=access_token)
    try:
        page = await client.pages.retrieve(page_id=task_id)
        page_properties = page.get("properties", {})
        update_properties: dict = {}

        if title is not None:
            title_property_name = _find_title_property_name(page_properties)
            update_properties[title_property_name] = {
                "title": [{"type": "text", "text": {"content": title}}],
            }

        if status is not None:
            status_info = _find_status_property(page_properties)
            if not status_info:
                raise ValueError("Status property not found")

            status_name, status_schema = status_info
            if status_schema.get("type") == "status":
                update_properties[status_name] = {"status": {"name": status}}
            else:
                update_properties[status_name] = {"select": {"name": status}}

        if due_date is not None or clear_due_date:
            date_property_name = _find_date_property_name(page_properties)
            if date_property_name:
                if clear_due_date or not due_date:
                    update_properties[date_property_name] = {"date": None}
                else:
                    update_properties[date_property_name] = {
                        "date": {"start": due_date},
                    }

        description_property_name = _find_description_property_name(page_properties)
        if description is not None and description_property_name:
            update_properties[description_property_name] = {
                "rich_text": (
                    [{"type": "text", "text": {"content": description}}]
                    if description
                    else []
                ),
            }

        updated_page = page
        if update_properties:
            updated_page = await client.pages.update(
                page_id=task_id,
                properties=update_properties,
            )

        if description is not None and not description_property_name:
            await _update_page_description_blocks(client, task_id, description)

        return _parse_task(updated_page)
    except ValueError:
        raise
    except Exception as e:
        raise Exception(f"Notion API error: {e}") from e
    finally:
        await client.aclose()


async def delete_task(task_id: str, access_token: str) -> None:
    client = AsyncClient(auth=access_token)
    try:
        await client.pages.update(page_id=task_id, archived=True)
    except Exception as e:
        raise Exception(f"Notion API error: {e}") from e
    finally:
        await client.aclose()