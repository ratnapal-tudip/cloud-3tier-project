"""URL configuration for myproject."""
from django.urls import path, include
from myproject.auth_app import views as auth_views

urlpatterns = [
    # Root endpoint  GET /
    path('', auth_views.root, name='root'),

    # All other endpoints delegated to auth_app
    path('', include('myproject.auth_app.urls')),
]
