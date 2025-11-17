# Contract Clause Extractor

FastAPI service that extracts and structures legal clauses from contracts using OpenAI LLM.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API key

### Setup

1. **Create `.env` file** in project root:
```bash
OPENAI_API_KEY=your-api-key-here
JWT_SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite+aiosqlite:///./data/contracts.db
```

2. **Start the application**:
```bash
docker-compose up --build
```

3. **Access the app**:
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

## Usage

### Web Interface
1. Open http://localhost:3000
2. Register/Login
3. Upload PDF, DOCX, or TXT contract files
4. View extracted clauses

### API
```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","password":"test123","full_name":"Test User"}'

# Login & get token
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@test.com&password=test123" | jq -r '.access_token')

# Upload contract
curl -X POST http://localhost:8000/api/extract \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@contract.pdf"

# List extractions
curl http://localhost:8000/api/extractions \
  -H "Authorization: Bearer $TOKEN"
```

## Running Tests

```bash
# Rebuild containers to include test mounts
docker-compose down && docker-compose up --build -d

# Run tests
docker exec contract_extractor_api python -m pytest tests/ -v

# With coverage
docker exec contract_extractor_api python -m pytest tests/ --cov=app --cov-report=term
```

### Demo script (`demo.py`)

If you want to validate the full workflow quickly, run the bundled demo script. It walks through registration/login, contract upload, extraction retrieval, and listing results.

```bash
# Ensure the stack is running
docker-compose up -d

# Run the demo with your own contract
python demo.py samples/sample_contract.txt
```

The script automatically creates a temporary user, checks the API health, uploads the provided file, and prints a concise summary of each extracted clause.

## Architecture

### Stack
- **Backend**: FastAPI + SQLAlchemy (async) + SQLite
- **Frontend**: React + Vite
- **Auth**: JWT tokens + bcrypt password hashing
- **LLM**: OpenAI GPT-4o-mini
- **Document Processing**: PyMuPDF (PDF), python-docx (DOCX), native (TXT)
- **Deployment**: Docker Compose

### Database Schema
```
users
├── id (UUID, PK)
├── email (unique)
├── hashed_password
└── full_name

extractions
├── id (UUID, PK)
├── user_id (FK → users.id)
├── filename
├── file_type (pdf/docx/txt)
├── status (processing/completed/failed)
└── created_at

clauses
├── id (UUID, PK)
├── extraction_id (FK → extractions.id)
├── clause_type (e.g., payment_terms, termination)
├── title
├── content
├── order
└── extra_data (JSON)
```

### API Endpoints
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/register` | POST | No | Register new user |
| `/api/auth/login` | POST | No | Login & get JWT token |
| `/api/extract` | POST | Yes | Upload & extract clauses |
| `/api/extractions` | GET | Yes | List all extractions (paginated) |
| `/api/extractions/{id}` | GET | Yes | Get specific extraction |

## Design Decisions

### LLM Integration
- **Model**: OpenAI GPT-4o-mini (cost-effective, sufficient accuracy)
- **Temperature**: 0.1 (consistent, factual output)
- **Prompt**: Structured JSON output with predefined clause types
- **Error Handling**: Failed extractions marked in DB, not deleted

### Authentication
- **JWT tokens** for stateless auth (24h expiration)
- **Bcrypt** for password hashing (handles 72-byte limit)
- **All extraction endpoints** require authentication
- Users can only access their own extractions

### Async Architecture
- **FastAPI async** for I/O-bound operations
- **SQLAlchemy async** with aiosqlite
- **Non-blocking** LLM API calls
- Better resource utilization for concurrent requests

### File Processing
- **In-memory** processing (suitable for <10MB contracts)
- **Text-based PDFs** only (no OCR for scanned docs)
- **Supported formats**: PDF, DOCX, TXT

### Frontend
- **React** with hooks for state management
- **Black/white design** (clean, professional)
- **JWT token** stored in localStorage
- **Real-time updates** after extraction

## Assumptions

1. Contracts are <10MB, <100 pages
2. PDFs are text-based (not scanned images requiring OCR)
3. Moderate load (<10 simultaneous uploads)
4. OpenAI API is accessible and responsive
5. Contracts are in English
6. Users manage their own credentials (no SSO/OAuth)
7. Single-tenant deployment (no organizations)


## Project Structure

```
task3/
├── app/
│   ├── api/
│   │   ├── auth.py              # Authentication endpoints
│   │   └── extraction.py        # Extraction endpoints
│   ├── models/
│   │   ├── user.py              # User model
│   │   └── extraction.py        # Extraction & Clause models
│   ├── schemas/
│   │   ├── auth.py              # Auth schemas
│   │   └── extraction.py        # Extraction schemas
│   ├── services/
│   │   ├── auth_service.py      # JWT & password hashing
│   │   ├── document_processor.py # PDF/DOCX/TXT extraction
│   │   └── llm_service.py       # OpenAI integration
│   ├── database/
│   │   └── __init__.py          # SQLAlchemy setup
│   ├── config.py                # Configuration
│   └── main.py                  # FastAPI app
├── frontend/
│   └── src/
│       ├── pages/               # React pages
│       ├── services/api.js      # API client
│       └── App.jsx              # Root component
├── tests/
│   ├── test_api.py              # API endpoint tests
│   ├── test_auth_service.py     # Auth tests
│   └── test_document_processor.py # Document processing tests
├── .env                         # Backend environment variables
├── docker-compose.yml           # Multi-container setup
├── Dockerfile                   # Backend container
├── requirements.txt             # Python dependencies
└── demo.py                      # E2E demo script
```

## Troubleshooting

**Containers won't start:**
```bash
docker-compose down
docker-compose up --build
```

**Can't login/register:**
- Check backend is running: http://localhost:8000/docs
- Check browser console for errors
- Verify `.env` file exists with `JWT_SECRET_KEY`

**File upload fails:**
- Ensure you're logged in
- Check file is PDF/DOCX/TXT
- Verify OpenAI API key is valid and has credits
- Check backend logs: `docker-compose logs api`

**Tests fail:**
- Rebuild containers: `docker-compose down && docker-compose up --build`
- Tests directory must be mounted in container