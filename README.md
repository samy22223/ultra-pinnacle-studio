# Ultra Pinnacle AI Studio

An offline AI studio integrating advanced tools across math, AI, development, fashion design, and cross-domain patterns for comprehensive creative and technical workflows.

## Features

- **AI Models**: Pre-loaded offline models (e.g., Llama-2-7B-Chat) for text generation and processing.
- **FastAPI Gateway**: RESTful API for model interactions and encyclopedia access.
- **Authentication**: JWT-based user authentication and session management.
- **Chat Interface**: Real-time conversational AI with multiple model support.
- **Prompt Enhancement**: AI-powered prompt improvement with context from encyclopedia.
- **Code Analysis**: Background processing for code analysis, generation, refactoring, and debugging.
- **File Upload**: Secure file upload capabilities for processing user content.
- **Background Workers**: Asynchronous task processing for long-running operations.
- **Encyclopedia**: Expanded knowledge base covering:
  - Math sequences and algorithms
  - AI techniques and agents
  - Development tools and patterns
  - Fashion design principles
  - Cross-domain integrations
  - Software architecture
  - Machine learning
  - Blockchain & cryptography
- **Web UI**: Modern web interface for easy interaction with all features.
- **Logging**: Comprehensive logging system with file rotation.
- **Health Monitoring**: System health checks and status monitoring.
- **Orchestrator**: Automated workflow management for offline operations.
- **Offline Ready**: Fully self-contained with no internet dependency.

## Prerequisites

- Python 3.12
- Compatible with macOS, Linux, and ARM devices (e.g., Xiaomi Pad 7)

## Installation

1. Extract the `ultra_pinnacle_studio.tar.gz` archive.
2. Navigate to the extracted directory.

## Usage

1. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

2. Start the orchestrator:
   ```bash
   ./scripts/orchestrator/start_orchestrator.sh
   ```

3. Access the API at `http://localhost:8000`

## API Endpoints

### Authentication
- `POST /auth/login`: User login. Accepts `{"username": "string", "password": "string"}` and returns `{"access_token": "jwt_token", "token_type": "bearer"}`.

### System
- `GET /`: Studio status and information
- `GET /health`: System health check with model and task status
- `GET /models`: List available AI models
- `GET /workers`: List available worker scripts

### AI Features
- `POST /enhance_prompt`: Enhance a prompt using AI. Accepts `{"prompt": "string", "model": "optional", "temperature": "optional", "max_tokens": "optional"}` and returns `{"enhanced_prompt": "enhanced version"}`.
- `POST /chat`: Chat with AI model. Accepts `{"message": "string", "conversation_id": "optional", "model": "optional"}` and returns `{"response": "ai_response", "conversation_id": "id"}`.
- `POST /code/{task}`: Code analysis/generation. Task can be "analyze", "generate", "refactor", "debug". Accepts `{"code": "string", "language": "string", "task": "string"}` and returns `{"task_id": "id", "status": "submitted"}`.

### Encyclopedia
- `GET /encyclopedia/list`: List available encyclopedia topics. Returns `{"topics": ["topic1", "topic2", ...]}`.
- `GET /encyclopedia/{topic}`: Get content of a specific encyclopedia topic. Returns `{"topic": "topic", "content": "markdown content"}` or `{"error": "Topic not found"}`.
- `POST /encyclopedia/search`: Search encyclopedia for a query. Accepts `{"query": "search term", "limit": "optional"}` and returns `{"query": "term", "results": [{"topic": "topic", "matches": ["line1", "line2", ...]}]}`.

### File Operations
- `POST /upload`: Upload a file for processing. Requires authentication.
- `GET /tasks/{task_id}`: Get status of a background task.

### Web UI
Access the web interface at `web_ui/index.html` for a user-friendly experience with all features.

## Encyclopedia Access

Encyclopedia files are located in `encyclopedia/` directory and cover comprehensive knowledge across domains:
- `math_sequences.md` - Mathematical sequences, algorithms, and patterns
- `ai_algorithms.md` - AI techniques, agents, and machine learning methods
- `dev_tools.md` - Development tools, patterns, and DevOps practices
- `fashion_design.md` - Fashion design principles and AI applications
- `cross_domain.md` - Cross-domain integrations and collaborative patterns
- `software_architecture.md` - System design, patterns, and architecture principles
- `machine_learning.md` - ML algorithms, deep learning, and model evaluation
- `blockchain_cryptography.md` - Blockchain, crypto primitives, and DeFi concepts

## Components

- **API Gateway**: `api_gateway/main.py` - FastAPI application with authentication, AI models, and encyclopedia
- **Models**: `models/` - Offline AI models (Llama, Stable Diffusion, etc.)
- **Scripts**: `scripts/` - Orchestrator and utility scripts
- **Encyclopedia**: `encyclopedia/` - Domain-specific knowledge base
- **Web UI**: `web_ui/index.html` - Modern web interface
- **Workers**: `api_gateway/workers.py` - Background task processing
- **Auth**: `api_gateway/auth.py` - JWT authentication system
- **Logging**: `api_gateway/logging_config.py` - Comprehensive logging system
- **Tests**: `tests/` - API and integration tests

## Testing

Run the test suite:
```bash
cd ultra_pinnacle_studio
pip install -r requirements.txt
pytest tests/
```

## Configuration

The system is configured via `config.json`:
- Model settings and paths
- Security configuration (JWT secrets)
- Feature toggles
- Directory paths
- Logging levels

## Deployment on Xiaomi Pad 7

1. Transfer `ultra_pinnacle_studio.tar.gz` to the device.
2. Extract using compatible tools.
3. Follow usage instructions above.

## Development

Built with Python, FastAPI, and integrated AI libraries. All dependencies are pre-installed in the virtual environment.

## License

[Specify license if applicable]