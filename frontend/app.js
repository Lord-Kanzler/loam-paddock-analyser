/**
 * Paddock Analyser - Frontend Application
 * 
 * This application handles:
 * 1. File upload to backend API
 * 2. Processing and displaying API responses
 * 3. Interactive table features (sorting, filtering)
 * 4. Map visualization with Leaflet
 * 5. Project and paddock detail views
 * 
 * Dependencies:
 * - Leaflet.js for map functionality
 * - Backend API running on localhost:8000
 */

'use strict';

// ============================================================================
// Configuration
// ============================================================================

const CONFIG = {
    API_BASE_URL: 'http://localhost:8000',
    API_ENDPOINTS: {
        upload: '/api/upload',
        health: '/api/health'
    },
    MAP: {
        tileLayer: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
        defaultPadding: [20, 20]
    },
    COLORS: [
        '#3498db', '#e67e22', '#27ae60', '#9b59b6',
        '#e74c3c', '#16a085', '#f39c12', '#2c3e50',
        '#c0392b', '#8e44ad', '#d35400', '#1abc9c'
    ]
};

// ============================================================================
// Global State
// ============================================================================

const state = {
    projectData: null,
    map: null,
    geoJsonLayer: null,
    sortState: {},
    projectColors: {}
};

// ============================================================================
// Initialization
// ============================================================================

/**
 * Check if backend API is available on page load
 */
async function checkBackendHealth() {
    try {
        const url = `${CONFIG.API_BASE_URL}${CONFIG.API_ENDPOINTS.health}`;
        const response = await fetch(url);
        
        if (!response.ok) {
            showError('Backend API is not responding. Please start the FastAPI server.');
        }
    } catch (error) {
        showError('Cannot connect to backend API. Please run: cd backend && pipenv run uvicorn app.main:app --reload');
        console.error('Backend health check failed:', error);
    }
}

// Run health check when page loads
document.addEventListener('DOMContentLoaded', checkBackendHealth);

// ============================================================================
// File Upload and Processing
// ============================================================================

/**
 * Handle file upload and trigger analysis
 */
async function uploadFile() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        showError('Please select a GeoJSON file to analyze');
        return;
    }
    
    // Validate file extension
    const fileName = file.name.toLowerCase();
    if (!fileName.endsWith('.geojson') && !fileName.endsWith('.json')) {
        showError('Please select a valid GeoJSON file (.geojson or .json)');
        return;
    }
    
    // Show loading state
    setLoadingState(true);
    hideError();
    
    // Prepare form data
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const url = `${CONFIG.API_BASE_URL}${CONFIG.API_ENDPOINTS.upload}`;
        const response = await fetch(url, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Upload failed');
        }
        
        const data = await response.json();
        state.projectData = data;
        
        // Display results
        displayResults(data);
        
    } catch (error) {
        showError(`Error: ${error.message}`);
        console.error('Upload error:', error);
    } finally {
        setLoadingState(false);
    }
}

/**
 * Set loading state for upload button and loading indicator
 */
function setLoadingState(isLoading) {
    const loadingDiv = document.getElementById('loading');
    const uploadBtn = document.getElementById('uploadBtn');
    
    if (isLoading) {
        loadingDiv.classList.remove('hidden');
        uploadBtn.disabled = true;
    } else {
        loadingDiv.classList.add('hidden');
        uploadBtn.disabled = false;
    }
}

// ============================================================================
// UI Display Functions
// ============================================================================

/**
 * Display all results: summary cards, table, and map
 */
function displayResults(data) {
    // Show results section
    document.getElementById('results').classList.remove('hidden');
    
    // Update all components
    updateSummaryCards(data.summary);
    populateProjectsTable(data.projects);
    initializeMap(data.normalized_geojson, data.projects);
    
    // Scroll to results
    document.getElementById('results').scrollIntoView({ 
        behavior: 'smooth',
        block: 'start'
    });
}

/**
 * Update summary statistics cards
 */
