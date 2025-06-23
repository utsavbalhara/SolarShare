import random
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import time
import os
import pandas as pd
from datetime import datetime, timedelta
import json


class Role(Enum):
    """Enumeration for household roles in energy trading"""
    IDLE = "idle"
    SELLER = "seller"
    BUYER = "buyer"


@dataclass
class CrisisEvent:
    """Data class for crisis events like heatwaves"""
    demand_multiplier: float
    solar_reduction: float
    duration: int
    start_hour: int
    end_hour: int


class MetricsCollector:
    """Collects and calculates community-wide energy metrics"""
    def __init__(self):
        self.energy_traded = 0.0
        self.cost_savings = 0.0
        self.co2_reduced = 0.0
        self.resilience = 50.0  # Start at 50% resilience
        
        # Previous values for delta calculations
        self.prev_energy = 0.0
        self.prev_savings = 0.0
        self.prev_co2 = 0.0
        self.prev_resilience = 50.0
        
        # Constants
        self.GRID_PRICE = 0.20  # $/kWh
        self.GRID_EMISSIONS = 0.5  # kg CO2/kWh

    def update(self, engine, trades: list):
        """Update metrics based on simulation state and trades"""
        # Update cumulative metrics
        hourly_energy = sum(trade["kwh"] for trade in trades)
        self.energy_traded += hourly_energy
        self.cost_savings += hourly_energy * self.GRID_PRICE
        self.co2_reduced += hourly_energy * self.GRID_EMISSIONS
        
        # Calculate resilience score (0-100) using stored energy percentages
        stored_energy_levels = [h.stored_energy for h in engine.households.values()]
        avg_stored_energy = sum(stored_energy_levels) / len(stored_energy_levels) if stored_energy_levels else 0
        trading_activity = min(1.0, len(trades) / 5)  # Scale with trades
        
        num_households = len(engine.households)
        if num_households > 0:
            buyer_ratio = len([h for h in engine.households.values() if h.role == Role.BUYER]) / num_households
        else:
            buyer_ratio = 0

        self.resilience = min(100, max(0, (
            avg_stored_energy * 0.5 +  # 50% weight to stored energy levels
            trading_activity * 30 +  # 30% weight to trading activity
            (1 - buyer_ratio) * 20  # 20% weight to buyers
        )))

    def get_deltas(self):
        """Calculate hourly changes for all metrics"""
        return {
            "energy": self.energy_traded - self.prev_energy,
            "savings": self.cost_savings - self.prev_savings,
            "co2": self.co2_reduced - self.prev_co2,
            "resilience": self.resilience - self.prev_resilience
        }

    def finalize_hour(self):
        """Store current values as previous for next delta calculation"""
        self.prev_energy = self.energy_traded
        self.prev_savings = self.cost_savings
        self.prev_co2 = self.co2_reduced
        self.prev_resilience = self.resilience

    def get_metrics(self) -> dict:
        """Get metrics in API format"""
        deltas = self.get_deltas()
        return {
            "energy_traded": round(self.energy_traded, 1),
            "cost_savings": round(self.cost_savings, 1),
            "co2_reduced": round(self.co2_reduced, 1),
            "resilience": round(self.resilience),
            "delta_energy": f"+{deltas['energy']:.1f}" if deltas['energy'] >= 0 else f"{deltas['energy']:.1f}",
            "delta_savings": f"+{deltas['savings']:.1f}" if deltas['savings'] >= 0 else f"{deltas['savings']:.1f}",
            "delta_co2": f"+{deltas['co2']:.1f}" if deltas['co2'] >= 0 else f"{deltas['co2']:.1f}",
            "delta_resilience": f"+{deltas['resilience']:.0f}" if deltas['resilience'] >= 0 else f"{deltas['resilience']:.0f}"
        }


