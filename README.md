# 🎵 iTunes Artist Search Web App

A FastAPI application that allows users to search for artists using the iTunes API with persistent session and search history.

## Features

✨ **Core Features:**
- 🔍 Search for artists using the iTunes API (up to 200 results)
- 🎯 **Comprehensive filtering** on search results (genre, type, text search, sorting)
- 📊 Display results in a nicely formatted table
- 💾 Persistent SQLite database with SQLModel ORM
- 🍪 User sessions with HTTP-only cookies
- 📜 Search history per user session
- 🎼 **Browse albums by artist** with artwork gallery (up to 150 albums)
- 🎵 **Collect detailed track metadata** from albums with progress tracking
- 📚 **Dedicated Collected Artists page** with easy management
- 🎧 **Preview tracks** with built-in audio player
- 🧭 **Navigation bar** for easy access between pages
- 📊 **Per-artist metrics** showing tracks, albums, and average song duration
- 📈 **Global metrics dashboard** with comprehensive statistics
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
├── database.py             # SQLModel models (UserSession, Search, Result, ArtistCache, Track)
├── itunes_client.py        # iTunes API client functions
├── templates/
│   ├── index.html          # Frontend UI with search form, results, history, cached artists
│   └── albums.html         # Album gallery with track collection modal
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

### `artistcache` Table
- `id`: Primary key
- `artist_id`: Unique artist identifier (indexed)
- `artist_name`: Artist name
- `albums_collected`: Whether albums have been fetched
- `tracks_collected`: Whether tracks have been collected
- `created_at`, `updated_at`: Timestamps

### `track` Table
- `id`: Primary key
- `artist_id`, `collection_id`, `track_id`: Foreign key references (indexed)
- `track_number`, `track_name`, `track_duration_ms`, `preview_url`, `explicit`, `primary_genre`, `release_date`
- `is_playable`: Whether preview is available
- `collection_name`: Album/collection name (new)
- `artwork_url_600`: Album artwork URL for 600px images (new)
- `created_at`: Timestamp

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
   - Results appear in a formatted table (up to 200 results)

2. **Filter Search Results:**
   - **Genre Filter:** Select one genre to show only artists in that genre
   - **Artist Type Filter:** Filter by Artist, Composer, or other types
   - **Sort:** Order results alphabetically (A→Z or Z→A)
   - **Live Search:** Search within results by typing artist name
   - **Clear Filters:** Reset all filters to show all results
   - **Filter Summary:** See all active filters at a glance

3. **View Artist Details:**
   - Results include artwork, name, genre, and iTunes link
   - Click "View on iTunes →" to visit the artist's iTunes page

4. **Browse Albums:**
   - Click "Check Albums" button in search results
   - View all albums by the artist with artwork
   - See track count and release date for each album

5. **Collect Track Data:**
   - Click "View Tracks" on any album
   - App collects detailed track metadata from iTunes API
   - Progress bar shows collection status (with rate limiting)
   - Modal displays all tracks with previews

6. **Preview Tracks:**
   - Click "▶ Preview" button on any track
   - Built-in audio player streams track preview
   - See track duration, genre, and explicit content flag

6. **View Collected Artists:**
   - "🎸 Collected Artists" section shows all cached artists
   - See which artists have had tracks collected
   - Quick access to view their albums again

7. **Search History:**
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

### `GET /albums`
Serves the albums gallery page.

**Response:** HTML page

### `GET /collected-artists`
Serves the collected artists page showing all cached artists.

**Response:** HTML page

### `GET /collected-tracks`
Serves the collected tracks dashboard with metrics and filterable track listing by artist and album.

**Response:** HTML page

### `GET /api/albums/{artist_id}`
Get all albums for a specific artist.

**Response:**
```json
{
  "artist_id": "159260351",
  "artist_name": "Taylor Swift",
  "albums": [
    {
      "collection_id": "123456789",
      "collection_name": "Fearless",
      "artist_name": "Taylor Swift",
      "primary_genre": "Pop",
      "release_date": "2008-11-11",
      "track_count": 13,
      "artwork_url_100": "https://...",
      "artwork_url_600": "https://...",
      "collection_view_url": "https://...",
      "collection_price": 9.99,
      "currency": "USD"
    }
  ]
}
```

### `POST /api/collect-album-tracks/{artist_id}/{collection_id}`
Collect and store all detailed tracks for an album with rate limiting.

