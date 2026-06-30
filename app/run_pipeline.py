import asyncio
from dotenv import load_dotenv
from app.db import init_db, search_jobs_in_db
from app.pipeline import parse_resume, match_jobs, generate_cover_letter

load_dotenv()

# A raw, unformatted student resume to parse
SAMPLE_RESUME_TEXT = """
Akash Kumar
Email: akash@example.com
Summary: Enthusiastic junior developer with passion for building clean backend systems and web applications.
Skills: Python, REST APIs, Git, SQL, HTML, CSS, JavaScript
Experience:
- Intern Developer at CodeLabs (Jan 2024 - June 2024): Assisted with building basic web pages and writing Python script automations.
"""

async def run_integration_pipeline():
    # 1. Setup the local database and seed it
    print("Step 1: Initializing and Seeding SQLite Database...")
    await init_db()
    
    # 2. Retrieve all active job listings from the database to match against
    print("\nStep 2: Fetching candidate jobs from database...")
    all_jobs_str = await search_jobs_in_db(query="")
    print(f"Fetched jobs list successfully.")
    
    # 3. Agent 1: Parse the raw resume text into Pydantic model
    print("\nStep 3: Running ResumeParserAgent (Agent 1)...")
    profile = await parse_resume(SAMPLE_RESUME_TEXT)
    print("Successfully Parsed Profile:")
    print(f"  Name: {profile.name}")
    print(f"  Skills: {profile.skills}")
    print("  Experiences:")
    for exp in profile.experience:
        print(f"    - {exp.title} at {exp.company} ({exp.duration})")
        
    # 4. Agent 2: Evaluate and rank all jobs against the parsed profile
    print("\nStep 4: Running JobMatcherAgent (Agent 2)...")
    match_results = await match_jobs(profile, all_jobs_str)
    
    # Sort matches by score in descending order
    sorted_matches = sorted(match_results.matches, key=lambda x: x.match_score, reverse=True)
    
    print("\nJob Matching & Ranking Results:")
    print("================================")
    for match in sorted_matches:
        print(f"\nJob ID: {match.job_id}")
        print(f"Match Score: {match.match_score}/100")
        print(f"Explanation: {match.fit_explanation}")
        print(f"Matching Skills: {match.matching_skills}")
        print(f"Missing Skills: {match.missing_skills}")
        print(f"Resume Advice:")
        for advice in match.resume_advice:
            print(f"  * {advice}")
            
    # 5. Agent 3: Write a cover letter for the best-matching job
    best_match = sorted_matches[0]
    print(f"\nStep 5: Generating tailored cover letter for Job ID {best_match.job_id} (Agent 3)...")
    
    # We retrieve the details of the best match to feed to the writer
    # For testing, we use Job ID 1 details if match is Job ID 1
    # We can write a quick lookup or just pass the title and company matching the ID
    job_title = "Junior Python Developer"
    company = "TechSoft Solutions"
    description = "We are looking for a Junior Python Developer to assist with backend API integrations."
    
    if best_match.job_id == 2:
        job_title = "ML Engineer Intern"
        company = "Cognitive AI"
        description = "Join our AI research team as an ML Intern. Help build and fine-tune NLP models."
    elif best_match.job_id == 3:
        job_title = "Frontend Engineer (React)"
        company = "WebFlow Corp"
        description = "Build high-performance web applications using React, HTML5, and TailwindCSS."
    elif best_match.job_id == 4:
        job_title = "Backend AI Developer"
        company = "Apex Robotics"
        description = "Build asynchronous Python microservices to coordinate robotic vision pipelines."
        
    cover_letter = await generate_cover_letter(
        profile=profile,
        job_title=job_title,
        company=company,
        job_desc=description
    )
    
    print("\nGenerated Cover Letter:")
    print("=======================")
    print(cover_letter)

if __name__ == "__main__":
    asyncio.run(run_integration_pipeline())
