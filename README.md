# 🚀 CareerPilot AI — Autonomous Career Navigation & Job Application Platform

An autonomous, end-to-end AI career agent designed for personalized job search, deep semantic ATS fit scoring, tailored resume and cover letter synthesis, full-lifecycle Kanban application tracking, and AI interview coaching.

---

## 🌟 Key Features

1. **Multi-Source Job Radar**:
   - Aggregates real-time tech listings across public APIs (RemoteOK, Arbeitnow) and curated high-signal tech feeds.
   - 1-click **Custom Job Importer** to paste job specifications directly from LinkedIn, Greenhouse, Lever, or company portals.

2. **Multi-Dimensional ATS Match Engine**:
   - Computes weighted fit scores (0-100%) evaluating hard tech skills, target seniority, remote alignment, and compensation expectations.
   - Identifies exact **Matched Skills** and **Missing ATS Keywords** to give candidates an unfair advantage in screening filters.

3. **Application Studio & Autonomous Tailoring**:
   - Dynamically re-aligns resume summaries, skill orders, and impact bullets for the specific role without fabricating fictitious experience.
   - Synthesizes compelling, hiring-manager-targeted cover letters addressing company vision.
   - Generates answers to standard portal screening questions ("Why work here?", "Describe your architecture philosophy").
   - Synthesizes role-specific **STAR-method interview talking points** on demand.

4. **Full Lifecycle Kanban Pipeline**:
   - Organize opportunities across 6 stages: `Discovered` ➔ `Tailored` ➔ `Ready for Review` ➔ `Applied` ➔ `Interviewing` ➔ `Offers Won`.
   - Track application dates, interview schedules, and notes.

5. **Autonomous vs. Copilot Modes**:
   - **Copilot Mode (Default)**: Stages tailored packages in "Ready for Review" for human-in-the-loop 1-click confirmation before application dispatch.
   - **Autonomous Mode**: Continuously scouts feeds, calculates scores, and auto-tailors applications for roles exceeding the minimum match threshold (e.g. &ge;75%).

6. **Market Intelligence & Skill Gap Analytics**:
   - Aggregates top in-demand skills across all scouted listings.
   - Highlights high-impact skill gaps you can bridge to boost match velocity.

7. **Dual-Mode AI Engine**:
   - **Google Gemini Integration**: Connect your `GEMINI_API_KEY` (Gemini 2.5 Flash / Gemini 1.5 Pro) for high-nuance semantic reasoning.
   - **Local Heuristic Fallback Engine**: Works 100% reliably out of the box with zero external API dependencies.

---

## 📂 Project Structure

```
ai-career-agent/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── matcher.py        # ATS & semantic scoring engine
│   │   │   ├── orchestrator.py   # Autonomous agent cycle runner
│   │   │   ├── scraper.py        # Multi-source job aggregator
│   │   │   └── tailor.py         # Tailored resume & cover letter synthesizer
│   │   ├── routes/
│   │   │   ├── agent.py          # Command center & execution triggers
│   │   │   ├── analytics.py      # Market demand & skill gap insights
│   │   │   ├── applications.py   # Kanban pipeline CRUD
│   │   │   ├── jobs.py           # Job discovery & search API
│   │   │   ├── profile.py        # Ground-truth Career DNA
│   │   │   └── tailor.py         # On-demand synthesis & interview prep
│   │   ├── database.py           # SQLite connection & seed data
│   │   ├── main.py               # FastAPI application & static server
│   │   └── models.py             # ORM models and Pydantic schemas
│   ├── tests/
│   │   └── test_career_agent.py  # Pytest test suite (8 passing tests)
│   ├── career_agent.db           # Persistent SQLite database
│   └── requirements.txt          # Python dependencies
├── frontend/
│   └── public/
│       ├── app.css               # Modern dark theme styles
│       ├── app.js                # Reactive client-side logic
│       └── index.html            # Executive web dashboard
├── run_server.py                 # Direct Python runner
├── start.bat                     # Windows batch launcher
├── start.ps1                     # PowerShell launcher
└── README.md
```

---

## ⚡ Quick Start

### 1. Launch the System
In Windows PowerShell or Command Prompt:
```powershell
python run_server.py
```
*(Or double-click `start.bat`)*

### 2. Open the Dashboard
Navigate to:
👉 **`http://localhost:8000`**

Interactive Swagger API docs are available at:
👉 **`http://localhost:8000/docs`**

---

## 🧪 Running Automated Tests
```powershell
python -m pytest backend/tests/test_career_agent.py -v
```
All 8 test suites verify profile updates, live job matching, ATS tailoring, manual job import, pipeline transitions, and autonomous agent loops.
