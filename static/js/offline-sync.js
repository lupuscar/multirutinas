/**
 * OPTIFIT — Motor de Sincronización Local y Modo Offline (Offline-First)
 * Permite registrar series y entrenamientos en el gimnasio sin cobertura
 * y los sincroniza automáticamente en segundo plano al recuperar la conexión.
 */

(function (window) {
    'use strict';

    const STORAGE_KEY = 'optifit_offline_series_queue';
    const DEFAULT_SYNC_URL = '/rutinas/serie/sincronizar-lote/';
    let isSyncing = false;

    const OptiFitOffline = {
        /**
         * Obtiene la lista actual de series pendientes en la cola local
         */
        getQueue: function () {
            try {
                const raw = localStorage.getItem(STORAGE_KEY);
                return raw ? JSON.parse(raw) : [];
            } catch (e) {
                console.error('Error al leer cola offline:', e);
                return [];
            }
        },

        /**
         * Guarda la lista de series en el almacenamiento local
         */
        saveQueue: function (queue) {
            try {
                localStorage.setItem(STORAGE_KEY, JSON.stringify(queue));
                window.dispatchEvent(new CustomEvent('optifit-queue-updated', {
                    detail: { count: queue.length }
                }));
            } catch (e) {
                console.error('Error al guardar en cola offline:', e);
            }
        },

        /**
         * Devuelve el número de series pendientes de sincronizar
         */
        getPendingCount: function () {
            return this.getQueue().length;
        },

        /**
         * Añade o actualiza una serie en la cola local
         */
        enqueueSerie: function (seriePayload) {
            const queue = this.getQueue();
            const id = 'serie_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);

            // Si ya existe una serie pendiente para el mismo ejercicio y número de serie, la actualizamos
            const existingIndex = queue.findIndex(function (item) {
                return String(item.ejercicio_id) === String(seriePayload.ejercicio_id) &&
                       parseInt(item.numero_serie) === parseInt(seriePayload.numero_serie);
            });

            const enrichedPayload = Object.assign({}, seriePayload, {
                offline_id: id,
                queued_at: new Date().toISOString()
            });

            if (existingIndex >= 0) {
                queue[existingIndex] = enrichedPayload;
            } else {
                queue.push(enrichedPayload);
            }

            this.saveQueue(queue);
            return enrichedPayload;
        },

        /**
         * Limpia toda la cola de series pendientes
         */
        clearQueue: function () {
            try {
                localStorage.removeItem(STORAGE_KEY);
                window.dispatchEvent(new CustomEvent('optifit-queue-updated', {
                    detail: { count: 0 }
                }));
            } catch (e) {
                console.error('Error al limpiar cola offline:', e);
            }
        },

        /**
         * Sincroniza todas las series pendientes enviándolas en un solo lote al servidor
         */
        syncAll: async function (csrfToken, syncUrl) {
            if (!navigator.onLine || isSyncing) {
                return { synced: false, reason: !navigator.onLine ? 'offline' : 'in_progress' };
            }

            const queue = this.getQueue();
            if (queue.length === 0) {
                return { synced: true, count: 0 };
            }

            isSyncing = true;
            const endpoint = syncUrl || DEFAULT_SYNC_URL;
            const token = csrfToken || this.getCSRFToken();

            try {
                window.dispatchEvent(new CustomEvent('optifit-sync-started', {
                    detail: { count: queue.length }
                }));

                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': token,
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({ series: queue })
                });

                if (!response.ok) {
                    throw new Error('Servidor devolvió código HTTP ' + response.status);
                }

                const data = await response.json();
                if (data.status === 'success') {
                    const syncedCount = data.synced_count || queue.length;
                    this.clearQueue();

                    window.dispatchEvent(new CustomEvent('optifit-sync-completed', {
                        detail: { count: syncedCount, message: data.message }
                    }));

                    return { synced: true, count: syncedCount };
                } else {
                    throw new Error(data.message || 'Error en respuesta de sincronización');
                }
            } catch (err) {
                console.warn('Fallo temporal al sincronizar lote offline:', err);
                window.dispatchEvent(new CustomEvent('optifit-sync-failed', {
                    detail: { error: err.message, pending: queue.length }
                }));
                return { synced: false, error: err.message };
            } finally {
                isSyncing = false;
            }
        },

        /**
         * Obtiene el token CSRF desde cookies o del DOM si no se pasó explícitamente
         */
        getCSRFToken: function () {
            const match = document.cookie.match(/(^|; )csrftoken=([^;]+)/);
            if (match) return match[2];
            const meta = document.querySelector('[name=csrfmiddlewaretoken]');
            return meta ? meta.value : '';
        }
    };

    // Escuchar evento nativo de reconexión a internet
    window.addEventListener('online', function () {
        console.log('⚡ Conexión recuperada: iniciando sincronización automática offline...');
        setTimeout(function () {
            OptiFitOffline.syncAll();
        }, 1200); // 1.2s de cortesía para estabilizar la conexión
    });

    // Verificación periódica en segundo plano cada 30 segundos si hay elementos pendientes
    setInterval(function () {
        if (navigator.onLine && OptiFitOffline.getPendingCount() > 0 && !isSyncing) {
            OptiFitOffline.syncAll();
        }
    }, 30000);

    // Exponer globalmente
    window.OptiFitOffline = OptiFitOffline;

})(window);
