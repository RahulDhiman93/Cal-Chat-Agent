"""LangChain tools for calendar operations using Cal.com API."""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from ..api.calcom_client import CalcomClient, BookingRequest
from ..config.settings import settings


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


class BookMeetingTool(BaseTool):
    """Tool for booking a new meeting."""
    
    name: str = "book_meeting"
    description: str = """
    Book a new meeting with the specified details. 
    Use this when the user wants to schedule a new meeting or appointment.
    Requires date, time, duration, title, and attendee information.
    """
    args_schema: type[BaseModel] = BookMeetingInput
    
    def __init__(self, calcom_client: Optional[CalcomClient] = None):
        super().__init__()
        self.calcom_client = calcom_client or CalcomClient()
    
    def _run(self, **kwargs) -> str:
        """Book a meeting with the provided details."""
        try:
            input_data = BookMeetingInput(**kwargs)
            
            # Parse date and time
            meeting_datetime = datetime.strptime(
                f"{input_data.date} {input_data.time}", 
                "%Y-%m-%d %H:%M"
            )
            
            # Calculate end time
            end_datetime = meeting_datetime + timedelta(minutes=input_data.duration)
            
            # Get available event types
            event_types = self.calcom_client.get_event_types()
            if not event_types:
                return "Error: No event types available. Please set up your Cal.com account first."
            
            # Use the first available event type (or find one matching duration)
            event_type = event_types[0]
            for et in event_types:
                if et.length == input_data.duration:
                    event_type = et
                    break
            
            # Check availability
            date_str = input_data.date
            available_slots = self.calcom_client.get_available_slots(
                event_type.id, 
                date_str, 
                date_str
            )
            
            # Check if the requested time is available
            requested_time_iso = meeting_datetime.isoformat()
            slot_available = any(
                slot.time.startswith(meeting_datetime.strftime("%Y-%m-%dT%H:%M"))
                for slot in available_slots
            )
            
            if not slot_available and available_slots:
                available_times = [
                    datetime.fromisoformat(slot.time.replace('Z', '')).strftime("%H:%M")
                    for slot in available_slots[:3]  # Show first 3 available slots
                ]
                return f"The requested time {input_data.time} is not available on {input_data.date}. Available times: {', '.join(available_times)}"
            
            # Create booking request
            booking_request = BookingRequest(
                eventTypeId=event_type.id,
                start=meeting_datetime.isoformat(),
                end=end_datetime.isoformat(),
                attendee={
                    "email": input_data.attendee_email,
                    "name": input_data.attendee_name
                },
                title=input_data.title,
                description=input_data.description
            )
            
            # Create the booking
            booking = self.calcom_client.create_booking(booking_request)
            
            return f"""
Meeting successfully booked! 

**Meeting Details:**
- **Title:** {booking.title}
- **Date & Time:** {meeting_datetime.strftime('%B %d, %Y at %I:%M %p')}
- **Duration:** {input_data.duration} minutes
- **Attendee:** {input_data.attendee_name} ({input_data.attendee_email})
- **Booking ID:** {booking.id}

The meeting has been confirmed and calendar invites will be sent to all attendees.
            """.strip()
            
        except Exception as e:
            return f"Error booking meeting: {str(e)}"


class ListBookingsTool(BaseTool):
    """Tool for listing scheduled bookings."""
    
    name: str = "list_bookings"
    description: str = """
    List all scheduled meetings/bookings for the user.
    Use this when the user wants to see their upcoming appointments or scheduled events.
    """
    args_schema: type[BaseModel] = ListBookingsInput
    
    def __init__(self, calcom_client: Optional[CalcomClient] = None):
        super().__init__()
        self.calcom_client = calcom_client or CalcomClient()
    
    def _run(self, **kwargs) -> str:
        """List all bookings for the user."""
        try:
            input_data = ListBookingsInput(**kwargs)
            user_email = input_data.user_email or settings.user_email
            
            bookings = self.calcom_client.get_bookings(user_email)
            
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


