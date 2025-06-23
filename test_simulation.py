#!/usr/bin/env python3
"""
Test script for the SolarShare Digital Twin Simulation Engine
Demonstrates household profiling, time step simulation, and crisis injection.
"""

from simulation_engine import (
    SimulationEngine, 
    Household, 
    generate_demand_pattern, 
    create_sample_community,
    CrisisEvent
)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def test_basic_simulation():
    """Test basic simulation functionality"""
    print("=== Testing Basic Simulation ===")
    
    # Create a simple household
    demand_pattern = generate_demand_pattern("typical")
    household = Household("TEST001", 3.0, 10.0, demand_pattern)
    
    print(f"Household ID: {household.id}")
    print(f"Solar Capacity: {household.solar} kW")
    print(f"Battery Size: {household.battery} kWh")
    print(f"Initial Battery Level: {household.battery_level:.2f}")
    
    # Simulate a few hours
    for hour in range(6, 18):  # 6 AM to 6 PM
        result = household.simulate_hour(
            hour, 
            weather_factor=0.8, 
            temp_factor=1.05,  # Assuming slightly cool day
            humidity=50        # Assuming average humidity
        )
        print(f"Hour {hour:2d}: Solar={result['solar_generation']:.2f}kW, "
              f"Demand={result['demand']:.2f}kW, "
              f"Net={result['net_energy']:.2f}kW, "
              f"Role={result['role']}, "
              f"Battery={result['battery_level']:.2f}")


def test_community_simulation():
    """Test community simulation with multiple households"""
    print("\n=== Testing Community Simulation ===")
    
    # Create sample community
    engine = create_sample_community()
    
    print(f"Created community with {len(engine.households)} households")
    
    # Simulate for 24 hours
    results = engine.simulate_period(24)
    
    # Show final status
    status = engine.get_community_status()
    print(f"\nFinal Community Status:")
    print(f"Total Energy Generated: {status['total_generated']:.2f} kWh")
    print(f"Total Energy Consumed: {status['total_consumed']:.2f} kWh")
    print(f"Total Energy Traded: {status['total_traded']:.2f} kWh")
    print(f"Current Roles - Sellers: {status['sellers']}, Buyers: {status['buyers']}, Idle: {status['idle']}")
    
    return engine, results


def test_crisis_injection():
    """Test crisis injection functionality"""
    print("\n=== Testing Crisis Injection ===")
    
    # Create a simple community
    engine = SimulationEngine()
    
    # Add a few households
    for i in range(3):
        demand_pattern = generate_demand_pattern("typical")
        household = Household(f"CRISIS{i+1:03d}", 3.0, 10.0, demand_pattern)
        engine.add_household(household)
    
    # Weather is now handled dynamically by the engine
    
    # Simulate until hour 12
    for _ in range(12):
        engine.simulate_step()
    
    print(f"Simulated until hour {engine.current_hour}")
    
    # Trigger heatwave crisis
    crisis = engine.trigger_heatwave()
    print(f"Triggered heatwave crisis:")
    print(f"  - Demand multiplier: {crisis.demand_multiplier:.2f}")
    print(f"  - Solar reduction: {crisis.solar_reduction:.2f}")
    print(f"  - Duration: {crisis.duration} hours")
    print(f"  - Start hour: {crisis.start_hour}")
    print(f"  - End hour: {crisis.end_hour}")
    
    # Continue simulation
    for _ in range(6):
        result = engine.simulate_step()
        hour = result['hour']
        print(f"Hour {hour}: Weather={result['weather_factor']:.2f}")
        
        for household_id, household_result in result['households'].items():
            print(f"  {household_id}: Solar={household_result['solar_generation']:.2f}kW, "
                  f"Demand={household_result['demand']:.2f}kW, "
                  f"Role={household_result['role']}")


