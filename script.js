// SolarShare Dashboard JavaScript
class SolarShareDashboard {
    constructor() {
        this.websocket = null;
        this.reconnectInterval = null;
        this.lastUpdateTime = null;
        this.chart = null;
        this.householdData = new Map();
        this.activityLog = [];
        this.isConnected = false;
        
        // Animation state
        this.animationQueue = [];
        this.isAnimating = false;
        
        this.init();
    }

    async init() {
        console.log('Initializing SolarShare Dashboard...');
        
        // Initialize UI components
        this.initializeUI();
        this.setupEventListeners();
        
        // Load initial data
        await this.loadInitialData();
        
        // Connect WebSocket
        this.connectWebSocket();
        
        // Initialize chart
        this.initializeChart();
        
        // Start periodic chart data refresh
        setInterval(() => {
            this.refreshChartData();
        }, 30000); // Refresh chart every 30 seconds
        
        // Hide loading overlay
        setTimeout(() => {
            document.getElementById('loadingOverlay').classList.add('hidden');
        }, 1500);
    }

    initializeUI() {
        // Update connection status
        this.updateConnectionStatus(false);
        
        // Initialize last updated time
        this.updateLastUpdatedTime();
        
        // Create initial household grid
        this.renderHouseholdGrid([]);
    }

