# Admin Search Testing Guide

Quick guide to test the newly fixed admin search functionality.

## Prerequisites

✅ Application running: `python -m app.main`
✅ TPDB_API_KEY set: `export TPDB_API_KEY=your_key`
✅ Running on: http://localhost:8000

---

## Test 1: Web UI Search (Easiest)

### Steps

1. **Open Admin Dashboard**
   - URL: `http://localhost:8000/admin`
   - Username: `admin`
   - Password: `change_me_in_production` (or your custom password)

2. **Click "Search TPDB" button**
   - Navigates to: `http://localhost:8000/admin/search`

3. **Test Scene Search**
   - Query: `brazzers` (or any scene title)
   - Type: `Scenes`
   - Click Search
   - **Expected**: See 1+ scene results with thumbnails

4. **Test Site Search**
   - Query: `brazzers`
   - Type: `Sites`
   - Click Search
   - **Expected**: See Brazzers site with logo

5. **Test Performer Search**
   - Query: `[any popular performer name]`
   - Type: `Performers`
   - Click Search
   - **Expected**: See performer results with images

6. **Test Movie Search**
   - Query: `[any movie title]`
   - Type: `Movies`
   - Click Search
   - **Expected**: See movie results with posters

---

## Test 2: cURL API Testing

### Basic Scene Search
```bash
curl "http://localhost:8000/admin/api/search?q=brazzers&type=scenes" \
  -u admin:change_me_in_production | jq .
```

**Expected response:**
```json
{
  "data": [
    {
      "id": "...",
      "title": "...",
      "date": "2024-...",
      "description": "...",
      "type": "scene"
    }
  ],
  "count": 25,
  "type": "scenes"
}
```

### Site Search
```bash
curl "http://localhost:8000/admin/api/search?q=brazzers&type=sites" \
  -u admin:change_me_in_production | jq .
```

### Performer Search
```bash
curl "http://localhost:8000/admin/api/search?q=performer+name&type=performers" \
  -u admin:change_me_in_production | jq .
```

### Movie Search
```bash
curl "http://localhost:8000/admin/api/search?q=movie+title&type=movies" \
  -u admin:change_me_in_production | jq .
```

---

## Test 3: Error Handling

### Invalid Search Type
```bash
curl "http://localhost:8000/admin/api/search?q=test&type=invalid" \
  -u admin:change_me_in_production
```

**Expected**: 400 Bad Request
```json
{"detail": "Invalid search type. Must be one of: scenes, sites, movies, performers"}
```

### Missing Authentication
```bash
curl "http://localhost:8000/admin/api/search?q=test&type=scenes"
```

**Expected**: 401 Unauthorized (browser shows login prompt)

### Empty Query
```bash
curl "http://localhost:8000/admin/api/search?q=&type=scenes" \
  -u admin:change_me_in_production
```

**Expected**: 422 Unprocessable Entity (query must be 1+ characters)

---

## Test 4: Browser Console Testing

### Step-by-Step

1. **Open admin search page**
   - `http://localhost:8000/admin/search`

2. **Open browser Developer Tools**
   - Chrome/Firefox: F12
   - Safari: Cmd+Option+I
   - Go to "Console" tab

3. **Perform a search**
   - Enter query: "test"
   - Select type: "Scenes"
   - Click Search

4. **Check console output**
   - Should see request: `GET /admin/api/search?q=test&type=scenes`
   - Should see response with results

5. **Check Network tab**
   - Click "Network" tab in DevTools
   - Do another search
   - Click on the `/admin/api/search` request
   - View "Response" tab to see JSON data
   - View "Headers" tab to see Basic Auth

---

## Test 5: Load Testing

### Multiple Searches (Tests Rate Limiting)

```bash
# Search 5 times rapidly (should be rate-limited to ~2/sec)
for i in {1..5}; do
  curl "http://localhost:8000/admin/api/search?q=test$i&type=scenes" \
    -u admin:change_me_in_production -s | jq '.count'
  echo "Search $i completed"
done
```

**Expected behavior:**
- First 2 requests: Fast (< 500ms)
- Requests 3-5: Slightly delayed (rate limiter waits for tokens)

---

## Test 6: Verify Logging

### Check Application Logs

When you search, you should see logs like:

