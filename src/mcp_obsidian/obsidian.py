import requests
import urllib.parse
from typing import Any

class Obsidian():
    def __init__(
            self,
            api_key: str,
            protocol: str = 'https',
            host: str = "127.0.0.1",
            port: int = 27124,
            verify_ssl: bool = False,
        ):
        self.api_key = api_key
        self.protocol = protocol
        self.host = host
        self.port = port
        self.verify_ssl = verify_ssl
        self.timeout = (3, 6)

    def _normalize_path(self, path: str) -> str:
        """
        Normalize a file or directory path to a consistent format.

        Args:
            path: File or directory path (relative to vault root)

        Returns:
            Normalized path

        This method:
        1. Removes leading/trailing slashes and whitespace
        2. Replaces backslashes with forward slashes
        3. Normalizes consecutive slashes to single slashes
        """
        if not path:
            return ""

        # Remove leading/trailing whitespace and slashes
        path = path.strip().strip('/')

        # Replace backslashes with forward slashes (for Windows paths)
        path = path.replace('\\', '/')

        # Normalize multiple consecutive slashes to a single slash
        while '//' in path:
            path = path.replace('//', '/')

        return path

    def get_base_url(self) -> str:
        return f'{self.protocol}://{self.host}:{self.port}'
    
    def _get_headers(self) -> dict:
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }
        return headers

    def _safe_call(self, f, operation=None, context=None) -> Any:
        """
        Safely call a function and provide enhanced error messages with context.

        Args:
            f: Function to call
            operation: String describing the operation being performed (e.g., "patch_content", "get_file_contents")
            context: Dictionary with additional context about the operation (e.g., filepath, target_type)

        Returns:
            Result from the function call

        Raises:
            Exception with detailed error information and suggestions
        """
        try:
            return f()
        except requests.HTTPError as e:
            status_code = e.response.status_code
            error_data = e.response.json() if e.response.content else {}
            code = error_data.get('errorCode', -1)
            message = error_data.get('message', '<unknown>')

            # Build enhanced error message with context
            error_msg = f"Error {code}: {message}"

            # Add operation context if provided
            if operation:
                error_msg = f"{error_msg}\nOperation: {operation}"

            # Include relevant context details
            if context:
                context_details = ", ".join([f"{k}='{v}'" for k, v in context.items() if v])
                if context_details:
                    error_msg = f"{error_msg}\nContext: {context_details}"

            # Add helpful suggestions based on status code and error
            if status_code == 404:
                if operation == "get_file_contents":
                    filepath = context.get('filepath', '') if context else ''
                    error_msg = f"{error_msg}\nSuggestion: Check if the file '{filepath}' exists in your vault. Use list_files_in_vault() to see available files."
                elif operation == "patch_content":
                    error_msg = f"{error_msg}\nSuggestion: Verify that the target exists in the document. For headings, ensure exact match including whitespace and case."
            elif status_code == 400:
                if operation == "patch_content":
                    error_msg = f"{error_msg}\nSuggestion: Check that your operation, target_type, and target values are valid. Ensure target is properly URL-encoded if it contains special characters."

            raise Exception(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"

            # Add operation context if provided
            if operation:
                error_msg = f"{error_msg}\nOperation: {operation}"

            # Add context-specific suggestions
            if "Connection refused" in str(e):
                error_msg = f"{error_msg}\nSuggestion: Verify that Obsidian is running and the Local REST API plugin is enabled. Check that the host ({self.host}) and port ({self.port}) are correct."

            raise Exception(error_msg)

    def list_files_in_vault(self) -> Any:
        """
        List all files and directories in the root of the vault.

        Returns:
            List of files and directories
        """
        url = f"{self.get_base_url()}/vault/"

        def call_fn():
            response = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()

            return response.json()['files']

        return self._safe_call(call_fn, operation="list_files_in_vault")


    def list_files_in_dir(self, dirpath: str) -> Any:
        """
        List all files and directories in a specific directory.

        Args:
            dirpath: Path to directory (relative to vault root)

        Returns:
            List of files and directories

        Note:
            Empty directories will not be returned.
        """
        # Normalize path to ensure consistent format
        dirpath = self._normalize_path(dirpath)
        url = f"{self.get_base_url()}/vault/{dirpath}/"

        def call_fn():
            response = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()

            return response.json()['files']

        return self._safe_call(call_fn, operation="list_files_in_dir", context={"dirpath": dirpath})

    def get_file_contents(self, filepath: str) -> Any:
        """
        Get the content of a file in the vault.

        Args:
            filepath: Path to file (relative to vault root)

        Returns:
            Content of the file as text
        """
        # Normalize path to ensure consistent format
        filepath = self._normalize_path(filepath)
        url = f"{self.get_base_url()}/vault/{filepath}"

        def call_fn():
            response = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()

            return response.text

        return self._safe_call(call_fn, operation="get_file_contents", context={"filepath": filepath})
    
    def get_batch_file_contents(self, filepaths: list[str]) -> str:
        """Get contents of multiple files and concatenate them with headers.
        
        Args:
            filepaths: List of file paths to read
            
        Returns:
            String containing all file contents with headers
        """
        result = []
        
        for filepath in filepaths:
            try:
                content = self.get_file_contents(filepath)
                result.append(f"# {filepath}\n\n{content}\n\n---\n\n")
            except Exception as e:
                # Add error message but continue processing other files
                result.append(f"# {filepath}\n\nError reading file: {str(e)}\n\n---\n\n")
                
        return "".join(result)

    def search(self, query: str, context_length: int = 100) -> Any:
        """
        Search for documents matching a specified text query.

        Args:
            query: Search query string
            context_length: How much context to return around the matching string (default: 100)

        Returns:
            List of search results with matches and context
        """
        url = f"{self.get_base_url()}/search/simple/"
        params = {
            'query': query,
            'contextLength': context_length
        }

        def call_fn():
            response = requests.post(url, headers=self._get_headers(), params=params, verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            return response.json()

        return self._safe_call(call_fn, operation="search", context={"query": query, "context_length": str(context_length)})
    
    def append_content(self, filepath: str, content: str) -> Any:
        """
        Append content to a new or existing file in the vault.

        Args:
            filepath: Path to the file (relative to vault root)
            content: Content to append to the file

        Returns:
            None on success
        """
        # Normalize the file path
        filepath = self._normalize_path(filepath)
        url = f"{self.get_base_url()}/vault/{filepath}"

        def call_fn():
            response = requests.post(
                url,
                headers=self._get_headers() | {'Content-Type': 'text/markdown'},
                data=content,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            return None

        return self._safe_call(call_fn, operation="append_content", context={"filepath": filepath})
    
    def patch_content(self, filepath: str, operation: str, target_type: str, target: str, content: str,
                    create_if_missing: bool = False, trim_whitespace: bool = False) -> Any:
        """
        Insert content into an existing note relative to a heading, block reference, or frontmatter field.

        Args:
            filepath: Path to the file (relative to vault root)
            operation: Operation to perform (append, prepend, or replace)
            target_type: Type of target (heading, block, or frontmatter)
            target: Target identifier (heading path, block reference, or frontmatter field)
            content: Content to insert
            create_if_missing: Whether to create the target if it doesn't exist (optional)
            trim_whitespace: Whether to trim whitespace from target before matching (optional)

        Returns:
            None on success

        Raises:
            Exception: If the operation fails with detailed context and suggestions

        Examples:
            # Append content to a heading
            patch_content("Notes/example.md", "append", "heading", "Heading 1", "New content")

            # Replace content in a block
            patch_content("Notes/example.md", "replace", "block", "abc123", "New content")

            # Set a frontmatter field
            patch_content("Notes/example.md", "replace", "frontmatter", "status", "completed")
        """
        # Validate inputs
        valid_operations = ["append", "prepend", "replace"]
        if operation not in valid_operations:
            raise ValueError(f"Operation must be one of: {', '.join(valid_operations)}")

        valid_target_types = ["heading", "block", "frontmatter"]
        if target_type not in valid_target_types:
            raise ValueError(f"Target type must be one of: {', '.join(valid_target_types)}")

        if not target:
            raise ValueError("Target cannot be empty")

        # Normalize file path
        filepath = self._normalize_path(filepath)
        url = f"{self.get_base_url()}/vault/{filepath}"

        # Prepare headers with properly encoded target
        headers = self._get_headers() | {
            'Content-Type': 'text/markdown',
            'Operation': operation,
            'Target-Type': target_type,
            'Target': urllib.parse.quote(target)
        }

        # Add optional headers
        if create_if_missing:
            headers['Create-Target-If-Missing'] = 'true'

        if trim_whitespace:
            headers['Trim-Target-Whitespace'] = 'true'

        def call_fn():
            response = requests.patch(url, headers=headers, data=content, verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            return None

        # Create context for error handling
        context = {
            "filepath": filepath,
            "operation": operation,
            "target_type": target_type,
            "target": target,
            "create_if_missing": str(create_if_missing),
            "trim_whitespace": str(trim_whitespace)
        }

        return self._safe_call(call_fn, operation="patch_content", context=context)
    
    def delete_file(self, filepath: str) -> Any:
        """Delete a file or directory from the vault.

        Args:
            filepath: Path to the file to delete (relative to vault root)

        Returns:
            None on success

        Raises:
            Exception: If the file doesn't exist or can't be deleted
        """
        # Normalize the file path
        filepath = self._normalize_path(filepath)
        url = f"{self.get_base_url()}/vault/{filepath}"

        def call_fn():
            response = requests.delete(url, headers=self._get_headers(), verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            return None

        return self._safe_call(call_fn, operation="delete_file", context={"filepath": filepath})
    
    def search_json(self, query: dict) -> Any:
        """
        Search for documents using a JsonLogic query.

        Args:
            query: JsonLogic query object (see API docs for format)

        Returns:
            List of search results matching the query

        Examples:
            # Find notes with a specific tag
            search_json({"in": ["mytag", {"var": "tags"}]})

            # Find notes with a specific frontmatter field value
            search_json({"==": [{"var": "frontmatter.status"}, "completed"]})

            # Find notes with file paths matching a pattern
            search_json({"glob": ["*.md", {"var": "path"}]})
        """
        url = f"{self.get_base_url()}/search/"

        headers = self._get_headers() | {
            'Content-Type': 'application/vnd.olrapi.jsonlogic+json'
        }

        def call_fn():
            response = requests.post(url, headers=headers, json=query, verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            return response.json()

        return self._safe_call(call_fn, operation="search_json", context={"query": str(query)})
    
    def get_periodic_note(self, period: str) -> Any:
        """Get current periodic note for the specified period.
        
        Args:
            period: The period type (daily, weekly, monthly, quarterly, yearly)
            
        Returns:
            Content of the periodic note
        """
        url = f"{self.get_base_url()}/periodic/{period}/"
        
        def call_fn():
            response = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            
            return response.text

        return self._safe_call(call_fn)
    
    def get_recent_periodic_notes(self, period: str, limit: int = 5, include_content: bool = False) -> Any:
        """Get most recent periodic notes for the specified period type.
        
        Args:
            period: The period type (daily, weekly, monthly, quarterly, yearly)
            limit: Maximum number of notes to return (default: 5)
            include_content: Whether to include note content (default: False)
            
        Returns:
            List of recent periodic notes
        """
        url = f"{self.get_base_url()}/periodic/{period}/recent"
        params = {
            "limit": limit,
            "includeContent": include_content
        }
        
        def call_fn():
            response = requests.get(
                url, 
                headers=self._get_headers(), 
                params=params,
                verify=self.verify_ssl, 
                timeout=self.timeout
            )
            response.raise_for_status()
            
            return response.json()

        return self._safe_call(call_fn)
    
    def get_recent_changes(self, limit: int = 10, days: int = 90) -> Any:
        """Get recently modified files in the vault.

        Args:
            limit: Maximum number of files to return (default: 10)
            days: Only include files modified within this many days (default: 90)

        Returns:
            List of recently modified files with metadata
        """
        # Build the DQL query
        query_lines = [
            "TABLE file.mtime",
            f"WHERE file.mtime >= date(today) - dur({days} days)",
            "SORT file.mtime DESC",
            f"LIMIT {limit}"
        ]

        # Join with proper DQL line breaks
        dql_query = "\n".join(query_lines)

        # Make the request to search endpoint
        url = f"{self.get_base_url()}/search/"
        headers = self._get_headers() | {
            'Content-Type': 'application/vnd.olrapi.dataview.dql+txt'
        }

        def call_fn():
            response = requests.post(
                url,
                headers=headers,
                data=dql_query.encode('utf-8'),
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        return self._safe_call(call_fn, operation="get_recent_changes", context={"limit": str(limit), "days": str(days)})

    # --------- HELPER METHODS FOR COMMON OPERATIONS ---------

    def add_to_heading(self, filepath: str, heading: str, content: str, position: str = "end") -> None:
        """
        Add content to a specific heading in a note.

        Args:
            filepath: Path to the file (relative to vault root)
            heading: Heading text (exact match, including levels)
            content: Content to add
            position: Where to add the content - "start" or "end" (default: "end")

        Returns:
            None on success

        This is a simplified wrapper around patch_content for the common task
        of adding content to a specific heading.
        """
        operation = "append" if position == "end" else "prepend"
        return self.patch_content(filepath, operation, "heading", heading, content, trim_whitespace=True)

    def set_frontmatter_field(self, filepath: str, field: str, value: str, create_if_missing: bool = True) -> None:
        """
        Set a frontmatter field in a note.

        Args:
            filepath: Path to the file (relative to vault root)
            field: Frontmatter field name
            value: Value to set
            create_if_missing: Whether to create the field if it doesn't exist (default: True)

        Returns:
            None on success

        This is a simplified wrapper around patch_content for the common task
        of setting a frontmatter field value.
        """
        return self.patch_content(
            filepath, "replace", "frontmatter", field, value,
            create_if_missing=create_if_missing
        )

    def add_tag(self, filepath: str, tag: str) -> None:
        """
        Add a tag to a note by updating the frontmatter tags field.

        Args:
            filepath: Path to the file (relative to vault root)
            tag: Tag to add (without the # symbol)

        Returns:
            None on success

        Note:
            Uses the set_frontmatter_field method with create_if_missing=True
        """
        # Remove any # at the beginning if present
        tag = tag.lstrip('#')

        # First, try to get the existing tags
        try:
            content = self.get_file_contents(filepath)
            # Simple check for tags in frontmatter
            tags_line = None
            in_frontmatter = False

            for line in content.split('\n'):
                if line.strip() == '---':
                    in_frontmatter = not in_frontmatter
                    continue

                if in_frontmatter and line.strip().startswith('tags:'):
                    tags_line = line.strip()
                    break

            if tags_line:
                # If tags exist, append the new tag
                # This is a simplified approach - for complex tag arrays, use the JSON Content-Type
                return self.patch_content(
                    filepath, "append", "frontmatter", "tags", f", {tag}",
                    create_if_missing=True
                )
            else:
                # If no tags field exists, create it with the new tag
                return self.patch_content(
                    filepath, "replace", "frontmatter", "tags", f"[{tag}]",
                    create_if_missing=True
                )
        except Exception:
            # If any error occurs, fall back to replacing the tags field
            return self.patch_content(
                filepath, "replace", "frontmatter", "tags", f"[{tag}]",
                create_if_missing=True
            )

    def create_or_update_note(self, filepath: str, content: str, overwrite: bool = False) -> None:
        """
        Create a new note or update an existing one.

        Args:
            filepath: Path to the file (relative to vault root)
            content: Content for the note
            overwrite: Whether to overwrite an existing note (default: False)

        Returns:
            None on success

        This method:
        1. Checks if the file already exists
        2. If it doesn't exist or overwrite is True, creates or replaces the file
        3. If it exists and overwrite is False, appends the content to the end
        """
        filepath = self._normalize_path(filepath)

        try:
            # Try to get the file to see if it exists
            existing_content = self.get_file_contents(filepath)

            # If we get here, the file exists
            if overwrite:
                # Replace entire file content
                url = f"{self.get_base_url()}/vault/{filepath}"
                headers = self._get_headers() | {'Content-Type': 'text/markdown'}

                def call_fn():
                    response = requests.put(
                        url,
                        headers=headers,
                        data=content,
                        verify=self.verify_ssl,
                        timeout=self.timeout
                    )
                    response.raise_for_status()
                    return None

                return self._safe_call(call_fn, operation="create_or_update_note", context={"filepath": filepath, "action": "overwrite"})
            else:
                # Append to existing file
                return self.append_content(filepath, content)

        except Exception:
            # If the file doesn't exist, create it
            url = f"{self.get_base_url()}/vault/{filepath}"
            headers = self._get_headers() | {'Content-Type': 'text/markdown'}

            def call_fn():
                response = requests.put(
                    url,
                    headers=headers,
                    data=content,
                    verify=self.verify_ssl,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return None

            return self._safe_call(call_fn, operation="create_or_update_note", context={"filepath": filepath, "action": "create"})

    def find_headings(self, filepath: str) -> list:
        """
        Extract all headings from a note to help with targeting.

        Args:
            filepath: Path to the file (relative to vault root)

        Returns:
            List of dictionaries with heading info:
            [{'level': 1, 'text': 'Heading 1', 'path': 'Heading 1'}, ...]

        This helper method makes it easier to find valid heading paths for patch_content.
        """
        try:
            content = self.get_file_contents(filepath)

            headings = []
            for line in content.split('\n'):
                # Check if line starts with one or more '#' followed by a space
                if line.strip().startswith('#') and ' ' in line.strip():
                    # Count the heading level by number of # characters
                    level = 0
                    for char in line.strip():
                        if char == '#':
                            level += 1
                        else:
                            break

                    # Extract the heading text
                    text = line.strip().split(' ', 1)[1].strip()

                    # Build a path from the previous headings
                    path = []
                    # Add all parent headings that have lower level numbers
                    for h in reversed(headings):
                        if h['level'] < level:
                            path.insert(0, h['text'])
                            break

                    # Add the current heading
                    path.append(text)

                    # Create the heading entry
                    heading_info = {
                        'level': level,
                        'text': text,
                        'path': '::'.join(path)
                    }

                    headings.append(heading_info)

            return headings
        except Exception as e:
            # If any error occurs, return an empty list
            return []

    def try_patch_content(self, filepath: str, operation: str, target_type: str, target: str,
                        content: str, fallback_operation: str = None) -> tuple:
        """
        Try to patch content and return success status instead of raising an exception.

        Args:
            filepath: Path to the file (relative to vault root)
            operation: Operation to perform (append, prepend, or replace)
            target_type: Type of target (heading, block, or frontmatter)
            target: Target identifier (heading path, block reference, or frontmatter field)
            content: Content to insert
            fallback_operation: Optional fallback operation if the primary fails

        Returns:
            Tuple of (success:bool, error_message:str)

        This method is useful when you want to try a patch operation without
        having to catch exceptions, and optionally try a fallback if it fails.
        """
        try:
            self.patch_content(filepath, operation, target_type, target, content)
            return (True, None)
        except Exception as e:
            if fallback_operation:
                try:
                    self.patch_content(filepath, fallback_operation, target_type, target, content)
                    return (True, None)
                except Exception as fallback_e:
                    return (False, str(fallback_e))
            else:
                return (False, str(e))
