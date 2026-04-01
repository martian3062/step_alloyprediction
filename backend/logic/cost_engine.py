import math

# Market Rates (Simplified simulation)
METAL_PROPERTIES = {
    "A380 (Aluminum)": {"density": 0.0027, "price_per_kg": 2.8, "injection_pressure": 80}, # 80 MPa
    "Zinc-3": {"density": 0.0066, "price_per_kg": 3.4, "injection_pressure": 30},
    "Magnesium-AZ91D": {"density": 0.0018, "price_per_kg": 4.5, "injection_pressure": 60}
}

# Machine Tonnage Mapping (Tonne : Hourly Rate $)
MACHINE_RATES = [
    {"limit": 250, "rate": 45},
    {"limit": 500, "rate": 75},
    {"limit": 850, "rate": 110},
    {"limit": 1250, "rate": 160},
    {"limit": 2000, "rate": 280},
    {"limit": 4000, "rate": 550}
]

def calculate_hpdc_cost(traits, metal, annual_volume, sliders, location_multiplier=1.0, live_price_per_kg=None):
    """
    Calculates HPDC cost based on part traits and user parameters.
    """
    if metal not in METAL_PROPERTIES:
        metal = "A380 (Aluminum)"
        
    props = METAL_PROPERTIES[metal]
    volume = traits['volume']
    projected_area = traits['projected_area']
    
    # Use live price if provided, else fallback to static data
    market_price = live_price_per_kg if live_price_per_kg is not None else props['price_per_kg']
    
    # 1. Material Cost
    weight = volume * props['density'] # grams
    weight_kg = weight / 1000
    material_cost = weight_kg * market_price * 1.15 # 15% scrap factor
    
    # 2. Machine Tonnage (Clamping Force)
    # Total Tonnage = (Projected Area * Injection Pressure) * SF / 10
    # Projected Area is in mm^2, Injection Pressure in MPa (N/mm^2)
    # Force in N = PA * IP -> 1000N ~= 100kg ~= 0.1 Tonne
    force_kn = projected_area * props.get('injection_pressure', 80) / 1000
    force_tonne = force_kn / 10.0 # Approximation
    required_tonnage = force_tonne * 1.3 # 30% Safety factor
    
    # Select Machine
    machine_rate = 45 # Default
    machine_tonnage = 250
    for m in MACHINE_RATES:
        if required_tonnage <= m['limit']:
            machine_rate = m['rate']
            machine_tonnage = m['limit']
            break
            
    # 3. Cycle Time Estimation (simplified)
    # Base: 30s + 2s per 100g weight + complexity factor
    cycle_time = 25 + (weight_kg * 10) + (sliders * 5)
    shots_per_hour = 3600 / cycle_time
    machine_cost_per_part = (machine_rate * location_multiplier) / shots_per_hour
    
    # 4. Tooling Cost (Estimated)
    # Base Mold: $12,000 + $4500 per slider + size factor
    base_tooling = 12000 + (max(0, machine_tonnage - 250) * 15)
    tooling_cost_total = base_tooling + (sliders * 4500)
    amortization_cost = tooling_cost_total / annual_volume
    
    # 5. Total
    total_unit_cost = material_cost + machine_cost_per_part + amortization_cost
    
    return {
        "material_cost": round(material_cost, 2),
        "machine_cost": round(machine_cost_per_part, 2),
        "amortization": round(amortization_cost, 2),
        "total_unit_cost": round(total_unit_cost, 2),
        "market_price": round(market_price, 2),
        "machine_details": {
            "required_tonnage": round(required_tonnage, 1),
            "selected_machine": machine_tonnage,
            "cycle_time_s": round(cycle_time, 1)
        },
        "tooling_estimate": round(tooling_cost_total, 0),
        "weight_g": round(weight, 1)
    }