class Household:
    """
    Digital twin representation of a household with solar panels and battery storage.
    Simulates energy generation, consumption, and trading behavior.
    """
    
    def __init__(self, 
                 id: str, 
                 solar_capacity: float, 
                 battery_size: float, 
                 demand_pattern: List[float],
                 initial_battery_level: float = 0.5,
                 orientation: str = "south",
                 energy_conscious: bool = False,
                 energy_hoarder: bool = False):
        """
        Initialize a household digital twin.
        
        Args:
            id: Unique identifier for the household
            solar_capacity: Solar panel capacity in kW (2-5 kW typical)
            battery_size: Battery storage capacity in kWh (5-15 kWh typical)
            demand_pattern: 24-hour demand pattern (kWh per hour)
            initial_battery_level: Initial battery charge level (0.0 to 1.0)
            orientation: Solar panel orientation ("south", "east", "west", "north")
            energy_conscious: Flag for households that conserve energy
            energy_hoarder: Flag for households that prefer to store energy
        """
        self.id = id
        self.solar = solar_capacity
        self.battery = battery_size
        self.demand = demand_pattern
        self.role = Role.IDLE
        self.orientation = orientation
        self.energy_conscious = energy_conscious
        self.energy_hoarder = energy_hoarder

        self.orientation_factors = {
            "south": 1.0,
            "east": 0.8,
            "west": 0.8,
            "north": 0.6
        }
        
        # Battery state - now using percentage (0-100%)
        self.stored_energy = initial_battery_level * 100  # 0.0 to 100.0 percentage
        self.battery_efficiency = 1.0  # 100% efficiency (simplified)
        
        # Energy tracking
        self.total_generated = 0.0
        self.total_consumed = 0.0
        self.total_traded = 0.0
        
        # Current hour state
        self.current_hour = 0
        self.current_solar_gen = 0.0
        self.current_demand = 0.0
        self.current_net_energy = 0.0  # For internal calculations only, not for trading
        
        # Trading history
        self.trading_history = []
        
        # Crisis state
        self.active_crisis = None
        
    def simulate_hour(self, hour: int, weather_factor: float, temp_factor: float, humidity: float) -> Dict[str, float]:
        """
        Simulate energy behavior for a specific hour.
        
        Args:
            hour: Hour of day (0-23)
            weather_factor: Weather impact on solar generation (0.0 to 1.0)
            temp_factor: Temperature impact on demand
            humidity: Humidity impact on demand
            
        Returns:
            Dictionary with energy metrics for the hour
        """
        self.current_hour = hour
        
        # Calculate solar generation (peaks at noon)
        base_solar_gen = self.solar * weather_factor * max(0, 1 - abs(12 - hour) / 6)
        base_solar_gen *= self.orientation_factors[self.orientation]
        
        # Apply crisis effects if active
        if self.active_crisis and self.active_crisis.start_hour <= hour <= self.active_crisis.end_hour:
            base_solar_gen *= (1 - self.active_crisis.solar_reduction)
        
        self.current_solar_gen = base_solar_gen
        
        # Get hourly demand and apply weather effects
        self.current_demand = self.demand[hour] * temp_factor
        if humidity > 70:
            self.current_demand *= 1.1
        
        # Apply crisis effects to demand
        if self.active_crisis and self.active_crisis.start_hour <= hour <= self.active_crisis.end_hour:
            self.current_demand *= self.active_crisis.demand_multiplier
        
        # Calculate net energy
        self.current_net_energy = self.current_solar_gen - self.current_demand
        
        # Update battery state
        self._update_battery()
        
        # Update role based on current state
        self._update_role()
        
        # Update totals
        self.total_generated += self.current_solar_gen
        self.total_consumed += self.current_demand
        
        return {
            'hour': hour,
            'solar_generation': self.current_solar_gen,
            'demand': self.current_demand,
            'net_energy': self.current_net_energy,
            'stored_energy': self.stored_energy,  # Now in percentage (0-100)
            'role': self.role.value,
            'weather_factor': weather_factor
        }
    
    def _update_battery(self):
        """Update stored energy based on net energy (100% efficiency)"""
        if self.current_net_energy > 0:
            # Excess energy - store in battery (100% efficiency)
            # Convert kWh to percentage: (kWh / battery_capacity) * 100
            storage_percentage_available = 100.0 - self.stored_energy
            max_storable_kwh = (storage_percentage_available / 100.0) * self.battery
            
            energy_to_store = min(self.current_net_energy, max_storable_kwh)
            storage_percentage_gain = (energy_to_store / self.battery) * 100.0
            
            self.stored_energy += storage_percentage_gain
            self.current_net_energy -= energy_to_store
            
        elif self.current_net_energy < 0:
            # Energy deficit - draw from stored energy (100% efficiency)
            energy_needed = abs(self.current_net_energy)
            available_stored_kwh = (self.stored_energy / 100.0) * self.battery
            
            energy_from_storage = min(energy_needed, available_stored_kwh)
            storage_percentage_loss = (energy_from_storage / self.battery) * 100.0
            
            self.stored_energy -= storage_percentage_loss
            self.current_net_energy += energy_from_storage
    
    def _update_role(self):
        """Update household role based on stored energy only (storage-first trading)"""
        # Seller: Has stored energy above 20% minimum reserve
        if self.stored_energy > 20.0:
            self.role = Role.SELLER
        # Buyer: Has energy deficit AND has storage capacity available
        elif self.current_net_energy < 0 and self.stored_energy < 100.0:
            self.role = Role.BUYER
        # Idle: At minimum reserve OR no energy need/capacity
        else:
            self.role = Role.IDLE
    
    def can_sell_energy(self, amount: float) -> bool:
        """Check if household can sell energy from stored reserves"""
        # Must be seller role and have stored energy above 20% minimum reserve
        if self.role != Role.SELLER or self.stored_energy <= 20.0:
            return False
        
        # Check if we have enough stored energy for the trade
        amount_percentage = (amount / self.battery) * 100.0
        return (self.stored_energy - amount_percentage) >= 20.0
    
    def can_buy_energy(self, amount: float) -> bool:
        """Check if household can buy energy (has storage capacity)"""
        if self.role != Role.BUYER:
            return False
        
        # Check if we have capacity to store the energy
        amount_percentage = (amount / self.battery) * 100.0
        return (self.stored_energy + amount_percentage) <= 100.0
    
    def trade_energy(self, amount: float, price: float, partner_id: str):
        """Execute energy trade using stored energy only (100% efficiency)"""
        amount_percentage = (amount / self.battery) * 100.0
        
        if self.role == Role.SELLER:
            # Sell from stored energy - check if we can maintain 20% reserve
            if (self.stored_energy - amount_percentage) >= 20.0:
                self.stored_energy -= amount_percentage
                self.total_traded += amount
                self.trading_history.append({
                    'hour': self.current_hour, 'type': 'sell', 'amount': amount,
                    'price': price, 'partner': partner_id
                })
                return True
            
        elif self.role == Role.BUYER:
            # Buy into stored energy - check if we have capacity
            if (self.stored_energy + amount_percentage) <= 100.0:
                self.stored_energy += amount_percentage
                self.total_traded += amount
                self.trading_history.append({
                    'hour': self.current_hour, 'type': 'buy', 'amount': amount,
                    'price': price, 'partner': partner_id
                })
                return True
            
        return False
    
    def trigger_crisis(self, crisis: CrisisEvent):
        """Apply crisis effects to the household"""
        self.active_crisis = crisis
    
    def clear_crisis(self):
        """Clear active crisis effects"""
        self.active_crisis = None
    
    def get_status(self) -> Dict:
        """Get current household status"""
        return {
            'id': self.id,
            'role': self.role.value,
            'stored_energy': self.stored_energy,  # Now in percentage (0-100)
            'current_net_energy': self.current_net_energy,
            'total_generated': self.total_generated,
            'total_consumed': self.total_consumed,
            'total_traded': self.total_traded,
            'active_crisis': self.active_crisis is not None
        }


