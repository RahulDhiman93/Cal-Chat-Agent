"""Calendar functions for LangChain tool integration."""

from datetime import datetime, timedelta
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ..api.calcom_client import CalcomClient, BookingRequest
from ..config.settings import settings


# Global client instance
_calcom_client: Optional[CalcomClient] = None


def get_calcom_client() -> CalcomClient:
    """Get or create the global CalcomClient instance."""
    global _calcom_client
    if _calcom_client is None:
        _calcom_client = CalcomClient()
    return _calcom_client


class BookMeetingInput(BaseModel):
    """Input schema for booking a meeting."""
    date: str = Field(description="Date for the meeting in YYYY-MM-DD format")
    time: str = Field(description="Time for the meeting in HH:MM format (24-hour)")
    duration: int = Field(description="Duration of the meeting in minutes", default=30)
    title: str = Field(description="Title/subject of the meeting")
    description: str = Field(description="Description or reason for the meeting", default="")
    attendee_name: str = Field(description="Name of the attendee")
    attendee_email: str = Field(description="Email of the attendee")


class ListBookingsInput(BaseModel):
    """Input schema for listing bookings."""
    user_email: Optional[str] = Field(description="Email of the user to get bookings for", default=None)


class CancelBookingInput(BaseModel):
    """Input schema for canceling a booking."""
    booking_identifier: str = Field(description="Booking ID or description to identify which booking to cancel")
    reason: Optional[str] = Field(description="Reason for cancellation", default="User requested cancellation")


class RescheduleBookingInput(BaseModel):
    """Input schema for rescheduling a booking."""
    booking_identifier: str = Field(description="Booking ID or description to identify which booking to reschedule")
    new_date: str = Field(description="New date for the meeting in YYYY-MM-DD format")
    new_time: str = Field(description="New time for the meeting in HH:MM format (24-hour)")


@tool("book_meeting", args_schema=BookMeetingInput)
def book_meeting(
    date: str,
    time: str,
    title: str,
    attendee_name: str,
    attendee_email: str,
    duration: int = 30,
    description: str = ""
) -> str:
    """Book a new meeting with the specified details.
    
    Use this when the user wants to schedule a new meeting or appointment.
    Requires date, time, duration, title, and attendee information.
    """
    try:
        calcom_client = get_calcom_client()
        
        # Parse date and time
        meeting_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        
        # Calculate end time
        end_datetime = meeting_datetime + timedelta(minutes=duration)
        
        # Get available event types
        event_types = calcom_client.get_event_types()
        if not event_types:
            return "Error: No event types available. Please set up your Cal.com account first."
        
        # Use the first available event type (or find one matching duration)
        event_type = event_types[0]
        for et in event_types:
            if et.length == duration:
                event_type = et
                break
        
        # Check availability
        available_slots = calcom_client.get_available_slots(
            event_type.id, 
            date, 
            date
        )
        
        # Check if the requested time is available
        slot_available = any(
            slot.time.startswith(meeting_datetime.strftime("%Y-%m-%dT%H:%M"))
            for slot in available_slots
        )
        
        if not slot_available and available_slots:
            available_times = [
                datetime.fromisoformat(slot.time.replace('Z', '')).strftime("%H:%M")
                for slot in available_slots[:3]  # Show first 3 available slots
            ]
            return f"The requested time {time} is not available on {date}. Available times: {', '.join(available_times)}"
        
        # Create booking request
        booking_request = BookingRequest(
            eventTypeId=event_type.id,
            start=meeting_datetime.isoformat(),
            end=end_datetime.isoformat(),
            attendee={
                "email": attendee_email,
                "name": attendee_name
            },
            title=title,
            description=description
        )
        
        # Create the booking
        booking = calcom_client.create_booking(booking_request)
        
        return f"""
Meeting successfully booked! 

**Meeting Details:**
- **Title:** {booking.title}
- **Date & Time:** {meeting_datetime.strftime('%B %d, %Y at %I:%M %p')}
- **Duration:** {duration} minutes
- **Attendee:** {attendee_name} ({attendee_email})
- **Booking ID:** {booking.id}

The meeting has been confirmed and calendar invites will be sent to all attendees.
        """.strip()
        
    except Exception as e:
        return f"Error booking meeting: {str(e)}"


@tool("list_bookings", args_schema=ListBookingsInput)
def list_bookings(user_email: Optional[str] = None) -> str:
    """List all scheduled meetings/bookings for the user.
    
    Use this when the user wants to see their upcoming appointments or scheduled events.
    """
    try:
        calcom_client = get_calcom_client()
        email = user_email or settings.user_email
        
        bookings = calcom_client.get_bookings(email)
        
        if not bookings:
            return "No scheduled meetings found."
        
        # Sort bookings by start time
        bookings.sort(key=lambda b: b.startTime)
        
        result = "**Your Scheduled Meetings:**\n\n"
        
        for booking in bookings:
            try:
                start_time = datetime.fromisoformat(booking.startTime.replace('Z', ''))
                end_time = datetime.fromisoformat(booking.endTime.replace('Z', ''))
                
                attendees = ", ".join([
                    f"{att.get('name', 'Unknown')} ({att.get('email', 'No email')})"
                    for att in booking.attendees
                ])
                
                result += f"""
**{booking.title}** (ID: {booking.id})
- **Date & Time:** {start_time.strftime('%B %d, %Y at %I:%M %p')} - {end_time.strftime('%I:%M %p')}
- **Status:** {booking.status.title()}
- **Attendees:** {attendees}
- **Description:** {booking.description or 'No description'}

                """.strip() + "\n\n"
                
            except Exception as e:
                result += f"**{booking.title}** (ID: {booking.id}) - Error parsing time details\n\n"
        
        return result.strip()
        
    except Exception as e:
        return f"Error retrieving bookings: {str(e)}"


