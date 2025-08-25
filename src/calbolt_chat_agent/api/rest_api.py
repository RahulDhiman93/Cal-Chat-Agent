"""REST API endpoints for the CalBolt Chat Agent."""

import uuid
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..core.agent import session_manager, LiveXChatSession
from ..config.settings import settings


# Request/Response Models
class ChatMessage(BaseModel):
    """Chat message model."""
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str = Field(..., description="Agent response")
    session_id: str = Field(..., description="Session ID")


class SessionInfo(BaseModel):
    """Session information model."""
    session_id: str = Field(..., description="Session ID")
    created_at: Optional[str] = Field(None, description="Session creation time")
    last_active: Optional[str] = Field(None, description="Last activity time")
    message_count: int = Field(..., description="Number of messages in conversation")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")


# Create FastAPI app
app = FastAPI(
    title="CalBolt Chat Agent API",
    description="AI-powered chatbot for Cal.com calendar management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get or create session
def get_session(session_id: Optional[str] = None) -> LiveXChatSession:
    """Get or create a chat session."""
    if not session_id:
        session_id = str(uuid.uuid4())
    
    return session_manager.get_session(session_id)


# API Endpoints
@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check."""
    return HealthResponse(
        status="healthy",
        version="1.0.0"
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0"
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """Send a message to the chat agent.
    
    Args:
        message: Chat message with optional session ID
        
    Returns:
        Agent response with session ID
    """
    try:
        # Get or create session
        session = get_session(message.session_id)
        
        # Process message
        response = session.send_message(message.message)
        
        return ChatResponse(
            response=response,
            session_id=session.session_id
        )
        
    except Exception as e:
        error_detail = str(e) if settings.debug else "Internal server error"
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )


@app.post("/chat/{session_id}", response_model=ChatResponse)
async def chat_with_session(session_id: str, message: ChatMessage):
    """Send a message to a specific session.
    
    Args:
        session_id: Session identifier
        message: Chat message
        
    Returns:
        Agent response
    """
    try:
        session = get_session(session_id)
        response = session.send_message(message.message)
        
        return ChatResponse(
            response=response,
            session_id=session.session_id
        )
        
    except Exception as e:
        error_detail = str(e) if settings.debug else "Internal server error"
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )


@app.get("/sessions", response_model=List[str])
async def list_sessions():
    """List all active session IDs.
    
    Returns:
        List of session IDs
    """
    return session_manager.list_sessions()


@app.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session_info(session_id: str):
    """Get information about a specific session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Session information
    """
    if session_id not in session_manager.sessions:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )
    
    session = session_manager.sessions[session_id]
    history = session.get_history()
    
    return SessionInfo(
        session_id=session_id,
        created_at=session.created_at.isoformat() if session.created_at else None,
        last_active=session.last_active.isoformat() if session.last_active else None,
        message_count=len(history)
    )


@app.post("/sessions/{session_id}/reset")
async def reset_session(session_id: str):
    """Reset a session conversation.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Success message
    """
    if session_id not in session_manager.sessions:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )
    
    session_manager.sessions[session_id].reset()
    
    return {"message": f"Session {session_id} has been reset"}


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Success message
    """
    if not session_manager.delete_session(session_id):
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )
    
    return {"message": f"Session {session_id} has been deleted"}


@app.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """Get conversation history for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Conversation history
    """
    if session_id not in session_manager.sessions:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )
    
    session = session_manager.sessions[session_id]
    history = session.get_history()
    
    # Convert messages to serializable format
    formatted_history = []
    for msg in history:
        formatted_history.append({
            "type": msg.__class__.__name__,
            "content": msg.content,
            "timestamp": getattr(msg, 'timestamp', None)
        })
    
    return {"history": formatted_history}


@app.post("/sessions/cleanup")
async def cleanup_sessions():
    """Clean up inactive sessions.
    
    Returns:
        Number of sessions cleaned up
    """
    cleaned_count = session_manager.cleanup_inactive_sessions()
    return {"message": f"Cleaned up {cleaned_count} inactive sessions"}


@app.get("/tools")
async def get_available_tools():
    """Get information about available tools.
    
    Returns:
        List of available tools and their descriptions
    """
    from ..core.agent import LiveXChatAgent
    
    try:
        agent = LiveXChatAgent()
        tools = agent.get_available_tools()
        return {"tools": tools}
    except Exception as e:
        error_detail = str(e) if settings.debug else "Error retrieving tools"
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )


# Exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle ValueError exceptions."""
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(error="Invalid input", detail=str(exc)).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    error_detail = str(exc) if settings.debug else "Internal server error"
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="Server error", detail=error_detail).dict()
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    try:
        # Validate settings
        settings.validate_required_settings()
        print("✅ CalBolt Chat Agent API started successfully")
        print(f"📊 Debug mode: {settings.debug}")
        print(f"🔑 OpenAI API key configured: {'Yes' if settings.openai_api_key else 'No'}")
        print(f"📅 Cal.com API key configured: {'Yes' if settings.calcom_api_key else 'No'}")
        
    except Exception as e:
        print(f"❌ Error during startup: {e}")
        if not settings.debug:
            raise


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "calbolt_chat_agent.api.rest_api:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
