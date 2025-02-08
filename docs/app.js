// Map initialization
let map = null;
let markers = null;
let currentCountry = null;

/**
 * Initialize the map and base layer
 */
function initializeMap() {
    // Create the map centered on [0, 0]
    map = L.map('map').setView([0, 0], 2);

    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);

    // Initialize marker cluster group
    markers = L.markerClusterGroup();
    map.addLayer(markers);
}

/**
 * Load and populate the countries dropdown
 */
async function loadCountries() {
    try {
        const response = await fetch('../data/countries.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const countries = await response.json();

        const select = document.getElementById('countrySelect');
        select.innerHTML = '<option value="">Select a country</option>';

        // Sort countries by name
        countries.sort((a, b) => a.name.localeCompare(b.name));

        countries.forEach(country => {
            const option = document.createElement('option');
            option.value = country.code.toLowerCase();  // Important: lowercase for directory matching
            option.textContent = `${country.name} (${country.airport_count} airports)`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading countries:', error);
        showError('Failed to load countries list. Please make sure the data is properly generated.');
    }
}

/**
 * Load and display airports for a selected country
 * @param {string} countryCode - The ISO country code
 */
async function loadAirports(countryCode) {
    try {
        // Clear existing markers
        markers.clearLayers();

        // Show loading indicator
        showLoading(true);

        const response = await fetch(`../data/${countryCode}/airports.json`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        const bounds = [];

        // Add markers for each airport
        data.airports.forEach(airport => {
            if (!airport.coordinates) return;

            const [lat, lon] = airport.coordinates.split(',').map(coord => parseFloat(coord.trim()));

            if (!isNaN(lat) && !isNaN(lon)) {
                bounds.push([lat, lon]);

                const marker = L.marker([lat, lon])
                    .bindPopup(createPopupContent(airport));

                markers.addLayer(marker);
            }
        });

        // Fit map to show all markers
        if (bounds.length > 0) {
            map.fitBounds(bounds);
        }

        // Update statistics
        updateStatistics(data);

    } catch (error) {
        console.error('Error loading airports:', error);
        showError('Failed to load airport data. Please try again.');
    } finally {
        showLoading(false);
    }
}

/**
 * Create popup content for an airport marker
 * @param {Object} airport - Airport data object
 * @returns {string} HTML content for the popup
 */
function createPopupContent(airport) {
    const details = [
        ['Type', airport.type],
        ['IATA', airport.iata_code],
        ['GPS', airport.gps_code],
        ['Local Code', airport.local_code],
        ['Elevation', airport.elevation_ft ? `${airport.elevation_ft} ft` : 'N/A'],
        ['Municipality', airport.municipality],
        ['Region', airport.iso_region]
    ];

    const detailsHtml = details
        .filter(([_, value]) => value)
        .map(([label, value]) => `<p><strong>${label}:</strong> ${value}</p>`)
        .join('');

    return `
        <div class="airport-popup">
            <h3>${airport.name}</h3>
            ${detailsHtml}
        </div>
    `;
}

/**
 * Update statistics display
 * @param {Object} data - Country airport data
 */
function updateStatistics(data) {
    const stats = document.getElementById('statistics');

    const formatType = (type) => {
        return type
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    };

    const typesHtml = Object.entries(data.types_distribution || {})
        .sort((a, b) => b[1] - a[1])
        .map(([type, count]) =>
            `<li>${formatType(type)}: <strong>${count}</strong> (${(count/data.total_airports*100).toFixed(1)}%)</li>`
        )
        .join('');

    stats.innerHTML = `
        <h3>Statistics for ${data.country_name}</h3>
        <p>Total airports: <strong>${data.total_airports}</strong></p>
        <h4>By type:</h4>
        <ul class="types-list">${typesHtml}</ul>
        <p class="text-sm">Last updated: ${new Date(data.last_updated).toLocaleString()}</p>
    `;
}

/**
 * Show/hide loading indicator
 * @param {boolean} show - Whether to show or hide the loading indicator
 */
function showLoading(show) {
    const loader = document.getElementById('loader');
    loader.style.display = show ? 'block' : 'none';
}

/**
 * Show error message
 * @param {string} message - Error message to display
 */
function showError(message) {
    const error = document.getElementById('error');
    error.textContent = message;
    error.style.display = 'block';
    setTimeout(() => {
        error.style.display = 'none';
    }, 5000);
}

// Initialize when document is loaded
document.addEventListener('DOMContentLoaded', () => {
    initializeMap();
    loadCountries();

    // Add event listener for country selection
    document.getElementById('countrySelect').addEventListener('change', (e) => {
        if (e.target.value) {
            currentCountry = e.target.value;
            loadAirports(currentCountry);
        }
    });
});