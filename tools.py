import base64
import os

import httpx
from livekit.agents import function_tool, RunContext, ToolError


@function_tool()
async def lookup_ticket(context: RunContext, ticket_number: str) -> dict:
    """Look up a support ticket in ConnectWise by its six-digit ticket number and return its details.

    Args:
        ticket_number: The caller's six-digit ConnectWise ticket number, digits only (e.g. "923376").
    """
    await context.session.say("Sure — let me pull up that ticket for you. One moment.")
    context.disallow_interruptions()

    auth = base64.b64encode(
        f'{os.environ["CW_COMPANY_ID"]}+{os.environ["CW_PUBLIC_KEY"]}:{os.environ["CW_PRIVATE_KEY"]}'.encode()
    ).decode()
    headers = {
        "Authorization" : f"Basic {auth}",
        "clientId"      : os.environ["CW_CLIENT_ID"],
        "Accept"        : "application/json",
    }
    url = f'{os.environ["CW_API_BASE"]}/service/tickets/{ticket_number}'

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers = headers, timeout = 10)
    except Exception:
        raise ToolError("I'm having trouble reaching our ticket system right now.")

    if response.status_code == 404:
        raise ToolError(f"I couldn't find a ticket with the number {ticket_number}.")
    if response.status_code != 200:
        raise ToolError("Something went wrong while looking up that ticket.")

    ticket = response.json()
    return {
        "ticket_number" : ticket.get("id"),
        "summary"       : ticket.get("summary"),
        "status"        : (ticket.get("status") or {}).get("name"),
        "company"       : (ticket.get("company") or {}).get("name"),
        "contact_name"  : ticket.get("contactName"),
    }