@tool("cancel_booking", args_schema=CancelBookingInput)
def cancel_booking(booking_identifier: str, reason: str = "User requested cancellation") -> str:
    """Cancel a scheduled meeting/booking.
    
    Use this when the user wants to cancel an existing appointment.
    Can identify the booking by ID or by description (title, time, etc.).
    """
    try:
        calcom_client = get_calcom_client()
        
        # First, get all bookings to find the one to cancel
        bookings = calcom_client.get_bookings()
        
        if not bookings:
            return "No bookings found to cancel."
        
        booking_to_cancel = None
        
        # Try to find booking by ID first
        if booking_identifier.isdigit():
            booking_id = int(booking_identifier)
            booking_to_cancel = next(
                (b for b in bookings if b.id == booking_id), 
                None
            )
        
        # If not found by ID, search by description/title/time
        if not booking_to_cancel:
            identifier_lower = booking_identifier.lower()
            
            for booking in bookings:
                # Check title
                if identifier_lower in booking.title.lower():
                    booking_to_cancel = booking
                    break
                
                # Check time (e.g., "3pm today", "tomorrow at 2")
                try:
                    start_time = datetime.fromisoformat(booking.startTime.replace('Z', ''))
                    time_str = start_time.strftime('%I%p').lower()  # e.g., "3pm"
                    date_str = start_time.strftime('%Y-%m-%d')
                    
                    if time_str in identifier_lower or date_str in identifier_lower:
                        booking_to_cancel = booking
                        break
                        
                    # Check for "today" or "tomorrow"
                    today = datetime.now().date()
                    if "today" in identifier_lower and start_time.date() == today:
                        booking_to_cancel = booking
                        break
                    elif "tomorrow" in identifier_lower and start_time.date() == today + timedelta(days=1):
                        booking_to_cancel = booking
                        break
                        
                except Exception:
                    continue
        
        if not booking_to_cancel:
            # List available bookings to help user
            booking_list = "\n".join([
                f"- {b.title} (ID: {b.id}) - {datetime.fromisoformat(b.startTime.replace('Z', '')).strftime('%B %d at %I:%M %p')}"
                for b in bookings
            ])
            return f"Could not find a booking matching '{booking_identifier}'. Available bookings:\n{booking_list}"
        
        # Cancel the booking
        success = calcom_client.cancel_booking(booking_to_cancel.id, reason)
        
        if success:
            start_time = datetime.fromisoformat(booking_to_cancel.startTime.replace('Z', ''))
            return f"""
**Meeting Canceled Successfully**

**Canceled Meeting:**
- **Title:** {booking_to_cancel.title}
- **Date & Time:** {start_time.strftime('%B %d, %Y at %I:%M %p')}
- **Booking ID:** {booking_to_cancel.id}
- **Reason:** {reason}

All attendees will be notified of the cancellation.
            """.strip()
        else:
            return f"Failed to cancel booking {booking_to_cancel.id}. Please try again or contact support."
            
    except Exception as e:
        return f"Error canceling booking: {str(e)}"


@tool("reschedule_booking", args_schema=RescheduleBookingInput)
def reschedule_booking(booking_identifier: str, new_date: str, new_time: str) -> str:
    """Reschedule an existing meeting to a new date and time.
    
    Use this when the user wants to change the time of an existing appointment.
    """
    try:
        calcom_client = get_calcom_client()
        
        # Find the booking to reschedule (similar logic to cancel)
        bookings = calcom_client.get_bookings()
        
        if not bookings:
            return "No bookings found to reschedule."
        
        booking_to_reschedule = None
        
        # Try to find booking by ID first
        if booking_identifier.isdigit():
            booking_id = int(booking_identifier)
            booking_to_reschedule = next(
                (b for b in bookings if b.id == booking_id), 
                None
            )
        
        # If not found by ID, search by description
        if not booking_to_reschedule:
            identifier_lower = booking_identifier.lower()
            for booking in bookings:
                if identifier_lower in booking.title.lower():
                    booking_to_reschedule = booking
                    break
        
        if not booking_to_reschedule:
            booking_list = "\n".join([
                f"- {b.title} (ID: {b.id})"
                for b in bookings
            ])
            return f"Could not find a booking matching '{booking_identifier}'. Available bookings:\n{booking_list}"
        
        # Parse new date and time
        new_datetime = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")
        
        # Get original duration
        original_start = datetime.fromisoformat(booking_to_reschedule.startTime.replace('Z', ''))
        original_end = datetime.fromisoformat(booking_to_reschedule.endTime.replace('Z', ''))
        duration = original_end - original_start
        
        new_end_datetime = new_datetime + duration
        
        # Reschedule the booking
        updated_booking = calcom_client.reschedule_booking(
            booking_to_reschedule.id,
            new_datetime.isoformat(),
            new_end_datetime.isoformat()
        )
        
        return f"""
**Meeting Rescheduled Successfully**

**Original Time:** {original_start.strftime('%B %d, %Y at %I:%M %p')}
**New Time:** {new_datetime.strftime('%B %d, %Y at %I:%M %p')}

**Meeting Details:**
- **Title:** {updated_booking.title}
- **Duration:** {int(duration.total_seconds() / 60)} minutes
- **Booking ID:** {updated_booking.id}

All attendees will be notified of the schedule change.
        """.strip()
        
    except Exception as e:
        return f"Error rescheduling booking: {str(e)}"


def get_calendar_tools():
    """Get all calendar tools."""
    return [
        book_meeting,
        list_bookings,
        cancel_booking,
        reschedule_booking
    ]