    setupEventListeners() {
        // Navigation tabs
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                const section = tab.dataset.section;
                this.switchToSection(section);
            });
        });
        
        // Modal close
        document.getElementById('modalClose').addEventListener('click', () => {
            this.closeModal();
        });
        
        // Click outside modal to close
        document.getElementById('householdModal').addEventListener('click', (e) => {
            if (e.target.id === 'householdModal') {
                this.closeModal();
            }
        });
        
        // Escape key to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal();
            }
        });
    }

    async loadInitialData() {
        try {
            // Load initial metrics
            const metricsResponse = await fetch('http://localhost:8000/metrics');
            if (metricsResponse.ok) {
                const metrics = await metricsResponse.json();
                console.log('Loaded initial metrics:', metrics);
                this.updateMetrics(metrics);
            }
            
            // Load history data for chart
            const historyResponse = await fetch('http://localhost:8000/history?range=24h');
            if (historyResponse.ok) {
                const history = await historyResponse.json();
                console.log('Loaded chart data:', history);
                if (history.data && Array.isArray(history.data)) {
                    this.updateChart(history.data);
                } else {
                    console.warn('Invalid chart data format:', history);
                }
            } else {
                console.error('Failed to load history data:', historyResponse.status);
            }
        } catch (error) {
            console.error('Failed to load initial data:', error);
        }
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//localhost:8000/state`;
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.updateConnectionStatus(true);
                
                if (this.reconnectInterval) {
                    clearInterval(this.reconnectInterval);
                    this.reconnectInterval = null;
                }
            };
            
            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleRealtimeData(data);
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket disconnected');
                this.isConnected = false;
                this.updateConnectionStatus(false);
                this.scheduleReconnect();
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.isConnected = false;
                this.updateConnectionStatus(false);
            };
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            this.scheduleReconnect();
        }
    }

    scheduleReconnect() {
        if (this.reconnectInterval) return;
        
        this.reconnectInterval = setInterval(() => {
            console.log('Attempting to reconnect...');
            this.connectWebSocket();
        }, 5000);
    }

    handleRealtimeData(data) {
        console.log('Received real-time data:', data);
        
        // Update timestamp
        this.lastUpdateTime = new Date(data.timestamp);
        this.updateLastUpdatedTime();
        
        // Update simulation time
        if (data.timestamp) {
            this.updateSimulationTime(data.timestamp);
        }
        
        // Update weather
        if (data.weather) {
            this.updateWeather(data.weather);
        }
        
        // Update households
        if (data.households) {
            this.updateHouseholds(data.households);
        }
        
        // Update trades and activity
        if (data.trades) {
            this.updateTrades(data.trades);
        }
        
        // Refresh metrics
        this.refreshMetrics();
    }

    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connectionStatus');
        const statusDot = statusElement.querySelector('.status-dot');
        const statusText = statusElement.querySelector('span');
        
        if (connected) {
            statusElement.className = 'status-indicator connected';
            statusText.textContent = 'Connected';
        } else {
            statusElement.className = 'status-indicator disconnected';
            statusText.textContent = 'Disconnected';
        }
    }

    updateLastUpdatedTime() {
        const element = document.getElementById('lastUpdated');
        if (this.lastUpdateTime) {
            element.textContent = this.lastUpdateTime.toLocaleTimeString();
        } else {
            element.textContent = new Date().toLocaleTimeString();
        }
    }

    updateSimulationTime(timestamp) {
        console.log('DEBUG: Raw timestamp received:', timestamp);
        const simTime = new Date(timestamp);
        console.log('DEBUG: Parsed Date object:', simTime);
        console.log('DEBUG: UTC Hours:', simTime.getUTCHours(), 'UTC Minutes:', simTime.getUTCMinutes());
        console.log('DEBUG: Local Hours:', simTime.getHours(), 'Local Minutes:', simTime.getMinutes());
        
        // Format time in AM/PM format - using UTC to avoid timezone conversion
        const timeOptions = { 
            hour: 'numeric', 
            minute: '2-digit', 
            hour12: true,
            timeZone: 'UTC'  // Force UTC to match simulation time
        };
        const timeString = simTime.toLocaleTimeString('en-US', timeOptions);
        console.log('DEBUG: Formatted time string (UTC):', timeString);
        
        // Format date
        const dateOptions = { 
            month: 'short', 
            day: 'numeric', 
            year: 'numeric' 
        };
        const dateString = simTime.toLocaleDateString('en-US', dateOptions);
        
        // Format full date for weather section
        const fullDateOptions = { 
            month: 'long', 
            day: 'numeric', 
            year: 'numeric' 
        };
        const fullDateString = simTime.toLocaleDateString('en-US', fullDateOptions);
        
        // Update compact weather card
        const simTimeHome = document.getElementById('simTimeHome');
        const simDateHome = document.getElementById('simDateHome');
        const simTimeFull = document.getElementById('simTimeFull');
        const simDateFull = document.getElementById('simDateFull');
        
        if (simTimeHome) {
            simTimeHome.textContent = timeString;
        }
        
        if (simDateHome) {
            simDateHome.textContent = dateString;
        }
        
        // Update full weather section
        if (simTimeFull) {
            simTimeFull.textContent = timeString;
        }
        
        if (simDateFull) {
            simDateFull.textContent = fullDateString;
        }
    }

    updateWeather(weather) {
        // Update temperature - rounded to 2 decimal places
        const temp = parseFloat(weather.temp || 22.5).toFixed(2);
        const solarRad = parseFloat(weather.solar_radiation || 800).toFixed(0);
        const clouds = parseFloat(weather.clouds || 30).toFixed(0);
        const humidity = parseFloat(weather.humidity || 65).toFixed(0);
        
        // Update main weather section
        document.getElementById('temperature').textContent = `${temp}°C`;
        document.getElementById('solarRadiation').textContent = `${solarRad} W/m²`;
        document.getElementById('cloudCover').textContent = `${clouds}%`;
        document.getElementById('humidity').textContent = `${humidity}%`;
        
        // Update compact weather in home section
        document.getElementById('temperatureHome').textContent = `${temp}°C`;
        document.getElementById('solarRadiationHome').textContent = solarRad;
        document.getElementById('cloudCoverHome').textContent = clouds;
        
        // Update weather icon and description
        const cloudsValue = parseFloat(weather.clouds || 30);
        let icon, desc;
        
        if (cloudsValue < 20) {
            icon = '☀️';
            desc = 'Clear';
        } else if (cloudsValue < 60) {
            icon = '🌤️';
            desc = 'Partly Cloudy';
        } else {
            icon = '☁️';
            desc = 'Cloudy';
        }
        
        // Update both weather sections
        document.getElementById('weatherIcon').textContent = icon;
        document.getElementById('weatherIconHome').textContent = icon;
        document.getElementById('weatherDesc').textContent = desc;
        document.getElementById('weatherDescHome').textContent = desc;
    }

    updateHouseholds(households) {
        // Store household data
        households.forEach(household => {
            this.householdData.set(household.id, household);
        });
        
        this.renderHouseholdGrid(households);
        this.updateEnergyFlows(households);
    }

    renderHouseholdGrid(households) {
        const grid = document.getElementById('householdsGrid');
        
        if (households.length === 0) {
            grid.innerHTML = '<div class="no-data">No household data available</div>';
            return;
        }
        
        grid.innerHTML = households.map(household => {
            const batteryColor = this.getBatteryColor(household.battery);
            const netEnergy = (household.solar || 0) - (household.demand || 0);
            
            return `
                <div class="household-item" onclick="dashboard.showHouseholdDetails('${household.id}')">
                    <div class="household-header">
                        <div class="household-id">${household.id}</div>
                        <div class="role-badge ${household.role || 'idle'}">${household.role || 'idle'}</div>
                    </div>
                    
                    <div class="battery-container">
                        <div class="battery-label">
                            <span>Battery</span>
                            <span>${household.battery || 0}%</span>
                        </div>
                        <div class="battery-bar">
                            <div class="battery-fill" style="width: ${household.battery || 0}%; background: ${batteryColor}"></div>
                        </div>
                    </div>
                    
                    <div class="energy-stats">
                        <div class="energy-stat">
                            <div class="energy-stat-label">Solar</div>
                            <div class="energy-stat-value">${(household.solar || 0).toFixed(1)} kW</div>
                        </div>
                        <div class="energy-stat">
                            <div class="energy-stat-label">Demand</div>
                            <div class="energy-stat-value">${(household.demand || 0).toFixed(1)} kW</div>
                        </div>
                        <div class="energy-stat">
                            <div class="energy-stat-label">Net</div>
                            <div class="energy-stat-value ${netEnergy >= 0 ? 'positive' : 'negative'}">${netEnergy.toFixed(1)} kW</div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    getBatteryColor(level) {
        if (level >= 70) return 'linear-gradient(90deg, #38A169, #68D391)';
        if (level >= 30) return 'linear-gradient(90deg, #DD6B20, #F6AD55)';
        return 'linear-gradient(90deg, #E53E3E, #FC8181)';
    }

    updateEnergyFlows(households) {
        const svg = document.getElementById('flowSvg');
        svg.innerHTML = ''; // Clear existing flows - keep SVG empty
    }

    updateTrades(trades) {
        // Add new trades to activity log
        trades.forEach(trade => {
            if (!this.activityLog.find(log => 
                log.seller === trade.seller && 
                log.buyer === trade.buyer && 
                log.timestamp === trade.timestamp
            )) {
                this.activityLog.unshift({
                    type: 'trade',
                    text: `${trade.seller} → ${trade.buyer}: ${trade.kwh} kWh at $${trade.price}/kWh`,
                    timestamp: new Date(trade.timestamp || Date.now()),
                    ...trade
                });
            }
        });
        
        // Keep only last 50 activities
        this.activityLog = this.activityLog.slice(0, 50);
        this.renderActivityFeed();
    }

    renderActivityFeed() {
        const feed = document.getElementById('activityFeed');
        
        if (this.activityLog.length === 0) {
            feed.innerHTML = '<div class="no-activity">No recent activity</div>';
            return;
        }
        
        feed.innerHTML = this.activityLog.map(activity => `
            <div class="activity-item">
                <div class="activity-icon ${activity.type}">
                    ${activity.type === 'trade' ? '⚡' : 'ℹ️'}
                </div>
                <div class="activity-content">
                    <div class="activity-text">${activity.text}</div>
                    <div class="activity-time-stamp">${activity.timestamp.toLocaleTimeString()}</div>
                </div>
            </div>
        `).join('');
    }

    async refreshMetrics() {
        try {
            const response = await fetch('http://localhost:8000/metrics');
            if (response.ok) {
                const metrics = await response.json();
                this.updateMetrics(metrics);
            }
        } catch (error) {
            console.error('Failed to refresh metrics:', error);
        }
    }

    updateMetrics(metrics) {
        console.log('Updating metrics:', metrics);
        
        // Update metric values with animation
        this.animateCounter('energyTraded', parseFloat(metrics.energy_traded || 0), ' kWh');
        this.animateCounter('costSavings', parseFloat(metrics.cost_savings || 0), '', '$');
        this.animateCounter('co2Reduced', parseFloat(metrics.co2_reduced || 0), ' kg');
        this.animateCounter('resilience', parseInt(metrics.resilience || 0), '%');
        
        // Update deltas
        this.updateDelta('energyDelta', metrics.delta_energy || '+0.0');
        this.updateDelta('savingsDelta', metrics.delta_savings || '+0.0', '$');
        this.updateDelta('co2Delta', metrics.delta_co2 || '+0.0');
        this.updateDelta('resilienceDelta', metrics.delta_resilience || '+0');
    }

    animateCounter(elementId, targetValue, suffix = '', prefix = '') {
        const element = document.getElementById(elementId);
        if (!element) {
            console.error(`Element with id '${elementId}' not found`);
            return;
        }
        
        console.log(`Animating ${elementId} to ${targetValue}`);
        
        const currentValue = parseFloat(element.textContent.replace(/[^0-9.-]/g, '')) || 0;
        
        // If values are the same, just update immediately
        if (Math.abs(targetValue - currentValue) < 0.01) {
            element.textContent = prefix + targetValue.toFixed(1) + suffix;
            return;
        }
        
        const increment = (targetValue - currentValue) / 30; // 30 frames
        let currentStep = 0;
        
        const animate = () => {
            if (currentStep < 30) {
                const value = currentValue + (increment * currentStep);
                element.textContent = prefix + value.toFixed(1) + suffix;
                currentStep++;
                requestAnimationFrame(animate);
            } else {
                element.textContent = prefix + targetValue.toFixed(1) + suffix;
            }
        };
        
        animate();
    }

    updateDelta(elementId, deltaValue, prefix = '') {
        const element = document.getElementById(elementId);
        element.textContent = prefix + deltaValue;
        
        // Update class for color
        element.className = 'metric-delta';
        if (deltaValue.startsWith('+') && parseFloat(deltaValue.substring(1)) > 0) {
            element.classList.add('positive');
        } else if (deltaValue.startsWith('-')) {
            element.classList.add('negative');
        }
    }

    initializeChart() {
        const ctx = document.getElementById('metricsChart').getContext('2d');
        
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Energy Traded (kWh)',
                        data: [],
                        borderColor: '#38A169',
                        backgroundColor: 'rgba(56, 161, 105, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Cost Savings ($)',
                        data: [],
                        borderColor: '#3182CE',
                        backgroundColor: 'rgba(49, 130, 206, 0.1)',
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: '#A0AEC0',
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(26, 26, 46, 0.9)',
                        titleColor: '#FFFFFF',
                        bodyColor: '#A0AEC0',
                        borderColor: '#2D3748',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'hour',
                            displayFormats: {
                                hour: 'HH:mm'
                            }
                        },
                        grid: {
                            color: 'rgba(45, 55, 72, 0.5)'
                        },
                        ticks: {
                            color: '#718096'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(45, 55, 72, 0.5)'
                        },
                        ticks: {
                            color: '#718096'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        beginAtZero: true,
                        grid: {
                            drawOnChartArea: false,
                        },
                        ticks: {
                            color: '#718096'
                        }
                    }
                },
                elements: {
                    point: {
                        radius: 3,
                        hoverRadius: 6
                    }
                },
                animation: {
                    duration: 750,
                    easing: 'easeInOutQuart'
                }
            }
        });
    }

    updateChart(data) {
        if (!this.chart) {
            console.error('Chart not initialized');
            return;
        }
        
        if (!data || data.length === 0) {
            console.log('No chart data available');
            return;
        }
        
        console.log('Updating chart with data points:', data.length);
        
        try {
            const labels = data.map(item => new Date(item.timestamp));
            const energyData = data.map(item => parseFloat(item.energy_traded || 0));
            const savingsData = data.map(item => parseFloat(item.cost_savings || 0));
            
            console.log('Chart labels:', labels.length);
            console.log('Energy data range:', Math.min(...energyData), '-', Math.max(...energyData));
            console.log('Savings data range:', Math.min(...savingsData), '-', Math.max(...savingsData));
            
            this.chart.data.labels = labels;
            this.chart.data.datasets[0].data = energyData;
            this.chart.data.datasets[1].data = savingsData;
            
            this.chart.update('active'); // Use active animation for better visual feedback
        } catch (error) {
            console.error('Error updating chart:', error);
        }
    }

    async refreshChartData() {
        try {
            const response = await fetch('http://localhost:8000/history?range=24h');
            if (response.ok) {
                const history = await response.json();
                if (history.data && Array.isArray(history.data)) {
                    this.updateChart(history.data);
                }
            }
        } catch (error) {
            console.error('Failed to refresh chart data:', error);
        }
    }

    async showHouseholdDetails(householdId) {
        try {
            const response = await fetch(`http://localhost:8000/households/${householdId}/details`);
            if (!response.ok) throw new Error('Failed to fetch household details');
            
            const details = await response.json();
            this.renderHouseholdModal(details);
            
        } catch (error) {
            console.error('Error fetching household details:', error);
            this.showErrorModal('Failed to load household details');
        }
    }

    renderHouseholdModal(details) {
        const { household, recent_trades, performance } = details;
        
        document.getElementById('modalTitle').textContent = `${household.id} Details`;
        
        const modalBody = document.getElementById('modalBody');
        modalBody.innerHTML = `
            <div class="household-details">
                <div class="detail-section">
                    <h4>Current Status</h4>
                    <div class="detail-grid">
                        <div class="detail-item">
                            <span class="detail-label">Role</span>
                            <span class="role-badge ${household.current_role}">${household.current_role}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Battery</span>
                            <span class="detail-value">${household.current_battery}%</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Solar Generation</span>
                            <span class="detail-value">${household.solar_generation.toFixed(2)} kW</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Demand</span>
                            <span class="detail-value">${household.demand.toFixed(2)} kW</span>
                        </div>
                    </div>
                </div>
                
                <div class="detail-section">
                    <h4>Specifications</h4>
                    <div class="detail-grid">
                        <div class="detail-item">
                            <span class="detail-label">Solar Capacity</span>
                            <span class="detail-value">${household.solar_capacity} kW</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Battery Size</span>
                            <span class="detail-value">${household.battery_size} kWh</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Orientation</span>
                            <span class="detail-value">${household.orientation}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Type</span>
                            <span class="detail-value">${household.type}</span>
                        </div>
                    </div>
                </div>
                
                <div class="detail-section">
                    <h4>Performance</h4>
                    <div class="performance-metrics">
                        <div class="performance-item">
                            <div class="performance-label">Efficiency</div>
                            <div class="performance-bar">
                                <div class="performance-fill" style="width: ${performance.efficiency}%"></div>
                            </div>
                            <div class="performance-value">${performance.efficiency}%</div>
                        </div>
                        <div class="performance-item">
                            <div class="performance-label">Trading Score</div>
                            <div class="performance-bar">
                                <div class="performance-fill" style="width: ${performance.trading_score}%"></div>
                            </div>
                            <div class="performance-value">${performance.trading_score}%</div>
                        </div>
                        <div class="performance-item">
                            <div class="performance-label">Community Contribution</div>
                            <div class="contribution-badge ${performance.community_contribution}">
                                ${performance.community_contribution.toUpperCase()}
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="detail-section">
                    <h4>Recent Trades</h4>
                    <div class="trades-list">
                        ${recent_trades.length === 0 ? 
                            '<div class="no-trades">No recent trades</div>' :
                            recent_trades.map(trade => `
                                <div class="trade-item">
                                    <div class="trade-type ${trade.type}">${trade.type.toUpperCase()}</div>
                                    <div class="trade-details">
                                        <div class="trade-partner">Partner: ${trade.partner}</div>
                                        <div class="trade-amount">${trade.kwh.toFixed(2)} kWh at $${trade.price.toFixed(3)}/kWh</div>
                                        <div class="trade-time">${new Date(trade.timestamp).toLocaleString()}</div>
                                    </div>
                                </div>
                            `).join('')
                        }
                    </div>
                </div>
            </div>
        `;
        
        document.getElementById('householdModal').classList.add('active');
    }

    showErrorModal(message) {
        document.getElementById('modalTitle').textContent = 'Error';
        document.getElementById('modalBody').innerHTML = `
            <div class="error-message">
                <div class="error-icon">⚠️</div>
                <div class="error-text">${message}</div>
            </div>
        `;
        document.getElementById('householdModal').classList.add('active');
    }

    switchToSection(sectionName) {
        // Remove active class from all tabs and sections
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelectorAll('.section').forEach(section => {
            section.classList.remove('active');
        });
        
        // Add active class to selected tab and section
        document.querySelector(`[data-section="${sectionName}"]`).classList.add('active');
        document.getElementById(`${sectionName}Section`).classList.add('active');
    }
    
    closeModal() {
        document.getElementById('householdModal').classList.remove('active');
    }
}

