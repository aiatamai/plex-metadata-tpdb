# Quick Reference Guide

## One-Minute Overview

**What is this?**
A Plex plugin that gets movie/TV metadata from ThePornDB API

**How does it work?**
```
File in Plex → Provider searches ThePornDB → Shows user matches
→ User selects → Provider fetches full metadata → Plex stores it
```

**Key files:**
- `main.py` - Application startup
- `routes/tv.py`, `routes/movie.py` - HTTP endpoints
- `services/match_service.py` - Find matches
- `services/metadata_service.py` - Get full metadata
- `clients/tpdb_client.py` - Talk to ThePornDB API

---

## API Endpoints Cheat Sheet

### TV Provider

```
GET /tv
  Returns provider capabilities

POST /tv/library/metadata/matches
  Input: {type: 2/3/4, title, year, ...}
  Output: List of matching shows/seasons/episodes

GET /tv/library/metadata/{rating_key}
  Input: rating_key like "tpdb-site-brazzers"
  Output: Full metadata for that item

GET /tv/library/metadata/{rating_key}/children
  Input: rating_key, containerStart, containerSize
  Output: Children (seasons or episodes)
```

### Movie Provider

```
GET /movie
  Returns provider capabilities

POST /movie/library/metadata/matches
  Input: {type: 1, title, year, ...}
  Output: List of matching movies

GET /movie/library/metadata/{rating_key}
  Input: rating_key like "tpdb-movie-uuid"
  Output: Full movie metadata
```

### Other

```
GET /health
  Returns: {"status": "healthy", "service": "tpdb-plex-provider"}
```

---

## Data Model Quick Reference

### Hierarchy

```
SITE (Show)
├─ YEAR 2024 (Season)
│  ├─ SCENE 1 (Episode)
│  ├─ SCENE 2 (Episode)
│  └─ SCENE N (Episode)
├─ YEAR 2023 (Season)
│  └─ ...

MOVIE
├─ Title
├─ Year
└─ ...
```

### Rating Keys

```python
"tpdb-site-{slug}"           # A site/show
"tpdb-season-{slug}-{year}"  # A year/season
"tpdb-scene-{uuid}"          # A scene/episode
"tpdb-movie-{uuid}"          # A movie
```

### Metadata Types

```python
MetadataType.SHOW = 2      # A show/site
MetadataType.SEASON = 3    # A season/year
MetadataType.EPISODE = 4   # An episode/scene
MetadataType.MOVIE = 1     # A movie
```

---

## Configuration

### Environment Variables

```bash
# Required
TPDB_API_KEY=your_api_key_here

# Server
DEBUG=true|false
PROVIDER_HOST=0.0.0.0
PROVIDER_PORT=8000

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/tpdb_provider.db

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# API limits
TPDB_RATE_LIMIT=2.0

# Cache TTLs (seconds)
CACHE_TTL_SITE_LIST=86400      # 24 hours
CACHE_TTL_SITE_DETAIL=604800   # 7 days
CACHE_TTL_SCENE_SEARCH=300     # 5 minutes
CACHE_TTL_SCENE_DETAIL=86400   # 24 hours
CACHE_TTL_MOVIE_DETAIL=86400   # 24 hours
```

---

## Common Tasks

### Add Logging to a Function

```python
import structlog
logger = structlog.get_logger(__name__)

async def my_function():
    logger.info("Starting process", user_id=123)

    try:
        result = await do_work()
        logger.info("Work completed", result=result)
        return result
    except Exception as e:
        logger.error("Work failed", error=str(e))
        raise
```

### Cache a Result

```python
from app.services.cache_service import get_cache_service

cache = get_cache_service()

# Get or fetch and cache
data = await cache.get_or_fetch(
    "site_detail",                      # Cache endpoint name
    {"site_slug": "brazzers"},          # Cache key params
    lambda: client.get_site("brazzers"), # Fetch function
    ttl=604800                          # 7 days
)
```

### Handle API Errors

```python
from app.clients.tpdb_client import (
    TPDBError,
    TPDBNotFoundError,
    TPDBRateLimitError
)

try:
    result = await client.get_scene(scene_id)
except TPDBNotFoundError:
    logger.warning("Not found", scene_id=scene_id)
    return None
except TPDBRateLimitError:
    logger.error("Rate limited")
    # Should probably wait and retry
except TPDBError as e:
    logger.error("API error", error=str(e), status=e.status_code)
    raise
```

### Get the Cache Service

```python
from app.services.cache_service import get_cache_service

cache = get_cache_service()  # Singleton instance

# Get stats
stats = await cache.get_stats()
print(f"Cache hits: {stats['total_hits']}")
print(f"Active entries: {stats['active_entries']}")

# Clear cache
await cache.clear()
```

### Get the TPDB Client

```python
from app.clients.tpdb_client import get_tpdb_client

client = await get_tpdb_client()  # Singleton instance

# Search
response = await client.search_scenes(q="title", per_page=10)

# Get specific item
scene = await client.get_scene("uuid-or-slug")
```

---

## Debugging Checklist

- [ ] Is TPDB_API_KEY set? (`echo $TPDB_API_KEY`)
- [ ] Is app running? (`curl http://localhost:8000/health`)
- [ ] Check logs for errors (debug mode shows detailed logs)
- [ ] Is TPDB API responding? (check their status page)
- [ ] Is rate limiter blocking? (check available_tokens)
- [ ] Is cache working? (check get_stats())
- [ ] Are rate limits being hit? (look for 429 errors in logs)

---

## Performance Tips

### Improve Response Time

