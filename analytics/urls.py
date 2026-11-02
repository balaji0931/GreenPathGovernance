from django.urls import path
from . import views

urlpatterns = [
    # Village Manager Reports & Analytics (FR-39 to FR-45)
    path('reports/', views.manager_reports_view, name='manager_reports'),

    # Household Resident Portal (FR-46 to FR-50)
    path('household-dashboard/', views.household_dashboard_view, name='household_dashboard'),

    # REST-Style JSON API Endpoints (FR-51, FR-52)
    path('api/reports/summary/', views.api_reports_summary, name='analytics_api_reports_summary'),
    path('api/household/my-status/', views.api_household_my_status, name='analytics_api_household_my_status'),
]
