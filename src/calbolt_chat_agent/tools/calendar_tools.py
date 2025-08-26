"""LangChain tools for calendar operations using Cal.com API."""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pytz
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from ..api.calcom_client import CalcomClient, BookingRequest
from ..config.settings import settings


def convert_utc_to_la(utc_time_str: str) -> datetime:
    """Convert UTC time string to America/Los_Angeles timezone."""
    try:
        # Parse UTC time (handle both formats: with and without 'Z')
        if utc_time_str.endswith('Z'):
            utc_dt = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        else:
            utc_dt = datetime.fromisoformat(utc_time_str + '+00:00')
        
        # Convert to LA timezone
        la_tz = pytz.timezone('America/Los_Angeles')
        la_dt = utc_dt.astimezone(la_tz)
        return la_dt
    except:
        # Fallback: treat as UTC and convert
        utc_dt = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        la_tz = pytz.timezone('America/Los_Angeles')
        return utc_dt.astimezone(la_tz)


def convert_la_to_utc(date_str: str, time_str: str) -> str:
    """Convert LA timezone date/time to UTC ISO format for API calls.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        time_str: Time in HH:MM format (24-hour)
        
    Returns:
        UTC time in ISO format (e.g., "2025-08-26T23:00:00Z")
    """
    # Parse as LA timezone datetime
    la_tz = pytz.timezone('America/Los_Angeles')
    naive_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    la_datetime = la_tz.localize(naive_datetime)
    
    # Convert to UTC
    utc_datetime = la_datetime.astimezone(pytz.UTC)
    
    # Return in Cal.com API format
    return utc_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")


class BookMeetingInput(BaseModel):
    """Input schema for booking a meeting."""
    date: str = Field(description="Date for the meeting in YYYY-MM-DD format")
    time: str = Field(description="Time for the meeting in HH:MM format (24-hour)")
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


class GetAvailableSlotsInput(BaseModel):
    """Input schema for getting available slots."""
    date: str = Field(description="Date to check availability in YYYY-MM-DD format")
    end_date: str = Field(description="End date for range check in YYYY-MM-DD format (optional, defaults to same as start date)", default="")


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
            
            # Use hardcoded event type ID for 30-minute meetings
            event_type_id = 3161359
            
            # Convert LA timezone input to UTC for API
            meeting_start = convert_la_to_utc(input_data.date, input_data.time)
            
            # Parse for slot checking (still need datetime object)
            meeting_datetime = datetime.strptime(
                f"{input_data.date} {input_data.time}", 
                "%Y-%m-%d %H:%M"
            )
            
            # First, check availability using slots API
            available_slots = self.calcom_client.get_available_slots(
                event_type_id=event_type_id,
                start_date=input_data.date,
                end_date=input_data.date
            )
            
            # Check if the requested time is available
            requested_time_matches = [
                slot for slot in available_slots 
                if slot.time.startswith(meeting_datetime.strftime("%Y-%m-%dT%H:%M"))
            ]
            
            if not requested_time_matches:
                if available_slots:
                    # Show available times for the same date (convert to LA timezone)
                    available_times = []
                    for slot in available_slots[:5]:  # Show first 5 available slots
                        try:
                            slot_time_la = convert_utc_to_la(slot.time)
                            available_times.append(slot_time_la.strftime("%I:%M %p"))
                        except:
                            continue
                    
                    if available_times:
                        return f"""The requested time {input_data.time} is not available on {input_data.date}.

**Available times for {input_data.date} (PT):**
{', '.join(available_times)}

Please choose one of these available times or select a different date."""
                    else:
                        return f"No available slots found for {input_data.date}. Please try a different date."
                else:
                    return f"No available slots found for {input_data.date}. Please try a different date."
            
            # Create booking request with correct Cal.com v2 API format
            booking_request = BookingRequest(
                eventTypeId=event_type_id,
                start=meeting_start,
                attendee={
                    "language": "en",
                    "name": input_data.attendee_name,
                    "timeZone": "America/Los_Angeles",
                    "email": input_data.attendee_email
                },
                location={
                    "integration": "cal-video",
                    "type": "integration"
                }
            )
            
            # Create the booking
            booking = self.calcom_client.create_booking(booking_request)
            
            return f"""
Meeting successfully booked! 

**Meeting Details:**
- **Title:** {booking.title}
- **Date & Time:** {meeting_datetime.strftime('%B %d, %Y at %I:%M %p')}
- **Duration:** 30 minutes
- **Attendee:** {input_data.attendee_name} ({input_data.attendee_email})
- **Booking ID:** {booking.id}
- **Booking UID:** {booking.uid or 'N/A'}
- **Location:** Cal Video (online meeting)

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
            
            bookings = self.calcom_client.get_bookings()
            
            if not bookings:
                return "No scheduled meetings found."
            
            # Sort bookings by start time
            bookings.sort(key=lambda b: b.startTime)
            
            result = "**Your Scheduled Meetings:**\n\n"
            
            for booking in bookings:
                try:
                    start_time_la = convert_utc_to_la(booking.startTime)
                    end_time_la = convert_utc_to_la(booking.endTime)
                    
                    attendees = ", ".join([
                        f"{att.get('name', 'Unknown')} ({att.get('email', 'No email')})"
                        for att in booking.attendees
                    ])
                    
                    result += f"""
