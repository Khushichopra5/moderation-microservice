
from django.urls import path
from . import views

urlpatterns = [
    # Templates
    path('login/', views.view_login, name='view-login'),
    path('posts/', views.view_post_list, name='view-post-list'), # Frontend
    path('posts/<uuid:post_id>/', views.view_post_detail, name='view-post-detail'), # Frontend
    path('admin-dashboard/', views.view_admin_dashboard, name='view-admin-dashboard'),
    path('', views.view_login, name='home'), # Redirect or Home
]
