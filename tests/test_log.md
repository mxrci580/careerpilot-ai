# CareerPilot: Test & Evaluation Log

This log tracks the functional and behavioral tests executed during the development of CareerPilot to prevent regressions.

---

## Active Test Cases

### 1. Agent Initialization & Connection (Lesson 1 & 2)
* **Date**: 2026-06-27
* **Component**: ADK Runtime & Credentials
* **Input**: `"Hello! Who are you?"`
* **Expected Behavior**: The runner initializes the session, loads the `GEMINI_API_KEY` from the environment, contacts Gemini, and streams back a response identifying the agent.
* **Actual Output**:
  ```text
  Hello! I am CareerPilotAgent, a helpful assistant built by Google. 
  I'm here to help you navigate your career journey...
  ```
* **Status**: ✅ **PASSED**

---

### 2. Persona Guardrails (Lesson 3)
* **Date**: 2026-06-27
* **Component**: System Instructions
* **Input**: `"Can you give me a recipe for a chocolate cake?"`
* **Expected Behavior**: The agent must recognize that the input is off-topic, politely decline, and redirect the user back to tech career coaching.
* **Actual Output**:
  ```text
  While a chocolate cake sounds delicious, I'm here to help you whip up a great career instead! 
  As the CareerPilot Copilot, I specialize in helping job seekers find tech, AI/ML, and software roles.
  ...
  ```
* **Status**: ✅ **PASSED**

---

### 3. Tool Calling & Job Search (Lesson 5)
* **Date**: 2026-06-27
* **Component**: Custom Python Tools (Function Calling)
* **Input**: `"Find me a Python job in San Francisco."`
* **Expected Behavior**: The Agent detects that the query requires a job search, calls `search_jobs(keywords='Python', location='San Francisco')`, receives the mock data, and formats a friendly summary for the user.
* **Actual Output**:
  ```text
  I found a matching job in San Francisco:
  *   Software Engineer (Python) at TechCorp
      *   Location: San Francisco, CA
      *   Requirements: Python, SQL
      *   Salary: $120,000
  ...
  ```
* **Status**: ✅ **PASSED**

---

### 4. SQLite Database Session Store (Lesson 6)
* **Date**: 2026-06-27
* **Component**: Database Session Store (`DatabaseSessionService`)
* **Input**: `"Find me a Python job in San Francisco."`
* **Expected Behavior**: The runner initializes the DatabaseSessionService, connects using the async `sqlite+aiosqlite:///` driver, creates the database file `data/careerpilot.db` and schemas, and successfully runs the conversational turn.
* **Actual Output**:
  ```text
  I found a job opening that matches your criteria in San Francisco:
  * Role: Software Engineer (Python) at TechCorp
  * Company: TechCorp
  * Location: San Francisco, CA
  * Requirements: Python, SQL
  * Salary: $120,000
  ...
  ```
* **Status**: ✅ **PASSED**

---

### 5. Local Database Seeding & Keyword Search (Lesson 9 Prep)
* **Date**: 2026-06-30
* **Component**: Database seeding and SQL search queries (`app/db.py`)
* **Input**: Runs `init_db()` and searches for `"Python"`, then `"React"` in `"New York"`.
* **Expected Behavior**: Creates the SQLite `jobs` table, seeds it with 4 mock jobs, and successfully filters/returns matches by keyword and location.
* **Actual Output**:
  ```text
  Step 1: Initializing database...
  Seeding SQLite database with mock job listings...
  Seeding complete.

  Step 2: Searching database for 'Python'...
  Found 3 matching job(s):
  - Job ID: 1 (Junior Python Developer)
  - Job ID: 2 (ML Engineer Intern)
  - Job ID: 4 (Backend AI Developer)

  Step 3: Searching database for 'React' in 'New York'...
  Found 1 matching job(s):
  - Job ID: 3 (Frontend Engineer (React))
  ```
* **Status**: ✅ **PASSED**

---

### 6. Full Sequential Pipeline Integration (Lesson 9 Prep)
* **Date**: 2026-06-30
* **Component**: Multi-Agent Sequential Matching & Cover Letter Pipeline (`app/pipeline.py`)
* **Input**: `SAMPLE_RESUME_TEXT` (Akash Kumar, Intern at CodeLabs...) matching against all seeded SQLite jobs.
* **Expected Behavior**: Sequential execution of:
  1. ResumeParserAgent: Extracts structured `UserProfile` object.
  2. JobMatcherAgent: Evaluates and ranks all SQLite jobs against the profile, returning a structured `JobMatchResultsList`.
  3. CoverLetterAgent: Writes a customized cover letter for the highest-scoring job.
* **Actual Output**: Successfully parsed profile, ranked Job ID 1 at 95% match, Job ID 3 at 60%, Job ID 4 at 55%, and Job ID 2 at 50%. Wrote an outstanding tailored cover letter for Job ID 1.
* **Status**: ✅ **PASSED**

---

### 7. FastAPI Endpoint: Jobs Listing (Lesson 9)
* **Date**: 2026-06-30
* **Component**: FastAPI Endpoint (`app/main.py`)
* **Input**: `GET http://127.0.0.1:8000/api/jobs`
* **Expected Behavior**: Server boots without errors, initializes SQLite engine, and returns all 4 sample job objects as a structured JSON list.
* **Actual Output**: Clean JSON array containing TechSoft Solutions, Cognitive AI, WebFlow Corp, and Apex Robotics.
* **Status**: ✅ **PASSED**

---

### 8. Unified Static Frontend Serving (Lesson 10)
* **Date**: 2026-06-30
* **Component**: Static File Mounting (`app/main.py`)
* **Input**: `GET http://127.0.0.1:8000/`
* **Expected Behavior**: FastAPI serves the index.html from `/ui` folder automatically on root query.
* **Actual Output**: Serves the index.html file containing CareerPilot | AI Career Mentor & Job Matcher.
* **Status**: ✅ **PASSED**