class CancelBookingTool(BaseTool):
    """Tool for canceling a scheduled booking."""
    
    name: str = "cancel_booking"
    description: str = """
    Cancel a scheduled meeting/booking.
    Use this when the user wants to cancel an existing appointment.
    Can identify the booking by ID or by description (title, time, etc.).
    """
    args_schema: type[BaseModel] = CancelBookingInput
    
    def __init__(self, calcom_client: Optional[CalcomClient] = None):
        super().__init__()
        self.calcom_client = calcom_client or CalcomClient()
    
    def _run(self, **kwargs) -> str:
        """Cancel a booking."""
        try:
            input_data = CancelBookingInput(**kwargs)
            
            # First, get all bookings to find the one to cancel
            bookings = self.calcom_client.get_bookings()
            
            if not bookings:
                return "No bookings found to cancel."
            
            booking_to_cancel = None
            
            # Try to find booking by ID first
            if input_data.booking_identifier.isdigit():
                booking_id = int(input_data.booking_identifier)
                booking_to_cancel = next(
                    (b for b in bookings if b.id == booking_id), 
                    None
                )
            
            # If not found by ID, search by description/title/time
            if not booking_to_cancel:
                identifier_lower = input_data.booking_identifier.lower()
                
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
                return f"Could not find a booking matching '{input_data.booking_identifier}'. Available bookings:\n{booking_list}"
            
            # Cancel the booking
            success = self.calcom_client.cancel_booking(booking_to_cancel.id, input_data.reason)
            
            if success:
                start_time = datetime.fromisoformat(booking_to_cancel.startTime.replace('Z', ''))
                return f"""
**Meeting Canceled Successfully**

**Canceled Meeting:**
- **Title:** {booking_to_cancel.title}
- **Date & Time:** {start_time.strftime('%B %d, %Y at %I:%M %p')}
- **Booking ID:** {booking_to_cancel.id}
- **Reason:** {input_data.reason}

All attendees will be notified of the cancellation.
                """.strip()
            else:
                return f"Failed to cancel booking {booking_to_cancel.id}. Please try again or contact support."
                
        except Exception as e:
            return f"Error canceling booking: {str(e)}"


class RescheduleBookingTool(BaseTool):
    """Tool for rescheduling a booking to a new time."""
    
    name: str = "reschedule_booking"
    description: str = """
    Reschedule an existing meeting to a new date and time.
    Use this when the user wants to change the time of an existing appointment.
    """
    args_schema: type[BaseModel] = RescheduleBookingInput
    
    def __init__(self, calcom_client: Optional[CalcomClient] = None):
        super().__init__()
        self.calcom_client = calcom_client or CalcomClient()
    
    def _run(self, **kwargs) -> str:
        """Reschedule a booking to a new time."""
        try:
            input_data = RescheduleBookingInput(**kwargs)
            
            # Find the booking to reschedule (similar logic to cancel)
            bookings = self.calcom_client.get_bookings()
            
            if not bookings:
                return "No bookings found to reschedule."
            
            booking_to_reschedule = None
            
            # Try to find booking by ID first
            if input_data.booking_identifier.isdigit():
                booking_id = int(input_data.booking_identifier)
                booking_to_reschedule = next(
                    (b for b in bookings if b.id == booking_id), 
                    None
                )
            
            # If not found by ID, search by description
            if not booking_to_reschedule:
                identifier_lower = input_data.booking_identifier.lower()
                for booking in bookings:
                    if identifier_lower in booking.title.lower():
                        booking_to_reschedule = booking
                        break
            
            if not booking_to_reschedule:
                booking_list = "\n".join([
                    f"- {b.title} (ID: {b.id})"
                    for b in bookings
                ])
                return f"Could not find a booking matching '{input_data.booking_identifier}'. Available bookings:\n{booking_list}"
            
            # Parse new date and time
            new_datetime = datetime.strptime(
                f"{input_data.new_date} {input_data.new_time}", 
                "%Y-%m-%d %H:%M"
            )
            
            # Get original duration
            original_start = datetime.fromisoformat(booking_to_reschedule.startTime.replace('Z', ''))
            original_end = datetime.fromisoformat(booking_to_reschedule.endTime.replace('Z', ''))
            duration = original_end - original_start
            
            new_end_datetime = new_datetime + duration
            
            # Reschedule the booking
            updated_booking = self.calcom_client.reschedule_booking(
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


def get_calendar_tools(calcom_client: Optional[CalcomClient] = None) -> List[BaseTool]:
    """Get all calendar tools.
    
    Args:
        calcom_client: Optional CalcomClient instance
        
    Returns:
        List of calendar tools
    """
    client = calcom_client or CalcomClient()
    
    return [
        BookMeetingTool(client),
        ListBookingsTool(client),
        CancelBookingTool(client),
        RescheduleBookingTool(client)
    ]
