function initFilters(busManager) {
    if (!busManager) {
        return;
    }
    // Checkboxes de estado
    const estados = ['en_transito', 'llegando', 'en_parada', 'desconocido'];
    estados.forEach(est => {
        const el = document.getElementById(`filter-${est}`);
        if (el) {
            el.addEventListener('change', (e) => {
                busManager.setGlobalFilter('estado', e.target.checked, est);
            });
        }
    });

    // Filtros de Movimiento (Select o Radio Buttons)
    const movSelect = document.getElementById('filter-movimiento');
    if (movSelect) {
        movSelect.addEventListener('change', (e) => {
            busManager.setGlobalFilter('movimiento', e.target.value);
        });
    }
    const routeSelect = document.getElementById('filter-route-id');
    if (routeSelect) {
        routeSelect.addEventListener('change', (e) => {
            // Pasar coincidencia exacta para el desplegable
            busManager.setGlobalFilter('routeId', e.target.value);
        });
    }
    const busIdInput = document.getElementById('filter-bus-id');
    if (busIdInput) {
        busIdInput.addEventListener('input', (e) => {
            busManager.setGlobalFilter('busId', e.target.value);
        });
    }
    const speedMinInput = document.getElementById('filter-speed-min');
    if (speedMinInput) {
        speedMinInput.addEventListener('input', (e) => {
            busManager.setGlobalFilter('speedMin', e.target.value);
        });
    }
    const speedMaxInput = document.getElementById('filter-speed-max');
    if (speedMaxInput) {
        speedMaxInput.addEventListener('input', (e) => {
            busManager.setGlobalFilter('speedMax', e.target.value);
        });
    }

    const resetButton = document.getElementById('reset-filters');
    if (resetButton) {
        resetButton.addEventListener('click', () => {
            estados.forEach(est => {
                const checkbox = document.getElementById(`filter-${est}`);
                if (checkbox) {
                    checkbox.checked = true;
                }
                busManager.setGlobalFilter('estado', true, est);
            });

            if (movSelect) {
                movSelect.value = 'todos';
                busManager.setGlobalFilter('movimiento', 'todos');
            }

            if (routeSelect) {
                routeSelect.value = '';
                busManager.setGlobalFilter('routeId', '');
            }

            if (busIdInput) {
                busIdInput.value = '';
                busManager.setGlobalFilter('busId', '');
            }

            if (speedMinInput) {
                speedMinInput.value = '';
                busManager.setGlobalFilter('speedMin', '');
            }

            if (speedMaxInput) {
                speedMaxInput.value = '';
                busManager.setGlobalFilter('speedMax', '');
            }
        });
    }

    setupPopupHandler(busManager);
}

function setupPopupHandler(busManager) {
    const layerIds = ['buses-en_transito', 'buses-llegando', 'buses-en_parada', 'buses-desconocido'];
    const detailsPanel = document.getElementById('bus-details-panel');
    const closeBtn = document.getElementById('close-details');

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            detailsPanel.style.display = 'none';
            busManager.selectedBusId = null; // Deseleccionar en el manager
        });
    }

    layerIds.forEach(layerId => {
        busManager.map.on('click', layerId, (e) => {
            const busData = e.features[0].properties;
            // Guardar el ID de la guagua seleccionada
            busManager.selectedBusId = busData.id;
            detailsPanel.style.display = 'block';
            window.renderBusDetails(busData);
        });

        busManager.map.on('mouseenter', layerId, () => busManager.map.getCanvas().style.cursor = 'pointer');
        busManager.map.on('mouseleave', layerId, () => busManager.map.getCanvas().style.cursor = '');
    });
}

// Función global para actualizar el contenido html
window.renderBusDetails = function(busData) {
    const content = document.getElementById('bus-details-content');
    if (!content) return;

    const speed = Number(busData.velocidad) || 0;
    const isMoving = speed > 0.5 ? 'En marcha' : 'Detenida';

    content.innerHTML = `
        <p><strong>Línea:</strong> ${busData.linea || 'N/D'}</p>
        <p><strong>ID:</strong> ${busData.id || 'N/D'}</p>
        <p><strong>Estado:</strong> ${getEstadoTexto(busData.estado)}</p>
        <p><strong>Velocidad:</strong> ${speed.toFixed(1)} km/h</p>
        <p><strong>Movimiento:</strong> ${isMoving}</p>
        <p><strong>Próxima parada:</strong> ${busData.proxima_parada || 'N/D'}</p>
        <p><strong>Secuencia:</strong> ${busData.numero_parada || 'N/D'}</p>
    `;
};

function getEstadoTexto(estado) {
    const config = {
        en_transito: { bg: 'rgba(52, 211, 153, 0.2)', color: '#34D399', text: 'En tránsito' },
        llegando: { bg: 'rgba(251, 191, 36, 0.2)', color: '#FBBF24', text: 'Llegando' },
        en_parada: { bg: 'rgba(59, 130, 246, 0.2)', color: '#3B82F6', text: 'En parada' },
        desconocido: { bg: 'rgba(148, 163, 184, 0.2)', color: '#94A3B8', text: 'Desconocido' }
    };

    const c = config[estado] || config['desconocido'];

    return `<span style="background-color: ${c.bg}; color: ${c.color}; padding: 3px 10px; border-radius: 12px; font-size: 0.9em; font-weight: 600; display: inline-block; border: 1px solid ${c.bg};">${c.text}</span>`;
}
