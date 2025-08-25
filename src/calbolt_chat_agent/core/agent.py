"""Core chatbot agent implementation using LangChain and OpenAI."""

from typing import List, Dict, Any, Optional
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import BaseMessage
from langchain.memory import ConversationBufferMemory

from ..config.settings import settings
from ..tools.calendar_functions import get_calendar_tools
from ..api.calcom_client import CalcomClient


class LiveXChatAgent:
    """CalBolt Chat Agent for calendar operations using OpenAI function calling."""
    
    def __init__(self, 
                 openai_api_key: Optional[str] = None,
                 calcom_client: Optional[CalcomClient] = None,
                 model_name: Optional[str] = None,
                 temperature: Optional[float] = None):
        """Initialize the CalBolt Chat Agent.
        
        Args:
            openai_api_key: OpenAI API key. If not provided, uses settings.
            calcom_client: Cal.com client instance. If not provided, creates new one.
            model_name: OpenAI model name. If not provided, uses settings.
            temperature: Model temperature. If not provided, uses settings.
        """
        self.openai_api_key = openai_api_key or settings.openai_api_key
        self.model_name = model_name or settings.openai_model
        self.temperature = temperature or settings.temperature
        
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required")
        
        # Initialize components
        self.calcom_client = calcom_client or CalcomClient()
        self.llm = self._create_llm()
        self.tools = self._get_tools()
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        self.agent_executor = self._create_agent()
    
    def _create_llm(self) -> ChatOpenAI:
        """Create the OpenAI LLM instance."""
        return ChatOpenAI(
            api_key=self.openai_api_key,
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=settings.max_tokens
        )
    
    def _get_tools(self) -> List[BaseTool]:
        """Get all available tools for the agent."""
        return get_calendar_tools()
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for the agent."""
        return """You are CalBolt Chat Agent, an AI assistant specialized in helping users manage their calendar and meetings through Cal.com integration.

**Your Capabilities:**
- Book new meetings with specified date, time, and attendee details
- List all scheduled meetings for the user
- Cancel existing meetings by ID or description
- Reschedule meetings to new times
- Provide helpful scheduling assistance and recommendations

**Your Personality:**
- Friendly, professional, and helpful
- Proactive in asking for necessary details
- Clear in confirmations and updates
- Efficient in handling calendar operations

**Important Guidelines:**
1. **Always confirm important details** before booking or making changes
2. **Ask for missing information** required for calendar operations:
   - For booking: date, time, duration, title, attendee name and email
   - For canceling: specific meeting identifier (ID, title, or time)
   - For rescheduling: specific meeting identifier and new date/time
3. **Use natural language** to interpret user requests (e.g., "tomorrow at 3pm", "next Monday")
4. **Provide clear confirmations** with all relevant meeting details
5. **Handle errors gracefully** and suggest alternatives when possible
6. **Be proactive** in suggesting available time slots when requested times are unavailable

**User Context:**
- User email: {user_email}
- Current date/time: {current_time}

Remember to be conversational and helpful while being efficient with calendar operations. Always double-check important details before making changes to someone's calendar.
""".format(
            user_email=settings.user_email,
            current_time="Use current date/time from context"
        )
    
    def _create_agent(self) -> AgentExecutor:
        """Create the agent executor."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._create_system_prompt()),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad")
        ])
        
        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=settings.debug,
            handle_parsing_errors=True,
            max_iterations=5
        )
    
    def chat(self, message: str) -> str:
        """Process a chat message and return the response.
        
        Args:
            message: User message
            
        Returns:
            Agent response
        """
        try:
            response = self.agent_executor.invoke({"input": message})
            return response.get("output", "I'm sorry, I couldn't process your request. Please try again.")
        except Exception as e:
            error_msg = f"Error processing your request: {str(e)}"
            if settings.debug:
                print(error_msg)
            return "I encountered an error while processing your request. Please try again or contact support."
    
    def reset_conversation(self) -> None:
        """Reset the conversation memory."""
        self.memory.clear()
    
    def get_conversation_history(self) -> List[BaseMessage]:
        """Get the conversation history.
        
        Returns:
            List of conversation messages
        """
        return self.memory.chat_memory.messages
    
    def get_available_tools(self) -> List[Dict[str, str]]:
        """Get information about available tools.
        
        Returns:
            List of tool information dictionaries
        """
        return [
            {
                "name": tool.name,
                "description": tool.description
            }
            for tool in self.tools
        ]


class LiveXChatSession:
    """Manages a chat session with conversation state."""
    
    def __init__(self, 
                 session_id: str,
                 agent: Optional[LiveXChatAgent] = None):
        """Initialize a chat session.
        
        Args:
            session_id: Unique session identifier
            agent: CalBolt chat agent instance
        """
        self.session_id = session_id
        self.agent = agent or LiveXChatAgent()
        self.created_at = None
        self.last_active = None
    
    def send_message(self, message: str) -> str:
        """Send a message and get response.
        
        Args:
            message: User message
            
        Returns:
            Agent response
        """
        import datetime
        
        if not self.created_at:
            self.created_at = datetime.datetime.now()
        
        self.last_active = datetime.datetime.now()
        
        return self.agent.chat(message)
    
    def reset(self) -> None:
        """Reset the session conversation."""
        self.agent.reset_conversation()
    
    def get_history(self) -> List[BaseMessage]:
        """Get conversation history."""
        return self.agent.get_conversation_history()


class SessionManager:
    """Manages multiple chat sessions."""
    
    def __init__(self):
        """Initialize session manager."""
        self.sessions: Dict[str, LiveXChatSession] = {}
    
    def get_session(self, session_id: str) -> LiveXChatSession:
        """Get or create a chat session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Chat session instance
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = LiveXChatSession(session_id)
        
        return self.sessions[session_id]
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a chat session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was deleted, False if not found
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def list_sessions(self) -> List[str]:
        """List all active session IDs.
        
        Returns:
            List of session IDs
        """
        return list(self.sessions.keys())
    
    def cleanup_inactive_sessions(self, max_inactive_hours: int = 24) -> int:
        """Clean up inactive sessions.
        
        Args:
            max_inactive_hours: Maximum hours of inactivity before cleanup
            
        Returns:
            Number of sessions cleaned up
        """
        import datetime
        
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=max_inactive_hours)
        inactive_sessions = [
            sid for sid, session in self.sessions.items()
            if session.last_active and session.last_active < cutoff_time
        ]
        
        for session_id in inactive_sessions:
            del self.sessions[session_id]
        
        return len(inactive_sessions)


# Global session manager instance
session_manager = SessionManager()