function updateSummaryCards(summary) {
    // Calculate areas
    const totalHectares = summary.total_area_geodesic_m2 / 10000;
    const totalAcres = summary.total_area_geodesic_m2 * 0.000247105;
    
    // Update card values
    document.getElementById('totalArea').textContent = `${totalHectares.toFixed(1)} ha`;
    document.getElementById('totalAreaAc').textContent = `${totalAcres.toFixed(1)} acres`;
    document.getElementById('totalProjects').textContent = summary.total_projects;
    document.getElementById('totalPaddocks').textContent = summary.total_paddocks;
    
    // Format valid/invalid count
    const validCount = summary.total_paddocks - summary.invalid_paddocks;
    const validInvalidText = summary.invalid_paddocks > 0 
        ? `${validCount} valid, ${summary.invalid_paddocks} invalid`
        : 'All valid';
    document.getElementById('validInvalidCount').textContent = validInvalidText;
    
    // Display geodesic accuracy gain
    document.getElementById('accuracyGain').textContent = 
        `+${summary.total_difference_percent.toFixed(1)}%`;
}

/**
 * Populate projects table with summary data
 */
function populateProjectsTable(projects) {
    const tbody = document.getElementById('projectsBody');
    tbody.innerHTML = '';
    
    // Assign colors to projects
    projects.forEach((project, index) => {
        state.projectColors[project.project_name] = CONFIG.COLORS[index % CONFIG.COLORS.length];
    });
    
    // Create table rows
    projects.forEach(project => {
        const row = createProjectRow(project);
        tbody.appendChild(row);
    });
}

/**
 * Create a single project table row
 */
function createProjectRow(project) {
    const row = document.createElement('tr');
    row.onclick = () => showPaddockDetails(project);
    
    const color = state.projectColors[project.project_name];
    const validCount = project.valid_paddocks;
    const totalCount = project.paddock_count;
    
    row.innerHTML = `
        <td>
            <span class="project-color" style="background-color: ${color}"></span>
            ${escapeHtml(project.project_name)}
        </td>
        <td class="number">${totalCount} (${validCount} valid)</td>
        <td class="number">${project.area_ha.toFixed(2)}</td>
        <td class="number">${project.area_ac.toFixed(2)}</td>
        <td class="number positive-diff">+${project.difference_percent.toFixed(1)}%</td>
    `;
    
    return row;
}

/**
 * Display detailed paddock information for a project
 */
function showPaddockDetails(project) {
    const detailsDiv = document.getElementById('paddockDetails');
    const paddocksBody = document.getElementById('paddocksBody');
    
    // Update section title
    document.getElementById('selectedProjectName').textContent = 
        `${project.project_name} - Individual Paddocks`;
    
    // Clear existing rows
    paddocksBody.innerHTML = '';
    
    // Create rows for each paddock
    project.paddocks.forEach(paddock => {
        const row = createPaddockRow(paddock);
        paddocksBody.appendChild(row);
    });
    
    // Show details section
    detailsDiv.classList.remove('hidden');
    
    // Scroll to details
    detailsDiv.scrollIntoView({ behavior: 'smooth' });
}

/**
 * Create a single paddock table row
 */
function createPaddockRow(paddock) {
    const row = document.createElement('tr');
    
    if (paddock.note) {
        // Invalid paddock - show error message
        row.innerHTML = `
            <td>${escapeHtml(paddock.name)}</td>
            <td colspan="3" style="color: var(--color-error);">
                Invalid: ${escapeHtml(paddock.note)}
            </td>
        `;
    } else {
        // Valid paddock - show area data
        row.innerHTML = `
            <td>${escapeHtml(paddock.name)}</td>
            <td class="number">${paddock.area_ha.toFixed(2)}</td>
            <td class="number">${paddock.area_ac.toFixed(2)}</td>
            <td class="number positive-diff">+${paddock.difference_percent.toFixed(1)}%</td>
        `;
    }
    
    return row;
}

/**
 * Close paddock details section
 */
function closePaddockDetails() {
    document.getElementById('paddockDetails').classList.add('hidden');
}

// ============================================================================
// Table Interaction Functions
// ============================================================================

/**
 * Filter table rows based on search input
 */
function filterTable() {
    const searchTerm = document.getElementById('searchBox').value.toLowerCase();
    const rows = document.querySelectorAll('#projectsTable tbody tr');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchTerm) ? '' : 'none';
    });
}

/**
 * Sort table by column index
 */
