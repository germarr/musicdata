# 🎵 iTunes Artist Search Web App

A FastAPI application that allows users to search for artists using the iTunes API with persistent session and search history.

## Features

✨ **Core Features:**
- 🔍 Search for artists using the iTunes API
- 📊 Display results in a nicely formatted table
- 💾 Persistent SQLite database with SQLModel ORM
- 🍪 User sessions with HTTP-only cookies
- 📜 Search history per user session
- 📱 Responsive web interface
- ⚡ Real-time AJAX search without page reload

## Technology Stack

- **Backend:** FastAPI + Uvicorn
- **Database:** SQLite with SQLModel ORM
- **HTTP Client:** httpx (async)
- **Frontend:** HTML5, CSS3, Vanilla JavaScript
- **API:** iTunes Search API (free, no authentication required)

## Project Structure

```
yolo_seg/
├── main.py                 # FastAPI app, routes, session middleware
├── database.py             # SQLModel models (UserSession, Search, Result)
├── itunes_client.py        # iTunes API client functions
├── templates/
│   └── index.html          # Frontend UI with form and results table
├── pyproject.toml          # Project dependencies
├── yolo_seg.db             # SQLite database (auto-created)
└── uv.lock                 # Locked dependencies
```

## Database Schema

### `usersession` Table
- `id`: Primary key
- `session_id`: Unique session identifier (UUID)
- `created_at`: Session creation timestamp
- `updated_at`: Last activity timestamp

### `search` Table
- `id`: Primary key
- `session_id`: Foreign key to usersession
- `artist_query`: The artist name searched
- `created_at`: Search timestamp

### `result` Table
- `id`: Primary key
- `search_id`: Foreign key to search
- `artist_id`, `artist_name`, `primary_genre`, `artwork_url_100`, `artist_link_url`, `artist_type`, `wrapper_type`
- `created_at`: Result stored timestamp

## Installation & Setup

### Prerequisites
- Python 3.14+
- `uv` package manager (or pip/poetry)

### Steps

1. **Install Dependencies:**
   ```bash
   uv sync
   ```

2. **Run the Application:**
   ```bash
   uv run uvicorn main:app --reload
   ```

3. **Access the Web App:**
   - Open your browser and navigate to: **http://localhost:8000**

## Usage

1. **Search for an Artist:**
   - Enter an artist name in the search field
   - Click "Search" or press Enter
   - Results appear in a formatted table

2. **View Artist Details:**
   - Results include artwork, name, genre, and iTunes link
   - Click "View on iTunes →" to visit the artist's iTunes page

3. **Search History:**
   - Your search history appears below the results
   - Click on any previous search to run it again
   - History persists via session cookies

## API Endpoints

### `GET /`
Serves the main HTML page with the search form.

**Response:** HTML page

### `POST /search`
Search for artists on iTunes and store results in database.

**Request Body:**
```json
{
  "artist_name": "Taylor Swift"
}
```

**Response:**
```json
{
  "results": [
    {
      "artist_id": "159260351",
      "artist_name": "Taylor Swift",
      "primary_genre": "Pop",
      "artwork_url_100": "https://is1-ssl.mzstatic.com/...",
      "artist_link_url": "https://music.apple.com/...",
      "artist_type": "Artist"
    }
  ]
}
```

### `GET /history`
Retrieve search history for the current session.

**Response:**
```json
{
  "searches": [
    {
      "id": 1,
      "artist_query": "Taylor Swift",
      "created_at": "2026-01-06T14:31:22.335Z"
    }
  ]
}
```

## Session Management

- Sessions are created automatically on first visit
- Session ID stored in HTTP-only cookie (`session_id`)
- Cookies expire after 30 days
- Each session tracks its own search history
- Session data is stored in SQLite database

## Features Explained

### 1. Artist Search
- Queries iTunes API with artist name
- Filters for artist-type results only
- Returns up to 50 results per search

### 2. Data Persistence
- All searches and results stored in SQLite
- Users can see their search history
- Database survives app restarts

### 3. Session Tracking
- Each user gets a unique session ID
- Stored in secure HTTP-only cookie
- Middleware validates and updates sessions

### 4. Beautiful UI
- Gradient background
- Responsive table design
- Loading spinner during API calls
- Error messages for user feedback
- Mobile-friendly layout

## Development

### Run in Development Mode:
```bash
uv run uvicorn main:app --reload
```

### Run in Production Mode:
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

### Database
- Database file: `yolo_seg.db` (auto-created)
- Tables created automatically on app start
- Use SQLModel ORM for all database operations

## Troubleshooting

**Issue:** App fails to start
- **Solution:** Run `uv sync` to install dependencies

**Issue:** Database error
- **Solution:** Delete `yolo_seg.db` and restart app (tables will be recreated)

**Issue:** iTunes API not returning results
- **Solution:** Check internet connection and iTunes API status at https://itunes.apple.com/search

## Future Enhancements

- Add pagination for large result sets
- Filter results by genre, country
- Export search results to CSV/JSON
- Add user accounts with persistent data
- Cache iTunes API results
- Advanced search filters

## Dependencies

- **fastapi** - Web framework
- **uvicorn** - ASGI server
- **sqlmodel** - SQL ORM
- **httpx** - Async HTTP client
- **python-multipart** - Form parsing

## License

MIT License

## Notes

- iTunes API is free and does not require authentication
- Searches are rate-limited by iTunes (no official limit documented)
- All data stored locally in SQLite
- No external analytics or tracking

---

## iTunes API Notes

The iTunes Search API returns mixed content types (movies, audiobooks, tracks, etc.) when querying with an artist name. The application:

1. Queries the iTunes API with the artist search term
2. Extracts unique artists from all results using `artistId`
3. Returns only artist-related entries (avoiding duplicate artists)
4. Provides `artistViewUrl` as the link to the artist's iTunes page

This approach ensures users get diverse artist information from iTunes including music artists, audiobook narrators, and other artists in the iTunes catalog.
