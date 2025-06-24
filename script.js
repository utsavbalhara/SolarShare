// SolarShare Dashboard JavaScript
class SolarShareDashboard {
    constructor() {
        this.websocket = null;
        this.reconnectInterval = null;
        this.lastUpdateTime = null;
        this.chart = null;
        this.solarRadiationChart = null;
        this.temperatureChart = null;
        this.weatherData = [];
        this.householdData = new Map();
        this.activityLog = [];
        this.isConnected = false;
        
        // Animation state
        this.animationQueue = [];
        this.isAnimating = false;
        
        this.themeToggle = null;
        
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
        
        // Initialize charts
        this.initializeChart();
        this.initializeWeatherCharts();
        
        // Load initial weather data for charts
        this.loadInitialWeatherData();
        
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

        // Theme switcher
        this.themeToggle = document.getElementById('themeToggle');
        this.themeToggle.addEventListener('change', () => this.toggleTheme());
        this.applyInitialTheme();

        // Simulation control toggles
        document.getElementById('fastForwardToggle').addEventListener('change', (e) => {
            this.toggleControl('fast-forward-nights', e.target.checked);
        });
        
        document.getElementById('slowDownToggle').addEventListener('change', (e) => {
            this.toggleControl('slow-down-days', e.target.checked);
        });

        // Simulation control toggle
        document.getElementById('simulationControlToggle').addEventListener('change', (e) => {
            this.toggleSimulationControlModal(e.target.checked);
        });

        // Simulation parameters modal
        document.getElementById('paramsModalClose').addEventListener('click', () => {
            this.closeSimulationParamsModal();
        });

        // Parameters modal outside click
        document.getElementById('simulationParamsModal').addEventListener('click', (e) => {
            if (e.target.id === 'simulationParamsModal') {
                this.closeSimulationParamsModal();
            }
        });

        // Parameters tabs
        document.querySelectorAll('.params-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                const tabName = tab.dataset.tab;
                this.switchParamsTab(tabName);
            });
        });

        // Range input updates
        document.querySelectorAll('input[type="range"]').forEach(input => {
            input.addEventListener('input', (e) => {
                this.updateRangeDisplay(e.target);
            });
        });

        // Form submission
        document.getElementById('simulationParamsForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitSimulationParams();
        });

        // Reset button
        document.getElementById('resetParams').addEventListener('click', () => {
            this.resetSimulationParams();
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

            // Load initial control states
            const controlsResponse = await fetch('http://localhost:8000/controls/status');
            if (controlsResponse.ok) {
                const controls = await controlsResponse.json();
                console.log('Loaded initial controls:', controls);
                this.updateControlToggles(controls);
            }

            // Load initial simulation config status
            const configResponse = await fetch('http://localhost:8000/simulation/config');
            if (configResponse.ok) {
                const config = await configResponse.json();
                console.log('Loaded simulation config:', config);
                this.updateSimulationControlStatus(config);
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
            this.updateWeatherCharts(data.weather, data.timestamp);
        }
        
        // Update households
        if (data.households) {
            this.updateHouseholds(data.households);
        }
        
        // Update trades and activity
        if (data.trades) {
            this.updateTrades(data.trades);
        }
        
        // Update controls
        if (data.controls) {
            this.updateControlToggles(data.controls);
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
        // Update temperature - rounded to 1 decimal place
        const temp = parseFloat(weather.temp ?? 22.5).toFixed(1);
        // Use ?? instead of || to properly handle 0 values for solar radiation
        const solarRad = parseFloat(weather.solar_radiation ?? 800).toFixed(0);
        const clouds = parseFloat(weather.clouds ?? 30).toFixed(0);
        const humidity = parseFloat(weather.humidity ?? 65).toFixed(0);
        
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
        // Clean up any existing tooltips since we're about to update the activity feed
        this.cleanupAllTooltips();
        
        // Add new trades to activity log
        trades.forEach(trade => {
            if (!this.activityLog.find(log => 
                log.seller_id === trade.seller_id && 
                log.buyer_id === trade.buyer_id && 
                log.timestamp === trade.timestamp
            )) {
                this.activityLog.unshift({
                    type: 'trade',
                    text: `House ${trade.seller_id} → House ${trade.buyer_id}`,
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
        // Clean up any existing tooltips before re-rendering
        this.cleanupAllTooltips();
        
        const feed = document.getElementById('activityFeed');
        
        if (this.activityLog.length === 0) {
            feed.innerHTML = '<div class="no-activity">No recent activity</div>';
            return;
        }
        
        feed.innerHTML = this.activityLog.map(activity => `
            <div class="activity-item" 
                 data-kwh="${activity.kwh || 0}" 
                 data-price="${activity.price || 0}" 
                 data-total="${activity.total || (activity.kwh * activity.price) || 0}">
                <div class="activity-icon ${activity.type}">
                    ${activity.type === 'trade' ? '⚡' : 'ℹ️'}
                </div>
                <div class="activity-content">
                    <div class="activity-text">${activity.text}</div>
                    <div class="activity-time-stamp">${activity.timestamp.toLocaleTimeString()}</div>
                </div>
            </div>
        `).join('');
        
        // Add tooltip functionality to activity items
        this.addActivityTooltips();
    }

    addActivityTooltips() {
        const activityItems = document.querySelectorAll('.activity-item[data-kwh]');
        
        activityItems.forEach(item => {
            let tooltip = null;
            
            const showTooltip = (e) => {
                // Remove any existing tooltip first
                this.removeTooltip(tooltip);
                
                const activityItem = e.target.closest('.activity-item');
                const kwh = parseFloat(activityItem.dataset.kwh);
                const price = parseFloat(activityItem.dataset.price);
                const total = parseFloat(activityItem.dataset.total);
                
                // Only show tooltip for trade items with valid data
                if (kwh > 0 && price > 0) {
                    tooltip = this.createTooltip(kwh, price, total);
                    document.body.appendChild(tooltip);
                    
                    // Position tooltip relative to the activity item
                    this.positionTooltip(tooltip, activityItem);
                    
                    // Show tooltip with animation
                    setTimeout(() => {
                        if (tooltip) tooltip.classList.add('show');
                    }, 10);
                }
            };
            
            const hideTooltip = () => {
                if (tooltip && tooltip.parentNode) {
                    this.removeTooltip(tooltip);
                }
                tooltip = null;
            };
            
            item.addEventListener('mouseenter', showTooltip);
            item.addEventListener('mouseleave', hideTooltip);
        });
    }

    createTooltip(kwh, price, total) {
        const tooltip = document.createElement('div');
        tooltip.className = 'activity-tooltip';
        
        tooltip.innerHTML = `
            <div class="tooltip-content">
                <div class="tooltip-line">
                    <span class="tooltip-label">Energy Amount:</span>
                    <span class="tooltip-value">${kwh.toFixed(3)} kWh</span>
                </div>
                <div class="tooltip-line">
                    <span class="tooltip-label">Price per kWh:</span>
                    <span class="tooltip-value">$${price.toFixed(3)}</span>
                </div>
                <div class="tooltip-line">
                    <span class="tooltip-label">Total Cost:</span>
                    <span class="tooltip-value total">$${total.toFixed(3)}</span>
                </div>
            </div>
        `;
        
        return tooltip;
    }

    cleanupAllTooltips() {
        // Remove all existing tooltips immediately (no animation needed since we're re-rendering)
        const existingTooltips = document.querySelectorAll('.activity-tooltip');
        existingTooltips.forEach(tooltip => {
            if (tooltip.parentNode) {
                tooltip.parentNode.removeChild(tooltip);
            }
        });
    }

    removeTooltip(tooltip) {
        if (tooltip && tooltip.parentNode) {
            tooltip.classList.remove('show');
            setTimeout(() => {
                // Double-check that tooltip still exists and has a parent
                if (tooltip && tooltip.parentNode && document.contains(tooltip)) {
                    tooltip.parentNode.removeChild(tooltip);
                }
            }, 150); // Match CSS transition duration
        }
    }

    positionTooltip(tooltip, activityItem) {
        const itemRect = activityItem.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        const scrollX = window.pageXOffset || document.documentElement.scrollLeft;
        const scrollY = window.pageYOffset || document.documentElement.scrollTop;
        
        // Position tooltip above the activity item, centered horizontally
        let left = itemRect.left + scrollX + (itemRect.width / 2) - (tooltipRect.width / 2);
        let top = itemRect.top + scrollY - tooltipRect.height - 10;
        
        // Adjust if tooltip goes off screen horizontally
        if (left < 10) left = 10;
        if (left + tooltipRect.width > window.innerWidth - 10) {
            left = window.innerWidth - tooltipRect.width - 10;
        }
        
        // If tooltip would go above viewport, show it below the item instead
        if (top < scrollY + 10) {
            top = itemRect.bottom + scrollY + 10;
            tooltip.classList.add('below');
        } else {
            tooltip.classList.remove('below');
        }
        
        tooltip.style.left = left + 'px';
        tooltip.style.top = top + 'px';
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

    initializeWeatherCharts() {
        // Initialize Solar Radiation Chart
        const solarCtx = document.getElementById('solarRadiationChart').getContext('2d');
        this.solarRadiationChart = new Chart(solarCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Solar Radiation (W/m²)',
                    data: [],
                    borderColor: '#F59E0B',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 2,
                    pointHoverRadius: 6,
                    borderWidth: 2
                }]
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
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(26, 26, 46, 0.9)',
                        titleColor: '#FFFFFF',
                        bodyColor: '#A0AEC0',
                        borderColor: '#2D3748',
                        borderWidth: 1,
                        callbacks: {
                            title: function(context) {
                                const date = new Date(context[0].parsed.x);
                                return date.toLocaleTimeString('en-US', { 
                                    hour: 'numeric', 
                                    minute: '2-digit', 
                                    hour12: true,
                                    timeZone: 'UTC'
                                });
                            },
                            label: function(context) {
                                return `Solar Radiation: ${context.parsed.y.toFixed(0)} W/m²`;
                            }
                        }
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
                            color: '#718096',
                            maxTicksLimit: 12
                        },
                        title: {
                            display: true,
                            text: 'Simulation Time',
                            color: '#A0AEC0'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        max: 1000,
                        grid: {
                            color: 'rgba(45, 55, 72, 0.5)'
                        },
                        ticks: {
                            color: '#718096'
                        },
                        title: {
                            display: true,
                            text: 'Solar Radiation (W/m²)',
                            color: '#A0AEC0'
                        }
                    }
                },
                elements: {
                    point: {
                        radius: 2,
                        hoverRadius: 6
                    }
                },
                animation: {
                    duration: 750,
                    easing: 'easeInOutQuart'
                }
            }
        });

        // Initialize Temperature Chart
        const tempCtx = document.getElementById('temperatureChart').getContext('2d');
        this.temperatureChart = new Chart(tempCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Temperature (°C)',
                    data: [],
                    borderColor: '#EF4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 2,
                    pointHoverRadius: 6,
                    borderWidth: 2
                }]
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
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(26, 26, 46, 0.9)',
                        titleColor: '#FFFFFF',
                        bodyColor: '#A0AEC0',
                        borderColor: '#2D3748',
                        borderWidth: 1,
                        callbacks: {
                            title: function(context) {
                                const date = new Date(context[0].parsed.x);
                                return date.toLocaleTimeString('en-US', { 
                                    hour: 'numeric', 
                                    minute: '2-digit', 
                                    hour12: true,
                                    timeZone: 'UTC'
                                });
                            },
                            label: function(context) {
                                return `Temperature: ${context.parsed.y.toFixed(1)}°C`;
                            }
                        }
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
                            color: '#718096',
                            maxTicksLimit: 12
                        },
                        title: {
                            display: true,
                            text: 'Simulation Time',
                            color: '#A0AEC0'
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(45, 55, 72, 0.5)'
                        },
                        ticks: {
                            color: '#718096'
                        },
                        title: {
                            display: true,
                            text: 'Temperature (°C)',
                            color: '#A0AEC0'
                        }
                    }
                },
                elements: {
                    point: {
                        radius: 2,
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

    updateWeatherCharts(weather, timestamp) {
        if (!this.solarRadiationChart || !this.temperatureChart) return;

        const time = new Date(timestamp);
        const solar_radiation = parseFloat(weather.solar_radiation ?? 0);
        const temperature = parseFloat(weather.temp ?? 22.5);

        // Add new data point
        this.weatherData.push({
            timestamp: time,
            solar_radiation: solar_radiation,
            temperature: temperature
        });

        // Keep only last 24 hours of data (24 data points since we get 1 per hour)
        const maxDataPoints = 24;
        if (this.weatherData.length > maxDataPoints) {
            this.weatherData = this.weatherData.slice(-maxDataPoints);
        }

        // Update solar radiation chart
        const solarLabels = this.weatherData.map(item => item.timestamp);
        const solarData = this.weatherData.map(item => item.solar_radiation);
        
        this.solarRadiationChart.data.labels = solarLabels;
        this.solarRadiationChart.data.datasets[0].data = solarData;
        this.solarRadiationChart.update('none'); // Use 'none' for real-time updates

        // Update temperature chart
        const tempLabels = this.weatherData.map(item => item.timestamp);
        const tempData = this.weatherData.map(item => item.temperature);
        
        this.temperatureChart.data.labels = tempLabels;
        this.temperatureChart.data.datasets[0].data = tempData;
        this.temperatureChart.update('none'); // Use 'none' for real-time updates
    }

    async loadInitialWeatherData() {
        try {
            // Load the household_state.json file to get historical weather data
            const response = await fetch('/household_state.json');
            if (response.ok) {
                const data = await response.json();
                console.log('Loaded initial weather data:', data.length, 'data points');
                
                // Take the last 24 data points for initial display
                const recentData = data.slice(-24);
                
                // Initialize weather data array with historical data
                this.weatherData = recentData.map(item => ({
                    timestamp: new Date(item.timestamp),
                    solar_radiation: parseFloat(item.weather?.solar_radiation ?? 0),
                    temperature: parseFloat(item.weather?.temp ?? 22.5)
                }));
                
                // Update charts with initial data
                if (this.solarRadiationChart && this.temperatureChart) {
                    const solarLabels = this.weatherData.map(item => item.timestamp);
                    const solarData = this.weatherData.map(item => item.solar_radiation);
                    const tempLabels = this.weatherData.map(item => item.timestamp);
                    const tempData = this.weatherData.map(item => item.temperature);
                    
                    this.solarRadiationChart.data.labels = solarLabels;
                    this.solarRadiationChart.data.datasets[0].data = solarData;
                    this.solarRadiationChart.update();
                    
                    this.temperatureChart.data.labels = tempLabels;
                    this.temperatureChart.data.datasets[0].data = tempData;
                    this.temperatureChart.update();
                }
            }
        } catch (error) {
            console.error('Failed to load initial weather data:', error);
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

    updateControlToggles(controls) {
        const fastForwardToggle = document.getElementById('fastForwardToggle');
        const slowDownToggle = document.getElementById('slowDownToggle');
        
        if (fastForwardToggle) {
            fastForwardToggle.checked = controls.fast_forward_nights;
        }
        
        if (slowDownToggle) {
            slowDownToggle.checked = controls.slow_down_days;
        }
    }

    async toggleControl(controlName, isEnabled) {
        try {
            const response = await fetch(`http://localhost:8000/controls/${controlName}`, {
                method: 'POST'
            });
            if (response.ok) {
                const updatedControls = await response.json();
                this.updateControlToggles(updatedControls);
                console.log(`Toggled ${controlName} to ${isEnabled}`);
            } else {
                console.error(`Failed to toggle ${controlName}`);
                // Revert UI on failure
                this.refreshControls();
            }
        } catch (error) {
            console.error(`Error toggling ${controlName}:`, error);
            this.refreshControls();
        }
    }

    async refreshControls() {
        try {
            const response = await fetch('http://localhost:8000/controls/status');
            if (response.ok) {
                const controls = await response.json();
                this.updateControlToggles(controls);
            }
        } catch (error) {
            console.error('Failed to refresh controls state:', error);
        }
    }

    toggleTheme() {
        const isDarkMode = this.themeToggle.checked;
        this.setTheme(isDarkMode ? 'dark' : 'light');
    }

    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('solar-theme', theme);
        this.themeToggle.checked = theme === 'dark';

        // Update chart colors if they exist
        if (this.chart) {
            this.updateChartAppearance(this.chart, theme);
        }
        if (this.solarRadiationChart) {
            this.updateChartAppearance(this.solarRadiationChart, theme);
        }
        if (this.temperatureChart) {
            this.updateChartAppearance(this.temperatureChart, theme);
        }
    }

    applyInitialTheme() {
        const savedTheme = localStorage.getItem('solar-theme') || 'light';
        this.setTheme(savedTheme);
    }
    
    updateChartAppearance(chart, theme) {
        const isDark = theme === 'dark';
        const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
        const textColor = isDark ? '#a0aec0' : '#4a5568';
        const titleColor = isDark ? '#e2e8f0' : '#1a202c';

        chart.options.scales.x.grid.color = gridColor;
        chart.options.scales.y.grid.color = gridColor;
        chart.options.scales.x.ticks.color = textColor;
        chart.options.scales.y.ticks.color = textColor;
        chart.options.plugins.legend.labels.color = textColor;
        chart.options.plugins.title.color = titleColor;
        
        chart.update();
    }

    // Simulation Parameters Modal Methods
    toggleSimulationControlModal(isEnabled) {
        if (isEnabled) {
            this.openSimulationParamsModal();
        } else {
            this.closeSimulationParamsModal();
            this.resetSimulationControl();
        }
    }

    async openSimulationParamsModal() {
        try {
            // Load current configuration
            const response = await fetch('http://localhost:8000/simulation/config');
            if (response.ok) {
                const config = await response.json();
                this.populateSimulationParams(config);
            }
            
            // Show modal
            document.getElementById('simulationParamsModal').classList.add('active');
        } catch (error) {
            console.error('Failed to load simulation config:', error);
        }
    }

    closeSimulationParamsModal() {
        document.getElementById('simulationParamsModal').classList.remove('active');
        // Don't uncheck the toggle here - let the user decide
    }

    resetSimulationControl() {
        // Reset toggle if modal was closed without applying
        document.getElementById('simulationControlToggle').checked = false;
        // Reset simulation to defaults
        this.resetSimulationParams();
    }

    switchParamsTab(tabName) {
        // Remove active class from all tabs and content
        document.querySelectorAll('.params-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelectorAll('.params-tab-content').forEach(content => {
            content.classList.remove('active');
        });

        // Add active class to selected tab and content
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        document.getElementById(`${tabName}Tab`).classList.add('active');
    }

    updateRangeDisplay(input) {
        const valueSpan = input.parentElement.querySelector('.param-value');
        if (valueSpan) {
            let value = input.value;
            // Format value based on input type
            if (input.step === '0.01') {
                value = parseFloat(value).toFixed(2);
            } else if (input.step === '0.1') {
                value = parseFloat(value).toFixed(1);
            }
            valueSpan.textContent = value;
        }
    }

    populateSimulationParams(config) {
        const { custom_enabled, parameters } = config;
        
        if (custom_enabled && parameters) {
            // Populate household parameters
            if (parameters.household) {
                this.setInputValue('solarCapacity', parameters.household.solar_capacity);
                this.setInputValue('batterySize', parameters.household.battery_size);
                this.setInputValue('initialBatteryLevel', parameters.household.initial_battery_level);
                this.setInputValue('orientation', parameters.household.orientation);
                this.setInputValue('householdType', parameters.household.household_type);
                this.setInputValue('energyConscious', parameters.household.energy_conscious);
            }

            // Populate trading parameters
            if (parameters.trading) {
                this.setInputValue('minReserve', parameters.trading.minimum_reserve_percentage);
                this.setInputValue('minPrice', parameters.trading.min_price);
                this.setInputValue('maxPrice', parameters.trading.max_price);
                this.setInputValue('maxTradingRounds', parameters.trading.max_trading_rounds);
                this.setInputValue('maxTradeSize', parameters.trading.max_trade_size_first);
                this.setInputValue('minTradeSize', parameters.trading.min_trade_size);
            }

            // Populate weather parameters
            if (parameters.weather) {
                this.setInputValue('tempMean', parameters.weather.temp_mean);
                this.setInputValue('maxSolarRadiation', parameters.weather.max_solar_radiation);
                this.setInputValue('cloudsBase', parameters.weather.clouds_base);
                this.setInputValue('heatwaveDemand', parameters.weather.heatwave_demand_multiplier);
                this.setInputValue('heatwaveSolar', parameters.weather.heatwave_solar_reduction);
                this.setInputValue('heatwaveDuration', parameters.weather.heatwave_min_duration);
            }

            // Populate speed parameters
            if (parameters.speed) {
                this.setInputValue('fastForwardNights', parameters.speed.fast_forward_nights);
                this.setInputValue('slowDownDays', parameters.speed.slow_down_days);
            }
        }

        // Update range displays
        document.querySelectorAll('input[type="range"]').forEach(input => {
            this.updateRangeDisplay(input);
        });
    }

    setInputValue(inputId, value) {
        const input = document.getElementById(inputId);
        if (input) {
            if (input.type === 'checkbox') {
                input.checked = value;
            } else {
                input.value = value;
            }
        }
    }

    async submitSimulationParams() {
        try {
            const formData = new FormData(document.getElementById('simulationParamsForm'));
            const parameters = {
                household: {
                    solar_capacity: parseFloat(formData.get('solar_capacity')),
                    battery_size: parseFloat(formData.get('battery_size')),
                    initial_battery_level: parseInt(formData.get('initial_battery_level')),
                    orientation: formData.get('orientation'),
                    household_type: formData.get('household_type'),
                    energy_conscious: formData.has('energy_conscious')
                },
                trading: {
                    minimum_reserve_percentage: parseInt(formData.get('minimum_reserve_percentage')),
                    min_price: parseFloat(formData.get('min_price')),
                    max_price: parseFloat(formData.get('max_price')),
                    max_trading_rounds: parseInt(formData.get('max_trading_rounds')),
                    max_trade_size_first: parseFloat(formData.get('max_trade_size_first')),
                    min_trade_size: parseFloat(formData.get('min_trade_size'))
                },
                weather: {
                    temp_mean: parseInt(formData.get('temp_mean')),
                    max_solar_radiation: parseInt(formData.get('max_solar_radiation')),
                    clouds_base: parseInt(formData.get('clouds_base')),
                    heatwave_demand_multiplier: parseFloat(formData.get('heatwave_demand_multiplier')),
                    heatwave_solar_reduction: parseFloat(formData.get('heatwave_solar_reduction')),
                    heatwave_min_duration: parseInt(formData.get('heatwave_min_duration'))
                },
                speed: {
                    fast_forward_nights: formData.has('fast_forward_nights'),
                    slow_down_days: formData.has('slow_down_days')
                }
            };

            const response = await fetch('http://localhost:8000/simulation/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    enabled: true,
                    parameters: parameters
                })
            });

            if (response.ok) {
                const result = await response.json();
                console.log('Simulation parameters updated:', result);
                this.closeSimulationParamsModal();
                
                // Add to activity log
                this.addActivity('simulation', 'Custom simulation parameters applied', 'system');
            } else {
                console.error('Failed to update simulation parameters');
                alert('Failed to update simulation parameters. Please try again.');
            }
        } catch (error) {
            console.error('Error submitting simulation parameters:', error);
            alert('Error updating simulation parameters. Please check your network connection.');
        }
    }

    async resetSimulationParams() {
        try {
            const response = await fetch('http://localhost:8000/simulation/config', {
                method: 'DELETE'
            });

            if (response.ok) {
                console.log('Simulation parameters reset to defaults');
                // Reset form to default values
                this.loadDefaultParameters();
                
                // Add to activity log
                this.addActivity('simulation', 'Simulation parameters reset to defaults', 'system');
            } else {
                console.error('Failed to reset simulation parameters');
            }
        } catch (error) {
            console.error('Error resetting simulation parameters:', error);
        }
    }

    loadDefaultParameters() {
        // Set default values for all parameters
        this.setInputValue('solarCapacity', 3.5);
        this.setInputValue('batterySize', 10.0);
        this.setInputValue('initialBatteryLevel', 50);
        this.setInputValue('orientation', 'south');
        this.setInputValue('householdType', 'typical');
        this.setInputValue('energyConscious', false);

        this.setInputValue('minReserve', 20);
        this.setInputValue('minPrice', 0.10);
        this.setInputValue('maxPrice', 0.20);
        this.setInputValue('maxTradingRounds', 3);
        this.setInputValue('maxTradeSize', 2.0);
        this.setInputValue('minTradeSize', 0.05);

        this.setInputValue('tempMean', 22);
        this.setInputValue('maxSolarRadiation', 800);
        this.setInputValue('cloudsBase', 25);
        this.setInputValue('heatwaveDemand', 1.5);
        this.setInputValue('heatwaveSolar', 0.4);
        this.setInputValue('heatwaveDuration', 3);

        this.setInputValue('fastForwardNights', false);
        this.setInputValue('slowDownDays', false);

        // Update range displays
        document.querySelectorAll('input[type="range"]').forEach(input => {
            this.updateRangeDisplay(input);
        });
    }

    updateSimulationControlStatus(config) {
        const toggle = document.getElementById('simulationControlToggle');
        if (toggle) {
            toggle.checked = config.custom_enabled || false;
        }
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