# Ultra Pinnacle AI Studio

A comprehensive offline AI development platform featuring local model management, interactive chat interfaces, code analysis, and extensible plugin architecture.

## 🚀 Features

- **🤖 Local AI Model Management**: Load and manage multiple AI models locally
- **💬 Interactive Chat Interface**: Conversational AI with conversation threading
- **🔧 Code Analysis & Generation**: Analyze, refactor, and generate code with AI assistance
- **📚 Knowledge Base**: Integrated encyclopedia with search capabilities
- **📁 Secure File Management**: Upload and manage files with validation
- **📊 Real-time Monitoring**: Health checks, metrics, and performance monitoring
- **🔌 Plugin Architecture**: Extensible system with custom plugins
- **🛡️ Security First**: Rate limiting, input validation, and secure authentication
- **🐳 Container Ready**: Docker and docker-compose support for easy deployment

## 📋 Requirements

- Python 3.12+
- 4GB RAM minimum (8GB recommended)
- 10GB storage minimum
- SQLite (default) or PostgreSQL (production)

## 🛠️ Quick Start

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ultra_pinnacle_studio
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the application**
   ```bash
   python start_server.py
   ```

4. **Access the application**
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Dashboard: http://localhost:8000/dashboard

### Docker Setup

```bash
# Development
docker-compose up

# Production
docker-compose --profile production up -d
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment (development/production) | development |
| `JWT_SECRET` | JWT signing secret | auto-generated |
| `DATABASE_URL` | Database connection URL | sqlite:///./ultra_pinnacle.db |
| `LOG_LEVEL` | Logging level | INFO |

### Configuration Files

- `config.json` - Development configuration
- `config.production.json` - Production configuration

## 📖 API Usage

### Authentication

```bash
# Login to get access token
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "demo123"}'

# Use token in subsequent requests
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/users/profile
```

### AI Chat

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain quantum computing",
    "conversation_id": null,
    "model": "llama-2-7b-chat"
  }'
```

### Code Analysis

```bash
curl -X POST "http://localhost:8000/code/analyze" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def hello(): print(\"Hello World\")",
    "language": "python",
    "task": "analyze"
  }'
```

## 🏗️ Architecture

```
ultra_pinnacle_studio/
├── api_gateway/          # FastAPI application
│   ├── main.py          # Main application
│   ├── config.py        # Configuration management
│   ├── database.py      # Database models and connections
│   ├── auth.py          # Authentication and authorization
│   ├── models.py        # AI model management
│   ├── security.py      # Security middleware and utilities
│   ├── metrics.py       # Monitoring and metrics
│   ├── plugins.py       # Plugin system
│   └── validation.py    # Input validation
├── web_ui/              # Web interface
├── encyclopedia/        # Knowledge base
├── validation_scripts/  # Validation and testing
├── tests/               # Unit tests
├── scripts/             # Utility scripts
└── docs/                # Documentation
```

## 🔒 Security

- JWT-based authentication
- **Advanced Rate Limiting**: Sliding window algorithm with user-based and endpoint-specific limits
- Input sanitization and validation
- SQL injection protection
- XSS prevention
- Secure file upload handling
- CORS configuration

### Rate Limiting

Ultra Pinnacle AI Studio implements comprehensive API rate limiting to protect against abuse while ensuring fair access:

**Features:**
- **Sliding Window Algorithm**: More accurate than fixed windows, prevents burst attacks
- **User-Based Limits**: Different limits for different user types
- **Endpoint-Specific Limits**: Custom limits for sensitive endpoints
- **Burst Allowance**: Short-term high usage allowance
- **Redis Support**: Distributed rate limiting with Redis fallback to in-memory
- **Auto-Adjustment**: Dynamic limit adjustment based on system load
- **Rate Limit Headers**: Standard headers (X-RateLimit-Remaining, X-RateLimit-Reset)
- **Admin Interface**: Web-based management of rate limits
- **Monitoring**: Real-time analytics and reporting

**Default Limits:**
- **Per Minute**: 60 requests
- **Per Hour**: 1000 requests
- **Per Day**: 5000 requests
- **Burst**: 10 requests (10-second window)

**Rate Limit Headers:**
```
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1640995200
X-RateLimit-Limit: 60
```

**Admin Management:**
Access rate limit management at `/admin/rate-limits` (admin users only).

## 📊 Monitoring

Access the monitoring dashboard at `/dashboard` or view metrics at `/metrics`.

### Health Checks

```bash
curl http://localhost:8000/health
```

### Metrics

- System resource usage (CPU, memory, disk)
- Request/response metrics
- AI model performance
- Background task status

## 🔌 Plugins

The system supports extensible plugins for:

- **API Extensions**: Add custom endpoints
- **Processing Plugins**: Custom data processing
- **Storage Plugins**: Alternative storage backends

## 🧪 Testing

### Run Validation Suite

```bash
cd validation_scripts
python comprehensive_validation.py
```

### Run Unit Tests

```bash
python -m pytest tests/ -v
```

## 🚀 Deployment

### Railway (Free Tier)

The project includes Railway deployment configuration for easy hosting.

### Render

Configuration for Render deployment is also included.

### Manual Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ENVIRONMENT=production
export JWT_SECRET=your-secret-key
export DATABASE_URL=postgresql://...

# Start application
uvicorn api_gateway.main:app --host 0.0.0.0 --port 8000
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run validation scripts
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

1. **Segmentation Fault**: Reduce memory usage by avoiding torch imports
2. **Database Connection**: Check DATABASE_URL environment variable
3. **Model Loading**: Ensure model files exist in the models directory
4. **Plugin Issues**: Check plugin initialization logs

### Logs

Application logs are stored in `logs/ultra_pinnacle.log`.

### Support

- Check the documentation in `docs/`
- Run validation scripts for diagnostics
- Check GitHub issues for known problems

---

**Ultra Pinnacle AI Studio** - Bringing AI power to your local development environment.