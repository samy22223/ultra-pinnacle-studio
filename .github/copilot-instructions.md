# Copilot Instructions for Ultra Pinnacle Studio

## Project Overview
Ultra Pinnacle Studio is an offline, modular AI platform for creative and technical workflows. It integrates:
- Local AI models (text, image, code)
- FastAPI-based API gateway
- Web UI and REST endpoints
- Encyclopedia/knowledge base
- Auto-install, domain builder, and universal hosting engines
- Advanced security, monitoring, and plugin systems

## Architecture & Key Components
- `ultra_pinnacle_studio/api_gateway/`: FastAPI app, main entry (`main.py`), authentication (`auth.py`), database (`database.py`), plugins, metrics, logging, security, and feedback.
- `ai_runtimes/`: Local model runners (Llama, Stable Diffusion, etc.), started via shell scripts.
- `web_ui/`: Modern web interface for all features.
- `encyclopedia/`: Markdown files with domain knowledge, used for prompt enhancement and code analysis.
- `auto_install/`, `domain_builder/`, `universal_hosting/`: Automated deployment, domain, and hosting tools with web and CLI interfaces.
- `validation_scripts/`: System validation and health checks.
- `tests/`: API and integration tests.

## Developer Workflows
- **Start API Gateway:**
  ```bash
  python start_server.py
  # or for enhanced mode:
  python start_enhanced_studio.py
  ```
- **Run AI Runtimes:**
  - Llama: `ai_runtimes/llama_service/start_llama_service.sh`
  - Stable Diffusion: `ai_runtimes/sd_automatic/start_auto1111.sh`
- **Web UI:** Open `web_ui/index.html` or access via API at `http://localhost:8000`
- **Testing:**
  ```bash
  pip install -r requirements.txt
  pytest tests/
  # or
  cd validation_scripts && python comprehensive_validation.py
  ```
- **Auto-Install:**
  ```bash
  cd auto_install && python setup_server.py
  # then visit http://localhost:8001
  ```
- **Domain Builder:**
  ```bash
  cd domain_builder && python start_domain_builder.py
  # then visit http://localhost:8002
  ```
- **Universal Hosting:**
  ```bash
  cd universal_hosting && python start_hosting_dashboard.py
  # then visit http://localhost:8003
  ```

## Project Conventions & Patterns
- **Configuration:**
  - Use `config.json` for dev, `config.production.json` for prod. Secrets and environment variables are auto-generated or set in `.env`.
- **Authentication:** JWT-based, endpoints require Bearer tokens.
- **Rate Limiting:** Sliding window, user/endpoint-specific, headers returned.
- **Plugins:** Add to `api_gateway/plugins.py` and register in config.
- **Background Tasks:** Use `api_gateway/workers.py` for async jobs.
- **Logging:** All logs in `logs/`, with rotation and audit trails.
- **Encyclopedia:** Markdown files in `encyclopedia/` are loaded at runtime for prompt enhancement and code analysis.
- **Testing:** Use both `tests/` and `validation_scripts/` for full coverage.

## Integration & External Dependencies
- **Models:** Download LLMs/SD models manually to `ai_runtimes/models/`.
- **Database:** SQLite by default, PostgreSQL for production (set in config).
- **Docker:** Use `docker-compose.yml` for dev, `docker-compose --profile production up -d` for prod.
- **Cloud/Edge:** Universal hosting supports hybrid, local, and cloud deployments.

## Examples
- **Add a new API endpoint:**
  - Implement in `api_gateway/`, register in `main.py`.
- **Add a new AI model:**
  - Place model in `ai_runtimes/models/`, update runner script.
- **Add a new encyclopedia topic:**
  - Add markdown file to `encyclopedia/`, update index if needed.

## References
- See `README.md` (root and submodules) for detailed usage, endpoints, and troubleshooting.
- See `DEPLOYMENT_README.md` for deployment-specific notes.

---
**If any section is unclear or missing, please provide feedback for improvement.**
