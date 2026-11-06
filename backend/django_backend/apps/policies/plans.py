"""Demo insurance plans shown to customers for viewing and comparison.

These are illustrative product tiers for the demonstration app. The premium
estimates are sample values, not insurer quotes. Replace this list with approved
product data before real use.
"""

DEMO_NOTICE = 'Demonstration plans. Premium estimates are sample values, not insurer quotes.'

PLAN_CATALOGUE = [
    {
        'id': 'PLAN-TP-001',
        'name': 'Third Party Liability',
        'category': 'Private Car',
        'coverage_sections': ['Third-party injury cover', 'Third-party property damage cover'],
        'mandatory_covers': ['Third-party liability (required by law)'],
        'own_damage_cover': False,
        'addons': [],
        'base_premium_estimate_inr': 2100,
        'deductible_inr': 0,
        'max_claim_inr': 500000,
        'roadside_assistance': False,
    },
    {
        'id': 'PLAN-CS-001',
        'name': 'Standard Comprehensive',
        'category': 'Private Car',
        'coverage_sections': [
            'Own damage (fire, theft, accidental damage)',
            'Third-party liability',
        ],
        'mandatory_covers': ['Personal accident cover for owner-driver'],
        'own_damage_cover': True,
        'addons': ['Roadside assistance', 'Key protect'],
        'base_premium_estimate_inr': 12500,
        'deductible_inr': 1000,
        'max_claim_inr': 3000000,
        'roadside_assistance': True,
    },
    {
        'id': 'PLAN-PC-001',
        'name': 'Premium Comprehensive',
        'category': 'Private Car',
        'coverage_sections': [
            'Own damage (fire, theft, accidental damage)',
            'Third-party liability',
            'Engine and gearbox protection',
        ],
        'mandatory_covers': ['Personal accident cover for owner-driver'],
        'own_damage_cover': True,
        'addons': ['Zero depreciation', 'Roadside assistance', 'Key protect', 'Consumables'],
        'base_premium_estimate_inr': 18500,
        'deductible_inr': 500,
        'max_claim_inr': 6000000,
        'roadside_assistance': True,
    },
]
