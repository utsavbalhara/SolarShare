# SolarShare Simulation Engine Documentation

## Overview

This document provides comprehensive documentation for the SolarShare simulation engine, including all parameters, formulas, output formats, and trading mechanisms.

## Table of Contents
1. [Input Parameters](#input-parameters)
2. [Output Parameters](#output-parameters)
3. [Mathematical Formulas](#mathematical-formulas)
4. [Trading System](#trading-system)
5. [Role Assignment](#role-assignment)
6. [Weather System](#weather-system)
7. [Crisis Events](#crisis-events)
8. [Metrics Calculation](#metrics-calculation)

---

## Input Parameters

### Household Configuration Parameters

#### Core Parameters
- **`id`** (string): Unique identifier for the household
- **`solar_capacity`** (float): Solar panel capacity in kW (typical range: 2-5 kW)
- **`battery_size`** (float): Battery storage capacity in kWh (typical range: 5-15 kWh)
- **`demand_pattern`** (List[float]): 24-hour demand pattern in kWh per hour
- **`initial_battery_level`** (float): Initial battery charge level (0.0 to 1.0, default: 0.5)

#### Configuration Parameters
- **`orientation`** (string): Solar panel orientation
  - Options: "south", "east", "west", "north"
  - Default: "south"
- **`energy_conscious`** (boolean): Flag for households that conserve energy during community deficit
  - Default: False
- **`energy_hoarder`** (boolean): Flag for households that prefer storing energy over trading
  - Default: False

#### Demand Pattern Types
- **"typical"**: Standard household with morning and evening peaks
- **"high_usage"**: High energy consumption household
- **"low_usage"**: Energy-efficient household
- **"night_shift"**: Household with night shift workers (shifted demand pattern)

### Simulation Engine Parameters

#### Time Configuration
- **`start_date`** (string): Simulation start date and time (format: "YYYY-MM-DD HH:MM:SS")
  - Default: "2025-06-23 00:00:00"
- **`speed_factor`** (int): Simulation speed (seconds per simulation step)
  - Default: 3600 (1 simulated hour per real second)

#### System Constants
- **`GRID_PRICE`**: Grid electricity price = $0.20/kWh
- **`GRID_EMISSIONS`**: Grid CO2 emissions = 0.5 kg CO2/kWh
- **`MINIMUM_RESERVE`**: Minimum battery reserve for selling = 20%
- **`BATTERY_EFFICIENCY`**: Battery charging/discharging efficiency = 100% (simplified)

---

## Output Parameters

### Household State Output
Each household generates the following state information per simulation step:

```json
{
  "id": "H001",
  "role": "seller|buyer|idle",
  "battery": 75,                    // Battery level (0-100%)
  "solar": 3.45,                   // Solar generation (kWh)
  "demand": 1.20,                  // Energy demand (kWh)
  "net_energy": 2.25               // Net energy after internal consumption (kWh)
}
```

### Simulation Step Output
Each simulation step produces:

```json
{
  "timestamp": "2025-06-23T15:00:00Z",
  "households": [...],             // Array of household states
  "trades": [...],                 // Array of executed trades
  "weather": {...},                // Weather conditions
  "metrics": {...}                 // Community metrics
}
```

### Trade Output Format
```json
{
  "from": "H001",                  // Seller ID
  "to": "H006",                    // Buyer ID
  "kwh": 1.25,                     // Energy amount (kWh)
  "price": 0.19                    // Total price ($)
}
```

### Weather Output Format
```json
{
  "temp": 24.5,                    // Temperature (°C)
  "clouds": 35.0,                  // Cloud cover (0-100%)
  "solar_radiation": 650.0,        // Solar radiation (W/m²)
  "humidity": 62.0                 // Humidity (0-100%)
}
```

### Metrics Output Format
```json
{
  "energy_traded": 156.7,          // Total energy traded (kWh)
  "cost_savings": 31.3,            // Total cost savings ($)
  "co2_reduced": 78.4,             // CO2 emissions reduced (kg)
  "resilience": 72,                // Community resilience score (0-100)
  "delta_energy": "+2.5",          // Hourly change in energy traded
  "delta_savings": "+0.5",         // Hourly change in savings
  "delta_co2": "+1.2",             // Hourly change in CO2 reduction
  "delta_resilience": "+3"         // Hourly change in resilience
}
```

---

## Mathematical Formulas

### Solar Generation Formula
```
solar_generation = solar_capacity × weather_factor × time_factor × orientation_factor × crisis_factor
```

Where:
- **time_factor** = `max(0, 1 - abs(12 - hour) / 6)` (peaks at noon)
- **weather_factor** = `max(0.4, (1 - clouds/100 × cloud_impact) × radiation_boost)`
- **cloud_impact** = `random(0.6, 0.8)` (reduced cloud impact for balance)
- **radiation_boost** = `min(1.1, solar_radiation / 600)`
- **orientation_factor**: 
  - South: 1.0
  - East/West: 0.8  
  - North: 0.6
- **crisis_factor** = `(1 - crisis.solar_reduction)` during crisis events

### Energy Demand Formula
```
energy_demand = base_demand[hour] × temp_factor × humidity_factor × crisis_factor
```

Where:
- **base_demand[hour]**: Hourly demand from 24-hour pattern
- **temp_factor** = `1 + abs(temperature - 22) × 0.015`
- **humidity_factor** = `1.1` if humidity > 70%, else `1.0`
- **crisis_factor** = `crisis.demand_multiplier` during crisis events

### Battery Storage Formulas

#### Charging (Excess Energy)
```
available_capacity_percentage = 100 - current_stored_energy
max_storable_kwh = (available_capacity_percentage / 100) × battery_size
energy_to_store = min(excess_energy, max_storable_kwh)
storage_gain_percentage = (energy_to_store / battery_size) × 100
new_stored_energy = current_stored_energy + storage_gain_percentage
```

#### Discharging (Energy Deficit)
```
available_stored_kwh = (current_stored_energy / 100) × battery_size
energy_from_storage = min(energy_needed, available_stored_kwh)
storage_loss_percentage = (energy_from_storage / battery_size) × 100
new_stored_energy = current_stored_energy - storage_loss_percentage
```

### Net Energy Calculation
```
net_energy = solar_generation - energy_demand
```

After battery operations:
```
final_net_energy = net_energy - energy_stored_in_battery + energy_drawn_from_battery
```

---

## Trading System

### Storage-First Trading Model
The system implements a **storage-first energy trading model** where:
1. Solar generation first meets current demand
2. Excess energy is stored in batteries
3. Trading occurs only from stored energy reserves
4. Current generation cannot be directly traded

### Trading Process Flow

#### 1. Role Assignment Phase
- Households are assigned roles based on storage levels and energy needs
- Role assignment occurs after battery state updates

#### 2. Market Formation Phase
```
sellers = households where (stored_energy > 20% AND role == SELLER)
buyers = households where (stored_energy < 100% AND role == BUYER)
```

#### 3. Dynamic Pricing Phase
```
supply = Σ((seller.stored_energy - 20) / 100 × seller.battery) for all sellers
demand = Σ(abs(min(0, buyer.net_energy))) for all buyers

supply_demand_ratio = supply / demand

if supply_demand_ratio > 1.5:
    price = $0.10/kWh  // Buyer's market
elif supply_demand_ratio > 0.8:
    price = $0.15/kWh  // Balanced market
else:
    price = $0.20/kWh  // Seller's market
```

#### 4. Multi-Round Matching
The system executes up to 3 trading rounds per simulation step:

**Round 1 (Large Trades):**
```
max_trade = min(
    seller_available_kwh × 0.6,    // Up to 60% of available stored energy
    buyer_need × 0.8,              // Up to 80% of buyer's need
    2.0 kWh                        // Maximum trade size
)
```

**Subsequent Rounds (Small Trades):**
```
max_trade = min(
    seller_available_kwh × 0.4,    // Up to 40% of available stored energy
    buyer_need × 0.6,              // Up to 60% of buyer's need
    1.0 kWh                        // Maximum trade size
)
```

#### 5. Trade Execution
```
seller_available_kwh = ((seller.stored_energy - 20.0) / 100.0) × seller.battery
```

For sellers:
```
trade_percentage = (trade_amount / seller.battery) × 100
new_stored_energy = seller.stored_energy - trade_percentage
```

For buyers:
```
trade_percentage = (trade_amount / buyer.battery) × 100
new_stored_energy = buyer.stored_energy + trade_percentage
```

### Trading Constraints
- **Minimum Reserve**: Sellers must maintain 20% battery reserve
- **Storage Capacity**: Buyers cannot exceed 100% battery capacity
- **Minimum Trade Size**: 0.05 kWh minimum per trade
- **Maximum Rounds**: 3 trading rounds per simulation step

---

## Role Assignment

### Role Determination Logic
Household roles are updated after each simulation step based on current battery state and energy balance:

```python
def _update_role(self):
    if self.stored_energy > 20.0:
        self.role = Role.SELLER
    elif self.current_net_energy < 0 and self.stored_energy < 100.0:
        self.role = Role.BUYER
    else:
        self.role = Role.IDLE
```

### Role Definitions

#### SELLER
- **Condition**: `stored_energy > 20%`
- **Behavior**: Can sell excess stored energy while maintaining 20% reserve
- **Priority**: Sorted by highest stored energy first in trading

#### BUYER  
- **Condition**: `net_energy < 0 AND stored_energy < 100%`
- **Behavior**: Can purchase energy to meet deficit and store excess
- **Priority**: Sorted by lowest stored energy and highest deficit first

#### IDLE
- **Conditions**: 
  - At minimum reserve (stored_energy ≤ 20%), OR
  - No energy deficit (net_energy ≥ 0), OR  
  - Battery full (stored_energy = 100%)
- **Behavior**: Does not participate in trading

### Role Transition Examples

```
Initial: stored_energy = 15%, net_energy = -2.0 kWh → BUYER
After purchase: stored_energy = 35%, net_energy = 0 kWh → SELLER

Initial: stored_energy = 80%, net_energy = +1.5 kWh → SELLER  
After sale: stored_energy = 25%, net_energy = +1.5 kWh → SELLER

Initial: stored_energy = 22%, net_energy = 0 kWh → IDLE
After solar generation: stored_energy = 45%, net_energy = 0 kWh → SELLER
```

---

## Weather System

### Weather Generation
The system generates realistic weather patterns with daily cycles:

#### Temperature Model
```
temp_mean = 22°C
temp_amplitude = 5°C
temperature = temp_mean + temp_amplitude × sin(2π × (hour - 9) / 24) + noise
```
- Peaks around 3 PM (hour 15)
- Daily variation: ±5°C around 22°C mean
- Random noise: ±0.5°C

#### Solar Radiation Model
```
For daylight hours (6 AM - 6 PM):
solar_radiation = max(200, cos((hour - 12) × π / 15) × 800) + noise

For nighttime hours:
solar_radiation = 0 W/m²
```
- Peaks at noon (hour 12)
- Range: 200-800 W/m² during daylight
- Random variation: ±30 W/m²

#### Cloud Cover Model
```
clouds_base = 25%
clouds_variation = 15%
clouds = clouds_base + random(-clouds_variation, +clouds_variation)
clouds = constrain(clouds, 10%, 60%)
```
- Moderate cloud conditions for balanced trading
- Range: 10-60% cloud cover

#### Humidity Model
```
humidity = 55 + 15 × sin(2π × (hour - 6) / 24) + noise
humidity = constrain(humidity, 40%, 80%)
```
- Daily cycle with morning/evening peaks
- Range: 40-80% humidity

---

## Crisis Events

### Heatwave Crisis Parameters
```python
CrisisEvent(
    demand_multiplier: 1.5 - 1.8,    // Demand increase factor
    solar_reduction: 0.3 - 0.5,      // Solar generation reduction factor  
    duration: 3 - 6 hours,           // Crisis duration
    start_hour: current_hour,        // Crisis start time
    end_hour: start_hour + duration  // Crisis end time
)
```

### Crisis Effects on Households

#### Demand Impact
```
crisis_demand = normal_demand × crisis.demand_multiplier
```
- Increases energy consumption by 50-80%
- Simulates increased cooling/heating needs

#### Solar Impact  
```
crisis_solar = normal_solar × (1 - crisis.solar_reduction)
```
- Reduces solar generation by 30-50%
- Simulates reduced sunlight during extreme weather

### Crisis Triggering
- Randomly triggered during simulation
- Affects all households simultaneously
- Automatically clears after duration expires

---

## Metrics Calculation

### Energy Trading Metrics
```
total_energy_traded = Σ(trade.kwh) for all trades
hourly_energy_delta = current_hour_traded - previous_hour_traded
```

### Cost Savings Calculation
```
cost_savings = total_energy_traded × GRID_PRICE
hourly_savings_delta = current_hour_savings - previous_hour_savings
```
- Assumes all traded energy would otherwise be purchased from grid at $0.20/kWh

### CO2 Reduction Calculation  
```
co2_reduced = total_energy_traded × GRID_EMISSIONS
hourly_co2_delta = current_hour_co2 - previous_hour_co2
```
- Assumes all traded energy avoids grid emissions at 0.5 kg CO2/kWh

### Community Resilience Score
```
avg_stored_energy = Σ(household.stored_energy) / num_households
trading_activity = min(1.0, num_trades / 5)
buyer_ratio = num_buyers / num_households

resilience = min(100, max(0, 
    avg_stored_energy × 0.5 +      // 50% weight to storage levels
    trading_activity × 30 +        // 30% weight to trading activity  
    (1 - buyer_ratio) × 20         // 20% weight to energy independence
))
```

### Delta Calculations
All metrics include hourly change indicators:
```
delta_format = f"+{value:.1f}" if value >= 0 else f"{value:.1f}"
```

---

## Behavioral Features

### Energy Consciousness
Households with `energy_conscious = True`:
- Reduce demand by 15% when community has energy deficit
- Only activates when sellers = 0 and buyers > 0
- Helps balance supply/demand for better trading

### Energy Hoarding
Households with `energy_hoarder = True`:
- Do not increase demand during surplus conditions  
- Prefer storing energy over consuming
- Maintain higher battery reserves

### Smart Demand Adjustment
The system automatically adjusts demand patterns to encourage trading:

**Surplus Scenario** (sellers > 0, buyers = 0):
```
selected_households = lowest_demand_households[:2]
for household in selected_households:
    if not household.energy_hoarder:
        household.demand *= 1.1  // Increase demand by 10%
```

**Deficit Scenario** (sellers = 0, buyers > 0):
```
selected_households = highest_demand_households[:2] 
for household in selected_households:
    if household.energy_conscious:
        household.demand *= 0.85  // Reduce demand by 15%
```

---

## File Outputs

### trades.csv
Detailed transaction log with columns:
- `time`: Transaction timestamp
- `hour`: Simulation hour (0-23)
- `seller_id`: Selling household ID
- `buyer_id`: Buying household ID  
- `kwh`: Energy amount traded
- `price`: Price per kWh
- `total`: Total transaction value

### household_state.json
Real-time state log in array format containing timestamped snapshots of:
- All household states
- Executed trades
- Weather conditions
- Community metrics
- Simulation timestamp

This documentation provides a complete reference for understanding and working with the SolarShare simulation engine parameters, outputs, and trading mechanisms.