// Global function for section switching
function switchToSection(sectionName) {
    if (window.dashboard) {
        window.dashboard.switchToSection(sectionName);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new SolarShareDashboard();
});

// Add additional styles for modal content
const additionalStyles = `
<style>
.household-details {
    color: var(--text-primary);
}

.detail-section {
    margin-bottom: var(--spacing-xl);
}

.detail-section h4 {
    color: var(--text-primary);
    margin-bottom: var(--spacing-md);
    font-size: 1.1rem;
    font-weight: 600;
}

.detail-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: var(--spacing-md);
}

.detail-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-sm);
    background: rgba(255, 255, 255, 0.05);
    border-radius: 6px;
}

.detail-label {
    color: var(--text-secondary);
    font-size: 0.875rem;
}

.detail-value {
    color: var(--text-primary);
    font-weight: 500;
}

.performance-metrics {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
}

.performance-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
}

.performance-label {
    min-width: 120px;
    color: var(--text-secondary);
    font-size: 0.875rem;
}

.performance-bar {
    flex: 1;
    height: 8px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
    overflow: hidden;
}

.performance-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--seller-primary), var(--seller-secondary));
    border-radius: 4px;
    transition: width var(--transition-slow);
}

.performance-value {
    min-width: 40px;
    text-align: right;
    color: var(--text-primary);
    font-weight: 500;
}

.contribution-badge {
    padding: var(--spacing-xs) var(--spacing-sm);
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
}

.contribution-badge.high {
    background: rgba(56, 161, 105, 0.2);
    color: var(--seller-secondary);
    border: 1px solid var(--seller-primary);
}

.contribution-badge.medium {
    background: rgba(221, 107, 32, 0.2);
    color: var(--crisis-secondary);
    border: 1px solid var(--crisis-primary);
}

.contribution-badge.low {
    background: rgba(113, 128, 150, 0.2);
    color: var(--text-muted);
    border: 1px solid var(--text-muted);
}

.trades-list {
    max-height: 300px;
    overflow-y: auto;
}

.trade-item {
    display: flex;
    gap: var(--spacing-md);
    padding: var(--spacing-md);
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    margin-bottom: var(--spacing-sm);
}

.trade-type {
    padding: var(--spacing-xs) var(--spacing-sm);
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    text-align: center;
    min-width: 60px;
}

.trade-type.sell {
    background: rgba(56, 161, 105, 0.2);
    color: var(--seller-secondary);
}

.trade-type.buy {
    background: rgba(229, 62, 62, 0.2);
    color: var(--buyer-secondary);
}

.trade-details {
    flex: 1;
}

.trade-partner {
    font-weight: 500;
    color: var(--text-primary);
    margin-bottom: var(--spacing-xs);
}

.trade-amount {
    color: var(--text-secondary);
    font-size: 0.875rem;
    margin-bottom: var(--spacing-xs);
}

.trade-time {
    color: var(--text-muted);
    font-size: 0.75rem;
}

.no-trades {
    text-align: center;
    color: var(--text-muted);
    padding: var(--spacing-xl);
}

.error-message {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-md);
    padding: var(--spacing-xl);
}

.error-icon {
    font-size: 3rem;
}

.error-text {
    color: var(--text-secondary);
    text-align: center;
}

.no-data, .no-activity {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 200px;
    color: var(--text-muted);
    font-style: italic;
}
</style>
`;

// Inject additional styles
document.head.insertAdjacentHTML('beforeend', additionalStyles);