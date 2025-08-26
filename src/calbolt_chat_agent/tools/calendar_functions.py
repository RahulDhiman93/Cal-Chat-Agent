"""Calendar functions for LangChain tool integration."""

from datetime import datetime, timedelta
from typing import Optional
import pytz

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


@tool("book_meeting", args_schema=BookMeetingInput)
def book_meeting(
    date: str,
    time: str,
    title: str,
    attendee_name: str,
    attendee_email: str,
    description: str = ""
) -> str:
    """Book a new meeting with the specified details.
    
    Use this when the user wants to schedule a new meeting or appointment.
    Books a 30-minute meeting using the default event type.
    Requires date, time, title, and attendee information.
    """
    try:
        calcom_client = get_calcom_client()
        
        # Use hardcoded event type ID for 30-minute meetings
        event_type_id = 3161359
        
        # Convert LA timezone input to UTC for API
        meeting_start = convert_la_to_utc(date, time)
        
        # Parse for slot checking (still need datetime object)
        meeting_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        
        # First, check availability using slots API
        available_slots = calcom_client.get_available_slots(
            event_type_id=event_type_id,
            start_date=date,
            end_date=date
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
                    return f"""The requested time {time} is not available on {date}.

**Available times for {date} (PT):**
{', '.join(available_times)}

Please choose one of these available times or select a different date."""
                else:
                    return f"No available slots found for {date}. Please try a different date."
            else:
                return f"No available slots found for {date}. Please try a different date."
        
        # Create booking request with correct Cal.com v2 API format
        booking_request = BookingRequest(
            eventTypeId=event_type_id,
            start=meeting_start,
            attendee={
                "language": "en",
                "name": attendee_name,
                "timeZone": "America/Los_Angeles",
                "email": attendee_email
            },
            location={
                "integration": "cal-video",
                "type": "integration"
            }
        )
        
        # Create the booking
        booking = calcom_client.create_booking(booking_request)
        
        return f"""
Meeting successfully booked! 

**Meeting Details:**
- **Title:** {booking.title}
- **Date & Time:** {meeting_datetime.strftime('%B %d, %Y at %I:%M %p')}
- **Duration:** 30 minutes
- **Attendee:** {attendee_name} ({attendee_email})
- **Booking ID:** {booking.id}
- **Booking UID:** {booking.uid or 'N/A'}
- **Location:** Cal Video (online meeting)

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
        
        bookings = calcom_client.get_bookings()
        
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


@tool("cancel_booking", args_schema=CancelBookingInput)
def cancel_booking(booking_identifier: str, reason: str = "User requested cancellation") -> str:
    """Cancel a scheduled meeting/booking.
    
    Use this when the user wants to cancel an existing appointment.
    Can identify the booking by ID, UID, or by description (title, time, etc.).
    """
    try:
        calcom_client = get_calcom_client()
        
        # First, get all bookings to find the one to cancel
        bookings = calcom_client.get_bookings()
        
        if not bookings:
            return "No bookings found to cancel."
        
        booking_to_cancel = None
        
        # Try to find booking by ID or UID first
        if booking_identifier.isdigit():
            booking_id = int(booking_identifier)
            booking_to_cancel = next(
                (b for b in bookings if b.id == booking_id), 
                None
            )
        else:
            # Try to find by UID
            booking_to_cancel = next(
                (b for b in bookings if b.uid == booking_identifier), 
                None
            )
        
        # If not found by ID/UID, search by description/title/time
        if not booking_to_cancel:
            identifier_lower = booking_identifier.lower()
            
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
            return f"Could not find a booking matching '{booking_identifier}'. Available bookings:\n{booking_list}"
        
        if not booking_to_cancel.uid:
            return f"Cannot cancel booking {booking_to_cancel.id}: booking UID is required for cancellation."
        
        # Cancel the booking using UID
        success = calcom_client.cancel_booking(booking_to_cancel.uid, reason)
        
        if success:
            start_time_la = convert_utc_to_la(booking_to_cancel.startTime)
            return f"""
**Meeting Canceled Successfully**

**Canceled Meeting:**
- **Title:** {booking_to_cancel.title}
- **Date & Time:** {start_time_la.strftime('%B %d, %Y at %I:%M %p')} (PT)
- **Booking ID:** {booking_to_cancel.id}
- **Booking UID:** {booking_to_cancel.uid}
- **Reason:** {reason}

All attendees will be notified of the cancellation.
            """.strip()
        else:
            return f"Failed to cancel booking {booking_to_cancel.uid}. Please try again or contact support."
            
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
        
        # Try to find booking by ID or UID first
        if booking_identifier.isdigit():
            booking_id = int(booking_identifier)
            booking_to_reschedule = next(
                (b for b in bookings if b.id == booking_id), 
                None
            )
        else:
            # Try to find by UID
            booking_to_reschedule = next(
                (b for b in bookings if b.uid == booking_identifier), 
                None
            )
        
        # If not found by ID/UID, search by description
        if not booking_to_reschedule:
            identifier_lower = booking_identifier.lower()
            for booking in bookings:
                if identifier_lower in booking.title.lower():
                    booking_to_reschedule = booking
                    break
        
        if not booking_to_reschedule:
            booking_list = "\n".join([
                f"- {b.title} (ID: {b.id}, UID: {b.uid or 'N/A'})"
                for b in bookings
            ])
            return f"Could not find a booking matching '{booking_identifier}'. Available bookings:\n{booking_list}"
        
        if not booking_to_reschedule.uid:
            return f"Cannot reschedule booking {booking_to_reschedule.id}: booking UID is required for rescheduling."
        
        # Convert new LA timezone input to UTC for API
        new_start_utc = convert_la_to_utc(new_date, new_time)
        
        # Parse for slot checking and display (still need datetime object)
        new_datetime = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")
        
        # Check availability for the new time slot
        event_type_id = 3161359  # Use the same event type ID
        available_slots = calcom_client.get_available_slots(
            event_type_id=event_type_id,
            start_date=new_date,
            end_date=new_date
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
                    return f"""The requested new time {new_time} is not available on {new_date}.

**Available times for {new_date} (PT):**
{', '.join(available_times)}

Please choose one of these available times or select a different date for rescheduling."""
                else:
                    return f"No available slots found for {new_date}. Please try a different date for rescheduling."
            else:
                return f"No available slots found for {new_date}. Please try a different date for rescheduling."
        
        # Get original timing for comparison (convert to LA timezone for display)
        original_start_la = convert_utc_to_la(booking_to_reschedule.startTime)
        original_end_utc = datetime.fromisoformat(booking_to_reschedule.startTime.replace('Z', '+00:00'))
        end_time_utc = datetime.fromisoformat(booking_to_reschedule.endTime.replace('Z', '+00:00'))
        duration = end_time_utc - original_end_utc
        
        # Reschedule the booking using UID
        updated_booking = calcom_client.reschedule_booking(
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


@tool("get_available_slots", args_schema=GetAvailableSlotsInput)
def get_available_slots(date: str, end_date: str = "") -> str:
    """Get available time slots for scheduling meetings.
    
    Use this when the user wants to check what times are available for booking meetings.
    Shows available slots for a specific date or date range.
    """
    try:
        calcom_client = get_calcom_client()
        
        # Use hardcoded event type ID
        event_type_id = 3161359
        
        # Use same date for end if not provided
        if not end_date or end_date == "":
            end_date = date
        
        # Get available slots from API
        available_slots = calcom_client.get_available_slots(
            event_type_id=event_type_id,
            start_date=date,
            end_date=end_date
        )
        
        if not available_slots:
            if date == end_date:
                return f"No available slots found for {date}. Please try a different date."
            else:
                return f"No available slots found between {date} and {end_date}. Please try different dates."
        
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
        if date == end_date:
            result = f"**Available time slots for {date} (PT):**\n\n"
        else:
            result = f"**Available time slots from {date} to {end_date} (PT):**\n\n"
        
        for slot_date in sorted(slots_by_date.keys()):
            date_obj = datetime.strptime(slot_date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%B %d, %Y')
            times = ', '.join(sorted(slots_by_date[slot_date]))
            result += f"**{formatted_date}:**\n{times}\n\n"
        
        result += "You can book any of these available times by saying something like:\n"
        result += f'"Book a meeting on {date} at [time] with [attendee name] [attendee email]"'
        
        return result.strip()
        
    except Exception as e:
        return f"Error getting available slots: {str(e)}"


def get_calendar_tools():
    """Get all calendar tools."""
    return [
        book_meeting,
        list_bookings,
        cancel_booking,
        reschedule_booking,
        get_available_slots
    ]
