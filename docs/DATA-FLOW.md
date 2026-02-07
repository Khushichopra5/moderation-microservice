# Data Flow Documentation

## Overview

This document describes the data flow through the Content Moderation Microservice, detailing how information moves between components, how requests are processed, and how data is transformed at each stage.

## Table of Contents

- [System Data Flow Overview](#system-data-flow-overview)
- [Authentication Flow](#authentication-flow)
- [Comment Submission Flow](#comment-submission-flow)
- [Content Moderation Flow](#content-moderation-flow)
- [Admin Review Flow](#admin-review-flow)
- [Notification Flow](#notification-flow)
- [Database Transaction Flow](#database-transaction-flow)
- [Error Handling Flow](#error-handling-flow)
- [Caching Flow](#caching-flow)

## System Data Flow Overview

```
User Request
    ↓
Load Balancer (Production)
    ↓
Django Web Server
    ↓
┌─────────────────────────────────┐
│  Request Processing Pipeline    │
│  1. Middleware                  │
│  2. URL Routing                 │
│  3. Authentication              │
│  4. Authorization               │
│  5. View Logic                  │
│  6. Serialization               │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  Data Layer                     │
│  - PostgreSQL                   │
│  - Redis Cache                  │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  Response Pipeline              │
│  1. Serialization               │
│  2. Rendering                   │
│  3. Middleware                  │
└─────────────────────────────────┘
    ↓
JSON Response / HTML Page
    ↓
User
```

## Authentication Flow

### User Login

```
Step 1: User submits credentials
┌──────────────────────────────────────┐
│ POST /api/auth/login/                │
│ Body: {                              │
│   "username": "user",                │
│   "password": "password"             │
│ }                                    │
└──────────────┬───────────────────────┘
               │
               ▼
Step 2: Request reaches Django
┌──────────────────────────────────────┐
│ Django URL Router                    │
│ - Matches URL pattern                │
│ - Routes to view function            │
└──────────────┬───────────────────────┘
               │
               ▼
Step 3: View processes credentials
┌──────────────────────────────────────┐
│ AuthenticationView                   │
│ 1. Extract username/password         │
│ 2. Query User table                  │
│ 3. Validate password hash            │
└──────────────┬───────────────────────┘
               │
               ▼
Step 4: Database query
┌──────────────────────────────────────┐
│ PostgreSQL                           │
│ SELECT * FROM content_user           │
│ WHERE username = 'user'              │
└──────────────┬───────────────────────┘
               │
               ▼ User object returned
Step 5: Password verification
┌──────────────────────────────────────┐
│ Django Authentication Backend        │
│ - PBKDF2 hash comparison             │
│ - Password match verification        │
└──────────────┬───────────────────────┘
               │
               ▼ Valid
Step 6: Generate JWT tokens
┌──────────────────────────────────────┐
│ Simple JWT Library                   │
│ 1. Create access token (5 min)      │
│ 2. Create refresh token (24 hr)     │
│ 3. Sign with SECRET_KEY              │
└──────────────┬───────────────────────┘
               │
               ▼
Step 7: Response
┌──────────────────────────────────────┐
│ JSON Response                        │
│ {                                    │
│   "access": "eyJ...",                │
│   "refresh": "eyJ...",               │
│   "user_id": "uuid",                 │
│   "username": "user",                │
│   "role": "user"                     │
│ }                                    │
└──────────────┬───────────────────────┘
               │
               ▼
Step 8: Client stores tokens
┌──────────────────────────────────────┐
│ Browser LocalStorage                 │
│ - access token                       │
│ - refresh token                      │
│ - user metadata                      │
└──────────────────────────────────────┘
```

### Authenticated Request

```
Step 1: Client makes request
┌──────────────────────────────────────┐
│ GET /api/posts/                      │
│ Authorization: Bearer eyJ...         │
└──────────────┬───────────────────────┘
               │
               ▼
Step 2: JWT Middleware
┌──────────────────────────────────────┐
│ JWTAuthentication                    │
│ 1. Extract token from header         │
│ 2. Decode token                      │
│ 3. Verify signature                  │
│ 4. Check expiration                  │
└──────────────┬───────────────────────┘
               │
               ▼ Valid token
Step 3: Load user
┌──────────────────────────────────────┐
│ Database Query                       │
│ SELECT * FROM content_user           │
│ WHERE id = token.user_id             │
└──────────────┬───────────────────────┘
               │
               ▼ User loaded
Step 4: Attach to request
┌──────────────────────────────────────┐
│ request.user = User object           │
│ request.auth = token                 │
└──────────────┬───────────────────────┘
               │
               ▼
Step 5: Continue to view
┌──────────────────────────────────────┐
│ View function executes               │
│ - Can access request.user            │
│ - Can check permissions              │
└──────────────────────────────────────┘
```

## Comment Submission Flow

### Complete Comment Lifecycle

```
Step 1: User submits comment
┌──────────────────────────────────────────────┐
│ POST /api/posts/{post_id}/comments/submit/  │
│ Authorization: Bearer {token}                │
│ Body: {                                      │
│   "content": "This is a comment"             │
│ }                                            │
└──────────────┬───────────────────────────────┘
               │
               ▼
Step 2: Authentication & Authorization
┌──────────────────────────────────────────────┐
│ 1. Verify JWT token                          │
│ 2. Load user from database                   │
│ 3. Check IsAuthenticated permission          │
└──────────────┬───────────────────────────────┘
               │
               ▼ Authorized
Step 3: Validate request
┌──────────────────────────────────────────────┐
│ CommentSerializer                            │
│ 1. Validate content field exists             │
│ 2. Validate content is not empty             │
│ 3. Validate content length                   │
│ 4. Sanitize input                            │
└──────────────┬───────────────────────────────┘
               │
               ▼ Valid
Step 4: Verify post exists
┌──────────────────────────────────────────────┐
│ Database Query                               │
│ SELECT * FROM content_post                   │
│ WHERE id = post_id                           │
└──────────────┬───────────────────────────────┘
               │
               ▼ Post found
Step 5: Create comment
┌──────────────────────────────────────────────┐
│ BEGIN TRANSACTION                            │
│                                              │
│ INSERT INTO content_comment                  │
│ (id, post_id, author_id, content,           │
│  status, created_at)                         │
│ VALUES                                       │
│ ('uuid', 'post_uuid', 'user_uuid',          │
│  'comment text', 'UNDER_REVIEW', NOW())     │
│                                              │
│ COMMIT                                       │
└──────────────┬───────────────────────────────┘
               │
               ▼ Comment saved
Step 6: Queue moderation task
┌──────────────────────────────────────────────┐
│ Celery Task Queue                            │
│ moderate_comment_task.delay(comment.id)      │
│                                              │
│ Redis LPUSH moderation_queue                 │
│ {                                            │
│   "task": "moderate_comment_task",           │
│   "args": ["comment_uuid"],                  │
│   "kwargs": {},                              │
│   "id": "task_uuid"                          │
│ }                                            │
└──────────────┬───────────────────────────────┘
               │
               ▼
Step 7: Return response
┌──────────────────────────────────────────────┐
│ HTTP 201 Created                             │
│ {                                            │
│   "id": "comment_uuid",                      │
│   "post": "post_uuid",                       │
│   "author": "username",                      │
│   "content": "This is a comment",            │
│   "status": "UNDER_REVIEW",                  │
│   "created_at": "2024-01-01T00:00:00Z"      │
│ }                                            │
└──────────────────────────────────────────────┘
```

## Content Moderation Flow

### Asynchronous Moderation Process

```
Step 1: Celery worker polls queue
┌──────────────────────────────────────────────┐
│ Celery Worker                                │
│ BRPOP moderation_queue 1                     │
└──────────────┬───────────────────────────────┘
               │
               ▼ Task received
Step 2: Execute moderation task
┌──────────────────────────────────────────────┐
│ moderate_comment_task(comment_id)            │
│ 1. Load comment from database                │
│ 2. Log start of moderation                   │
└──────────────┬───────────────────────────────┘
               │
               ▼
Step 3: Load comment
┌──────────────────────────────────────────────┐
│ Database Query                               │
│ SELECT * FROM content_comment                │
│ WHERE id = comment_id                        │
└──────────────┬───────────────────────────────┘
               │
               ▼ Comment loaded
Step 4: Obtain OAuth2 token
┌──────────────────────────────────────────────┐
│ Google OAuth2 Flow                           │
│ 1. Load service account credentials          │
│    - From SERVICE_KEY_JSON env var           │
│    - From service-account-key.json file      │
│ 2. Create credentials object                 │
│ 3. Request access token                      │
│ 4. Receive Bearer token                      │
└──────────────┬───────────────────────────────┘
               │
               ▼ Token obtained
Step 5: Call Google Cloud API
┌──────────────────────────────────────────────┐
│ POST https://language.googleapis.com/        │
│      v1/documents:moderateText               │
│                                              │
│ Headers:                                     │
│   Authorization: Bearer {token}              │
│   Content-Type: application/json             │
│                                              │
│ Body:                                        │
│ {                                            │
│   "document": {                              │
│     "type": "PLAIN_TEXT",                    │
│     "content": "comment text"                │
│   }                                          │
│ }                                            │
└──────────────┬───────────────────────────────┘
               │
               ▼ API response
Step 6: Parse moderation result
┌──────────────────────────────────────────────┐
│ Response:                                    │
│ {                                            │
│   "moderationCategories": [                  │
│     {                                        │
│       "name": "Toxic",                       │
│       "confidence": 0.936                    │
│     },                                       │
│     {                                        │
│       "name": "Insult",                      │
│       "confidence": 0.782                    │
│     }                                        │
│   ]                                          │
│ }                                            │
└──────────────┬───────────────────────────────┘
               │
               ▼
Step 7: Decision logic
┌──────────────────────────────────────────────┐
│ Analyze Confidence Scores                    │
│                                              │
│ threshold = 0.6                              │
│ flagged = False                              │
│                                              │
│ for category in categories:                  │
│     if category.confidence > 0.6:            │
│         flagged = True                       │
│         break                                │
└──────────────┬───────────────────────────────┘
               │
               ├─── flagged = True ───────────┐
               │                              │
               │                              ▼
               │                    ┌─────────────────┐
               │                    │ Status: FLAGGED │
               │                    └────────┬────────┘
               │                             │
               ├─── flagged = False ─────┐   │
               │                         │   │
               ▼                         ▼   ▼
    ┌──────────────────┐    ┌──────────────────────┐
    │ Status: APPROVED │    │ Notify User & Admins │
    └────────┬─────────┘    └──────────┬───────────┘
             │                         │
             ▼                         ▼
Step 8: Update database
┌──────────────────────────────────────────────┐
│ BEGIN TRANSACTION                            │
│                                              │
│ UPDATE content_comment                       │
│ SET status = 'APPROVED'/'FLAGGED',           │
│     moderation_response = {json},            │
│     updated_at = NOW()                       │
│ WHERE id = comment_id                        │
│                                              │
│ COMMIT                                       │
└──────────────┬───────────────────────────────┘
               │
               ▼
Step 9: Create notifications
┌──────────────────────────────────────────────┐
│ If APPROVED:                                 │
│   INSERT notification for author             │
│   Message: "Comment successfully posted"     │
│                                              │
│ If FLAGGED:                                  │
│   INSERT notification for author             │
│   Message: "Comment flagged for review"      │
│                                              │
│   INSERT notifications for all admins        │
│   Message: "New flagged comment: {id}"       │
└──────────────┬───────────────────────────────┘
               │
               ▼
Step 10: Log completion
┌──────────────────────────────────────────────┐
│ Logging                                      │
│ [INFO] Comment {id} moderated               │
│ [INFO] Status: APPROVED/FLAGGED              │
│ [CRITICAL] FLAGGED CONTENT (if applicable)   │
└──────────────────────────────────────────────┘
```

### Fallback Moderation Flow

```
If Google Cloud API fails:
    ↓
┌──────────────────────────────────────────────┐
│ Exception Handler                            │
│ [ERROR] Google Cloud API failed: {error}     │
│ [WARNING] Using mock moderation              │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ Keyword-Based Detection                      │
│                                              │
│ keywords = [                                 │
│   "bad", "flag", "hate",                     │
│   "kill", "stupid", "idiot",                 │
│   "attack"                                   │
│ ]                                            │
│                                              │
│ if any(word in content.lower()               │
│        for word in keywords):                │
│     status = 'FLAGGED'                       │
│ else:                                        │
│     status = 'APPROVED'                      │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ Update database and notify                   │
│ (same as Step 8-10 above)                    │
└──────────────────────────────────────────────┘
```

## Admin Review Flow

### Admin Approves Comment

```
Step 1: Admin views flagged comments
┌──────────────────────────────────────────────┐
│ GET /api/admin/comments/flagged/             │
│ Authorization: Bearer {admin_token}          │
└──────────────┬───────────────────────────────┘
               │
               ▼
Step 2: Authorization check
┌──────────────────────────────────────────────┐
│ IsAuthenticated AND IsAdmin                  │
│ - Verify token valid                         │
│ - Check user.role == 'admin'                 │
└──────────────┬───────────────────────────────┘
               │
               ▼ Authorized
Step 3: Query flagged comments
┌──────────────────────────────────────────────┐
│ Database Query                               │
│ SELECT c.*, p.title, u.username              │
│ FROM content_comment c                       │
│ JOIN content_post p ON c.post_id = p.id      │
│ JOIN content_user u ON c.author_id = u.id    │
│ WHERE c.status = 'FLAGGED'                   │
│ ORDER BY c.created_at DESC                   │
└──────────────┬───────────────────────────────┘
               │
               ▼
Step 4: Return comment list
┌──────────────────────────────────────────────┐
│ HTTP 200 OK                                  │
│ [                                            │
│   {                                          │
│     "id": "comment_uuid",                    │
│     "author": "username",                    │
│     "content": "comment text",               │
│     "post": "post_uuid",                     │
│     "status": "FLAGGED",                     │
│     "created_at": "2024-01-01T00:00:00Z"    │
│   }                                          │
│ ]                                            │
└──────────────┬───────────────────────────────┘
               │
               ▼
Step 5: Admin takes action
┌──────────────────────────────────────────────┐
│ POST /api/admin/comments/{id}/action/        │
│ Authorization: Bearer {admin_token}          │
│ Body: {                                      │
│   "action": "approve"                        │
│ }                                            │
└──────────────┬───────────────────────────────┘
               │
               ▼
Step 6: Validate action
┌──────────────────────────────────────────────┐
│ Validation                                   │
│ - action in ['approve', 'reject']            │
│ - Comment exists                             │
│ - Comment status is FLAGGED                  │
└──────────────┬───────────────────────────────┘
               │
               ▼ Valid
Step 7: Update comment status
┌──────────────────────────────────────────────┐
│ BEGIN TRANSACTION                            │
│                                              │
│ UPDATE content_comment                       │
│ SET status = 'APPROVED',                     │
│     updated_at = NOW()                       │
│ WHERE id = comment_id                        │
│                                              │
│ COMMIT                                       │
└──────────────┬───────────────────────────────┘
               │
               ▼
Step 8: Create notification
┌──────────────────────────────────────────────┐
│ INSERT INTO content_notification             │
│ (id, recipient_id, message, created_at)      │
│ VALUES                                       │
│ ('uuid', comment.author_id,                  │
│  'Your comment was approved by admin',       │
│  NOW())                                      │
└──────────────┬───────────────────────────────┘
               │
               ▼
Step 9: Log action
┌──────────────────────────────────────────────┐
│ [INFO] Admin {admin_id} approved             │
│        comment {comment_id}                  │
└──────────────┬───────────────────────────────┘
               │
               ▼
Step 10: Return response
┌──────────────────────────────────────────────┐
│ HTTP 200 OK                                  │
│ {                                            │
│   "message": "Comment approved"              │
│ }                                            │
└──────────────────────────────────────────────┘
```

### Admin Rejects Comment

```
Same flow as approval, but:

Step 7: Update status to REJECTED
┌──────────────────────────────────────────────┐
│ UPDATE content_comment                       │
│ SET status = 'REJECTED',                     │
│     updated_at = NOW()                       │
│ WHERE id = comment_id                        │
└──────────────┬───────────────────────────────┘
               │
               ▼
Step 8: Queue deletion task
┌──────────────────────────────────────────────┐
│ Celery Task Queue                            │
│ delete_rejected_comment_task.apply_async(    │
│     args=[comment_id],                       │
│     countdown=1728000  # 20 days             │
│ )                                            │
└──────────────┬───────────────────────────────┘
               │
               ▼
Step 9: Notify user
┌──────────────────────────────────────────────┐
│ INSERT notification                          │
│ Message: "Your comment was rejected"         │
└──────────────────────────────────────────────┘
```

## Notification Flow

### Real-Time Notification Delivery

```
Step 1: Event triggers notification
┌──────────────────────────────────────────────┐
│ Comment approved/rejected                    │
│ OR                                           │
│ Comment flagged                              │
└──────────────┬───────────────────────────────┘
               │
               ▼
Step 2: Create notification record
┌──────────────────────────────────────────────┐
│ BEGIN TRANSACTION                            │
│                                              │
│ INSERT INTO content_notification             │
│ (id, recipient_id, message,                  │
│  is_read, created_at)                        │
│ VALUES                                       │
│ ('uuid', user_id, 'notification text',      │
│  FALSE, NOW())                               │
│                                              │
│ COMMIT                                       │
└──────────────┬───────────────────────────────┘
               │
               ▼
Step 3: User requests notifications
┌──────────────────────────────────────────────┐
│ GET /api/notifications/                      │
│ Authorization: Bearer {token}                │
└──────────────┬───────────────────────────────┘
               │
               ▼
Step 4: Query notifications
┌──────────────────────────────────────────────┐
│ Database Query                               │
│ SELECT * FROM content_notification           │
│ WHERE recipient_id = user_id                 │
│ ORDER BY created_at DESC                     │
└──────────────┬───────────────────────────────┘
               │
               ▼
Step 5: Return notifications
┌──────────────────────────────────────────────┐
│ HTTP 200 OK                                  │
│ [                                            │
│   {                                          │
│     "id": "notif_uuid",                      │
│     "message": "Your comment was approved",  │
│     "is_read": false,                        │
│     "created_at": "2024-01-01T00:00:00Z"    │
│   }                                          │
│ ]                                            │
└──────────────┬───────────────────────────────┘
               │
               ▼
Step 6: User marks as read
┌──────────────────────────────────────────────┐
│ POST /api/notifications/{id}/read/           │
│ Authorization: Bearer {token}                │
└──────────────┬───────────────────────────────┘
               │
               ▼
Step 7: Update read status
┌──────────────────────────────────────────────┐
│ UPDATE content_notification                  │
│ SET is_read = TRUE                           │
│ WHERE id = notification_id                   │
│   AND recipient_id = user_id                 │
└──────────────────────────────────────────────┘
```

### Polling Mechanism

```
Frontend JavaScript (base.html):

Every 10 seconds:
    ↓
┌──────────────────────────────────────────────┐
│ fetch('/api/notifications/', {               │
│   headers: {                                 │
│     'Authorization': 'Bearer ' + token       │
│   }                                          │
│ })                                           │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ Update notification badge                    │
│ badge.innerText = data.length                │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ Store in JavaScript variable                 │
│ notificationsData = data                     │
└──────────────────────────────────────────────┘
```

## Database Transaction Flow

### Comment Creation with Transaction

```
BEGIN TRANSACTION
    ↓
┌──────────────────────────────────────────────┐
│ 1. Lock tables (if needed)                   │
│    SELECT ... FOR UPDATE                     │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ 2. Insert comment record                     │
│    INSERT INTO content_comment ...           │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ 3. Increment post comment count (if needed)  │
│    UPDATE content_post                       │
│    SET comment_count = comment_count + 1     │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ 4. Check for errors                          │
│    If error: ROLLBACK                        │
│    If success: COMMIT                        │
└──────────────────────────────────────────────┘
```

### Notification Creation with Transaction

```
BEGIN TRANSACTION
    ↓
┌──────────────────────────────────────────────┐
│ 1. Insert user notification                  │
│    INSERT INTO content_notification          │
│    (recipient_id = author_id, ...)           │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ 2. Insert admin notifications (if flagged)   │
│    FOR EACH admin:                           │
│      INSERT INTO content_notification        │
│      (recipient_id = admin_id, ...)          │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ 3. Update comment status                     │
│    UPDATE content_comment                    │
│    SET status = 'APPROVED'/'FLAGGED'         │
└──────────────┬───────────────────────────────┘
               │
               ▼
COMMIT (or ROLLBACK on error)
```

## Error Handling Flow

### API Error Handling

```
Request received
    ↓
Try:
    Process request
    ↓
    Return success response

Except ValidationError:
    ↓
    ┌──────────────────────────────────────┐
    │ HTTP 400 Bad Request                 │
    │ {                                    │
    │   "detail": "Validation error",      │
    │   "errors": {...}                    │
    │ }                                    │
    └──────────────────────────────────────┘

Except PermissionDenied:
    ↓
    ┌──────────────────────────────────────┐
    │ HTTP 403 Forbidden                   │
    │ {                                    │
    │   "detail": "Permission denied"      │
    │ }                                    │
    └──────────────────────────────────────┘

Except NotFound:
    ↓
    ┌──────────────────────────────────────┐
    │ HTTP 404 Not Found                   │
    │ {                                    │
    │   "detail": "Resource not found"     │
    │ }                                    │
    └──────────────────────────────────────┘

Except DatabaseError:
    ↓
    ┌──────────────────────────────────────┐
    │ HTTP 500 Internal Server Error       │
    │ {                                    │
    │   "detail": "Database error"         │
    │ }                                    │
    │ Log full error details               │
    │ Send alert to monitoring system      │
    └──────────────────────────────────────┘
```

### Task Error Handling

```
Celery task execution
    ↓
Try:
    Execute task logic
    ↓
    Return success

Except Google API Error:
    ↓
    ┌──────────────────────────────────────┐
    │ Log error                            │
    │ Fall back to mock moderation         │
    │ Continue processing                  │
    └──────────────────────────────────────┘

Except Database Error:
    ↓
    ┌──────────────────────────────────────┐
    │ Log error                            │
    │ Retry task (max 3 attempts)          │
    │ If max retries: move to DLQ          │
    └──────────────────────────────────────┘

Except Critical Error:
    ↓
    ┌──────────────────────────────────────┐
    │ Log critical error                   │
    │ Send alert                           │
    │ Mark task as failed                  │
    └──────────────────────────────────────┘
```

## Caching Flow

### Read-Through Cache Pattern

```
Request for post
    ↓
Check cache
    ↓
    ├─── Cache HIT ────────┐
    │                      │
    │                      ▼
    │              ┌──────────────┐
    │              │ Return data  │
    │              └──────────────┘
    │
    └─── Cache MISS
         ↓
    Query database
         ↓
    ┌──────────────────────┐
    │ SELECT * FROM post   │
    │ WHERE id = post_id   │
    └────────┬─────────────┘
             │
             ▼
    Store in cache
    ┌──────────────────────┐
    │ SETEX post:{id}      │
    │ 3600 {data}          │
    └────────┬─────────────┘
             │
             ▼
    Return data to client
```

### Cache Invalidation

```
Post updated
    ↓
┌──────────────────────────────────────┐
│ BEGIN TRANSACTION                    │
│                                      │
│ UPDATE content_post                  │
│ SET title = 'New Title'              │
│ WHERE id = post_id                   │
│                                      │
│ COMMIT                               │
└────────┬─────────────────────────────┘
         │
         ▼
Delete from cache
┌──────────────────────────────────────┐
│ DEL post:{id}                        │
│ DEL posts:page:*                     │
└──────────────────────────────────────┘
```

## Conclusion

This document provides a comprehensive view of data flow through the moderation microservice. Key takeaways:

1. **Asynchronous Processing**: Comment moderation happens asynchronously via Celery
2. **Transactional Integrity**: Database operations use transactions for consistency
3. **Error Resilience**: Multiple fallback mechanisms ensure reliability
4. **Security**: Authentication and authorization checked at every step
5. **Real-Time Updates**: Polling mechanism provides near real-time notifications
6. **Scalability**: Stateless design allows horizontal scaling

Understanding these flows is essential for:

- Debugging production issues
- Optimizing performance
- Adding new features
- Maintaining system reliability
- Training new developers
