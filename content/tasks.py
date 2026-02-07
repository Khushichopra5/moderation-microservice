
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import requests
import logging
import os
from .models import Comment, Notification, Post

logger = logging.getLogger(__name__)

def get_google_cloud_token():
    """
    Get OAuth2 access token for Google Cloud API.

    Supports three authentication methods (in order of priority):
    1. Service Account JSON from environment variable (recommended for Railway/cloud deployment)
    2. Service Account JSON from file (for local development)
    3. API Key fallback (deprecated by Google, will fail)

    Returns:
        str: Access token or None
    """
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
        import json

        # Method 1: Service Account JSON from environment variable (Railway deployment)
        service_key_json = getattr(settings, 'SERVICE_KEY_JSON', None)
        if service_key_json:
            try:
                # Parse JSON string from environment variable
                service_account_info = json.loads(service_key_json)
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                credentials.refresh(Request())
                logger.info("Successfully obtained OAuth2 token from SERVICE_KEY_JSON environment variable")
                return credentials.token
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse SERVICE_KEY_JSON: {e}")
            except Exception as e:
                logger.error(f"Failed to get OAuth2 token from SERVICE_KEY_JSON: {e}")

        # Method 2: Service Account JSON from file (local development)
        service_account_path = getattr(settings, 'GOOGLE_SERVICE_ACCOUNT_JSON', None)
        if service_account_path and os.path.exists(service_account_path):
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    service_account_path,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                credentials.refresh(Request())
                logger.info("Successfully obtained OAuth2 token from service account file")
                return credentials.token
            except Exception as e:
                logger.error(f"Failed to get OAuth2 token from service account file: {e}")

    except ImportError as e:
        logger.error(f"Google auth libraries not installed: {e}")
        return None

    # Method 3: API Key (deprecated, will fail for moderateText endpoint)
    api_key = getattr(settings, 'GOOGLE_CLOUD_API', None)
    if api_key:
        logger.warning("Using API key authentication (deprecated for this endpoint)")
        return api_key

    logger.error("No Google Cloud authentication credentials configured")
    return None

@shared_task
def moderate_comment_task(comment_id):
    """
    Moderate a comment using Google Cloud Natural Language API.
    Falls back to keyword-based moderation if API is unavailable.
    """
    try:
        comment = Comment.objects.get(id=comment_id)
    except Comment.DoesNotExist:
        logger.error(f"Comment {comment_id} not found")
        return

    logger.info(f"Starting moderation for comment {comment_id}")

    # Get authentication token
    auth_token = get_google_cloud_token()

    if not auth_token:
        logger.error("No authentication token available, skipping to mock fallback")
        raise Exception("Google Cloud API credentials not configured")

    # Prepare API request
    url = "https://language.googleapis.com/v1/documents:moderateText"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }
    data = {
        "document": {
            "type": "PLAIN_TEXT",
            "content": comment.content
        }
    }

    try:
        logger.debug(f"Calling Google Cloud API for comment {comment_id}")
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()

        logger.info(f"Successfully received moderation result for comment {comment_id}")

        # Store raw API response for audit trail
        comment.moderation_response = result

        # Check moderation categories
        flagged = False
        categories = result.get('moderationCategories', [])

        logger.debug(f"Moderation categories for comment {comment_id}: {categories}")

        for category in categories:
            # Common toxic categories: Toxic, Insult, Profanity, etc.
            # We flag if any category has high confidence (>60%)
            confidence = category.get('confidence', 0)
            if confidence > 0.6:
                flagged = True
                logger.warning(f"Comment {comment_id} flagged: {category.get('name')} (confidence: {confidence})")
                break

        if not flagged:
            comment.status = 'APPROVED'
            comment.save()

            Notification.objects.create(
                recipient=comment.author,
                message=f"Your comment on '{comment.post.title}' has been successfully posted."
            )
            logger.info(f"Comment {comment_id} APPROVED via Google Cloud API")
        else:
            comment.status = 'FLAGGED'
            comment.save()

            # Notify comment author
            Notification.objects.create(
                recipient=comment.author,
                message=f"Your comment on '{comment.post.title}' has been flagged and is under review."
            )

            # Notify all admins
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admins = User.objects.filter(role='admin')
            admin_count = 0
            for admin in admins:
                Notification.objects.create(
                    recipient=admin,
                    message=f"New flagged comment requires review: {comment.id}"
                )
                admin_count += 1

            logger.critical(f"FLAGGED CONTENT DETECTED: Comment {comment_id} - {admin_count} admins notified")

    except Exception as e:
        logger.error(f"Error calling Google Cloud API: {e}")
        logger.warning("FALLBACK: Using Mock Moderation (keyword-based detection)")

        # Mock Fallback for testing/unconfigured envs
        if any(word in comment.content.lower() for word in ["bad", "flag", "hate", "kill", "stupid", "idiot", "attack"]):
            comment.status = 'FLAGGED'
            comment.save()

            # Notify comment author
            Notification.objects.create(
                recipient=comment.author,
                message=f"Your comment on '{comment.post.title}' has been flagged and is under review."
            )

            # BUG FIX #2: Notify admins about flagged content (was missing!)
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admins = User.objects.filter(role='admin')
            for admin in admins:
                Notification.objects.create(
                    recipient=admin,
                    message=f"New flagged comment requires review: {comment.id} [Mock Moderation]"
                )

            # BUG FIX #3: Create alert for operations team
            logger.critical(f"FLAGGED CONTENT DETECTED (Mock): Comment {comment.id} - Admins notified")

        else:
            comment.status = 'APPROVED'
            comment.save()
            Notification.objects.create(
                recipient=comment.author,
                message=f"Your comment on '{comment.post.title}' has been successfully posted."
            )
            logger.info(f"Comment {comment.id} auto-approved via Mock Moderation")

@shared_task
def delete_rejected_comment_task(comment_id):
    try:
        comment = Comment.objects.get(id=comment_id)
        if comment.status == 'REJECTED':
            comment.delete()
    except Comment.DoesNotExist:
        pass
