import random
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import time
import os
import pandas as pd
from datetime import datetime
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
                 initial_battery_level: float = 0.5):
        """
        Initialize a household digital twin.
        
        Args:
            id: Unique identifier for the household
            solar_capacity: Solar panel capacity in kW (2-5 kW typical)
            battery_size: Battery storage capacity in kWh (5-15 kWh typical)
            demand_pattern: 24-hour demand pattern (kWh per hour)
            initial_battery_level: Initial battery charge level (0.0 to 1.0)
        """
        self.id = id
        self.solar = solar_capacity
        self.battery = battery_size
        self.demand = demand_pattern
        self.role = Role.IDLE
        
        # Battery state
        self.battery_level = initial_battery_level  # 0.0 to 1.0
        self.battery_efficiency = 0.95  # 95% round-trip efficiency
        
        # Energy tracking
        self.total_generated = 0.0
        self.total_consumed = 0.0
        self.total_traded = 0.0
        
        # Current hour state
        self.current_hour = 0
        self.current_solar_gen = 0.0
        self.current_demand = 0.0
        self.current_net_energy = 0.0
        
        # Trading history
        self.trading_history = []
        
        # Crisis state
        self.active_crisis = None
        
    def simulate_hour(self, hour: int, weather_factor: float = 1.0) -> Dict[str, float]:
        """
        Simulate energy behavior for a specific hour.
        
        Args:
            hour: Hour of day (0-23)
            weather_factor: Weather impact on solar generation (0.0 to 1.0)
            
        Returns:
            Dictionary with energy metrics for the hour
        """
        self.current_hour = hour
        
        # Calculate solar generation (peaks at noon)
        base_solar_gen = self.solar * weather_factor * max(0, 1 - abs(12 - hour) / 6)
        
        # Apply crisis effects if active
        if self.active_crisis and self.active_crisis.start_hour <= hour <= self.active_crisis.end_hour:
            base_solar_gen *= (1 - self.active_crisis.solar_reduction)
        
        self.current_solar_gen = base_solar_gen
        
        # Get hourly demand
        self.current_demand = self.demand[hour]
        
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
            'battery_level': self.battery_level,
            'role': self.role.value,
            'weather_factor': weather_factor
        }
    
    def _update_battery(self):
        """Update battery state based on net energy"""
        if self.current_net_energy > 0:
            # Excess energy - charge battery
            charge_amount = min(
                self.current_net_energy * self.battery_efficiency,
                (1.0 - self.battery_level) * self.battery
            )
            self.battery_level += charge_amount / self.battery
            self.current_net_energy -= charge_amount / self.battery_efficiency
            
        elif self.current_net_energy < 0:
            # Energy deficit - discharge battery
            discharge_amount = min(
                abs(self.current_net_energy),
                self.battery_level * self.battery * self.battery_efficiency
            )
            self.battery_level -= discharge_amount / (self.battery * self.battery_efficiency)
            self.current_net_energy += discharge_amount
    
    def _update_role(self):
        """Update household role based on battery level and current energy state"""
        if self.battery_level > 0.8 and self.current_net_energy > 0:
            self.role = Role.SELLER
        elif self.battery_level < 0.2 and self.current_net_energy < 0:
            self.role = Role.BUYER
        else:
            self.role = Role.IDLE
    
    def can_sell_energy(self, amount: float) -> bool:
        """Check if household can sell specified amount of energy"""
        return (self.role == Role.SELLER and 
                self.current_net_energy >= amount and
                self.battery_level > 0.1)  # Keep some reserve
    
    def can_buy_energy(self, amount: float) -> bool:
        """Check if household can buy specified amount of energy"""
        return (self.role == Role.BUYER and
                self.battery_level < 0.9)  # Don't overcharge
    
    def trade_energy(self, amount: float, price: float, partner_id: str):
        """Execute energy trade with another household"""
        if self.role == Role.SELLER and self.can_sell_energy(amount):
            self.current_net_energy -= amount
            self.total_traded += amount
            self.trading_history.append({
                'hour': self.current_hour,
                'type': 'sell',
                'amount': amount,
                'price': price,
                'partner': partner_id
            })
            return True
            
        elif self.role == Role.BUYER and self.can_buy_energy(amount):
            self.current_net_energy += amount
            self.total_traded -= amount
            self.trading_history.append({
                'hour': self.current_hour,
                'type': 'buy',
                'amount': amount,
                'price': price,
                'partner': partner_id
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
            'battery_level': self.battery_level,
            'current_net_energy': self.current_net_energy,
            'total_generated': self.total_generated,
            'total_consumed': self.total_consumed,
            'total_traded': self.total_traded,
            'active_crisis': self.active_crisis is not None
        }


class SimulationEngine:
    """
    Main simulation engine that manages multiple households and coordinates trading.
    """
    
    def __init__(self):
        self.households: Dict[str, Household] = {}
        self.current_hour = 0
        self.weather_conditions = []
        self.crisis_events = []
        self.simulation_log = []
        self.trading_system = None  # Will be initialized after households are added
        
    def add_household(self, household: Household):
        """Add a household to the simulation"""
        self.households[household.id] = household
    
    def generate_weather_conditions(self, days: int = 1) -> List[float]:
        """Generate weather conditions for simulation period"""
        weather = []
        for day in range(days):
            for hour in range(24):
                # Base weather pattern with some randomness
                base_weather = 0.8 + 0.2 * np.sin(2 * np.pi * (hour - 6) / 24)
                # Add some daily variation
                daily_variation = random.uniform(0.9, 1.1)
                # Add some hourly noise
                hourly_noise = random.uniform(0.95, 1.05)
                
                weather_factor = base_weather * daily_variation * hourly_noise
                weather_factor = max(0.0, min(1.0, weather_factor))  # Clamp to [0, 1]
                weather.append(weather_factor)
        
        self.weather_conditions = weather
        return weather
    
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
        if self.current_hour >= len(self.weather_conditions):
            return {'error': 'Simulation period exceeded'}
        
        weather_factor = self.weather_conditions[self.current_hour]
        step_results = {
            'hour': self.current_hour,
            'weather_factor': weather_factor,
            'households': {}
        }
        
        # Simulate each household
        for household_id, household in self.households.items():
            result = household.simulate_hour(self.current_hour, weather_factor)
            step_results['households'][household_id] = result
        
        # After simulating each household, run trading
        if self.trading_system:
            self.trading_system.match_trades(self.current_hour)
        
        # Clear expired crises
        for household in self.households.values():
            if (household.active_crisis and 
                self.current_hour > household.active_crisis.end_hour):
                household.clear_crisis()
        
        self.simulation_log.append(step_results)
        self.current_hour += 1
        
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
    """Create a sample community with various household types"""
    engine = SimulationEngine()
    
    # Create households with different characteristics
    households_data = [
        ("H001", 3.5, 10.0, "typical"),
        ("H002", 4.2, 12.0, "high_usage"),
        ("H003", 2.8, 8.0, "low_usage"),
        ("H004", 3.0, 10.0, "night_shift"),
        ("H005", 4.5, 15.0, "typical"),
        ("H006", 2.5, 7.0, "low_usage"),
        ("H007", 3.8, 11.0, "high_usage"),
        ("H008", 3.2, 9.0, "typical"),
    ]
    
    for household_id, solar_capacity, battery_size, household_type in households_data:
        demand_pattern = generate_demand_pattern(household_type)
        household = Household(household_id, solar_capacity, battery_size, demand_pattern)
        engine.add_household(household)
    
    # Generate weather conditions for 3 days
    engine.generate_weather_conditions(days=3)
    
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
        """
        Match sellers with buyers and execute trades.
        Buyers are sorted by priority and battery level.
        """
        households = list(self.engine.households.values())
        sellers = [h for h in households if h.role == Role.SELLER]
        buyers = [h for h in households if h.role == Role.BUYER]
        buyers.sort(key=lambda x: x.battery_level)
        for buyer in buyers:
            for seller in sellers:
                surplus = seller.current_net_energy
                deficit = abs(buyer.current_net_energy)
                if surplus <= 0 or deficit <= 0:
                    continue
                kwh = min(surplus, deficit)
                price = 0.15  # $0.15 per kWh
                try:
                    success = self._execute_trade(seller, buyer, kwh, price, hour)
                except Exception as e:
                    print(f"Trade error: {e}")
                    continue
                if not success:
                    continue

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
    # Example usage
    print("Creating SolarShare Digital Twin Simulation Engine...")
    
    # Create sample community
    engine = create_sample_community()
    
    # Simulate for 24 hours
    print(f"\nSimulating 24 hours for {len(engine.households)} households...")
    results = []
    for hour in range(24):
        result = engine.simulate_step()
        results.append(result)
        print(f"\nHour {hour}:")
        for hid, hdata in result['households'].items():
            print(f"  {hid}: Battery={hdata['battery_level']:.2f}, Net={hdata['net_energy']:.2f}, Role={hdata['role']}")
        # Write household_state.json for backend
        household_state = {
            "hour": hour,
            "households": {
                hid: {
                    "battery_level": hdata["battery_level"],
                    "net_energy": hdata["net_energy"],
                    "role": hdata["role"],
                    "solar_generation": hdata["solar_generation"],
                    "demand": hdata["demand"]
                } for hid, hdata in result["households"].items()
            }
        }
        with open("household_state.json", "w") as f:
            json.dump(household_state, f, indent=2)
    
    # Print summary
    print(f"\nSimulation completed!")
    print(f"Total households: {len(engine.households)}")
    print(f"Simulation period: 24 hours")
    
    # Show final community status
    status = engine.get_community_status()
    print(f"\nFinal Community Status:")
    print(f"Total energy generated: {status['total_generated']:.2f} kWh")
    print(f"Total energy consumed: {status['total_consumed']:.2f} kWh")
    print(f"Total energy traded: {status['total_traded']:.2f} kWh")
    print(f"Current roles - Sellers: {status['sellers']}, Buyers: {status['buyers']}, Idle: {status['idle']}")
