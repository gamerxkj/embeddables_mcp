# ServiceNow Embedding Diagnostics MCP Server

This MCP (Model Context Protocol) server provides diagnostic tools for checking if a ServiceNow instance is properly configured for embedding components on third-party websites.

## Features

The server can diagnose the following configurations:

1. Check if embeddables are enabled via system property (`glide.uxf.lib.embeddables.enabled`)
2. Check if the Embeddables plugin (`com.glide.ux.embeddables`) is active
3. Check if the Client Access Security plugin (`com.glide.security.client_access`) is active
4. Check if CORS rules are configured for a specific third-party domain
5. Run a full diagnostic and provide specific recommendations

## Prerequisites

- Python 3.8 or higher
- ServiceNow instance with admin access

## Installation

1. Clone this repository
2. Install the dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Starting the Server

```bash
python servicenow_mcp_server.py
```

The server will start on port 6060 by default. You can change the port by setting the `PORT` environment variable.

### Connecting to the MCP Server from an LLM

This MCP server is designed to be used by AI systems that support the Model Context Protocol. When connected, the MCP server will provide several tools to the LLM:

- `connect_to_instance`: Connect to a ServiceNow instance
- `check_embeddables_enabled`: Check if embeddables are enabled
- `check_embeddables_plugin`: Check if the embeddables plugin is active
- `check_client_access_plugin`: Check if the client access security plugin is active
- `check_cors_rule`: Check if a CORS rule exists for a specific domain
- `run_full_diagnostic`: Run all diagnostic checks and provide recommendations

### Example Workflow

Once connected to the MCP server, the LLM will be able to perform these actions:

1. Ask the user for their ServiceNow instance URL
2. Ask the user for their username and password
3. Connect to the instance using the provided credentials
4. Check if all required configurations are in place
5. Ask the user which component they want to embed
6. Ask the user on which third-party website they want to embed it
7. Check if CORS rules are configured for the specified domain
8. Provide recommendations for any missing configurations

## Security Considerations

- This server does not store any credentials
- All communication with ServiceNow is done directly from the server
- For production use, it is recommended to implement OAuth authentication instead of basic authentication

## API Documentation

The MCP server provides a standard MCP interface. You can access the API documentation at the following endpoint:

```
GET /v0/mcp
```

This will return the server metadata and available tools with their schemas.
