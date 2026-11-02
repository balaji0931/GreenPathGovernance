from django.urls import path
from . import views

urlpatterns = [
    # Village Manager Central Views
    path('dashboard/', views.manager_dashboard_view, name='manager_dashboard'),
    path('list/', views.household_list_view, name='household_list'),
    path('new/', views.household_create_view, name='household_create'),
    path('<int:household_id>/edit/', views.household_edit_view, name='household_edit'),
    path('<int:household_id>/qr/', views.household_qr_card_view, name='household_qr_card'),
    path('qr-batch/', views.household_qr_batch_view, name='household_qr_batch'),
    path('collectors/', views.collector_list_create_view, name='collector_manage'),
    path('collectors/<int:collector_user_id>/toggle/', views.collector_toggle_status_view, name='collector_toggle_status'),

    # REST-Style JSON API Endpoints (FR-51, FR-52)
    path('api/households/', views.api_households_list_create, name='households_api_list'),
    path('api/households/<str:uid>/qr/', views.api_household_qr, name='households_api_qr'),
    path('api/collectors/', views.api_collectors_list_create, name='collectors_api_list'),
]
