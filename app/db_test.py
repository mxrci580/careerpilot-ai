import asyncio
from app.db import init_db, search_jobs_in_db

async def test_pipeline():
    # 1. Initialize and seed the SQLite database
    print("Step 1: Initializing database...")
    await init_db()
    
    # 2. Run a search query for "Python"
    print("\nStep 2: Searching database for 'Python'...")
    search_results = await search_jobs_in_db(query="Python")
    print(search_results)
    
    # 3. Run a search query for "React" in "New York"
    print("\nStep 3: Searching database for 'React' in 'New York'...")
    react_results = await search_jobs_in_db(query="React", location="New York")
    print(react_results)

if __name__ == "__main__":
    asyncio.run(test_pipeline())
