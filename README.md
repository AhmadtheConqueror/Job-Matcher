# AI Career Assistant

A Flask web application for students, graduates, and early-career professionals who want to review CVs, compare themselves against real vacancies, prepare application materials, and track skill gaps.

The app combines uploaded CV context, pasted job descriptions, saved chat history, Gemini-powered career guidance, feedback collection, evaluation data, and downloadable PDF artifacts.

## Features

### Accounts and Dashboard

- User registration, login, and logout with password hashing.
- Per-user CVs, analyses, conversations, feedback, and skill-gap records.
- Dashboard summary with uploaded CV count and recent job analyses.
- Quick links to upload a CV, analyze a job, and draft a cover letter.

### CV Upload and Parsing

- Upload CVs in PDF, DOCX, or TXT format.
- Maximum upload size: 8 MB.
- CV text extraction for downstream AI analysis.
- Uploaded CV list with original filename and upload date.
- Delete uploaded CVs from the dashboard.

### Job Matching

- Select a saved CV and paste a job description.
- Store job title, company, and description.
- Generate a structured AI analysis with:
  - Match summary
  - Strongest relevant experience
  - Missing or weak skills
  - Suggested CV improvements
  - Interview preparation points
- View saved analysis results later.
- Copy analysis text.
- Download analysis results as PDF.

### Career Chat

- Logged-in chatbot for career guidance.
- Conversation history saved per user.
- Create, open, and delete chat conversations.
- Conversation titles are generated from the first user message.
- Use latest CV context automatically.
- Choose a specific uploaded CV from the chat dropdown.
- Turn CV context on or off for the next message.
- Attach, update, or clear job-description context inside a conversation.
- Chat starter buttons for common workflows:
  - Review my CV
  - Analyze fit
  - CV plan
  - Interview prep
  - Skill gaps
  - Roadmap
  - Role ideas
- Message limit: 8,000 characters.
- Job-description context limit: 12,000 characters.
- Assistant replies are rendered with headings, bullets, and ordered lists.
- Copy assistant responses.
- Mark assistant responses as helpful or not helpful.

### Chat Tool Actions

The chat can launch saved, structured career artifacts from suggested actions.

- Generate cover letters from chat.
- Create CV tailoring plans for a target role.
- Prepare interview questions and practice guidance.
- Identify skill gaps for a job description.
- Create a 30-60-90 day career roadmap.
- Save generated artifacts as assistant messages.
- Attach metadata to generated messages, including prompt version, provider, CV usage, job-description usage, and tool action.
- Download generated chat artifacts as PDFs:
  - Cover letter
  - CV tailoring plan
  - Interview prep
  - Skill-gap plan
  - Career roadmap

### Cover Letter Generator

- Standalone cover-letter workflow outside chat.
- Select a CV, role title, company, style, length, and job description.
- Supported styles:
  - Professional
  - Concise
  - Warm and personal
- Supported lengths:
  - Standard
  - Short
- Generates structured cover-letter fields.
- Normalizes unknown fields safely.
- Avoids invented details by prompting the model to use only CV and job-description evidence.
- Preview the generated letter.
- Copy cover-letter text.
- Download the cover letter as PDF.

### Skill-Gap Tracking

- Detect known skills from CV and job-description text.
- Track missing job skills that are not detected in the selected CV.
- Skill gaps are stored per user with unique skill names.
- Skill-gap priorities:
  - High
  - Medium
  - Low
- Skill-gap statuses:
  - Open
  - Learning
  - Done
- Update skill-gap status from the chat sidebar.
- Skill gaps appear in the evaluation dashboard.

### Evaluation Dashboard

- View product and prompt-evaluation metrics.
- Shows totals for:
  - Conversations
  - Messages
  - User messages
  - Assistant replies
  - Feedback
  - Training examples
- Shows active prompt versions.
- Shows observed prompt usage.
- Shows tool-action counts.
- Shows feedback-rating counts.
- Shows skill-gap status counts.
- Shows recent feedback excerpts.
- Download anonymized training data as JSONL.

### Feedback and Training Data

- Collect response feedback from chat messages.
- Store feedback ratings and optional notes.
- Build anonymized training examples from user and assistant message pairs.
- Anonymization replaces:
  - Email addresses
  - Phone numbers
  - URLs
  - User name parts
- JSONL export includes prompt version, tool action, feedback rating, CV usage, and job-description usage.

### PDF Exports

- Download job-match analyses as PDF.
- Download standalone cover letters as PDF.
- Download chat-generated artifacts as PDF.
- PDF builders format structured text, headings, bullets, and cover-letter layouts.

### AI Provider and Error Handling

- Gemini-backed AI provider layer.
- Uses the current Gemini Interactions API by default.
- Optional fallback to the older Generate Content API through configuration.
- Centralized Gemini client setup.
- Configurable Gemini timeout.
- Clear placeholder response when `GEMINI_API_KEY` is missing.
- Classified AI errors for:
  - Blocked outbound socket access
  - General connectivity problems
  - Timeouts
  - Invalid API keys
  - Project or permission problems
  - Invalid model names
  - Quota or rate limits
  - Temporary Google server errors

