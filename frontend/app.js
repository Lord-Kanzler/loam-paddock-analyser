/**
 * Paddock Analyser - Frontend Application
 * 
 * This application handles:
 * 1. File upload to backend API
 * 2. Processing and displaying API responses
 * 3. Interactive table features (sorting, filtering)
 * 4. Map visualization with Leaflet
 * 5. Project and paddock detail views
 * 6. Separate invalid paddocks table
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
    
    // Separate valid projects from invalid paddocks
    const validProjects = data.projects.filter(p => p.project_name !== 'Invalid Paddocks');
    const invalidProjects = data.projects.filter(p => p.project_name === 'Invalid Paddocks');
    
    // Update all components
    updateSummaryCards(data.summary);
    populateProjectsTable(validProjects);
    populateInvalidPaddocksTable(invalidProjects);
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
 * Populate valid projects table with summary data
 */
function populateProjectsTable(projects) {
    const tbody = document.getElementById('projectsBody');
    tbody.innerHTML = '';
    
    // Assign colors to projects
    projects.forEach((project, index) => {
        const projectKey = `${project.owner}::${project.project_name}`;
        state.projectColors[projectKey] = CONFIG.COLORS[index % CONFIG.COLORS.length];
    });
    
    // Create table rows
    projects.forEach(project => {
        const row = createProjectRow(project);
        tbody.appendChild(row);
    });
}

/**
 * Populate invalid paddocks table from ALL owners
 */
function populateInvalidPaddocksTable(invalidProjects) {
    const section = document.getElementById('invalidPaddocksSection');
    const tbody = document.getElementById('invalidPaddocksBody');
    
    // Clear existing rows
    tbody.innerHTML = '';
    
    // Check if there are any invalid projects
    if (!invalidProjects || invalidProjects.length === 0) {
        // No invalid paddocks - hide section
        section.classList.add('hidden');
        return;
    }
    
    // Show section
    section.classList.remove('hidden');
    
    // Assign color for invalid paddocks
    invalidProjects.forEach(invalidProject => {
        const projectKey = `${invalidProject.owner}::Invalid Paddocks`;
        state.projectColors[projectKey] = '#e74c3c'; // Red color
        
        // Create rows for each invalid paddock in this owner's invalid project
        invalidProject.paddocks.forEach(paddock => {
            const row = createInvalidPaddockRow(invalidProject.owner, paddock);
            tbody.appendChild(row);
        });
    });
}

/**
 * Create a single invalid paddock table row
 */
function createInvalidPaddockRow(owner, paddock) {
    const row = document.createElement('tr');
    row.classList.add('invalid-row');
    
    row.innerHTML = `
        <td>${escapeHtml(owner)}</td>
        <td>${escapeHtml(paddock.name)}</td>
        <td>${escapeHtml(paddock.paddock_type)}</td>
        <td class="number">${paddock.area_ha ? paddock.area_ha.toFixed(2) : '-'}</td>
        <td class="number">${paddock.area_ac ? paddock.area_ac.toFixed(2) : '-'}</td>
        <td style="color: var(--color-error);">⚠️ ${escapeHtml(paddock.note || 'No project assigned')}</td>
    `;
    
    return row;
}

/**
 * Create a single project table row
 */
