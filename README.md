# Document MCP Server

A lightweight [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server written in Python. It exposes tools allowing LLM-powered clients (such as Claude Desktop, Cursor, or AI coding assistants) to discover and read documents from an in-memory document store.

---

## Features

- **Built on MCP SDK 2.x**: Uses `mcp.server.mcpserver.MCPServer` with standard I/O (`stdio`) transport.
- **Tools Provided**:
  - `list_documents`: Lists all available documents in the repository.
  - `read_document`: Fetches the content of a specified document by name.

---

## Project Structure

```text
.
├── mcp_server.py   # Main MCP server implementation and tools
├── app.py          # Application entry / scratchpad
├── .gitignore      # Git ignore rules for virtual environments and caches
└── README.md       # Project documentation
```

---

## Prerequisites

- **Python**: Version 3.10 or later
- **MCP SDK**: `mcp` package (version 2.x)

---

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/dhananjaykumar137c-netizen/mcp_server.git
   cd mcp_server
   ```

2. **Create and activate a virtual environment** (recommended):
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv mcp
     .\mcp\Scripts\Activate.ps1
     ```
   - **macOS / Linux**:
     ```bash
     python -m venv mcp
     source mcp/bin/activate
     ```

3. **Install dependencies**:
   ```bash
   pip install mcp
   ```

---

## Running the Server

Start the server process in standard I/O mode:

```bash
python mcp_server.py
```

> **Note**: Because MCP servers communicate via JSON-RPC over `stdio`, the process will wait silently for messages from an MCP client rather than printing interactive text to your terminal.

---

## Testing with MCP Inspector

The fastest way to test and inspect the tools interactively is using the official MCP Inspector web interface:

```bash
npx @modelcontextprotocol/inspector python mcp_server.py
```

1. A browser window will open automatically.
2. Click **Connect**.
3. Go to the **Tools** tab:
   - Click **`list_documents`** -> **Call Tool** to see all available documents.
   - Click **`read_document`** -> Enter a filename (e.g. `plan.md`) -> **Call Tool** to read its content.

---

## Integration with MCP Clients

To use this server in an MCP client (such as Claude Desktop or other MCP hosts), add it to your configuration file (e.g., `claude_desktop_config.json` or `mcp_config.json`):

```json
{
  "mcpServers": {
    "document-mcp": {
      "command": "python",
      "args": ["c:/Users/dhana/ai_apps/MCP/mcp_server.py"]
    }
  }
}
```

Once configured, your AI assistant will be able to query the documents directly in chat:
> *"What documents do you have access to?"*  
> *"Can you summarize the contents of plan.md?"*

---

## Available Tools Reference

### `list_documents`
- **Arguments**: None (`{}`)
- **Returns**: A comma-separated string containing all document filenames.

### `read_document`
- **Arguments**:
  - `filename` (*string*, required): The name of the document to retrieve.
- **Returns**: The text content of the document, or `"Document not found."` if not present.
