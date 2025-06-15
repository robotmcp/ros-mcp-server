import asyncio
from fastmcp import Client


async def test_mcp():
    async with Client("server.py") as client:
        tools = await client.list_tools()
        print("Доступные инструменты:", tools)

        # Тестовый вызов make_step
        result = await client.call_tool("make_step", {"direction": {"x": 0.0, "z": 1.0}})
        print("Результат make_step:", result.text)


if __name__ == "__main__":
    asyncio.run(test_mcp())