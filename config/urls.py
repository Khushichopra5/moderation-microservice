
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('content.urls_api')),
    path('', include('content.urls_ui')),
]
