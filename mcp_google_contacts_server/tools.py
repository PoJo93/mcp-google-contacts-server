"""MCP tools implementation for Google Contacts (FastMCP 2.x)."""
from functools import partial
import sys
import traceback
from typing import Optional

from fastmcp import FastMCP

_log = partial(print, file=sys.stderr)

from mcp_google_contacts_server.google_contacts_service import (
    GoogleContactsService,
    GoogleContactsError,
)
from mcp_google_contacts_server.formatters import (
    format_contact,
    format_contacts_list,
    format_directory_people,
)
from mcp_google_contacts_server.config import config

# Global service instance
contacts_service: Optional[GoogleContactsService] = None


def init_service() -> Optional[GoogleContactsService]:
    """Initialize and return a Google Contacts service instance."""
    global contacts_service

    if contacts_service:
        return contacts_service

    try:
        try:
            contacts_service = GoogleContactsService.from_env()
            _log("Successfully loaded credentials from environment variables.")
            return contacts_service
        except GoogleContactsError:
            pass

        for path in config.credentials_paths:
            if path.exists():
                try:
                    _log(f"Found credentials file at {path}")
                    contacts_service = GoogleContactsService.from_file(path)
                    _log("Successfully loaded credentials from file.")
                    return contacts_service
                except GoogleContactsError as e:
                    _log(f"Error with credentials at {path}: {e}")
                    continue

        _log(
            "No valid credentials found. Please provide credentials to use Google Contacts."
        )
        return None

    except Exception as e:
        _log(f"Error initializing Google Contacts service: {str(e)}")
        traceback.print_exc(file=sys.stderr)
        return None


