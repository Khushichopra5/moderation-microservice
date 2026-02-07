
from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('auth/login/', views.login_view, name='login'),
    
    # Posts
    path('posts/', views.post_list, name='post-list'),
    path('posts/<uuid:post_id>/', views.post_detail, name='post-detail'),
    
    # Comments
    path('posts/<uuid:post_id>/comments/', views.get_comments, name='get-comments'),
    path('posts/<uuid:post_id>/comments/submit/', views.submit_comment, name='submit-comment'),
    
    # Admin
    path('admin/comments/flagged/', views.admin_list_flagged_comments, name='admin-flagged-list'),
    path('admin/comments/<uuid:comment_id>/action/', views.admin_comment_action, name='admin-comment-action'),
    
    # Notifications
    path('notifications/', views.get_notifications, name='get-notifications'),
    
    # Templates
    path('login/', views.view_login, name='view-login'),
    path('posts/', views.view_post_list, name='view-post-list'), # Frontend
    path('posts/<uuid:post_id>/', views.view_post_detail, name='view-post-detail'), # Frontend
    path('admin-dashboard/', views.view_admin_dashboard, name='view-admin-dashboard'),
    path('', views.view_login, name='home'), # Redirect or Home
]

