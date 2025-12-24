# Detailed Code Comments and Explanations

This document provides deep dives into key components with line-by-line explanations.

---

## Rate Limiter Deep Dive

### Token Bucket Algorithm Explained

```python
class RateLimiter:
    def __init__(self, requests_per_second: float = 2.0, burst_size: int = 5):
        # How fast tokens are added per second
        self.rate = requests_per_second  # e.g., 2.0 = 2 tokens per second

        # Maximum tokens that can accumulate
        self.burst_size = burst_size  # e.g., 5 = can handle 5 requests at once

        # Start with a full bucket
        self.tokens = float(burst_size)  # Start with 5 tokens

        # When was the last time we checked/updated tokens?
        self.last_update = datetime.now()  # Track time for refill calculation

        # Lock prevents race conditions in async code
        # (Multiple coroutines might access this at the same time)
        self._lock = asyncio.Lock()
```

### Visual Example

```
Scenario: rate=2.0/sec, burst_size=5

TIMELINE:
T=0.0s: |#####    | 5 tokens available
        Request 1 → OK (4 tokens left)

T=0.1s: |####     | 4 tokens + (0.1s × 2 tokens/s) = 4.2 tokens
        Request 2 → OK (3.2 tokens left)

T=0.2s: |###      | 3.2 tokens + (0.1s × 2) = 3.4 tokens
        Request 3 → OK (2.4 tokens left)

T=0.3s: |##       | 2.4 tokens + (0.1s × 2) = 2.6 tokens
        Request 4 → OK (1.6 tokens left)

T=0.4s: |#        | 1.6 tokens + (0.1s × 2) = 1.8 tokens
        Request 5 → OK (0.8 tokens left)

T=0.5s: |         | 0.8 tokens + (0.1s × 2) = 0.8 tokens
        Request 6 → NOT OK (need 1, have 0.8)
                    WAIT 0.2 seconds for 1 token to refill

T=0.7s: |#        | 0.8 + (0.2 × 2) = 1.2 tokens
        Request 6 → OK (0.2 tokens left)

T=0.8s: |         | 0.2 tokens + (0.1s × 2) = 0.4 tokens
        Request 7 → NOT OK
                    WAIT 0.3 seconds

T=1.1s: |#        | Refilled, request succeeds
```

### The acquire() Method Flow

```python
async def acquire(self, tokens: int = 1) -> float:
    """
    STEP 1: Lock
    ─────────────
    async with self._lock:
        # Only one coroutine can execute this code at a time
        # Prevents: Thread A refills while Thread B consumes
        #           Thread A refills while Thread B reads tokens
    """

    """
    STEP 2: Calculate Time Elapsed
    ───────────────────────────────
    now = datetime.now()                              # Current time
    elapsed = (now - self.last_update).total_seconds() # How much time passed?

    Example:
    - Last update: 10:00:00.500
    - Now:         10:00:00.600
    - Elapsed:     0.1 seconds
    """

    """
    STEP 3: Refill Tokens
    ─────────────────────
    self.tokens = min(self.burst_size, self.tokens + elapsed * self.rate)

    Logic:
    - Add: elapsed_seconds × rate_per_second
      Example: 0.1 sec × 2 tokens/sec = 0.2 tokens added

    - Cap at burst_size: don't exceed bucket capacity
      Example: if we had 4.8 and would add 0.5, cap at 5

    Example calculation:
    self.tokens = 4.5
    elapsed = 0.1
    rate = 2.0

    new_tokens = 4.5 + (0.1 × 2.0)
              = 4.5 + 0.2
              = 4.7

    min(5, 4.7) = 4.7 ✓
    """

    """
    STEP 4: Check If We Have Enough
    ────────────────────────────────
    if self.tokens < tokens:
        # Not enough tokens, need to wait
        deficit = tokens - self.tokens  # How many short?
        wait_time = deficit / self.rate  # How long to wait?

        Example:
        - Need 1 token
        - Have 0.8 tokens
        - Deficit = 1 - 0.8 = 0.2
        - Wait = 0.2 / 2.0 = 0.1 seconds

        # Sleep until tokens are available
        await asyncio.sleep(wait_time)

        # Recalculate tokens after sleep
        now = datetime.now()
        elapsed = (now - self.last_update).total_seconds()
        self.tokens = min(self.burst_size, self.tokens + elapsed * self.rate)
    """

    """
    STEP 5: Consume Tokens
    ──────────────────────
    self.tokens -= tokens  # Remove tokens from bucket
    return wait_time       # How long did we wait?
    """
```

