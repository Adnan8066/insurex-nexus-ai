"""Static reference data: geography, vehicles, parts, medical services, naming vocab.

Figures are representative, not authoritative (state minimum limits and PIP amounts
change; verify before quoting them as facts). They exist to make the synthetic world
internally consistent.
"""

# metro_key: (state, display_city, weight, territory_factor, area_codes, zip3_prefixes)
METROS = {
    "LOS_ANGELES":  ("CA", "Los Angeles",   0.072, 1.55, [213, 310, 323, 818, 626], ["900", "902", "906", "910", "913", "917"]),
    "SAN_DIEGO":    ("CA", "San Diego",     0.022, 1.20, [619, 858], ["919", "920", "921"]),
    "SF_BAY":       ("CA", "San Jose",      0.028, 1.35, [408, 510, 415], ["940", "945", "950", "951"]),
    "SACRAMENTO":   ("CA", "Sacramento",    0.014, 1.15, [916], ["956", "958"]),
    "HOUSTON":      ("TX", "Houston",       0.050, 1.45, [713, 281, 832], ["770", "772", "773", "774"]),
    "DALLAS":       ("TX", "Dallas",        0.050, 1.35, [214, 972, 817], ["750", "751", "752", "760", "761"]),
    "SAN_ANTONIO":  ("TX", "San Antonio",   0.019, 1.20, [210], ["780", "781", "782"]),
    "AUSTIN":       ("TX", "Austin",        0.017, 1.15, [512], ["786", "787"]),
    "TX_RURAL":     ("TX", "Tyler",         0.016, 0.85, [903], ["756", "757"]),
    "MIAMI":        ("FL", "Miami",         0.040, 1.90, [305, 786, 954], ["330", "331", "333"]),
    "TAMPA":        ("FL", "Tampa",         0.024, 1.50, [813, 727], ["335", "336", "337"]),
    "ORLANDO":      ("FL", "Orlando",       0.020, 1.45, [407, 321], ["327", "328"]),
    "JACKSONVILLE": ("FL", "Jacksonville",  0.011, 1.30, [904], ["320", "322"]),
    "NEW_YORK":     ("NY", "Brooklyn",      0.055, 1.85, [718, 347, 929], ["112", "113", "114", "104"]),
    "BUFFALO":      ("NY", "Buffalo",       0.010, 1.10, [716], ["140", "142"]),
    "NEWARK":       ("NJ", "Newark",        0.028, 1.60, [973, 201, 862], ["070", "071", "073", "076"]),
    "PHILADELPHIA": ("PA", "Philadelphia",  0.028, 1.50, [215, 267], ["190", "191"]),
    "PITTSBURGH":   ("PA", "Pittsburgh",    0.011, 1.05, [412], ["150", "151", "152"]),
    "ALLENTOWN":    ("PA", "Allentown",     0.007, 0.92, [610, 484], ["180", "181"]),
    "CHICAGO":      ("IL", "Chicago",       0.044, 1.40, [312, 773, 630, 708], ["600", "601", "604", "606"]),
    "COLUMBUS":     ("OH", "Columbus",      0.016, 1.00, [614], ["430", "432"]),
    "CLEVELAND":    ("OH", "Cleveland",     0.013, 1.05, [216, 440], ["440", "441"]),
    "OH_RURAL":     ("OH", "Findlay",       0.010, 0.82, [419], ["448", "458"]),
    "ATLANTA":      ("GA", "Atlanta",       0.034, 1.45, [404, 770, 678], ["300", "301", "303"]),
    "GA_RURAL":     ("GA", "Macon",         0.008, 0.95, [478], ["310", "312"]),
    "CHARLOTTE":    ("NC", "Charlotte",     0.017, 1.00, [704, 980], ["280", "282"]),
    "RALEIGH":      ("NC", "Raleigh",       0.012, 0.95, [919, 984], ["275", "276"]),
    "DETROIT":      ("MI", "Detroit",       0.028, 1.95, [313, 248, 586], ["480", "481", "482"]),
    "PHOENIX":      ("AZ", "Phoenix",       0.030, 1.20, [602, 480, 623], ["850", "852", "853"]),
    "DENVER":       ("CO", "Denver",        0.021, 1.30, [303, 720], ["800", "801", "802"]),
    "SEATTLE":      ("WA", "Seattle",       0.021, 1.15, [206, 425, 253], ["980", "981", "984"]),
    "BOSTON":       ("MA", "Boston",        0.019, 1.15, [617, 781, 508], ["021", "022", "024"]),
    "NASHVILLE":    ("TN", "Nashville",     0.014, 1.05, [615], ["370", "372"]),
    "MINNEAPOLIS":  ("MN", "Minneapolis",   0.016, 1.00, [612, 651, 952], ["551", "553", "554"]),
    "NEW_ORLEANS":  ("LA", "New Orleans",   0.011, 1.70, [504, 985], ["700", "701"]),
}