```
{"event": "TPDB search", "query": "brazzers", "search_type": "sites", "username": "admin"}
{"event": "TPDB search successful", "query": "brazzers", "search_type": "sites", "result_count": 1}
```

In the app console output, look for:
- `TPDB search` - Logs the search request
- `TPDB search successful` - Logs successful result
- `TPDB API error` - Logs any API errors
- `Cache hit` - Logs if results were cached

---

## Test 7: All Search Types at Once

### Quick Validation Script

```bash
#!/bin/bash
# Save as: test_search.sh

API_KEY="your_api_key"
BASE_URL="http://localhost:8000/admin/api/search"
AUTH="admin:change_me_in_production"

echo "Testing Scene Search..."
curl -s "$BASE_URL?q=brazzers&type=scenes" -u "$AUTH" | jq '.type, .count'

echo "Testing Site Search..."
curl -s "$BASE_URL?q=brazzers&type=sites" -u "$AUTH" | jq '.type, .count'

echo "Testing Movie Search..."
curl -s "$BASE_URL?q=movie&type=movies" -u "$AUTH" | jq '.type, .count'

echo "Testing Performer Search..."
curl -s "$BASE_URL?q=performer&type=performers" -u "$AUTH" | jq '.type, .count'

echo "Testing Invalid Type..."
curl -s "$BASE_URL?q=test&type=invalid" -u "$AUTH" | jq '.detail'

echo "All tests completed!"
```

Run it:
```bash
chmod +x test_search.sh
./test_search.sh
```

---

## Checklist: What Should Work

After implementing the fix, verify:

- [ ] Web UI search page loads without errors
- [ ] Can search for scenes by keyword
- [ ] Can search for sites/studios by name
- [ ] Can search for performers by name
- [ ] Can search for movies by title
- [ ] Results display with images/thumbnails
- [ ] Results show proper descriptions
- [ ] Error messages are clear if search fails
- [ ] Authentication is required for searches
- [ ] cURL requests work with HTTP Basic Auth
- [ ] Rate limiting doesn't block legitimate searches
- [ ] Logs show search requests and results
- [ ] Invalid search types return 400 error
- [ ] Unauthenticated requests return 401 error

---

## Troubleshooting

### Search Returns 404 Error
**Problem**: Endpoint not found
**Solution**: Make sure you're using `/admin/api/search` (not `/api/v1/...`)

### Search Returns 401 Unauthorized
**Problem**: Wrong credentials
**Solution**: Check ADMIN_USERNAME and ADMIN_PASSWORD in config/environment

### Search Returns 500 Error
**Problem**: TPDB API error
**Solution**:
- Check TPDB_API_KEY is valid
- Check TPDB API is accessible (theporndb.net)
- Check application logs for error details

### No Results (Even for Real Queries)
**Problem**: Results don't exist or typo in query
**Solution**: Try simpler/different search terms

### Search is Very Slow
**Problem**: Rate limiting or TPDB slow response
**Solution**:
- Wait a moment and retry
- Check TPDB API status
- Check network latency

---

## Expected Response Times

| Scenario | Time |
|----------|------|
| First search (no cache) | 1-2 seconds |
| Second search (rate limit refill) | 0.5-1 second |
| Subsequent searches | 50-200ms |
| Invalid parameters | <100ms |

---

## Success Criteria

✅ **The fix is working if:**

1. Web UI search page works without JavaScript errors
2. cURL requests to `/admin/api/search` return JSON with results
3. Search results include proper fields (id, title, image, type, etc.)
4. Error handling works (invalid types, auth failures, etc.)
5. Results are formatted correctly for the UI
6. Rate limiting is applied smoothly
7. Logs show successful searches

---

## Quick Test Command (Copy & Paste)

```bash
# Set your TPDB API key
export TPDB_API_KEY=your_api_key_here

# Start the app
python -m app.main &
sleep 2

# Test the search endpoint
curl "http://localhost:8000/admin/api/search?q=brazzers&type=sites" \
  -u admin:change_me_in_production | jq .

# Should see results with site data!
```

---

## Next Steps

If all tests pass:

1. ✅ Admin search is fixed and working
2. ✅ Users can now search TPDB from the dashboard
3. ✅ Results display with proper formatting
4. ✅ Rate limiting is applied correctly

If tests fail:
1. Check application logs for errors
2. Verify TPDB_API_KEY is valid
3. Check network connectivity to TPDB API
4. Review error messages in browser console

