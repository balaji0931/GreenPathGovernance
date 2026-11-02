from django.urls import path
from . import views

urlpatterns = [
    # Browser Template Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('redirect/', views.role_redirect_view, name='role_redirect'),

    # REST-Style JSON API Authentication (SRS FR-51)
    path('api/login/', views.api_login, name='accounts_api_login'),
    path('api/logout/', views.api_logout, name='accounts_api_logout'),
    path('api/me/', views.api_me, name='accounts_api_me'),
]