# state: (no_fault, pip_limit_options, state_min_bi, state_min_pd, state_factor)
STATES = {
    "CA": (False, [0],            "30/60",  15000, 1.10),
    "TX": (False, [0],            "30/60",  25000, 1.05),
    "FL": (True,  [10000],        "10/20",  10000, 1.20),
    "NY": (True,  [50000],        "25/50",  10000, 1.20),
    "NJ": (True,  [15000, 250000],"25/50",  25000, 1.15),
    "PA": (True,  [5000],         "15/30",   5000, 1.00),
    "IL": (False, [0],            "25/50",  20000, 1.00),
    "OH": (False, [0],            "25/50",  25000, 0.90),
    "GA": (False, [0],            "25/50",  25000, 1.05),
    "NC": (False, [0],            "50/100", 50000, 0.88),
    "MI": (True,  [250000, 500000],"50/100",10000, 1.25),
    "AZ": (False, [0],            "25/50",  15000, 1.00),
    "CO": (False, [0],            "25/50",  15000, 1.05),
    "WA": (False, [0],            "25/50",  10000, 1.00),
    "MA": (True,  [8000],         "25/50",  30000, 1.00),
    "TN": (False, [0],            "25/50",  25000, 0.92),
    "MN": (True,  [40000],        "30/60",  10000, 0.95),
    "LA": (False, [0],            "15/30",  25000, 1.30),
}

