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
        result = household.simulate_hour(hour, weather_factor=0.8)
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
    
    # Generate weather conditions
    engine.generate_weather_conditions(days=1)
    
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


def test_trading_functionality():
    """Test energy trading between households"""
    print("\n=== Testing Trading Functionality ===")
    
    # Create two households
    demand_pattern1 = generate_demand_pattern("low_usage")
    demand_pattern2 = generate_demand_pattern("high_usage")
    
    household1 = Household("TRADE001", 4.0, 12.0, demand_pattern1)
    household2 = Household("TRADE002", 2.5, 8.0, demand_pattern2)
    
    # Simulate both households at noon (peak solar generation)
    result1 = household1.simulate_hour(12, weather_factor=0.9)
    result2 = household2.simulate_hour(12, weather_factor=0.9)
    
    print(f"Before trading:")
    print(f"  {household1.id}: Net={result1['net_energy']:.2f}kW, Role={result1['role']}")
    print(f"  {household2.id}: Net={result2['net_energy']:.2f}kW, Role={result2['role']}")
    
    # Attempt energy trade
    if household1.role.value == 'seller' and household2.role.value == 'buyer':
        trade_amount = min(abs(household1.current_net_energy), abs(household2.current_net_energy)) * 0.5
        trade_price = 0.15  # $0.15 per kWh
        
        success1 = household1.trade_energy(trade_amount, trade_price, household2.id)
        success2 = household2.trade_energy(trade_amount, trade_price, household1.id)
        
        if success1 and success2:
            print(f"\nTrade successful!")
            print(f"  Amount: {trade_amount:.2f} kWh")
            print(f"  Price: ${trade_price:.2f}/kWh")
            print(f"  Total: ${trade_amount * trade_price:.2f}")
            
            print(f"\nAfter trading:")
            print(f"  {household1.id}: Net={household1.current_net_energy:.2f}kW, Total traded={household1.total_traded:.2f}kWh")
            print(f"  {household2.id}: Net={household2.current_net_energy:.2f}kW, Total traded={household2.total_traded:.2f}kWh")
        else:
            print("Trade failed - insufficient energy or battery constraints")
    else:
        print("No trading opportunity - households not in complementary roles")


if __name__ == "__main__":
    print("SolarShare Digital Twin Simulation Engine - Test Suite")
    print("=" * 60)
    
    # Run all tests
    test_basic_simulation()
    engine, results = test_community_simulation()
    test_crisis_injection()
    test_trading_functionality()
    
    # Create visualizations
    try:
        visualize_simulation(engine, results)
    except ImportError:
        print("Matplotlib not available - skipping visualizations")
    
    print("\n" + "=" * 60)
    print("All tests completed successfully!")
    print("The Digital Twin Simulation Engine is ready for integration with the trading system.") 