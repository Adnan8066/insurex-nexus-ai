// User-provided draft motor policy tiers. Prices are estimates, not insurer quotes.
export const policyTiers = [
  {
    id: 'POL-PC-001', name: 'Comprehensive Package Policy - Standard', category: 'Private Car',
    type: 'auto_comprehensive',
    coverageSections: ['Section I (Own Damage - Fire, Theft, Accidental Damage)', 'Section II (Third Party Liability)'],
    mandatoryCovers: ['Section III (PA Cover for Owner-Driver)'], deductible: 1000,
    addons: ['Zero Depreciation', 'Road Side Assistance', 'Key Protect', 'Consumables'], basePremium: 12500,
  },
  {
    id: 'POL-PC-002', name: 'Comprehensive Package Policy - Premium', category: 'Private Car',
    type: 'auto_comprehensive',
    coverageSections: ['Section I (Own Damage - Fire, Theft, Accidental Damage)', 'Section II (Third Party Liability)'],
    mandatoryCovers: ['Section III (PA Cover for Owner-Driver)'], deductible: 1000,
    addons: ['Zero Depreciation', 'Consumable Items', 'Engine Protect Plus', 'Return to Invoice', 'Road Side Assistance', 'Key Protect', 'Loss of Personal Belongings', 'Tyre Protect'], basePremium: 18200,
  },
  {
    id: 'POL-PC-003', name: 'Standalone Own Damage Policy', category: 'Private Car',
    type: 'auto_collision',
    coverageSections: ['Section I (Own Damage - Fire, Theft, Accidental Damage)'],
    mandatoryCovers: [], deductible: 1000,
    addons: ['Zero Depreciation', 'Engine Protect Plus', 'Consumable Items', 'Road Side Assistance', 'NCB Protect'], basePremium: 8500,
  },
  {
    id: 'POL-PC-004', name: 'Third Party Liability Only Policy', category: 'Private Car',
    type: 'auto_liability', coverageSections: ['Section II (Third Party Liability)'],
    mandatoryCovers: ['Section III (PA Cover for Owner-Driver)'], deductible: 0, addons: [], basePremium: 2094,
  },
  {
    id: 'POL-PC-005', name: 'EV Comprehensive Package Policy', category: 'Private Car (EV)',
    type: 'auto_comprehensive',
    coverageSections: ['Section I (Own Damage - Battery & Vehicle Damage)', 'Section II (Third Party Liability)'],
    mandatoryCovers: ['Section III (PA Cover for Owner-Driver)'], deductible: 1000,
    addons: ['Battery Protect Cover', 'Zero Depreciation', 'Road Side Assistance', 'Key Protect', 'Cyber Risk Cover'], basePremium: 15400,
  },
  {
    id: 'POL-PC-006', name: 'Pay As You Drive (Telematics) Policy', category: 'Private Car',
    type: 'auto_comprehensive',
    coverageSections: ['Section I (Own Damage - Usage Based)', 'Section II (Third Party Liability)'],
    mandatoryCovers: ['Section III (PA Cover for Owner-Driver)'], deductible: 1000,
    addons: ['Zero Depreciation', 'Road Side Assistance', 'Telematics Protect'], basePremium: 9800,
  },
  {
    id: 'POL-TW-007', name: 'Two Wheeler Comprehensive Package Policy', category: 'Two-Wheeler',
    type: 'auto_comprehensive', coverageSections: ['Section I (Own Damage)', 'Section II (Third Party Liability)'],
    mandatoryCovers: ['Section III (PA Cover for Owner-Driver)'], deductible: 100,
    addons: ['Zero Depreciation', 'Key Protect', 'Road Side Assistance'], basePremium: 1850,
  },
  {
    id: 'POL-TW-008', name: 'Two Wheeler Third Party Liability Policy', category: 'Two-Wheeler',
    type: 'auto_liability', coverageSections: ['Section II (Third Party Liability)'],
    mandatoryCovers: ['Section III (PA Cover for Owner-Driver)'], deductible: 0, addons: [], basePremium: 714,
  },
]
