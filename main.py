#!/usr/bin/env python3
"""Main entry point for LiveX Chat Agent."""

import sys
import os
import argparse
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from livex_chat_agent.config.settings import settings


def run_streamlit():
    """Run the Streamlit web interface."""
    import subprocess
    
    streamlit_app = Path(__file__).parent / "streamlit_app.py"
    
    cmd = [
        sys.executable, 
        "-m", "streamlit", 
        "run", 
        str(streamlit_app),
        "--server.port", str(settings.port),
        "--server.address", settings.host
    ]
    
    print(f"🚀 Starting Streamlit app on http://{settings.host}:{settings.port}")
    subprocess.run(cmd)


def run_api():
    """Run the FastAPI REST API server."""
    import uvicorn
    
    print(f"🚀 Starting FastAPI server on http://{settings.host}:{settings.port}")
    
    uvicorn.run(
        "livex_chat_agent.api.rest_api:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )


def run_cli():
    """Run the command line interface."""
    from livex_chat_agent.core.agent import LiveXChatAgent
    
    print("🤖 LiveX Chat Agent - CLI Mode")
    print("Type 'exit' or 'quit' to end the conversation\n")
    
    try:
        agent = LiveXChatAgent()
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                print("🤖 Agent: ", end="")
                response = agent.chat(user_input)
                print(response)
                print()
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                print()
                
    except Exception as e:
        print(f"❌ Failed to initialize agent: {str(e)}")
        print("Please check your configuration and try again.")


def validate_config():
    """Validate configuration and show status."""
    print("🔍 Checking configuration...")
    
    try:
        settings.validate_required_settings()
        print("✅ Configuration is valid!")
        
        print(f"\n📊 Configuration Status:")
        print(f"- OpenAI API Key: {'✅ Set' if settings.openai_api_key else '❌ Missing'}")
        print(f"- Cal.com API Key: {'✅ Set' if settings.calcom_api_key else '❌ Missing'}")
        print(f"- User Email: {'✅ Set' if settings.user_email else '❌ Missing'}")
        print(f"- Debug Mode: {settings.debug}")
        print(f"- Model: {settings.openai_model}")
        
    except ValueError as e:
        print(f"❌ Configuration Error: {str(e)}")
        print("\n📝 Setup Instructions:")
        print("1. Copy 'env.example' to '.env'")
        print("2. Edit '.env' and add your API keys")
        print("3. Run 'python main.py validate' to check again")
        sys.exit(1)


def setup_env():
    """Set up environment file from example."""
    env_example = Path("env.example")
    env_file = Path(".env")
    
    if not env_example.exists():
        print("❌ env.example file not found")
        return
    
    if env_file.exists():
        print(f"⚠️  .env file already exists")
        response = input("Do you want to overwrite it? (y/N): ")
        if response.lower() != 'y':
            print("Setup cancelled")
            return
    
    # Copy example to .env
    with open(env_example, 'r') as src, open(env_file, 'w') as dst:
        dst.write(src.read())
    
    print("✅ Created .env file from example")
    print("📝 Please edit .env and add your API keys:")
    print("- OPENAI_API_KEY")
    print("- CALCOM_API_KEY") 
    print("- USER_EMAIL")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="LiveX Chat Agent - AI-powered calendar assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py web          # Run Streamlit web interface
  python main.py api          # Run FastAPI REST server
  python main.py cli          # Run command line interface
  python main.py validate     # Validate configuration
  python main.py setup        # Setup environment file
        """
    )
    
    parser.add_argument(
        "mode",
        choices=["web", "api", "cli", "validate", "setup"],
        help="Run mode"
    )
    
    parser.add_argument(
        "--host",
        default=settings.host,
        help=f"Host address (default: {settings.host})"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=settings.port,
        help=f"Port number (default: {settings.port})"
    )
    
    args = parser.parse_args()
    
    # Update settings with command line args
    if args.host != settings.host:
        settings.host = args.host
    if args.port != settings.port:
        settings.port = args.port
    
    # Route to appropriate function
    if args.mode == "web":
        run_streamlit()
    elif args.mode == "api":
        run_api()
    elif args.mode == "cli":
        run_cli()
    elif args.mode == "validate":
        validate_config()
    elif args.mode == "setup":
        setup_env()


if __name__ == "__main__":
    main()