**{booking.title}** (ID: {booking.id}, UID: {booking.uid or 'N/A'})
- **Date & Time:** {start_time_la.strftime('%B %d, %Y at %I:%M %p')} - {end_time_la.strftime('%I:%M %p')} (PT)
- **Status:** {booking.status.title()}
- **Attendees:** {attendees}
- **Description:** {booking.description or 'No description'}

                    """.strip() + "\n\n"
                    
                except Exception as e:
                    result += f"**{booking.title}** (ID: {booking.id}, UID: {booking.uid or 'N/A'}) - Error parsing time details\n\n"
            
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
            
            # Try to find booking by ID or UID first
            if input_data.booking_identifier.isdigit():
                booking_id = int(input_data.booking_identifier)
                booking_to_cancel = next(
                    (b for b in bookings if b.id == booking_id), 
                    None
                )
            else:
                # Try to find by UID
                booking_to_cancel = next(
                    (b for b in bookings if b.uid == input_data.booking_identifier), 
                    None
                )
            
            # If not found by ID/UID, search by description/title/time
            if not booking_to_cancel:
                identifier_lower = input_data.booking_identifier.lower()
                
                for booking in bookings:
                    # Check title
                    if identifier_lower in booking.title.lower():
                        booking_to_cancel = booking
                        break
                    
                    # Check time (e.g., "3pm today", "tomorrow at 2")
                    try:
                        start_time_la = convert_utc_to_la(booking.startTime)
                        time_str = start_time_la.strftime('%I%p').lower()  # e.g., "3pm"
                        date_str = start_time_la.strftime('%Y-%m-%d')
                        
                        if time_str in identifier_lower or date_str in identifier_lower:
                            booking_to_cancel = booking
                            break
                            
                        # Check for "today" or "tomorrow" (in LA timezone)
                        la_tz = pytz.timezone('America/Los_Angeles')
                        today_la = datetime.now(la_tz).date()
                        if "today" in identifier_lower and start_time_la.date() == today_la:
                            booking_to_cancel = booking
                            break
                        elif "tomorrow" in identifier_lower and start_time_la.date() == today_la + timedelta(days=1):
                            booking_to_cancel = booking
                            break
                            
                    except Exception:
                        continue
            
            if not booking_to_cancel:
                # List available bookings to help user
                booking_list = "\n".join([
                    f"- {b.title} (ID: {b.id}, UID: {b.uid or 'N/A'}) - {convert_utc_to_la(b.startTime).strftime('%B %d at %I:%M %p')} (PT)"
                    for b in bookings
                ])
                return f"Could not find a booking matching '{input_data.booking_identifier}'. Available bookings:\n{booking_list}"
            
            if not booking_to_cancel.uid:
                return f"Cannot cancel booking {booking_to_cancel.id}: booking UID is required for cancellation."
            
            # Cancel the booking using UID
            success = self.calcom_client.cancel_booking(booking_to_cancel.uid, input_data.reason)
            
            if success:
                start_time_la = convert_utc_to_la(booking_to_cancel.startTime)
                return f"""