function createProjectRow(project) {
    const row = document.createElement('tr');
    row.onclick = () => showPaddockDetails(project);
    
    const projectKey = `${project.owner}::${project.project_name}`;
    const color = state.projectColors[projectKey];
    const totalCount = project.paddock_count;
    
    row.innerHTML = `
        <td>
            <span class="project-color" style="background-color: ${color}"></span>
            ${escapeHtml(project.owner)}
        </td>
        <td>${escapeHtml(project.project_name)}</td>
        <td class="number">${totalCount}</td>
        <td class="number">${project.area_ha.toFixed(2)}</td>
        <td class="number">${project.area_ac.toFixed(2)}</td>
        <td class="number positive-diff">${project.difference_percent > 0 ? '+' : ''}${project.difference_percent.toFixed(1)}%</td>
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
        `${project.owner} - ${project.project_name} - Individual Paddocks`;
    
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
 * Check if paddock name indicates infrastructure
 */
function isInfrastructure(name) {
    const nameLower = name.toLowerCase();
    return nameLower.includes('shed') || 
           nameLower.includes('house') || 
           nameLower.includes('building');
}

/**
 * Create a single paddock table row
 */
function createPaddockRow(paddock) {
    const row = document.createElement('tr');
    
    // Add class for infrastructure or invalid styling
    if (paddock.note) {
        row.classList.add('invalid-row');
    } else if (isInfrastructure(paddock.name)) {
        row.classList.add('infrastructure-row');
    }
    
    if (paddock.note) {
        // Invalid paddock - show error message
        row.innerHTML = `
            <td>${escapeHtml(paddock.name)}</td>
            <td>${escapeHtml(paddock.paddock_type)}</td>
            <td colspan="3" style="color: var(--color-error);">
                ⚠️ ${escapeHtml(paddock.note)}
            </td>
        `;
    } else {
        // Valid paddock - show area data
        row.innerHTML = `
            <td>${escapeHtml(paddock.name)}</td>
            <td>${escapeHtml(paddock.paddock_type)}</td>
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
    
    // Extract owner and project
    const owner = props.owner || 'Unknown';
    const projectName = props.Project__Name || 
                       props.project_name || 
                       props.project || 
                       'Invalid Paddocks';
    
    const projectKey = `${owner}::${projectName}`;
    const color = state.projectColors[projectKey] || '#95a5a6';
    
    // Check if invalid
    const isInvalid = props.is_invalid === true;
    
    return {
        fillColor: isInvalid ? '#e74c3c' : color,
        weight: 2,
        opacity: 1,
        color: color,
        fillOpacity: isInvalid ? 0.3 : 0.4,
        className: isInvalid ? 'invalid-feature' : ''
    };
}

/**
 * Bind popup to a GeoJSON feature
 */
function bindFeaturePopup(feature, layer) {
    const props = feature.properties;
    
    // Extract data from properties
    const name = props.name || 'Unnamed';
    const owner = props.owner || 'Unknown';
    const project = props.Project__Name || props.project_name || props.project || 'Invalid Paddocks';
    const type = props.paddock_type || 'Unknown';
    const areaHa = props.area_ha ? props.area_ha.toFixed(2) : 'N/A';
    const areaAc = props.area_ac ? props.area_ac.toFixed(2) : 'N/A';
    const diff = props.difference_percent ? props.difference_percent.toFixed(1) : 'N/A';
    const isInvalid = props.is_invalid === true;
    
    // Create popup content
    const popupContent = `
        <strong>${escapeHtml(name)}</strong><br>
        Owner: ${escapeHtml(owner)}<br>
        Project: ${escapeHtml(project)}<br>
        Type: ${escapeHtml(type)}<br>
        ${isInvalid ? '<span style="color: #e74c3c;">⚠️ Invalid (No project assigned)</span><br>' : ''}
        Area: ${areaHa} ha (${areaAc} ac)<br>
        Geodesic vs Planar: +${diff}%
    `;
    
    layer.bindPopup(popupContent);
}

/**
 * Toggle invalid paddock visibility on map
 */
function toggleInvalid() {
    const checkbox = document.getElementById('toggleInvalid');
    const showInvalid = checkbox.checked;
    
    if (!state.geoJsonLayer) return;
    
    // Iterate through all layers
    state.geoJsonLayer.eachLayer((layer) => {
        const props = layer.feature.properties;
        const isInvalid = props.is_invalid === true;
        
        if (isInvalid) {
            if (showInvalid) {
                // Show invalid paddocks
                layer.setStyle({ fillOpacity: 0.3, opacity: 1 });
            } else {
                // Hide invalid paddocks
                layer.setStyle({ fillOpacity: 0, opacity: 0 });
            }
        }
    });
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