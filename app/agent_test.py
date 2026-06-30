import asyncio
from dotenv import load_dotenv
from google.adk import Agent, Runner
from google.adk.apps.app import App
from google.adk.sessions import DatabaseSessionService
from google.genai import types

# Load environment variables from the local .env file
load_dotenv()

# Define the custom tool with descriptive docstrings
def search_jobs(keywords: str, location: str = "") -> str:
    """Searches the database for matching job listings.

    Args:
        keywords: The job search keywords (e.g., 'python', 'react').
        location: The job location filter (e.g., 'San Francisco', 'Remote').
    """
    # For now, we return mock job details
    return (
        f"Found 1 job matching '{keywords}' in '{location}':\n"
        "- Software Engineer (Python) at TechCorp (San Francisco, CA). "
        "Requirements: Python, SQL. Salary: $120k."
    )

async def main():
    # 1. Define the Agent
    agent = Agent(
        name="CareerPilotAgent",
        model="gemini-3.5-flash",
        tools=[search_jobs],  # Register the tool
        instruction=(
            "You are the CareerPilot Copilot, an AI career coach. Your goal is to "
            "help job seekers find tech, AI/ML, and software roles. Only discuss careers, "
            "resumes, interviews, and professional development. If the user asks about "
            "off-topic subjects (like recipes, movies, general knowledge, or programming logic "
            "unrelated to career advice), politely decline and redirect them back to careers."
        )
    )
    
    # 2. Define the App wrapping the Agent (The Play)
    app = App(name="CareerPilot", root_agent=agent)
    
    # 3. Create the Session Service (The Notepad)
    session_service = DatabaseSessionService(db_url="sqlite+aiosqlite:///data/careerpilot.db")
    
    # 4. Create the Runner to execute the App (The Director)
    runner = Runner(app=app, session_service=session_service, auto_create_session=True)
    
    # 5. Build the user's message using google.genai structured content
    new_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text="Find me a Python job in San Francisco.")]
    )
    
    # 6. Run the runner asynchronously and consume events
    async for event in runner.run_async(
        user_id="test_user",
        session_id="test_session",
        new_message=new_message
    ):
        # 7. Print the text response chunks as they stream in
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(part.text, end="", flush=True)
    print()

if __name__ == "__main__":
    asyncio.run(main())
