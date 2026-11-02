"""
URL configuration for greenpath project.
GreenPath - Waste Governance System
Monolithic Django routing for HTML Views and REST-style JSON Endpoints.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from accounts import views as accounts_views
from governance import views as governance_views
from households import views as households_views
from waste_collections import views as waste_collections_views
from analytics import views as analytics_views

urlpatterns = [
    # Django Technical Administration
    path('admin/', admin.site.urls),

    # Core Public Interface (Landing, Waste Awareness)
    path('', include('core.urls')),

    # Modular App Inclusions
    path('accounts/', include('accounts.urls')),
    path('governance/', include('governance.urls')),
    path('manager/', include('households.urls')),
    path('households/', include('households.urls')),
    path('collector/', include('waste_collections.urls')),
    path('analytics/', include('analytics.urls')),

    # REST-Style JSON API Contract (SRS Section 3.2.9)
    path('api/v1/auth/login/', accounts_views.api_login, name='api_auth_login'),
    path('api/v1/auth/logout/', accounts_views.api_logout, name='api_auth_logout'),
    path('api/v1/auth/me/', accounts_views.api_me, name='api_auth_me'),
    path('api/v1/villages/', governance_views.api_villages_list_create, name='api_villages'),
    path('api/v1/managers/', governance_views.api_managers_list_create, name='api_managers'),
    path('api/v1/households/', households_views.api_households_list_create, name='api_households'),
    path('api/v1/households/<str:uid>/qr/', households_views.api_household_qr, name='api_household_qr'),
    path('api/v1/collectors/', households_views.api_collectors_list_create, name='api_collectors'),
    path('api/v1/collector/validate-qr/', waste_collections_views.api_validate_qr, name='api_collector_validate_qr'),
    path('api/v1/collector/submit/', waste_collections_views.api_collector_submit, name='api_collector_submit'),
    path('api/v1/reports/summary/', analytics_views.api_reports_summary, name='api_reports_summary'),
    path('api/v1/household/my-status/', analytics_views.api_household_my_status, name='api_household_my_status'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom Error Handlers
handler400 = 'core.views.handler400'
handler403 = 'core.views.handler403'
handler404 = 'core.views.handler404'
handler500 = 'core.views.handler500'
