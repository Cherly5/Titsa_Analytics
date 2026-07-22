let ws = null;

function connectWebSocket(busManager, wsUrl) {
    const WS_URL = wsUrl || 'ws://localhost:8765';

    ws = new WebSocket(WS_URL);
    ws.onopen = () => {
        console.log('WebSocket conectado');
        document.querySelector('.loading')?.remove();
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            document.getElementById('last-update').textContent =
                new Date().toLocaleTimeString();

            if (Array.isArray(data)) {
                busManager.updateBuses(data);
            } else if (data.buses) {
                busManager.updateBuses(data.buses);
            } else if (data.type === 'connection') {
                console.log('Mensaje del servidor:', data.message);
                if (busManager && typeof data.interpolation_use !== 'undefined') {
                    busManager.interpolationUse = data.interpolation_use;
                }

            } else {
                console.warn('Formato de datos no reconocido:', data);
            }
        } catch (error) {
            console.error('Error procesando mensaje WebSocket:', error);
        }
    };

    ws.onerror = (error) => {
        console.error('Error en WebSocket:', error);
    };

    ws.onclose = () => {
        console.log('WebSocket desconectado, reconectando en 5 segundos...');
        setTimeout(() => connectWebSocket(busManager, wsUrl), 5000);
    };
}