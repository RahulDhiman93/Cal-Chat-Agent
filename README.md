# LiveX Chat Agent 🤖📅

An AI-powered chatbot for seamless calendar management using OpenAI's function calling capabilities and Cal.com API integration.

## Overview

LiveX Chat Agent is an interactive chatbot that allows users to manage their calendar directly through natural language conversations. Built with Python, LangChain, and OpenAI's GPT function calling, it provides a seamless interface for booking, listing, canceling, and rescheduling meetings.

## Features ✨

### Core Features
- 📅 **Book Meetings**: Schedule new meetings with natural language input
- 📋 **List Meetings**: View all scheduled meetings and appointments
- ❌ **Cancel Meetings**: Cancel existing meetings by ID or description
- 🔄 **Reschedule Meetings**: Move meetings to new dates and times

### Interface Options
- 🌐 **Web Interface**: Beautiful Streamlit-based web UI
- 🔌 **REST API**: Full REST API for integration with other applications
- 💻 **CLI Interface**: Command-line interface for terminal users

### AI Capabilities
- 🧠 **Natural Language Processing**: Understand requests in plain English
- 🎯 **Context Awareness**: Maintain conversation context for multi-turn interactions
- 🔧 **Function Calling**: Leverages OpenAI's function calling for precise actions
- 💡 **Smart Suggestions**: Provides alternative times when requested slots are unavailable

## Quick Start 🚀

### Prerequisites
- Python 3.8 or higher
- OpenAI API key
- Cal.com account and API key

### Installation

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd livex-chat-agent
   chmod +x scripts/setup.sh
   ./scripts/setup.sh
   ```

2. **Configure environment**:
   ```bash
   cp env.example .env
   # Edit .env and add your API keys
   ```

3. **Validate configuration**:
   ```bash
   python main.py validate
   ```

4. **Run the application**:
   ```bash
   # Web interface (recommended)
   python main.py web
   
   # Alternative: Run Streamlit directly
   streamlit run streamlit_app.py
   
   # REST API server
   python main.py api
   
   # Command line interface
   python main.py cli
   ```

## Configuration ⚙️

### Environment Variables

Create a `.env` file with the following variables:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-your-openai-api-key-here

# Cal.com Configuration
CALCOM_API_KEY=your-calcom-api-key-here
CALCOM_BASE_URL=https://api.cal.com/v2

# User Configuration
USER_EMAIL=your-email@example.com

# Application Configuration
DEBUG=True
HOST=0.0.0.0
PORT=8000
```

### Getting API Keys

#### OpenAI API Key
1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy the key to your `.env` file

#### Cal.com API Key
1. Log in to your [Cal.com account](https://app.cal.com)
2. Go to Settings → Developer → API Keys
3. Create a new API key
4. Copy the key to your `.env` file

## Usage Examples 💬

### Natural Language Commands

The chatbot understands natural language requests:

```text
"Book a meeting with John tomorrow at 3pm"
"Show me my meetings for this week"
"Cancel my 2pm meeting today"
"Reschedule my meeting with Sarah to next Monday at 10am"
"What meetings do I have on Friday?"
"Book a 1-hour call with the team next Tuesday"
```

### Web Interface

1. Start the web interface: `python main.py web`
2. Open your browser to `http://localhost:8000`
3. Type your requests in natural language
4. Use quick action buttons for common tasks

### REST API

#### Send a chat message:
```bash
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Book a meeting tomorrow at 3pm"}'
```

#### List active sessions:
```bash
curl "http://localhost:8000/sessions"
```

#### Get session history:
```bash
curl "http://localhost:8000/sessions/{session_id}/history"
```

### CLI Interface

```bash
python main.py cli

You: Book a meeting with John tomorrow at 3pm
🤖 Agent: I'd be happy to help you book a meeting with John tomorrow at 3pm. 
To proceed, I'll need a few more details:
- What's John's email address?
- What should be the subject/title of the meeting?
- How long should the meeting be? (default is 30 minutes)
```

## Project Structure 📁

```
livex-chat-agent/
├── src/livex_chat_agent/
│   ├── api/                    # API clients and REST endpoints
│   │   ├── calcom_client.py   # Cal.com API client
│   │   └── rest_api.py        # FastAPI REST API
│   ├── config/                # Configuration management
│   │   └── settings.py        # Application settings
│   ├── core/                  # Core chatbot logic
│   │   └── agent.py           # Main agent implementation
│   ├── tools/                 # LangChain tools
│   │   └── calendar_tools.py  # Calendar operation tools
│   └── ui/                    # User interfaces
│       └── streamlit_app.py   # Streamlit web interface
├── scripts/
│   └── setup.sh              # Setup script
├── main.py                    # Main entry point
├── requirements.txt           # Python dependencies
└── README.md                 # This file
```

## API Reference 📖

### REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/chat` | POST | Send chat message |
| `/chat/{session_id}` | POST | Send message to specific session |
| `/sessions` | GET | List all sessions |
| `/sessions/{session_id}` | GET | Get session info |
| `/sessions/{session_id}/reset` | POST | Reset session |
| `/sessions/{session_id}/history` | GET | Get conversation history |
| `/sessions/{session_id}` | DELETE | Delete session |
| `/tools` | GET | List available tools |

### Function Tools

The agent uses the following LangChain tools:

- **book_meeting**: Book a new meeting
- **list_bookings**: List scheduled meetings  
- **cancel_booking**: Cancel an existing meeting
- **reschedule_booking**: Reschedule a meeting

## Development 🛠️

### Setting up Development Environment

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run tests** (when available):
   ```bash
   pytest tests/
   ```

3. **Code formatting**:
   ```bash
   black src/
   flake8 src/
   ```

### Adding New Features

1. **New Tools**: Add to `src/livex_chat_agent/tools/`
2. **API Endpoints**: Extend `src/livex_chat_agent/api/rest_api.py`
3. **UI Components**: Modify `src/livex_chat_agent/ui/streamlit_app.py`

## Troubleshooting 🔧

### Common Issues

#### Configuration Errors
```bash
# Validate your configuration
python main.py validate

# Check if API keys are set
echo $OPENAI_API_KEY
echo $CALCOM_API_KEY
```

#### Cal.com API Issues
- Ensure your Cal.com API key has the correct permissions
- Check that your event types are properly configured
- Verify your Cal.com account is active

#### OpenAI API Issues
- Verify your API key is valid and has sufficient credits
- Check rate limits if you're making many requests
- Ensure the model (default: gpt-4) is available to your account

### Debug Mode

Enable debug mode in your `.env` file:
```env
DEBUG=True
```

This will provide detailed logging and error messages.

### Import Errors

If you encounter import errors when running the Streamlit app:

```bash
# Use the standalone app
streamlit run streamlit_app.py

# Or run through main.py
python main.py web
```

If you still have issues, ensure you're in the project root directory and the virtual environment is activated.

## Contributing 🤝

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License 📄

This project is licensed under the MIT License - see the LICENSE file for details.

## Support 💬

If you encounter any issues or have questions:

1. Check the troubleshooting section above
2. Review the API documentation
3. Open an issue on the repository
4. Contact the development team

## Acknowledgments 🙏

- [OpenAI](https://openai.com) for GPT function calling capabilities
- [Cal.com](https://cal.com) for calendar API integration
- [LangChain](https://langchain.com) for AI application framework
- [Streamlit](https://streamlit.io) for the web interface
- [FastAPI](https://fastapi.tiangolo.com) for the REST API framework

---

Built with ❤️ by the LiveX Team
