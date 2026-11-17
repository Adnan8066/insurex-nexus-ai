// Motor policy tiers. Prices are estimates, not insurer quotes.
export const policyTiers = [
  {
    id: 'POL-PC-004', name: 'Third Party Liability Only Policy', category: 'Private Car',
    type: 'auto_liability', coverageSections: ['Section II (Third Party Liability)'],
    mandatoryCovers: ['Section III (PA Cover for Owner-Driver)'], deductible: 0, addons: [], basePremium: 2094,
  },
  {
    id: 'POL-PC-001', name: 'Comprehensive Package Policy', category: 'Private Car',
    type: 'auto_comprehensive',
    coverageSections: ['Section I (Own Damage - Fire, Theft, Accidental Damage)', 'Section II (Third Party Liability)'],
    mandatoryCovers: ['Section III (PA Cover for Owner-Driver)'], deductible: 1000,
    addons: ['Zero Depreciation', 'Road Side Assistance', 'Key Protect', 'Consumables'], basePremium: 12500,
  },
  {
    id: 'POL-PC-003', name: 'Standalone Own Damage Policy', category: 'Private Car',
    type: 'auto_collision',
    coverageSections: ['Section I (Own Damage - Fire, Theft, Accidental Damage)'],
    mandatoryCovers: ['Valid third-party liability policy required'], deductible: 1000,
    addons: ['Zero Depreciation', 'Engine Protect Plus', 'Consumable Items', 'Road Side Assistance', 'NCB Protect'], basePremium: 8500,
  },
]