# make, model, body, segment, msrp_new, wmi, adas_from_year, weight
VEHICLES = [
    ("Ford", "F-150", "Pickup", "pickup", 52000, "1FT", 2018, 0.060),
    ("Chevrolet", "Silverado 1500", "Pickup", "pickup", 50000, "1GC", 2019, 0.045),
    ("Ram", "1500", "Pickup", "pickup", 50000, "1C6", 2019, 0.035),
    ("GMC", "Sierra 1500", "Pickup", "pickup", 55000, "1GT", 2019, 0.018),
    ("Toyota", "Tacoma", "Pickup", "pickup", 36000, "3TM", 2018, 0.022),
    ("Toyota", "RAV4", "SUV", "suv_small", 33000, "2T3", 2017, 0.045),
    ("Honda", "CR-V", "SUV", "suv_small", 34000, "2HK", 2017, 0.040),
    ("Nissan", "Rogue", "SUV", "suv_small", 31000, "JN8", 2018, 0.030),
    ("Chevrolet", "Equinox", "SUV", "suv_small", 29000, "2GN", 2019, 0.028),
    ("Ford", "Escape", "SUV", "suv_small", 30000, "1FM", 2019, 0.022),
    ("Hyundai", "Tucson", "SUV", "suv_small", 30000, "5NM", 2019, 0.022),
    ("Kia", "Sportage", "SUV", "suv_small", 29000, "KND", 2020, 0.018),
    ("Mazda", "CX-5", "SUV", "suv_small", 30000, "JM3", 2018, 0.020),
    ("Subaru", "Forester", "SUV", "suv_small", 30000, "JF2", 2017, 0.016),
    ("Jeep", "Grand Cherokee", "SUV", "suv_mid", 42000, "1C4", 2018, 0.024),
    ("Jeep", "Wrangler", "SUV", "suv_mid", 38000, "1C4", 2021, 0.018),
    ("Ford", "Explorer", "SUV", "suv_mid", 41000, "1FM", 2020, 0.020),
    ("Toyota", "Highlander", "SUV", "suv_mid", 42000, "5TD", 2018, 0.018),
    ("Honda", "Pilot", "SUV", "suv_mid", 42000, "5FN", 2019, 0.014),
    ("Kia", "Telluride", "SUV", "suv_mid", 38000, "5XY", 2020, 0.010),
    ("Hyundai", "Santa Fe", "SUV", "suv_mid", 32000, "5NM", 2019, 0.012),
    ("Chevrolet", "Tahoe", "SUV", "suv_large", 60000, "1GN", 2019, 0.012),
    ("Toyota", "Camry", "Sedan", "sedan_mid", 29000, "4T1", 2018, 0.040),
    ("Honda", "Accord", "Sedan", "sedan_mid", 30000, "1HG", 2018, 0.030),
    ("Nissan", "Altima", "Sedan", "sedan_mid", 27000, "1N4", 2019, 0.024),
    ("Chevrolet", "Malibu", "Sedan", "sedan_mid", 26000, "1G1", 2019, 0.014),
    ("Honda", "Civic", "Sedan", "sedan_small", 26000, "2HG", 2019, 0.035),
    ("Toyota", "Corolla", "Sedan", "sedan_small", 23000, "5YF", 2019, 0.035),
    ("Hyundai", "Elantra", "Sedan", "sedan_small", 22000, "KMH", 2021, 0.020),
    ("Kia", "Forte", "Sedan", "sedan_small", 21000, "3KP", 2021, 0.014),
    ("Nissan", "Sentra", "Sedan", "sedan_small", 21000, "3N1", 2020, 0.016),
    ("Volkswagen", "Jetta", "Sedan", "sedan_small", 23000, "3VW", 2019, 0.010),
    ("Subaru", "Outback", "Wagon", "wagon", 32000, "4S4", 2017, 0.014),
    ("Tesla", "Model Y", "SUV", "ev", 47000, "7SA", 2020, 0.018),
    ("Tesla", "Model 3", "Sedan", "ev", 42000, "5YJ", 2017, 0.014),
    ("BMW", "3 Series", "Sedan", "luxury", 46000, "WBA", 2017, 0.010),
    ("BMW", "X5", "SUV", "luxury_suv", 66000, "5UX", 2017, 0.008),
    ("Mercedes-Benz", "C-Class", "Sedan", "luxury", 48000, "W1K", 2017, 0.009),
    ("Lexus", "RX 350", "SUV", "luxury_suv", 52000, "2T2", 2017, 0.009),
    ("Audi", "Q5", "SUV", "luxury_suv", 47000, "WA1", 2018, 0.007),
    ("Cadillac", "Escalade", "SUV", "luxury_suv", 85000, "1GY", 2019, 0.004),
    ("Dodge", "Charger", "Sedan", "sports", 36000, "2C3", 2021, 0.012),
    ("Dodge", "Durango", "SUV", "suv_mid", 42000, "1C4", 2021, 0.008),
    ("Ford", "Mustang", "Coupe", "sports", 33000, "1FA", 2018, 0.010),
    ("Chevrolet", "Camaro", "Coupe", "sports", 32000, "1G1", 2019, 0.006),
    ("Honda", "Odyssey", "Minivan", "minivan", 40000, "5FN", 2018, 0.010),
    ("Toyota", "Sienna", "Minivan", "minivan", 40000, "5TD", 2018, 0.009),
    ("Chrysler", "Pacifica", "Minivan", "minivan", 41000, "2C4", 2018, 0.007),
]

