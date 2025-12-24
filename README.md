# Plex MediaProvider for ThePornDB

A Plex Media Provider built with Python/FastAPI that implements the official Plex MediaProvider interface using [ThePornDB](https://theporndb.net) as the metadata source.

## Features

- **Plex MediaProvider Interface** - Native Plex agent integration (compatible with [tmdb-example-provider](https://github.com/plexinc/tmdb-example-provider))
- **TV Provider** - Sites as Shows, Scenes as Episodes, Year-based Seasons
- **Movie Provider** - Full-length movie support
- **Multi-tier Caching** - Redis + SQLite for optimal performance
- **Rate Limiting** - Respects TPDB API limits (configurable)
- **Filename Parsing** - Automatic metadata extraction from filenames
- **Admin Web UI** - Dashboard, search, cache management

## Content Mapping

| ThePornDB | Plex |
|-----------|------|
| Site/Studio | TV Show |
| Scene | Episode |
| Release Year | Season |
| Movie | Movie |

## Quick Start

### Prerequisites

- Python 3.11+
- ThePornDB API key ([get one here](https://theporndb.net))
- Redis (optional, for distributed caching)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/plex-metadata-tpdb.git
cd plex-metadata-tpdb

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and configure your settings
```

Required settings:
```env
TPDB_API_KEY=your_api_key_here
```

Optional settings:
```env
DATABASE_URL=sqlite+aiosqlite:///./data/tpdb_provider.db
REDIS_URL=redis://localhost:6379/0
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
DEBUG=false
```

### Running

```bash
# Development
python -m app.main

# Or with uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker

```bash
cd docker

# Set your API key
export TPDB_API_KEY=your_api_key_here

# Start services
docker-compose up -d
```

## API Endpoints

### TV Provider (`/tv`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tv` | MediaProvider definition |
| POST | `/tv/library/metadata/matches` | Match shows/seasons/episodes |
| GET | `/tv/library/metadata/{ratingKey}` | Get metadata |
| GET | `/tv/library/metadata/{ratingKey}/children` | Get children |

### Movie Provider (`/movie`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/movie` | MediaProvider definition |
| POST | `/movie/library/metadata/matches` | Match movies |
| GET | `/movie/library/metadata/{ratingKey}` | Get metadata |

### Other

| Endpoint | Description |
|----------|-------------|
| `/health` | Health check |
| `/admin` | Admin Web UI (requires auth) |
| `/docs` | API documentation (debug mode only) |

## Plex Configuration

1. Start the provider and note the URL (e.g., `http://192.168.1.100:8000`)

2. In Plex, go to **Settings > Agents**

3. Add a custom agent pointing to:
   - TV: `http://your-server:8000/tv`
   - Movies: `http://your-server:8000/movie`

## Project Structure

```
plex-metadata-tpdb/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── constants.py         # Constants and enums
│   ├── providers/           # Plex MediaProvider definitions
│   ├── routes/              # API endpoints
│   ├── clients/             # TPDB API client
│   ├── services/            # Business logic
│   ├── mappers/             # Data transformers
│   ├── parsers/             # Filename parsing
│   ├── models/              # Pydantic schemas
│   ├── db/                  # Database layer
│   └── web/                 # Admin UI
├── docker/                  # Docker files
├── tests/                   # Test suite
├── pyproject.toml           # Dependencies
└── .env.example             # Environment template
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint code
ruff check .

# Type check
mypy app
```

## Cache TTLs

| Content Type | Default TTL |
|--------------|-------------|
| Site list | 24 hours |
| Site detail | 7 days |
| Scene search | 5 minutes |
| Scene detail | 24 hours |
| Movie detail | 24 hours |

## Rate Limiting

- **Outgoing (to TPDB)**: 2 requests/second (configurable via `TPDB_RATE_LIMIT`)
- **Incoming (API)**: 100 requests/minute default

## License

MIT

## Acknowledgments

- [ThePornDB](https://theporndb.net) for the metadata API
- [Plex](https://plex.tv) for the MediaProvider specification
- [tmdb-example-provider](https://github.com/plexinc/tmdb-example-provider) for the reference implementation