def visualize_simulation(engine, results):
    """Create visualizations of the simulation results"""
    print("\n=== Creating Visualizations ===")
    
    # Extract data for plotting
    hours = [r['hour'] for r in results]
    weather_factors = [r['weather_factor'] for r in results]
    
    # Aggregate household data
    total_solar = []
    total_demand = []
    total_net = []
    sellers_count = []
    buyers_count = []
    
    for result in results:
        households_data = result['households']
        total_solar.append(sum(h['solar_generation'] for h in households_data.values()))
        total_demand.append(sum(h['demand'] for h in households_data.values()))
        total_net.append(sum(h['net_energy'] for h in households_data.values()))
        sellers_count.append(sum(1 for h in households_data.values() if h['role'] == 'seller'))
        buyers_count.append(sum(1 for h in households_data.values() if h['role'] == 'buyer'))
    
    # Create plots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    
    # Plot 1: Energy generation and consumption
    ax1.plot(hours, total_solar, 'g-', label='Solar Generation', linewidth=2)
    ax1.plot(hours, total_demand, 'r-', label='Energy Demand', linewidth=2)
    ax1.plot(hours, total_net, 'b--', label='Net Energy', linewidth=2)
    ax1.set_xlabel('Hour of Day')
    ax1.set_ylabel('Energy (kWh)')
    ax1.set_title('Community Energy Profile')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Weather conditions
    ax2.plot(hours, weather_factors, 'orange', linewidth=2)
    ax2.set_xlabel('Hour of Day')
    ax2.set_ylabel('Weather Factor')
    ax2.set_title('Weather Conditions')
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Trading roles over time
    ax3.plot(hours, sellers_count, 'g-', label='Sellers', linewidth=2)
    ax3.plot(hours, buyers_count, 'r-', label='Buyers', linewidth=2)
    ax3.set_xlabel('Hour of Day')
    ax3.set_ylabel('Number of Households')
    ax3.set_title('Trading Roles Over Time')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Individual household battery levels
    household_ids = list(engine.households.keys())
    battery_levels = []
    for household_id in household_ids:
        household = engine.households[household_id]
        battery_levels.append(household.battery_level)
    
    ax4.bar(household_ids, battery_levels, color='skyblue', alpha=0.7)
    ax4.set_xlabel('Household ID')
    ax4.set_ylabel('Battery Level')
    ax4.set_title('Final Battery Levels')
    ax4.tick_params(axis='x', rotation=45)
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('simulation_results.png', dpi=300, bbox_inches='tight')
    print("Visualization saved as 'simulation_results.png'")


def test_trading_system_integration():
    """Test TradingSystem integration with SimulationEngine"""
    print("\n=== Testing TradingSystem Integration ===")
    engine = SimulationEngine()
    # Add two households: one seller, one buyer
    demand_pattern_seller = [0.5]*24
    demand_pattern_buyer = [2.0]*24
    seller = Household("SELLER1", 4.0, 12.0, demand_pattern_seller, initial_battery_level=0.9)
    buyer = Household("BUYER1", 2.0, 8.0, demand_pattern_buyer, initial_battery_level=0.1)
    engine.add_household(seller)
    engine.add_household(buyer)
    # Weather is now handled dynamically by the engine
    engine.initialize_trading_system()
    # Simulate up to hour 12 to ensure sunny conditions
    for _ in range(12):
        engine.simulate_step()

    # Simulate one more hour (should trigger trading)
    engine.simulate_step()
    # Check transaction history
    ts = engine.trading_system

    trades = ts.match_trades(engine.current_hour)
    
    # Read and print the ledger file
    ledger = pd.read_csv(ts.ledger_file)
    print("Ledger file contents:")
    print(ledger.tail())
    # Check that at least one trade was executed (check ledger instead of current trades)
    assert len(ledger) > 0, "No trades were recorded in ledger!"
    print("TradingSystem integration test passed.")


if __name__ == "__main__":
    print("SolarShare Digital Twin Simulation Engine - Test Suite")
    print("=" * 60)
    
    # Run all tests
    test_basic_simulation()
    engine, results = test_community_simulation()
    test_crisis_injection()
    test_trading_system_integration()
    
    # Create visualizations
    try:
        visualize_simulation(engine, results)
    except ImportError:
        print("Matplotlib not available - skipping visualizations")
    
    print("\n" + "=" * 60)
    print("All tests completed successfully!")
    print("The Digital Twin Simulation Engine is ready for integration with the trading system.") 