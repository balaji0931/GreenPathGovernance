from django.shortcuts import render, redirect
from django.contrib import messages

def landing_view(request):
    """Public home landing page with mission overview, live metrics, and entry portals."""
    return render(request, 'core/landing.html')

def product_view(request):
    """Detailed showcase of the GreenPath software, hardware-free QR engine, and collector PWA."""
    return render(request, 'core/product.html')

def about_view(request):
    """About page outlining mission, grassroots governance, and sustainability roadmap."""
    return render(request, 'core/about.html')

def pricing_view(request):
    """
    Transparent B2B Organization-based pricing:
    Zero cost to direct households; managing organization is charged ₹5/household/month
    with a minimum total of ₹500/month.
    """
    return render(request, 'core/pricing.html')

def contact_view(request):
    """
    Official contact inquiry portal with direct contact@greenpath.com details
    and demo/onboarding request form.
    """
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        org_name = request.POST.get('org_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        households = request.POST.get('households', '').strip()
        message_text = request.POST.get('message', '').strip()

        if not name or not email:
            messages.error(request, "Please provide your name and a valid email address.")
            return render(request, 'core/contact.html', {
                'form_data': request.POST
            })

        # Acknowledge user submission
        messages.success(
            request,
            f"Thank you, {name}! Your message for '{org_name or 'your organization'}' has been received. "
            f"Our onboarding team will reach out to you within 24 hours at {email}."
        )
        return redirect('contact')

    return render(request, 'core/contact.html')

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