# Frequency relativity by segment (collision, comprehensive, theft)
SEGMENT_REL = {
    "pickup": (0.95, 1.05, 1.30), "suv_small": (0.95, 0.95, 0.80), "suv_mid": (1.00, 1.00, 1.00),
    "suv_large": (1.00, 1.05, 1.40), "sedan_mid": (1.05, 0.95, 1.00), "sedan_small": (1.10, 0.95, 1.10),
    "wagon": (0.85, 0.95, 0.60), "ev": (1.05, 1.10, 0.50), "luxury": (1.00, 1.05, 1.10),
    "luxury_suv": (0.95, 1.05, 1.20), "sports": (1.30, 1.10, 1.80), "minivan": (0.85, 0.90, 0.60),
}

VIN_YEAR_CODES = {2001: "1", 2002: "2", 2003: "3", 2004: "4", 2005: "5", 2006: "6", 2007: "7",
                  2008: "8", 2009: "9", 2010: "A", 2011: "B", 2012: "C", 2013: "D", 2014: "E",
                  2015: "F", 2016: "G", 2017: "H", 2018: "J", 2019: "K", 2020: "L", 2021: "M",
                  2022: "N", 2023: "P", 2024: "R", 2025: "S", 2026: "T"}

# Repair parts: zone -> list of (part, base_price, repair_hrs, replace_hrs, refinish_hrs, weight)
PARTS = {
    "FRONT": [
        ("Front bumper cover", 480, 2.5, 2.0, 3.0, 1.00), ("Headlamp assembly", 650, 0.0, 0.8, 0.0, 0.70),
        ("Grille", 290, 0.0, 0.6, 0.0, 0.60), ("Hood panel", 720, 3.0, 1.2, 3.6, 0.55),
        ("Front bumper reinforcement", 260, 0.0, 1.5, 0.0, 0.50), ("Radiator support", 540, 3.5, 6.0, 1.5, 0.35),
        ("Radiator", 390, 0.0, 2.0, 0.0, 0.30), ("A/C condenser", 360, 0.0, 1.6, 0.0, 0.30),
        ("Front fender", 390, 2.0, 1.8, 2.8, 0.45), ("Fog lamp", 140, 0.0, 0.4, 0.0, 0.25),
        ("Front airbag module", 1150, 0.0, 1.0, 0.0, 0.08), ("Front parking sensor", 120, 0.0, 0.5, 0.0, 0.25),
    ],
    "REAR": [
        ("Rear bumper cover", 450, 2.5, 2.0, 3.0, 1.00), ("Tail lamp assembly", 310, 0.0, 0.5, 0.0, 0.65),
        ("Liftgate / trunk lid", 950, 3.0, 2.0, 3.5, 0.45), ("Rear body panel", 360, 2.5, 5.5, 2.0, 0.35),
        ("Rear bumper reinforcement", 240, 0.0, 1.4, 0.0, 0.45), ("Backup camera", 260, 0.0, 0.6, 0.0, 0.30),
        ("Quarter panel", 620, 4.0, 9.0, 3.0, 0.35), ("Rear parking sensor", 120, 0.0, 0.5, 0.0, 0.30),
        ("Exhaust tip", 110, 0.0, 0.4, 0.0, 0.15),
    ],
    "LEFT": [
        ("Front door shell LH", 960, 3.0, 3.2, 3.0, 0.80), ("Rear door shell LH", 910, 3.0, 3.0, 3.0, 0.65),
        ("Outside mirror LH", 380, 0.0, 0.5, 0.6, 0.50), ("Rocker panel LH", 320, 2.5, 4.5, 1.8, 0.35),
        ("Alloy wheel LH", 460, 0.0, 0.3, 0.0, 0.35), ("Tire", 220, 0.0, 0.3, 0.0, 0.30),
        ("Lower control arm LH", 270, 0.0, 1.6, 0.0, 0.25), ("Side curtain airbag LH", 980, 0.0, 1.5, 0.0, 0.06),
        ("B-pillar LH", 480, 4.0, 8.5, 2.0, 0.10),
    ],
    "RIGHT": [
        ("Front door shell RH", 960, 3.0, 3.2, 3.0, 0.80), ("Rear door shell RH", 910, 3.0, 3.0, 3.0, 0.65),
        ("Outside mirror RH", 380, 0.0, 0.5, 0.6, 0.50), ("Rocker panel RH", 320, 2.5, 4.5, 1.8, 0.35),
        ("Alloy wheel RH", 460, 0.0, 0.3, 0.0, 0.35), ("Tire", 220, 0.0, 0.3, 0.0, 0.30),
        ("Lower control arm RH", 270, 0.0, 1.6, 0.0, 0.25), ("Side curtain airbag RH", 980, 0.0, 1.5, 0.0, 0.06),
        ("B-pillar RH", 480, 4.0, 8.5, 2.0, 0.10),
    ],
    "TOP": [
        ("Roof panel", 880, 6.0, 12.0, 4.0, 0.60), ("Hood panel", 720, 3.0, 1.2, 3.6, 0.70),
        ("Windshield", 520, 0.0, 1.5, 0.0, 0.45), ("Trunk lid", 820, 3.0, 2.0, 3.5, 0.40),
        ("Moonroof glass", 690, 0.0, 2.0, 0.0, 0.20),
    ],
}
SUBLET = {"ADAS calibration": 380, "Frame setup & pull": 850, "Four-wheel alignment": 140,
          "Towing": 175, "Storage (per day)": 55, "Hazardous waste disposal": 12}

