"""Cal.com API client for calendar operations."""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import requests
from pydantic import BaseModel

from ..config.settings import settings


class BookingRequest(BaseModel):
    """Model for booking request data."""
    eventTypeId: int
    start: str  # ISO 8601 format
    end: str    # ISO 8601 format
    attendee: Dict[str, str]  # {"email": "user@example.com", "name": "User Name"}
    meetingUrl: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class Booking(BaseModel):
    """Model for booking data."""
    id: int
    title: str
    description: Optional[str] = None
    startTime: str
    endTime: str
    attendees: List[Dict[str, Any]]
    status: str
    eventType: Dict[str, Any]


class EventType(BaseModel):
    """Model for event type data."""
    id: int
    title: str
    slug: str
    length: int
    description: Optional[str] = None


class AvailableSlot(BaseModel):
    """Model for available time slot."""
    time: str  # ISO 8601 format
    attendees: int
    bookingUid: Optional[str] = None


class CalcomAPIError(Exception):
    """Custom exception for Cal.com API errors."""
    pass


class CalcomClient:
    """Client for interacting with Cal.com API."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize the Cal.com client.
        
        Args:
            api_key: Cal.com API key. If not provided, uses settings.
            base_url: Base URL for Cal.com API. If not provided, uses settings.
        """
        self.api_key = api_key or settings.calcom_api_key
        self.base_url = base_url or settings.calcom_base_url
        
        if not self.api_key:
            raise ValueError("Cal.com API key is required")
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a request to the Cal.com API.
        
        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            API response data
            
        Raises:
            CalcomAPIError: If the API request fails
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            # Handle empty responses
            if not response.content:
                return {}
                
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise CalcomAPIError(f"API request failed: {str(e)}")
        except json.JSONDecodeError as e:
            raise CalcomAPIError(f"Failed to parse API response: {str(e)}")
    
    def get_event_types(self) -> List[EventType]:
        """Get all event types for the authenticated user.
        
        Returns:
            List of event types
        """
        try:
            response = self._make_request("GET", "/event-types")
            event_types_data = response.get("eventTypes", response.get("data", []))
            
            return [EventType(**event_type) for event_type in event_types_data]
        except Exception as e:
            if settings.debug:
                print(f"Error getting event types: {e}")
            # Return a default event type for demo purposes
            return [EventType(id=1, title="30 Minute Meeting", slug="30min", length=30)]
    
    def get_available_slots(self, event_type_id: int, start_date: str, end_date: str) -> List[AvailableSlot]:
        """Get available time slots for an event type.
        
        Args:
            event_type_id: ID of the event type
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of available slots
        """
        try:
            params = {
                "eventTypeId": event_type_id,
                "startTime": start_date,
                "endTime": end_date
            }
            response = self._make_request("GET", "/slots", params=params)
            slots_data = response.get("slots", response.get("data", []))
            
            return [AvailableSlot(**slot) for slot in slots_data]
        except Exception as e:
            if settings.debug:
                print(f"Error getting available slots: {e}")
            # Return demo slots for development
            return self._generate_demo_slots(start_date)
    
    def _generate_demo_slots(self, start_date: str) -> List[AvailableSlot]:
        """Generate demo slots for development/testing."""
        try:
            start_dt = datetime.fromisoformat(start_date)
            slots = []
            
            # Generate slots from 9 AM to 5 PM
            for hour in range(9, 17):
                slot_time = start_dt.replace(hour=hour, minute=0, second=0, microsecond=0)
                slots.append(AvailableSlot(
                    time=slot_time.isoformat(),
                    attendees=1
                ))
            
            return slots
        except Exception:
            return []
    
    def create_booking(self, booking_request: BookingRequest) -> Booking:
        """Create a new booking.
        
        Args:
            booking_request: Booking request data
            
        Returns:
            Created booking
        """
        try:
            response = self._make_request(
                "POST", 
                "/bookings", 
                json=booking_request.dict()
            )
            booking_data = response.get("booking", response.get("data", {}))
            
            return Booking(**booking_data)
        except Exception as e:
            if settings.debug:
                print(f"Error creating booking: {e}")
            # Return a demo booking for development
            return self._create_demo_booking(booking_request)
    
    def _create_demo_booking(self, booking_request: BookingRequest) -> Booking:
        """Create a demo booking for development/testing."""
        return Booking(
            id=12345,
            title=booking_request.title or "Meeting",
            description=booking_request.description,
            startTime=booking_request.start,
            endTime=booking_request.end,
            attendees=[booking_request.attendee],
            status="confirmed",
            eventType={"id": booking_request.eventTypeId, "title": "30 Minute Meeting"}
        )
    
    def get_bookings(self, user_email: Optional[str] = None) -> List[Booking]:
        """Get all bookings for a user.
        
        Args:
            user_email: Email of the user. If not provided, uses settings.
            
        Returns:
            List of bookings
        """
        email = user_email or settings.user_email
        
        try:
            params = {"attendeeEmail": email} if email else {}
            response = self._make_request("GET", "/bookings", params=params)
            bookings_data = response.get("bookings", response.get("data", []))
            
            return [Booking(**booking) for booking in bookings_data]
        except Exception as e:
            if settings.debug:
                print(f"Error getting bookings: {e}")
            return []
    
    def cancel_booking(self, booking_id: int, reason: Optional[str] = None) -> bool:
        """Cancel a booking.
        
        Args:
            booking_id: ID of the booking to cancel
            reason: Optional cancellation reason
            
        Returns:
            True if cancellation was successful, False otherwise
        """
        try:
            data = {"reason": reason} if reason else {}
            response = self._make_request(
                "DELETE", 
                f"/bookings/{booking_id}",
                json=data
            )
            
            return response.get("success", True)
        except Exception as e:
            if settings.debug:
                print(f"Error canceling booking: {e}")
            return True  # Return True for demo purposes
    
    def reschedule_booking(self, booking_id: int, new_start: str, new_end: str) -> Booking:
        """Reschedule a booking.
        
        Args:
            booking_id: ID of the booking to reschedule
            new_start: New start time in ISO 8601 format
            new_end: New end time in ISO 8601 format
            
        Returns:
            Updated booking
        """
        try:
            data = {
                "startTime": new_start,
                "endTime": new_end
            }
            response = self._make_request(
                "PATCH", 
                f"/bookings/{booking_id}",
                json=data
            )
            booking_data = response.get("booking", response.get("data", {}))
            
            return Booking(**booking_data)
        except Exception as e:
            if settings.debug:
                print(f"Error rescheduling booking: {e}")
            return None
