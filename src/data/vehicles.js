export const mockVehicles = [
  {
    id: 1,
    customerId: 1,
    make: 'Toyota',
    model: 'Camry',
    year: 2022,
    vin: '1HGCM82633A123456',
    color: 'Silver',
    licensePlate: 'ABC-1234',
    registrationExpiry: '2025-06-15',
    purchaseDate: '2022-03-10',
    purchasePrice: 28500,
    currentMileage: 24500,
    fuelType: 'Gasoline',
    transmission: 'Automatic',
    status: 'active',
    policyId: 'POL-2024-005678',
    claims: [
      { id: 'CLM-2024-001234', date: '2024-02-15', type: 'Collision', amount: 3200, status: 'approved' },
      { id: 'CLM-2023-000891', date: '2023-11-20', type: 'Comprehensive', amount: 1500, status: 'closed' },
    ],
    documents: [
      { name: 'Registration', type: 'registration', uploadedAt: '2024-01-15' },
      { name: 'Inspection Report', type: 'inspection', uploadedAt: '2024-01-10' },
    ],
  },
  {
    id: 2,
    customerId: 1,
    make: 'Honda',
    model: 'Accord',
    year: 2020,
    vin: '1HGCV1F30LA123456',
    color: 'Blue',
    licensePlate: 'XYZ-7890',
    registrationExpiry: '2024-12-01',
    purchaseDate: '2020-05-15',
    purchasePrice: 25000,
    currentMileage: 45200,
    fuelType: 'Gasoline',
    transmission: 'CVT',
    status: 'sold',
    policyId: 'POL-2023-004521',
    claims: [
      { id: 'CLM-2023-000456', date: '2023-06-10', type: 'Collision', amount: 4500, status: 'closed' },
    ],
    documents: [
      { name: 'Registration', type: 'registration', uploadedAt: '2023-01-15' },
      { name: 'Bill of Sale', type: 'sale', uploadedAt: '2024-01-20' },
    ],
  },
]

export const mockVehicleStats = {
  totalVehicles: 2,
  activeVehicles: 1,
  totalClaims: 3,
  totalClaimAmount: 9200,
}

export default { mockVehicles, mockVehicleStats }