# Content Moderation Microservice

A production-ready Django-based microservice for automated content moderation using Google Cloud Natural Language API. The system automatically reviews user-generated content, flags inappropriate material, and provides an admin interface for manual review.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## Overview

This microservice provides automated content moderation capabilities for user-generated comments on posts. It integrates with Google Cloud Natural Language API to analyze content for toxicity, hate speech, and other inappropriate material. The system supports both automatic approval of clean content and manual review workflows for flagged content.

### Key Capabilities

- **Automated Moderation**: Real-time content analysis using Google Cloud AI
- **Manual Review**: Admin dashboard for reviewing flagged content
- **User Notifications**: Real-time notifications for content status changes
- **Role-Based Access**: User and Admin roles with appropriate permissions
- **Background Processing**: Asynchronous task processing with Celery
- **RESTful API**: Complete REST API for all operations
- **Web Interface**: Django template-based UI for all user interactions

## Features

### Content Moderation

- Automatic analysis of comments using Google Cloud Natural Language API
- Confidence-based flagging (configurable threshold)
- Support for multiple content categories (Toxic, Insult, Profanity, etc.)
- Fallback to keyword-based moderation if API is unavailable

### User Management

- JWT-based authentication
- Role-based access control (User, Admin)
- User registration and login
- Profile management

### Notification System

- Real-time notifications for users and admins
- Comment status updates (approved, flagged, rejected)
- Mark-as-read functionality
- Bulk notification management

### Admin Dashboard

- Review flagged comments
- Approve or reject content
- View moderation history
- User management

### API Features

- RESTful endpoints for all operations
- JWT authentication
- Pagination support
- Comprehensive error handling
- API documentation

## Technology Stack

### Backend

- **Django 4.2**: Web framework
- **Django REST Framework**: API development
- **PostgreSQL**: Primary database
- **Redis**: Message broker and caching
- **Celery**: Asynchronous task processing
- **Google Cloud Natural Language API**: Content moderation

### Frontend

- **Django Templates**: Server-side rendering
- **Bootstrap 5**: UI framework
- **jQuery**: JavaScript utilities

### Infrastructure

- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration
- **Gunicorn**: WSGI HTTP server
- **Nginx**: Reverse proxy (production)

## Prerequisites

### Required

- Docker 20.10+
- Docker Compose 2.0+
- Google Cloud Platform account with Natural Language API enabled
- Service account credentials with appropriate permissions

### Optional

- Python 3.10+ (for local development)
- PostgreSQL 14+ (for local development)
- Redis 6+ (for local development)

## Installation

### Clone Repository

```bash
git clone https://github.com/yourusername/moderation-microservice.git
cd moderation-microservice
```

### Environment Setup

1. Copy the environment example file:

```bash
cp .env.example .env
```

2. Edit `.env` with your configuration:

```bash
# Django Configuration
SECRET_KEY=your-secret-key-here
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
SQL_ENGINE=django.db.backends.postgresql
SQL_DATABASE=moderation_db
SQL_USER=postgres
SQL_PASSWORD=postgres
SQL_HOST=db
SQL_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# Google Cloud Credentials
SERVICE_KEY_JSON={"type":"service_account",...}
```

### Google Cloud Setup

#### Option 1: Environment Variable (Recommended for Production)

1. Run the conversion script:

```bash
python3 convert_json_to_env.py
```

2. Copy the output and add to `.env`:

```bash
SERVICE_KEY_JSON={"type":"service_account","project_id":"..."}
```

#### Option 2: File-Based (Local Development)

Place your `service-account-key.json` in the project root.

### Build Containers

```bash
docker-compose build
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| SECRET_KEY | Django secret key | - | Yes |
| DEBUG | Debug mode | 0 | No |
| ALLOWED_HOSTS | Allowed host headers | * | Yes |
| SQL_DATABASE | Database name | moderation_db | Yes |
| SQL_USER | Database user | postgres | Yes |
| SQL_PASSWORD | Database password | postgres | Yes |
| SQL_HOST | Database host | db | Yes |
| SQL_PORT | Database port | 5432 | Yes |
| REDIS_URL | Redis connection URL | redis://redis:6379/0 | Yes |
| SERVICE_KEY_JSON | Google Cloud credentials (JSON string) | - | Yes |
| GOOGLE_SERVICE_ACCOUNT_JSON | Path to credentials file | service-account-key.json | No |

### Google Cloud API

The service requires Google Cloud Natural Language API access. Obtain credentials:

1. Create a project in Google Cloud Console
2. Enable Natural Language API
3. Create a service account
4. Download JSON key
5. Configure using one of the methods above

## Running the Application

### Development

Start all services:

```bash
docker-compose up -d
```

Services will be available at:

- Web Application: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f celery
```

### Create Admin User

```bash
docker-compose exec web python manage.py shell
```

```python
from content.models import User
admin = User.objects.create_user(
    username='admin',
    email='admin@example.com',
    password='admin123',
    role='admin'
)
admin.is_staff = True
admin.is_superuser = True
admin.save()
```

Or use the provided script:

```bash
docker-compose exec web python create_test_users.py
```

### Stop Services

```bash
docker-compose down
```

### Reset Database

```bash
docker-compose down -v
docker-compose up -d
```

## API Documentation

### Authentication

#### Login

```http
POST /api/auth/login/
Content-Type: application/json

{
  "username": "user",
  "password": "password"
}
```

Response:

```json
{
  "message": "login / registration successful",
  "user_id": "uuid",
  "username": "user",
  "role": "user",
  "access": "jwt_access_token",
  "refresh": "jwt_refresh_token"
}
```

### Posts

#### List Posts

```http
GET /api/posts/?page=1&page_size=20
Authorization: Bearer {access_token}
```

Response:

```json
{
  "count": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5,
  "results": [
    {
      "id": "uuid",
      "title": "Post Title",
      "content": "Post content",
      "author": "username",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### Create Post

```http
POST /api/posts/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "title": "Post Title",
  "content": "Post content"
}
```

### Comments

#### Submit Comment

```http
POST /api/posts/{post_id}/comments/submit/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "content": "Comment text"
}
```

Response:

```json
{
  "id": "uuid",
  "post": "post_uuid",
  "author": "username",
  "content": "Comment text",
  "status": "UNDER_REVIEW",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Get Comments

```http
GET /api/posts/{post_id}/comments/
Authorization: Bearer {access_token}
```

### Notifications

#### Get Notifications

```http
GET /api/notifications/
Authorization: Bearer {access_token}
```

#### Mark Notification as Read

```http
POST /api/notifications/{notification_id}/read/
Authorization: Bearer {access_token}
```

#### Mark All Notifications as Read

```http
POST /api/notifications/mark-all-read/
Authorization: Bearer {access_token}
```

### Admin Endpoints

#### Get Flagged Comments

```http
GET /api/admin/comments/flagged/
Authorization: Bearer {admin_access_token}
```

#### Review Comment

```http
POST /api/admin/comments/{comment_id}/action/
Authorization: Bearer {admin_access_token}
Content-Type: application/json

{
  "action": "approve"  // or "reject"
}
```

## Testing

### Run Tests

```bash
docker-compose exec web python manage.py test
```

### Manual Testing

1. Start services
2. Create test users
3. Submit comments with various content
4. Check moderation logs
5. Test admin approval/rejection

### Test Reports

See [COMPREHENSIVE_TEST_REPORT.md](COMPREHENSIVE_TEST_REPORT.md) for full test results.

## Project Structure

```
moderation-microservice/
├── config/                      # Django project configuration
│   ├── __init__.py
│   ├── settings.py             # Django settings
│   ├── urls.py                 # Root URL configuration
│   ├── celery.py               # Celery configuration
│   └── wsgi.py                 # WSGI configuration
├── content/                     # Main application
│   ├── migrations/             # Database migrations
│   ├── templates/              # Django templates
│   │   └── content/
│   │       ├── base.html
│   │       ├── login.html
│   │       ├── post_list.html
│   │       ├── post_detail.html
│   │       └── admin_dashboard.html
│   ├── __init__.py
│   ├── models.py               # Data models
│   ├── serializers.py          # DRF serializers
│   ├── views.py                # API views
│   ├── urls_api.py             # API URL routing
│   ├── urls_views.py           # Template view routing
│   └── tasks.py                # Celery tasks
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md
│   └── DATA-FLOW.md
├── docker-compose.yml          # Docker orchestration
├── Dockerfile                  # Container definition
├── entrypoint.sh              # Container startup script
├── requirements.txt           # Python dependencies
├── manage.py                  # Django management script
├── convert_json_to_env.py     # Credentials conversion utility
├── create_test_users.py       # User creation utility
├── .env.example               # Environment template
├── .gitignore                 # Git ignore rules
├── README.md                  # This file
├── ARCHITECTURE.md            # System architecture
├── DATA-FLOW.md               # Data flow documentation
├── RAILWAY_DEPLOYMENT.md      # Railway deployment guide
├── BUG_REPORT.md              # Historical bug reports
├── FIXES_IMPLEMENTED.md       # Implementation changelog
└── COMPREHENSIVE_TEST_REPORT.md  # Test results
```

## Contributing

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Submit a pull request

### Code Style

- Follow PEP 8 guidelines
- Use meaningful variable names
- Add docstrings to functions
- Keep functions focused and small
- Write clear commit messages

### Testing

- Write tests for new features
- Ensure all tests pass
- Maintain test coverage

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Support

For issues and questions:

- GitHub Issues: https://github.com/yourusername/moderation-microservice/issues
- Documentation: See docs/ directory
- Email: support@example.com

## Acknowledgments

- Google Cloud Platform for Natural Language API
- Django and Django REST Framework communities
- Celery project maintainers
- All contributors

## Version History

See [FIXES_IMPLEMENTED.md](FIXES_IMPLEMENTED.md) for detailed changelog.

### Current Version: 1.0.0

- Initial release
- Google Cloud API integration
- Admin notification system
- Pagination support
- Mark-as-read notifications
- Comprehensive logging
- Railway deployment support