---

## Cache Service Deep Dive

### Cache Key Generation

```python
def _make_key(self, endpoint: str, params: dict[str, Any]) -> str:
    """
    Generate a unique cache key from endpoint and params.

    Example:
    endpoint = "site_detail"
    params = {"site_slug": "brazzers", "include_scenes": True}

    Process:
    1. Sort params by key: {"include_scenes": True, "site_slug": "brazzers"}
    2. Convert to JSON: '{"include_scenes": true, "site_slug": "brazzers"}'
    3. Create key string: "site_detail:{"include_scenes": true, "site_slug": "brazzers"}'
    4. Hash with MD5: "a1b2c3d4e5f6g7h8i9j0..."

    Why hash?
    - Short, fixed-length keys
    - Fast database lookups
    - No special characters
    - Consistent ordering (sorted params)

    Why sort params?
    - Ensures same cache key regardless of param order
    - Example: {a:1, b:2} and {b:2, a:1} produce same key
    """
```

### Two-Tier Cache Flow

```python
async def get(self, endpoint: str, params: dict[str, Any]) -> Optional[Any]:
    """
    Get value from cache.

    Flow:

    1. Generate cache key
    key = self._make_key(endpoint, params)
    Example: "a1b2c3d4..."

    2. Check MEMORY CACHE (Tier 1)
    if key in self._memory_cache:
        value, expires_at = self._memory_cache[key]

        # Check if expired
        if datetime.utcnow() < expires_at:
            logger.debug("Memory cache hit")
            return value  ← Fast return! No database access
        else:
            # Expired, remove and fall through
            del self._memory_cache[key]

    3. Check DATABASE CACHE (Tier 2)
    async with async_session_maker() as session:
        result = await session.execute(
            select(CacheEntry).where(CacheEntry.cache_key == cache_key)
        )
        entry = result.scalar_one_or_none()

        if entry and not entry.is_expired:
            logger.debug("Database cache hit")
            # Move to memory for faster access next time
            self._memory_cache[cache_key] = (
                entry.response_data,
                datetime.utcnow() + timedelta(seconds=300)  # 5 min memory TTL
            )
            return entry.response_data

    4. MISS - Return None
    logger.debug("Cache miss")
    return None

    Why two tiers?
    ─────────────
    Memory cache:
    ✓ Super fast (dict lookup)
    ✗ Lost on restart
    ✓ Short TTL to prevent stale data

    Database cache:
    ✓ Persistent across restarts
    ✓ Shared across processes (if needed)
    ✗ Slightly slower (SQL query)
    ✓ Configurable TTL per endpoint
    """
```

### Cache Statistics

```python
async def get_stats(self) -> dict[str, Any]:
    """
    Get cache statistics.

    Example output:
    {
        "total_entries": 150,      # Total cached items
        "active_entries": 120,     # Not expired
        "expired_entries": 30,     # Still in DB but expired
        "total_hits": 5000,        # How many times was cache used?
        "memory_entries": 15,      # In-memory cache size
        "by_endpoint": {
            "site_detail": 45,     # 45 cached sites
            "scene_search": 75,    # 75 search results
            "movie_detail": 30     # 30 movies
        }
    }

    Why track this?
    - See if caching is effective
    - Identify hot endpoints (many hits)
    - Optimize TTL (if movie_detail has 1 hit but 24hr TTL, reduce it)
    - Debug issues (is cache being used?)
    """
```

---

## Match Service Deep Dive

### Show Matching Logic

