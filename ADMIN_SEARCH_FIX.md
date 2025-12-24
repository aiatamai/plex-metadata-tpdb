# Admin Dashboard Search Fix

### Problem

The search function in the admin dashboard was not working. When users tried to search for content, they would get an error:
```
"Failed to search. Please check your API configuration."
```

## Root Cause

The frontend (search.html) was trying to call an API endpoint that didn't exist:
```javascript
const response = await fetch(`/api/v1/${this.searchType}?q=${encodeURIComponent(this.query)}`);
// This would call: /api/v1/scenes?q=...
// /api/v1/performers?q=...
// etc.
```

The application never had these `/api/v1/*` endpoints implemented.

## Solution

I've implemented the missing search API endpoint that:

1. **Created a new endpoint**: `/admin/api/search`
2. **Supports all search types**: scenes, sites, movies, performers
3. **Uses TPDB client directly**: Calls ThePornDB API with your API key
4. **Returns standardized JSON**: Formatted for the UI to display
5. **Includes proper authentication**: Uses HTTP Basic auth (same as admin dashboard)
6. **Includes error handling**: Gracefully handles TPDB API errors

---

## Files Changed

### 1. `app/web/router.py` - Added Search API Endpoint

**What was added:**
- New endpoint: `GET /admin/api/search`
- Query parameters:
  - `q` (required): Search query string (1-255 characters)
  - `type` (optional): Search type - `scenes`, `sites`, `movies`, or `performers` (default: `scenes`)

**How it works:**
```
User searches → Frontend calls /admin/api/search?q=query&type=scenes
              → Router calls TPDBClient.search_scenes()
              → Returns standardized JSON response
              → Frontend displays results
```

**Example requests:**
```bash
# Search for scenes
curl "http://localhost:8000/admin/api/search?q=brazzers&type=scenes" \
  -u admin:password

# Search for sites
curl "http://localhost:8000/admin/api/search?q=brazzers&type=sites" \
  -u admin:password

# Search for performers
curl "http://localhost:8000/admin/api/search?q=performer+name&type=performers" \
  -u admin:password

# Search for movies
curl "http://localhost:8000/admin/api/search?q=movie+title&type=movies" \
  -u admin:password
```

**Example response:**
```json
{
  "data": [
    {
      "id": "scene-uuid-123",
      "title": "Scene Title",
      "date": "2024-01-15",
      "description": "Scene description",
      "image": "https://...",
      "poster": "https://...",
      "site": {"name": "Brazzers", "id": "..."},
      "performers": [{"name": "Performer Name", ...}],
      "type": "scene"
    },
    ...
  ],
  "count": 1,
  "type": "scenes"
}
```

**Error handling:**
- Invalid search type → 400 Bad Request
- TPDB API error → 500 Internal Server Error with error message
- No results found → 200 OK with empty data array

### 2. `app/web/templates/search.html` - Updated Frontend

**What changed:**
- Updated the API endpoint from `/api/v1/{type}` to `/admin/api/search`
- Added error message logging to browser console
- Improved error handling with more descriptive messages

**Before:**
```javascript
const response = await fetch(`/api/v1/${this.searchType}?q=${encodeURIComponent(this.query)}`);
```

**After:**
```javascript
const response = await fetch(
    `/admin/api/search?q=${encodeURIComponent(this.query)}&type=${encodeURIComponent(this.searchType)}`
);
```

---

## How It Works Now

### Step-by-Step Flow

```
1. User opens admin dashboard
   └─ http://localhost:8000/admin

2. User logs in with credentials
   └─ HTTP Basic Auth (admin_username, admin_password)

3. User clicks "Search TPDB"
   └─ Navigates to http://localhost:8000/admin/search

4. User enters search query (e.g., "Brazzers")
   └─ Selects search type (e.g., "Sites")

5. User clicks Search button
   └─ Frontend calls /admin/api/search with query and type

6. Backend processes request
   a. Verifies HTTP Basic credentials
   b. Validates search type
   c. Calls TPDBClient with appropriate search method
   d. TPDBClient applies rate limiting (2 req/sec)
   e. TPDBClient makes HTTP request to ThePornDB API
   f. Results are formatted for UI display

7. Response returned to frontend
   └─ {data: [...], count: N, type: "scenes"}

8. Frontend displays results
   └─ Shows thumbnails, titles, descriptions, etc.
```

