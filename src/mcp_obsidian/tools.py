from collections.abc import Sequence
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
import json
import os
from . import obsidian

api_key = os.getenv("OBSIDIAN_API_KEY", "")
obsidian_host = os.getenv("OBSIDIAN_HOST", "127.0.0.1")

if api_key == "":
    raise ValueError(f"OBSIDIAN_API_KEY environment variable required. Working directory: {os.getcwd()}")

TOOL_LIST_FILES_IN_VAULT = "obsidian_list_files_in_vault"
TOOL_LIST_FILES_IN_DIR = "obsidian_list_files_in_dir"

class ToolHandler():
    def __init__(self, tool_name: str):
        self.name = tool_name

    def get_tool_description(self) -> Tool:
        raise NotImplementedError()

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        raise NotImplementedError()
    
class ListFilesInVaultToolHandler(ToolHandler):
    def __init__(self):
        super().__init__(TOOL_LIST_FILES_IN_VAULT)

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Lists all files and directories in the root directory of your Obsidian vault.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)

        files = api.list_files_in_vault()

        return [
            TextContent(
                type="text",
                text=json.dumps(files, indent=2)
            )
        ]
    
class ListFilesInDirToolHandler(ToolHandler):
    def __init__(self):
        super().__init__(TOOL_LIST_FILES_IN_DIR)

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Lists all files and directories that exist in a specific Obsidian directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dirpath": {
                        "type": "string",
                        "description": "Path to list files from (relative to your vault root). Note that empty directories will not be returned."
                    },
                },
                "required": ["dirpath"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:

        if "dirpath" not in args:
            raise RuntimeError("dirpath argument missing in arguments")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)

        files = api.list_files_in_dir(args["dirpath"])

        return [
            TextContent(
                type="text",
                text=json.dumps(files, indent=2)
            )
        ]
    
class GetFileContentsToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_file_contents")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Return the content of a single file in your vault.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the relevant file (relative to your vault root).",
                        "format": "path"
                    },
                },
                "required": ["filepath"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "filepath" not in args:
            raise RuntimeError("filepath argument missing in arguments")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)

        content = api.get_file_contents(args["filepath"])

        return [
            TextContent(
                type="text",
                text=json.dumps(content, indent=2)
            )
        ]
    
class SearchToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_simple_search")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="""Simple search for documents matching a specified text query across all files in the vault. 
            Use this tool when you want to do a simple text search""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text to a simple search for in the vault."
                    },
                    "context_length": {
                        "type": "integer",
                        "description": "How much context to return around the matching string (default: 100)",
                        "default": 100
                    }
                },
                "required": ["query"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "query" not in args:
            raise RuntimeError("query argument missing in arguments")

        context_length = args.get("context_length", 100)
        
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        results = api.search(args["query"], context_length)
        
        formatted_results = []
        for result in results:
            formatted_matches = []
            for match in result.get('matches', []):
                context = match.get('context', '')
                match_pos = match.get('match', {})
                start = match_pos.get('start', 0)
                end = match_pos.get('end', 0)
                
                formatted_matches.append({
                    'context': context,
                    'match_position': {'start': start, 'end': end}
                })
                
            formatted_results.append({
                'filename': result.get('filename', ''),
                'score': result.get('score', 0),
                'matches': formatted_matches
            })

        return [
            TextContent(
                type="text",
                text=json.dumps(formatted_results, indent=2)
            )
        ]
    
class AppendContentToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_append_content")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="Append content to a new or existing file in the vault.",
           inputSchema={
               "type": "object",
               "properties": {
                   "filepath": {
                       "type": "string",
                       "description": "Path to the file (relative to vault root)",
                       "format": "path"
                   },
                   "content": {
                       "type": "string",
                       "description": "Content to append to the file"
                   }
               },
               "required": ["filepath", "content"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if "filepath" not in args or "content" not in args:
           raise RuntimeError("filepath and content arguments required")

       api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
       api.append_content(args.get("filepath", ""), args["content"])

       return [
           TextContent(
               type="text",
               text=f"Successfully appended content to {args['filepath']}"
           )
       ]
   
class PatchContentToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_patch_content")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="Insert content into an existing note relative to a heading, block reference, or frontmatter field.",
           inputSchema={
               "type": "object",
               "properties": {
                   "filepath": {
                       "type": "string",
                       "description": "Path to the file (relative to vault root)",
                       "format": "path"
                   },
                   "operation": {
                       "type": "string",
                       "description": "Operation to perform (append, prepend, or replace)",
                       "enum": ["append", "prepend", "replace"]
                   },
                   "target_type": {
                       "type": "string",
                       "description": "Type of target to patch",
                       "enum": ["heading", "block", "frontmatter"]
                   },
                   "target": {
                       "type": "string",
                       "description": "Target identifier (heading path, block reference, or frontmatter field)"
                   },
                   "content": {
                       "type": "string",
                       "description": "Content to insert"
                   },
                   "create_if_missing": {
                       "type": "boolean",
                       "description": "Whether to create the target if it doesn't exist (default: false)",
                       "default": False
                   },
                   "trim_whitespace": {
                       "type": "boolean",
                       "description": "Whether to trim whitespace from target before matching (default: false)",
                       "default": False
                   }
               },
               "required": ["filepath", "operation", "target_type", "target", "content"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if not all(k in args for k in ["filepath", "operation", "target_type", "target", "content"]):
           raise RuntimeError("filepath, operation, target_type, target and content arguments required")

       try:
           api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)

           # Extract optional parameters
           create_if_missing = args.get("create_if_missing", False)
           trim_whitespace = args.get("trim_whitespace", False)

           # If this is a heading target, try to find the heading first to provide better feedback
           if args.get("target_type") == "heading":
               # Try to get headings from the file
               headings = api.find_headings(args["filepath"])
               if headings:
                   # Check if the target heading exists
                   target_heading = args["target"]
                   matching_headings = [h for h in headings if h["path"] == target_heading]

                   if not matching_headings and not create_if_missing:
                       # If no exact match, try to find similar headings
                       similar_headings = [h["path"] for h in headings if target_heading in h["path"] or h["path"] in target_heading]

                       if similar_headings:
                           suggestion = f"No exact match for heading '{target_heading}'. Similar headings: {', '.join(similar_headings)}"
                           if trim_whitespace:
                               suggestion += ". Target already has trim_whitespace=true."
                           else:
                               suggestion += ". Consider using trim_whitespace=true or check exact heading path."

                           return [
                               TextContent(
                                   type="text",
                                   text=suggestion
                               )
                           ]

           # Call the API with all parameters
           api.patch_content(
               args["filepath"],
               args["operation"],
               args["target_type"],
               args["target"],
               args["content"],
               create_if_missing=create_if_missing,
               trim_whitespace=trim_whitespace
           )

           return [
               TextContent(
                   type="text",
                   text=f"Successfully patched content in {args['filepath']}"
               )
           ]
       except Exception as e:
           # Provide a more user-friendly error message
           error_message = str(e)

           # Add suggestions based on the error
           if "404" in error_message and args.get("target_type") == "heading":
               error_message += "\n\nSuggestion: Check that the heading exists exactly as specified. You can use trim_whitespace=true to ignore whitespace differences, or create_if_missing=true to create the heading if it doesn't exist."
           elif "400" in error_message:
               error_message += "\n\nSuggestion: Verify that your operation, target_type, and target values are valid. Heading paths should use :: as delimiters between levels."

           raise RuntimeError(error_message)

class DeleteFileToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_delete_file")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="Delete a file or directory from the vault.",
           inputSchema={
               "type": "object",
               "properties": {
                   "filepath": {
                       "type": "string",
                       "description": "Path to the file or directory to delete (relative to vault root)",
                       "format": "path"
                   },
                   "confirm": {
                       "type": "boolean",
                       "description": "Confirmation to delete the file (must be true)",
                       "default": False
                   }
               },
               "required": ["filepath", "confirm"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if "filepath" not in args:
           raise RuntimeError("filepath argument missing in arguments")
       
       if not args.get("confirm", False):
           raise RuntimeError("confirm must be set to true to delete a file")

       api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
       api.delete_file(args["filepath"])

       return [
           TextContent(
               type="text",
               text=f"Successfully deleted {args['filepath']}"
           )
       ]
   
class ComplexSearchToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_complex_search")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="""Complex search for documents using a JsonLogic query. 
           Supports standard JsonLogic operators plus 'glob' and 'regexp' for pattern matching. Results must be non-falsy.

           Use this tool when you want to do a complex search, e.g. for all documents with certain tags etc.
           """,
           inputSchema={
               "type": "object",
               "properties": {
                   "query": {
                       "type": "object",
                       "description": "JsonLogic query object. Example: {\"glob\": [\"*.md\", {\"var\": \"path\"}]} matches all markdown files"
                   }
               },
               "required": ["query"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if "query" not in args:
           raise RuntimeError("query argument missing in arguments")

       api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
       results = api.search_json(args.get("query", ""))

       return [
           TextContent(
               type="text",
               text=json.dumps(results, indent=2)
           )
       ]

class BatchGetFileContentsToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_batch_get_file_contents")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Return the contents of multiple files in your vault, concatenated with headers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepaths": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "Path to a file (relative to your vault root)",
                            "format": "path"
                        },
                        "description": "List of file paths to read"
                    },
                },
                "required": ["filepaths"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "filepaths" not in args:
            raise RuntimeError("filepaths argument missing in arguments")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        content = api.get_batch_file_contents(args["filepaths"])

        return [
            TextContent(
                type="text",
                text=content
            )
        ]

class PeriodicNotesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_periodic_note")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get current periodic note for the specified period.",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": "The period type (daily, weekly, monthly, quarterly, yearly)",
                        "enum": ["daily", "weekly", "monthly", "quarterly", "yearly"]
                    }
                },
                "required": ["period"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "period" not in args:
            raise RuntimeError("period argument missing in arguments")

        period = args["period"]
        valid_periods = ["daily", "weekly", "monthly", "quarterly", "yearly"]
        if period not in valid_periods:
            raise RuntimeError(f"Invalid period: {period}. Must be one of: {', '.join(valid_periods)}")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        content = api.get_periodic_note(period)

        return [
            TextContent(
                type="text",
                text=content
            )
        ]
        
class RecentPeriodicNotesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_recent_periodic_notes")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get most recent periodic notes for the specified period type.",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": "The period type (daily, weekly, monthly, quarterly, yearly)",
                        "enum": ["daily", "weekly", "monthly", "quarterly", "yearly"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of notes to return (default: 5)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 50
                    },
                    "include_content": {
                        "type": "boolean",
                        "description": "Whether to include note content (default: false)",
                        "default": False
                    }
                },
                "required": ["period"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "period" not in args:
            raise RuntimeError("period argument missing in arguments")

        period = args["period"]
        valid_periods = ["daily", "weekly", "monthly", "quarterly", "yearly"]
        if period not in valid_periods:
            raise RuntimeError(f"Invalid period: {period}. Must be one of: {', '.join(valid_periods)}")

        limit = args.get("limit", 5)
        if not isinstance(limit, int) or limit < 1:
            raise RuntimeError(f"Invalid limit: {limit}. Must be a positive integer")
            
        include_content = args.get("include_content", False)
        if not isinstance(include_content, bool):
            raise RuntimeError(f"Invalid include_content: {include_content}. Must be a boolean")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        results = api.get_recent_periodic_notes(period, limit, include_content)

        return [
            TextContent(
                type="text",
                text=json.dumps(results, indent=2)
            )
        ]
        
class RecentChangesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_recent_changes")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get recently modified files in the vault.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of files to return (default: 10)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    },
                    "days": {
                        "type": "integer",
                        "description": "Only include files modified within this many days (default: 90)",
                        "minimum": 1,
                        "default": 90
                    }
                }
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        limit = args.get("limit", 10)
        if not isinstance(limit, int) or limit < 1:
            raise RuntimeError(f"Invalid limit: {limit}. Must be a positive integer")

        days = args.get("days", 90)
        if not isinstance(days, int) or days < 1:
            raise RuntimeError(f"Invalid days: {days}. Must be a positive integer")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        results = api.get_recent_changes(limit, days)

        return [
            TextContent(
                type="text",
                text=json.dumps(results, indent=2)
            )
        ]

class AddToHeadingToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_add_to_heading")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Add content to a specific heading in a note (simplified version of patch_content).",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file (relative to vault root)",
                        "format": "path"
                    },
                    "heading": {
                        "type": "string",
                        "description": "Heading text (exact match or partial match with trim_whitespace=true)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to add to the heading section"
                    },
                    "position": {
                        "type": "string",
                        "description": "Where to add the content - start or end of the section (default: end)",
                        "enum": ["start", "end"],
                        "default": "end"
                    },
                    "trim_whitespace": {
                        "type": "boolean",
                        "description": "Whether to trim whitespace from heading before matching (default: true)",
                        "default": True
                    },
                    "create_if_missing": {
                        "type": "boolean",
                        "description": "Whether to create the heading if it doesn't exist (default: false)",
                        "default": False
                    },
                    "list_headings": {
                        "type": "boolean",
                        "description": "If true, returns a list of all headings in the file before proceeding (default: false)",
                        "default": False
                    }
                },
                "required": ["filepath", "heading", "content"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if not all(k in args for k in ["filepath", "heading", "content"]):
            raise RuntimeError("filepath, heading, and content arguments required")

        filepath = args["filepath"]
        heading = args["heading"]
        content = args["content"]
        position = args.get("position", "end")
        trim_whitespace = args.get("trim_whitespace", True)
        create_if_missing = args.get("create_if_missing", False)
        list_headings = args.get("list_headings", False)

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)

        # If list_headings is true, get all headings first
        if list_headings:
            try:
                headings = api.find_headings(filepath)
                if headings:
                    heading_list = "\n".join([f"Level {h['level']}: {h['text']} (path: {h['path']})" for h in headings])
                    return [
                        TextContent(
                            type="text",
                            text=f"Headings in {filepath}:\n\n{heading_list}\n\nUse one of these paths with the 'heading' parameter to target a specific section."
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"No headings found in {filepath}."
                        )
                    ]
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=f"Error getting headings: {str(e)}"
                    )
                ]

        try:
            # First, try to get the headings to find a match
            headings = api.find_headings(filepath)

            # Try to find an exact match first
            exact_match = None
            similar_matches = []

            for h in headings:
                if h["path"] == heading:
                    exact_match = h["path"]
                    break
                elif heading in h["path"] or (trim_whitespace and heading.strip() in h["path"].strip()):
                    similar_matches.append(h["path"])

            # If we have an exact match, use it
            if exact_match:
                target = exact_match
            # If we have similar matches and trim_whitespace is enabled, use the first one
            elif similar_matches and trim_whitespace:
                target = similar_matches[0]
            # Otherwise use the heading as provided
            else:
                target = heading

            # Convert position to operation
            operation = "append" if position == "end" else "prepend"

            # Call the patch_content method
            api.patch_content(
                filepath,
                operation,
                "heading",
                target,
                content,
                create_if_missing=create_if_missing,
                trim_whitespace=trim_whitespace
            )

            return [
                TextContent(
                    type="text",
                    text=f"Successfully added content to heading '{target}' in {filepath}"
                )
            ]
        except Exception as e:
            error_message = str(e)

            # If we have headings but no match, suggest alternatives
            if headings and "404" in error_message:
                suggestions = "\n".join([f"- {h['path']}" for h in headings])
                error_message += f"\n\nAvailable headings in {filepath}:\n{suggestions}\n\nTry using one of these heading paths or set create_if_missing=true to create a new heading."

            raise RuntimeError(error_message)
