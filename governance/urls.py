from django.urls import path
from . import views

urlpatterns = [
    # Super Admin HTML Views
    path('admin-dashboard/', views.superadmin_dashboard_view, name='superadmin_dashboard'),
    path('villages/new/', views.village_create_view, name='village_create'),
    path('villages/<int:village_id>/', views.village_detail_view, name='village_detail'),
    path('villages/<int:village_id>/wards/new/', views.ward_create_view, name='ward_create'),
    path('villages/<int:village_id>/toggle/', views.village_toggle_status_view, name='village_toggle_status'),
    path('managers/new/', views.manager_create_view, name='manager_create'),

    # REST-Style JSON API Endpoints (FR-51, FR-52)
    path('api/villages/', views.api_villages_list_create, name='governance_api_villages'),
    path('api/managers/', views.api_managers_list_create, name='governance_api_managers'),
]
