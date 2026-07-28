from django.shortcuts import render
# from .models import Rutinas

def lista_rutinas(request):
    # Django buscará automáticamente dentro de "templates/rutinas/rutina_list.html"
    return render(request, 'rutinas/rutinas.html')


# def lista_rutinas(request):
#     # Obtenemos todos los ejercicios ordenados por nombre (como definimos en el Meta del modelo)
#     ejercicios = Ejercicio.objects.all()
    
#     context = {
#         'ejercicios': ejercicios
#     }
#     return render(request, 'ejercicios/ejercicio_list.html', context)