class SimulationClock:
    """Manages the simulation's time, advancing in discrete steps."""
    def __init__(self, start_date="2025-06-23 00:00:00", speed_factor=3600):
        """
        Initializes the clock.
        
        Args:
            start_date (str): The simulation's starting date and time.
            speed_factor (int): How many simulation seconds pass for each real-world second.
                                Default is 3600 (1 simulated hour per real second).
        """
        self.current_time = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        self.step_interval = timedelta(seconds=speed_factor)

    def tick(self):
        """Advances the simulation time by one step."""
        self.current_time += self.step_interval
        return self.current_time


class SimulationEngine:
    """
    Main simulation engine that manages multiple households and coordinates trading.
    """
    
    def __init__(self, weather_fetcher=None):
        self.households: Dict[str, Household] = {}
        self.clock = SimulationClock()
        self.current_hour = self.clock.current_time.hour
        self.crisis_events = []
        self.simulation_log = []
        self.trading_system = None  # Will be initialized after households are added
        self.weather_fetcher = weather_fetcher
        self.weather_cache = {}
        self.metrics = MetricsCollector()
        
    def add_household(self, household: Household):
        """Add a household to the simulation"""
        self.households[household.id] = household
    
    def get_weather_for_hour(self, hour_idx):
        """Get weather data with caching mechanism"""
        if hour_idx in self.weather_cache:
            return self.weather_cache[hour_idx]
        
        if self.weather_fetcher:
            forecast = self.weather_fetcher.get_hourly_forecast()
            if forecast and hour_idx < len(forecast):
                self.weather_cache = {i: f for i, f in enumerate(forecast)}
                return forecast[hour_idx]
        
        # Fallback to random generation
        return self.generate_fallback_weather(hour_idx % 24)

    def generate_fallback_weather(self, hour):
        """Generate more balanced weather conditions for better trading opportunities."""
        # Temperature (peaks in the afternoon)
        temp_amplitude = 5  # Reduced variation for more stable conditions
        temp_mean = 22
        # Peaks around 3 PM (hour 15)
        temp = temp_mean + temp_amplitude * np.sin(2 * np.pi * (hour - 9) / 24)
        temp += random.uniform(-0.5, 0.5)  # Less noise

        # Solar radiation (peaks at 3pm) - More moderate conditions
        # Using a cosine function to model daylight hours (approx 6am to 6pm)
        if 6 <= hour <= 18:
            solar_radiation = max(200, np.cos((hour - 12) * np.pi / 15) * 800)  # More moderate range
            solar_radiation = max(200, solar_radiation + random.uniform(-30, 30))  # Less variation
        else:
            solar_radiation = 0

        # Cloud cover - More moderate and predictable
        clouds_base = 25  # Reduced base cloud cover
        clouds_variation = 15  # Less extreme variation
        # Some randomness but keep it moderate
        clouds = clouds_base + random.uniform(-clouds_variation, clouds_variation)
        clouds = max(10, min(60, clouds))  # Constrain to moderate range

        # Humidity (more stable)
        humidity = 55 + 15 * np.sin(2 * np.pi * (hour - 6) / 24) + random.uniform(-3, 3)
        humidity = max(40, min(80, humidity))

        return {
            'clouds': float(clouds),
            'temp': float(temp),
            'solar_radiation': float(solar_radiation),
            'humidity': float(humidity)
        }
    
    def trigger_heatwave(self) -> CrisisEvent:
        """Trigger a heatwave crisis event"""
        crisis = CrisisEvent(
            demand_multiplier=random.uniform(1.5, 1.8),
            solar_reduction=random.uniform(0.3, 0.5),
            duration=random.randint(3, 6),
            start_hour=self.current_hour,
            end_hour=min(23, self.current_hour + random.randint(3, 6))
        )
        
        # Apply to all households
        for household in self.households.values():
            household.trigger_crisis(crisis)
        
        self.crisis_events.append(crisis)
        return crisis
    
    def initialize_trading_system(self):
        """Initialize the trading system after households are added"""
        self.trading_system = TradingSystem(self)

    def simulate_step(self) -> Dict:
        """Simulate one hour for all households"""
        current_time = self.clock.tick()
        self.current_hour = current_time.hour
        
        raw_weather = self.get_weather_for_hour(self.current_hour)
        
        # Calculate weather factors - More balanced for trading
        cloud_impact_factor = random.uniform(0.6, 0.8)  # Reduced cloud impact
        weather_factor = 1 - (raw_weather['clouds'] / 100) * cloud_impact_factor
        temp_factor = 1 + abs(raw_weather['temp'] - 22) * 0.015  # Less temperature impact
        radiation_boost = min(1.1, raw_weather.get('solar_radiation', 600) / 600)  # More moderate boost
        
        # Combine factors - ensure minimum viable generation
        effective_weather = max(0.4, weather_factor * radiation_boost)  # Minimum 40% generation
        humidity = raw_weather['humidity']

        step_results = {
            'hour': self.current_hour,
            'weather_factor': effective_weather,
            'temp_factor': temp_factor,
            'humidity': humidity,
            'raw_weather': raw_weather,
            'households': {}
        }
        
        # Simulate each household
        for household_id, household in self.households.items():
            result = household.simulate_hour(
                hour=self.current_hour, 
                weather_factor=effective_weather, 
                temp_factor=temp_factor,
                humidity=humidity
            )
            step_results['households'][household_id] = result
        
        # Smart demand adjustment for better market balance
        community_net = sum(h.current_net_energy for h in self.households.values())
        sellers = sum(1 for h in self.households.values() if h.role == Role.SELLER)
        buyers = sum(1 for h in self.households.values() if h.role == Role.BUYER)
        
        # Encourage trading by adjusting demand patterns when market is imbalanced
        if sellers == 0 and buyers > 0:  # Only buyers - reduce some demand
            high_demand_households = sorted(self.households.values(), key=lambda h: h.current_demand, reverse=True)[:2]
            for household in high_demand_households:
                if household.energy_conscious:
                    original_demand = household.current_demand
                    household.current_demand *= 0.85
                    demand_reduction = original_demand - household.current_demand
                    household.current_net_energy += demand_reduction
                    household._update_battery()
                    household._update_role()
                    step_results['households'][household.id].update({
                        'demand': household.current_demand,
                        'net_energy': household.current_net_energy,
                        'stored_energy': household.stored_energy,
                        'role': household.role.value
                    })
        
        elif buyers == 0 and sellers > 0:  # Only sellers - increase some demand
            low_demand_households = sorted(self.households.values(), key=lambda h: h.current_demand)[:2]
            for household in low_demand_households:
                if not household.energy_hoarder:  # Don't force hoarders to use more
                    original_demand = household.current_demand
                    household.current_demand *= 1.1
                    demand_increase = household.current_demand - original_demand
                    household.current_net_energy -= demand_increase
                    household._update_battery()
                    household._update_role()
                    step_results['households'][household.id].update({
                        'demand': household.current_demand,
                        'net_energy': household.current_net_energy,
                        'stored_energy': household.stored_energy,
                        'role': household.role.value
                    })

        # After simulating each household, run trading
        trades_this_hour = []
        if self.trading_system:
            trades_this_hour = self.trading_system.match_trades(self.current_hour)
        
        # Add trades to step results for external logging
        step_results['trades'] = trades_this_hour
        
        # Update metrics collector
        self.metrics.update(self, trades_this_hour)
        self.metrics.finalize_hour()
        step_results['metrics'] = self.metrics.get_metrics()
        
        # Clear expired crises
        for household in self.households.values():
            if (household.active_crisis and 
                self.current_hour > household.active_crisis.end_hour):
                household.clear_crisis()
        
        self.simulation_log.append(step_results)
        
        return step_results
    
    def simulate_period(self, hours: int) -> List[Dict]:
        """Simulate for a specified number of hours"""
        results = []
        for _ in range(hours):
            result = self.simulate_step()
            if 'error' in result:
                break
            results.append(result)
        return results
    
    def get_community_status(self) -> Dict:
        """Get overall community energy status"""
        total_generated = sum(h.total_generated for h in self.households.values())
        total_consumed = sum(h.total_consumed for h in self.households.values())
        total_traded = sum(h.total_traded for h in self.households.values())
        
        sellers = sum(1 for h in self.households.values() if h.role == Role.SELLER)
        buyers = sum(1 for h in self.households.values() if h.role == Role.BUYER)
        idle = sum(1 for h in self.households.values() if h.role == Role.IDLE)
        
        return {
            'total_households': len(self.households),
            'total_generated': total_generated,
            'total_consumed': total_consumed,
            'total_traded': total_traded,
            'sellers': sellers,
            'buyers': buyers,
            'idle': idle,
            'current_hour': self.current_hour
        }