### Data Flow Diagram

```
Browser (search.html)
    │
    ├─ User enters query: "Brazzers"
    ├─ User selects type: "Sites"
    │
    └─→ fetch("/admin/api/search?q=Brazzers&type=sites")
        │
        └─→ [HTTP request with Basic Auth credentials]
            │
            └─→ router.py:search_tpdb()
                │
                ├─ verify_credentials() → Check HTTP Basic Auth
                │
                ├─ Validate search type ("sites" is valid)
                │
                ├─ await client.search_sites(q="Brazzers", per_page=25)
                │   │
                │   └─→ tpdb_client.py:search_sites()
                │       │
                │       ├─ Apply rate limiter (token bucket)
                │       ├─ Make HTTP request to https://api.theporndb.net/sites?q=Brazzers
                │       └─ Return TPDB API response
                │
                ├─ Flatten results for UI display
                │   └─ Extract: id, name, slug, description, logo, poster, type
                │
                └─→ Return JSON: {data: [...], count: 2, type: "sites"}
                    │
                    └─→ Browser receives response
                        │
                        └─→ Frontend displays results with images and descriptions
```

---

## Testing the Fix

### 1. Start the Application
```bash
export TPDB_API_KEY=your_api_key_here
python -m app.main
```

### 2. Access the Admin Dashboard
```
http://localhost:8000/admin
Username: admin
Password: change_me_in_production
```

### 3. Navigate to Search
Click "Search TPDB" or go to:
```
http://localhost:8000/admin/search
```

### 4. Test Searches

**Test 1: Search for Sites**
- Query: "Brazzers"
- Type: "Sites"
- Expected: 1-2 results with site logos

**Test 2: Search for Scenes**
- Query: "scene name"
- Type: "Scenes"
- Expected: Multiple scene results with thumbnails

**Test 3: Search for Performers**
- Query: "performer name"
- Type: "Performers"
- Expected: Performer results with images

**Test 4: Search for Movies**
- Query: "movie title"
- Type: "Movies"
- Expected: Movie results with posters

### 5. Test Error Handling

**Invalid search type:**
```bash
curl "http://localhost:8000/admin/api/search?q=test&type=invalid" \
  -u admin:password
```
Expected: 400 Bad Request with error message

**Unauthenticated request:**
```bash
curl "http://localhost:8000/admin/api/search?q=test&type=scenes"
```
Expected: 401 Unauthorized

---

## API Endpoint Details

### Endpoint: `GET /admin/api/search`

**Path:** `/admin/api/search`

**Authentication:** HTTP Basic Auth (required)

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query (1-255 characters) |
| `type` | string | No | Search type: `scenes`, `sites`, `movies`, `performers` (default: `scenes`) |

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "string",
      "title": "string or null",
      "name": "string or null",
      "date": "string or null",
      "description": "string or null",
      "image": "url or null",
      "poster": "url or null",
      "logo": "url or null",
      "site": "object or null",
      "studio": "object or null",
      "performers": "array or null",
      "type": "scene|site|movie|performer"
    }
  ],
  "count": 0,
  "type": "scenes|sites|movies|performers"
}
```

**Error Responses:**

400 Bad Request:
```json
{"detail": "Invalid search type. Must be one of: scenes, sites, movies, performers"}
```

401 Unauthorized:
```json
{"detail": "Invalid credentials"}
```

500 Internal Server Error:
```json
{"detail": "TPDB API error: ..."}
```

---

## Implementation Details

### Search Type Handling

#### Scenes Search
- **TPDB Method**: `client.search_scenes(q=query, per_page=25)`
- **Fields Returned**: id, title, date, description, image, poster, site, performers
- **UI Display**: Thumbnail + title + date + description + performers

#### Sites Search
- **TPDB Method**: `client.search_sites(q=query, per_page=25)`
- **Fields Returned**: id, name, slug, description, logo, poster
- **UI Display**: Logo as thumbnail + name + description

#### Movies Search
- **TPDB Method**: `client.search_movies(q=query, per_page=25)`
- **Fields Returned**: id, title, year, date, description, image, poster, studio, performers
- **UI Display**: Poster + title + year + description + performers

#### Performers Search
- **TPDB Method**: `client.search_performers(q=query, per_page=25)`
- **Fields Returned**: id, name, slug, bio, image, gender, birthdate
- **UI Display**: Image + name + bio + gender + birthdate

### Authentication Flow

1. User makes request to `/admin/api/search`
2. FastAPI extracts HTTP Basic Auth credentials from request headers
3. `verify_credentials()` dependency checks:
   - Username matches `ADMIN_USERNAME` (from config)
   - Password matches `ADMIN_PASSWORD` (from config)
4. If valid, request proceeds; if invalid, returns 401 Unauthorized
5. Authenticated username is logged for audit trail

### Error Handling

**TPDB API Errors:**
```python
try:
    response = await client.search_scenes(q=q, per_page=25)
