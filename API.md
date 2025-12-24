# Plex ThePornDB Provider - API Documentation

Complete API reference for the Plex Media Provider that integrates with ThePornDB.

**Base URL**: `http://localhost:8000`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Provider Definition](#provider-definition)
4. [TV Provider API](#tv-provider-api)
5. [Movie Provider API](#movie-provider-api)
6. [Admin API](#admin-api)
7. [Health & Status](#health--status)
8. [Error Handling](#error-handling)
9. [Rate Limiting](#rate-limiting)
10. [Response Format](#response-format)
11. [Examples](#examples)

---

## Overview

This API implements the **Plex MediaProvider specification**, allowing Plex Media Server to:
- Discover this provider
- Request metadata matches for files
- Retrieve full metadata for matched items
- Manage hierarchical content (shows → seasons → episodes)

### Provider Types

| Provider | Endpoint | Description |
|----------|----------|---|
| **TV** | `/tv` | Sites as Shows, Scenes as Episodes |
| **Movie** | `/movie` | Full-length Movies |
| **Admin** | `/admin` | Management & Search Interface |

### Content Mapping

```
ThePornDB          →  Plex
─────────────         ──────
Site (Studio)      →  Show
Scene              →  Episode
Release Year       →  Season
Movie              →  Movie
Performer          →  Actor
```

---

## Authentication

### Plex Provider API (TV & Movie)

**No authentication required** - Plex directly calls these endpoints

The provider is registered in Plex with a URL like:
```
http://your-server:8000/tv
http://your-server:8000/movie
```

### Admin API

**HTTP Basic Authentication** required for admin endpoints

```bash
# Example
curl -u admin:password http://localhost:8000/admin/api/search?q=test
```

Configure credentials via environment variables:
- `ADMIN_USERNAME` (default: "admin")
- `ADMIN_PASSWORD` (default: "change_me_in_production")

---

## Provider Definition

### TV Provider Definition

**Request**
```
GET /tv
```

**Response (XML)**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<MediaProvider identifier="tv.plex.agents.tpdb.tv" title="ThePornDB TV Provider" version="1.0.0">
  <PlexFeatures>
    <Feature type="metadata">
      <Argument name="ScannerIdentifier">com.plexapp.scanners.series</Argument>
    </Feature>
  </PlexFeatures>
</MediaProvider>
```

### Movie Provider Definition

**Request**
```
GET /movie
```

**Response (XML)**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<MediaProvider identifier="tv.plex.agents.tpdb.movie" title="ThePornDB Movie Provider" version="1.0.0">
  <PlexFeatures>
    <Feature type="metadata">
      <Argument name="ScannerIdentifier">com.plexapp.scanners.movie</Argument>
    </Feature>
  </PlexFeatures>
</MediaProvider>
```

---

## TV Provider API

### 1. Match Shows/Seasons/Episodes

**Request**
```
POST /tv/library/metadata/matches
Content-Type: application/json

{
  "type": 2,
  "title": "Show Title",
  "year": 2024,
  "grandparentTitle": "Parent Show",
  "parentIndex": 2024,
  "index": 1,
  "date": "2024-01-15",
  "guid": "tpdb://site-uuid"
}
```

**Parameters**

| Field | Type | Description |
|-------|------|---|
| `type` | int | Metadata type: 2=show, 3=season, 4=episode |
| `title` | string | Item title to match |
| `year` | int | Release year (optional) |
| `grandparentTitle` | string | Parent show name (for seasons/episodes) |
| `parentIndex` | int | Season number (for episodes) |
| `index` | int | Episode number |
| `date` | string | Release date YYYY-MM-DD |
| `guid` | string | Previous match ID (format: tpdb://uuid) |

**Response (200 OK)**
```json
{
  "MediaContainer": {
    "offset": 0,
    "totalSize": 10,
    "identifier": "tv.plex.agents.tpdb.tv",
    "size": 10,
    "Metadata": [
      {
        "key": "tpdb-site-brazzers",
        "type": "show",
        "title": "Brazzers",
        "summary": "One of the largest...",
        "thumb": "https://...",
        "art": "https://...",
        "year": 2024
      }
    ]
  }
}
```

**Match Logic**

| Type | Search Method | Returns |
|------|---|---|
| 2 (show) | By title | List of matching sites |
| 3 (season) | By parent + index | Year-based season |
| 4 (episode) | By title + parent | List of matching scenes |

### 2. Get Item Metadata

**Request**
```
GET /tv/library/metadata/{rating_key}
X-Plex-Language: en
```

**Parameters**

| Parameter | Type | Description |
|-----------|------|---|
| `rating_key` | string | Item identifier (e.g., `tpdb-site-brazzers`) |
| `X-Plex-Language` | header | Preferred language (optional) |

**Response (200 OK)**
```json
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
        "summary": "Long description",
        "thumb": "https://...",
        "art": "https://...",
        "year": 2024,
        "contentRating": "R",
        "originals": true
      }
    ]
  }
}
```

### 3. Get Children (Seasons/Episodes)

**Request**
```
GET /tv/library/metadata/{rating_key}/children
X-Plex-Language: en
X-Plex-Container-Start: 0
X-Plex-Container-Size: 50
```

**Parameters**

| Parameter | Type | Description |
|-----------|------|---|
| `rating_key` | string | Parent item ID |
| `X-Plex-Language` | header | Preferred language |
| `X-Plex-Container-Start` | header | Pagination offset |
| `X-Plex-Container-Size` | header | Results per page |

**Response (200 OK)**
```json
{
  "MediaContainer": {
    "offset": 0,
    "totalSize": 5,
    "identifier": "tv.plex.agents.tpdb.tv",
    "size": 5,
    "Metadata": [
      {
        "key": "tpdb-season-brazzers-2024",
        "type": "season",
        "title": "2024",
        "parentKey": "tpdb-site-brazzers",
        "parentTitle": "Brazzers",
        "index": 2024,
        "thumb": "https://..."
      }
    ]
  }
}
```

---

## Movie Provider API

### 1. Match Movies

**Request**
```
POST /movie/library/metadata/matches
Content-Type: application/json

{
  "type": 1,
  "title": "Movie Title",
  "year": 2024,
  "guid": "tpdb://movie-uuid"
}
```

**Parameters**

| Field | Type | Description |
|-------|------|---|
| `type` | int | Metadata type: 1=movie |
| `title` | string | Movie title to match |
| `year` | int | Release year (optional) |
| `guid` | string | Previous match ID |

**Response (200 OK)**
```json
{
  "MediaContainer": {
    "offset": 0,
    "totalSize": 5,
    "identifier": "tv.plex.agents.tpdb.movie",
    "size": 5,
    "Metadata": [
      {
        "key": "tpdb-movie-uuid-123",
        "type": "movie",
        "title": "Movie Title",
        "summary": "Movie description",
        "thumb": "https://...",
        "art": "https://...",
        "year": 2024,
        "duration": 7200000
      }
    ]
  }
}
```

### 2. Get Movie Metadata

**Request**
```
GET /movie/library/metadata/{rating_key}
X-Plex-Language: en
```

**Response (200 OK)**
```json
{
  "MediaContainer": {
    "offset": 0,
    "totalSize": 1,
    "identifier": "tv.plex.agents.tpdb.movie",
    "size": 1,
    "Metadata": [
      {
        "key": "tpdb-movie-uuid-123",
        "type": "movie",
        "title": "Movie Title",
        "summary": "Full description",
        "thumb": "https://...",
        "art": "https://...",
        "year": 2024,
        "duration": 7200000,
        "rating": 8.5,
        "Director": [
          {"tag": "Director Name"}
        ],
        "Guest": [
          {"tag": "Performer Name"}
        ]
      }
    ]
  }
}
```

---

## Admin API

### 1. Dashboard

**Request**
```
GET /admin
```

**Authentication**: HTTP Basic Auth required

**Response**: HTML dashboard with cache statistics and quick actions

### 2. Search TPDB

**Request**
```
GET /admin/api/search?q={query}&type={type}
```

**Authentication**: HTTP Basic Auth required

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|---|
| `q` | string | Yes | Search query (1-255 chars) |
| `type` | string | No | Search type: `scenes`, `sites`, `movies`, `performers` (default: `scenes`) |

**Response (200 OK)**
```json
{
  "data": [
    {
      "id": "uuid-123",
      "title": "Title",
      "date": "2024-01-15",
      "description": "Description",
      "image": "https://...",
      "poster": "https://...",
      "type": "scene"
    }
  ],
  "count": 25,
  "type": "scenes"
}
```

**Search Types**

| Type | Returns | Fields |
|------|---------|--------|
| `scenes` | Scene results | id, title, date, description, image, poster, site, performers |
| `sites` | Studio results | id, name, slug, description, logo, poster |
| `movies` | Movie results | id, title, year, date, description, image, poster, studio, performers |
| `performers` | Performer results | id, name, slug, bio, image, gender, birthdate |

### 3. Cache Management

**Request - Get Cache Stats**
```
GET /admin/cache
```

**Response**: HTML page with cache statistics

**Request - Clear Cache**
```
POST /admin/cache/clear
Content-Type: application/x-www-form-urlencoded

endpoint=site_detail
```

**Parameters**

| Parameter | Type | Description |
|-----------|------|---|
| `endpoint` | string | Cache endpoint to clear (optional, clears all if not specified) |

**Response**: Redirect to `/admin/cache`

**Request - Clear Expired Cache**
```
POST /admin/cache/clear-expired
```

**Response**: Redirect to `/admin/cache`

### 4. Settings

**Request**
```
GET /admin/settings
```

**Response**: HTML page showing configuration settings

---

## Health & Status

### Health Check

**Request**
```
GET /health
```

**Response (200 OK)**
```json
{
  "status": "healthy",
  "service": "tpdb-plex-provider"
}
```

### API Documentation

**Request**
```
GET /docs
```

**Response**: Interactive Swagger UI (debug mode only)

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Match or metadata retrieved |
| 400 | Bad Request | Invalid search type |
| 401 | Unauthorized | Missing/invalid auth credentials |
| 404 | Not Found | Resource doesn't exist in TPDB |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Server Error | TPDB API error or unexpected error |

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Errors

**Invalid Search Type**
```
Status: 400
{
  "detail": "Invalid search type. Must be one of: scenes, sites, movies, performers"
}
```

**Missing Authentication**
```
Status: 401
{
  "detail": "Invalid credentials"
}
```

**TPDB API Error**
```
Status: 500
{
  "detail": "TPDB API error: Unauthorized"
}
```

**Rate Limit Exceeded (TPDB)**
```
Status: 500
{
  "detail": "TPDB API error: Rate limit exceeded"
}
```

---

## Rate Limiting

### Outgoing Rate Limit (to TPDB)

- **Algorithm**: Token bucket
- **Rate**: 2 requests/second (configurable via `TPDB_RATE_LIMIT`)
- **Burst Size**: 5 requests
- **Behavior**: Requests wait if rate limit exceeded

### Incoming Rate Limit (to this API)

| Endpoint | Limit | Duration |
|----------|-------|----------|
| General endpoints | 100 | per minute |
| Search endpoints | 30 | per minute |

---

## Response Format

### MediaContainer (TV/Movie)

```json
{
  "MediaContainer": {
    "offset": 0,
    "totalSize": 10,
    "identifier": "provider-id",
    "size": 10,
    "Metadata": [
      {
        "key": "tpdb-type-id",
        "type": "show|season|episode|movie",
        "title": "Title",
        "summary": "Description",
        "thumb": "thumbnail-url",
        "art": "background-url",
        "year": 2024,
        "rating": 8.5,
        "duration": 1800000,
        "airDate": "2024-01-15",
        "contentRating": "R",
        "originals": true,
        "index": 1,
        "parentIndex": 2024,
        "parentKey": "parent-id",
        "parentTitle": "Parent Title",
        "grandparentKey": "grandparent-id",
        "grandparentTitle": "Grandparent Title",
        "Director": [{"tag": "Director Name"}],
        "Guest": [{"tag": "Performer Name"}],
        "Tag": [{"tag": "tag-name"}]
      }
    ]
  }
}
```

### Search Response

```json
{
  "data": [
    {
      "id": "unique-id",
      "title": "or name",
      "date": "2024-01-15",
      "description": "or bio",
      "image": "image-url",
      "poster": "poster-url",
      "logo": "logo-url",
      "type": "scene|site|movie|performer"
    }
  ],
  "count": 25,
  "type": "scenes"
}
```

---

## Examples

### Example 1: Match a Scene in Plex

```bash
# User has file: Brazzers.2024.01.15.Scene.Title.mp4
# Plex sends this request

curl -X POST http://localhost:8000/tv/library/metadata/matches \
  -H "Content-Type: application/json" \
  -d '{
    "type": 4,
    "title": "Brazzers 2024 01 15 Scene Title",
    "grandparentTitle": "Brazzers",
    "date": "2024-01-15"
  }' | jq .

# Response: List of matching scenes
# User selects the correct match
# Plex stores GUID: tpdb://scene-uuid
```

### Example 2: Get Full Scene Metadata

```bash
# After user selects a match, Plex requests full metadata

curl "http://localhost:8000/tv/library/metadata/tpdb-scene-uuid-123" | jq .

# Response: Full metadata with description, performers, images, etc.
```

### Example 3: Get Show Seasons

```bash
# User views show details, Plex gets seasons

curl "http://localhost:8000/tv/library/metadata/tpdb-site-brazzers/children?X-Plex-Container-Start=0&X-Plex-Container-Size=50" | jq .

# Response: List of years (2024, 2023, 2022, etc.) as seasons
```

### Example 4: Search Admin API

```bash
# Admin user searches for scenes

curl "http://localhost:8000/admin/api/search?q=brazzers&type=sites" \
  -u admin:change_me_in_production | jq .

# Response: Matching sites with logos and descriptions
```

### Example 5: Search Performers

```bash
# Search for a specific performer

curl "http://localhost:8000/admin/api/search?q=performer%20name&type=performers" \
  -u admin:change_me_in_production | jq .

# Response: Performer results with images and info
```

### Example 6: Match a Movie

```bash
# User has a full-length movie file

curl -X POST http://localhost:8000/movie/library/metadata/matches \
  -H "Content-Type: application/json" \
  -d '{
    "type": 1,
    "title": "Movie Title",
    "year": 2024
  }' | jq .

# Response: List of matching movies
```

---

## Rating Key Format

Rating keys are used to uniquely identify items in the provider.

### Format
```
tpdb-{type}-{id}
```

### Examples

| Item Type | Format | Example |
|-----------|--------|---------|
| Site/Show | `tpdb-site-{slug}` | `tpdb-site-brazzers` |
| Season | `tpdb-season-{slug}-{year}` | `tpdb-season-brazzers-2024` |
| Scene/Episode | `tpdb-scene-{uuid}` | `tpdb-scene-a1b2c3d4-e5f6` |
| Movie | `tpdb-movie-{uuid}` | `tpdb-movie-m1n2o3p4-q5r6` |
| Performer | `tpdb-performer-{uuid}` | `tpdb-performer-p1e2r3f4` |

---

## Caching Behavior

### Cache TTLs

| Endpoint | Default TTL | Description |
|----------|-------------|---|
| `site_list` | 24 hours | Site/studio lists |
| `site_detail` | 7 days | Individual site details |
| `scene_search` | 5 minutes | Scene search results |
| `scene_detail` | 24 hours | Individual scene metadata |
| `movie_detail` | 24 hours | Movie metadata |

### Cache Tiers

1. **Memory Cache** (fast, 5-min TTL)
   - In-process dictionary
   - Lost on restart
   - Fastest response (5-10ms)

2. **Database Cache** (persistent)
   - SQLite storage
   - Survives restart
   - Configurable TTL per endpoint
   - Moderate response time (50-100ms)

3. **Live API Call** (slow, no cache)
   - Direct TPDB API call
   - Always fresh data
   - Slowest response (1-2 seconds)

---

## Rate Limit Headers

Responses may include rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1234567890
```

---

## Webhook & Integration

### Plex Integration

This provider registers with Plex at the following URL:

```
http://your-server:8000/tv
http://your-server:8000/movie
```

Plex communicates exclusively via:
1. GET requests to discover provider capabilities
2. POST requests to match content
3. GET requests to retrieve metadata

### No Webhooks

This provider is **pull-based only**. It doesn't send webhooks or notifications to Plex. Plex initiates all communication.

---

## Testing API

### Health Check
```bash
curl http://localhost:8000/health
```

### TV Provider Definition
```bash
curl http://localhost:8000/tv
```

### Movie Provider Definition
```bash
curl http://localhost:8000/movie
```

### Test Search (requires auth)
```bash
curl "http://localhost:8000/admin/api/search?q=test&type=scenes" \
  -u admin:password
```

---

## Performance Considerations

### Response Times

| Operation | Time | Notes |
|-----------|------|-------|
| Cache hit (memory) | 5-10ms | In-process lookup |
| Cache hit (database) | 50-100ms | SQL query |
| API call (no cache) | 1-2 seconds | Network + TPDB processing |
| Rate-limited | +wait time | Automatic token refill |

### Optimization Tips

1. **Use results caching**: Scene search cached for 5 minutes
2. **Reduce queries**: Site details cached for 7 days
3. **Batch requests**: Get multiple items in one call when possible
4. **Enable Redis**: Faster caching if deployed at scale

---

## Versioning

**Current Version**: 1.0.0

**API Compatibility**: Follows Plex MediaProvider specification v1

Changes that maintain backward compatibility:
- Adding new optional fields
- Adding new endpoints
- Changing internal implementation

Changes that break compatibility:
- Removing required fields
- Changing response structure
- Removing endpoints

---

## Support & Issues

### Common Issues

**"Failed to search"**: Check TPDB_API_KEY is valid
**No results**: Try different search terms or check TPDB directly
**Slow responses**: Check rate limiting, network, or TPDB status
**Auth error**: Verify admin credentials in config

### Debugging

Enable debug mode for detailed logging:
```bash
DEBUG=true python -m app.main
```

Check logs for detailed error messages and request traces.

---

## Additional Resources

- [ThePornDB API Documentation](https://api.theporndb.net)
- [Plex MediaProvider Specification](https://github.com/plexinc/tmdb-example-provider)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- Project Documentation: See `API.md` (this file) and other .md files in project root

