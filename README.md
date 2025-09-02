# Aspen Backend

Multi-tenant AI workflow platform backend API.

## Development

### Prerequisites
- Docker
- Docker Compose

### Getting Started

1. Build and start the services:
```bash
docker compose up --build
```

2. Run tests:
```bash
docker compose exec app poetry run test
```

3. Access the API:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Available Commands

Inside the container:
- `poetry run test` - Run tests
- `poetry run lint` - Run linting
- `poetry run format` - Format code
- `poetry run type-check` - Run type checking 