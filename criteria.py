criteria_structure = {

    "Conventional Criteria": [
        "Cost","Quality","Delivery","Lead Time","Production Capacity",
        "Financial Stability","Technical Capability","After Sales Service",
        "Market Reputation","Supplier Experience","Warranty Policy",
        "Inventory Capability","Communication Efficiency","Flexibility"
    ],

    "Environmental Criteria":[
        "Energy Consumption","Waste Recycling","Carbon Footprint",
        "Water Consumption","Green Packaging","Pollution Emission",
        "Renewable Energy Usage","Hazardous Material Handling",
        "Environmental Certification","Eco Friendly Design"
    ],

    "Circular Economy Criteria":[
        "Product Recyclability","Reverse Logistics","Material Reuse",
        "Remanufacturing Capability","Waste Recovery",
        "Closed Loop Supply","Recycled Material Usage",
        "Product Life Extension","Modular Design"
    ],

    "Resilience Criteria":[
        "Risk Management","Supply Redundancy","Disaster Recovery Plan",
        "Demand Surge Adaptability","Supplier Diversification",
        "Inventory Buffer","Cyber Security Readiness",
        "Digital Tracking Capability","Emergency Response",
        "Supply Chain Visibility"
    ]
}

criteria = []
for category in criteria_structure.values():
    criteria.extend(category)