# Utility functions for creating realistic demand patterns
def generate_demand_pattern(household_type: str = "typical") -> List[float]:
    """
    Generate realistic 24-hour demand patterns for different household types.
    
    Args:
        household_type: Type of household ("typical", "high_usage", "low_usage", "night_shift")
        
    Returns:
        List of 24 hourly demand values in kWh
    """
    if household_type == "typical":
        # Typical household with morning and evening peaks
        base_pattern = [
            0.8, 0.6, 0.5, 0.4, 0.4, 0.5,  # 0-5 AM
            0.8, 1.2, 1.0, 0.8, 0.7, 0.6,  # 6-11 AM
            0.8, 0.9, 0.8, 0.7, 0.8, 1.2,  # 12-5 PM
            1.5, 1.8, 1.6, 1.2, 1.0, 0.9   # 6-11 PM
        ]
    elif household_type == "high_usage":
        # High energy consumption household
        base_pattern = [
            1.2, 0.9, 0.7, 0.6, 0.6, 0.7,
            1.2, 1.8, 1.5, 1.2, 1.0, 0.9,
            1.2, 1.3, 1.2, 1.0, 1.2, 1.8,
            2.2, 2.6, 2.4, 1.8, 1.5, 1.3
        ]
    elif household_type == "low_usage":
        # Energy-efficient household
        base_pattern = [
            0.4, 0.3, 0.2, 0.2, 0.2, 0.3,
            0.4, 0.6, 0.5, 0.4, 0.3, 0.3,
            0.4, 0.5, 0.4, 0.3, 0.4, 0.6,
            0.7, 0.9, 0.8, 0.6, 0.5, 0.4
        ]
    elif household_type == "night_shift":
        # Household with night shift workers
        base_pattern = [
            1.0, 1.2, 1.0, 0.8, 0.6, 0.4,
            0.3, 0.4, 0.6, 0.8, 0.7, 0.6,
            0.8, 0.9, 0.8, 0.7, 0.8, 1.0,
            1.2, 1.4, 1.2, 1.0, 0.9, 0.8
        ]
    else:
        base_pattern = [0.8] * 24  # Default pattern
    
    # Add some randomness to make each household unique
    pattern = [max(0.1, base + random.uniform(-0.2, 0.2)) for base in base_pattern]
    return pattern


