# AI Career Assistant

A Flask web application for CV analysis, job matching, feedback on strong and weak points, and cover letter support.

The app also includes a logged-in career chatbot that can use a student's latest CV context, save conversation history, and collect response feedback.

## Tech Stack

- Python + Flask
- Flask-Login
- Flask-SQLAlchemy
- SQLite for development
- Google AI Studio Gemini API integration
- PyPDF2 and python-docx for CV parsing
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

Then open `http://127.0.0.1:5000`.

## Environment Variables

- `SECRET_KEY`: Flask session secret.
- `DATABASE_URL`: Database connection string. Defaults to SQLite.
- `GEMINI_API_KEY`: Required for real AI analysis.
- `GEMINI_MODEL`: Defaults to `gemini-2.5-flash`.
- `AI_PROVIDER`: Defaults to `gemini` for the chatbot provider layer.

If `GEMINI_API_KEY` is missing, the app returns a clear placeholder response instead of crashing.

## Project Structure

```text
app/
  auth/              Authentication routes
  main/              Core app routes
  services/          AI and file parsing helpers
  static/            CSS and JavaScript
  templates/         Jinja templates
  __init__.py        Application factory
  config.py          Settings
  models.py          Database models
run.py               Flask entry point
requirements.txt     Python dependencies
```
