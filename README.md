# MCP server for Obsidian

MCP server to interact with Obsidian via the Local REST API community plugin.

<a href="https://glama.ai/mcp/servers/3wko1bhuek"><img width="380" height="200" src="https://glama.ai/mcp/servers/3wko1bhuek/badge" alt="server for Obsidian MCP server" /></a>

## Components

### Tools

The server implements multiple tools to interact with Obsidian:

#### Basic File Operations
- `list_files_in_vault`: Lists all files and directories in the root directory of your Obsidian vault
- `list_files_in_dir`: Lists all files and directories in a specific Obsidian directory
- `get_file_contents`: Return the content of a single file in your vault
- `batch_get_file_contents`: Get contents of multiple files at once
- `append_content`: Append content to a new or existing file in the vault
- `delete_file`: Delete a file or directory from your vault

#### Content Editing
- `patch_content`: Insert content into an existing note relative to a heading, block reference, or frontmatter field
- `add_to_heading`: Simplified tool for adding content to a specific heading with better error handling and suggestions

#### Search Tools
- `simple_search`: Search for documents matching a specified text query across all files in the vault
- `complex_search`: Advanced search using JsonLogic queries for complex filtering

#### Periodic Notes
- `get_periodic_note`: Get content of the current periodic note (daily, weekly, etc.)
- `get_recent_periodic_notes`: Get a list of recent periodic notes
- `get_recent_changes`: Get a list of recently modified files in the vault

### Improved Features

#### Simplified Heading Operations
The `add_to_heading` tool provides a much easier way to work with headings:

```python
# List all headings in a note to see what's available
result = obsidian_add_to_heading(
    filepath="Notes/example.md",
    heading="",  # Empty heading for listing
    content="",  # Empty content for listing
    list_headings=True
)

# Add content to a heading section
result = obsidian_add_to_heading(
    filepath="Notes/example.md",
    heading="Section Header",
    content="New content to add",
    position="end",  # "start" or "end"
    trim_whitespace=True  # More forgiving heading matching
)
```

#### Better Error Handling
All operations now provide detailed error messages with helpful suggestions, making it easier to troubleshoot issues when they occur.

#### Path Normalization
File paths are automatically normalized, handling both forward and backslashes consistently, and removing extra whitespace or slashes.

### Example prompts

Its good to first instruct Claude to use Obsidian. Then it will always call the tool.

The use prompts like this:
- Get the contents of the last architecture call note and summarize them
- Search for all files where Azure CosmosDb is mentioned and quickly explain to me the context in which it is mentioned
- Summarize the last meeting notes and put them into a new note 'summary meeting.md'. Add an introduction so that I can send it via email.

## Configuration

### Obsidian REST API Key

There are two ways to configure the environment with the Obsidian REST API Key. 

1. Add to server config (preferred)

```json
{
  "mcp-obsidian": {
    "command": "uvx",
    "args": [
      "mcp-obsidian"
    ],
    "env": {
      "OBSIDIAN_API_KEY": "<your_api_key_here>",
      "OBSIDIAN_HOST": "<your_obsidian_host>"
    }
  }
}
```

2. Create a `.env` file in the working directory with the following required variable:

```
OBSIDIAN_API_KEY=your_api_key_here
OBSIDIAN_HOST=your_obsidian_host
```

Note: You can find the key in the Obsidian plugin config.

## Quickstart

### Install

#### Obsidian REST API

You need the Obsidian REST API community plugin running: https://github.com/coddingtonbear/obsidian-local-rest-api

Install and enable it in the settings and copy the api key.

#### Claude Desktop

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`

On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>Development/Unpublished Servers Configuration</summary>
  
```json
{
  "mcpServers": {
    "mcp-obsidian": {
      "command": "uv",
      "args": [
        "--directory",
        "<dir_to>/mcp-obsidian",
        "run",
        "mcp-obsidian"
      ]
    }
  }
}
```
</details>

<details>
  <summary>Published Servers Configuration</summary>
  
```json
{
  "mcpServers": {
    "mcp-obsidian": {
      "command": "uvx",
      "args": [
        "mcp-obsidian"
      ],
      "env": {
        "OBSIDIAN_API_KEY" : "<YOUR_OBSIDIAN_API_KEY>"
      }
    }
  }
}
```
</details>

## Development

### Building

To prepare the package for distribution:

1. Sync dependencies and update lockfile:
```bash
uv sync
```

### Debugging

Since MCP servers run over stdio, debugging can be challenging. For the best debugging
experience, we strongly recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).

You can launch the MCP Inspector via [`npm`](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) with this command:

```bash
npx @modelcontextprotocol/inspector uv --directory /path/to/mcp-obsidian run mcp-obsidian
```

Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.

You can also watch the server logs with this command:

```bash
tail -n 20 -f ~/Library/Logs/Claude/mcp-server-mcp-obsidian.log
```
