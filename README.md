# AI Requirement Engineering Assistant

AI Requirement Engineering Assistant is a full-stack web application for analyzing natural language software requirements with LLM support and NLP-based pre-analysis.

The system can generate user stories, detect ambiguities, suggest improvements, classify requirement type, and produce alternative improved requirement texts.

---

## Features

- Analyze natural language software requirements
- Generate user stories
- Detect ambiguous requirement expressions
- Suggest requirement improvements
- Generate improved requirement text
- Generate multiple improved text alternatives
- Classify requirement type
- Support multiple providers:
  - Mock
  - Gemini
- Automatic fallback to mock provider when selected provider fails
- V1, V2, and V3 analysis modes
- NLP-based pre-analysis for V2
- Type-aware semantic requirement analysis for V3
- Analysis timing metadata
- Clean result copy action for easier test comparison

---

## Analysis Versions

### V1 - Direct LLM Analysis

V1 uses the cleaned requirement text directly.

Flow:

```text
Raw text
-> Text cleaning
-> V1 prompt generation
-> LLM provider
-> Analysis response
```

V1 does not run NLP pre-analysis.

### V2 - NLP Enhanced Analysis

V2 uses NLP-based pre-analysis before prompt generation.

Flow:

```text
Raw text
-> Text cleaning
-> NLP pre-analysis
-> V2 prompt generation
-> LLM provider
-> Analysis response
```

V2 pre-analysis detects:

- Known ambiguity terms
- Linguistic ambiguity candidates
- Semantic similarity support for NLP-derived candidates
- Reference ambiguities
- Measurement ambiguities
- Measurement context observations
- Measurable expressions

### V3 - Type-Aware Enhanced Analysis

V3 extends V2 with semantic requirement type analysis.

Flow:

```text
Raw text
-> Text cleaning
-> NLP pre-analysis
-> Semantic requirement type analysis
-> V3 prompt generation when type context is reliable
-> LLM provider
-> Analysis response
```

V3 can detect:

- Primary requirement type
- Possible secondary requirement types
- Type-aware observations
- Semantic confidence for requirement type analysis

If V3 does not find reliable type context, it falls back to the V2 prompt. If V2 also has no meaningful pre-analysis findings, the system uses the V1 direct prompt.

---

## Tech Stack

### Backend

- Python 3.12
- FastAPI
- Pydantic
- spaCy
- spaCy Transformers
- Transformers
- Torch
- Google Gemini API
- python-dotenv

### Frontend

- React
- JavaScript
- Fetch API

---

## Project Structure

```text
ai-requirement-engineering-assistant/
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |-- application/
|   |   |-- core/
|   |   |-- domain/
|   |   `-- infrastructure/
|   |-- main.py
|   |-- requirements.txt
|   `-- .env
|-- frontend/
|   |-- src/
|   `-- package.json
|-- .gitignore
`-- README.md
```

---

## Requirements

Install these before running the project:

- Python 3.12
- Node.js LTS
- npm
- Git

Check Python version:

```powershell
py -3.12 --version
```

---

## Clone Repository

```powershell
git clone <YOUR_REPOSITORY_LINK>
cd ai-requirement-engineering-assistant
```

---

## Backend Setup

Go to backend folder:

```powershell
cd backend
```

Create virtual environment with Python 3.12:

```powershell
py -3.12 -m venv venv
```

Activate virtual environment:

```powershell
.\venv\Scripts\activate
```

If PowerShell blocks script execution:

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Install dependencies:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Verify spaCy installation:

```powershell
.\venv\Scripts\python.exe -c "import spacy; print(spacy.__version__)"
```

Verify spaCy model:

```powershell
.\venv\Scripts\python.exe -c "import spacy; nlp = spacy.load('en_core_web_trf'); print(nlp.pipe_names)"
```

Expected output should include:

```text
transformer
tagger
parser
attribute_ruler
lemmatizer
ner
```

Cache the semantic similarity model used by V2 and V3:

```powershell
.\venv\Scripts\python.exe -c "from transformers import AutoTokenizer, AutoModel; model='sentence-transformers/all-mpnet-base-v2'; AutoTokenizer.from_pretrained(model); AutoModel.from_pretrained(model); print('semantic model cached')"
```

V2 and V3 can still run if this model is not cached, but semantic similarity findings and requirement type analysis will be skipped until the model is available locally.

---

## Environment Variables

Create a `.env` file inside the backend folder:

```text
backend/.env
```

Add:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Mock provider does not require an API key.

---

## Run Backend

From backend folder:

```powershell
.\venv\Scripts\uvicorn.exe main:app --reload
```

Backend runs at:

```text
http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

Note:

The `google.generativeai` package may show a deprecation warning. This is currently only a warning and does not block the application.

---

## Frontend Setup

Open a new terminal and go to frontend folder:

```powershell
cd frontend
```

Install dependencies:

```powershell
npm install
```

Run frontend:

```powershell
npm start
```

Frontend runs at:

```text
http://localhost:3000
```

---

## How to Use

1. Open the frontend in browser.
2. Enter a requirement text.
3. Select provider:
   - Mock
   - Gemini
4. Select analysis version:
   - V1
   - V2
   - V3
5. Click Analyze.

Example requirement:

```text
The system should be fast and respond within 2 seconds.
```

---

## Output

The system returns:

- Provider info
- User story
- Requirement type
- Ambiguities
- Suggestions
- Improved text
- Improved text options
- Generated prompt
- Analysis timing metadata
- Pre-analysis details for V2 and V3

---

## V2 Pre-analysis Output

V2 can return:

- Candidate ambiguities
- Confirmed ambiguities
- Rejected candidates
- Reference ambiguities
- Measurement ambiguities
- Measurement contexts
- Measurable expressions
- Semantic findings

Example:

```text
The system should be fast and respond within 2 seconds.
```

Possible V2 pre-analysis:

```text
Candidate ambiguity:
- fast

