"""Streamlit web interface for CalBolt Chat Agent."""

import streamlit as st
import uuid
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import json

# Add src directory to Python path for proper imports
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

try:
    from calbolt_chat_agent.core.agent import LiveXChatAgent
    from calbolt_chat_agent.config.settings import settings
except ImportError:
    # Fallback for relative imports
    from ..core.agent import LiveXChatAgent
    from ..config.settings import settings


# Page configuration
st.set_page_config(
    page_title="CalBolt Chat Agent",
    page_icon="L",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1.5rem 0;
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        margin-bottom: 2rem;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        max-width: 80%;
        border: 1px solid #e0e0e0;
    }
    
    .user-message {
        background-color: #f8f9fa;
        margin-left: auto;
        text-align: right;
        border-left: 4px solid #2a5298;
    }
    
    .agent-message {
        background-color: #ffffff;
        margin-right: auto;
        border-left: 4px solid #6c757d;
    }
    
    .sidebar-section {
        background-color: #f8f9fa;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 6px;
        border-left: 4px solid #2a5298;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 6px;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
        font-weight: 500;
    }
    
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 6px;
        border: 1px solid #f5c6cb;
        margin: 1rem 0;
        font-weight: 500;
    }
    
    .info-message {
        background-color: #e8f4f8;
        color: #2c3e50;
        padding: 1.25rem;
        border-radius: 6px;
        border: 1px solid #bee5eb;
        margin: 1rem 0;
        font-weight: 400;
        line-height: 1.6;
    }
    
    .stButton > button {
        border-radius: 6px;
        border: 1px solid #2a5298;
        background-color: #2a5298;
        color: white;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background-color: #1e3c72;
        border-color: #1e3c72;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)


class StreamlitChatInterface:
    """Streamlit chat interface for CalBolt Chat Agent."""
    
    def __init__(self):
        """Initialize the Streamlit interface."""
        self.initialize_session_state()
        self.setup_configuration()
    
    def initialize_session_state(self):
        """Initialize Streamlit session state variables."""
        if "session_id" not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        
        if "agent" not in st.session_state:
            st.session_state.agent = None
        
        if "agent_initialized" not in st.session_state:
            st.session_state.agent_initialized = False
        
        if "show_config" not in st.session_state:
            st.session_state.show_config = False
    
    def setup_configuration(self):
        """Setup agent configuration."""
        if not st.session_state.agent_initialized:
            try:
                st.session_state.agent = LiveXChatAgent()
                st.session_state.agent_initialized = True
            except Exception as e:
                st.session_state.config_error = str(e)
    
    def render_header(self):
        """Render the main header."""
        st.markdown("""
        <div class="main-header">
            <h1>CalBolt Chat Agent</h1>
            <p>Professional Calendar Management Assistant</p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_sidebar(self):
        """Render the sidebar with controls and information."""
        with st.sidebar:
            st.title("Controls")
            
            # Configuration section
            with st.expander("Configuration", expanded=st.session_state.show_config):
                self.render_configuration()
            
            # Session management
            with st.expander("Session Management"):
                self.render_session_management()
            
            # Quick actions
            with st.expander("Quick Actions"):
                self.render_quick_actions()
            
            # Help section
            with st.expander("Help & Examples"):
                self.render_help_section()
    
    def render_configuration(self):
        """Render configuration settings."""
        st.markdown("### API Configuration")
        
        # Check current configuration
        config_status = self.check_configuration()
        
        if config_status["all_configured"]:
            st.markdown('<div class="success-message">All APIs configured successfully</div>', 
                       unsafe_allow_html=True)
        else:
            st.markdown('<div class="error-message">Missing API configuration</div>', 
                       unsafe_allow_html=True)
        
        # Configuration status
        st.markdown("**Status:**")
        st.write(f"- OpenAI API: {'Configured' if config_status['openai'] else 'Not configured'}")
        st.write(f"- Cal.com API: {'Configured' if config_status['calcom'] else 'Not configured'}")
        st.write(f"- User Email: {'Configured' if config_status['email'] else 'Not configured'}")
        
        if not config_status["all_configured"]:
            st.markdown("**Setup Instructions:**")
            st.write("1. Copy `env.example` to `.env`")
            st.write("2. Add your API keys and email")
            st.write("3. Restart the application")
    
    def check_configuration(self) -> Dict[str, bool]:
        """Check if all required configuration is present."""
        return {
            "openai": bool(settings.openai_api_key),
            "calcom": bool(settings.calcom_api_key),
            "email": bool(settings.user_email),
            "all_configured": bool(settings.openai_api_key and settings.calcom_api_key and settings.user_email)
        }
    
    def render_session_management(self):
        """Render session management controls."""
        st.markdown(f"**Session ID:** `{st.session_state.session_id[:8]}...`")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("New Session", help="Start a new conversation"):
                self.start_new_session()
        
        with col2:
            if st.button("Clear Chat", help="Clear current conversation"):
                self.clear_chat()
        
        # Chat history info
        if st.session_state.chat_history:
            st.write(f"**Messages:** {len(st.session_state.chat_history)}")
            
            if st.button("Export Chat", help="Export conversation as JSON"):
                self.export_chat_history()
    
    def render_quick_actions(self):
        """Render quick action buttons."""
        st.markdown("**Common Tasks:**")
        
        quick_actions = [
            ("List my meetings", "Show me all my scheduled meetings"),
            ("Book a meeting", "Help me book a new meeting"),
            ("Cancel a meeting", "I need to cancel a meeting"),
            ("Reschedule meeting", "I want to reschedule a meeting"),
        ]
        
        for label, message in quick_actions:
            if st.button(label, help=f"Send: {message}"):
                self.send_quick_message(message)
    
    def render_help_section(self):
        """Render help and examples section."""
        st.markdown("**Example Commands:**")
        
        examples = [
            "Book a meeting with John on Tuesday at 3pm",
            "Show me my meetings for this week",
            "Cancel my 2pm meeting today",
            "Reschedule my meeting with Sarah to tomorrow",
            "What meetings do I have on Friday?",
            "Book a 1-hour call with the team next Monday"
        ]
        
        for example in examples:
            if st.button(f"{example}", key=f"example_{hash(example)}"):
                self.send_quick_message(example)
        
        st.markdown("---")
        st.markdown("**Tips:**")
        st.write("- Use natural language for dates and times")
        st.write("- Be specific about meeting details")
        st.write("- Ask for confirmation before changes")
    
    def render_chat_interface(self):
        """Render the main chat interface."""
        # Chat container
        chat_container = st.container()
        
        # Display chat history
        with chat_container:
            if not st.session_state.chat_history:
                st.markdown("""
                <div class="info-message">
                    Welcome! I'm your CalBolt Chat Agent. I can help you:
                    <ul>
                        <li>Book new meetings</li>
                        <li>List your scheduled meetings</li>
                        <li>Cancel meetings</li>
                        <li>Reschedule meetings</li>
                    </ul>
                    Simply type your request in natural language to get started.
                </div>
                """, unsafe_allow_html=True)
            
            for message in st.session_state.chat_history:
                self.render_message(message)
        
        # Input area
        self.render_input_area()
    
    def render_message(self, message: Dict[str, Any]):
        """Render a single chat message."""
        is_user = message["role"] == "user"
        
        # Message container
        message_class = "user-message" if is_user else "agent-message"
        
        # Format timestamp
        timestamp = message.get("timestamp", "")
        if timestamp:
            timestamp_str = f" - {timestamp}"
        else:
            timestamp_str = ""
        
        # Render message
        st.markdown(f"""
        <div class="chat-message {message_class}">
            <strong>{'You' if is_user else 'CalBolt Agent'}{timestamp_str}:</strong><br>
            {message['content']}
        </div>
        """, unsafe_allow_html=True)
    
    def render_input_area(self):
        """Render the chat input area."""
        # Input form
        with st.form("chat_form", clear_on_submit=True):
            col1, col2 = st.columns([4, 1])
            
            with col1:
                user_input = st.text_area(
                    "Type your message:",
                    placeholder="e.g., 'Book a meeting with John tomorrow at 3pm'",
                    height=100,
                    label_visibility="collapsed"
                )
            
            with col2:
                st.write("")  # Spacing
                submit_button = st.form_submit_button("Send", use_container_width=True)
        
        # Process input
        if submit_button and user_input.strip():
            self.process_user_message(user_input.strip())
    
    def process_user_message(self, message: str):
        """Process user message and get agent response."""
        if not st.session_state.agent_initialized:
            st.error("Agent not initialized. Please check your configuration.")
            return
        
        # Add user message to history
        user_message = {
            "role": "user",
            "content": message,
            "timestamp": datetime.now().strftime("%H:%M")
        }
        st.session_state.chat_history.append(user_message)
        
        # Get agent response
        with st.spinner("Processing your request..."):
            try:
                response = st.session_state.agent.chat(message)
                
                # Add agent response to history
                agent_message = {
                    "role": "agent",
                    "content": response,
                    "timestamp": datetime.now().strftime("%H:%M")
                }
                st.session_state.chat_history.append(agent_message)
                
            except Exception as e:
                error_message = {
                    "role": "agent",
                    "content": f"Sorry, I encountered an error: {str(e)}",
                    "timestamp": datetime.now().strftime("%H:%M")
                }
                st.session_state.chat_history.append(error_message)
        
        # Rerun to update the interface
        st.rerun()
    
    def send_quick_message(self, message: str):
        """Send a predefined quick message."""
        self.process_user_message(message)
    
    def start_new_session(self):
        """Start a new chat session."""
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.chat_history = []
        if st.session_state.agent:
            st.session_state.agent.reset_conversation()
        st.rerun()
    
    def clear_chat(self):
        """Clear the current chat history."""
        st.session_state.chat_history = []
        if st.session_state.agent:
            st.session_state.agent.reset_conversation()
        st.rerun()
    
    def export_chat_history(self):
        """Export chat history as JSON."""
        export_data = {
            "session_id": st.session_state.session_id,
            "export_time": datetime.now().isoformat(),
            "messages": st.session_state.chat_history
        }
        
        st.download_button(
            label="Download Chat History",
            data=json.dumps(export_data, indent=2),
            file_name=f"calbolt_chat_{st.session_state.session_id[:8]}.json",
            mime="application/json"
        )
    
    def run(self):
        """Run the Streamlit application."""
        self.render_header()
        
        # Main layout
        col1, col2 = st.columns([3, 1])
        
        with col1:
            self.render_chat_interface()
        
        with col2:
            self.render_sidebar()


def main():
    """Main function to run the Streamlit app."""
    try:
        # Initialize and run the interface
        interface = StreamlitChatInterface()
        interface.run()
        
    except Exception as e:
        st.error(f"Application Error: {str(e)}")
        
        # Show configuration help
        st.markdown("### Configuration Help")
        st.write("1. Ensure you have set up your `.env` file with required API keys")
        st.write("2. Check that all dependencies are installed")
        st.write("3. Verify your Cal.com and OpenAI API keys are valid")
        
        if st.button("Retry"):
            st.rerun()


if __name__ == "__main__":
    main()
