import asyncio
import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List
from google.adk import Agent, Runner
from google.adk.apps.app import App
from google.adk.sessions import InMemorySessionService
from google.genai import types

load_dotenv()

# 1. Define the Pydantic schemas (the form)
class Experience(BaseModel):
    title: str = Field(description="Job title or role")
    company: str = Field(description="Company or organization name")
    duration: str = Field(description="Timeframe of the role, e.g. July 2024 - Present")

class UserProfile(BaseModel):
    name: str = Field(description="Candidate full name")
    skills: List[str] = Field(description="Key technical skills")
    experience: List[Experience] = Field(description="List of past professional experiences")

async def main():
    # 2. Define the Agent (omitting mode, defaults to 'chat' as required)
    agent = Agent(
        name="ResumeParserAgent",
        model="gemini-3.5-flash",
        output_schema=UserProfile,  # Enforces structured output
        instruction="Parse the raw resume text and extract the candidate's name, skills, and experience."
    )
    
    app = App(name="ResumeParser", root_agent=agent)
    session_service = InMemorySessionService()
    runner = Runner(app=app, session_service=session_service, auto_create_session=True)
    
    # 3. Raw resume text to parse
    raw_resume_text = """
    Alex Mercer
    Email: alex@example.com
    Skills: Python, SQLite, HTML, CSS, JavaScript, Git
    Experience:
    - Junior Web Developer at TechSoft (July 2024 - Present)
    - Intern at CodeLabs (Jan 2024 - June 2024)
    """
    
    new_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=raw_resume_text)]
    )
    
    print("Parsing resume text...")
    
    # 4. Accumulate the text chunks in this variable
    accumulated_text = ""
    
    async for event in runner.run_async(
        user_id="test_user",
        session_id="parse_session",
        new_message=new_message
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    # Append each text chunk to our accumulator
                    accumulated_text += part.text
                    print(part.text, end="", flush=True)
    print()

    # 5. Parse the final accumulated JSON text into our Pydantic model
    try:
        parsed_profile = UserProfile.model_validate_json(accumulated_text)
        print("\nSuccessfully Parsed Pydantic Object!")
        print("Candidate Name:", parsed_profile.name)
        print("Candidate Skills:", parsed_profile.skills)
        print("Candidate Experience:")
        for exp in parsed_profile.experience:
            print(f"  - {exp.title} at {exp.company} ({exp.duration})")
    except json.JSONDecodeError as e:
        print("\nFailed to decode JSON:", e)
    except Exception as e:
        print("\nValidation failed:", e)

if __name__ == "__main__":
    asyncio.run(main())