Rejected candidate:
- fast, because within 2 seconds provides measurable context

Measurement ambiguities:
- statisticalTarget
- loadCondition
- measurementBoundary
```

Measurement context observations are supporting data for the LLM, not direct ambiguity findings. They can include:

- load context, such as `5000 concurrent users`
- statistical target, such as `average`
- measured item, such as `average page response`
- time target, such as `below 2 seconds`
- related action, such as `process checkout requests`
- condition phrase, such as `under peak load`

---

## V3 Type-aware Output

V3 includes all V2 pre-analysis output and can additionally return:

- Requirement type analysis
- Primary requirement type
- Possible secondary requirement types
- Type-aware observations
- Semantic confidence

Example:

```text
Type Analysis
Detected Type: Safety (0.43)

Type Observations
- safe state: a safe state (0.57)
```

Low-confidence type analysis may be shown in the frontend as a possible type, but it is not added to the LLM prompt.

---

## API Endpoint

```text
POST /api/v1/requirements/analyze
```

Example request:

```json
{
  "text": "The system should be fast and respond within 2 seconds.",
  "provider": "mock",
  "analysisVersion": "v2"
}
```

Example providers:

```text
mock
gemini
```

Example analysis versions:

```text
v1
v2
v3
```

---

## Provider Behavior

### Mock Provider

- Does not call external APIs
- Does not require API key
- Useful for development and frontend testing
- Returns a fixed response

### Gemini Provider

- Calls Google Gemini API
- Requires `GEMINI_API_KEY`
- Produces real LLM analysis
- May depend on quota or billing settings

---

## Fallback Behavior

If the selected provider fails:

- The system automatically falls back to mock provider
- `isFallback` becomes `true`
- Warning and error details are returned in the response

---

## Common Issues

### uvicorn is not recognized

Use the virtual environment executable:

```powershell
.\venv\Scripts\uvicorn.exe main:app --reload
```

### spaCy model cannot be loaded

Reinstall backend dependencies:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Then verify:

```powershell
.\venv\Scripts\python.exe -c "import spacy; spacy.load('en_core_web_trf'); print('ok')"
```

### Failed to fetch

Check:

- Backend is running
- Frontend is running
- Backend URL is `http://127.0.0.1:8000`
- CORS settings include frontend port

### Gemini errors

Check:

- `.env` file exists in backend folder
- `GEMINI_API_KEY` is correct
- Backend was restarted after editing `.env`
- Gemini quota/billing is available

### V2 semantic findings are empty

Check whether the semantic similarity model is cached:

```powershell
.\venv\Scripts\python.exe -c "from transformers import AutoTokenizer, AutoModel; model='sentence-transformers/all-mpnet-base-v2'; AutoTokenizer.from_pretrained(model, local_files_only=True); AutoModel.from_pretrained(model, local_files_only=True); print('semantic model available')"
```

If it is not available, run the semantic model cache command from the backend setup section.

### Frontend build permission error on Windows

If `npm run build` fails with a permission error for `frontend/build`, delete the generated build folder and run build again.

---

## Development Notes

Current simplified backend flow:

```text
API Controller
-> AnalysisService
-> TextProcessingPipeline
-> version-specific preparation
-> PromptBuilder
-> LLM Provider
-> Response
```

V2 pre-analysis flow:

```text
PreAnalysisService
-> spaCy NLP analysis
-> KnownAmbiguityDetector
-> LinguisticAmbiguityDetector
-> SemanticSimilarityAnalyzer
-> ReferenceAmbiguityDetector
-> MeasurementAmbiguityDetector
-> MeasurementContextExtractor
-> PreAnalysisResult
```

V3 type analysis flow:

```text
PreAnalysisResult
-> RequirementTypeAnalyzer
-> requirement_types.json
-> semantic similarity scoring
-> primary/secondary type analysis
-> type-aware observations
-> V3 prompt context when reliable
```

---

## Updating an Existing Local Copy

If you already cloned the repository before this refactor, update your local copy:

```powershell
git pull
```

Then update backend dependencies:

```powershell
cd backend
.\venv\Scripts\activate
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Verify or cache the NLP models:

```powershell
.\venv\Scripts\python.exe -c "import spacy; spacy.load('en_core_web_trf'); print('spacy model available')"
.\venv\Scripts\python.exe -c "from transformers import AutoTokenizer, AutoModel; model='sentence-transformers/all-mpnet-base-v2'; AutoTokenizer.from_pretrained(model); AutoModel.from_pretrained(model); print('semantic model cached')"
```

Restart the backend and frontend after updating:

```powershell
.\venv\Scripts\uvicorn.exe main:app --reload
```

In a separate terminal:

```powershell
cd frontend
npm install
npm start
```

---

## Future Work

Planned next steps:

- Review V1/V2 prompt fairness
- Evaluate a fine-tuned BERT/transformer model trained on a requirement ambiguity dataset
- Improve rate-style measurement gap detection
- Improve type-specific ambiguity dimensions
- Improve security access-control pre-analysis
- Improved frontend comparison between versions
- Multi-agent feedback/review flow in later versions
