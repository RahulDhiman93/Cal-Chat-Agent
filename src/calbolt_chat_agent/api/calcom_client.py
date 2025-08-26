"""Cal.com API client for calendar operations."""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import requests
from pydantic import BaseModel

from ..config.settings import settings


class BookingRequest(BaseModel):
    """Model for booking request data matching Cal.com v2 API."""
    eventTypeId: int
    start: str  # ISO 8601 format (UTC)
    attendee: Dict[str, Any]  # supports name, email, timeZone, language
    location: Optional[Dict[str, Any]] = None  # e.g., {"integration": "cal-video", "type": "integration"}
    # Optional fields
    end: Optional[str] = None
    lengthInMinutes: Optional[int] = None
    bookingFieldsResponses: Optional[Dict[str, Any]] = None
    eventTypeSlug: Optional[str] = None
    username: Optional[str] = None
    teamSlug: Optional[str] = None
    organizationSlug: Optional[str] = None
    guests: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    routing: Optional[Dict[str, Any]] = None
    meetingUrl: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class Booking(BaseModel):
    """Model for booking data."""
    id: int
    uid: Optional[str] = None
    title: str
    description: Optional[str] = None
    startTime: str
    endTime: str
    attendees: List[Dict[str, Any]]
    status: str
    eventType: Dict[str, Any]





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
            "Content-Type": "application/json",
            "cal-api-version": settings.calcom_api_version
        })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a request to the Cal.com API.
        
        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            API response data
            
        Raises:
            CalcomAPIError: If the API request fails
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        # Merge headers (allow override from kwargs)
        headers = kwargs.pop('headers', {})
        if 'cal-api-version' not in headers:
            headers['cal-api-version'] = settings.calcom_api_version
        kwargs['headers'] = headers
        
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
    

    
    def get_available_slots(self, event_type_id: int, start_date: str, end_date: str) -> List[AvailableSlot]:
        """Get available time slots using the slots API.
        
        Args:
            event_type_id: Event type ID
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of available slots
        """
        try:
            params = {
                "eventTypeId": event_type_id,
                "start": start_date,
                "end": end_date
            }
            response = self._make_request(
                "GET",
                "/slots",
                params=params,
                headers={"cal-api-version": "2024-09-04"}
            )
            data = response.get("data", {})
            slots: List[AvailableSlot] = []
            
            # Parse the response format: {"2025-08-26": [{"start": "..."}, ...]}
            if isinstance(data, dict):
                for date, slot_list in data.items():
                    if isinstance(slot_list, list):
                        for slot in slot_list:
                            if isinstance(slot, dict) and "start" in slot:
                                slots.append(AvailableSlot(time=slot["start"], attendees=1))
            
            return slots
        except Exception as e:
            if settings.debug:
                print(f"Error getting available slots: {e}")
            return []
    
    def create_booking(self, booking_request: BookingRequest) -> Booking:
        """Create a new booking.
        
        Args:
            booking_request: Booking request data
            
        Returns:
            Created booking
        """
        try:
            # Build payload by excluding None values
            payload = {k: v for k, v in booking_request.model_dump().items() if v is not None}
            print(f"payload for create booking: {payload}")
            response = self._make_request(
                "POST", 
                "/bookings", 
                json=payload,
                headers={"cal-api-version": "2024-08-13"}
            )
            print(f"response for create booking: {response}")
            booking_data = response.get("data", {})
            if booking_data:
                return self._map_booking_v2_to_model(booking_data)
            
            # Fallback response structure
            return Booking(
                id=0,
                title=booking_request.title or "Meeting",
                description=booking_request.description,
                startTime=booking_request.start,
                endTime=booking_request.end or booking_request.start,
                attendees=[booking_request.attendee],
                status="confirmed",
                eventType={"id": booking_request.eventTypeId}
            )
        except Exception as e:
            if settings.debug:
                print(f"Error creating booking: {e}")
            raise CalcomAPIError(f"Failed to create booking: {str(e)}")
    
    def get_bookings(self, take: int = 100) -> List[Booking]:
        """Get all bookings.
        
        Args:
            take: Number of bookings to retrieve (default: 100)
            
        Returns:
            List of bookings
        """
        try:
            params = {"take": take}
            response = self._make_request(
                "GET", 
                "/bookings", 
                params=params,
                headers={"cal-api-version": "2024-08-13"}
            )
            bookings_data = response.get("data", [])
            
            return [self._map_booking_v2_to_model(booking) for booking in bookings_data]
        except Exception as e:
            if settings.debug:
                print(f"Error getting bookings: {e}")
            return []
    
    def cancel_booking(self, booking_uid: str, cancellation_reason: Optional[str] = None, cancel_subsequent_bookings: bool = False) -> bool:
        """Cancel a booking.
        
        Args:
            booking_uid: UID of the booking to cancel
            cancellation_reason: Optional cancellation reason
            cancel_subsequent_bookings: Whether to cancel subsequent bookings
            
        Returns:
            True if cancellation was successful, False otherwise
        """
        try:
            data = {}
            if cancellation_reason:
                data["cancellationReason"] = cancellation_reason
            if cancel_subsequent_bookings:
                data["cancelSubsequentBookings"] = cancel_subsequent_bookings
                
            response = self._make_request(
                "POST", 
                f"/bookings/{booking_uid}/cancel",
                json=data
            )
            
            return response.get("status") == "success" or response.get("success", True)
        except Exception as e:
            if settings.debug:
                print(f"Error canceling booking: {e}")
            return False
    
    def reschedule_booking(self, booking_uid: str, new_start: str) -> Optional[Booking]:
        """Reschedule a booking using booking UID.
        
        Args:
            booking_uid: UID of the booking to reschedule
            new_start: New start time in ISO 8601 UTC format (e.g., 2025-08-26T23:00:00Z)
            
        Returns:
            Updated booking or None
        """
        try:
            body = {"start": new_start}
                
            response = self._make_request(
                "POST", 
                f"/bookings/{booking_uid}/reschedule",
                json=body,
                headers={"cal-api-version": "2024-08-13"}
            )
            booking_data = response.get("data", {})
            if not booking_data:
                return None
            return self._map_booking_v2_to_model(booking_data)
        except Exception as e:
            if settings.debug:
                print(f"Error rescheduling booking {booking_uid}: {e}")
            return None

    def _map_booking_v2_to_model(self, booking: Dict[str, Any]) -> Booking:
        """Map v2 booking response (with start/end) to internal Booking model (startTime/endTime)."""
        return Booking(
            id=booking.get("id", 0),
            uid=booking.get("uid"),
            title=booking.get("title", ""),
            description=booking.get("description"),
            startTime=booking.get("start") or booking.get("startTime", ""),
            endTime=booking.get("end") or booking.get("endTime", ""),
            attendees=booking.get("attendees", []),
            status=booking.get("status", ""),
            eventType=booking.get("eventType", {})
        )



    def get_booking(self, booking_uid: str) -> Optional[Booking]:
        """Get a specific booking by its UID.

        Args:
            booking_uid: The Cal.com booking UID

        Returns:
            Booking model if found, else None
        """
        try:
            response = self._make_request("GET", f"/bookings/{booking_uid}")
            booking_data = response.get("data", {})
            if not booking_data:
                return None
            return self._map_booking_v2_to_model(booking_data)
        except Exception as e:
            if settings.debug:
                print(f"Error getting booking {booking_uid}: {e}")
            return None