def create_sample_community() -> SimulationEngine:
    """Create a balanced community optimized for trading"""
    engine = SimulationEngine()
    
    # Create households with more diverse and balanced characteristics
    # Mix of high-solar/low-demand and low-solar/high-demand households for better trading
    households_data = [
        # High solar producers (potential sellers)
        ("H001", 5.0, 8.0, "low_usage", "south", False, False),     # High solar, low demand
        ("H002", 4.8, 9.0, "typical", "south", False, True),       # High solar, typical demand, hoarder
        ("H003", 4.5, 7.0, "low_usage", "east", True, False),      # Good solar, energy conscious
        
        # Medium solar households (flexible traders)
        ("H004", 3.2, 12.0, "typical", "west", False, False),     # Medium solar, big battery
        ("H005", 3.0, 11.0, "night_shift", "south", False, False), # Medium solar, shifted demand
        
        # Lower solar/higher demand (potential buyers)
        ("H006", 2.0, 15.0, "high_usage", "north", False, False),  # Low solar, high demand, big battery
        ("H007", 2.5, 10.0, "high_usage", "west", False, False),   # Low solar, high demand
        ("H008", 1.8, 12.0, "typical", "north", True, False),     # Low solar, energy conscious
        
        # Add more diversity
        ("H009", 3.8, 6.0, "low_usage", "east", False, True),      # Medium-high solar, small battery, hoarder
        ("H010", 2.2, 14.0, "night_shift", "west", False, False),  # Low solar, night shift, big battery
    ]
    
    for household_id, solar_capacity, battery_size, household_type, orientation, energy_conscious, energy_hoarder in households_data:
        demand_pattern = generate_demand_pattern(household_type)
        household = Household(
            household_id, 
            solar_capacity, 
            battery_size, 
            demand_pattern,
            orientation=orientation,
            energy_conscious=energy_conscious,
            energy_hoarder=energy_hoarder
        )
        engine.add_household(household)
    
    # Weather is now handled by the simulation engine dynamically
    
    return engine


