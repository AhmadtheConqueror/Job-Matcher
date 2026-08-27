# AI Career Assistant Chatbot Implementation Plan

## Purpose

Build a dedicated career-assistant chatbot inside the existing Flask app. The chatbot should feel like the main assistant for the product: it should understand the logged-in student, use their saved CV where appropriate, answer career questions, and eventually trigger existing app actions such as CV analysis and cover-letter generation.

The first version should not try to train a model from scratch. The practical path is to create an assistant layer with strong instructions, user-specific context, conversation history, feedback collection, evaluations, and later optional fine-tuning if we collect enough high-quality examples.

## Product Vision

The chatbot becomes the student's career coach inside the app.

Students should be able to ask things like:

- "Do I qualify for this internship?"
- "What should I improve in my CV?"
- "Make this cover letter sound more natural."
- "What skills am I missing for this role?"
- "Prepare me for an interview for this job."
- "Use my latest CV and tell me what jobs fit me."

The chatbot should not be a generic AI box. It should be grounded in:

- The logged-in user's profile
- Uploaded CVs
- Saved job descriptions
- Previous analyses
- Existing app tools
- A strict career-assistant behavior policy

## Current App Baseline

The app currently has:

- Flask application factory in `app/__init__.py`
- Auth with Flask-Login
- User, CV, JobDescription, and AnalysisResult models in `app/models.py`
- CV upload and parsing
- Job matching with Gemini
- Cover-letter generation with structured rendering and PDF export
- SQLite development database
- Bootstrap-based templates and vanilla JavaScript

This is a good base. The chatbot can be added without replacing the existing features.

## Recommended Direction

Start with a provider-neutral chatbot service. The app can keep Gemini for existing generation, but the chatbot layer should be designed so the AI provider can be swapped later.

Recommended architecture:

```text
Browser chat UI
  -> Flask /api/chat endpoint
  -> Load logged-in user context
  -> Add assistant instructions
  -> Send message to AI provider
  -> Save user and assistant messages
  -> Return response to browser
```

Important rule:

Never call the AI provider directly from browser JavaScript. API keys must stay on the Flask server.

## What "Training" Means For This Project

There are four levels of "training." We should do them in this order.

### Level 1: Instructions

Give the chatbot a central instruction prompt that defines its role, tone, boundaries, and behavior.

This is the first and most important layer.

### Level 2: Context

The app should dynamically provide useful student context:

- Name
- Uploaded CV summary
- Skills found in the CV
- Education
- Projects
- Work experience
- Recent job description if relevant
- Previous analysis summaries

This makes the chatbot feel trained on the student without actually training a model.

### Level 3: Feedback And Evaluation

Store feedback on chatbot answers:

- Helpful / not helpful
- User corrections
- Regenerated answers
- Accepted cover letters
- Edited final letters

Use this data to improve prompts and test future changes.

### Level 4: Fine-Tuning

Fine-tuning should come later, after we have a strong dataset of approved examples. Fine-tuning is useful for repeated style and behavior patterns, but it should not be the first solution for personal student data. Personal CV facts should come from context/retrieval, not from permanently training them into a model.

## MVP Scope

Build the first version with:

- Chat page
- Conversation history
- Logged-in-user access control
- Chatbot service
- Central assistant instructions
- Automatic use of the student's latest CV
- Ability to paste a job description into chat
- Clean loading state
- Error handling
- Feedback buttons

Do not add tool-calling in the first pass unless the basic chat experience is already stable.

## Phase Plan

### Phase 1: Data Model

Add database tables for conversations and messages.

Proposed models:

```python
class ChatConversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(180), nullable=False, default="New chat")
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("chat_conversation.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    metadata_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
```

Roles:

- `user`
- `assistant`
- `system_context`
- `tool`

Add feedback later:

```python
class ChatFeedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey("chat_message.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    rating = db.Column(db.String(20), nullable=False)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
```

Implementation note:

The current app uses `db.create_all()`. Before this grows further, add `Flask-Migrate` so schema changes are safer.

### Phase 2: Chat UI

Add a new page:

- Route: `GET /chat`
- Template: `app/templates/chat.html`
- JavaScript: extend `app/static/js/app.js` or create `app/static/js/chat.js`
- Navigation link: `Chat`

UI requirements:

- Left side: recent conversations
- Main area: message thread
- Bottom composer
- Send button
- New chat button
- Loading state while the assistant responds
- Copy button on assistant messages
- Feedback buttons on assistant messages

Keep the design work-focused and simple. This should feel like a useful dashboard tool, not a marketing page.

### Phase 3: Chat API

Add JSON endpoints:

```text
GET  /api/chat/conversations
POST /api/chat/conversations
GET  /api/chat/conversations/<id>
POST /api/chat
POST /api/chat/messages/<id>/feedback
```

`POST /api/chat` request:

```json
{
  "conversation_id": 1,
  "message": "Can you tell me if my CV fits this internship?",
  "include_latest_cv": true
}
```

Response:

```json
{
  "conversation_id": 1,
  "message_id": 14,
  "reply": "Your CV has a good foundation for this internship...",
  "suggested_actions": [
    "Analyze fit",
    "Generate cover letter",
    "Prepare interview questions"
  ]
}
```

Access control:

- A user must only see their own conversations.
- A user must only send CV/job data attached to their own account.
- All chat routes must require login.

### Phase 4: Assistant Instructions

Create a central instruction builder, for example:

```text
You are the AI Career Assistant for a career-development platform for students,
graduates, and early-career professionals.

Your purpose is to help users make better career decisions and produce stronger
job applications.

Be supportive, practical, and professional.
Do not simply agree with the user.
Give constructive feedback when the application, CV, experience, or strategy
could be stronger.
Explain why you recommend something.
Keep ordinary responses concise unless the user asks for detail.

Use supplied student context to personalize advice.
Never invent education, experience, skills, achievements, employers, dates,
certifications, projects, metrics, or portfolio links.

Clearly distinguish between:
- Demonstrated skills
- Transferable skills
- Required skills not yet demonstrated

When a job description is provided:
1. Identify the most important requirements.
2. Compare them with the student's CV or profile.
3. Highlight strong matches.
4. Identify meaningful gaps.
5. Recommend positioning and next actions.

Avoid generic AI phrases such as:
- highly motivated individual
- results-oriented professional
- dynamic professional
- proven track record
- leverage my skills
- passionate about

Offer next actions when useful:
- Tailor my CV
- Generate a cover letter
- Analyze my fit
- Prepare interview questions
- Identify skill gaps
```

This should live in code, not be typed by the user each time.

Suggested file:

```text
app/services/chat_prompts.py
```

### Phase 5: Student Context Builder

Create a service that builds compact context for the assistant.

Suggested file:

```text
app/services/student_context.py
```

It should gather:

- User name
- Latest CV filename
- Latest CV text summary or relevant excerpts
- Recent job analyses
- Recently used job descriptions

Keep context short at first. Do not dump every full CV and every previous message into every request.

Example internal context:

```text
STUDENT CONTEXT
Name: Ahmad Isah Bello
Latest CV: Ahmad_Isah_Bello_Resume_.pdf
Known skills from CV: Python, Flask, SQL, JavaScript, troubleshooting
Relevant experience: SIWES IT support, inventory system project
```

Privacy rule:

Show the user when CV context is being used, and allow them to send a message without CV context.

### Phase 6: Provider Layer

Create one service interface so the app is not locked to a single AI provider.

Suggested file:

```text
app/services/chatbot.py
```

Initial functions:

```python
def generate_chat_reply(user, conversation, user_message, include_latest_cv=True):
    ...
```

Possible provider files:

```text
app/services/providers/gemini_provider.py
app/services/providers/openai_provider.py
```

Environment variables:

```text
AI_PROVIDER=gemini
GEMINI_API_KEY=...
GEMINI_MODEL=...
OPENAI_API_KEY=...
OPENAI_MODEL=...
```

This lets the app keep Gemini now and test OpenAI later without rewriting the chatbot.

### Phase 7: Tool Actions

After chat is stable, give the chatbot controlled access to app actions.

Potential tools:

- `get_latest_cv()`
- `analyze_job_match(cv_id, job_description)`
- `generate_cover_letter(cv_id, role, company, job_description, style, length)`
- `prepare_interview_questions(cv_id, job_description)`
- `identify_skill_gaps(cv_id, job_description)`

The assistant should never directly modify user files without confirmation.