**Meeting Canceled Successfully**

**Canceled Meeting:**
- **Title:** {booking_to_cancel.title}
- **Date & Time:** {start_time_la.strftime('%B %d, %Y at %I:%M %p')} (PT)
- **Booking ID:** {booking_to_cancel.id}
- **Booking UID:** {booking_to_cancel.uid}
- **Reason:** {input_data.reason}

All attendees will be notified of the cancellation.
                """.strip()
            else:
                return f"Failed to cancel booking {booking_to_cancel.uid}. Please try again or contact support."
                
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
            
            # Try to find booking by ID or UID first
            if input_data.booking_identifier.isdigit():
                booking_id = int(input_data.booking_identifier)
                booking_to_reschedule = next(
                    (b for b in bookings if b.id == booking_id), 
                    None
                )
            else:
                # Try to find by UID
                booking_to_reschedule = next(
                    (b for b in bookings if b.uid == input_data.booking_identifier), 
                    None
                )
            
            # If not found by ID/UID, search by description
            if not booking_to_reschedule:
                identifier_lower = input_data.booking_identifier.lower()
                for booking in bookings:
                    if identifier_lower in booking.title.lower():
                        booking_to_reschedule = booking
                        break
            
            if not booking_to_reschedule:
                booking_list = "\n".join([
                    f"- {b.title} (ID: {b.id}, UID: {b.uid or 'N/A'})"
                    for b in bookings
                ])
                return f"Could not find a booking matching '{input_data.booking_identifier}'. Available bookings:\n{booking_list}"
            
            if not booking_to_reschedule.uid:
                return f"Cannot reschedule booking {booking_to_reschedule.id}: booking UID is required for rescheduling."
            
            # Convert new LA timezone input to UTC for API
            new_start_utc = convert_la_to_utc(input_data.new_date, input_data.new_time)
            
            # Parse for slot checking and display (still need datetime object)
            new_datetime = datetime.strptime(
                f"{input_data.new_date} {input_data.new_time}", 
                "%Y-%m-%d %H:%M"
            )
            
            # Check availability for the new time slot
            event_type_id = 3161359  # Use the same event type ID
            available_slots = self.calcom_client.get_available_slots(
                event_type_id=event_type_id,
                start_date=input_data.new_date,
                end_date=input_data.new_date
            )
            
            # Check if the new requested time is available
            new_time_matches = [
                slot for slot in available_slots 
                if slot.time.startswith(new_datetime.strftime("%Y-%m-%dT%H:%M"))
            ]
            
            if not new_time_matches:
                if available_slots:
                    # Show available times for the new date (convert to LA timezone)
                    available_times = []
                    for slot in available_slots[:5]:  # Show first 5 available slots
                        try:
                            slot_time_la = convert_utc_to_la(slot.time)
                            available_times.append(slot_time_la.strftime("%I:%M %p"))
                        except:
                            continue
                    
                    if available_times:
                        return f"""The requested new time {input_data.new_time} is not available on {input_data.new_date}.

**Available times for {input_data.new_date} (PT):**
{', '.join(available_times)}

