# AI-Based Requirement Engineering Assistant

AI-Based Requirement Engineering Assistant is a full-stack web application that analyzes natural language software requirements using Large Language Models (LLMs) and produces structured requirement engineering outputs.

---

## 🚀 Features

- Analyze raw software requirement text
- Generate structured user stories
- Detect ambiguous expressions
- Suggest requirement improvements
- Produce improved requirement text
- Classify requirement types
- Support multiple LLM providers (Gemini, Mock)
- Automatic fallback to mock provider in case of errors

---

## 🧱 Tech Stack

### Backend
- Python
- FastAPI
- Pydantic
- Google Gemini API
- Clean Architecture (layered structure)

### Frontend
- React
- JavaScript
- Fetch API

---

## 📁 Project Structure

ai-requirement-engineering-assistant/
├── backend/
├── frontend/
└── README.md

---

## ⚙️ Requirements

Before running the project, install:

- Python 3.11+
- Node.js (LTS)
- npm
- Git

---

## 📥 1. Clone the Repository

git clone <YOUR_REPOSITORY_LINK>
cd ai-requirement-engineering-assistant

---

## 🖥️ 2. Backend Setup

Go to backend folder:

cd backend

Create virtual environment:

python -m venv venv

Activate virtual environment (Windows PowerShell):

venv\Scripts\activate

If blocked:

Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

Install dependencies:

pip install -r requirements.txt

Create `.env` file inside backend folder:

backend/.env

Add:

GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=

Run backend:

uvicorn main:app --reload

Backend runs at:
http://127.0.0.1:8000

Swagger UI:
http://127.0.0.1:8000/docs

---

## 🌐 3. Frontend Setup

Open a new terminal:

cd frontend

Install dependencies:

npm install

Run frontend:

npm start

Frontend runs at:
http://localhost:3000

---

## ▶️ 4. How to Use

1. Open frontend in browser
2. Enter requirement text

Example:
The system should be fast and user-friendly.

3. Select provider:
- mock → development/testing
- gemini → real AI analysis

4. Click Analyze

---

## 📊 Output

The system returns:

- User Story
- Requirement Type
- Ambiguities
- Suggestions
- Improved Text
- Provider Info
- Warnings / Errors (if any)

---

## 🤖 Provider Behavior

Mock Provider:
- No API usage
- Safe for development
- Instant response

Gemini Provider:
- Real AI analysis
- Requires API key
- May depend on quota/billing

---

## 🔁 Fallback Mechanism

If selected provider fails:

- System automatically switches to mock provider
- isFallback = true
- Warning and error messages are returned

---

## 📡 API Endpoint

POST /api/v1/requirements/analyze

Example request:

{
  "text": "The system should be fast and user-friendly.",
  "provider": "mock"
}

---

## ⚠️ Common Issues

npx is not recognized:
- Install Node.js
- Restart terminal / VS Code

uvicorn not recognized:
- Activate virtual environment

API key errors:
- Check .env file
- Restart backend

Failed to fetch:
- Backend not running
- CORS issue

Gemini errors:
- Quota exceeded
- Billing not enabled

---

## 🧠 Development Notes

- Default provider is mock
- Backend uses layered architecture:
  API → Use Case → Service → LLM Provider

---

## 🔮 Future Improvements

- OpenAI integration
- NLP-based ambiguity detection
- Grammarly-like UI highlighting
- Multi-LLM comparison

---

## 👨‍💻 Author