Suggested flow:

1. User says: "Generate a cover letter for this internship."
2. Assistant asks for missing role/company/job description if needed.
3. Assistant proposes action.
4. User confirms.
5. Backend calls the existing cover-letter generator.
6. Chat shows the generated result and links to download PDF.

### Phase 8: Training Data Collection

Add lightweight feedback collection from day one.

Store:

- User prompt
- Assistant answer
- Whether CV context was used
- Tool actions used
- Feedback rating
- User correction
- Final accepted output

Do not fine-tune on private student data without explicit consent.

Useful labels:

- `helpful`
- `not_helpful`
- `too_generic`
- `invented_fact`
- `too_long`
- `bad_formatting`
- `wrong_tone`
- `excellent`

This becomes the training/evaluation dataset.

### Phase 9: Evaluation

Before changing prompts or models, create a small test set.

Example eval cases:

- Student asks if they qualify for a role with obvious gaps.
- Student asks for a cover letter with no company name.
- Student asks the bot to invent experience.
- Student asks for CV advice with weak bullet points.
- Student asks for interview questions from a job description.
- Student asks a vague career question.

Each test should check:

- Did the answer avoid invented facts?
- Did it use CV evidence?
- Did it identify gaps honestly?
- Was it clear and practical?
- Was it concise?
- Did it offer useful next actions?
- Did it avoid generic AI language?

Use these tests whenever:

- The central prompt changes
- The model changes
- Tool-calling is added
- The CV context builder changes

### Phase 10: Optional Fine-Tuning

Only consider fine-tuning after:

- The chatbot has a stable prompt
- We have many reviewed examples
- We know exactly what behavior prompting/context cannot solve
- Users have consented to use their data for training, or the data is anonymized

Fine-tuning is best for style and repeated task behavior. It is not the right way to store individual student facts. Student facts should come from the database and context builder.

## OpenAI Option

If we switch or add OpenAI later, the Responses API is a good fit because official OpenAI documentation describes it as supporting text/JSON outputs, conversation state, and model access to tools such as file search and custom function calls.

OpenAI's documentation also includes platform support for evals and fine-tuning jobs. That maps well to the plan above:

- Responses API for chat and tool-calling
- File search or app-managed retrieval for CV/job context
- Evals for testing answer quality
- Fine-tuning later, only if we have reviewed examples and consent

References:

- OpenAI Responses API: https://developers.openai.com/api/reference/cli/resources/responses/methods/create
- OpenAI tools/function calling overview: https://platform.openai.com/docs/quickstart/make-your-first-api-request
- OpenAI evals API reference: https://developers.openai.com/api/reference/resources/evals/methods/delete
- OpenAI fine-tuning API reference: https://platform.openai.com/docs/api-reference/fine-tuning/resume

## Security And Privacy Requirements

The chatbot will handle sensitive student data, so this must be designed carefully.

Requirements:

- Keep API keys only on the server.
- Never expose provider keys in JavaScript.
- Scope all conversations and CV access by `current_user.id`.
- Add user-facing notice when CV/job text may be sent to the AI provider.
- Do not send more CV text than needed.
- Log provider errors, but do not log full CV text or full job descriptions.
- Allow users to delete conversations.
- Add a future setting to disable using CV context by default.
- Do not use chat history for training unless the user has consented.

## Suggested File Changes

New files:

```text
app/templates/chat.html
app/services/chatbot.py
app/services/chat_prompts.py
app/services/student_context.py
app/services/providers/__init__.py
app/services/providers/gemini_provider.py
app/static/js/chat.js
```

Updated files:

```text
app/models.py
app/main/routes.py
app/templates/base.html
app/static/css/styles.css
requirements.txt
README.md
```

Optional later:

```text
migrations/
tests/
```

## User Experience Details

Chat page layout:

- Header: "Career Assistant"
- Left panel: conversation list
- Main panel: chat messages
- Bottom input: message composer
- Toggle: "Use my latest CV"
- Button: "New chat"
- Assistant message actions: copy, helpful, not helpful
- Suggested actions under messages

Suggested starter prompts:

- "Review my latest CV"
- "Do I match this job?"
- "Prepare interview questions"
- "Improve my cover letter"
- "What roles should I apply for?"

## First Build Checklist