**Response:**
```json
{
  "collection_id": "123456789",
  "collection_name": "Fearless",
  "artist_name": "Taylor Swift",
  "artist_id": "159260351",
  "tracks": [
    {
      "track_id": "1",
      "track_number": 1,
      "track_name": "Fearless",
      "track_duration_ms": 294000,
      "preview_url": "https://...",
      "explicit": false,
      "primary_genre": "Pop"
    }
  ],
  "total_tracks": 13
}
```

### `GET /api/cached-artists`
Get all artists whose tracks have been collected.

**Response:**
```json
{
  "artists": [
    {
      "artist_id": "159260351",
      "artist_name": "Taylor Swift",
      "tracks_collected": true,
      "updated_at": "2026-01-06T16:34:26.922869"
    }
  ]
}
```

### `GET /api/artists-with-track-counts`
Get all artists with their collected track counts and albums with global metrics.

**Response:**
```json
{
  "artists": [
    {
      "artist_id": "159260351",
      "artist_name": "Taylor Swift",
      "album_count": 12,
      "track_count": 156,
      "updated_at": "2026-01-06T16:34:26.922869"
    }
  ],
  "total_artists": 5,
  "total_tracks": 487,
  "total_albums": 42,
  "avg_duration_ms": 220000
}
```

### `GET /api/tracks/{artist_id}`
Get all tracks for a specific artist grouped by album with album metadata, artwork, and artist-specific metrics.

**Response:**
```json
{
  "artist_id": "159260351",
  "albums": [
    {
      "collection_id": "123456789",
      "collection_name": "Fearless",
      "artwork_url_600": "https://is1-ssl.mzstatic.com/...",
      "tracks": [
        {
          "track_id": "1",
          "track_number": 1,
          "track_name": "Fearless",
          "track_duration_ms": 294000,
          "preview_url": "https://...",
          "explicit": false,
          "primary_genre": "Pop",
          "release_date": "2008-11-11"
        }
      ]
    }
  ],
  "total_tracks": 156,
  "total_albums": 12,
  "avg_duration_ms": 215000
}
```

### `POST /api/collect-all-artist-tracks/{artist_id}`
Collect and store all detailed tracks from all albums for an artist with deduplication.

**Response:**
```json
{
  "artist_id": "159260351",
  "artist_name": "Taylor Swift",
  "total_albums": 12,
  "total_tracks_collected": 142,
  "albums": [
    {
      "collection_id": "123456789",
      "collection_name": "Fearless",
      "new_tracks": 13,
      "skipped_tracks": 0
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
- Returns up to 200 results per search (deduped by artist ID)

### 2. Album Discovery
- Fetches all albums for a selected artist
- Displays album artwork, release date, track count
- Links to iTunes for each album

### 3. Track Collection with Caching
- Fetches detailed metadata for all tracks in an album
- Stores track data in SQLite for future access (including album name and artwork)
- Shows progress bar during collection
- Rate-limited (50ms between operations) to be respectful to iTunes API
- Reuses cached data on subsequent requests
- Auto-collects all albums when viewing an artist

### 4. Track Preview
- Streams 30-second preview from iTunes
- Built-in HTML5 audio player
- Shows track details (duration, genre, explicit flag)

### 5. Collected Tracks Dashboard
- View all collected tracks organized by artist and album
- Display album artwork (600px resolution) and full album names
- **Global metrics** showing:
  - Total artists, total tracks, total albums
  - Average tracks per artist
  - Average song duration across all collected music
- **Per-artist metrics** showing:
  - Track count for selected artist
  - Album count for selected artist
  - Average song duration for selected artist
- Filter tracks by album
- See track details (number, duration, genre, explicit flag)

### 6. Data Persistence
- All searches, albums, and tracks stored in SQLite
- Users can see their search history and collected artists
- Database survives app restarts

### 7. Session Tracking
- Each user gets a unique session ID
- Stored in secure HTTP-only cookie
- Middleware validates and updates sessions

### 8. Beautiful UI
- Gradient background with modern design
- Responsive table design for search results
- Album grid gallery with hover effects
- Track modal with smooth animations
- Album artwork display in tracks table
- Metrics cards for global and per-artist statistics
- Loading spinners and progress bars
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

- Add pagination for large album/track result sets
- Filter albums and tracks by genre, year
- Export track data to CSV/JSON
- Add user accounts with persistent collection across devices
- Advanced search filters (country, language)
- Artist/album comparisons
- Trending albums and artists
- Recommendation engine based on collected data

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
