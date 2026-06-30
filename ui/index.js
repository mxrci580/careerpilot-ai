// ==========================================================================
// STATE MANAGEMENT & CONSTANTS
// ==========================================================================
const API_BASE = window.location.origin; // Dynamically binds to our FastAPI server port
let currentProfile = null;
let rawJobsList = [];
let jobMatchResults = [];
let selectedJob = null;

// DOM Elements Lookup
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('resume-file-input');
const uploadSection = document.getElementById('upload-section');
const loadingSection = document.getElementById('loading-section');
const loadingStatus = document.getElementById('loading-status');
const loadingSubtext = document.getElementById('loading-subtext');
const dashboardLayout = document.getElementById('dashboard-layout');

// Sidebar DOM Elements
const candidateName = document.getElementById('candidate-name');
const parsedSkillsContainer = document.getElementById('parsed-skills-container');
const parsedExperienceList = document.getElementById('parsed-experience-list');
const jobsContainer = document.getElementById('jobs-container');

// Drawer DOM Elements
const detailsDrawer = document.getElementById('details-drawer');
const closeDrawerBtn = document.getElementById('close-drawer-btn');
const drawerOverlay = document.getElementById('drawer-overlay');
const drawerJobCompany = document.getElementById('drawer-job-company');
const drawerJobTitle = document.getElementById('drawer-job-title');
const drawerMatchScore = document.getElementById('drawer-match-score');
const drawerFitExplanation = document.getElementById('drawer-fit-explanation');
const drawerMatchingSkills = document.getElementById('drawer-matching-skills');
const drawerMissingSkills = document.getElementById('drawer-missing-skills');
const drawerResumeAdvice = document.getElementById('drawer-resume-advice');

// Cover Letter DOM Elements
const generateLetterBtn = document.getElementById('generate-letter-btn');
const letterLoadingContainer = document.getElementById('letter-loading-container');
const letterContentContainer = document.getElementById('letter-content-container');
const coverLetterTextarea = document.getElementById('cover-letter-textarea');
const copyLetterBtn = document.getElementById('copy-letter-btn');

// ==========================================================================
// INITIALIZATION
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
    // 1. Initial Job Fetch (so the page is not empty)
    fetchInitialJobs();
    
    // 2. Setup File Upload Event Listeners
    setupUploadHandlers();
    
    // 3. Setup Drawer Actions
    closeDrawerBtn.addEventListener('click', closeDrawer);
    drawerOverlay.addEventListener('click', closeDrawer);
    
    // 4. Setup Cover Letter Actions
    generateLetterBtn.addEventListener('click', triggerCoverLetterGeneration);
    copyLetterBtn.addEventListener('click', copyCoverLetterToClipboard);
});

// ==========================================================================
// API CLIENT CALLS
// ==========================================================================

async function fetchInitialJobs() {
    try {
        const res = await fetch(`${API_BASE}/api/jobs`);
        if (!res.ok) throw new Error("Failed to load jobs");
        rawJobsList = await res.json();
        
        // Show initial jobs on screen
        renderJobs(rawJobsList, false);
    } catch (e) {
        console.error("Error fetching initial jobs:", e);
        jobsContainer.innerHTML = `<p class="error-msg">⚠️ Failed to connect to jobs database. Make sure uvicorn server is running.</p>`;
    }
}

