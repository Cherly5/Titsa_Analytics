class BusManager {
    constructor(map) {
        this.map = map;
        this.buses = new Map();
        this.previousPositions = new Map();
        this.animationFrame = null;
        this.interpolationUse = true;
        this.selectedBusId = null;
        this.filters = {
            estados: { en_transito: true, llegando: true, en_parada: true, desconocido: true},
            movimiento: 'todos',
            routeId: '',
            busId: '',
            speedMin: null,
            speedMax: null
        };
        this.setupLayers();
        this.startAnimationLoop();
    }

    setupLayers() {
        this.map.addSource('buses', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] }
        });
        this.loadCustomIcon();

        const estados = [
            { id: 'en_transito', color: '#34D399' },
            { id: 'llegando', color: '#FBBF24' },
            { id: 'en_parada', color: '#3B82F6' },
            { id: 'desconocido', color: '#94A3B8' }
        ];

        estados.forEach(est => {
            this.map.addLayer({
                id: `buses-${est.id}`,
                type: 'symbol',
                source: 'buses',
                filter: ['==', ['get', 'estado'], est.id],
                layout: {
                    'icon-image': 'bus-marker-modern',
                    'icon-size': 0.72,
                    'icon-allow-overlap': false,
                    'text-allow-overlap': false,
                    'icon-optional': false,
                    'text-optional': false,
                    'icon-rotate': ['get', 'heading'],
                    'icon-rotation-alignment': 'map',
                    'text-field': ['get', 'linea'],
                    'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
                    'text-size': 10.5,
                    'text-offset': [0, 1.65],
                    'text-anchor': 'top',
                },
                paint: {
                    'icon-color': est.color,
                    'text-color': '#0F172A',
                    'text-halo-color': 'rgba(255,255,255,0.95)',
                    'text-halo-width': 1.5
                }
            });
        });
    }

    loadCustomIcon() {
        if (this.map.hasImage('bus-marker-modern')) return;
        this.map.loadImage('resources/arrow_icon.png', (error, image) => {
            if (error) throw error;
            this.map.addImage('bus-marker-modern', image, { sdf: true });
        });
    }

    updateBuses(busesData) {
        const now = Date.now();
        busesData.forEach(bus => {
            if (this.buses.has(bus.id)) {
                this.previousPositions.set(bus.id, {
                    ...this.buses.get(bus.id),
                    localTimestamp: now
                });
            }
            this.buses.set(bus.id, { ...bus, localTimestamp: now });
        });
        this.updateRouteDropdown();
    }

    updateMapVisuals() {
        const features = [];
        const now = Date.now();
        const STALE_TIMEOUT = 15 * 60 * 1000; // 15 minutos en milisegundos

        this.buses.forEach((bus, id) => {
            // Si la guagua no ha enviado datos en 15 min, se borra del mapa
            if (now - bus.localTimestamp > STALE_TIMEOUT) {
                this.buses.delete(id);
                this.previousPositions.delete(id);
                return; // se salta a la siguiente guagua sin procesar esta
            }

            const previous = this.previousPositions.get(id);
            let heading = bus.heading || 0;
            let currentLng = bus.lng;
            let currentLat = bus.lat;

            if (previous && this.interpolationUse) {
                const duration = 32000;
                const elapsedTime = now - bus.localTimestamp;
                if (elapsedTime < duration) {
                    const interpolationFactor = elapsedTime / duration;
                    currentLng = previous.lng + ((bus.lng - previous.lng) * interpolationFactor);
                    currentLat = previous.lat + ((bus.lat - previous.lat) * interpolationFactor);
                }
            }

            const interpolatedBus = {
                ...bus,
                heading,
                lat: currentLat,
                lng: currentLng
            };

            if (!this.passesGlobalFilters(interpolatedBus)) {
                return;
            }

            features.push({
                type: 'Feature',
                geometry: { type: 'Point', coordinates: [currentLng, currentLat] },
                properties: interpolatedBus
            });
        });

        const source = this.map.getSource('buses');
        if (source) {
            source.setData({ type: 'FeatureCollection', features: features });
        }

        const counter = document.getElementById('bus-count');
        if (counter) {
            counter.textContent = features.length;
        }

        const totalCounter = document.getElementById('bus-total-count');
        if (totalCounter) {
            totalCounter.textContent = this.buses.size;
        }
        if (this.selectedBusId && window.renderBusDetails) {
            const selectedBus = this.buses.get(this.selectedBusId);
            if (selectedBus) {
                window.renderBusDetails(selectedBus);
            } else {
                const panel = document.getElementById('bus-details-panel');
                if (panel) panel.style.display = 'none';
            }
        }
    }

    startAnimationLoop() {
        const animate = () => {
            this.updateMapVisuals();
            this.animationFrame = requestAnimationFrame(animate);
        };
        animate();
    }

    setGlobalFilter(type, value, subvalue = null) {
        if (type === 'estado') {
            this.filters.estados[subvalue] = value;
        } else if (type === 'movimiento') {
            this.filters.movimiento = value;
        } else if (type === 'routeId') {
            this.filters.routeId = (value || '').trim().toUpperCase();
        } else if (type === 'busId') {
            this.filters.busId = (value || '').trim().toUpperCase();
        } else if (type === 'speedMin') {
            this.filters.speedMin = this.normalizeNumericFilter(value);
        } else if (type === 'speedMax') {
            this.filters.speedMax = this.normalizeNumericFilter(value);
        }
        this.applyFilters();
    }

    normalizeNumericFilter(value) {
        if (value === '' || value === null || value === undefined) {
            return null;
        }
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) {
            return null;
        }
        return Math.max(0, numeric);
    }

    passesGlobalFilters(bus) {
        const estado = bus.estado || 'desconocido';
        if (!this.filters.estados[estado]) {
            return false;
        }

        const speed = Number(bus.velocidad) || 0;
        if (this.filters.movimiento === 'movimiento' && speed <= 0.5) {
            return false;
        }
        if (this.filters.movimiento === 'parado' && speed > 0.5) {
            return false;
        }
        if (this.filters.speedMin !== null && speed < this.filters.speedMin) {
            return false;
        }
        if (this.filters.speedMax !== null && speed > this.filters.speedMax) {
            return false;
        }

        const routeId = String(bus.linea || '').toUpperCase();
        if (this.filters.routeId && routeId !== this.filters.routeId) {
            return false;
        }

        const busId = String(bus.id || '').toUpperCase();
        if (this.filters.busId && !busId.includes(this.filters.busId)) {
            return false;
        }

        return true;
    }

    applyFilters() {
        this.updateMapVisuals();
    }
    updateRouteDropdown() {
        const select = document.getElementById('filter-route-id');
        if (!select) return;

        const currentSelection = select.value;
        const routes = new Set();

        // Recopilar todas las líneas de las guaguas activas
        this.buses.forEach(bus => {
            if (bus.linea && bus.linea !== 'N/A') {
                routes.add(bus.linea);
            }
        });

        // Ordenar las líneas alfanuméricamente
        const sortedRoutes = Array.from(routes).sort((a, b) =>
            a.localeCompare(b, undefined, {numeric: true, sensitivity: 'base'})
        );

        // Generar el HTML solo si hay cambios para evitar parpadeos en el DOM
        let html = '<option value="">Todas las rutas</option>';
        sortedRoutes.forEach(r => {
            const selected = r === currentSelection ? 'selected' : '';
            html += `<option value="${r}" ${selected}>Línea ${r}</option>`;
        });

        if (select.innerHTML !== html) {
            select.innerHTML = html;
        }
    }
}