# --- Trading System ---
class TradingSystem:
    def __init__(self, simulation_engine):
        self.engine = simulation_engine
        self.transaction_history = []
        self.ledger_file = "trades.csv"
        self._initialize_ledger()

    def _initialize_ledger(self):
        """Initialize the transaction ledger file if it doesn't exist"""
        if not os.path.exists(self.ledger_file):
            df = pd.DataFrame(columns=["time", "hour", "seller_id", "buyer_id", "kwh", "price", "total"])
            df.to_csv(self.ledger_file, index=False)

    def match_trades(self, hour):
        """Enhanced matching algorithm optimized for more trading opportunities"""
        executed_trades = []
        households = list(self.engine.households.values())
        
        # Get active participants based on storage-first criteria
        sellers = [h for h in households if h.role == Role.SELLER and h.stored_energy > 20.0]
        buyers = [h for h in households if h.role == Role.BUYER and h.stored_energy < 100.0]
        
        if not sellers or not buyers:
            return executed_trades
        
        # Sort by urgency and capacity
        sellers.sort(key=lambda x: x.stored_energy, reverse=True)  # High stored energy first
        buyers.sort(key=lambda x: (x.stored_energy, -x.current_net_energy))  # Low stored energy, high deficit first
        
        # Dynamic pricing based on supply/demand ratio (using available stored energy)
        supply = sum((h.stored_energy - 20.0) / 100.0 * h.battery for h in sellers)  # Available kWh above reserve
        demand = sum(abs(min(0, h.current_net_energy)) for h in buyers)  # Energy deficit in kWh
        
        if demand > 0:
            supply_demand_ratio = supply / demand
            if supply_demand_ratio > 1.5:
                price = 0.10  # Buyer's market
            elif supply_demand_ratio > 0.8:
                price = 0.15  # Balanced market
            else:
                price = 0.20  # Seller's market
        else:
            price = 0.15  # Default price
        
        # Match trades with multiple rounds for better satisfaction
        max_rounds = 3
        for round_num in range(max_rounds):
            trades_this_round = []
            
            for buyer in buyers[:]:
                if buyer.current_net_energy >= -0.05:  # Buyer satisfied
                    buyers.remove(buyer)
                    continue
                    
                for seller in sellers[:]:
                    if seller.stored_energy <= 20.0:  # Seller at minimum reserve
                        sellers.remove(seller)
                        continue
                        
                    # Calculate trade amount based on stored energy and need
                    buyer_need = abs(buyer.current_net_energy)
                    # Available stored energy above 20% reserve (in kWh)
                    seller_available_kwh = ((seller.stored_energy - 20.0) / 100.0) * seller.battery
                    
                    # Scale trade size based on storage levels and round
                    if round_num == 0:  # First round - larger trades
                        max_trade = min(
                            seller_available_kwh * 0.6,  # Up to 60% of available stored energy
                            buyer_need * 0.8,            # Up to 80% of need
                            2.0                           # Max 2 kWh per trade
                        )
                    else:  # Later rounds - smaller trades
                        max_trade = min(
                            seller_available_kwh * 0.4,
                            buyer_need * 0.6,
                            1.0
                        )
                    
                    # Ensure meaningful trade
                    if max_trade < 0.05:
                        continue
                        
                    # Execute trade
                    try:
                        success = self._execute_trade(seller, buyer, max_trade, price, hour)
                        if success:
                            trades_this_round.append({
                                "from": seller.id,
                                "to": buyer.id,
                                "kwh": round(max_trade, 2),
                                "price": round(max_trade * price, 2)
                            })
                            break  # Move to next buyer
                    except Exception as e:
                        print(f"Trade error: {e}")
            
            executed_trades.extend(trades_this_round)
            
            # If no trades happened this round, stop
            if not trades_this_round:
                break
        
        return executed_trades

    def _execute_trade(self, seller, buyer, kwh, price, hour):
        """
        Execute a trade between a seller and a buyer.
        """
        seller_success = seller.trade_energy(kwh, price, buyer.id)
        buyer_success = buyer.trade_energy(kwh, price, seller.id)
        if seller_success and buyer_success:
            self.log_transaction(seller, buyer, kwh, price, hour)
            return True
        return False

    def log_transaction(self, seller, buyer, kwh, price, hour):
        """
        Log a transaction to the ledger.
        """
        timestamp = datetime.now()
        total_price = kwh * price
        transaction = {
            "time": timestamp,
            "hour": hour,
            "seller_id": seller.id,
            "buyer_id": buyer.id,
            "kwh": kwh,
            "price": price,
            "total": total_price
        }
        self.transaction_history.append(transaction)
        df = pd.DataFrame([transaction])
        df.to_csv(self.ledger_file, mode="a", header=False, index=False)
        return transaction


