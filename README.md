# SolarShare - Digital Twin Simulation Engine

A sophisticated digital twin simulation engine for community solar energy trading. This project emulates household energy behaviors without requiring physical hardware, enabling the development and testing of peer-to-peer energy trading systems.

## 🏗️ Architecture Overview

```
graph LR
    A[Simulation Engine] --> B[Household Models]
    B --> C[Role Switching Logic]
    C --> D[Trading System]
    D --> E[Data Logger]
    E --> F[WebSocket Server]
    F --> G[React Dashboard]
    G --> H[User Interactions]
    H --> A
```

## 🎯 Core Features

### 1. Household Profiling
- **Digital Twin Representation**: Each household is modeled as a digital twin with realistic energy characteristics
- **Solar Capacity**: Configurable solar panel capacity (2-5 kW typical)
- **Battery Storage**: Realistic battery storage simulation (5-15 kWh typical)
- **Demand Patterns**: 24-hour energy consumption patterns for different household types

### 2. Time Step Simulation
- **Hourly Simulation**: Real-time energy generation and consumption simulation
- **Weather Integration**: Dynamic weather factors affecting solar generation
- **Battery Management**: Intelligent battery charge/discharge logic with efficiency modeling
- **Role Switching**: Automatic switching between seller/buyer/idle roles based on energy balance

### 3. Crisis Injection
- **Heatwave Simulation**: Realistic crisis events with increased demand and reduced solar generation
- **Configurable Parameters**: Demand multipliers, solar reduction factors, and duration
- **Community Impact**: Crisis effects applied across all households in the community

## 🚀 Quick Start

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd SolarShare
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the test suite:
```bash
python test_simulation.py
```

### Basic Usage

```python
from simulation_engine import SimulationEngine, Household, generate_demand_pattern

# Create a simulation engine
engine = SimulationEngine()

# Create a household
demand_pattern = generate_demand_pattern("typical")
household = Household("H001", 3.5, 10.0, demand_pattern)
engine.add_household(household)

# Generate weather conditions
engine.generate_weather_conditions(days=3)

# Simulate for 24 hours
results = engine.simulate_period(24)

# Get community status
status = engine.get_community_status()
print(f"Total energy generated: {status['total_generated']:.2f} kWh")
```

## 📊 Household Types

The simulation supports different household types with realistic demand patterns:

- **Typical**: Standard household with morning and evening peaks
- **High Usage**: Energy-intensive household with higher consumption
- **Low Usage**: Energy-efficient household with minimal consumption
- **Night Shift**: Household with non-standard activity patterns

## 🔧 Configuration

### Household Parameters

```python
household = Household(
    id="H001",                    # Unique identifier
    solar_capacity=3.5,           # Solar panel capacity in kW
    battery_size=10.0,            # Battery storage in kWh
    demand_pattern=demand_pattern, # 24-hour demand pattern
    initial_battery_level=0.5     # Initial battery charge (0.0-1.0)
)
```

### Crisis Events

```python
crisis = CrisisEvent(
    demand_multiplier=1.6,        # Increase in energy demand
    solar_reduction=0.4,          # Reduction in solar generation
    duration=4,                   # Duration in hours
    start_hour=12,                # Start hour
    end_hour=16                   # End hour
)
```

## 📈 Simulation Results

The engine provides comprehensive data for analysis:

- **Energy Metrics**: Generation, consumption, and net energy for each household
- **Trading Data**: Energy trades, prices, and partner information
- **Battery States**: Real-time battery levels and efficiency
- **Role Distribution**: Number of sellers, buyers, and idle households
- **Weather Impact**: Weather factors affecting solar generation

## 🔄 Trading System Integration

The simulation engine is designed to integrate seamlessly with trading systems:

```python
# Check if household can trade
if household.can_sell_energy(2.0):
    # Execute trade
    success = household.trade_energy(2.0, 0.15, "H002")
```

## 📁 Project Structure

```
SolarShare/
├── simulation_engine.py    # Main simulation engine
├── test_simulation.py      # Test suite and examples
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_simulation.py
```

The test suite includes:
- Basic household simulation
- Community simulation with multiple households
- Crisis injection testing
- Trading functionality validation
- Data visualization (requires matplotlib)

## 🔮 Next Steps

This Digital Twin Simulation Engine is the foundation for the complete SolarShare system. Next components to implement:

1. **Trading System**: Peer-to-peer energy trading algorithms
2. **Data Logger**: Persistent storage and historical analysis
3. **WebSocket Server**: Real-time data streaming
4. **React Dashboard**: User interface for monitoring and control
5. **Role Switching Logic**: Advanced trading role management

## 🤝 Contributing

This project is part of a larger solar energy trading platform. The simulation engine provides a solid foundation for testing and developing energy trading algorithms without requiring physical infrastructure.

## 📄 License

[Add your license information here]

---

**SolarShare** - Empowering communities through peer-to-peer solar energy trading. 