from django.shortcuts import render

def landing_view(request):
    """Public home landing page with mission overview and entry portals."""
    return render(request, 'core/landing.html')

def segregation_guide_view(request):
    """Educational guide for 3-way household waste segregation."""
    return render(request, 'core/segregation_guide.html')

def handler400(request, exception=None):
    """Custom bad request handler."""
    return render(request, 'errors/400.html', status=400)

def handler403(request, exception=None):
    """Custom permission denied handler."""
    return render(request, 'errors/403.html', status=403)

def handler404(request, exception=None):
    """Custom not found handler."""
    return render(request, 'errors/404.html', status=404)

def handler500(request):
    """Custom internal server error handler."""
    return render(request, 'errors/500.html', status=500)
