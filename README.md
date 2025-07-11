# Japanese Government Procurement Automation System

An automated system for crawling, analyzing, and managing Japanese government procurement opportunities from NJSS (National Japan Supercomputer System).

## Features

- **Automated Data Collection**: Crawls bidding information from NJSS using Apache Airflow
- **AI-Powered Analysis**: Uses OpenAI API for intelligent eligibility determination and analysis
- **Vector Search**: Leverages PostgreSQL with pgvector for semantic search capabilities
- **Real-time Dashboard**: React-based web interface for viewing and searching procurement opportunities
- **PDF Processing**: Extracts and analyzes information from procurement PDFs
- **Workflow Orchestration**: Automated daily crawling and processing via Airflow DAGs

## Architecture

The system consists of four main services:

1. **PostgreSQL Database** (pgvector/pgvector:pg15)
   - Main database with pgvector extension for embeddings
   - Tables: bidding_anken, bidding_anken_embeddings, job_logs
   - Stores procurement data and semantic embeddings

2. **Apache Airflow** (Custom image with Playwright)
   - Webserver on port 3031
   - Scheduler for automated DAG execution
   - NJSS crawler with PDF processing capabilities

3. **FastAPI Backend** (port 8002)
   - REST API for database operations
   - OpenAI integration for AI features
   - Vector similarity search endpoints

4. **React Frontend** (port 3032)
   - Modern dashboard for data visualization
   - TypeScript + Tailwind CSS
   - Real-time procurement data display

## Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key
- NJSS credentials (for crawler)

### Setup

1. Clone the repository and set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your credentials:
# - OPENAI_API_KEY
# - NJSS_USERNAME
# - NJSS_PASSWORD
```

2. Start all services:
```bash
docker compose up
```

3. Initialize the database (run once):
```bash
docker exec -i airflow_postgres psql -U airflow -d automation-jp-procurement < sql/setup_db.sql
```

4. Access the applications:
   - Airflow UI: http://localhost:3031 (username: airflow, password: airflow)
   - API Documentation: http://localhost:8002/docs
   - Web Dashboard: http://localhost:3032

## Development

### Frontend Development
```bash
cd web
npm install
npm start           # Development server on port 3000
npm run build       # Production build
npm test            # Run tests
```

### Backend Development
```bash
cd api
pip install -r requirements.txt
pytest              # Run tests
pytest --cov=src    # With coverage
uvicorn src.main:app --reload --port 8000  # Local development
```

### Database Access
```bash
# Connect to PostgreSQL
docker exec -it airflow_postgres psql -U airflow -d automation-jp-procurement

# View recent bidding cases
SELECT * FROM bidding_anken ORDER BY created_at DESC LIMIT 10;

# Check job logs
SELECT * FROM job_logs ORDER BY created_at DESC;
```

### Airflow DAG Management
```bash
# Test DAG syntax
docker exec airflow_webserver airflow dags test njss_daily_crawler

# Trigger DAG manually
docker exec airflow_webserver airflow dags trigger njss_daily_crawler

# View logs
docker compose logs -f airflow-webserver
docker compose logs -f airflow-scheduler
```

## Project Structure

```
.
├── api/                    # FastAPI backend
│   ├── src/
│   │   ├── main.py        # Application entry point
│   │   ├── database.py    # Database models and connection
│   │   ├── routers/       # API endpoints
│   │   └── schemas.py     # Pydantic models
│   └── requirements.txt
├── web/                    # React frontend
│   ├── src/
│   │   ├── App.tsx        # Main component
│   │   ├── components/    # React components
│   │   └── pages/         # Page components
│   └── package.json
├── dags/                   # Airflow DAGs
│   ├── njss_crawler_with_pdf_dag.py
│   └── njss_auth_config.py
├── sql/                    # Database scripts
│   └── setup_db.sql
├── docker-compose.yaml     # Service orchestration
└── .env.example           # Environment template
```

## Configuration

Key environment variables:

- `OPENAI_API_KEY`: Required for AI analysis features
- `NJSS_USERNAME`, `NJSS_PASSWORD`: NJSS crawler credentials
- `POSTGRES_*`: Database configuration
- `AIRFLOW_*`: Airflow settings
- `CRAWLER_*`: Browser/crawler configuration

## Troubleshooting

### NJSS Crawler Issues
- Enable debug mode: Set `NJSS_DEBUG_MODE=true` and `CRAWLER_HEADLESS=false`
- Check screenshots in the logs directory
- Run `python debug_njss_auth.py` for interactive debugging

### API Connection Issues
- Verify API health: `curl http://localhost:8002/health`
- Check database connection in API logs
- Ensure OPENAI_API_KEY is properly set

### Frontend Build Issues
- Clear npm cache: `cd web && npm cache clean --force`
- Delete node_modules and reinstall dependencies
- Verify proxy settings in package.json

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Security

- Never commit `.env` files or credentials
- Use Airflow Connections for production credentials
- Rotate API keys regularly
- Keep dependencies updated

## License

This project is proprietary software. All rights reserved.