async function uploadResumeFile(file) {
    // Show Loading Phase 1
    uploadSection.classList.add('hidden');
    loadingSection.classList.remove('hidden');
    loadingStatus.textContent = "Extracting Resume Content...";
    loadingSubtext.textContent = "Our Resume Agent is converting your PDF into structured data models.";

    const formData = new FormData();
    formData.append('file', file);

    try {
        // Run Agent 1: Parse PDF
        const res = await fetch(`${API_BASE}/api/parse-resume`, {
            method: 'POST',
            body: formData
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed parsing resume");
        }
        currentProfile = await res.json();
        
        // Update Sidebar View with parsed profile
        updateSidebar(currentProfile);
        
        // Transition to Loading Phase 2
        loadingStatus.textContent = "Matching Jobs...";
        loadingSubtext.textContent = "Comparing your skills and experience against our jobs database.";
        
        // Run Agent 2: Evaluate & Re-rank
        await evaluateAndRankJobs(currentProfile);
        
    } catch (e) {
        console.error(e);
        alert(`Parsing failed: ${e.message}`);
        // Reset view
        loadingSection.classList.add('hidden');
        uploadSection.classList.remove('hidden');
    }
}

async function evaluateAndRankJobs(profile) {
    try {
        const res = await fetch(`${API_BASE}/api/match-jobs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(profile)
        });
        if (!res.ok) throw new Error("Matching request failed");
        
        const results = await res.json();
        jobMatchResults = results.matches;
        
        // Render evaluated, sorted jobs on screen
        renderJobs(rawJobsList, true);
        
        // Transition to Dashboard view
        loadingSection.classList.add('hidden');
        dashboardLayout.classList.remove('hidden');
        
    } catch (e) {
        console.error(e);
        alert("Job matching analysis failed.");
        loadingSection.classList.add('hidden');
        uploadSection.classList.remove('hidden');
    }
}

async function triggerCoverLetterGeneration() {
    if (!currentProfile || !selectedJob) return;
    
    // Toggle Loading State
    generateLetterBtn.classList.add('hidden');
    letterLoadingContainer.classList.remove('hidden');
    letterContentContainer.classList.add('hidden');
    
    try {
        // Run Agent 3: Generate cover letter
        const res = await fetch(`${API_BASE}/api/cover-letter`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                profile: currentProfile,
                job_title: selectedJob.title,
                company: selectedJob.company,
                description: selectedJob.description
            })
        });
        if (!res.ok) throw new Error("Failed to write cover letter");
        
        const data = await res.json();
        
        // Populate text container
        coverLetterTextarea.value = data.cover_letter;
        
        // Display Text Container
        letterLoadingContainer.classList.add('hidden');
        letterContentContainer.classList.remove('hidden');
        
    } catch (e) {
        console.error(e);
        alert("Cover letter tailoring failed.");
        letterLoadingContainer.classList.add('hidden');
        generateLetterBtn.classList.remove('hidden');
    }
}

// ==========================================================================
// RENDERERS & LAYOUT UPDATERS
// ==========================================================================

function updateSidebar(profile) {
    candidateName.textContent = profile.name || "Akash Kumar";
    
    // Render Skills Tags
    parsedSkillsContainer.innerHTML = "";
    profile.skills.forEach(skill => {
        const span = document.createElement('span');
        span.className = 'skill-tag';
        span.textContent = skill;
        parsedSkillsContainer.appendChild(span);
    });
    
    // Render Experience List
    parsedExperienceList.innerHTML = "";
    profile.experience.forEach(exp => {
        const div = document.createElement('div');
        div.className = 'exp-item';
        div.innerHTML = `
            <h4>${exp.title}</h4>
            <p class="exp-company">${exp.company}</p>
            <p class="exp-duration">🕒 ${exp.duration}</p>
        `;
        parsedExperienceList.appendChild(div);
    });
}

function renderJobs(jobs, isEvaluated = false) {
    jobsContainer.innerHTML = "";
    
    let jobsToRender = [...jobs];
    
    // If evaluated, join and sort by score
    if (isEvaluated) {
        jobsToRender = jobsToRender.map(job => {
            const matchInfo = jobMatchResults.find(r => r.job_id === job.id);
            return {
                ...job,
                match_score: matchInfo ? matchInfo.match_score : 0,
                evaluation: matchInfo || null
            };
        });
        
        // Sort by match score in descending order
        jobsToRender.sort((a, b) => b.match_score - a.match_score);
    }
    
    jobsToRender.forEach(job => {
        const card = document.createElement('div');
        card.className = 'job-card';
        
        // Get requirements display string
        const reqsStr = job.requirements.slice(0, 3).join(", ") + (job.requirements.length > 3 ? "..." : "");
        
        // Set match badge styling class based on score value
        let scoreClass = 'match-low';
        let scoreDisplay = "Not Analyzed";
        
        if (isEvaluated) {
            scoreDisplay = `${job.match_score}%`;
            if (job.match_score >= 85) scoreClass = 'match-90';
            else if (job.match_score >= 60) scoreClass = 'match-70';
        }
        
        card.innerHTML = `
            <div class="job-meta-left">
                <span class="job-card-company">${job.company}</span>
                <h3 class="job-card-title">${job.title}</h3>
                <div class="job-card-details">
                    <span>📍 ${job.location}</span>
                    <span>💰 ${job.salary_range || 'Not specified'}</span>
                    <span>🛠️ [${reqsStr}]</span>
                </div>
            </div>
            <div class="job-meta-right">
                ${isEvaluated ? `
                    <div class="score-badge-container" style="flex-direction:column; align-items:flex-end; gap:0;">
                        <span class="score-text ${scoreClass}">${scoreDisplay}</span>
                        <span style="font-size:0.75rem; color:var(--text-muted);">Match Score</span>
                    </div>
                ` : `
                    <span class="badge warning">Upload Resume</span>
                `}
            </div>
        `;
        
        // Add click listener to show job details in side drawer
        card.addEventListener('click', () => openJobDrawer(job, isEvaluated));
        jobsContainer.appendChild(card);
    });
}

function openJobDrawer(job, isEvaluated) {
    selectedJob = job;
    
    // Set Header Info
    drawerJobCompany.textContent = job.company;
    drawerJobTitle.textContent = job.title;
    
    // Reset Cover Letter display state
    generateLetterBtn.classList.remove('hidden');
    letterLoadingContainer.classList.add('hidden');
    letterContentContainer.classList.add('hidden');
    coverLetterTextarea.value = "";
    
    if (isEvaluated && job.evaluation) {
        const evalData = job.evaluation;
        
        // Populate scores & explanations
        drawerMatchScore.textContent = `${evalData.match_score}%`;
        drawerFitExplanation.textContent = evalData.fit_explanation;
        
        // Populate Matching Skills (Green Tags)
        drawerMatchingSkills.innerHTML = "";
        evalData.matching_skills.forEach(skill => {
            const span = document.createElement('span');
            span.className = 'skill-tag match';
            span.textContent = skill;
            drawerMatchingSkills.appendChild(span);
        });
        if (evalData.matching_skills.length === 0) {
            drawerMatchingSkills.innerHTML = `<span style="font-size:0.85rem; color:var(--text-muted);">None</span>`;
        }

        // Populate Missing Skills (Red Tags)
        drawerMissingSkills.innerHTML = "";
        evalData.missing_skills.forEach(skill => {
            const span = document.createElement('span');
            span.className = 'skill-tag missing';
            span.textContent = skill;
            drawerMissingSkills.appendChild(span);
        });
        if (evalData.missing_skills.length === 0) {
            drawerMissingSkills.innerHTML = `<span style="font-size:0.85rem; color:var(--color-success);">None! Fully aligned.</span>`;
        }

        // Populate Advice list
        drawerResumeAdvice.innerHTML = "";
        evalData.resume_advice.forEach(bullet => {
            const li = document.createElement('li');
            li.textContent = bullet;
            drawerResumeAdvice.appendChild(li);
        });
        
    } else {
        // Fallback if drawer clicked before upload
        drawerMatchScore.textContent = "N/A";
        drawerFitExplanation.textContent = "Please upload a PDF resume in the main dashboard to evaluate your compatibility score, missing skill tags, and resume optimization tips.";
        drawerMatchingSkills.innerHTML = `<span style="font-size:0.85rem; color:var(--text-muted);">Upload resume first</span>`;
        drawerMissingSkills.innerHTML = `<span style="font-size:0.85rem; color:var(--text-muted);">Upload resume first</span>`;
        drawerResumeAdvice.innerHTML = `<li>Upload your PDF resume to generate customized actionable advice.</li>`;
        
        // Hide cover letter button if resume is not parsed
        generateLetterBtn.classList.add('hidden');
    }
    
    // Show drawer
    detailsDrawer.classList.remove('hidden');
    document.body.style.overflow = 'hidden'; // Disable background scrolling
}

function closeDrawer() {
    detailsDrawer.classList.add('hidden');
    document.body.style.overflow = ''; // Enable background scrolling
}

// ==========================================================================
// ACTIONS & EVENT UTILITIES
// ==========================================================================

function setupUploadHandlers() {
    // Drop Zone Visual Triggers
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
        }, false);
    });

    // File dropped trigger
    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0 && files[0].type === "application/pdf") {
            uploadResumeFile(files[0]);
        } else {
            alert("Only PDF resume files are supported!");
        }
    });

    // File selected trigger via browse click
    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            uploadResumeFile(fileInput.files[0]);
        }
    });
}

function copyCoverLetterToClipboard() {
    coverLetterTextarea.select();
    coverLetterTextarea.setSelectionRange(0, 99999); // For mobile devices
    
    navigator.clipboard.writeText(coverLetterTextarea.value)
        .then(() => {
            const originalText = copyLetterBtn.textContent;
            copyLetterBtn.textContent = "Copied! ✓";
            copyLetterBtn.classList.add('success');
            
            setTimeout(() => {
                copyLetterBtn.textContent = originalText;
                copyLetterBtn.classList.remove('success');
            }, 2000);
        })
        .catch(err => {
            console.error("Clipboard write failed:", err);
            alert("Failed to copy letter. Please select and copy manually.");
        });
}
