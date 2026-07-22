// Esperar a que todo esté listo
(function() {
    function initialize() {
        if (!window.CONFIG) {
            console.log('- Esperando configuración...');
            setTimeout(initialize, 100);
            return;
        }
        if (!window.CONFIG.MAPBOX_ACCESS_TOKEN || window.CONFIG.MAPBOX_ACCESS_TOKEN === '') {
            console.error('ERROR: MAPBOX_ACCESS_TOKEN no configurado en window.CONFIG');
            console.log('window.CONFIG actual:', window.CONFIG);
            return;
        }
        console.log('Configuración encontrada:', window.CONFIG);
        mapboxgl.accessToken = window.CONFIG.MAPBOX_ACCESS_TOKEN;

        const map = new mapboxgl.Map({
            container: 'map',
            style: 'mapbox://styles/mapbox/streets-v12',
            center: [-16.60, 28.27],
            zoom: 9,
            pitch: 0
        });

        let busManager = null;

        map.on('load', () => {
            console.log('Mapa cargado correctamente');

            // Ajustar límites de Tenerife
            const tenerifeBounds = [
                [-16.95, 27.95],
                [-16.10, 28.60]
            ];

            map.fitBounds(tenerifeBounds, {
                padding: 40,
                duration: 0,
                maxZoom: 12
            });

            if (typeof BusManager !== 'undefined') {
                busManager = new BusManager(map);
            } else {
                console.warn('BusManager no definido');
            }
            if (typeof initFilters !== 'undefined') {
                initFilters(busManager);
            }

            // Conectar WebSocket
            const wsUrl = window.CONFIG.WS_URL || 'ws://localhost:8765';
            if (typeof connectWebSocket !== 'undefined') {
                connectWebSocket(busManager, wsUrl);
            }

            map.addControl(new mapboxgl.NavigationControl(), 'top-right');
        });

        map.on('error', (e) => {
            console.error('Error del mapa:', e);
        });
    }

    // Iniciar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }
})();