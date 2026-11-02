from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('segregation-guide/', views.segregation_guide_view, name='segregation_guide'),
]