1. **Enable cache** - responses drop from 1-2 sec to 50-100ms
2. **Increase TTL** - fewer re-fetches
3. **Use memory cache** - 5-10ms vs 50-100ms for DB cache
4. **Add Redis** - distributed caching, fast lookups

### Reduce API Calls

1. **Increase TTL for stable data** - sites don't change often
2. **Clear expired entries regularly** - don't waste space
3. **Monitor cache stats** - identify low-hit endpoints
4. **Batch requests** - if possible, combine searches

### Handle High Traffic

1. **Use async throughout** - concurrent requests
2. **Add Redis for caching** - faster than SQLite
3. **Use PostgreSQL instead of SQLite** - better concurrency
4. **Run multiple instances** - with shared Redis cache
5. **Increase rate limit if safe** - respect TPDB's limits

---

## File Organization

```
app/
├── main.py                    # Application entry point
├── config.py                  # Configuration
├── constants.py              # Constants/enums
├── clients/
│   ├── tpdb_client.py        # ThePornDB API client
│   └── rate_limiter.py       # Token bucket rate limiter
├── db/
│   ├── database.py           # DB session management
│   └── models/
│       ├── site.py           # Site/Show table
│       ├── scene.py          # Scene/Episode table
│       ├── movie.py          # Movie table
│       ├── performer.py      # Performer table
│       └── cache_entry.py    # Cache table
├── models/
│   └── tpdb.py              # TPDB response models
├── services/
│   ├── match_service.py      # Find matches
│   ├── metadata_service.py   # Get metadata
│   └── cache_service.py      # Cache management
├── mappers/
│   ├── show_mapper.py        # TPDB → Plex Show
│   └── movie_mapper.py       # TPDB → Plex Movie
├── parsers/
│   ├── scene_parser.py       # Parse filenames
│   └── patterns.py           # Regex patterns
├── routes/
│   ├── tv.py                 # /tv endpoints
│   └── movie.py              # /movie endpoints
└── web/
    └── router.py             # Admin UI routes
```

---

## Key Classes/Functions by Purpose

### Want to... | Go to...
```
Start the app          | main.py:run()
Add a route            | routes/tv.py or routes/movie.py
Search TPDB            | match_service.py
Get full metadata      | metadata_service.py
Cache results          | cache_service.py
Make API calls         | tpdb_client.py
Limit request rate     | rate_limiter.py
Load settings          | config.get_settings()
Parse filename         | SceneParser.parse()
Convert to Plex format | ShowMapper, MovieMapper
```

---

## Error Messages & Solutions

### "TPDB API error: 401 Unauthorized"
- **Cause**: Invalid API key
- **Fix**: Check TPDB_API_KEY environment variable

### "TPDB rate limit exceeded"
- **Cause**: Too many requests to TPDB
- **Fix**: Increase cache TTLs or lower TPDB_RATE_LIMIT

### "Resource not found: /scenes/invalid-uuid"
- **Cause**: Scene doesn't exist on TPDB
- **Fix**: This is normal, provider returns empty results

### "Connection refused (localhost:8000)"
- **Cause**: App not running
- **Fix**: Start app: `python -m app.main`

### "No metadata found"
- **Cause**: Couldn't find match on TPDB
- **Fix**: Try searching by different name

---

## Testing with cURL

### Test provider definition
```bash
curl http://localhost:8000/tv
```

### Test matching
```bash
curl -X POST http://localhost:8000/tv/library/metadata/matches \
  -H "Content-Type: application/json" \
  -d '{"type": 2, "title": "Brazzers"}'
```

### Test metadata
```bash
curl "http://localhost:8000/tv/library/metadata/tpdb-site-brazzers"
```

### Pretty print JSON
```bash
curl -s ... | jq .
```

---

## Useful Commands

```bash
# Start app
python -m app.main

# Start with uvicorn
uvicorn app.main:app --reload

# Test API
curl http://localhost:8000/health

# View logs (if using file logging)
tail -f logs/provider.log

# Check if port is in use
lsof -i :8000

# Kill app
pkill -f "app.main"

# Run tests
pytest

# Format code
black app/

# Check types
mypy app/

# Lint code
ruff check app/
```

---

## When Things Go Wrong

### App crashes on startup
1. Check Python version (needs 3.11+)
2. Check dependencies installed (`pip install -e .`)
3. Check TPDB_API_KEY is set
4. Check database is writable (`ls -la data/`)

### Slow requests
1. Check if cached (look for "Cache hit" in logs)
2. Check TPDB API response time (might be slow)
3. Check network connectivity to TPDB
4. Check rate limiter isn't blocking (check available_tokens)

### No results found
1. Try searching with different keywords
2. Check TPDB API directly (api.theporndb.net)
3. Verify TPDB_API_KEY has search permission
4. Check cache isn't returning stale 0-result responses

### High memory usage
1. Check how many items are cached
2. Reduce cache TTLs (fewer items kept in memory)
3. Restart app to clear memory cache
4. Check for memory leaks in logs

---

## Next Steps to Learn More

1. **Understand token bucket**: See `CODE_COMMENTS_DETAILED.md` - "Rate Limiter Deep Dive"
2. **Understand caching**: See `CODE_COMMENTS_DETAILED.md` - "Cache Service Deep Dive"
3. **Understand matching**: See `CODE_COMMENTS_DETAILED.md` - "Match Service Deep Dive"
4. **Full architecture**: See `CODEBASE_EXPLANATION.md`
5. **Code review**: See `README_CODE_REVIEW.md`

---

## Useful Links

- [Plex MediaProvider Spec](https://github.com/plexinc/tmdb-example-provider)
- [ThePornDB API Docs](https://api.theporndb.net)
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Pydantic Docs](https://docs.pydantic.dev)