function sortTable(columnIndex) {
    const table = document.getElementById('projectsTable');
    const tbody = table.tBodies[0];
    const rows = Array.from(tbody.rows);
    
    // Toggle sort direction for this column
    state.sortState[columnIndex] = !state.sortState[columnIndex];
    const ascending = state.sortState[columnIndex];
    
    // Sort rows
    rows.sort((rowA, rowB) => {
        return compareCells(rowA.cells[columnIndex], rowB.cells[columnIndex], ascending);
    });
    
    // Re-append rows in sorted order
    rows.forEach(row => tbody.appendChild(row));
}

/**
 * Compare two table cells for sorting
 */
function compareCells(cellA, cellB, ascending) {
    const textA = cellA.textContent.trim();
    const textB = cellB.textContent.trim();
    
    // Try to parse as numbers
    const numA = parseFloat(textA.replace(/[^0-9.-]/g, ''));
    const numB = parseFloat(textB.replace(/[^0-9.-]/g, ''));
    
    if (!isNaN(numA) && !isNaN(numB)) {
        // Numeric comparison
        return ascending ? numA - numB : numB - numA;
    }
    
    // String comparison
    return ascending 
        ? textA.localeCompare(textB)
        : textB.localeCompare(textA);
}

// ============================================================================
// Map Functionality
// ============================================================================

/**
 * Initialize or update Leaflet map with GeoJSON data
 */
function initializeMap(geojson, projects) {
    // Create map if it doesn't exist
    if (!state.map) {
        state.map = L.map('map');
        
        // Add tile layer
        L.tileLayer(CONFIG.MAP.tileLayer, {
            attribution: CONFIG.MAP.attribution,
            maxZoom: CONFIG.MAP.maxZoom
        }).addTo(state.map);
    }
    
    // Remove existing GeoJSON layer if present
    if (state.geoJsonLayer) {
        state.map.removeLayer(state.geoJsonLayer);
    }
    
    // Add new GeoJSON layer
    state.geoJsonLayer = createGeoJsonLayer(geojson);
    state.geoJsonLayer.addTo(state.map);
    
    // Fit map bounds to show all features
    const bounds = state.geoJsonLayer.getBounds();
    state.map.fitBounds(bounds, { padding: CONFIG.MAP.defaultPadding });
}

/**
 * Create styled GeoJSON layer
 */
function createGeoJsonLayer(geojson) {
    return L.geoJSON(geojson, {
        style: getFeatureStyle,
        onEachFeature: bindFeaturePopup
    });
}

/**
 * Get style for a GeoJSON feature
 */
function getFeatureStyle(feature) {
    const props = feature.properties;
    
    // Extract project name from various possible field names
    const projectName = props.Project__Name || 
                       props.project_name || 
                       props.project || 
                       'Unknown';
    
    // Get color for this project
    const color = state.projectColors[projectName] || '#95a5a6';
    
    return {
        fillColor: color,
        weight: 2,
        opacity: 1,
        color: color,
        fillOpacity: 0.4
    };
}

/**
 * Bind popup to a GeoJSON feature
 */
function bindFeaturePopup(feature, layer) {
    const props = feature.properties;
    
    // Extract data from properties
    const name = props.name || 'Unnamed';
    const project = props.Project__Name || props.project_name || props.project || 'Unknown';
    const areaHa = props.area_ha ? props.area_ha.toFixed(2) : 'N/A';
    const areaAc = props.area_ac ? props.area_ac.toFixed(2) : 'N/A';
    const diff = props.difference_percent ? props.difference_percent.toFixed(1) : 'N/A';
    
    // Create popup content
    const popupContent = `
        <strong>${escapeHtml(name)}</strong><br>
        Project: ${escapeHtml(project)}<br>
        Area: ${areaHa} ha (${areaAc} ac)<br>
        Geodesic vs Planar: +${diff}%
    `;
    
    layer.bindPopup(popupContent);
}

// ============================================================================
// Error Handling
// ============================================================================

/**
 * Display error message
 */
function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
}

/**
 * Hide error message
 */
function hideError() {
    const errorDiv = document.getElementById('error');
    errorDiv.classList.add('hidden');
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Escape HTML to prevent XSS attacks
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}