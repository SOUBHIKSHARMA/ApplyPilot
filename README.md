# ApplyPilot — Resume-Based Job Discovery & Application Tracker

ApplyPilot is a Python-based job discovery and application tracking application designed to help job seekers discover relevant opportunities, prioritize jobs based on resume relevance, and manage their job search workflow efficiently.

Built using Python, Streamlit, and SQLite, ApplyPilot searches selected public job sources, filters recent listings, calculates heuristic resume-match scores, and provides direct links to original job postings.

**Status:** In Progress

## Features

- **Resume Management:** Upload resumes in PDF, DOCX, or TXT format and extract text for review.
- **Personalized Job Search:** Configure target roles, skills, preferred locations, and relevant experience.
- **Job Discovery:** Retrieve listings from selected public job sources, including Himalayas, Remotive, and Arbeitnow.
- **Resume-Based Matching:** Score listings using target job roles and relevant skills.
- **Advanced Filtering:** Filter opportunities by role, location, posting date, and minimum match score.
- **Duplicate Prevention:** Avoid importing duplicate listings based on application URLs.
- **Application Tracking:** Manually mark jobs as applied and maintain a history of job discovery and status changes.
- **Interactive Dashboard:** Manage resumes, search jobs, review matching opportunities, and track application activity through Streamlit.
- **Local Storage:** Store job listings in SQLite and profile preferences in JSON files.
- **External Job Board Search:** Access quick-search links for Unstop and Wellfound.

## Tech Stack

- Python
- Streamlit
- SQLite
- Pandas
- Requests
- Feedparser
- pypdf
- python-docx

## Project Structure

```text
ApplyPilot/
├── app.py
├── applypilot_core.py
├── requirements.txt
├── README.md
├── RUN_APPLYPILOT.bat
└── data/
    ├── applypilot.db
    └── profile.json
```

The `data/` directory and its files are generated locally as the application saves information.

## Installation

### Prerequisites

- Python 3.10 or a compatible newer version
- pip
- Internet connection for retrieving job listings

### 1. Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd ApplyPilot
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with your actual repository URL.

### 2. Create a Virtual Environment

**Windows**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Run the Application

```bash
python -m streamlit run app.py
```

Open the local URL provided by Streamlit, usually `http://localhost:8501`.

## How to Use

1. Open the Resume & Preferences tab.
2. Upload your resume and review the extracted text.
3. Configure your target roles, skills, and preferred locations.
4. Save your profile and preferences.
5. Navigate to Find Jobs and select the roles, date range, locations, and sources you want to search.
6. Set the minimum resume-match score and start the search.
7. Review matching listings, job details, and detected skills.
8. Open the original job listing to review the opportunity and apply manually.
9. Mark jobs as applied to organize your search and hide completed applications from the default results.
10. Use Search History to review recorded activity.

## Matching Methodology

ApplyPilot calculates a heuristic relevance score using factors such as:

- Target job role relevance
- Skills detected in the job listing and saved resume
- Entry-level and junior role indicators
- Location-related keywords

The score helps prioritize listings but is not a probability of selection or a guarantee of suitability.

## Privacy & Responsible Automation

- Resume text and profile details are stored locally by the application.
- Job listings are retrieved from selected public sources.
- Applications are submitted manually through the original job websites.
- ApplyPilot does not automatically submit job applications.
- Private resumes, profile files, databases, credentials, and other sensitive information should not be committed to a public repository.

## Current Limitations

- Job discovery is limited to the selected public sources.
- Unstop and Wellfound are quick-search links and are not automatically imported in the current implementation.
- Listing availability, posting dates, and location information depend on the source data.
- Listings with unverifiable posting dates or certain location mismatches may be excluded.
- Matching uses rule-based scoring rather than a trained machine-learning model.
- Results vary depending on selected roles, locations, date ranges, and source availability.

## Future Enhancements

- Semantic matching between resumes and job descriptions.
- Additional authorized job-source integrations.
- Customizable matching weights and relevance criteria.
- Application deadlines, reminders, and follow-up management.
- Analytics for application activity and job-search progress.
- Automated tests and enhanced error handling.

## Project Objective

ApplyPilot aims to simplify job discovery by combining relevant job listings, resume-based matching, filtering, and application tracking in one interface.

The project demonstrates practical software development and product-oriented problem-solving through workflow design, feature prioritization, relevance scoring, usability, and responsible automation.

---

**Built with Python, Streamlit, and SQLite.**
