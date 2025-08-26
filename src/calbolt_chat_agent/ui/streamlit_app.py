"""Simple, clean chat interface for CalBolt Chat Agent."""

import streamlit as st
import uuid
import sys
import os
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
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


# Simple page configuration
st.set_page_config(
    page_title="CalBolt - Calendar Assistant",
    page_icon=None,
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Clean, simple CSS
st.markdown("""
<style>
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Main app styling */
    .stApp {
        background-color: #f8fafc;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    /* Container */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 800px;
    }
    
    /* Header */
    .header {
        text-align: center;
        margin-bottom: 2rem;
        padding: 1rem;
        background: white;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .header h1 {
        color: #1f2937;
        margin: 0 0 0.5rem 0;
        font-size: 2rem;
        font-weight: 600;
    }
    
    .header p {
        color: #6b7280;
        margin: 0;
        font-size: 1.1rem;
    }
    
    /* Chat container */
    .chat-container {
        background: white;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        overflow: hidden;
    }
    
    /* Messages area */
    .messages {
        padding: 1.5rem;
        min-height: 400px;
        max-height: 500px;
        overflow-y: auto;
    }
    
    .message {
        margin-bottom: 1rem;
        display: flex;
        gap: 0.75rem;
    }
    
    .message.user {
        flex-direction: row-reverse;
    }
    
    .avatar {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background: #e5e7eb;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 0.875rem;
        color: #374151;
        flex-shrink: 0;
    }
    
    .message.user .avatar {
        background: #3b82f6;
        color: white;
    }
    
    .message-content {
        background: #f3f4f6;
        padding: 0.75rem 1rem;
        border-radius: 12px;
        max-width: 70%;
        color: #1f2937;
        line-height: 1.5;
    }
    
    .message.user .message-content {
        background: #3b82f6;
        color: white;
    }
    
    .timestamp {
        font-size: 0.75rem;
        color: #9ca3af;
        margin-top: 0.25rem;
    }
    
    /* Welcome area */
    .welcome {
        text-align: center;
        padding: 2rem;
        color: #6b7280;
    }
    
    .welcome h3 {
        color: #1f2937;
        margin-bottom: 1rem;
    }
    
    /* Suggestions */
    .suggestions {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 0.75rem;
        margin: 1.5rem 0;
    }
    
    .suggestion {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 0.75rem;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 0.875rem;
        color: #374151;
    }
    
    .suggestion:hover {
        background: #f3f4f6;
        border-color: #3b82f6;
        transform: translateY(-1px);
    }
    
    /* Input area */
    .input-area {
        padding: 1.5rem;
        border-top: 1px solid #e5e7eb;
        background: #f9fafb;
    }
    
    /* Enhanced Streamlit components */
    .stTextArea > div > div > textarea {
        border-radius: 8px;
        border: 1px solid #d1d5db;
        font-size: 0.875rem;
        padding: 0.75rem;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        outline: none;
    }
    
    .stButton > button {
        background: #3b82f6;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
        transition: background-color 0.2s ease;
    }
    
    .stButton > button:hover {
        background: #2563eb;
    }
    
    /* Status indicator */
    .status {
        text-align: center;
        padding: 0.5rem;
        font-size: 0.875rem;
        color: #6b7280;
    }
    
    .status.error {
        color: #dc2626;
        background: #fef2f2;
        border-radius: 6px;
        margin-bottom: 1rem;
    }
    
    .status.success {
        color: #059669;
        background: #ecfdf5;
        border-radius: 6px;
        margin-bottom: 1rem;
    }
    
    /* Typing indicator */
    .typing {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 1rem;
    }
    
    .typing-dots {
        display: flex;
        gap: 2px;
    }
    
    .typing-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #9ca3af;
        animation: typing 1.4s infinite ease-in-out;
    }
    
    .typing-dot:nth-child(1) { animation-delay: -0.32s; }
    .typing-dot:nth-child(2) { animation-delay: -0.16s; }
    .typing-dot:nth-child(3) { animation-delay: 0s; }
    
    @keyframes typing {
        0%, 80%, 100% {
            transform: scale(0.8);
            opacity: 0.5;
        }
        40% {
            transform: scale(1);
            opacity: 1;
        }
    }
    
    /* Controls */
    .controls {
        display: flex;
        gap: 0.5rem;
        justify-content: center;
        margin: 1rem 0;
    }
    
    .control-btn {
        background: white;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        font-size: 0.875rem;
        color: #374151;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .control-btn:hover {
        background: #f9fafb;
        border-color: #9ca3af;
    }
</style>
""", unsafe_allow_html=True)


class SimpleChatInterface:
    """Simple chat interface for CalBolt."""
    
    def __init__(self):
        """Initialize the simple chat interface."""
        self.initialize_session_state()
        self.setup_agent()
    
    def initialize_session_state(self):
        """Initialize session state variables."""
        if "session_id" not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        
        if "agent" not in st.session_state:
            st.session_state.agent = None
        
        if "agent_ready" not in st.session_state:
            st.session_state.agent_ready = False
        
        if "is_processing" not in st.session_state:
            st.session_state.is_processing = False
        
        if "error_message" not in st.session_state:
            st.session_state.error_message = None
    
    def setup_agent(self):
        """Setup the chat agent."""
        if not st.session_state.agent_ready:
            try:
                st.session_state.agent = LiveXChatAgent()
                st.session_state.agent_ready = True
                st.session_state.error_message = None
            except Exception as e:
                st.session_state.agent_ready = False
                st.session_state.error_message = str(e)
    
    def check_configuration(self):
        """Check if configuration is valid."""
        return (
            bool(settings.openai_api_key) and 
            bool(settings.calcom_api_key) and 
            bool(settings.user_email)
        )
    
    def render_header(self):
        """Render simple header."""
        st.markdown("""
        <div class="header">
            <h1>CalBolt</h1>
            <p>Your Calendar Assistant</p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_status(self):
        """Render configuration status."""
        if st.session_state.error_message:
            st.markdown(f"""
            <div class="status error">
                Configuration needed. Please check your API keys in the .env file.
            </div>
            """, unsafe_allow_html=True)
            return False
        elif not self.check_configuration():
            st.markdown("""
            <div class="status error">
                Please configure your API keys to get started.
            </div>
            """, unsafe_allow_html=True)
            return False
        else:
            st.markdown("""
            <div class="status success">
                Ready to help with your calendar!
            </div>
            """, unsafe_allow_html=True)
            return True
    
    def render_welcome(self):
        """Render welcome message with suggestions."""
        st.markdown("""
        <div class="welcome">
            <h3>Welcome! How can I help you today?</h3>
            <p>I can help you manage your calendar, schedule meetings, and check your availability.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Simple suggestions
        suggestions = [
            "Show my meetings today",
            "Schedule a meeting",
            "Check my availability this week",
            "Cancel a meeting"
        ]
        
        st.markdown("### Try these examples:")
        cols = st.columns(2)
        
        for i, suggestion in enumerate(suggestions):
            col = cols[i % 2]
            with col:
                if st.button(suggestion, key=f"suggestion_{i}", use_container_width=True):
                    self.send_message(suggestion)
    
    def render_messages(self):
        """Render chat messages."""
        st.markdown('<div class="messages">', unsafe_allow_html=True)
        
        if not st.session_state.chat_history:
            self.render_welcome()
        else:
            for message in st.session_state.chat_history:
                self.render_message(message)
        
        # Typing indicator
        if st.session_state.is_processing:
            st.markdown("""
            <div class="typing">
                <div class="avatar">CB</div>
                <div>
                    <div class="typing-dots">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                    <span style="margin-left: 0.5rem; color: #6b7280; font-size: 0.875rem;">
                        CalBolt is thinking...
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def render_message(self, message):
        """Render a single message."""
        is_user = message["role"] == "user"
        role_class = "user" if is_user else "assistant"
        avatar_text = "U" if is_user else "CB"
        
        st.markdown(f"""
        <div class="message {role_class}">
            <div class="avatar">{avatar_text}</div>
            <div>
                <div class="message-content">{message['content']}</div>
                <div class="timestamp">{message.get('timestamp', '')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    def render_input(self):
        """Render input area."""
        st.markdown('<div class="input-area">', unsafe_allow_html=True)
        
        # Simple controls
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("Clear", use_container_width=True):
                self.clear_chat()
        with col2:
            if st.button("Export", use_container_width=True):
                self.export_chat()
        
        # Input form
        with st.form("chat_form", clear_on_submit=True):
            col1, col2 = st.columns([4, 1])
            
            with col1:
                user_input = st.text_area(
                    "Type your message...",
                    height=60,
                    placeholder="Ask me about your calendar, meetings, or schedule...",
                    label_visibility="collapsed",
                    disabled=st.session_state.is_processing
                )
            
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                send_button = st.form_submit_button(
                    "Send" if not st.session_state.is_processing else "...",
                    use_container_width=True,
                    disabled=st.session_state.is_processing
                )
        
        if send_button and user_input.strip():
            self.send_message(user_input.strip())
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def send_message(self, message):
        """Send a message to the agent."""
        if not st.session_state.agent_ready:
            st.error("Agent not ready. Please check your configuration.")
            return
        
        if st.session_state.is_processing:
            return
        
        try:
            # Add user message
            user_message = {
                "role": "user",
                "content": message,
                "timestamp": datetime.now().strftime("%H:%M")
            }
            st.session_state.chat_history.append(user_message)
            
            # Set processing state
            st.session_state.is_processing = True
            st.rerun()
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    def process_response(self, user_message):
        """Process agent response."""
        try:
            response = st.session_state.agent.chat(user_message)
            
            agent_message = {
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().strftime("%H:%M")
            }
            st.session_state.chat_history.append(agent_message)
            
        except Exception as e:
            error_message = {
                "role": "assistant",
                "content": f"Sorry, I encountered an error: {str(e)}",
                "timestamp": datetime.now().strftime("%H:%M")
            }
            st.session_state.chat_history.append(error_message)
        
        finally:
            st.session_state.is_processing = False
    
    def clear_chat(self):
        """Clear chat history."""
        st.session_state.chat_history = []
        if st.session_state.agent:
            try:
                st.session_state.agent.reset_conversation()
            except:
                pass
        st.success("Chat cleared!")
        st.rerun()
    
    def export_chat(self):
        """Export chat history."""
        if not st.session_state.chat_history:
            st.warning("No messages to export.")
            return
        
        export_data = {
            "session_id": st.session_state.session_id,
            "export_time": datetime.now().isoformat(),
            "messages": st.session_state.chat_history
        }
        
        st.download_button(
            label="Download Chat",
            data=json.dumps(export_data, indent=2),
            file_name=f"calbolt_chat_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json"
        )
    
    def run(self):
        """Run the simple chat interface."""
        # Header
        self.render_header()
        
        # Status
        is_ready = self.render_status()
        
        if not is_ready:
            st.markdown("""
            ### Setup Instructions:
            1. Copy `env.example` to `.env`
            2. Add your API keys:
               - `OPENAI_API_KEY=your_openai_key`
               - `CALCOM_API_KEY=your_calcom_key` 
               - `USER_EMAIL=your_email`
            3. Restart the application
            """)
            return
        
        # Handle agent processing
        if st.session_state.is_processing and st.session_state.chat_history:
            last_message = st.session_state.chat_history[-1]
            if last_message["role"] == "user":
                self.process_response(last_message["content"])
                st.rerun()
        
        # Chat container
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        # Messages
        self.render_messages()
        
        # Input
        self.render_input()
        
        st.markdown('</div>', unsafe_allow_html=True)


def main():
    """Main function."""
    try:
        interface = SimpleChatInterface()
        interface.run()
    except Exception as e:
        st.error(f"Application Error: {str(e)}")
        
        with st.expander("Need Help?"):
            st.markdown("""
            **Common Issues:**
            - Missing API keys in .env file
            - Invalid API keys
            - Network connectivity issues
            
            **Setup:**
            1. Make sure you have a .env file with your API keys
            2. Check that all required dependencies are installed
            3. Restart the application after making changes
            """)


if __name__ == "__main__":
    main()