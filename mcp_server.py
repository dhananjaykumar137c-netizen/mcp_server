from mcp.server.mcpserver import MCPServer

mcp = MCPServer("DocumentMCP")

docs = {
    "deposition.md": "This deposition covers the testimony of Angela Smith, P.E.",
    "report.pdf": "The report details the state of a 20m condenser tower.",
    "financials.docx": "These financials outline the project's budget and expenditures",
    "outlook.pdf": "This document presents the projected future performance of the system",
    "plan.md": "The plan outlines the steps for the project's implementation.",
    "spec.txt": "These specifications define the technical requirements for the equipment",
}

@mcp.tool()
def list_documents() -> str:
    """Lists all the documents available in the system."""
    return ", ".join(docs.keys())

@mcp.tool()
def read_document(filename: str) -> str:
    """Reads the content of a document.

    Args:
        filename: The name of the document to read.
    """
    return docs.get(filename, "Document not found.")

if __name__ == "__main__":
    mcp.run()