- [x] Add chat models.
- [x] Add database migration or update init flow.
- [x] Add `/chat` page.
- [x] Add `/api/chat` endpoint.
- [x] Add conversation list endpoint.
- [x] Add message history endpoint.
- [x] Add central assistant instructions.
- [x] Add student context builder.
- [x] Add Gemini-backed chatbot provider first.
- [x] Add provider abstraction for later OpenAI support.
- [x] Add feedback endpoint.
- [x] Add copy button for assistant messages.
- [x] Add delete conversation button.
- [x] Add chat-triggered cover-letter generation.
- [x] Add chat-triggered CV tailoring plan export.
- [x] Add interview preparation chat action.
- [x] Add skill-gap tracking and status updates.
- [x] Add career roadmap chat action.
- [x] Add loading state.
- [x] Add privacy notice.
- [x] Add tests for user access control.
- [x] Add tests for conversation persistence.
- [x] Add tests for provider failure behavior.

## Definition Of Done For V1

V1 is done when:

- A logged-in user can open `/chat`.
- The user can start a new conversation.
- Messages save to the database.
- The assistant replies using the central career-assistant instructions.
- The assistant can use the user's latest CV when the toggle is enabled.
- The assistant does not invent unsupported experience.
- The assistant can discuss a pasted job description.
- The user can copy assistant responses.
- The user can rate responses.
- A user cannot access another user's conversations.
- Provider errors show a clean warning instead of raw stack traces.

## Version Roadmap

### V1

Career chat with conversation history and optional latest-CV context.

### V1.1

Better student context builder with CV summaries and recent analysis summaries.

Status: Implemented. The app now extracts a compact latest-CV context locally,
including detected skills, education, experience, projects, certifications, and
general CV evidence. The chat UI also shows which CV context is active before
messages are sent.

### V1.2

Job-description-aware chat with structured fit analysis.

Status: Implemented. Users can paste a job description into the chat, keep it
attached to the active conversation, clear it when needed, and receive
job-aware answers organized around fit summary, strong matches, gaps,
positioning, and next actions.

### V1.3

Chatbot can trigger the existing cover-letter generator after user confirmation.

Status: Implemented. Chat responses can show a Generate cover letter action.
After the user confirms role, company, style, and length, the backend calls the
existing cover-letter generator, stores the draft in the conversation, and shows
a PDF download link on the generated assistant message.

### V1.4

Chatbot can suggest CV tailoring edits and export a revised CV plan.

Status: Implemented. Chat responses can show a Create CV tailoring plan action.
After the user confirms optional role and company details, the backend uses the
latest CV and active job description to generate a structured tailoring plan,
stores it in the conversation, and provides a PDF download link.

### V2

Career roadmap, skill-gap tracking, interview preparation mode, and richer tool actions.

Status: Implemented. Chat now includes confirmed actions for interview
preparation, skill-gap planning, and career roadmap generation. Skill gaps are
tracked as user-level records with status updates, and generated V2 artifacts
can be downloaded as PDFs from their chat messages.

### V3

Evaluation dashboard, prompt versioning, anonymized training dataset, and optional fine-tuning.

Status: Implemented. The app now records active prompt versions in new chat and
tool-action metadata, exposes an evaluation dashboard, summarizes tool usage,
feedback, prompt usage, and skill-gap status, and exports anonymized JSONL
training/evaluation examples for future review. Fine-tuning remains optional
and should only happen after explicit consent and enough high-quality examples.

## Review Questions

- Should V1 continue using Gemini first, or should we add OpenAI as a second provider immediately?
- Should the chatbot use the latest CV by default, or ask every time?
- Should conversations be deletable in V1? Yes. Implemented with a sidebar
  delete button and an owner-only API route.
- Should feedback be visible only to developers, or should users see that their feedback improves the assistant?
- Should the chatbot be the main app homepage after login, or stay as a separate navigation item?

## Recommendation

Build V1 with Gemini first because the current app already has Gemini working. However, create a provider layer from the start so switching to OpenAI, adding tool-calling, or testing multiple models later does not require rewriting the app.

The most important idea is this:

Do not train student facts into the model. Store student facts in the app, retrieve them when needed, and send only the relevant context for each request. Train the assistant's behavior through strong instructions, saved feedback, evals, and only later optional fine-tuning.