```python
async def match_show(self, request: MatchRequest, language: str = "en") -> MediaContainer:
    """
    Match a show (site/studio) request from Plex.

    Input from Plex:
    {
        "type": 2,                    # MetadataType.SHOW
        "title": "Brazzers",          # Show title to search
        "year": 2024,                 # Optional year
        "guid": "tpdb://site-uuid",   # Optional previous match ID
        "includeExternalMediaSources": True
    }

    Process:
    ────────
    1. CHECK FOR GUID (previous match)
    if request.guid and request.guid.startswith("tpdb://"):
        site_id = request.guid.replace("tpdb://", "")
        # If we have a GUID, directly fetch that site
        # User might want to re-match to the same site
        # Or this might be cached from a previous match
        response = await client.get_site(site_id)
        site_data = response.get("data", {})
        # Convert to Plex format
        metadata.append(ShowMapper.site_to_show(site_data))

    2. SEARCH BY TITLE (if no GUID match or GUID failed)
    if not metadata and request.title:
        response = await client.search_sites(
            q=request.title,    # "Brazzers"
            per_page=10         # Return top 10 matches
        )
        # Plex will rank these by relevance and show to user
        for site_data in response.get("data", []):
            metadata.append(ShowMapper.site_to_show(site_data))

    3. RETURN RESULTS
    return MediaContainer(
        offset=0,
        totalSize=len(metadata),  # How many matches found?
        identifier=TV_PROVIDER_IDENTIFIER,
        size=len(metadata),
        Metadata=metadata           # List of match results
    )

    Example TPDB response:
    {
        "data": [
            {
                "id": "uuid-123",
                "name": "Brazzers",
                "slug": "brazzers",
                "description": "One of the largest porn sites...",
                "logo": "https://...",
                "poster": "https://..."
            },
            {
                "id": "uuid-456",
                "name": "Brazzers HD",
                "slug": "brazzers-hd",
                ...
            }
        ],
        "meta": {
            "current_page": 1,
            "per_page": 10,
            "total": 2
        }
    }

    What Plex does next:
    ────────────────────
    1. Shows user a list of matches
    2. User selects "Brazzers" (uuid-123)
    3. Plex stores GUID: "tpdb://uuid-123"
    4. For future metadata requests, Plex will use this GUID
    5. Plex asks: GET /tv/library/metadata/tpdb-site-uuid-123
    """
```

### Episode Matching Logic

```python
async def match_episode(self, request: MatchRequest, language: str = "en") -> MediaContainer:
    """
    Match an episode (scene).

    Input from Plex:
    {
        "type": 4,                          # MetadataType.EPISODE
        "title": "Amazing Scene Title",     # Scene title to search
        "parentIndex": 2024,                # Season (year in our case)
        "index": 5,                         # Episode number
        "date": "2024-01-15",              # Release date
        "grandparentTitle": "Brazzers",    # Parent show name
        "guid": "tpdb://scene-uuid"        # Previous match ID
    }

    Process:
    ────────
    1. BUILD SEARCH PARAMS
    search_params = {"per_page": 10}  # Return top 10

    2. ADD TITLE IF PROVIDED
    if request.title:
        search_params["q"] = request.title

    3. FIND PARENT SITE (if provided)
    if request.grandparentTitle:
        # User has already matched the parent show
        # Let's search for scenes ONLY from that site
        site_response = await client.search_sites(
            q=request.grandparentTitle,  # "Brazzers"
            per_page=1  # Just need one match
        )
        sites = site_response.get("data", [])
        if sites:
            # Use site slug to filter scene search
            search_params["site"] = sites[0].get("slug")  # "brazzers"

    4. ADD DATE FILTER (if provided)
    if request.date:
        search_params["date"] = request.date  # "2024-01-15"

    5. SEARCH SCENES
    response = await client.search_scenes(**search_params)
    # Request to TPDB API with filtering

    6. CONVERT RESULTS
    for idx, scene_data in enumerate(response.get("data", []), start=1):
        metadata.append(
            ShowMapper.scene_to_episode(scene_data, episode_index=idx)
        )

    Example: User has file "Brazzers.2024.01.15.Scene.Name.mp4"
    Plex might send:
    {
        "title": "Brazzers 2024 01 15 Scene Name",
        "grandparentTitle": "Brazzers",
        "date": "2024-01-15",
        "index": 1
    }

    Our match process:
    1. Find Brazzers site (slug: "brazzers")
    2. Search scenes: q="Brazzers 2024 01 15 Scene Name" AND site="brazzers" AND date="2024-01-15"
    3. TPDB returns matching scenes
    4. Return top results to Plex
    5. User selects the correct scene
    6. Plex stores GUID: "tpdb://scene-uuid-789"
    """
```

---

## Metadata Service Deep Dive

### Rating Key Parsing