# Medical service groups: code, label, price_low, price_high, provider_type
MED_SERVICES = {
    "ER":     ("ER visit / triage", 900, 3200, "HOSPITAL"),
    "XRAY":   ("Radiology - X-ray", 120, 450, "IMAGING"),
    "MRI":    ("MRI - spine", 900, 2600, "IMAGING"),
    "EM":     ("Office visit E/M", 140, 320, "ORTHO"),
    "CHIRO":  ("Chiropractic manipulation", 75, 160, "CHIRO"),
    "PT":     ("Physical therapy session", 110, 240, "PT"),
    "INJECT": ("Epidural / facet injection", 1400, 4200, "PAIN_MGMT"),
    "SURG":   ("Orthopedic surgery", 18000, 65000, "ORTHO"),
    "RX":     ("Pharmacy", 25, 180, "PHARMACY"),
}
INJURIES = {"SPRAIN_STRAIN_NECK": 0.38, "SPRAIN_STRAIN_BACK": 0.22, "CONTUSION": 0.12,
            "LACERATION": 0.08, "CONCUSSION": 0.07, "FRACTURE": 0.08, "OTHER": 0.05}

STREET_NAMES = [
    "Oak", "Maple", "Cedar", "Elm", "Pine", "Walnut", "Willow", "Birch", "Chestnut", "Hickory", "Magnolia",
    "Sycamore", "Juniper", "Laurel", "Aspen", "Cypress", "Dogwood", "Hawthorn", "Linden", "Poplar",
    "Washington", "Jefferson", "Lincoln", "Madison", "Monroe", "Franklin", "Jackson", "Adams", "Hamilton",
    "Park", "Lake", "Hill", "River", "Spring", "Meadow", "Ridge", "Valley", "Forest", "Highland", "Sunset",
    "Church", "Mill", "Center", "Market", "Union", "Prospect", "Liberty", "Harbor", "Bay", "Summit",
    "Fairview", "Grandview", "Lakeview", "Riverside", "Brookside", "Woodland", "Greenwood", "Kingston",
    "Lexington", "Arlington", "Clifton", "Belmont", "Ashford", "Brighton", "Chester", "Dover", "Easton",
    "Garfield", "Grant", "Hayes", "Kennedy", "Mckinley", "Pierce", "Polk", "Taylor", "Tyler", "Wilson",
    "Bluebonnet", "Mesquite", "Saguaro", "Palmetto", "Coral", "Seminole", "Peachtree", "Dogwood Trace",
    "Old Mill", "Stone", "Copper", "Silver", "Granite", "Quarry", "Canyon", "Prairie", "Orchard", "Vineyard",
]
STREET_SUFFIX = ["St", "Ave", "Rd", "Dr", "Ln", "Ct", "Blvd", "Way", "Pl", "Ter", "Cir", "Pkwy", "Trl"]
EMAIL_DOMAINS = ["mailbox.example", "inbox.example", "postnet.example", "webmail.example", "fastmail.example"]