## Tech Stack

- Python + Flask
- Flask-Login
- Flask-SQLAlchemy
- SQLite for local development
- Google GenAI SDK
- Google AI Studio Gemini API
- PyPDF2 for PDF parsing
- python-docx for DOCX parsing
- ReportLab for PDF generation
- Bootstrap, HTML, CSS, and JavaScript

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
flask --app run.py init-db
flask --app run.py run
```

Then open:

```text
http://127.0.0.1:5000
```

## Environment Variables

Create `.env` from `.env.example` and fill in the values needed for your local setup.

```env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=change-this-in-development
DATABASE_URL=sqlite:///career_assistant.db
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
GEMINI_API_MODE=interactions
GEMINI_TIMEOUT_MS=60000
AI_PROVIDER=gemini
ADMIN_EMAILS=admin@example.com
```

- `SECRET_KEY`: Flask session secret.
- `DATABASE_URL`: Database connection string. Defaults to SQLite.
- `GEMINI_API_KEY`: Required for real AI analysis.
- `GEMINI_MODEL`: Defaults to `gemini-2.5-flash`.
- `GEMINI_API_MODE`: Defaults to `interactions`. Set to `generate_content` to use the older Generate Content API.
- `GEMINI_TIMEOUT_MS`: Defaults to `60000`.
- `AI_PROVIDER`: Defaults to `gemini` for the chatbot provider layer.
- `ADMIN_EMAILS`: Comma-separated email addresses that can access `/admin/evaluations`.

CV and job text may be sent to the configured AI provider when AI features are used.

## Gemini Setup

1. Create a Gemini API key in Google AI Studio:

```text
https://aistudio.google.com/apikey
```

2. Put the key in `.env`:

```env
GEMINI_API_KEY=your_real_key_here
```

3. Restart Flask after changing `.env`.

Use a Gemini API key, not an OAuth token, service-account JSON file, browser token, client secret, or value prefixed with `Bearer`.

## Troubleshooting

### Missing API Key

If `GEMINI_API_KEY` is missing, the app returns a placeholder response instead of crashing.

### Invalid API Key

If Google returns `HTTP 400 API_KEY_INVALID` or `HTTP 401 UNAUTHENTICATED`, replace `GEMINI_API_KEY` with a current Gemini API key from Google AI Studio, save `.env`, and restart Flask.

### Firewall or Socket Errors

If the app reports blocked socket access, allow Python or Flask through your firewall, VPN, antivirus, or Windows network restrictions. Running Flask from a normal terminal can also help if a sandboxed shell is blocking outbound traffic.

### Model Errors

If the app reports that the model cannot be found, update `GEMINI_MODEL` in `.env` to a model available to your Gemini API key.

### Quota or Rate Limits

If the app reports quota or rate limits, wait, check Google AI Studio quota/billing, or switch to a project/model with available capacity.

## Project Structure

```text
app/
  auth/              Registration, login, and logout routes
  main/              Dashboard, chat, CV upload, matching, evaluations, and downloads
  services/          AI, prompts, parsing, PDF generation, evaluation, and skill tracking
  static/            CSS and JavaScript
  templates/         Jinja templates
  __init__.py        Flask application factory
  config.py          App configuration
  models.py          Database models
run.py               Flask entry point and init-db command
requirements.txt     Python dependencies
```

## Main Routes

- `/`: Public landing page.
- `/auth/register`: Register a new user.
- `/auth/login`: Log in.
- `/auth/logout`: Log out.
- `/dashboard`: User dashboard.
- `/cv/upload`: Upload and parse a CV.
- `/match`: Match a CV against a job description.
- `/results/<id>`: View a saved job-match result.
- `/cover-letter`: Generate a standalone cover letter.
- `/chat`: Career chat workspace.
- `/evaluations`: Evaluation dashboard.
- `/evaluations/training-data.jsonl`: Download anonymized JSONL training data.

## Data Models

- `User`: Account and relationships.
- `CV`: Uploaded CV metadata and extracted text.
- `JobDescription`: Saved job descriptions used for matching.
- `AnalysisResult`: AI-generated job-match results.
- `ChatConversation`: Saved chat threads.
- `ChatConversationContext`: Conversation-level context such as attached job descriptions.
- `ChatMessage`: User and assistant chat messages with metadata.
- `ChatFeedback`: Feedback on assistant messages.
- `SkillGap`: Tracked missing skills with status, priority, source, and notes.

## Development Notes

- Initialize the database with `flask --app run.py init-db`.
- Local uploads and SQLite data live under `instance/` by default.
- The app is designed for local development and learning, not production deployment.
- The Flask development server should not be used as a production WSGI server.