```python
# Rating keys identify items uniquely
# Format: "tpdb-[type]-[id]"

Examples:
"tpdb-site-brazzers"          # Site named "brazzers"
"tpdb-season-brazzers-2024"   # 2024 season of Brazzers
"tpdb-scene-uuid-789"         # Scene with UUID
"tpdb-movie-uuid-456"         # Movie with UUID

How they're parsed:
──────────────────
def parse_rating_key(key: str) -> dict:
    # "tpdb-site-brazzers" → {
    #   "type": "site",
    #   "site_slug": "brazzers"
    # }

    # "tpdb-season-brazzers-2024" → {
    #   "type": "season",
    #   "site_slug": "brazzers",
    #   "year": 2024
    # }

    # "tpdb-scene-uuid-789" → {
    #   "type": "scene",
    #   "scene_id": "uuid-789"
    # }
```

### Metadata Retrieval Flow

```python
async def get_metadata(
    self,
    rating_key: str,      # e.g., "tpdb-site-brazzers"
    provider_identifier: str,  # e.g., TV_PROVIDER_IDENTIFIER
    language: str = "en"
) -> MediaContainer:
    """
    Get full metadata for an item.

    Flow for a site:
    1. Parse rating_key → {"type": "site", "site_slug": "brazzers"}
    2. Fetch site data: await self._get_site("brazzers")
    3. Convert to Plex format: ShowMapper.site_to_show(site_data)
    4. Return wrapped in MediaContainer

    Example Plex Site Response:
    {
        "MediaContainer": {
            "offset": 0,
            "totalSize": 1,
            "identifier": "tv.plex.agents.tpdb.tv",
            "size": 1,
            "Metadata": [
                {
                    "key": "tpdb-site-brazzers",
                    "type": "show",
                    "title": "Brazzers",
                    "summary": "Long description...",
                    "thumb": "https://...",
                    "art": "https://...",
                    "year": 2024
                }
            ]
        }
    }
    """
```

### Getting Site Years (Seasons)

```python
async def _get_site_years(self, site_slug: str) -> list[int]:
    """
    Get list of years where scenes exist.

    Why?
    - In Plex, seasons are groupings
    - We use years as seasons
    - Need to fetch all years to show all seasons

    Process:
    1. Fetch first 100 scenes from site
    2. Extract year from each scene's date
    3. Return sorted unique years

    Example:
    - Scene 1: date = "2024-12-15" → year 2024
    - Scene 2: date = "2024-06-10" → year 2024
    - Scene 3: date = "2023-11-20" → year 2023

    Result: [2024, 2023]

    Cache for 1 hour: years don't change that often

    Limitation:
    - Only fetches first 100 scenes
    - If a site has scenes from 2010 but only shows 100 recent,
      we won't see 2010
    - TODO: Paginate through all scenes to find all years
    """
```

---

## Plex Format Conversion

### How TPDB Data Becomes Plex Metadata

```python
# TPDB API returns raw data:
tpdb_site = {
    "id": "uuid-123",
    "name": "Brazzers",
    "slug": "brazzers",
    "description": "One of the largest...",
    "logo": "https://...",
    "poster": "https://..."
}

# We convert to Plex format:
plex_show = {
    "key": "tpdb-site-brazzers",      # Rating key for Plex
    "type": "show",                    # Must be "show" for TV
    "title": "Brazzers",
    "summary": "One of the largest...",
    "thumb": "https://...",            # Logo as thumbnail
    "art": "https://...",              # Poster as background art
    "year": 2024,                      # Current year (or first scene year)
    "contentRating": "R",              # Adult content
    "originals": True,                 # Mark as original content
}

# TPDB Scene → Plex Episode
tpdb_scene = {
    "id": "uuid-789",
    "title": "Hot Scene Title",
    "date": "2024-01-15",
    "duration": 1800,  # seconds
    "performers": [
        {"name": "Performer A"},
        {"name": "Performer B"}
    ],
    "image": "https://..."
}

plex_episode = {
    "key": "tpdb-scene-uuid-789",      # Rating key
    "type": "episode",
    "title": "Hot Scene Title",
    "summary": "Scene description",
    "thumb": "https://...",
    "duration": 1800000,               # milliseconds (1800 * 1000)
    "airDate": "2024-01-15",
    "index": 1,                        # Episode number
    "parentIndex": 2024,               # Season (year)
    "grandparentKey": "tpdb-site-brazzers",
    "grandparentTitle": "Brazzers",
    "rating": "9.0",                   # Could use views/popularity
    "addedAt": 1234567890,             # Unix timestamp
    "updatedAt": 1234567890,
    "Guest": [                         # Actors
        {"tag": "Performer A"},
        {"tag": "Performer B"}
    ]
}

Why this conversion?
───────────────────
Plex has a specific XML/JSON format it expects.
Keys like "key", "type", "thumb" have special meanings.
We must conform to Plex's MediaProvider specification.
```