Please choose one of these available times or select a different date for rescheduling."""
                    else:
                        return f"No available slots found for {input_data.new_date}. Please try a different date for rescheduling."
                else:
                    return f"No available slots found for {input_data.new_date}. Please try a different date for rescheduling."
            
            # Get original timing for comparison (convert to LA timezone for display)
            original_start_la = convert_utc_to_la(booking_to_reschedule.startTime)
            original_end_utc = datetime.fromisoformat(booking_to_reschedule.startTime.replace('Z', '+00:00'))
            end_time_utc = datetime.fromisoformat(booking_to_reschedule.endTime.replace('Z', '+00:00'))
            duration = end_time_utc - original_end_utc
            
            # Reschedule the booking using UID
            updated_booking = self.calcom_client.reschedule_booking(
                booking_to_reschedule.uid,
                new_start_utc
            )
            
            if updated_booking:
                # Convert new time to LA timezone for display
                new_datetime_la = pytz.timezone('America/Los_Angeles').localize(new_datetime)
                return f"""
**Meeting Rescheduled Successfully**

**Original Time:** {original_start_la.strftime('%B %d, %Y at %I:%M %p')} (PT)
**New Time:** {new_datetime_la.strftime('%B %d, %Y at %I:%M %p')} (PT)

**Meeting Details:**
- **Title:** {updated_booking.title}
- **Duration:** {int(duration.total_seconds() / 60)} minutes
- **Booking ID:** {updated_booking.id}
- **Booking UID:** {updated_booking.uid}

All attendees will be notified of the schedule change.
                """.strip()
            else:
                return f"Failed to reschedule booking {booking_to_reschedule.uid}. Please try again or contact support."
            
        except Exception as e:
            return f"Error rescheduling booking: {str(e)}"


class GetAvailableSlotsTool(BaseTool):
    """Tool for getting available time slots."""
    
    name: str = "get_available_slots"
    description: str = """
    Get available time slots for scheduling meetings.
    Use this when the user wants to check what times are available for booking meetings.
    Shows available slots for a specific date or date range.
    """
    args_schema: type[BaseModel] = GetAvailableSlotsInput
    
    def __init__(self, calcom_client: Optional[CalcomClient] = None):
        super().__init__()
        self.calcom_client = calcom_client or CalcomClient()
    
    def _run(self, **kwargs) -> str:
        """Get available slots for the specified date(s)."""
        try:
            input_data = GetAvailableSlotsInput(**kwargs)
            
            # Use hardcoded event type ID
            event_type_id = 3161359
            
            # Use same date for end if not provided
            end_date = input_data.end_date if input_data.end_date else input_data.date
            
            # Get available slots from API
            available_slots = self.calcom_client.get_available_slots(
                event_type_id=event_type_id,
                start_date=input_data.date,
                end_date=end_date
            )
            
            if not available_slots:
                if input_data.date == end_date:
                    return f"No available slots found for {input_data.date}. Please try a different date."
                else:
                    return f"No available slots found between {input_data.date} and {end_date}. Please try different dates."
            
            # Group slots by date and convert to LA timezone
            slots_by_date = {}
            for slot in available_slots:
                try:
                    slot_time_la = convert_utc_to_la(slot.time)
                    slot_date = slot_time_la.strftime('%Y-%m-%d')
                    slot_time_formatted = slot_time_la.strftime('%I:%M %p')
                    
                    if slot_date not in slots_by_date:
                        slots_by_date[slot_date] = []
                    slots_by_date[slot_date].append(slot_time_formatted)
                except:
                    continue
            
            if not slots_by_date:
                return f"No valid time slots found. Please try a different date."
            
            # Format the response
            if input_data.date == end_date:
                result = f"**Available time slots for {input_data.date} (PT):**\n\n"
            else:
                result = f"**Available time slots from {input_data.date} to {end_date} (PT):**\n\n"
            
            for slot_date in sorted(slots_by_date.keys()):
                date_obj = datetime.strptime(slot_date, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%B %d, %Y')
                times = ', '.join(sorted(slots_by_date[slot_date]))
                result += f"**{formatted_date}:**\n{times}\n\n"
            
            result += "You can book any of these available times by saying something like:\n"
            result += f'"Book a meeting on {input_data.date} at [time] with [attendee name] [attendee email]"'
            
            return result.strip()
            
        except Exception as e:
            return f"Error getting available slots: {str(e)}"


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
        RescheduleBookingTool(client),
        GetAvailableSlotsTool(client)
    ]
