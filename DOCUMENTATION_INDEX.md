# Documentation Index

## Welcome to the Plex ThePornDB Provider Documentation

This folder contains comprehensive documentation explaining every aspect of this codebase. Start here to understand what documentation is available and find what you need.

---

## 📋 Documentation Files

### 🚀 **START HERE**

#### [QUICK_REFERENCE.md](QUICK_REFERENCE.md) (5 min read)
- One-minute overview
- API endpoints cheat sheet
- Common tasks with code examples
- Debugging checklist
- Performance tips
- Error messages and solutions

**Best for:** Getting started quickly, finding an API endpoint, solving a common problem

---

### 📖 **COMPREHENSIVE GUIDES**

#### [README_CODE_REVIEW.md](README_CODE_REVIEW.md) (20 min read)
- What this application does
- Architecture layers diagram
- Key design patterns explained
- Common workflows
- Code quality observations
- Testing the application
- Performance metrics

**Best for:** Understanding the overall architecture, code review feedback, testing approach

#### [CODEBASE_EXPLANATION.md](CODEBASE_EXPLANATION.md) (30 min read)
- Complete file-by-file explanation
- Data flow examples
- Content mapping (TPDB → Plex)
- Performance optimizations
- Configuration tips
- Debugging tips
- Summary of all components

**Best for:** Understanding each component, how data flows through the system, deep learning

#### [CODE_COMMENTS_DETAILED.md](CODE_COMMENTS_DETAILED.md) (45 min read)
- Line-by-line code explanations
- Rate limiter deep dive with visual examples
- Cache service deep dive with flow diagrams
- Match service logic explanation
- Metadata service explanation
- Request/response flow examples
- Error handling examples
- Performance considerations

**Best for:** Understanding complex algorithms, learning how specific features work, detailed debugging

---

### 📝 **SOURCE CODE**

The application code is organized as follows:

```
app/
├── main.py                    # Application startup (now with comments!)
├── config.py                  # Configuration management (now with comments!)
├── constants.py              # Constants and enums
├── clients/
│   ├── tpdb_client.py        # ThePornDB API client
│   └── rate_limiter.py       # Token bucket rate limiter
├── db/
│   ├── database.py           # Database setup
│   └── models/
│       ├── site.py           # Site/Show model
│       ├── scene.py          # Scene/Episode model
│       ├── movie.py          # Movie model
│       ├── performer.py      # Performer model
│       └── cache_entry.py    # Cache model
├── models/
│   └── tpdb.py              # TPDB API response models
├── services/
│   ├── match_service.py      # Matching logic
│   ├── metadata_service.py   # Metadata retrieval
│   └── cache_service.py      # Caching logic
├── mappers/
│   ├── show_mapper.py        # TPDB → Plex conversion
│   └── movie_mapper.py       # TPDB → Plex conversion
├── parsers/
│   ├── scene_parser.py       # Filename parsing
│   └── patterns.py           # Regex patterns
├── routes/
│   ├── tv.py                 # TV provider endpoints
│   └── movie.py              # Movie provider endpoints
└── web/
    └── router.py             # Admin UI
```

---

## 🎯 Finding Information by Topic