---

## Request/Response Flow

### Complete TV Match Request

```
CLIENT REQUEST
──────────────

POST /tv/library/metadata/matches HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
    "type": 4,
    "title": "Scene Title",
    "grandparentTitle": "Brazzers",
    "date": "2024-01-15"
}

SERVER PROCESSING
─────────────────

1. FastAPI route handler (tv.py:match_content)
   - Parse request body as MatchRequest
   - Route to match_service.match_episode()

2. Match service (match_service.py:match_episode)
   - Build search parameters
   - Call client.search_scenes()
   - Get TPDB response with scene data
   - Convert scenes to Plex format

3. TPDB client (tpdb_client.py:search_scenes)
   - Apply rate limiter: await limiter.acquire()
   - Make HTTP request to TPDB API
   - Handle errors and convert to exceptions

4. Rate limiter (rate_limiter.py:acquire)
   - Check if tokens available
   - If not, wait until available
   - Consume token from bucket

SERVER RESPONSE
───────────────

HTTP/1.1 200 OK
Content-Type: application/json

{
    "MediaContainer": {
        "offset": 0,
        "totalSize": 3,
        "identifier": "tv.plex.agents.tpdb.tv",
        "size": 3,
        "Metadata": [
            {
                "key": "tpdb-scene-uuid-1",
                "type": "episode",
                "title": "Scene Title",
                "thumb": "https://...",
                "index": 1,
                "parentIndex": 2024
            },
            {
                "key": "tpdb-scene-uuid-2",
                "type": "episode",
                "title": "Scene Title - Alternate",
                ...
            },
            ...
        ]
    }
}

CLIENT ACTION
─────────────
Plex displays these 3 matches to the user.
User selects one.
Plex stores the "key" as GUID for future lookups.
```

### Complete Metadata Request

```
CLIENT REQUEST
──────────────

GET /tv/library/metadata/tpdb-scene-uuid-1 HTTP/1.1
Host: localhost:8000
X-Plex-Language: en

SERVER PROCESSING
─────────────────

1. FastAPI route handler (tv.py:get_metadata)
   - Extract rating_key from URL: "tpdb-scene-uuid-1"
   - Call metadata_service.get_metadata()

2. Metadata service (metadata_service.py:get_metadata)
   - Parse rating_key → {"type": "scene", "scene_id": "uuid-1"}
   - Call _get_scene("uuid-1")

3. Get scene with caching (metadata_service.py:_get_scene)
   - Check cache for "scene_detail" with params {"scene_id": "uuid-1"}
   - Cache HIT: Return cached scene data
   - Cache MISS: Fetch from TPDB, cache result, return

4. TPDB client (tpdb_client.py:get_scene)
   - Apply rate limiter
   - Make HTTP request to https://api.theporndb.net/scenes/uuid-1
   - Return scene JSON

5. Convert to Plex format (show_mapper.py:scene_to_episode)
   - Map TPDB fields to Plex fields
   - Format performers list
   - Convert duration to milliseconds
   - Return MetadataItem

6. Create response (metadata_service.py:get_metadata)
   - Wrap MetadataItem in MediaContainer
   - Return to route handler

SERVER RESPONSE
───────────────

HTTP/1.1 200 OK
Content-Type: application/json

{
    "MediaContainer": {
        "offset": 0,
        "totalSize": 1,
        "identifier": "tv.plex.agents.tpdb.tv",
        "size": 1,
        "Metadata": [
            {
                "key": "tpdb-scene-uuid-1",
                "type": "episode",
                "title": "Hot Scene",
                "summary": "Description here...",
                "thumb": "https://thumb.jpg",
                "duration": 1800000,  # 30 minutes in ms
                "airDate": "2024-01-15",
                "year": 2024,
                "index": 1,
                "parentIndex": 2024,
                "grandparentKey": "tpdb-site-brazzers",
                "grandparentTitle": "Brazzers",
                "Guest": [
                    {"tag": "Performer Name"}
                ],
                "addedAt": 1234567890
            }
        ]
    }
}

CLIENT ACTION
─────────────
Plex displays the full metadata in the UI.
Shows title, description, performers, thumbnail, runtime, etc.
```

