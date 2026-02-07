
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from django.utils import timezone
from .models import User, Post, Comment, Notification
from .serializers import UserCreateSerializer, PostSerializer, CommentSerializer, NotificationSerializer
from .tasks import moderate_comment_task, delete_rejected_comment_task

# -------------------------
# AUTHENTICATION
# -------------------------

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Login or Register user with JWT tokens
    """
    username = request.data.get("username")
    password = request.data.get("password")
    email = request.data.get("email", "")

    if not username or not password:
        return Response({"error": "credentials required"}, status=400)

    user = User.objects.filter(username=username).first()

    if user:
        # Login
        if not user.check_password(password):
            return Response({"error": "invalid credentials"}, status=401)
    else:
        # Register
        user = User.objects.create_user(username=username, email=email, password=password, role='user')

    refresh = RefreshToken.for_user(user)
    access = refresh.access_token

    return Response({
        "message": "login / registration successful",
        "user_id": str(user.id),
        "username": user.username,
        "role": user.role,
        "access": str(access),
        "refresh": str(refresh)
    })

# -------------------------
# POSTS
# -------------------------

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def post_list(request):
    if request.method == 'GET':
        posts = Post.objects.all()

        # Pagination
        page_size = int(request.GET.get('page_size', 20))  # Default 20 posts per page
        page = int(request.GET.get('page', 1))  # Default to page 1

        # Limit page_size to prevent abuse
        page_size = min(page_size, 100)

        # Calculate pagination
        total_count = posts.count()
        start = (page - 1) * page_size
        end = start + page_size

        paginated_posts = posts[start:end]
        serializer = PostSerializer(paginated_posts, many=True)

        return Response({
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
            'results': serializer.data
        })

    elif request.method == 'POST':
        serializer = PostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    serializer = PostSerializer(post)
    return Response(serializer.data)

# -------------------------
# COMMENTS
# -------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_comments(request, post_id):
    """
    Fetch approved comments for a post
    """
    post = get_object_or_404(Post, id=post_id)
    comments = Comment.objects.filter(post=post, status='APPROVED') # Only approved comments
    serializer = CommentSerializer(comments, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_comment(request, post_id):
    """
    Submit a comment -> status=UNDER_REVIEW -> Trigger Celery Task
    """
    post = get_object_or_404(Post, id=post_id)
    serializer = CommentSerializer(data=request.data)
    
    if serializer.is_valid():
        comment = serializer.save(author=request.user, post=post, status='UNDER_REVIEW')
        
        # Trigger Celery Task
        moderate_comment_task.delay(comment.id)
        
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)

# -------------------------
# ADMIN REVIEW
# -------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_list_flagged_comments(request):
    if request.user.role != 'admin':
        return Response({"error": "Unauthorized"}, status=403)
        
    comments = Comment.objects.filter(status='FLAGGED')
    serializer = CommentSerializer(comments, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_comment_action(request, comment_id):
    if request.user.role != 'admin':
        return Response({"error": "Unauthorized"}, status=403)

    comment = get_object_or_404(Comment, id=comment_id)
    action = request.data.get('action') # 'approve' or 'reject'
    
    if action == 'approve':
        comment.status = 'APPROVED'
        comment.save()
        
        # Follow-up Notification
        Notification.objects.create(
            recipient=comment.author,
            message=f"Your comment on '{comment.post.title}' was approved by an admin."
        )
        return Response({"message": "Comment approved"})

    elif action == 'reject':
        comment.status = 'REJECTED'
        comment.save()
        
        # Follow-up Notification
        Notification.objects.create(
            recipient=comment.author,
            message=f"Your comment on '{comment.post.title}' was rejected by an admin."
        )
        
        # Schedule Deletion
        delete_rejected_comment_task.apply_async((comment.id,), eta=timezone.now() + timezone.timedelta(days=20))
        
        return Response({"message": "Comment rejected and scheduled for deletion"})

    return Response({"error": "Invalid action"}, status=400)

# -------------------------
# NOTIFICATIONS
# -------------------------


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    """
    Get all notifications for the authenticated user
    """
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """
    Mark a specific notification as read
    """
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    return Response({"message": "Notification marked as read"})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    """
    Mark all notifications as read for the authenticated user
    """
    count = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return Response({"message": f"{count} notifications marked as read"})

# -------------------------
# TEMPLATE VIEWS
# -------------------------
from django.shortcuts import render


@api_view(['GET'])
@permission_classes([AllowAny])
def view_login(request):
    return render(request, 'content/login.html')

@api_view(['GET'])
@permission_classes([AllowAny]) 
def view_post_list(request):
    return render(request, 'content/post_list.html')

@api_view(['GET'])
@permission_classes([AllowAny])
def view_post_detail(request, post_id):
    return render(request, 'content/post_detail.html')

@api_view(['GET'])
@permission_classes([AllowAny])
def view_admin_dashboard(request):
    return render(request, 'content/admin_dashboard.html')

