from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('product/', views.product_view, name='product'),
    path('about/', views.about_view, name='about'),
    path('pricing/', views.pricing_view, name='pricing'),
    path('contact/', views.contact_view, name='contact'),
    path('segregation-guide/', views.segregation_guide_view, name='segregation_guide'),
]
