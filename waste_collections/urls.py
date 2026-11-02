from django.urls import path
from . import views

urlpatterns = [
    # Collector Mobile Web App
    path('doorstep/', views.collector_doorstep_view, name='collector_doorstep'),
    path('doorstep/submit/', views.doorstep_submit_view, name='doorstep_submit'),

    # REST-Style JSON API Endpoints (FR-51, FR-52)
    path('api/validate-qr/', views.api_validate_qr, name='collector_api_validate_qr'),
    path('api/submit/', views.api_collector_submit, name='collector_api_submit'),
]
