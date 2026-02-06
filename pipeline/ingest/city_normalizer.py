"""Maps lab-specific location identifiers to canonical city names."""

# Apollo centre codes -> city (based on centre_name analysis)
APOLLO_CITY_MAP = {
    "GRL0001": "Hyderabad",
    "RRL0002": "Bangalore",
    "RRL0004": "Pune",
    "RRL0006": "Vijayawada",
    "RRL0008": "Patna",
    "RRL134": "Hyderabad",
    "RRL138": "Kolkata",
    "RRL140": "Delhi",
    "SL0001": "Guwahati",
    "SL0003": "Bhubaneswar",
    "SL0006": "Coimbatore",
    "SL0007": "Visakhapatnam",
    "SL0011": "Madurai",
    "SL0021": "Mysore",
    "SL0029": "Tirupati",
    "SL0044": "Trichy",
    "SL0053": "Salem",
    "SL101": "Lucknow",
    "SL106": "Raipur",
    "SL108": "Ranchi",
    "SL109": "Ahmedabad",
    "SL113": "Jaipur",
    "SL76": "Jaipur",
}

# TRUSTlab location names -> canonical city
TRUSTLAB_CITY_MAP = {
    "Begumpet": "Hyderabad",
    "Dilsukhnagar": "Hyderabad",
    "Miyapur": "Hyderabad",
    "Noida": "Delhi",
    "Chandigarh": "Chandigarh",
    "Jammu": "Jammu",
    "Guntur": "Guntur",
    "Vijayawada": "Vijayawada",
    "Vizag": "Visakhapatnam",
    "Anantapur": "Anantapur",
    "Bangalore": "Bangalore",
    "Karimnagar": "Karimnagar",
    "Mahbubnagar": "Mahbubnagar",
    "Nizamabad": "Nizamabad",
    "Hanumakonda": "Hanumakonda",
}

# Agilus/Metropolis single-city mappings
STATIC_CITY_MAP = {
    "NEW_DELHI": "Delhi",
    "DELHI": "Delhi",
}

# Neuberg cities are already canonical names (Hyderabad, Bangalore, etc.)
# Just normalize common variants
NEUBERG_CITY_NORMALIZE = {
    "Bangalore": "Bangalore",
    "Hyderabad": "Hyderabad",
    "Mumbai": "Mumbai",
    "Delhi": "Delhi",
    "Chennai": "Chennai",
    "Kolkata": "Kolkata",
    "Ahmedabad": "Ahmedabad",
    "Jaipur": "Jaipur",
    "Lucknow": "Lucknow",
    "Chandigarh": "Chandigarh",
    "Bhopal": "Bhopal",
    "Indore": "Indore",
    "Vijayawada": "Vijayawada",
    "Kochi": "Kochi",
    "Coimbatore": "Coimbatore",
}

# State lookup for city records
CITY_STATE_MAP = {
    "Delhi": ("Delhi", 1),
    "Mumbai": ("Maharashtra", 1),
    "Bangalore": ("Karnataka", 1),
    "Hyderabad": ("Telangana", 1),
    "Chennai": ("Tamil Nadu", 1),
    "Kolkata": ("West Bengal", 1),
    "Ahmedabad": ("Gujarat", 1),
    "Pune": ("Maharashtra", 1),
    "Jaipur": ("Rajasthan", 1),
    "Lucknow": ("Uttar Pradesh", 1),
    "Chandigarh": ("Chandigarh", 1),
    "Bhopal": ("Madhya Pradesh", 2),
    "Indore": ("Madhya Pradesh", 2),
    "Kochi": ("Kerala", 2),
    "Coimbatore": ("Tamil Nadu", 2),
    "Vijayawada": ("Andhra Pradesh", 2),
    "Visakhapatnam": ("Andhra Pradesh", 2),
    "Patna": ("Bihar", 2),
    "Guwahati": ("Assam", 2),
    "Bhubaneswar": ("Odisha", 2),
    "Madurai": ("Tamil Nadu", 2),
    "Mysore": ("Karnataka", 2),
    "Tirupati": ("Andhra Pradesh", 2),
    "Trichy": ("Tamil Nadu", 2),
    "Salem": ("Tamil Nadu", 2),
    "Raipur": ("Chhattisgarh", 2),
    "Ranchi": ("Jharkhand", 2),
    "Jammu": ("Jammu & Kashmir", 2),
    "Guntur": ("Andhra Pradesh", 2),
    "Anantapur": ("Andhra Pradesh", 3),
    "Karimnagar": ("Telangana", 3),
    "Mahbubnagar": ("Telangana", 3),
    "Nizamabad": ("Telangana", 3),
    "Hanumakonda": ("Telangana", 3),
}


def normalize_city(location_code: str | None, lab_slug: str) -> str | None:
    """Map a lab-specific location identifier to a canonical city name."""
    if not location_code:
        return None

    code = location_code.strip()

    if lab_slug == "apollo":
        return APOLLO_CITY_MAP.get(code)
    elif lab_slug == "neuberg":
        return NEUBERG_CITY_NORMALIZE.get(code, code)
    elif lab_slug == "trustlab":
        return TRUSTLAB_CITY_MAP.get(code, code)
    elif lab_slug in ("metropolis", "agilus"):
        return STATIC_CITY_MAP.get(code, "Delhi")

    return None


def get_all_cities() -> list[dict]:
    """Return list of all canonical city records for seeding."""
    cities = []
    for city_name, (state, tier) in CITY_STATE_MAP.items():
        cities.append({
            "name": city_name,
            "state": state,
            "tier": tier,
        })
    return cities