---

## Error Handling Examples

### Handling Missing Resources

```python
async def _get_scene(self, scene_id: str) -> Optional[dict[str, Any]]:
    """
    Get scene data, returning None if not found.
    """
    cache = self._get_cache()
    client = await self._get_client()

    async def fetch() -> dict[str, Any]:
        response = await client.get_scene(scene_id)
        return response.get("data", {})

    try:
        return await cache.get_or_fetch(
            "scene_detail",
            {"scene_id": scene_id},
            fetch,
        )
    except TPDBNotFoundError:
        # Scene doesn't exist on TPDB
        logger.warning("Scene not found", scene_id=scene_id)
        return None  # Return None gracefully
        # Plex will show "no metadata found" to user
```

### Handling Rate Limit Errors

```python
async def _request(self, method: str, endpoint: str, ...) -> dict[str, Any]:
    """
    Make API request with rate limiting and error handling.
    """
    # Apply rate limiting
    await self._rate_limiter.acquire()  # Will wait if needed

    try:
        async with session.request(method, url, ...) as response:
            if response.status == 429:
                # Rate limited by TPDB
                raise TPDBRateLimitError(
                    "TPDB rate limit exceeded",
                    status_code=429
                )
            elif response.status == 404:
                # Not found
                raise TPDBNotFoundError(
                    f"Resource not found: {endpoint}",
                    status_code=404
                )
            elif response.status >= 400:
                # Other error (500, 403, etc.)
                text = await response.text()
                raise TPDBError(
                    f"TPDB API error: {text}",
                    status_code=response.status
                )

            data = await response.json()
            return data

    except aiohttp.ClientError as e:
        # Network error (timeout, connection refused, etc.)
        logger.error("TPDB request failed", error=str(e), url=url)
        raise TPDBError(f"Request failed: {str(e)}")
```

---

## Performance Considerations

### Why Async?

```python
# WITHOUT async - Blocking approach
def get_multiple_scenes(scene_ids: list[str]):
    results = []
    for scene_id in scene_ids:  # Process one by one
        response = requests.get(f"{url}/scenes/{scene_id}")  # BLOCKS
        results.append(response.json())
    return results

# Time: 3 scenes × 1 second per request = 3 seconds

# WITH async - Concurrent approach
async def get_multiple_scenes(scene_ids: list[str]):
    tasks = [
        client.get_scene(scene_id)  # Create tasks (not waiting)
        for scene_id in scene_ids
    ]
    results = await asyncio.gather(*tasks)  # Run concurrently
    return results

# Time: 1 second (all three requests happen simultaneously)
```

### Cache Hit Rate Impact

```python
# Without caching
100 requests × 1 second per TPDB call = 100 seconds
(and risk of rate limiting)

# With caching
- First request: MISS → 1 second (cached for 5 minutes)
- Next 59 requests: HIT → ~50ms each (dict lookup)
- Request 60: MISS → 1 second (cache expired, re-fetch)

Total time: ~1 second + (59 × 0.05 sec) = ~4 seconds
Savings: 96 seconds! (96% faster)
API calls reduced: 100 → ~2
```

---

## Summary of Key Concepts

| Concept | Purpose | Key File |
|---------|---------|----------|
| **Token Bucket Rate Limiter** | Prevent exceeding API limits | `rate_limiter.py` |
| **Multi-Tier Cache** | Reduce API calls with memory + DB | `cache_service.py` |
| **Service Layer** | Business logic abstraction | `match_service.py`, `metadata_service.py` |
| **Dependency Injection** | Testable, loose coupling | `routes/tv.py` |
| **Async/Await** | Fast concurrent I/O | Throughout |
| **Plex Format Conversion** | Convert TPDB → Plex XML | `mappers/` |
| **Rating Keys** | Unique item identifiers | `constants.py` |
| **Structured Logging** | Context-aware debugging | `main.py` |

