"""
auth_app URL configuration.
All routes mirror the FastAPI endpoints in main.py.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Health checks
    path('health',       views.health_check,    name='health_check'),
    path('health/ready', views.readiness_check, name='readiness_check'),
    path('health/live',  views.liveness_check,  name='liveness_check'),

    # Auth
    path('api/auth/signup', views.signup, name='signup'),
    path('api/auth/login',  views.login,  name='login'),

    # Protected user endpoints
    path('api/me',        views.get_profile, name='get_profile'),
    path('api/dashboard', views.dashboard,   name='dashboard'),
]
