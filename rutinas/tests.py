import json
from django.test import TestCase, RequestFactory, Client
from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite
from django.urls import reverse
from django.utils import timezone

from rutinas.models import Rutina, RutinaEjercicio
from ejercicios.models import Ejercicio, RegistroEjercicio, Serie
from rutinas.admin import RutinaAdmin, iniciar_rutina_hoy


class MockModelAdmin:
    def __init__(self):
        self.messages = []

    def message_user(self, request, message, level=None):
        self.messages.append((message, level))


class RutinaAppTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client.login(username='testuser', password='password123')

        # Ejercicio de Fuerza (Peso + Reps)
        self.ejercicio_peso = Ejercicio.objects.create(
            nombre='Press de Banca',
            definicion='Técnica pecho',
            modalidad='REPS_PESO',
            grupo_muscular='PEC'
        )

        # Ejercicio de Tiempo
        self.ejercicio_tiempo = Ejercicio.objects.create(
            nombre='Plancha Abdominal',
            definicion='Técnica core',
            modalidad='TIEMPO',
            grupo_muscular='COR'
        )

        # Rutina de prueba
        self.rutina = Rutina.objects.create(nombre='Torso y Core', usuario=self.user)
        RutinaEjercicio.objects.create(
            rutina=self.rutina,
            ejercicio=self.ejercicio_peso,
            orden=1,
            series_objetivo=3,
            repeticiones_objetivo=10
        )
        RutinaEjercicio.objects.create(
            rutina=self.rutina,
            ejercicio=self.ejercicio_tiempo,
            orden=2,
            series_objetivo=3,
            tiempo_objetivo_segundos=45
        )

    def test_iniciar_rutina_hoy_action_admin(self):
        """Verifica la acción del panel admin creando series de peso y de tiempo"""
        request = self.factory.get('/admin/')
        request.user = self.user
        modeladmin = MockModelAdmin()

        iniciar_rutina_hoy(modeladmin, request, Rutina.objects.filter(id=self.rutina.id))

        registros = RegistroEjercicio.objects.filter(usuario=self.user)
        self.assertEqual(registros.count(), 2)

        reg_peso = registros.get(ejercicio=self.ejercicio_peso)
        self.assertEqual(reg_peso.series_detalle.count(), 3)
        self.assertEqual(reg_peso.series_detalle.first().repeticiones, 10)

        reg_tiempo = registros.get(ejercicio=self.ejercicio_tiempo)
        self.assertEqual(reg_tiempo.series_detalle.count(), 3)
        self.assertEqual(reg_tiempo.series_detalle.first().tiempo_segundos, 45)

    def test_crear_rutina_view(self):
        """Verifica la creación interactiva de una rutina desde la web"""
        payload = {
            'nombre': 'Rutina Nueva Web',
            'descripcion': 'Probando creador de rutinas',
            'ejercicios': [
                {
                    'ejercicio_id': self.ejercicio_peso.id,
                    'series_objetivo': 4,
                    'repeticiones_objetivo': 12,
                    'tiempo_objetivo_segundos': None
                }
            ]
        }
        response = self.client.post(
            reverse('rutinas:crear_rutina'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        nueva_rutina = Rutina.objects.filter(nombre='Rutina Nueva Web', usuario=self.user).first()
        self.assertIsNotNone(nueva_rutina)
        self.assertEqual(nueva_rutina.ejercicios.count(), 1)

    def test_crear_ejercicio_rapido_ajax(self):
        """Verifica la creación de un ejercicio personalizado por el usuario"""
        payload = {
            'nombre': 'Dominadas Neutras',
            'modalidad': 'REPS_PESO',
            'grupo_muscular': 'ESP',
            'tipo': 'CAL'
        }
        response = self.client.post(
            reverse('rutinas:crear_ejercicio_rapido_ajax'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['ejercicio']['nombre'], 'Dominadas Neutras')

        # Comprobar que pertenece al usuario
        ej = Ejercicio.objects.get(id=data['ejercicio']['id'])
        self.assertEqual(ej.creado_por, self.user)

    def test_guardar_serie_ajax_peso_y_tiempo(self):
        """Verifica el guardado en directo desde el 'Modo Gym' de series con peso y con tiempo"""
        # Guardar serie con peso y reps
        payload_peso = {
            'ejercicio_id': self.ejercicio_peso.id,
            'numero_serie': 1,
            'repeticiones': 10,
            'peso': 70.5,
            'tiempo_segundos': None,
            'rutina_nombre': 'Torso y Core'
        }
        res1 = self.client.post(
            reverse('rutinas:guardar_serie_ajax'),
            data=json.dumps(payload_peso),
            content_type='application/json'
        )
        self.assertEqual(res1.status_code, 200)

        # Guardar serie con tiempo
        payload_tiempo = {
            'ejercicio_id': self.ejercicio_tiempo.id,
            'numero_serie': 1,
            'repeticiones': None,
            'peso': None,
            'tiempo_segundos': 60,
            'rutina_nombre': 'Torso y Core'
        }
        res2 = self.client.post(
            reverse('rutinas:guardar_serie_ajax'),
            data=json.dumps(payload_tiempo),
            content_type='application/json'
        )
        self.assertEqual(res2.status_code, 200)

        # Verificar en base de datos
        serie_peso = Serie.objects.filter(registro__ejercicio=self.ejercicio_peso, numero_serie=1).first()
        self.assertIsNotNone(serie_peso)
        self.assertEqual(float(serie_peso.peso_kg), 70.5)

        serie_tiempo = Serie.objects.filter(registro__ejercicio=self.ejercicio_tiempo, numero_serie=1).first()
        self.assertIsNotNone(serie_tiempo)
        self.assertEqual(serie_tiempo.tiempo_segundos, 60)

        # Guardar serie con tiempo y distancia en km (carrera / cardio)
        payload_distancia = {
            'ejercicio_id': self.ejercicio_tiempo.id,
            'numero_serie': 2,
            'tiempo_segundos': 1200,
            'distancia_km': 4.5,
            'rutina_nombre': 'Torso y Core'
        }
        res3 = self.client.post(
            reverse('rutinas:guardar_serie_ajax'),
            data=json.dumps(payload_distancia),
            content_type='application/json'
        )
        self.assertEqual(res3.status_code, 200)

        serie_dist = Serie.objects.filter(registro__ejercicio=self.ejercicio_tiempo, numero_serie=2).first()
        self.assertIsNotNone(serie_dist)
        self.assertEqual(float(serie_dist.distancia_km), 4.5)
        self.assertEqual(serie_dist.tiempo_segundos, 1200)

    def test_dashboard_view(self):
        """Verifica que el dashboard carga sin errores y calcula métricas"""
        # Crear un registro con serie para simular actividad
        reg = RegistroEjercicio.objects.create(usuario=self.user, ejercicio=self.ejercicio_peso)
        Serie.objects.create(registro=reg, numero_serie=1, repeticiones=10, peso_kg=80.0, distancia_km=5.0)

        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tu Progreso')
        self.assertIn('volumen_total', response.context)
        self.assertEqual(response.context['volumen_total'], 800.0)
        self.assertIn('km_total', response.context)
        self.assertEqual(response.context['km_total'], 5.0)

    def test_rutina_dias_semana_model_methods(self):
        """Verifica los métodos y propiedades de días de la semana en el modelo Rutina"""
        hoy_weekday = timezone.now().date().weekday()
        otro_dia = (hoy_weekday + 1) % 7

        # Rutina con días programados
        rutina_programada = Rutina.objects.create(
            nombre='Rutina Programada',
            usuario=self.user,
            dias_semana=f"{hoy_weekday},{otro_dia}"
        )
        self.assertEqual(rutina_programada.lista_dias_numeros, sorted([hoy_weekday, otro_dia]))
        self.assertEqual(len(rutina_programada.badges_dias), 2)
        self.assertTrue(rutina_programada.toca_hoy)

        # Rutina sin días asignados
        rutina_sin_dias = Rutina.objects.create(
            nombre='Rutina Sin Días',
            usuario=self.user,
            dias_semana=""
        )
        self.assertEqual(rutina_sin_dias.lista_dias_numeros, [])
        self.assertEqual(rutina_sin_dias.badges_dias, [])
        self.assertFalse(rutina_sin_dias.toca_hoy)

    def test_crear_rutina_con_dias_semana_view(self):
        """Verifica que al crear una rutina vía JSON se persistan los días seleccionados"""
        payload = {
            'nombre': 'Rutina Con Días',
            'descripcion': 'Martes y Jueves',
            'dias_semana': [1, 3],
            'ejercicios': [
                {
                    'ejercicio_id': self.ejercicio_peso.id,
                    'series_objetivo': 3,
                    'repeticiones_objetivo': 10
                }
            ]
        }
        response = self.client.post(
            reverse('rutinas:crear_rutina'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        creada = Rutina.objects.filter(nombre='Rutina Con Días', usuario=self.user).first()
        self.assertIsNotNone(creada)
        self.assertEqual(creada.dias_semana, '1,3')
        self.assertEqual([b['corto'] for b in creada.badges_dias], ['Mar', 'Jue'])

    def test_editar_rutina_con_dias_semana_view(self):
        """Verifica que al editar una rutina se actualicen los días asignados"""
        payload = {
            'nombre': 'Torso y Core Actualizado',
            'descripcion': 'Nueva descripción',
            'dias_semana': [0, 4],  # Lunes y Viernes
            'ejercicios': [
                {
                    'ejercicio_id': self.ejercicio_peso.id,
                    'series_objetivo': 4,
                    'repeticiones_objetivo': 8
                }
            ]
        }
        response = self.client.post(
            reverse('rutinas:editar_rutina', args=[self.rutina.id]),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.rutina.refresh_from_db()
        self.assertEqual(self.rutina.dias_semana, '0,4')
        self.assertEqual([b['corto'] for b in self.rutina.badges_dias], ['Lun', 'Vie'])

    def test_lista_rutinas_muestra_dias_y_toca_hoy(self):
        """Verifica que en la lista de rutinas se rendericen los badges de días y Toca Hoy"""
        hoy_weekday = timezone.now().date().weekday()
        self.rutina.dias_semana = str(hoy_weekday)
        self.rutina.save()

        response = self.client.get(reverse('rutinas:lista_rutinas'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '¡Toca hoy!')

    def test_crear_rutina_con_peso_objetivo(self):
        """Verifica que al crear una rutina se guarde el peso objetivo planificado"""
        payload = {
            'nombre': 'Rutina Con Cargas',
            'descripcion': 'Fuerza hipertrofia',
            'ejercicios': [
                {
                    'ejercicio_id': self.ejercicio_peso.id,
                    'series_objetivo': 4,
                    'repeticiones_objetivo': 8,
                    'peso_objetivo': 65.5
                }
            ]
        }
        response = self.client.post(
            reverse('rutinas:crear_rutina'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        rutina_creada = Rutina.objects.filter(nombre='Rutina Con Cargas').first()
        self.assertIsNotNone(rutina_creada)
        re = rutina_creada.rutinaejercicio_set.first()
        self.assertEqual(float(re.peso_objetivo), 65.5)

    def test_editar_rutina_actualiza_peso_objetivo(self):
        """Verifica que al editar una rutina se persista la modificación del peso objetivo"""
        payload = {
            'nombre': 'Torso Actualizado',
            'descripcion': 'Incremento de cargas',
            'ejercicios': [
                {
                    'ejercicio_id': self.ejercicio_peso.id,
                    'series_objetivo': 3,
                    'repeticiones_objetivo': 10,
                    'peso_objetivo': 70.0
                }
            ]
        }
        response = self.client.post(
            reverse('rutinas:editar_rutina', args=[self.rutina.id]),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.rutina.refresh_from_db()
        re = self.rutina.rutinaejercicio_set.filter(ejercicio=self.ejercicio_peso).first()
        self.assertEqual(float(re.peso_objetivo), 70.0)

    def test_iniciar_rutina_precarga_peso_objetivo_e_historial(self):
        """Verifica que el Modo Gym inicialice las series con el peso objetivo o datos históricos"""
        # Configuramos peso objetivo en la rutina
        re_peso = self.rutina.rutinaejercicio_set.get(ejercicio=self.ejercicio_peso)
        re_peso.peso_objetivo = 55.0
        re_peso.save()

        # Caso A: Sin historial previo -> Las series deben sugerir 55.0 kg
        res = self.client.get(reverse('rutinas:iniciar_rutina', args=[self.rutina.id]))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, '55.0')

        # Caso B: Con historial previo de 60 kg -> Debe sugerir 60 kg y ofrecer peso anterior
        reg = RegistroEjercicio.objects.create(usuario=self.user, ejercicio=self.ejercicio_peso)
        Serie.objects.create(registro=reg, numero_serie=1, repeticiones=8, peso_kg=60.0)

        res_con_historial = self.client.get(reverse('rutinas:iniciar_rutina', args=[self.rutina.id]))
        self.assertEqual(res_con_historial.status_code, 200)
        self.assertContains(res_con_historial, '60.0')

    # =========================================================================
    # PRUEBAS DEL RECOMENDADOR AUTOMÁTICO DE RUTINAS
    # =========================================================================
    def test_generar_plan_recomendado_diferentes_dias(self):
        """Verifica que el generador produzca la cantidad exacta de rutinas según la meta semanal (2 a 6 días)"""
        from rutinas.recomendador import generar_plan_recomendado

        for dias in [2, 3, 4, 5, 6]:
            plan = generar_plan_recomendado(self.user, {'dias_semana': dias})
            self.assertEqual(len(plan['rutinas']), dias)
            self.assertEqual(plan['dias_semana'], dias)
            for r in plan['rutinas']:
                self.assertTrue(len(r['ejercicios']) >= 3)
                self.assertTrue(bool(r['dias_semana']))

    def test_generar_plan_adaptacion_objetivos_y_niveles(self):
        """Verifica que los objetivos modifiquen repeticiones y descansos adecuadamente"""
        from rutinas.recomendador import generar_plan_recomendado

        # Fuerza (FUE) debe tener descansos >= 120s y repeticiones bajas (4-8)
        plan_fuerza = generar_plan_recomendado(self.user, {'objetivo': 'FUE', 'nivel': 'AV'})
        self.assertGreaterEqual(plan_fuerza['descanso_promedio_seg'], 120)
        primer_ej = plan_fuerza['rutinas'][0]['ejercicios'][0]
        self.assertLessEqual(primer_ej['repeticiones_objetivo'], 6)

        # Definición (DEF) debe tener descansos <= 60s y repeticiones altas (>= 12)
        plan_def = generar_plan_recomendado(self.user, {'objetivo': 'DEF', 'nivel': 'PR'})
        self.assertLessEqual(plan_def['descanso_promedio_seg'], 60)
        primer_ej_def = plan_def['rutinas'][0]['ejercicios'][0]
        self.assertGreaterEqual(primer_ej_def['repeticiones_objetivo'], 12)

    def test_generar_plan_adaptacion_edad_y_genero(self):
        """Verifica que la edad >= 50 aumente el descanso y que el género sea reflejado en el plan"""
        from rutinas.recomendador import generar_plan_recomendado

        # Adulto mayor >= 50
        plan_senior = generar_plan_recomendado(self.user, {'edad': 55, 'genero': 'M', 'objetivo': 'HIP'})
        self.assertEqual(plan_senior['descanso_promedio_seg'], 75 + 15)
        self.assertTrue(any('estabilidad articular' in n.lower() or 'soporte lumbar' in n.lower() for n in plan_senior['notas_adaptacion']))

        # Mujer: nota específica de tren inferior
        self.assertTrue(any('glúteos' in n.lower() for n in plan_senior['notas_adaptacion']))

    def test_vista_recomendador_rutinas_get_y_post_ajax(self):
        """Verifica que la vista GET renderice la plantilla y que POST/AJAX devuelva JSON con el plan"""
        # GET estándar
        res_get = self.client.get(reverse('rutinas:recomendador_rutinas'))
        self.assertEqual(res_get.status_code, 200)
        self.assertTemplateUsed(res_get, 'rutinas/recomendador.html')
        self.assertContains(res_get, 'Recomendador de Rutinas')

        # POST AJAX
        payload = {
            'dias_semana': 3,
            'objetivo': 'HIP',
            'nivel': 'IN',
            'genero': 'H',
            'edad': 30
        }
        res_post = self.client.post(
            reverse('rutinas:recomendador_rutinas'),
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(res_post.status_code, 200)
        data = res_post.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['plan']['rutinas']), 3)

    def test_guardar_plan_recomendado_ajax_en_base_de_datos(self):
        """Verifica que guardar_plan_recomendado_ajax persista las rutinas y ejercicios en la BD"""
        from rutinas.recomendador import generar_plan_recomendado

        plan = generar_plan_recomendado(self.user, {'dias_semana': 3})
        payload = {'rutinas': plan['rutinas']}

        response = self.client.post(
            reverse('rutinas:guardar_plan_recomendado_ajax'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data['status'], 'success')
        self.assertEqual(len(res_data['rutinas_creadas']), 3)

        # Verificar que se crearon en la BD vinculadas al usuario
        rutinas_creadas = Rutina.objects.filter(usuario=self.user, nombre__in=res_data['rutinas_creadas'])
        self.assertEqual(rutinas_creadas.count(), 3)
        for r in rutinas_creadas:
            self.assertGreater(r.ejercicios.count(), 0)
            self.assertTrue(bool(r.dias_semana))

    def test_generar_plan_resistencia_cardiovascular_y_calistenia(self):
        """Verifica que el plan de Resistencia (RES) incluya ejercicios cardiovasculares y calistenia con tiempos continuos"""
        from rutinas.recomendador import generar_plan_recomendado

        plan_res = generar_plan_recomendado(self.user, {'objetivo': 'RES', 'dias_semana': 3, 'nivel': 'IN'})
        self.assertEqual(plan_res['objetivo_codigo'], 'RES')
        self.assertTrue('Running' in plan_res['descripcion_esquema'] or 'Resistencia' in plan_res['descripcion_esquema'])

        # Debe contener al menos un ejercicio cardiovascular con modalidad TIEMPO y >= 600 segundos (10 min)
        todos_ejercicios = [ej for r in plan_res['rutinas'] for ej in r['ejercicios']]
        ejercicios_cardio = [ej for ej in todos_ejercicios if ej['modalidad'] == 'TIEMPO' and (ej['tiempo_objetivo_segundos'] or 0) >= 600]
        self.assertGreaterEqual(len(ejercicios_cardio), 1)
        self.assertTrue(any('min' in (ej.get('tiempo_display') or '') for ej in ejercicios_cardio))

    def test_generar_plan_salud_incluye_movilidad_y_cardio_suave(self):
        """Verifica que el plan de Salud (SAL) incorpore movilidad/yoga, ejercicios guiados y descansos seguros"""
        from rutinas.recomendador import generar_plan_recomendado

        plan_sal = generar_plan_recomendado(self.user, {'objetivo': 'SAL', 'dias_semana': 3, 'nivel': 'PR'})
        self.assertEqual(plan_sal['objetivo_codigo'], 'SAL')
        self.assertTrue('Salud' in plan_sal['descripcion_esquema'] or 'Movilidad' in plan_sal['descripcion_esquema'])

        todos_nombres = [ej['nombre'].lower() for r in plan_sal['rutinas'] for ej in r['ejercicios']]
        tiene_movilidad_o_cardio = any(k in n for n in todos_nombres for k in ['yoga', 'movilidad', 'caminata', 'senderismo', 'bicicleta', 'prensa'])
        self.assertTrue(tiene_movilidad_o_cardio)

    def test_generar_plan_fuerza_prioriza_basicos_y_descansos_largos(self):
        """Verifica que el plan de Fuerza (FUE) programe levantamientos pesados y descansos >= 120s"""
        from rutinas.recomendador import generar_plan_recomendado

        plan_fue = generar_plan_recomendado(self.user, {'objetivo': 'FUE', 'dias_semana': 3, 'nivel': 'AV'})
        self.assertEqual(plan_fue['objetivo_codigo'], 'FUE')
        self.assertGreaterEqual(plan_fue['descanso_promedio_seg'], 120)

        primer_dia_ej = [ej['nombre'].lower() for ej in plan_fue['rutinas'][0]['ejercicios']]
        # El primer día de fuerza debe incluir sentadilla o banca
        tiene_basico = any('sentadilla' in n or 'banca' in n for n in primer_dia_ej)
        self.assertTrue(tiene_basico)

    def test_todos_los_objetivos_generan_planes_validos_en_todas_las_frecuencias(self):
        """Verifica que todos los objetivos (HIP, FUE, DEF, RES, SAL) produzcan planes completos de 2 a 6 días"""
        from rutinas.recomendador import generar_plan_recomendado

        for obj in ['HIP', 'FUE', 'DEF', 'RES', 'SAL']:
            for dias in [2, 3, 4, 5, 6]:
                plan = generar_plan_recomendado(self.user, {'objetivo': obj, 'dias_semana': dias})
                self.assertEqual(len(plan['rutinas']), dias, f"Fallo en objetivo {obj} con {dias} días")
                self.assertTrue(bool(plan['descripcion_esquema']))
                for r in plan['rutinas']:
                    self.assertGreaterEqual(len(r['ejercicios']), 3)

    def test_estimar_peso_partida_por_nivel_y_genero(self):
        """Verifica que estimar_peso_partida calcule cargas realistas según nivel y género"""
        from rutinas.recomendador import estimar_peso_partida

        # Hombre Principiante vs Intermedio vs Avanzado en Press de Banca
        peso_h_pr = estimar_peso_partida(self.ejercicio_peso, nivel='PR', genero='H')
        peso_h_in = estimar_peso_partida(self.ejercicio_peso, nivel='IN', genero='H')
        peso_h_av = estimar_peso_partida(self.ejercicio_peso, nivel='AV', genero='H')
        self.assertEqual(peso_h_pr, 35.0)
        self.assertEqual(peso_h_in, 60.0)
        self.assertEqual(peso_h_av, 85.0)

        # Mujer Principiante vs Intermedia en Press de Banca
        peso_m_pr = estimar_peso_partida(self.ejercicio_peso, nivel='PR', genero='M')
        peso_m_in = estimar_peso_partida(self.ejercicio_peso, nivel='IN', genero='M')
        self.assertEqual(peso_m_pr, 17.5)
        self.assertEqual(peso_m_in, 30.0)

        # Ejercicio de tiempo o calistenia sin lastre devuelve None
        ej_flex = Ejercicio.objects.create(nombre='Flexiones Clásicas', tipo='CAL', modalidad='REPS_PESO')
        self.assertIsNone(estimar_peso_partida(ej_flex, nivel='IN', genero='H'))
        self.assertIsNone(estimar_peso_partida(self.ejercicio_tiempo, nivel='IN', genero='H'))

    def test_obtener_peso_objetivo_recomendado_prioriza_historial(self):
        """Verifica que el recomendador use la última marca real del usuario si existe en su historial"""
        from rutinas.recomendador import obtener_peso_objetivo_recomendado

        # Sin historial: devuelve peso sugerido de partida
        peso_sug, origen_sug = obtener_peso_objetivo_recomendado(self.user, self.ejercicio_peso, nivel='IN', genero='H')
        self.assertEqual(peso_sug, 60.0)
        self.assertEqual(origen_sug, 'sugerido')

        # Creamos un registro anterior con serie real de 72.5 kg
        reg = RegistroEjercicio.objects.create(usuario=self.user, ejercicio=self.ejercicio_peso)
        Serie.objects.create(registro=reg, numero_serie=1, repeticiones=8, peso_kg=72.5)

        # Con historial: devuelve la marca real de 72.5 kg con origen 'historial'
        peso_hist, origen_hist = obtener_peso_objetivo_recomendado(self.user, self.ejercicio_peso, nivel='IN', genero='H')
        self.assertEqual(peso_hist, 72.5)
        self.assertEqual(origen_hist, 'historial')

    def test_guardar_plan_recomendado_persiste_valores_modificados_por_usuario(self):
        """Verifica que los pesos, series, repeticiones y distancias editados por el usuario se guarden fielmente"""
        payload = {
            'rutinas': [
                {
                    'nombre': 'Rutina Personalizada Recomendador',
                    'descripcion': 'Ajustada por el usuario',
                    'dias_semana': '0,2,4',
                    'ejercicios': [
                        {
                            'ejercicio_id': self.ejercicio_peso.id,
                            'series_objetivo': 4,
                            'repeticiones_objetivo': 12,
                            'peso_objetivo': '57.5',  # Modificado manualmente
                            'distancia_objetivo_km': None,
                            'tiempo_objetivo_segundos': None,
                        },
                        {
                            'ejercicio_id': self.ejercicio_tiempo.id,
                            'series_objetivo': 3,
                            'repeticiones_objetivo': None,
                            'peso_objetivo': None,
                            'distancia_objetivo_km': '5.5',  # Modificado manualmente
                            'tiempo_objetivo_segundos': 1800,
                        }
                    ]
                }
            ]
        }

        response = self.client.post(
            reverse('rutinas:guardar_plan_recomendado_ajax'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        rutina_guardada = Rutina.objects.filter(nombre='Rutina Personalizada Recomendador', usuario=self.user).first()
        self.assertIsNotNone(rutina_guardada)

        ej_peso_guardado = RutinaEjercicio.objects.get(rutina=rutina_guardada, ejercicio=self.ejercicio_peso)
        self.assertEqual(ej_peso_guardado.series_objetivo, 4)
        self.assertEqual(ej_peso_guardado.repeticiones_objetivo, 12)
        self.assertEqual(float(ej_peso_guardado.peso_objetivo), 57.5)

        ej_tiempo_guardado = RutinaEjercicio.objects.get(rutina=rutina_guardada, ejercicio=self.ejercicio_tiempo)
        self.assertEqual(ej_tiempo_guardado.series_objetivo, 3)
        self.assertEqual(ej_tiempo_guardado.tiempo_objetivo_segundos, 1800)
        self.assertEqual(float(ej_tiempo_guardado.distancia_objetivo_km), 5.5)

    def test_iniciar_rutina_tiempo_en_minutos_para_cardio_y_tiempos_largos(self):
        """Verifica que al empezar una rutina con ejercicios de >= 5 min (como correr o bicicleta) se presenten en minutos"""
        ej_correr = Ejercicio.objects.create(
            nombre='Correr al Aire Libre',
            tipo='OUT',
            modalidad='TIEMPO'
        )
        RutinaEjercicio.objects.create(
            rutina=self.rutina,
            ejercicio=ej_correr,
            orden=3,
            series_objetivo=1,
            tiempo_objetivo_segundos=1800,  # 30 minutos
            distancia_objetivo_km=5.0
        )

        res = self.client.get(reverse('rutinas:iniciar_rutina', args=[self.rutina.id]))
        self.assertEqual(res.status_code, 200)

        # En el contexto JSON enviado a Alpine.js, verificar que el ejercicio de correr tenga tiempo_minutos=30 y unidad_tiempo='min'
        rutina_prep = res.context['rutina_preparada']
        item_correr = next(item for item in rutina_prep if item['ejercicio_id'] == ej_correr.id)
        primera_serie = item_correr['series_sugeridas'][0]

        self.assertEqual(primera_serie['tiempo_minutos'], 30)
        self.assertEqual(primera_serie['tiempo_segundos'], 1800)
        self.assertEqual(primera_serie['unidad_tiempo'], 'min')

    def test_guardar_serie_ajax_tiempo_en_minutos(self):
        """Verifica que guardar_serie_ajax acepte tiempo_minutos y lo convierta a segundos en la BD"""
        payload = {
            'ejercicio_id': self.ejercicio_tiempo.id,
            'numero_serie': 1,
            'repeticiones': None,
            'peso': None,
            'tiempo_minutos': '25',  # 25 minutos
            'tiempo_segundos': None,
            'distancia_km': None,
            'rutina_nombre': 'Entreno Cardio'
        }
        res = self.client.post(
            reverse('rutinas:guardar_serie_ajax'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)

        reg = RegistroEjercicio.objects.filter(usuario=self.user, ejercicio=self.ejercicio_tiempo).first()
        self.assertIsNotNone(reg)
        serie = reg.series_detalle.filter(numero_serie=1).first()
        self.assertIsNotNone(serie)
        self.assertEqual(serie.tiempo_segundos, 1500)  # 25 * 60 = 1500 segundos

    # =========================================================================
    # PRUEBAS DE MODO OFFLINE Y SINCRONIZACIÓN POR LOTE
    # =========================================================================
    def test_sincronizar_series_lote_ajax_exitoso(self):
        """Verifica que sincronizar_series_lote_ajax guarde en un solo lote series de fuerza y tiempo/distancia"""
        payload = {
            'series': [
                {
                    'ejercicio_id': self.ejercicio_peso.id,
                    'numero_serie': 1,
                    'repeticiones': 12,
                    'peso': 75.0,
                    'rutina_nombre': 'Rutina Offline Test'
                },
                {
                    'ejercicio_id': self.ejercicio_peso.id,
                    'numero_serie': 2,
                    'repeticiones': 10,
                    'peso': 80.0,
                    'rutina_nombre': 'Rutina Offline Test'
                },
                {
                    'ejercicio_id': self.ejercicio_tiempo.id,
                    'numero_serie': 1,
                    'tiempo_minutos': 20,
                    'distancia_km': 3.5,
                    'rutina_nombre': 'Rutina Offline Test'
                }
            ]
        }

        response = self.client.post(
            reverse('rutinas:sincronizar_series_lote_ajax'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['guardadas'], 3)
        self.assertEqual(data['total'], 3)

        # Comprobar registros y series creados
        reg_peso = RegistroEjercicio.objects.filter(usuario=self.user, ejercicio=self.ejercicio_peso).first()
        self.assertIsNotNone(reg_peso)
        self.assertEqual(reg_peso.series_detalle.count(), 2)
        s1 = reg_peso.series_detalle.get(numero_serie=1)
        self.assertEqual(s1.repeticiones, 12)
        self.assertEqual(float(s1.peso_kg), 75.0)

        reg_tiempo = RegistroEjercicio.objects.filter(usuario=self.user, ejercicio=self.ejercicio_tiempo).first()
        self.assertIsNotNone(reg_tiempo)
        s_t1 = reg_tiempo.series_detalle.get(numero_serie=1)
        self.assertEqual(s_t1.tiempo_segundos, 1200)  # 20 min * 60
        self.assertEqual(float(s_t1.distancia_km), 3.5)

    def test_sincronizar_series_lote_ajax_actualiza_existente(self):
        """Verifica la idempotencia al sincronizar una serie que ya había sido creada"""
        # Primera sincronización
        payload_1 = {
            'series': [
                {
                    'ejercicio_id': self.ejercicio_peso.id,
                    'numero_serie': 1,
                    'repeticiones': 8,
                    'peso': 60.0
                }
            ]
        }
        res1 = self.client.post(
            reverse('rutinas:sincronizar_series_lote_ajax'),
            data=json.dumps(payload_1),
            content_type='application/json'
        )
        self.assertEqual(res1.status_code, 200)

        # Segunda sincronización con peso corregido en la misma serie
        payload_2 = {
            'series': [
                {
                    'ejercicio_id': self.ejercicio_peso.id,
                    'numero_serie': 1,
                    'repeticiones': 10,
                    'peso': 65.0
                }
            ]
        }
        res2 = self.client.post(
            reverse('rutinas:sincronizar_series_lote_ajax'),
            data=json.dumps(payload_2),
            content_type='application/json'
        )
        self.assertEqual(res2.status_code, 200)

        reg = RegistroEjercicio.objects.get(usuario=self.user, ejercicio=self.ejercicio_peso)
        self.assertEqual(reg.series_detalle.count(), 1)
        serie = reg.series_detalle.first()
        self.assertEqual(serie.repeticiones, 10)
        self.assertEqual(float(serie.peso_kg), 65.0)

    def test_sincronizar_series_lote_ajax_vacio_o_invalido(self):
        """Verifica que una lista vacía o con datos faltantes responda de forma segura sin excepciones 500"""
        # Lista vacía
        res_vacio = self.client.post(
            reverse('rutinas:sincronizar_series_lote_ajax'),
            data=json.dumps({'series': []}),
            content_type='application/json'
        )
        self.assertEqual(res_vacio.status_code, 200)
        self.assertEqual(res_vacio.json()['guardadas'], 0)

        # Ejercicio inexistente y datos corruptos ignorados de forma resiliente
        res_invalido = self.client.post(
            reverse('rutinas:sincronizar_series_lote_ajax'),
            data=json.dumps({'series': [{'ejercicio_id': 99999, 'numero_serie': 1}]}),
            content_type='application/json'
        )
        self.assertEqual(res_invalido.status_code, 200)
        self.assertEqual(res_invalido.json()['guardadas'], 0)


