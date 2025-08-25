# CalBolt: AI Calendar Assistant

CalBolt is a simple chat-based assistant that helps you manage your calendar. You can ask it to book, list, cancel, or reschedule meetings in plain English. It connects to OpenAI for understanding your requests and to Cal.com to manage your calendar.

Built by Rahul Dhiman.

## What you can do

- Book a meeting
- See your upcoming meetings
- Cancel a meeting
- Reschedule a meeting

## Requirements

- Python 3.8+
- An OpenAI API key
- A Cal.com account and API key

## Set up

1) Clone the project and install dependencies
```bash
git clone <repository-url>
cd CalBolt-chat-agent
pip install -r requirements.txt
```

2) Add your settings
Create a file named `.env` in the project folder with the following values:
```env
OPENAI_API_KEY=sk-...
CALCOM_API_KEY=...
CALCOM_BASE_URL=https://api.cal.com/v2
USER_EMAIL=your-email@example.com

# Optional
DEBUG=True
HOST=0.0.0.0
PORT=8000
```

3) Check your configuration
```bash
python main.py validate
```

## Run CalBolt

Pick one of the options below.

```bash
# Web app (recommended)
python main.py web

# REST API server
python main.py api

# Command-line chat
python main.py cli
```

## How to talk to it

Type simple requests like:
```text
Book a meeting with John tomorrow at 3pm
Show my meetings for this week
Cancel my 2pm meeting today
Reschedule my meeting with Sarah to next Monday at 10am
```

## Web and API

- Web: visit `http://localhost:8000`
- API example:
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Book a meeting tomorrow at 3pm"}'
```

## Troubleshooting

Configuration check:
```bash
python main.py validate
echo $OPENAI_API_KEY
echo $CALCOM_API_KEY
```

If the web app fails to start, try:
```bash
streamlit run streamlit_app.py
```

Ensure your Cal.com API key has the right permissions and your OpenAI key is valid.

## License

MIT License. See the `LICENSE` file.

## Thanks

OpenAI, Cal.com, LangChain, Streamlit, and FastAPI.
