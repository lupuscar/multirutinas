from django.shortcuts import render
from .models import Ejercicio

# def lista_ejercicios(request):
#     # Django buscará automáticamente dentro de "templates/ejercicios/ejercicio_list.html"
#     return render(request, 'ejercicios/ejercicios.html')


def lista_ejercicios(request):
    # Obtenemos todos los ejercicios ordenados por nombre (como definimos en el Meta del modelo)
    ejercicios = Ejercicio.objects.all()
    
    context = {
        'ejercicios': ejercicios
    }
    return render(request, 'ejercicios/ejercicio_list.html', context)