# Modern first names (born 1995+) the 1990 Census lists under-represent
MODERN_MALE = ["LIAM", "AIDEN", "JAYDEN", "ETHAN", "LOGAN", "CALEB", "OWEN", "WYATT", "LUCAS", "LEVI",
               "CARTER", "GRAYSON", "HUDSON", "EASTON", "BRAYDEN", "COOPER", "JAXON", "MATEO", "ELIJAH", "ISAIAH"]
MODERN_FEMALE = ["ISABELLA", "AVA", "MADISON", "CHLOE", "ADDISON", "HARPER", "AVERY", "KAYLEE", "BROOKLYN",
                 "AUBREY", "PEYTON", "MACKENZIE", "ZOEY", "SKYLAR", "PAISLEY", "AALIYAH", "NEVAEH", "HAILEY",
                 "RILEY", "SAVANNAH"]

BIZ_WORDS = ["Precision", "Summit", "Elite", "Premier", "Allied", "Cornerstone", "Liberty", "Pioneer", "Keystone",
             "Heritage", "Northstar", "Lakeside", "Metro", "Crossroads", "Ironwood", "Bluewater", "Redline",
             "Silverline", "Trident", "Apex", "Benchmark", "Cardinal", "Evergreen", "Frontier", "Granite",
             "Harborview", "Landmark", "Midtown", "Patriot", "Quantum", "Ridgeway", "Sterling", "Titan",
             "Uptown", "Vanguard", "Westgate", "Yellowstone", "Zenith", "Coastal", "Gateway", "Horizon",
             "Integrity", "Junction", "Kingsway", "Legacy", "Monarch", "Oakmont", "Paramount", "Regal", "Sunbelt"]
BIZ_TEMPLATES = {
    "BODY_SHOP": ["{w} Collision", "{s} Auto Body", "{w} Collision Center", "{s} & Sons Body Works",
                  "{w} Auto Body & Paint", "{s} Collision Repair"],
    "TOW":       ["{w} Towing", "{s} Towing & Recovery", "{w} Wrecker Service", "{s} Roadside & Tow"],
    "GLASS":     ["{w} Auto Glass", "{s} Glass & Mirror", "{w} Windshield Pros", "Mobile {w} Glass"],
    "HOSPITAL":  ["{w} Medical Center", "{s} Memorial Hospital", "{w} Regional Hospital"],
    "IMAGING":   ["{w} Imaging", "{s} Diagnostic Imaging", "{w} Open MRI"],
    "ORTHO":     ["{w} Orthopedics", "{s} Bone & Joint", "{w} Sports Medicine"],
    "CHIRO":     ["{w} Chiropractic", "{s} Spine & Wellness", "{w} Injury & Chiro Center"],
    "PT":        ["{w} Physical Therapy", "{s} Rehab Group", "{w} Motion PT"],
    "PAIN_MGMT": ["{w} Pain Institute", "{s} Pain & Spine", "{w} Interventional Pain"],
    "PHARMACY":  ["{w} Pharmacy", "{s} Drugs"],
    "ATTORNEY":  ["{s} & {s2} Injury Law", "Law Office of {f} {s}", "{s} Trial Lawyers", "{w} Accident Attorneys",
                  "{s} {s2} & Associates"],
    "RENTAL":    ["{w} Car Rental", "{w} Rent-A-Car"],
    "VENDOR":    ["{w} Claim Services LLC", "{s} Adjusting Solutions", "{w} Vehicle Inspections LLC"],
    "AGENCY":    ["{s} Insurance Agency", "{w} Insurance Group", "{s} & {s2} Insurance", "{w} Insurance Partners"],
}
