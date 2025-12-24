# Plex Metadata ThePornDB Provider - Complete Code Explanation

## Overview

This is a **Plex Media Provider** written in Python/FastAPI that integrates with **ThePornDB** API to provide metadata for adult content in Plex Media Server.

### What is a Plex Media Provider?

A Media Provider is a plugin that Plex uses to find and enrich metadata for your media. When you add a file to Plex, the provider:
1. Matches it against the database (finds what the file is)
2. Retrieves metadata (title, description, performers, images, etc.)
3. Organizes it properly (in this case, Sites as Shows, Scenes as Episodes)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Plex Media Server                         │
│  (Makes HTTP requests to match/get metadata)                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ HTTP Requests
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Application (main.py)                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  TV Provider Routes (/tv)      Movie Provider Routes │   │
│  │  ┌────────────────────────────┐ (/movie)             │   │
│  │  │ - GET /tv                  │ ┌──────────────────┐ │   │
│  │  │ - POST /tv/matches         │ │ - GET /movie     │ │   │
│  │  │ - GET /tv/metadata/{key}   │ │ - POST /matches  │ │   │
│  │  │ - GET /tv/children/{key}   │ │ - GET /metadata  │ │   │
│  │  └────────────────────────────┘ └──────────────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                   │
│                           ▼                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Service Layer (Business Logic)                       │   │
│  │  ├─ MatchService  (find matches for titles)          │   │
│  │  ├─ MetadataService (retrieve full metadata)         │   │
│  │  └─ CacheService (cache TPDB responses)              │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                   │
│                           ▼                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Client Layer (External APIs)                         │   │
│  │  ├─ TPDBClient (ThePornDB API calls)                │   │
│  │  └─ RateLimiter (control request rate)              │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                   │
└───────────────────────────┼───────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   External APIs & Local Storage        │
        │  ├─ ThePornDB API (https://api...)   │
        │  ├─ SQLite Database (local caching)  │
        │  └─ Redis (optional distributed cache)
        └───────────────────────────────────────┘
```

---

## File Structure & Explanation

### 1. **app/main.py** - Application Entry Point

**What it does:**
- Creates the FastAPI application
- Sets up logging (structured logs with context)
- Defines application lifecycle (startup/shutdown)
- Registers all route handlers
- Runs the HTTP server

**Key Components:**

```python
# Structured logging setup
structlog.configure(...)
# Captures logs in a structured format with context

# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    await init_db()
    yield
    # Shutdown: Cleanup

# Application factory
def create_app() -> FastAPI:
    app = FastAPI(...)
    app.add_middleware(CORSMiddleware)  # Allow cross-origin requests
    app.include_router(tv.router, prefix="/tv")      # TV provider
    app.include_router(movie.router, prefix="/movie")  # Movie provider
    return app
```

---

### 2. **app/config.py** - Configuration Management

**What it does:**
- Loads configuration from environment variables (.env file)
- Provides type validation using Pydantic
- Defines defaults for all settings

**Configuration Options:**

```
Application:
├─ app_name: Display name
├─ debug: Enable debug mode

Server:
├─ provider_host: IP to bind (default: 0.0.0.0)
├─ provider_port: Port (default: 8000)

Database:
├─ database_url: SQLite/PostgreSQL connection string

API:
├─ tpdb_api_key: ThePornDB API key (REQUIRED)
├─ tpdb_base_url: ThePornDB API endpoint
├─ tpdb_rate_limit: Max requests/second to TPDB (2.0)

Cache TTLs (how long to cache responses):
├─ cache_ttl_site_list: 24 hours
├─ cache_ttl_site_detail: 7 days
├─ cache_ttl_scene_search: 5 minutes
├─ cache_ttl_scene_detail: 24 hours
├─ cache_ttl_movie_detail: 24 hours

Rate Limiting (incoming):
├─ rate_limit_default: 100 requests/minute
├─ rate_limit_search: 30 requests/minute

Admin:
├─ admin_username: Dashboard login username
└─ admin_password: Dashboard login password
```

**How to use:**
```python
from app.config import get_settings
settings = get_settings()  # Returns cached singleton
print(settings.tpdb_api_key)
```

---

### 3. **app/constants.py** - Constants and Enums

**What it does:**
- Defines immutable values used throughout the app
- Provider identifiers for Plex
- Metadata type enums
- Rating key prefixes
- API endpoint paths

**Key Constants:**

```python
# Provider IDs (how Plex identifies this provider)
TV_PROVIDER_IDENTIFIER = "tv.plex.agents.tpdb.tv"
MOVIE_PROVIDER_IDENTIFIER = "tv.plex.agents.tpdb.movie"

# Metadata types
class MetadataType(IntEnum):
    MOVIE = 1      # Movie metadata type
    SHOW = 2       # TV show metadata type
    SEASON = 3     # Season metadata type
    EPISODE = 4    # Episode metadata type

# Rating key prefixes (used to construct IDs)
RATING_KEY_SITE = "tpdb-site"       # e.g., "tpdb-site-brazzers"
RATING_KEY_SEASON = "tpdb-season"   # Year-based season
RATING_KEY_SCENE = "tpdb-scene"     # Individual scene
RATING_KEY_MOVIE = "tpdb-movie"     # Movie ID

# ThePornDB API endpoints
class TPDB_ENDPOINTS:
    SCENES = "/scenes"
    MOVIES = "/movies"
    PERFORMERS = "/performers"
    SITES = "/sites"
```

---

### 4. **app/clients/rate_limiter.py** - Token Bucket Rate Limiter

**What it does:**
- Prevents exceeding ThePornDB API rate limits
- Uses the "token bucket" algorithm
- Allows bursts but enforces sustained rate limit

**How Token Bucket Works:**

```
Think of it like a water bucket:
- Bucket capacity: 5 tokens (burst_size)
- Water flows in at: 2 tokens/second (rate)
- Each request uses: 1 token

Timeline:
T=0s:   Bucket has 5 tokens → Request succeeds, 4 tokens left
T=0.1s: Bucket has 4 tokens → Request succeeds, 3 tokens left
T=0.2s: Bucket has 2.8 tokens → Request succeeds, 1.8 tokens left
T=0.3s: Bucket has 1.6 tokens → Request succeeds, 0.6 tokens left
T=0.4s: Bucket has 0.4 tokens → Must WAIT
T=0.5s: Bucket has 0.4 + 1.0 = 1.4 tokens → Request succeeds
```

**Methods:**

```python
# Block until tokens available (will wait if needed)
wait_time = await limiter.acquire(tokens=1)

# Try without waiting (returns True/False immediately)
success = await limiter.try_acquire(tokens=1)

# Check available tokens (doesn't consume them)
available = limiter.available_tokens
```

---

### 5. **app/clients/tpdb_client.py** - ThePornDB API Client

**What it does:**
- Makes HTTP requests to ThePornDB API
- Handles authentication (API key in headers)
- Implements rate limiting
- Provides typed methods for common queries
- Converts HTTP errors to custom exceptions

**Exception Types:**

```python
# Raised for general API errors
class TPDBError(Exception):
    message: str
    status_code: Optional[int]

# Raised when resource not found (404)
class TPDBNotFoundError(TPDBError):
    pass

# Raised when rate limit exceeded (429)
class TPDBRateLimitError(TPDBError):
    pass
```

**Key Methods:**

```python
# Scenes
client.search_scenes(q="title", site="brazzers", page=1, per_page=25)
client.get_scene(scene_id="uuid-or-slug")
client.get_scene_by_hash(hash_value="oshash")

# Sites/Studios
client.search_sites(q="brazzers", page=1, per_page=25)
client.get_site(site_id="uuid-or-slug")
client.get_site_scenes(site_id="uuid", page=1, per_page=25, year=2024)

# Movies
client.search_movies(q="title", year=2024, page=1, per_page=25)
client.get_movie(movie_id="uuid-or-slug")

# Performers
client.search_performers(q="name", page=1, per_page=25)
client.get_performer(performer_id="uuid-or-slug")
```

**Usage Pattern:**

```python
client = await get_tpdb_client()  # Get singleton
try:
    response = await client.search_scenes(q="title")
except TPDBNotFoundError:
    print("Not found")
except TPDBRateLimitError:
    print("Rate limited")
```

---

### 6. **app/models/tpdb.py** - ThePornDB Data Models

**What it does:**
- Defines Pydantic models for TPDB API responses
- Provides type validation and conversion
- Allows IDE autocomplete for API responses

**Key Models:**

```python
class TPDBPerformer:
    id: str
    name: str
    bio: Optional[str]
    gender: Optional[str]
    birthdate: Optional[str]
    aliases: Optional[list[str]]
    image: Optional[str]

class TPDBSite:
    id: str
    name: str
    slug: Optional[str]
    description: Optional[str]
    logo: Optional[str]
    poster: Optional[str]

class TPDBScene:
    id: str
    title: str
    slug: Optional[str]
    date: Optional[str]  # YYYY-MM-DD
    duration: Optional[int]  # seconds
    site: Optional[TPDBSite]
    performers: list[TPDBPerformer]
    tags: list[str]

    @property
    def year(self) -> Optional[int]:
        """Extract year from date"""
        return int(self.date[:4]) if self.date else None

class TPDBMovie:
    id: str
    title: str
    date: Optional[str]
    year: Optional[int]
    studio: Optional[TPDBSite]
    performers: list[TPDBPerformer]
    directors: list[str]
```

---

### 7. **app/db/database.py** - Database Setup

**What it does:**
- Creates async SQLAlchemy engine
- Manages database sessions
- Initializes database on startup
- Provides dependency injection for sessions

**Key Functions:**

```python
# SQLAlchemy setup for async
engine = create_async_engine(
    settings.database_url,  # SQLite or PostgreSQL
    echo=settings.debug,    # Log SQL queries in debug mode
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Called on startup to create all tables
async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Get a session for a request
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

---

### 8. **app/db/models/** - Database Models (ORM)

**What it does:**
- Defines database schema using SQLAlchemy ORM
- Creates tables for caching and content

**Key Models:**

#### **Site** (Maps to Plex Show)
```python
class Site(Base):
    __tablename__ = "sites"

    id: int  # Primary key
    tpdb_id: str  # TPDB UUID (unique)
    slug: str  # URL-friendly name (unique)
    name: str  # Display name
    description: Optional[str]
    logo_url: Optional[str]
    poster_url: Optional[str]

    # Relationship
    scenes: list[Scene]  # All scenes from this site
```

#### **Scene** (Maps to Plex Episode)
```python
class Scene(Base):
    __tablename__ = "scenes"

    id: int
    tpdb_id: str  # Scene UUID (unique)
    title: str
    description: Optional[str]
    release_date: Optional[date]
    duration: Optional[int]  # seconds

    poster_url: Optional[str]
    tags: Optional[list]  # JSON array

    site_id: Optional[int]  # Foreign key to Site
    scene_performers: list[ScenePerformer]  # Many-to-many

    @property
    def year(self) -> Optional[int]:
        """Get release year from date"""
        return self.release_date.year if self.release_date else None
```

#### **Movie** (Maps to Plex Movie)
```python
class Movie(Base):
    __tablename__ = "movies"

    id: int
    tpdb_id: str
    title: str
    release_date: Optional[date]
    year: Optional[int]
    duration: Optional[int]

    studio_name: Optional[str]
    poster_url: Optional[str]
    directors: Optional[list]  # JSON array
    performers: Optional[list]  # JSON array
```

#### **Performer** (Actor/Model)
```python
class Performer(Base):
    __tablename__ = "performers"

    id: int
    tpdb_id: str
    name: str
    gender: Optional[str]
    birthdate: Optional[date]
    height: Optional[int]
    weight: Optional[int]

    scenes: list[ScenePerformer]  # Many-to-many relationship
```

---

### 9. **app/services/cache_service.py** - Multi-Tier Caching

**What it does:**
- Caches TPDB API responses to reduce API calls
- Uses 2-tier caching: memory (fast) + database (persistent)
- Tracks cache hits for statistics
- Cleans up expired entries

**Cache Tiers:**

```
Fast tier (Memory):  In-process dict - expires after 5 mins
    ↓ Miss
Persistent tier:     SQLite database - expires per configured TTL
    ↓ Miss
Fetch:               Call TPDB API, cache result
```

**Key Methods:**

```python
# Get from cache
cached = await cache.get("site_detail", {"site_slug": "brazzers"})

# Set in cache
await cache.set(
    "site_detail",
    {"site_slug": "brazzers"},
    value=site_data,
    ttl=604800  # 7 days
)

# Get or fetch if not cached
data = await cache.get_or_fetch(
    "site_detail",
    {"site_slug": "brazzers"},
    fetch_func=lambda: client.get_site("brazzers")
)

# Clear expired entries
count = await cache.clear_expired()

# Get statistics
stats = await cache.get_stats()
# {
#   "total_entries": 150,
#   "active_entries": 120,
#   "expired_entries": 30,
#   "total_hits": 5000,
#   "memory_entries": 15,
#   "by_endpoint": {"site_detail": 45, "scene_search": 75}
# }
```

---

### 10. **app/services/match_service.py** - Metadata Matching

**What it does:**
- Takes partial information (filename, title, year)
- Searches TPDB for matches
- Returns ranked results for Plex to display

**How Matching Works:**

```
Plex sends:          MatchService does:
├─ Title: "Brazzers" ├─ Check for GUID (if previously matched)
├─ Year: 2024        ├─ Search TPDB for "Brazzers"
└─ Type: Show        └─ Return top 10 matches (ranked by relevance)

Plex displays matches to user →
User selects one      →
Plex stores GUID for future use
```

**Methods:**

```python
# Match a TV show/site
container = await match_service.match_show(
    MatchRequest(title="Brazzers", type=2)
)

# Match a season (year grouping)
container = await match_service.match_season(
    MatchRequest(grandparentTitle="Brazzers", parentIndex=2024)
)

# Match an episode (scene)
container = await match_service.match_episode(
    MatchRequest(
        title="Scene Title",
        grandparentTitle="Brazzers",
        date="2024-01-15"
    )
)

# Match a movie
container = await match_service.match_movie(
    MatchRequest(title="Movie Title", year=2024)
)
```

---

### 11. **app/services/metadata_service.py** - Metadata Retrieval

**What it does:**
- Retrieves full metadata for matched items
- Parses rating keys to determine what to fetch
- Returns formatted metadata for Plex

**Metadata Hierarchy:**

```
Show (Site)
├─ Season 1 (2024)
│  ├─ Episode 1 (Scene)
│  ├─ Episode 2 (Scene)
│  └─ ...
├─ Season 2 (2023)
│  └─ ...

Movie
├─ Title
├─ Year
├─ Description
├─ Performers
└─ ...
```

**Methods:**

```python
# Get metadata for an item
container = await metadata_service.get_metadata(
    rating_key="tpdb-site-brazzers",
    provider_identifier="tv.plex.agents.tpdb.tv"
)

# Get children (seasons for a show, episodes for a season)
container = await metadata_service.get_children(
    rating_key="tpdb-site-brazzers",
    provider_identifier="tv.plex.agents.tpdb.tv",
    offset=0,
    limit=50
)
```

---

### 12. **app/routes/tv.py** & **app/routes/movie.py** - HTTP Endpoints

**What they do:**
- Handle HTTP requests from Plex
- Validate input
- Call services
- Return JSON responses in Plex format

**TV Provider Endpoints:**

```
GET /tv
  └─ Return provider capabilities/metadata

POST /tv/library/metadata/matches
  └─ Match shows/seasons/episodes
     Input: MatchRequest {title, year, type, guid, ...}
     Output: MediaContainer with MetadataItems

GET /tv/library/metadata/{rating_key}
  └─ Get full metadata for item
     Input: rating_key like "tpdb-site-brazzers"
     Output: MediaContainer with MetadataItem

GET /tv/library/metadata/{rating_key}/children
  └─ Get children (seasons or episodes)
     Input: rating_key, containerStart, containerSize
     Output: MediaContainer with list of MetadataItems
```

**Movie Provider Endpoints:**

```
GET /movie
  └─ Return provider capabilities

POST /movie/library/metadata/matches
  └─ Match movies

GET /movie/library/metadata/{rating_key}
  └─ Get movie metadata
```

---

### 13. **app/parsers/scene_parser.py** - Filename Parsing

**What it does:**
- Extracts metadata hints from filenames
- Identifies site names, performers, dates
- Provides confidence scores
- Helps with matching

**Parse Example:**

```
Input:  "Brazzers - 2024.01.15 - Actress Name - Scene Title - 1080p.mp4"
Output: ParsedScene(
  site="Brazzers",
  release_date=date(2024, 1, 15),
  performers=["Actress Name"],
  title="Scene Title",
  resolution="1080p",
  confidence=0.9
)
```

**Methods:**

```python
parsed = SceneParser.parse(filename)
print(parsed.site)              # "Brazzers"
print(parsed.release_date)      # date(2024, 1, 15)
print(parsed.performers)        # ["Actress Name"]
print(parsed.to_search_query()) # "Brazzers Actress Name Scene Title"
```

---

## Data Flow Examples

### Example 1: User Adds a Scene File to Plex

```
1. User adds file: "Brazzers - 2024.01.15 - Jane Doe - Scene Name.mp4"

2. Plex sends POST /tv/library/metadata/matches:
   {
     "type": 4,  // EPISODE
     "title": "Brazzers - 2024.01.15 - Jane Doe - Scene Name",
     "year": 2024,
     "grandparentTitle": "Brazzers"
   }

3. match_service.match_episode():
   a. Parse filename → finds site, date, performers
   b. Search TPDB API for scenes matching criteria
   c. Return top 10 results with metadata

4. Plex displays matches to user

5. User selects match → Plex stores GUID
   (Example: "tpdb://scene-uuid-123")

6. Next time Plex needs metadata for this file:
   - POST /tv/library/metadata/matches with GUID
   - metadata_service.get_metadata() with rating_key
   - Returns full scene details (actors, description, images, etc.)
```

### Example 2: Getting Show Details

```
1. Plex user views "Brazzers" show in Plex

2. Plex sends GET /tv/library/metadata/tpdb-site-brazzers

3. metadata_service.get_metadata():
   a. Parse rating_key → "site", "brazzers"
   b. Check cache for site data
   c. If not in cache, call client.get_site("brazzers")
   d. Format response as Plex MetadataItem
   e. Return with images, description, etc.

4. Plex displays the show information
```

### Example 3: Getting Season (Year) Information

```
1. Plex user clicks on "2024" season

2. Plex sends GET /tv/library/metadata/tpdb-site-brazzers/children
   With: containerStart=0, containerSize=50

3. metadata_service.get_children():
   a. Parse rating_key → site="brazzers"
   b. Get all scenes from Brazzers in 2024
   c. Format as list of MetadataItems (episodes)
   d. Return paginated results

4. Plex displays list of scenes with thumbnails
```

---

## How Content is Structured (Mapping)

The app maps adult content database to Plex's media structure:

```
ThePornDB               Plex Media Server
─────────────           ────────────────

Site (Studio)        → TV Show
  ├─ Scenes           → Episodes
  ├─ Performers       → Actors
  └─ Description      → Show description

Release Year          → Season number

Scene                 → Episode
  ├─ Title            → Episode title
  ├─ Release Date     → Air date
  ├─ Duration         → Runtime
  ├─ Performers       → Guest stars
  ├─ Description      → Episode summary
  └─ Image/Poster     → Episode artwork

Movie                 → Movie
  ├─ Title            → Movie title
  ├─ Year             → Release year
  ├─ Duration         → Runtime
  ├─ Studio           → Production company
  ├─ Performers       → Actors
  ├─ Directors        → Directors
  ├─ Description      → Plot summary
  └─ Images           → Artwork
```

---

## Performance Optimizations

### 1. **Caching Strategy**
- Scene search results cached for 5 minutes (frequent queries)
- Site details cached for 7 days (rarely change)
- Memory + database cache for redundancy

### 2. **Rate Limiting**
- Token bucket algorithm respects API limits
- Prevents being rate-limited or banned by TPDB
- Configurable burst capacity

### 3. **Async I/O**
- All I/O operations are async (API calls, database)
- FastAPI can handle many concurrent requests
- Non-blocking operations maintain responsiveness

### 4. **Connection Pooling**
- Reuses HTTP connections to TPDB
- Reuses database connections
- Single SQLAlchemy engine and client instance (singletons)

---

## Common Workflows

### Add a New Endpoint

1. Create method in service (`match_service.py`, `metadata_service.py`)
2. Add route in `routes/tv.py` or `routes/movie.py`
3. Handle request, call service, return response
4. Test with curl or Plex

### Add Caching

```python
# Service method
async def _get_site(self, site_slug: str):
    cache = self._get_cache()
    client = await self._get_client()

    return await cache.get_or_fetch(
        "site_detail",                           # Cache endpoint name
        {"site_slug": site_slug},                # Cache key
        lambda: client.get_site(site_slug),      # Fetch function
        ttl=604800                               # TTL (7 days)
    )
```

### Handle Errors

```python
from app.clients.tpdb_client import TPDBError, TPDBNotFoundError

try:
    data = await client.get_scene(scene_id)
except TPDBNotFoundError:
    logger.warning("Scene not found", scene_id=scene_id)
    return None
except TPDBError as e:
    logger.error("TPDB error", error=str(e), status=e.status_code)
    raise
```

---

## Configuration Tips

### Development

```bash
# .env file for development
DEBUG=true
TPDB_API_KEY=your_test_key
DATABASE_URL=sqlite+aiosqlite:///./data/dev.db
```

### Production

```bash
# Use environment variables (more secure)
export DEBUG=false
export TPDB_API_KEY=your_prod_key
export DATABASE_URL=postgresql+asyncpg://user:pass@host/db
export REDIS_URL=redis://redis-server:6379/0
```

### Rate Limiting Config

```python
# In .env - allow more requests in bursts
TPDB_RATE_LIMIT=3.0  # 3 requests/sec (instead of 2)

# Or slower to be extra safe
TPDB_RATE_LIMIT=1.0  # 1 request/sec
```

---

## Testing

### Manual Testing with curl

```bash
# Get TV provider definition
curl http://localhost:8000/tv

# Match a show
curl -X POST http://localhost:8000/tv/library/metadata/matches \
  -H "Content-Type: application/json" \
  -d '{"type": 2, "title": "Brazzers"}'

# Get metadata
curl "http://localhost:8000/tv/library/metadata/tpdb-site-brazzers"

# Health check
curl http://localhost:8000/health
```

---

## Debugging Tips

1. **Enable debug mode** for more logging:
   ```
   DEBUG=true
   ```

2. **Check logs** for errors:
   ```
   # Console output in debug mode shows detailed logs
   ```

3. **Test TPDB client directly**:
   ```python
   from app.clients.tpdb_client import TPDBClient
   client = TPDBClient()
   result = await client.search_sites(q="brazzers")
   ```

4. **Check cache stats**:
   - Database queries to SQLite cache table
   - Look at `/admin` panel if available

---

## Summary

This codebase implements a complete Plex Media Provider that:

✅ Connects to ThePornDB API
✅ Searches for content matches
✅ Retrieves full metadata
✅ Caches responses for performance
✅ Rate-limits requests respectfully
✅ Structures adult content as TV shows and movies
✅ Provides a REST API for Plex integration

The architecture is:
- **Modular**: Clear separation of concerns (routes → services → clients)
- **Async**: Fast, non-blocking I/O throughout
- **Cached**: Multi-tier caching reduces API calls
- **Rate-limited**: Respects API provider limits
- **Typed**: Pydantic models for validation
- **Logged**: Structured logging for debugging

