from django.shortcuts import render

def dashboard(request):
    # Django buscará automáticamente dentro de "templates/dashboard/dashboard.html"
    return render(request, 'dashboard/dashboard.html')