### Getting Started
1. Read [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - 5 minutes
2. Run the health check endpoint
3. Try matching a show

**Next:** [README_CODE_REVIEW.md](README_CODE_REVIEW.md) for architecture overview

### Understanding the Architecture
1. Read [README_CODE_REVIEW.md](README_CODE_REVIEW.md) - "Architecture Layers"
2. Read [CODEBASE_EXPLANATION.md](CODEBASE_EXPLANATION.md) - "Architecture Overview"
3. Look at the file structure in [CODEBASE_EXPLANATION.md](CODEBASE_EXPLANATION.md)

**Next:** [CODE_COMMENTS_DETAILED.md](CODE_COMMENTS_DETAILED.md) for deeper understanding

### Understanding a Specific Component

| Component | Where to Learn |
|-----------|---|
| Rate Limiting | [CODE_COMMENTS_DETAILED.md](CODE_COMMENTS_DETAILED.md) - Rate Limiter Deep Dive |
| Caching | [CODE_COMMENTS_DETAILED.md](CODE_COMMENTS_DETAILED.md) - Cache Service Deep Dive |
| Matching | [CODE_COMMENTS_DETAILED.md](CODE_COMMENTS_DETAILED.md) - Match Service Deep Dive |
| API Endpoints | [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - API Endpoints Cheat Sheet |
| Database | [CODEBASE_EXPLANATION.md](CODEBASE_EXPLANATION.md) - File Structure #7 |
| Async/Await | [CODE_COMMENTS_DETAILED.md](CODE_COMMENTS_DETAILED.md) - Performance Considerations |

### Debugging Issues
1. Check [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - "Debugging Checklist"
2. Check [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - "Error Messages & Solutions"
3. Enable DEBUG=true and check logs
4. Use curl to test endpoints

**If not found:** Check [CODEBASE_EXPLANATION.md](CODEBASE_EXPLANATION.md) - "Debugging Tips"

### Configuration
1. See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - "Configuration"
2. See [CODEBASE_EXPLANATION.md](CODEBASE_EXPLANATION.md) - File Structure #2 (config.py)
3. Edit `.env` file or set environment variables

### Performance Optimization
1. Read [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - "Performance Tips"
2. Read [README_CODE_REVIEW.md](README_CODE_REVIEW.md) - "Performance Metrics"
3. Read [CODEBASE_EXPLANATION.md](CODEBASE_EXPLANATION.md) - "Performance Optimizations"

### Adding Features
1. Understand current architecture from [README_CODE_REVIEW.md](README_CODE_REVIEW.md)
2. Find similar feature in codebase
3. Follow the same pattern
4. Update appropriate service/route/mapper

---

## 📊 How This Application Works

```
User's Video File
       ↓
Plex Media Server
       ↓
HTTP Request to Provider (/tv/library/metadata/matches)
       ↓
FastAPI Route Handler (routes/tv.py)
       ↓
Service Layer (MatchService)
       ├─ Parse request
       ├─ Check cache
       ├─ Call TPDB API (if not cached)
       └─ Convert to Plex format
       ↓
Rate Limiter (ensures API limits respected)
       ↓
TPDB Client (makes HTTP request to ThePornDB)
       ↓
ThePornDB API
       ↓
HTTP Response (search results)
       ↓
Service Layer (convert to Plex format)
       ↓
Cache Service (store results for future requests)
       ↓
FastAPI Route (return to Plex)
       ↓
Plex Media Server (shows matches to user)
       ↓
User selects match
       ↓
Plex requests full metadata (GET /tv/library/metadata/{rating_key})
       ↓
(Repeat process, but now fetching full details)
       ↓
Plex stores metadata in its database
       ↓
User sees metadata in Plex UI
```

---

## 🔄 Data Flow Example

Let's trace a real example to understand the entire flow:

### Scenario: User adds "Brazzers.2024.01.15.Scene.Name.mp4" to Plex

**Step 1: User initiates match**
```
File: Brazzers.2024.01.15.Scene.Name.mp4
Action: Right-click → Edit Metadata → Search
```

**Step 2: Plex sends HTTP request**
```
POST /tv/library/metadata/matches
{
    "type": 4,  // EPISODE
    "title": "Brazzers 2024 01 15 Scene Name",
    "grandparentTitle": "Brazzers",
    "date": "2024-01-15"
}
```

**Step 3: Our provider processes request**
- Route handler (tv.py) receives request
- Calls match_service.match_episode()
- Service parses request, builds search parameters
- Checks cache for matching scenes

**Step 4: If cache miss, fetch from TPDB**
- Service calls tpdb_client.search_scenes()
- Client checks rate limiter (waits if necessary)
- Client makes HTTP request to ThePornDB API
- TPDB returns matching scenes

**Step 5: Convert and cache**
- Service converts TPDB scenes to Plex format
- Cache service stores results (5 min TTL for searches)
- Return results to Plex

**Step 6: Plex shows matches**
- User sees 10 possible matches
- User selects the correct one (e.g., #3)

**Step 7: Plex requests full metadata**
```
GET /tv/library/metadata/tpdb-scene-uuid-789
```

**Step 8: Our provider fetches details**
- Route handler receives request
- Calls metadata_service.get_metadata()
- Service checks cache (usually HIT for detailed metadata)
- If miss, calls tpdb_client.get_scene()
- Client makes API request
- Service converts to Plex format
- Cache stores for 24 hours

**Step 9: Plex stores metadata**
- User sees full metadata: title, description, performers, images, etc.
- Metadata is stored in Plex's database

---

## 💡 Key Concepts

### Rating Keys
Unique identifiers that Plex uses to refer to items in our provider.

```
tpdb-site-brazzers          # A site/show
tpdb-season-brazzers-2024   # A year/season
tpdb-scene-uuid-123         # A scene/episode
tpdb-movie-uuid-456         # A movie
```

### Cache Tiers
Two-layer caching for performance:
1. **Memory** (fast, expires in 5 min, lost on restart)
2. **Database** (persistent, TTL per endpoint, survives restart)

### Rate Limiting
Token bucket algorithm that:
- Allows bursts of 5 requests
- Sustained rate of 2 requests/second
- Prevents hitting TPDB API limits

### Async Architecture
Non-blocking I/O throughout:
- Can handle 100+ concurrent Plex clients
- Database queries don't block
- API requests don't block

---

## 🔧 Working with the Code

### Understanding a Component
1. Find file in [CODEBASE_EXPLANATION.md](CODEBASE_EXPLANATION.md)
2. Read the explanation section
3. Look at the code itself
4. Check [CODE_COMMENTS_DETAILED.md](CODE_COMMENTS_DETAILED.md) for deep dive
5. Try modifying it and test

### Adding a Feature
1. Read [README_CODE_REVIEW.md](README_CODE_REVIEW.md) - "Common Workflows"
2. Find similar existing feature
3. Implement following the same pattern
4. Update tests
5. Test with curl or Plex

### Debugging
1. Enable DEBUG=true in `.env`
2. Run app and watch logs
3. Use [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - curl commands to test
4. Check [CODE_COMMENTS_DETAILED.md](CODE_COMMENTS_DETAILED.md) for error handling

---

## 📚 Learning Path

**Level 1: Beginner (Understanding the Basics)**
- Read [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - 5 min
- Read [README_CODE_REVIEW.md](README_CODE_REVIEW.md) intro - 10 min
- Run health check and test an endpoint - 5 min
- **Total: 20 minutes**

**Level 2: Intermediate (Understanding Components)**
- Read [README_CODE_REVIEW.md](README_CODE_REVIEW.md) - 20 min
- Read [CODEBASE_EXPLANATION.md](CODEBASE_EXPLANATION.md) - 30 min
- Pick one component and read its explanation - 15 min
- **Total: 65 minutes**

**Level 3: Advanced (Deep Understanding)**
- Read [CODE_COMMENTS_DETAILED.md](CODE_COMMENTS_DETAILED.md) - 45 min
- Read source code with comments - 30 min
- Implement a small feature - 30 min
- **Total: 105 minutes**

**Level 4: Expert (Full Mastery)**
- Understand all components in detail
- Be able to modify any part
- Add new features easily
- Debug complex issues
- This takes time - work through the code methodically

---

## 🎓 Documentation Quality

### Main.py and Config.py
These files now have detailed inline comments explaining every section.

### Other Files
See [CODE_COMMENTS_DETAILED.md](CODE_COMMENTS_DETAILED.md) for detailed explanations of:
- Rate limiter (with visual diagrams)
- Cache service (with flow charts)
- Match service (with examples)
- Metadata service (with real-world scenarios)
- Request/response flows (with complete examples)

### Test These Components
Use [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - "Testing with cURL" to test endpoints

---

## 📞 Finding Answers

| Question | Answer Location |
|----------|---|
| "What does this code do?" | [CODEBASE_EXPLANATION.md](CODEBASE_EXPLANATION.md) |
| "How do I use this API?" | [QUICK_REFERENCE.md](QUICK_REFERENCE.md) |
| "How does caching work?" | [CODE_COMMENTS_DETAILED.md](CODE_COMMENTS_DETAILED.md) |
| "Why is it slow?" | [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Performance Tips |
| "Why did it error?" | [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Error Messages |
| "How do I add a feature?" | [README_CODE_REVIEW.md](README_CODE_REVIEW.md) - Common Workflows |
| "What's the architecture?" | [README_CODE_REVIEW.md](README_CODE_REVIEW.md) - Architecture Layers |
| "How does rate limiting work?" | [CODE_COMMENTS_DETAILED.md](CODE_COMMENTS_DETAILED.md) - Rate Limiter Deep Dive |
| "How does matching work?" | [CODE_COMMENTS_DETAILED.md](CODE_COMMENTS_DETAILED.md) - Match Service Deep Dive |
| "Help me debug this!" | [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Debugging Checklist |

---

## ✅ Documentation Checklist

This documentation includes:

✅ One-minute overview of the entire application
✅ Quick reference guide for common tasks
✅ Complete architecture explanation
✅ File-by-file code explanations
✅ Line-by-line algorithm explanations
✅ Visual diagrams and examples
✅ Real-world usage scenarios
✅ Error messages and solutions
✅ Performance tips and optimization
✅ Testing instructions
✅ Configuration guide
✅ Debugging guide
✅ Code quality assessment
✅ Learning path for different skill levels

---

## 🚀 Getting Started

**Right now, you should:**

1. **Open [QUICK_REFERENCE.md](QUICK_REFERENCE.md)**
   - Get a 5-minute overview
   - Learn the API endpoints
   - See common tasks

2. **Test the application**
   ```bash
   python -m app.main
   curl http://localhost:8000/health
   ```

3. **Explore the code**
   - Look at main.py (it has detailed comments now!)
   - Look at config.py (it has detailed comments now!)
   - Check the route files to see how endpoints work

4. **Read more**
   - For architecture: [README_CODE_REVIEW.md](README_CODE_REVIEW.md)
   - For components: [CODEBASE_EXPLANATION.md](CODEBASE_EXPLANATION.md)
   - For details: [CODE_COMMENTS_DETAILED.md](CODE_COMMENTS_DETAILED.md)

**Have fun learning!** 🎉