if __name__ == "__main__":
    print("Starting SolarShare Real-time Simulation...")

    # Create simulation engine
    engine = create_sample_community()
    engine.initialize_trading_system()

    # Initialize/clear the JSON log file
    with open("household_state.json", "w") as f:
        json.dump([], f, indent=2)

    # Real-time simulation loop
    try:
        while True:
            # Simulate one hour
            result = engine.simulate_step()
            
            # Format data for JSON output
            timestamp = engine.clock.current_time.isoformat() + "Z"
            
            households_data = []
            for hid, hdata in result['households'].items():
                households_data.append({
                    "id": hid,
                    "role": hdata['role'],
                    "battery": int(hdata['stored_energy']),  # Already in percentage
                    "solar": hdata['solar_generation'],
                    "demand": hdata['demand'],
                    "net_energy": hdata['net_energy']
                })

            # The new format for household_state.json
            output_data = {
                "timestamp": timestamp,
                "households": households_data,
                "trades": result.get('trades', []),
                "weather": result['raw_weather'],
                "metrics": result.get('metrics', {})
            }

            # Read current log, append new entry, and write back
            with open("household_state.json", "r+") as f:
                log_data = json.load(f)
                log_data.append(output_data)
                f.seek(0)
                json.dump(log_data, f, indent=2)

            # Log to terminal
            print(f"--- {timestamp} ---")
            raw_weather = result['raw_weather']
            print(f"Weather: {raw_weather['temp']:.1f}°C, {raw_weather['clouds']:.0f}% clouds, Solar Rad: {raw_weather['solar_radiation']:.0f}")
            
            for h in households_data:
                print(f"  ID: {h['id']}, Role: {h['role']:<6}, Battery: {h['battery']:>3}%, Solar: {h['solar']:.2f}, Demand: {h['demand']:.2f}, Net: {h['net_energy']:.2f}")

            if output_data['trades']:
                print("Trades this hour:")
                for t in output_data['trades']:
                    print(f"  {t['from']} -> {t['to']}: {t['kwh']:.2f} kWh @ ${t['price']:.2f}")
            
            # Add summary statistics
            status = engine.get_community_status()
            print(f"Sellers: {status['sellers']} | Buyers: {status['buyers']} | Idle: {status['idle']}")
            print(f"Community Net: {status['total_generated'] - status['total_consumed']:.2f} kWh")

            print("-" * (len(timestamp) + 6))

            # Wait for 1 second to simulate 1 hour passing
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nSimulation stopped by user.")
        # Print summary
        status = engine.get_community_status()
        print(f"\nFinal Community Status:")
        print(f"Total energy generated: {status['total_generated']:.2f} kWh")
        print(f"Total energy consumed: {status['total_consumed']:.2f} kWh")
        print(f"Total energy traded: {status['total_traded']:.2f} kWh")
