import asyncio
import os
import shutil
import sys
from contextlib import AsyncExitStack
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp import Client, StdioServerParameters
from mcp_types import TextContent

load_dotenv()  # load environment variables from .env

# Gemini model constant
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip().strip('"').strip("'")
MAX_TOOL_TURNS = 10


def clean_schema(schema: dict | None) -> dict:
    """Ensure JSON schema from MCP is clean and compatible with Gemini function declarations."""
    if not isinstance(schema, dict):
        return {"type": "object", "properties": {}}
    cleaned = {k: v for k, v in schema.items() if k not in ("$schema", "title")}
    if "type" not in cleaned:
        cleaned["type"] = "object"
    return cleaned


def extract_text(response) -> str:
    """Safely extract text content from a Gemini response without throwing if only function calls exist."""
    texts = []
    if hasattr(response, "candidates") and response.candidates:
        for candidate in response.candidates:
            if hasattr(candidate, "content") and candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if getattr(part, "text", None):
                        texts.append(part.text)
    return "\n".join(texts)


class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.client: Client | None = None
        self.exit_stack = AsyncExitStack()
        self._gemini: genai.Client | None = None

    @property
    def gemini(self) -> genai.Client:
        """Lazy-initialize Gemini client when needed"""
        if self._gemini is None:
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            self._gemini = genai.Client(api_key=api_key) if api_key else genai.Client()
        return self._gemini

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        if is_python:
            path = Path(server_script_path).resolve()
            # If uv is installed and available, use uv; otherwise fallback to the current Python interpreter
            command = "uv" if shutil.which("uv") else sys.executable
            args = ["--directory", str(path.parent), "run", path.name] if command == "uv" else [str(path)]
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=None,
            )
        else:
            server_params = StdioServerParameters(command="node", args=[server_script_path], env=None)

        # Client launches the command itself when given StdioServerParameters.
        # "auto" probes server/discover, falling back to the 2025-11-25 handshake.
        self.client = await self.exit_stack.enter_async_context(Client(server_params, mode="auto"))

        # List available tools
        response = await self.client.list_tools()
        tools = response.tools
        print(f"\nConnected over protocol {self.client.protocol_version} with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Gemini and available tools"""
        tools_response = await self.client.list_tools()
        function_declarations = [
            {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": clean_schema(tool.input_schema),
            }
            for tool in tools_response.tools
        ]

        tools = [{"function_declarations": function_declarations}] if function_declarations else None

        # Start a chat session with Gemini equipped with the MCP tools
        chat = self.gemini.chats.create(
            model=GEMINI_MODEL,
            config=types.GenerateContentConfig(
                tools=tools,
                temperature=0.0,
            ),
        )

        final_text = []

        response = chat.send_message(query)

        for _ in range(MAX_TOOL_TURNS):
            if not response.function_calls:
                text = extract_text(response)
                if text:
                    final_text.append(text)
                return "\n".join(final_text)

            text = extract_text(response)
            if text:
                final_text.append(text)

            function_responses = []
            for function_call in response.function_calls:
                tool_name = function_call.name
                tool_args = dict(function_call.args) if function_call.args else {}

                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                # call_tool validates the result against the declared schema
                result = await self.client.call_tool(tool_name, tool_args)

                # structured_content is data the application can use directly
                if getattr(result, "structured_content", None) and isinstance(result.structured_content, list):
                    final_text.append(f"[{tool_name} returned {len(result.structured_content)} items]")

                # content is a list of block types; forward only the text ones
                tool_result_text = "\n".join(
                    block.text for block in result.content if isinstance(block, TextContent)
                )

                function_responses.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response={"result": tool_result_text},
                    )
                )

            # Send tool execution results back to Gemini
            response = chat.send_message(function_responses)

        final_text.append(f"[Stopped after {MAX_TOOL_TURNS} tool-use turns]")
        text = extract_text(response)
        if text:
            final_text.append(text)
        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            # input() blocks, so keep it off the event loop.
            try:
                query = (await asyncio.to_thread(input, "\nQuery: ")).strip()
            except (EOFError, KeyboardInterrupt):
                break

            if query.lower() == "quit":
                break

            try:
                response = await self.process_query(query)
                print("\n" + response)
            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python mcp_client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])

        # Check if we have a valid API key to continue
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("\nNo GEMINI_API_KEY found. To query these tools with Gemini, set your API key in .env:")
            print("  GEMINI_API_KEY=your-api-key-here")
            return

        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())