def register_tools(mcp: FastMCP) -> None:
    """Register all Google Contacts tools with the MCP server."""

    @mcp.tool
    async def list_contacts(
        name_filter: Optional[str] = None, max_results: int = 100
    ) -> str:
        """List all contacts or filter by name.

        Args:
            name_filter: Optional filter to find contacts by name
            max_results: Maximum number of results to return (default: 100)
        """
        service = init_service()
        if not service:
            return "Error: Google Contacts service is not available. Please check your credentials."

        try:
            contacts = service.list_contacts(name_filter, max_results)
            return format_contacts_list(contacts)
        except Exception as e:
            return f"Error: Failed to list contacts - {str(e)}"

    @mcp.tool
    async def get_contact(identifier: str) -> str:
        """Get a contact by resource name or email.

        Args:
            identifier: Resource name (people/*) or email address of the contact
        """
        service = init_service()
        if not service:
            return "Error: Google Contacts service is not available. Please check your credentials."

        try:
            contact = service.get_contact(identifier)
            return format_contact(contact)
        except Exception as e:
            return f"Error: Failed to get contact - {str(e)}"

    @mcp.tool
    async def create_contact(
        given_name: str,
        family_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> str:
        """Create a new contact.

        Args:
            given_name: First name of the contact
            family_name: Last name of the contact
            email: Email address of the contact
            phone: Phone number of the contact
        """
        service = init_service()
        if not service:
            return "Error: Google Contacts service is not available. Please check your credentials."

        try:
            contact = service.create_contact(given_name, family_name, email, phone)
            return f"Contact created successfully!\n\n{format_contact(contact)}"
        except Exception as e:
            return f"Error: Failed to create contact - {str(e)}"

    @mcp.tool
    async def update_contact(
        resource_name: str,
        given_name: Optional[str] = None,
        family_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> str:
        """Update an existing contact.

        Args:
            resource_name: Contact resource name (people/*)
            given_name: Updated first name
            family_name: Updated last name
            email: Updated email address
            phone: Updated phone number
        """
        service = init_service()
        if not service:
            return "Error: Google Contacts service is not available. Please check your credentials."

        try:
            contact = service.update_contact(
                resource_name, given_name, family_name, email, phone
            )
            return f"Contact updated successfully!\n\n{format_contact(contact)}"
        except Exception as e:
            return f"Error: Failed to update contact - {str(e)}"

    @mcp.tool
    async def delete_contact(resource_name: str) -> str:
        """Delete a contact by resource name.

        Args:
            resource_name: Contact resource name (people/*) to delete
        """
        service = init_service()
        if not service:
            return "Error: Google Contacts service is not available. Please check your credentials."

        try:
            result = service.delete_contact(resource_name)
            if result.get("success"):
                return f"Contact {resource_name} deleted successfully."
            return f"Failed to delete contact: {result.get('message', 'Unknown error')}"
        except Exception as e:
            return f"Error: Failed to delete contact - {str(e)}"

    @mcp.tool
    async def search_contacts(query: str, max_results: int = 10) -> str:
        """Search contacts by name, email, or phone number.

        Args:
            query: Search term to find in contacts
            max_results: Maximum number of results to return (default: 10)
        """
        service = init_service()
        if not service:
            return "Error: Google Contacts service is not available. Please check your credentials."

        try:
            all_contacts = service.list_contacts(
                max_results=max(100, max_results * 2)
            )

            q = query.lower()
            matches = []
            for contact in all_contacts:
                if (
                    q in contact.get("displayName", "").lower()
                    or q in contact.get("givenName", "").lower()
                    or q in contact.get("familyName", "").lower()
                    or q in str(contact.get("email", "")).lower()
                    or q in str(contact.get("phone", "")).lower()
                ):
                    matches.append(contact)

                if len(matches) >= max_results:
                    break

            if not matches:
                return f"No contacts found matching '{query}'."

            return f"Search results for '{query}':\n\n{format_contacts_list(matches)}"
        except Exception as e:
            return f"Error: Failed to search contacts - {str(e)}"

    @mcp.tool
    async def list_workspace_users(
        query: Optional[str] = None, max_results: int = 50
    ) -> str:
        """List Google Workspace users in your organization's directory.

        Args:
            query: Optional search term to find specific users (name, email, etc.)
            max_results: Maximum number of results to return (default: 50)
        """
        service = init_service()
        if not service:
            return "Error: Google Contacts service is not available. Please check your credentials."

        try:
            workspace_users = service.list_directory_people(
                query=query, max_results=max_results
            )
            return format_directory_people(workspace_users, query)
        except Exception as e:
            return f"Error: Failed to list Google Workspace users - {str(e)}"

    @mcp.tool
    async def search_directory(query: str, max_results: int = 20) -> str:
        """Search for people specifically in the Google Workspace directory.

        Args:
            query: Search term to find specific directory members
            max_results: Maximum number of results to return (default: 20)
        """
        service = init_service()
        if not service:
            return "Error: Google Contacts service is not available. Please check your credentials."

        try:
            results = service.search_directory(query, max_results)
            return format_directory_people(results, query)
        except Exception as e:
            return f"Error: Failed to search directory - {str(e)}"

    @mcp.tool
    async def get_other_contacts(max_results: int = 50) -> str:
        """Retrieve contacts from the 'Other contacts' section.

        Args:
            max_results: Maximum number of results to return (default: 50)
        """
        service = init_service()
        if not service:
            return "Error: Google Contacts service is not available. Please check your credentials."

        try:
            other_contacts = service.get_other_contacts(max_results)

            if not other_contacts:
                return "No 'Other contacts' found in your Google account."

            with_email = sum(1 for c in other_contacts if c.get("email"))
            formatted_list = format_contacts_list(other_contacts)
            return (
                "Other Contacts (people you've interacted with but haven't added):\n\n"
                f"{formatted_list}\n\n{with_email} of these contacts have email addresses."
            )
        except Exception as e:
            return f"Error: Failed to retrieve other contacts - {str(e)}"

    @mcp.tool
    async def update_contact_photo(
        resource_name: str,
        photo_url: str,
        target_size: Optional[int] = None,
    ) -> str:
        """Set a contact's profile photo from a public image URL.

        The server downloads the image, center-crops it to a square, resizes
        it to ``target_size`` (default: 720 px, Google's recommended profile
        photo resolution) and JPEG-encodes it before calling
        ``people.updateContactPhoto``. Upload is capped at 5 MB; quality is
        lowered automatically if the JPEG is still too big.

        Args:
            resource_name: Contact resource name (people/*)
            photo_url: HTTP(S) URL pointing at an image (JPEG/PNG/etc.)
            target_size: Optional square edge length in pixels (min 250).
                Defaults to 720 or $MCP_CONTACT_PHOTO_SIZE.
        """
        service = init_service()
        if not service:
            return "Error: Google Contacts service is not available. Please check your credentials."

        try:
            result = service.update_contact_photo_from_url(
                resource_name, photo_url, target_size=target_size
            )
        except Exception as e:
            return f"Error: Failed to update contact photo - {e}"

        src_w, src_h = result["sourceDimensions"]
        parts = [
            f"Photo updated successfully for {result['resourceName']}",
            f"Source: {result['sourceUrl']}",
            f"Source: {src_w}x{src_h} px, {result['sourceBytes']} bytes "
            f"({result['sourceContentType'] or 'unknown'})",
            f"Uploaded: {result['uploadedSize']} {result['uploadedContentType']}, "
            f"{result['uploadedBytes']} bytes",
        ]
        if result.get("photoUrl"):
            parts.append(f"Google photo URL: {result['photoUrl']}")
        contact = result.get("contact")
        if contact:
            parts.append("")
            parts.append(format_contact(contact))
        return "\n".join(parts)
