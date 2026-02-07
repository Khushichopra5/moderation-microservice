# System Architecture

## Overview

This document describes the architecture of the Content Moderation Microservice, including its components, interactions, and design decisions.

## Table of Contents

- [High-Level Architecture](#high-level-architecture)
- [System Components](#system-components)
- [Technology Stack](#technology-stack)
- [Data Models](#data-models)
- [API Architecture](#api-architecture)
- [Authentication and Authorization](#authentication-and-authorization)
- [Background Processing](#background-processing)
- [External Integrations](#external-integrations)
- [Security Architecture](#security-architecture)
- [Scalability Considerations](#scalability-considerations)
- [Design Patterns](#design-patterns)

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  Web Browser │  │  Mobile App  │  │  API Client  │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTPS
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                     Django Application                          │
│  ┌────────────────────────────────────────────────────-──────┐  │
│  │                    Django REST Framework                  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │  │
│  │  │   Views     │  │ Serializers │  │    URLs     │        │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘        │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Business Logic                         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │  │
│  │  │   Models    │  │   Services  │  │   Tasks     │        │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘        │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Template Engine                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │  │
│  │  │    HTML     │  │     CSS     │  │  JavaScript │        │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘        │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           │                 │                 │
┌──────────▼──────────┐ ┌───▼──────────┐ ┌───▼─────────────────┐
│    PostgreSQL       │ │    Redis     │ │  Celery Worker      │
│                     │ │              │ │                     │
│  ┌──────────────┐   │ │  ┌────────┐  │ │  ┌──────────────┐   │
│  │   Database   │   │ │  │ Queue  │  │ │  │   Tasks      │   │
│  └──────────────┘   │ │  └────────┘  │ │  └──────────────┘   │
└─────────────────────┘ └──────────────┘ └────────────┬────────┘
                                                      │
                                                      │
                                        ┌─────────────▼──────────┐
                                        │  Google Cloud API      │
                                        │  Natural Language      │
                                        └────────────────────────┘
```

## System Components

### Web Application (Django)

Primary application server handling:

- HTTP request processing
- Business logic execution
- Template rendering
- API endpoint exposure
- Authentication and authorization
- Session management

**Key Responsibilities:**

- Receive and validate user input
- Execute business logic
- Query and update database
- Queue asynchronous tasks
- Return responses to clients

**Technology:**

- Django 4.2 web framework
- Django REST Framework for API
- Gunicorn WSGI server
- Python 3.10

### Database (PostgreSQL)

Relational database storing:

- User accounts and profiles
- Posts and comments
- Notifications
- Moderation history
- Authentication tokens

**Schema Design:**

- Normalized data structure
- Foreign key relationships
- UUID primary keys
- Timestamp tracking
- Indexed columns for performance

**Key Features:**

- ACID compliance
- Complex queries with JOINs
- Transaction support
- Connection pooling

### Message Broker (Redis)

In-memory data store serving as:

- Celery task queue
- Cache backend
- Session storage
- Rate limiting store

**Use Cases:**

- Task message passing
- Temporary data storage
- Pub/sub messaging
- Distributed locks

### Background Workers (Celery)

Asynchronous task processing for:

- Content moderation requests
- Notification delivery
- Scheduled comment deletion
- Background data processing

**Worker Configuration:**

- Prefork concurrency model
- 11 concurrent workers (default)
- Task routing
- Result backend
- Task retry logic

### External API (Google Cloud)

AI-powered content analysis:

- Natural Language API
- Content safety analysis
- Toxicity detection
- Multi-language support

**Integration Method:**

- OAuth2 authentication
- REST API calls
- Service account credentials
- Bearer token authorization

## Technology Stack

### Backend Framework

**Django 4.2**

- Full-featured web framework
- ORM for database operations
- Admin interface
- Authentication system
- Template engine
- Form handling
- Security features

**Django REST Framework**

- RESTful API development
- Serialization/deserialization
- Request/response handling
- Authentication backends
- Permissions system
- Browsable API

### Database Layer

**PostgreSQL 14**

- Open source RDBMS
- ACID compliance
- Complex queries
- JSON support
- Full-text search
- Robust ecosystem

### Message Queue

**Redis 6**

- In-memory data store
- Pub/sub messaging
- Atomic operations
- Persistence options
- Cluster support

**Celery 5**

- Distributed task queue
- Flexible routing
- Task prioritization
- Monitoring tools
- Result storage

### Authentication

**Simple JWT**

- JSON Web Token implementation
- Access/refresh token flow
- Token blacklisting
- Custom claims support

### Frontend

**Bootstrap 5**

- Responsive design
- Pre-built components
- Grid system
- Utilities

**jQuery**

- DOM manipulation
- AJAX requests
- Event handling

### Infrastructure

**Docker**

- Container platform
- Isolated environments
- Reproducible builds
- Easy deployment

**Docker Compose**

- Multi-container orchestration
- Service dependencies
- Network management
- Volume management

## Data Models

### User Model

```python
class User(AbstractUser):
    id = UUIDField(primary_key=True)
    username = CharField(max_length=150, unique=True)
    email = EmailField(unique=True)
    role = CharField(
        max_length=20,
        choices=[('user', 'User'), ('admin', 'Admin')],
        default='user'
    )
    is_staff = BooleanField(default=False)
    is_superuser = BooleanField(default=False)
    date_joined = DateTimeField(auto_now_add=True)
```

**Relationships:**

- One-to-many with Post
- One-to-many with Comment
- One-to-many with Notification

**Indexes:**

- username (unique)
- email (unique)
- role

### Post Model

```python
class Post(Model):
    id = UUIDField(primary_key=True)
    author = ForeignKey(User, on_delete=CASCADE)
    title = CharField(max_length=200)
    content = TextField()
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Relationships:**

- Many-to-one with User (author)
- One-to-many with Comment

**Indexes:**

- created_at (descending)
- author_id

### Comment Model

```python
class Comment(Model):
    id = UUIDField(primary_key=True)
    post = ForeignKey(Post, on_delete=CASCADE)
    author = ForeignKey(User, on_delete=CASCADE)
    content = TextField()
    status = CharField(
        max_length=20,
        choices=[
            ('UNDER_REVIEW', 'Under Review'),
            ('APPROVED', 'Approved'),
            ('FLAGGED', 'Flagged'),
            ('REJECTED', 'Rejected')
        ],
        default='UNDER_REVIEW'
    )
    moderation_response = JSONField(null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Relationships:**

- Many-to-one with Post
- Many-to-one with User (author)

**Indexes:**

- status
- post_id, status (composite)
- created_at (descending)

**Status Flow:**

```
UNDER_REVIEW --> APPROVED (auto or manual)
UNDER_REVIEW --> FLAGGED (by AI)
FLAGGED --> APPROVED (manual)
FLAGGED --> REJECTED (manual)
```

### Notification Model

```python
class Notification(Model):
    id = UUIDField(primary_key=True)
    recipient = ForeignKey(User, on_delete=CASCADE)
    message = TextField()
    is_read = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
```

**Relationships:**

- Many-to-one with User (recipient)

**Indexes:**

- recipient_id, is_read (composite)
- created_at (descending)

## API Architecture

### RESTful Design

**Resource-Based URLs:**

```
/api/auth/login/                          # Authentication
/api/posts/                               # Post collection
/api/posts/{id}/                          # Post resource
/api/posts/{id}/comments/                 # Comment collection
/api/posts/{id}/comments/submit/          # Comment submission
/api/notifications/                       # Notification collection
/api/notifications/{id}/read/             # Mark as read
/api/notifications/mark-all-read/         # Bulk mark as read
/api/admin/comments/flagged/              # Admin: flagged comments
/api/admin/comments/{id}/action/          # Admin: review action
```

**HTTP Methods:**

- GET: Retrieve resources
- POST: Create resources
- PUT/PATCH: Update resources
- DELETE: Remove resources

**Response Format:**

```json
{
  "data": {},
  "message": "",
  "status": "success"
}
```

**Error Format:**

```json
{
  "detail": "Error message",
  "code": "error_code",
  "status": "error"
}
```

### Authentication Flow

```
1. User submits credentials
   POST /api/auth/login/
   Body: {username, password}

2. Server validates credentials
   - Query database
   - Verify password hash
   - Check account status

3. Generate JWT tokens
   - Access token (5 min expiry)
   - Refresh token (24 hour expiry)

4. Return tokens to client
   Response: {access, refresh, user_id, role}

5. Client stores tokens
   - Local storage
   - Session storage
   - HTTP-only cookie

6. Subsequent requests include token
   Authorization: Bearer {access_token}

7. Server validates token
   - Verify signature
   - Check expiration
   - Extract user info

8. Token refresh (when expired)
   POST /api/auth/refresh/
   Body: {refresh}
```

### Pagination Implementation

```python
# Request
GET /api/posts/?page=1&page_size=20

# Implementation
def post_list(request):
    posts = Post.objects.all()
    page = int(request.GET.get('page', 1))
    page_size = min(int(request.GET.get('page_size', 20)), 100)

    total_count = posts.count()
    start = (page - 1) * page_size
    end = start + page_size

    return Response({
        'count': total_count,
        'page': page,
        'page_size': page_size,
        'total_pages': (total_count + page_size - 1) // page_size,
        'results': PostSerializer(posts[start:end], many=True).data
    })

# Response
{
  "count": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5,
  "results": [...]
}
```

## Authentication and Authorization

### JWT Token Structure

**Access Token:**

```json
{
  "token_type": "access",
  "exp": 1234567890,
  "iat": 1234567890,
  "jti": "unique-token-id",
  "user_id": "user-uuid"
}
```

**Refresh Token:**

```json
{
  "token_type": "refresh",
  "exp": 1234567890,
  "iat": 1234567890,
  "jti": "unique-token-id",
  "user_id": "user-uuid"
}
```

### Role-Based Access Control

**Permission Matrix:**

| Resource | User | Admin |
|----------|------|-------|
| Create Post | Yes | Yes |
| View Posts | Yes | Yes |
| Create Comment | Yes | Yes |
| View Own Comments | Yes | Yes |
| View Flagged Comments | No | Yes |
| Approve/Reject Comments | No | Yes |
| View All Notifications | Own | Own |
| User Management | No | Yes |

**Implementation:**

```python
@permission_classes([IsAuthenticated, IsAdmin])
def admin_view(request):
    # Only admins can access
    pass

def is_admin(user):
    return user.role == 'admin'

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'
```

## Background Processing

### Celery Architecture

```
┌─────────────────┐
│  Django App     │
│                 │
│  task.delay()   │
└────────┬────────┘
         │
         │ Serialize task
         │
         ▼
┌─────────────────┐
│     Redis       │
│  (Message Q)    │
└────────┬────────┘
         │
         │ Poll for tasks
         │
         ▼
┌─────────────────┐
│ Celery Worker   │
│                 │
│  Execute task   │
└────────┬────────┘
         │
         │ Store result
         │
         ▼
┌─────────────────┐
│     Redis       │
│  (Result Store) │
└─────────────────┘
```

### Task Types

**Moderation Task:**

```python
@shared_task
def moderate_comment_task(comment_id):
    # Priority: High
    # Retry: 3 attempts
    # Timeout: 30 seconds

    1. Fetch comment from database
    2. Obtain OAuth2 token
    3. Call Google Cloud API
    4. Parse moderation result
    5. Update comment status
    6. Send notifications
    7. Log result
```

**Deletion Task:**

```python
@shared_task
def delete_rejected_comment_task(comment_id):
    # Priority: Low
    # Retry: 1 attempt
    # Countdown: 20 days

    1. Fetch comment from database
    2. Check status is REJECTED
    3. Delete comment
    4. Log deletion
```

### Task Routing

```python
CELERY_ROUTES = {
    'content.tasks.moderate_comment_task': {
        'queue': 'moderation',
        'routing_key': 'moderation.moderate',
    },
    'content.tasks.delete_rejected_comment_task': {
        'queue': 'cleanup',
        'routing_key': 'cleanup.delete',
    }
}
```

## External Integrations

### Google Cloud Natural Language API

**Authentication:**

```python
# Service Account Flow
1. Load service account credentials
   - From environment variable (SERVICE_KEY_JSON)
   - From file (service-account-key.json)

2. Create credentials object
   credentials = service_account.Credentials.from_service_account_info(
       service_account_info,
       scopes=['https://www.googleapis.com/auth/cloud-platform']
   )

3. Refresh token
   credentials.refresh(Request())
   token = credentials.token

4. Use token in API requests
   headers = {'Authorization': f'Bearer {token}'}
```

**API Request:**

```python
POST https://language.googleapis.com/v1/documents:moderateText
Authorization: Bearer {token}
Content-Type: application/json

{
  "document": {
    "type": "PLAIN_TEXT",
    "content": "Comment text to moderate"
  }
}
```

**API Response:**

```json
{
  "moderationCategories": [
    {
      "name": "Toxic",
      "confidence": 0.936
    },
    {
      "name": "Insult",
      "confidence": 0.782
    }
  ]
}
```

**Decision Logic:**

```python
flagged = False
threshold = 0.6

for category in response['moderationCategories']:
    if category['confidence'] > threshold:
        flagged = True
        break

if flagged:
    comment.status = 'FLAGGED'
else:
    comment.status = 'APPROVED'
```

## Security Architecture

### Security Layers

**Transport Security:**

- HTTPS/TLS encryption
- Certificate validation
- Secure headers

**Authentication Security:**

- Password hashing (PBKDF2)
- JWT token signing
- Token expiration
- Refresh token rotation

**Authorization Security:**

- Role-based access control
- Permission checking
- Resource ownership validation

**Input Validation:**

- Request data validation
- SQL injection prevention
- XSS prevention
- CSRF protection

**API Security:**

- Rate limiting
- Request throttling
- IP whitelisting
- API key validation

### Security Best Practices

**Secrets Management:**

- Environment variables for sensitive data
- No hardcoded credentials
- Secure credential storage
- Rotation policies

**Database Security:**

- Parameterized queries
- Connection encryption
- Access control
- Backup encryption

**Session Security:**

- Secure session cookies
- Session timeout
- Session invalidation
- CSRF tokens

## Scalability Considerations

### Horizontal Scaling

**Web Application:**

- Stateless design
- Load balancer distribution
- Session storage in Redis
- No local file storage

**Celery Workers:**

- Independent worker processes
- Auto-scaling based on queue depth
- Task distribution
- Failure isolation

**Database:**

- Read replicas
- Connection pooling
- Query optimization
- Caching layer

### Vertical Scaling

**Resource Optimization:**

- Database query optimization
- Index usage
- Connection pooling
- Memory management

### Caching Strategy

**Cache Levels:**

```
Browser Cache
    ↓
CDN Cache
    ↓
Application Cache (Redis)
    ↓
Database Query Cache
    ↓
Database
```

**Cache Keys:**

- User data: `user:{user_id}`
- Posts: `post:{post_id}`
- Post list: `posts:page:{page}`
- Notifications: `notifications:{user_id}`

## Design Patterns

### Repository Pattern

```python
class CommentRepository:
    @staticmethod
    def get_by_id(comment_id):
        return Comment.objects.get(id=comment_id)

    @staticmethod
    def get_flagged_comments():
        return Comment.objects.filter(status='FLAGGED')

    @staticmethod
    def update_status(comment_id, status):
        comment = Comment.objects.get(id=comment_id)
        comment.status = status
        comment.save()
```

### Service Layer Pattern

```python
class ModerationService:
    def __init__(self):
        self.api_client = GoogleCloudClient()

    def moderate_comment(self, comment):
        result = self.api_client.analyze_text(comment.content)
        decision = self.make_decision(result)
        self.update_comment_status(comment, decision)
        self.send_notifications(comment, decision)
```

### Factory Pattern

```python
class NotificationFactory:
    @staticmethod
    def create_approval_notification(user, comment):
        return Notification.objects.create(
            recipient=user,
            message=f"Your comment was approved"
        )

    @staticmethod
    def create_rejection_notification(user, comment):
        return Notification.objects.create(
            recipient=user,
            message=f"Your comment was rejected"
        )
```

### Observer Pattern

```python
# Signal-based notifications
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Comment)
def comment_saved(sender, instance, created, **kwargs):
    if created and instance.status == 'UNDER_REVIEW':
        moderate_comment_task.delay(instance.id)
```

## Conclusion

This architecture provides a robust, scalable foundation for content moderation. The system is designed with:

- Clear separation of concerns
- Asynchronous processing for performance
- External AI integration for accuracy
- Comprehensive security measures
- Horizontal scalability
- Maintainable codebase

Future enhancements may include:

- Multi-language support
- Advanced analytics
- Machine learning model training
- Real-time websocket notifications
- Microservices decomposition
- Event sourcing
- CQRS pattern implementation