except TPDBNotFoundError:
    # Return empty results (200 OK, empty data)
except TPDBError as e:
    # Return 500 Internal Server Error with error message
```

**Frontend Error Display:**
- If search fails: Shows error message in red box
- Console logging: Detailed error logged to browser console for debugging
- User-friendly: "Search error: {error message}"

---

## Performance Considerations

### Rate Limiting
- Each search request applies rate limiting
- Max: 2 requests/second to TPDB API
- If limit exceeded: Request waits for tokens to refill

### Result Limiting
- Each search returns max 25 results (per_page=25)
- This balances completeness with response time
- Can be adjusted by changing per_page parameter

### No Caching
- Admin search results are NOT cached
- Ensures fresh, up-to-date results
- Slightly slower but more accurate
- (Optional: Could cache with short TTL if needed)

---

## Troubleshooting

### Issue: "Search error: Invalid credentials"
**Cause**: Wrong admin username/password
**Fix**: Check your ADMIN_USERNAME and ADMIN_PASSWORD settings

### Issue: "Search error: Search failed"
**Cause**: Network error or TPDB API down
**Fix**:
- Check TPDB_API_KEY is set
- Verify TPDB API is accessible
- Check browser console for detailed error

### Issue: "Search error: Invalid search type"
**Cause**: Frontend sent invalid type (shouldn't happen)
**Fix**: Check browser console, reload page

### Issue: Search is slow
**Cause**: TPDB API response time or rate limiting
**Fix**:
- Check TPDB API status
- Try simpler search query
- Wait for rate limiter tokens (2 req/sec)

### Issue: No results returned
**Cause**: No matches in TPDB for that query
**Fix**: Try different search terms

---

## Future Improvements

### Optional Enhancements

1. **Add caching** for search results (5-minute TTL)
   - Improves performance for repeated searches
   - Add to `cache_service.py`

2. **Pagination support** for large result sets
   - Add `page` parameter
   - Show "Load more" button in UI

3. **Filter options**
   - Filter by date range
   - Filter by site (for scene search)
   - Filter by year (for movie search)

4. **Search history**
   - Track recent searches
   - Quick access to previous searches

5. **Advanced search**
   - AND/OR operators
   - Negative search (exclude terms)

6. **Results sorting**
   - Sort by relevance
   - Sort by date
   - Sort by popularity

---

## Summary

The admin dashboard search is now fully functional! Users can:

✅ Search for Scenes by title, performer, or keywords
✅ Search for Sites/Studios by name
✅ Search for Movies by title
✅ Search for Performers by name
✅ View results with images and descriptions
✅ Authenticated access with HTTP Basic Auth

The implementation:
- Uses the TPDB API directly (via tpdb_client)
- Returns results in a standardized JSON format
- Includes proper error handling
- Respects rate limits
- Logs searches for auditing
- Integrates seamlessly with existing code

