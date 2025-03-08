# News Aggregator API Documentation

## Overview
The News Aggregator Backend provides a unified REST API interface for fetching, summarizing, managing, and tracking news articles. It integrates multiple microservices, handling authentication, summarization, news retrieval, bookmarking, and tracking stories.

## API Base URL
```
http://localhost:5000
```

## Authentication
The API utilizes JWT (JSON Web Tokens) for securing endpoints. All protected endpoints require an `Authorization` header:
```
Authorization: Bearer <JWT_TOKEN>
```

---

## Endpoints

### 1. Health Check

- **GET** `/health`

Checks API health status.

**Response:**
```json
{
  "status": "API Gateway is healthy"
}
```

---

### 2. Article Summarization

- **POST** `/summarize`

Summarizes provided article text.

**Request Body:**
```json
{
  "article_text": "<text-to-summarize>"
}
```

**Response:**
```json
{
  "summary": "<generated-summary>"
}
```

---

### 2. News Fetching

- **GET** `/api/news/fetch`

Fetches and stores news articles based on a keyword.

**Query Parameters:**
- `keyword` *(required)*: Keyword for fetching news.
- `user_id`: Optional user ID for logging searches.
- `session_id`: Session ID for tracking requests.

**Response:**
```json
{
  "status": "success",
  "data": ["article_id_1", "article_id_2"]
}
```

---

### 3. Summarization Processing

- **POST** `/api/news/process?session_id=<session_id>`

Processes and summarizes articles associated with a session ID.

**Response:**
```json
{
  "status": "success",
  "message": "Articles processed and summarized successfully",
  "data": [{"id": "article_id", "summary": "text"}],
  "session_id": "<session_id>"
}
```

---

### 2. User Authentication

#### Signup
- **POST** `/api/auth/signup`

Registers a new user.

**Request Body:**
```json
{
  "username": "<username>",
  "password": "<password>",
  "email": "user@example.com",
  "firstName": "First",
  "lastName": "Last"
}
```

**Response:**
```json
{
  "message": "User registered successfully",
  "user": {"id": "<uuid>", "username": "username", "email": "user@example.com", "firstName": "First", "lastName": "Last"},
  "token": "<jwt_token>"
}
```

#### Login
- **POST** `/api/auth/login`

**Request Body:**
```json
{
  "username": "username",
  "password": "password"
}
```

**Response:**
```json
{
  "token": "<JWT_TOKEN>",
  "user": {"id": "uuid", "username": "username", "email": "user@example.com"}
}
```

---

### 3. User Profile
- **GET** `/api/user/profile`

Returns the authenticated user's profile.

**Response:**
```json
{
  "id": "uuid",
  "username": "username",
  "email": "user@example.com",
  "firstName": "First",
  "lastName": "Last"
}
```

---

### 3. Bookmark Management

#### Get Bookmarks
- **GET** `/api/bookmarks`

**Response:**
```json
{
  "status": "success",
  "data": [{"bookmark_id": "bookmark_id", "article_id": "article_id"}]
}
```

#### Add Bookmark
- **POST** `/api/bookmarks`

**Request Body:**
```json
{
  "article_id": "<article_id>"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Bookmark added successfully",
  "data": {"bookmark_id": "bookmark_id"}
}
```

#### Delete Bookmark
- **DELETE** `/api/bookmarks/{bookmark_id}`

**Response:**
```json
{
  "status": "success",
  "message": "Bookmark removed successfully"
}
```

---

### 4. Story Tracking

#### Track Keyword
- **POST** `/api/story_tracking`

**Request Body:**
```json
{
  "keyword": "keyword",
  "sourceArticleId": "optional_article_id"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {"id": "story_id", "keyword": "keyword", "articles": []}
}
```

#### Get Tracked Stories
- **GET** `/api/story_tracking`

Retrieves all tracked stories for authenticated user.

**Response:**
```json
{
  "status": "success",
  "data": [{"id": "story_id", "keyword": "keyword"}]
}
```

#### Get Story Details
- **GET** `/api/story_tracking/{story_id}`

**Response:**
```json
{
  "status": "success",
  "data": {"id": "story_id", "keyword": "keyword", "articles": []}
}
```

#### Delete Tracked Story
- **DELETE** `/api/story_tracking/<story_id>`

Deletes a tracked story by ID.

**Response:**
```json
{
  "status": "success",
  "message": "Tracked story deleted successfully"
}
```

---

## Error Handling
- `400`: Validation errors or missing parameters.
- `401`: Authentication errors (missing/invalid token).
- `404`: Resource not found.
- `500`: Internal server error.

---

This documentation provides clear and structured guidance for developers interacting with the News Aggregator Backend API.

