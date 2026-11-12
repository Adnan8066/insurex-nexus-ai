"""Load a small, realistic Indian motor-insurance demo in one command.

    python manage.py load_demo            # create or refresh the demo data
    python manage.py load_demo --reset    # delete the demo data, then recreate it

Everything this command creates is marked so it can be found and removed again:
users have emails on DEMO_DOMAIN, and customer, policy, claim and investigation
numbers start with "DEMO-". Nothing else in the database is changed.

The staff accounts and the demo customer get a known password, so the command
refuses to run when DEBUG is False unless --allow-production is passed.
"""
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role, User, UserProfile
from apps.claims.models import (
    Claim, ClaimNote, ClaimPriority, ClaimStatus, ClaimStatusHistory, ClaimTimeline,
    IncidentSeverity, IncidentType,
)
from apps.customers.models import Customer
from apps.investigations.models import FraudAlert, Investigation, InvestigationEvidence, InvestigationNote
from apps.notifications.models import Notification
from apps.policies.models import PaymentFrequency, Policy, PolicyCoverage, PolicyStatus, PolicyType
from apps.vehicles.models import Vehicle, VehicleStatus
from common.risk import fraud_risk_band

DEMO_DOMAIN = 'demo.insurex.test'
DEMO_PREFIX = 'DEMO-'
DEFAULT_PASSWORD = 'InsureX@Demo2026'

STAFF = [
    {'key': 'admin', 'email': f'admin@{DEMO_DOMAIN}', 'first_name': 'Ananya', 'last_name': 'Iyer',
     'role': Role.ADMIN, 'department': 'Claims Operations', 'phone': '+91 90000 00010'},
    {'key': 'employee', 'email': f'employee@{DEMO_DOMAIN}', 'first_name': 'Vikram', 'last_name': 'Singh',
     'role': Role.EMPLOYEE, 'department': 'Motor Claims', 'phone': '+91 90000 00011'},
    {'key': 'investigator', 'email': f'investigator@{DEMO_DOMAIN}', 'first_name': 'Meera', 'last_name': 'Kulkarni',
     'role': Role.INVESTIGATOR, 'department': 'Special Investigations Unit', 'phone': '+91 90000 00012'},
]

COMPREHENSIVE_PLAN = {
    'id': 'private-car-package',
    'name': 'Private Car Package (Comprehensive)',
    'category': 'Motor - Private Car',
    'coverage_sections': ['Own damage', 'Third-party liability', 'Personal accident cover for owner-driver'],
    'mandatory_covers': ['Third-party liability', 'Compulsory PA cover (Rs 15 lakh)'],
    'addons': ['Zero depreciation', 'Engine protect', 'Roadside assistance'],
    'estimate_source': 'Demo data; not an insurer quote',
}

# Policy start dates are days before today, so the demo always has active policies.
CUSTOMERS = [
    {
        'key': 'priya', 'login': True, 'email': f'customer@{DEMO_DOMAIN}',
        'first_name': 'Priya', 'last_name': 'Sharma', 'phone': '+91 90000 00001',
        'address': '14, 3rd Cross, Koramangala 4th Block, Bengaluru, Karnataka 560034',
        'dob': (1990, 4, 12), 'license_number': 'KA0120150012345', 'license_state': 'KA',
        'credit_score': 782, 'risk_rating': 'low', 'number': 'DEMO-CUST-0001',
        'vehicles': [
            {'plate': 'KA 01 MJ 4521', 'state': 'KA', 'vin': 'MA3DEM00000000001', 'make': 'Maruti Suzuki',
             'model': 'Swift ZXi', 'year': 2022, 'color': 'Pearl Arctic White', 'purchase': (2022, 3, 15),
             'price': 745000, 'fuel': 'gasoline', 'transmission': 'manual', 'engine': '1.2', 'body': 'Hatchback',
             'mileage': 28400, 'policy': 'DEMO-POL-0001', 'start_days_ago': 300, 'premium': 14850, 'deductible': 1000},
            {'plate': 'KA 03 NB 7780', 'state': 'KA', 'vin': 'MALDEM00000000002', 'make': 'Hyundai',
             'model': 'Creta SX(O)', 'year': 2023, 'color': 'Titan Grey', 'purchase': (2023, 8, 20),
             'price': 1740000, 'fuel': 'diesel', 'transmission': 'automatic', 'engine': '1.5', 'body': 'SUV',
             'mileage': 15200, 'policy': 'DEMO-POL-0002', 'start_days_ago': 120, 'premium': 32600, 'deductible': 2000},
        ],
    },
    {
        'key': 'rahul', 'login': False, 'email': f'rahul.verma@{DEMO_DOMAIN}',
        'first_name': 'Rahul', 'last_name': 'Verma', 'phone': '+91 90000 00002',
        'address': 'House 221, Sector 56, Gurugram, Haryana 122011',
        'dob': (1986, 11, 2), 'license_number': 'HR2620090045678', 'license_state': 'HR',
        'credit_score': 655, 'risk_rating': 'medium', 'number': 'DEMO-CUST-0002',
        'vehicles': [
            {'plate': 'HR 26 DK 3390', 'state': 'HR', 'vin': 'MATDEM00000000003', 'make': 'Tata',
             'model': 'Nexon XZ+', 'year': 2022, 'color': 'Flame Red', 'purchase': (2022, 6, 4),
             'price': 1120000, 'fuel': 'gasoline', 'transmission': 'manual', 'engine': '1.2', 'body': 'Compact SUV',
             'mileage': 41800, 'policy': 'DEMO-POL-0003', 'start_days_ago': 200, 'premium': 21400, 'deductible': 1000},
            # Bought in 2024; insured with us only 55 days ago after switching insurer.
            {'plate': 'DL 8C AF 6612', 'state': 'DL', 'vin': 'MA1DEM00000000004', 'make': 'Mahindra',
             'model': 'Scorpio-N Z8', 'year': 2024, 'color': 'Napoli Black', 'purchase': (2024, 2, 10),
             'price': 2150000, 'fuel': 'diesel', 'transmission': 'automatic', 'engine': '2.2', 'body': 'SUV',
             'mileage': 33600, 'policy': 'DEMO-POL-0004', 'start_days_ago': 55, 'premium': 38900, 'deductible': 2000},
        ],
    },
    {
        'key': 'arjun', 'login': False, 'email': f'arjun.reddy@{DEMO_DOMAIN}',
        'first_name': 'Arjun', 'last_name': 'Reddy', 'phone': '+91 90000 00003',
        'address': '7, Lake View Road, Velachery, Chennai, Tamil Nadu 600042',
        'dob': (1978, 6, 21), 'license_number': 'TN0919990067890', 'license_state': 'TN',
        'credit_score': 741, 'risk_rating': 'low', 'number': 'DEMO-CUST-0003',
        'vehicles': [
            {'plate': 'TN 09 BX 2187', 'state': 'TN', 'vin': 'MA3DEM00000000005', 'make': 'Maruti Suzuki',
             'model': 'Wagon R LXi', 'year': 2011, 'color': 'Silky Silver', 'purchase': (2011, 5, 10),
             'price': 385000, 'fuel': 'gasoline', 'transmission': 'manual', 'engine': '1.0', 'body': 'Hatchback',
             'mileage': 118000, 'policy': 'DEMO-POL-0005', 'start_days_ago': 330, 'premium': 6200, 'deductible': 1000},
            {'plate': 'TN 22 DE 5504', 'state': 'TN', 'vin': 'MZBDEM00000000006', 'make': 'Kia',
             'model': 'Seltos HTX', 'year': 2024, 'color': 'Intense Red', 'purchase': (2024, 1, 18),
             'price': 1590000, 'fuel': 'gasoline', 'transmission': 'cvt', 'engine': '1.5', 'body': 'SUV',
             'mileage': 21900, 'policy': 'DEMO-POL-0006', 'start_days_ago': 250, 'premium': 29700, 'deductible': 2000},
        ],
    },
]

# Each status step is (status, days ago, hour, actor key, reason). The first step is the
# submission, so its date is when the claim was reported. Actor keys are staff keys or 'customer'.
CLAIMS = [
    {
        'number': 'DEMO-CLM-0001', 'plate': 'KA 01 MJ 4521',
        'story': 'Honest minor collision: rear-ended at a signal, small bill, settled and closed',
        'incident_days_ago': 62, 'incident_time': (18, 40), 'type': IncidentType.COLLISION,
        'severity': IncidentSeverity.MODERATE, 'vehicles_involved': 2,
        'location': '80 Feet Road signal, Koramangala, Bengaluru, Karnataka', 'lat': '12.935200', 'lon': '77.624500',
        'witnesses': True, 'witness_details': 'Traffic warden at the junction saw the auto-rickshaw hit the car.',
        'police_report': False, 'claim_amount': 14200, 'estimate': 13800, 'priority': ClaimPriority.LOW,
        'description': 'An auto-rickshaw rear-ended my car while I was stopped at the red light. '
                       'The rear bumper is cracked and the left tail lamp is broken. Repaired cashless at the '
                       'authorised Maruti workshop.',
        'adjuster': 'employee',
        'steps': [
            (ClaimStatus.SUBMITTED, 61, 9, 'customer', 'Claim submitted'),
            (ClaimStatus.UNDER_REVIEW, 59, 11, 'employee', 'Surveyor photos match the description; estimate within range.'),
            (ClaimStatus.APPROVED, 55, 15, 'employee', 'Approved for cashless repair at the authorised workshop.'),
            (ClaimStatus.CLOSED, 48, 17, 'employee', 'Repair completed; Rs 13,200 paid to the workshop after the Rs 1,000 deductible.'),
        ],
        'notes': [('employee', 'Rear bumper and tail lamp only; no structural damage. Low-risk, fast-track.', True)],
    },
    {
        'number': 'DEMO-CLM-0002', 'plate': 'HR 26 DK 3390',
        'story': 'Inflated repair bill: workshop invoice is about 13 times the surveyor estimate',
        'incident_days_ago': 20, 'incident_time': (13, 15), 'type': IncidentType.COLLISION,
        'severity': IncidentSeverity.MODERATE, 'vehicles_involved': 1,
        'location': 'DLF Cyber Hub basement parking, Gurugram, Haryana', 'lat': '28.495500', 'lon': '77.088900',
        'police_report': False, 'claim_amount': 285000, 'estimate': 21500, 'priority': ClaimPriority.HIGH,
        'description': 'Scraped a pillar while parking. The workshop invoice lists a new bonnet, radiator, both '
                       'headlamps and front airbags, but the surveyor found only the front bumper and the left '
                       'headlamp damaged.',
        'adjuster': 'employee',
        'steps': [
            (ClaimStatus.SUBMITTED, 18, 10, 'customer', 'Claim submitted'),
            (ClaimStatus.UNDER_REVIEW, 16, 12, 'employee', 'Workshop invoice (Rs 2,85,000) is far above the surveyor estimate (Rs 21,500). Itemised bill requested.'),
        ],
        'notes': [('employee', 'Airbags were not deployed in the surveyor photos. Asked the workshop for the old parts.', True)],
    },
    {
        'number': 'DEMO-CLM-0003', 'plate': 'DL 8C AF 6612',
        'story': 'Claim 8 days after the policy started, reported 41 days late; damage looks old',
        'incident_days_ago': 47, 'incident_time': (21, 30), 'type': IncidentType.COLLISION,
        'severity': IncidentSeverity.MAJOR, 'vehicles_involved': 1,
        'location': 'NH-48 near Manesar toll plaza, Gurugram, Haryana', 'lat': '28.359400', 'lon': '76.937800',
        'police_report': False, 'claim_amount': 340000, 'estimate': 325000, 'priority': ClaimPriority.HIGH,
        'description': 'Hit the road divider at night on NH-48. Front bumper, grille, bonnet and radiator damaged. '
                       'I was travelling, so I could not report the claim earlier.',
        'adjuster': None,
        'steps': [
            (ClaimStatus.SUBMITTED, 6, 19, 'customer', 'Claim submitted'),
        ],
        'notes': [('employee', 'Surveyor reports surface rust on the dented panels, which suggests the damage is older than 6 weeks.', True)],
    },
    {
        'number': 'DEMO-CLM-0004', 'plate': 'DL 8C AF 6612',
        'story': 'Night-time theft with no police report, on the same new-policy SUV a month after its damage claim',
        'incident_days_ago': 9, 'incident_time': (2, 40), 'type': IncidentType.THEFT,
        'severity': IncidentSeverity.TOTAL_LOSS, 'vehicles_involved': 1,
        'location': 'Outside House 221, Sector 56, Gurugram, Haryana', 'lat': '28.424700', 'lon': '77.104600',
        'police_report': False, 'claim_amount': 1950000, 'estimate': 1950000, 'priority': ClaimPriority.CRITICAL,
        'description': 'Car was parked outside my house at night and was missing at 6 am. Both keys are with me. '
                       'I have not filed an FIR yet because the police station asked me to wait.',
        'adjuster': 'employee',
        'steps': [
            (ClaimStatus.SUBMITTED, 8, 8, 'customer', 'Claim submitted'),
            (ClaimStatus.UNDER_REVIEW, 7, 11, 'employee', 'Theft claim without an FIR. Second claim on this vehicle within a month.'),
            (ClaimStatus.INVESTIGATION, 6, 10, 'employee', 'Investigator assigned'),
        ],
        'notes': [('employee', 'Customer asked to file an FIR and submit both keys. Referred to SIU.', True)],
        'investigation': {
            'number': 'DEMO-INV-0001',
            'summary': 'Theft of a Mahindra Scorpio-N insured 46 days earlier, with no FIR, a month after a '
                       'late-reported damage claim on the same vehicle.',
            'findings': 'FASTag shows the vehicle crossing the Kherki Daula toll at 03:12, 30 minutes after the '
                        'reported theft time. Resident welfare association CCTV requested.',
            'evidence': [
                ('financial', 'FASTag toll crossings', 'NHAI FASTag statement: Kherki Daula toll, 03:12 on the night of the theft.', True),
                ('surveillance', 'RWA gate CCTV request', 'Request sent to the Sector 56 RWA for gate camera footage, 01:00-06:00.', False),
                ('statement', 'Customer statement', 'Customer says both keys are at home and no one else drives the car.', False),
            ],
            'notes': [
                'Called the customer: he says he went to the police station but no FIR was registered. Asked for the station name and the officer he spoke to.',
            ],
        },
    },
    {
        'number': 'DEMO-CLM-0005', 'plate': 'TN 09 BX 2187',
        'story': 'Flood total loss on a 15-year-old car: the model flags it, the adjuster checks and approves at IDV',
        'incident_days_ago': 21, 'incident_time': (23, 0), 'type': IncidentType.WATER_DAMAGE,
        'severity': IncidentSeverity.TOTAL_LOSS, 'vehicles_involved': 1,
        'location': 'Lake View Road, Velachery, Chennai, Tamil Nadu', 'lat': '12.979100', 'lon': '80.218000',
        'property_damage': True, 'property_damage_details': 'Ground floor of the house also flooded.',
        'witnesses': True, 'witness_details': 'Neighbours on Lake View Road; the whole street was under water.',
        'police_report': False, 'claim_amount': 77000, 'estimate': 77000, 'priority': ClaimPriority.MEDIUM,
        'description': 'Northeast monsoon flooding. The car was parked in the street and was submerged in waist-deep '
                       'water overnight. The engine was hydrolocked and the interior and wiring are ruined.',
        'adjuster': 'employee',
        'vehicle_status': VehicleStatus.TOTAL_LOSS,
        'steps': [
            (ClaimStatus.SUBMITTED, 20, 9, 'customer', 'Claim submitted'),
            (ClaimStatus.UNDER_REVIEW, 18, 14, 'employee', 'Surveyor inspection done; IMD red alert for Chennai on the incident date.'),
            (ClaimStatus.APPROVED, 12, 16, 'employee', 'Constructive total loss. Settle at the IDV of Rs 77,000; salvage to be collected.'),
        ],
        'notes': [('employee', 'Repair would cost more than 75% of the IDV, so this is a total loss.', True)],
        # The model scores old-car total losses as risky; the adjuster reviewed and dismissed the alert.
        'alert_review': ('dismissed', 'Flooding confirmed by the IMD red alert and the surveyor visit; '
                                      'many cars on the street were submerged. Genuine claim.'),
    },
    {
        'number': 'DEMO-CLM-0006', 'plate': 'KA 03 NB 7780',
        'story': 'Windshield cracked by a stone on the highway; small glass claim, just submitted',
        'incident_days_ago': 3, 'incident_time': (10, 20), 'type': IncidentType.GLASS,
        'severity': IncidentSeverity.MINOR, 'vehicles_involved': 1,
        'location': 'NH-48, Bengaluru-Tumakuru highway near Nelamangala, Karnataka', 'lat': '13.097600', 'lon': '77.393500',
        'police_report': False, 'claim_amount': 14800, 'estimate': 14500, 'priority': ClaimPriority.LOW,
        'description': 'A stone thrown up by a truck cracked the front windshield. No other damage.',
        'adjuster': None,
        'steps': [
            (ClaimStatus.SUBMITTED, 2, 18, 'customer', 'Claim submitted'),
        ],
        'notes': [],
    },
    {
        'number': 'DEMO-CLM-0007', 'plate': 'TN 22 DE 5504',
        'story': 'Three-vehicle accident with injuries, FIR and witnesses; under review',
        'incident_days_ago': 10, 'incident_time': (8, 45), 'type': IncidentType.COLLISION,
        'severity': IncidentSeverity.MAJOR, 'vehicles_involved': 3,
        'location': 'GST Road near Tambaram, Chennai, Tamil Nadu', 'lat': '12.924900', 'lon': '80.127900',
        'injuries': True,
        'injury_details': 'Driver of the other car: fractured wrist. Policyholder: minor bruises, treated and discharged at a Tambaram hospital.',
        'property_damage': True, 'property_damage_details': 'Median railing damaged.',
        'witnesses': True, 'witness_details': 'Traffic constable on duty and a passenger on the MTC bus behind.',
        'police_report': True, 'police_report_number': 'FIR 412/2026, Tambaram Traffic Investigation Wing',
        'claim_amount': 84500, 'estimate': 82000, 'priority': ClaimPriority.HIGH,
        'description': 'A lorry braked suddenly in morning traffic; the car in front of me stopped and I hit it, '
                       'then the bus behind hit my car. Front and rear damage.',
        'adjuster': 'employee',
        'steps': [
            (ClaimStatus.SUBMITTED, 9, 12, 'customer', 'Claim submitted'),
            (ClaimStatus.UNDER_REVIEW, 7, 10, 'employee', 'FIR and medical records received. Third-party injury claim to be handled separately.'),
        ],
        'notes': [('employee', 'Front and rear damage is consistent with a three-vehicle pile-up.', True)],
    },
]


def _demo_email(email):
    return (email or '').lower().endswith('@' + DEMO_DOMAIN)


class Command(BaseCommand):
    help = (
        'Load a small Indian motor-insurance demo: 4 logins (admin, employee, investigator, customer) on '
        f'@{DEMO_DOMAIN}, 3 customers with cars and active policies, and 7 claims scored by the AI. '
        'Safe to run again; --reset deletes only the demo data and recreates it. '
        'Because it creates accounts with a known password, it refuses to run when DEBUG is False '
        'unless --allow-production is passed.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--password', default=DEFAULT_PASSWORD,
                            help=f'Password for the demo logins (default: {DEFAULT_PASSWORD}).')
        parser.add_argument('--reset', action='store_true',
                            help='Delete the demo data (and only the demo data), then recreate it.')
        parser.add_argument('--allow-production', action='store_true',
                            help='Run even when DEBUG is False. This creates accounts with a known password.')
        parser.add_argument('--skip-assessment', action='store_true',
                            help='Do not run the AI assessment on the demo claims.')

    def handle(self, *args, **options):
        if not settings.DEBUG and not options['allow_production']:
            raise CommandError(
                'Refusing to load demo data while DEBUG is False: it creates accounts with a known password. '
                'Pass --allow-production if you really want this.'
            )
        password = options['password']
        if len(password) < 8:
            raise CommandError('The demo password must be at least 8 characters.')

        self.today = timezone.localdate()
        if options['reset']:
            with transaction.atomic():
                self.delete_demo_data()

        with transaction.atomic():
            self.users = self.create_staff(password)
            self.vehicles = {}
            for spec in CUSTOMERS:
                self.create_customer(spec, password)
            claims = [self.create_claim(spec) for spec in CLAIMS]

        results = {}
        if not options['skip_assessment']:
            results = self.assess(claims)
        self.open_investigations(claims)
        self.report(claims, results, password)

    # ----- reset -----

    def delete_demo_data(self):
        demo_users = User.objects.filter(email__iendswith='@' + DEMO_DOMAIN)
        claims = Claim.objects.filter(claim_number__startswith=DEMO_PREFIX, customer__in=demo_users)
        counts = {'claims': claims.count()}
        claims.delete()  # cascades to assessments, alerts, investigations, timeline, notes
        counts['policies'] = Policy.objects.filter(customer__in=demo_users).count()
        Policy.objects.filter(customer__in=demo_users).delete()
        counts['vehicles'] = Vehicle.objects.filter(customer__in=demo_users).count()
        Vehicle.objects.filter(customer__in=demo_users).delete()
        Customer.objects.filter(user__in=demo_users).delete()
        Notification.objects.filter(recipient__in=demo_users).delete()

        from apps.accounts.account_removal import account_history_records
        deleted, kept = 0, []
        for user in list(demo_users):
            # A demo staff login may have been used on real claims; deleting it would
            # cascade into or blank those records, so keep it and reuse it.
            if account_history_records(user):
                kept.append(user.email)
                continue
            user.delete()
            deleted += 1
        self.stdout.write(
            f"Reset: deleted {counts['claims']} demo claims, {counts['policies']} policies, "
            f"{counts['vehicles']} vehicles and {deleted} demo users."
        )
        for email in kept:
            self.stdout.write(self.style.WARNING(
                f'Kept {email}: it is referenced by non-demo records. It will be reused.'
            ))

    # ----- users and customers -----

    def upsert_user(self, *, email, first_name, last_name, role, phone, address='', department='', password=None):
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            username = email.split('@')[0].replace('.', '-')
            username = f'demo-{username}'
            if User.objects.filter(username=username).exists():
                raise CommandError(f'Username {username!r} is already taken by a non-demo account.')
            user = User(email=email, username=username)
        user.first_name, user.last_name = first_name, last_name
        user.role, user.phone, user.address, user.department = role, phone, address, department
        user.is_active, user.is_verified = True, True
        user.is_staff = user.is_superuser = False
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        UserProfile.objects.update_or_create(
            user=user, defaults={'timezone': 'Asia/Kolkata', 'preferred_language': 'en'},
        )
        return user

    def create_staff(self, password):
        users = {}
        for spec in STAFF:
            users[spec['key']] = self.upsert_user(
                email=spec['email'], first_name=spec['first_name'], last_name=spec['last_name'],
                role=spec['role'], phone=spec['phone'], department=spec['department'], password=password,
            )
        return users

    def _check_owned(self, obj, label, owner):
        if obj is not None and not _demo_email(owner.email):
            raise CommandError(f'{label} already exists and belongs to a non-demo account; refusing to change it.')

    def create_customer(self, spec, password):
        user = self.upsert_user(
            email=spec['email'], first_name=spec['first_name'], last_name=spec['last_name'],
            role=Role.CUSTOMER, phone=spec['phone'], address=spec['address'],
            password=password if spec['login'] else None,
        )
        existing = Customer.objects.filter(customer_number=spec['number']).exclude(user=user).first()
        if existing:
            raise CommandError(f"Customer number {spec['number']} belongs to a non-demo account; refusing to change it.")
        dob = datetime(*spec['dob']).date()
        Customer.objects.update_or_create(user=user, defaults={
            'customer_number': spec['number'], 'date_of_birth': dob,
            'license_number': spec['license_number'], 'license_state': spec['license_state'],
            'license_expiry': dob.replace(year=dob.year + 50), 'credit_score': spec['credit_score'],
            'risk_rating': spec['risk_rating'], 'notes': 'Demo customer created by load_demo.',
        })
        if spec['login']:
            self.users['customer'] = user
            self.customer_login = {'email': user.email, 'plate': spec['vehicles'][0]['plate'], 'mobile': spec['phone']}

        for v in spec['vehicles']:
            vehicle = Vehicle.objects.filter(vin=v['vin']).select_related('customer').first()
            self._check_owned(vehicle, f"Vehicle VIN {v['vin']}", vehicle.customer if vehicle else None)
            vehicle, _ = Vehicle.objects.update_or_create(vin=v['vin'], defaults={
                'customer': user, 'make': v['make'], 'model': v['model'], 'year': v['year'],
                'color': v['color'], 'license_plate': v['plate'], 'license_state': v['state'],
                'purchase_date': datetime(*v['purchase']).date(), 'purchase_price': Decimal(v['price']),
                'current_mileage': v['mileage'], 'fuel_type': v['fuel'], 'transmission': v['transmission'],
                'engine_size': Decimal(v['engine']), 'body_style': v['body'],
                'registration_expiry': datetime(*v['purchase']).date().replace(year=v['purchase'][0] + 15),
                'status': VehicleStatus.ACTIVE,
            })
            policy = Policy.objects.filter(policy_number=v['policy']).select_related('customer').first()
            self._check_owned(policy, f"Policy {v['policy']}", policy.customer if policy else None)
            start = self.today - timedelta(days=v['start_days_ago'])
            idv = round(v['price'] * 0.7, -3)
            policy, _ = Policy.objects.update_or_create(policy_number=v['policy'], defaults={
                'customer': user, 'agent': self.users['employee'], 'type': PolicyType.AUTO_COMPREHENSIVE,
                'status': PolicyStatus.ACTIVE, 'start_date': start, 'end_date': start + timedelta(days=364),
                'premium': Decimal(v['premium']), 'deductible': Decimal(v['deductible']),
                'payment_frequency': PaymentFrequency.ANNUAL, 'auto_renew': True, 'vehicle': vehicle,
                'coverage': {'policy_plan': {**COMPREHENSIVE_PLAN, 'base_premium_estimate_inr': v['premium']},
                             'idv_inr': idv, 'demo': True},
            })
            PolicyCoverage.objects.update_or_create(policy=policy, defaults={
                'liability': Decimal('750000'), 'collision': Decimal(idv), 'comprehensive': Decimal(idv),
                'medical_payments': Decimal('1500000'), 'personal_injury_protection': Decimal('1500000'),
                'roadside_assistance': True, 'glass_coverage': True,
            })
            vehicle.policy = policy
            vehicle.save(update_fields=['policy', 'updated_at'])
            self.vehicles[v['plate']] = vehicle

    # ----- claims -----

    def _at(self, days_ago, hour, minute=0):
        moment = datetime.combine(self.today - timedelta(days=days_ago), time(hour, minute))
        return timezone.make_aware(moment) if settings.USE_TZ else moment

    def _actor(self, key):
        return self.users['customer'] if key == 'customer' else self.users[key]

    def create_claim(self, spec):
        vehicle = self.vehicles[spec['plate']]
        existing = Claim.objects.filter(claim_number=spec['number']).select_related('customer').first()
        self._check_owned(existing, f"Claim {spec['number']}", existing.customer if existing else None)
        final_status = spec['steps'][-1][0]
        submitted_at = self._at(spec['steps'][0][1], spec['steps'][0][2])
        complexity = min(1.0, 0.2 + min(max(spec['vehicles_involved'] - 1, 0), 3) * 0.12
                         + spec.get('injuries', False) * 0.2 + spec.get('property_damage', False) * 0.12
                         + spec.get('witnesses', False) * 0.08 + spec['police_report'] * 0.08)
        adjuster = self.users[spec['adjuster']] if spec['adjuster'] else None
        investigator = self.users['investigator'] if 'investigation' in spec else None
        defaults = {
            'customer': vehicle.customer, 'policy': vehicle.policy, 'vehicle': vehicle,
            'incident_date': self.today - timedelta(days=spec['incident_days_ago']),
            'incident_time': time(*spec['incident_time']),
            'incident_type': spec['type'], 'incident_severity': spec['severity'],
            'location': spec['location'], 'latitude': Decimal(spec['lat']), 'longitude': Decimal(spec['lon']),
            'number_of_vehicles': spec['vehicles_involved'],
            'injuries': spec.get('injuries', False), 'injury_details': spec.get('injury_details', ''),
            'property_damage': spec.get('property_damage', False),
            'property_damage_details': spec.get('property_damage_details', ''),
            'witnesses': spec.get('witnesses', False), 'witness_details': spec.get('witness_details', ''),
            'police_report': spec['police_report'], 'police_report_number': spec.get('police_report_number', ''),
            'claim_amount': Decimal(spec['claim_amount']), 'estimated_repair_cost': Decimal(spec['estimate']),
            'complexity_score': Decimal(str(round(complexity, 3))),
            'description': spec['description'], 'status': final_status, 'priority': spec['priority'],
            'assigned_adjuster': adjuster, 'assigned_investigator': investigator,
            'closed_at': self._at(*spec['steps'][-1][1:3]) if final_status == ClaimStatus.CLOSED else None,
        }
        claim, _ = Claim.objects.update_or_create(claim_number=spec['number'], defaults=defaults)
        # submitted_at is auto_now_add; the late-report fraud rule reads it, so backdate it.
        Claim.objects.filter(pk=claim.pk).update(submitted_at=submitted_at)
        claim.refresh_from_db()

        if spec.get('vehicle_status'):
            Vehicle.objects.filter(pk=vehicle.pk).update(status=spec['vehicle_status'])

        # Rebuild the audit trail so re-runs do not duplicate it.
        claim.status_history.all().delete()
        claim.timeline.all().delete()
        claim.notes.all().delete()
        Notification.objects.filter(related_object_type='claim', related_object_id=str(claim.pk)).delete()

        previous = ''
        for status, days_ago, hour, actor_key, reason in spec['steps']:
            actor = self._actor(actor_key)
            when = self._at(days_ago, hour)
            history = ClaimStatusHistory.objects.create(
                claim=claim, from_status=previous, to_status=status, reason=reason, changed_by=actor,
            )
            label = dict(ClaimStatus.choices)[status]
            if previous:
                title, description, system = f'Status changed to {label}', reason, False
            else:
                title, description, system = 'Claim Submitted', 'New claim has been submitted', True
            entry = ClaimTimeline.objects.create(
                claim=claim, status=status, title=title, description=description, user=actor, is_system=system,
            )
            ClaimStatusHistory.objects.filter(pk=history.pk).update(changed_at=when)
            ClaimTimeline.objects.filter(pk=entry.pk).update(timestamp=when)
            if status == ClaimStatus.UNDER_REVIEW and adjuster:
                assigned = ClaimTimeline.objects.create(
                    claim=claim, status=status, title='Adjuster Assigned',
                    description=f'Claim assigned to {adjuster.get_full_name()}', user=adjuster,
                )
                ClaimTimeline.objects.filter(pk=assigned.pk).update(timestamp=when + timedelta(minutes=5))
            if status == ClaimStatus.INVESTIGATION and investigator:
                assigned = ClaimTimeline.objects.create(
                    claim=claim, status=status, title='Investigator Assigned',
                    description=f'Claim assigned to investigator {investigator.get_full_name()}', user=adjuster,
                )
                ClaimTimeline.objects.filter(pk=assigned.pk).update(timestamp=when + timedelta(minutes=5))
            notification = Notification.objects.create(
                recipient=claim.customer, notification_type='claim',
                title='Claim submitted' if not previous else 'Claim status updated',
                message=(f'Claim {claim.claim_number} was submitted successfully.' if not previous
                         else f'Claim {claim.claim_number} is now {label}.'),
                link=f'/claims/{claim.id}', related_object_type='claim', related_object_id=str(claim.pk),
                is_read=days_ago > 7,
            )
            Notification.objects.filter(pk=notification.pk).update(sent_at=when)
            previous = status

        for actor_key, content, internal in spec['notes']:
            ClaimNote.objects.create(claim=claim, author=self._actor(actor_key), content=content, is_internal=internal)
        return claim

    # ----- AI and investigation -----

    def assess(self, claims):
        """Score every demo claim. A model failure is reported and does not stop the command."""
        from apps.assessments import ai_views

        results = {}
        for claim in claims:
            try:
                assessment = ai_views.run_claim_assessment(claim)
                results[claim.claim_number] = assessment
            except Exception as exc:  # noqa: BLE001 - any model error must not stop the demo load
                results[claim.claim_number] = exc
                self.stderr.write(self.style.WARNING(
                    f'AI assessment failed for {claim.claim_number}: {exc.__class__.__name__}: {exc}'
                ))
        return results

    def open_investigations(self, claims):
        by_number = {claim.claim_number: claim for claim in claims}
        investigator = self.users['investigator']
        for spec in CLAIMS:
            review = spec.get('alert_review')
            if review:
                last = spec['steps'][-1]
                FraudAlert.objects.filter(claim_id=by_number[spec['number']].pk).update(
                    status=review[0], investigator_notes=review[1],
                    reviewed_by=self.users['employee'], reviewed_at=self._at(last[1], last[2]),
                )
            info = spec.get('investigation')
            if not info:
                continue
            claim = Claim.objects.get(pk=by_number[spec['number']].pk)
            fraud_risk = (claim.ai_assessment or {}).get('fraud_risk') or {}
            score = claim.fraud_risk_score or Decimal('0')
            alert = FraudAlert.objects.filter(claim=claim).first()
            if alert is None:
                alert = FraudAlert(
                    claim=claim, risk_score=score, risk_level=fraud_risk_band(score),
                    risk_factors=fraud_risk.get('factors', []),
                    ai_recommendation='Claim assigned to an investigator for review.',
                )
            alert.assigned_investigator = investigator
            alert.status = 'investigation'
            alert.save()

            existing = Investigation.objects.filter(case_number=info['number']).exclude(claim=claim).exists()
            if existing:
                raise CommandError(f"Investigation {info['number']} belongs to a non-demo claim; refusing to change it.")
            started = self._at(spec['steps'][-1][1], spec['steps'][-1][2])
            investigation, _ = Investigation.objects.update_or_create(claim=claim, defaults={
                'investigator': investigator, 'fraud_alert': alert, 'case_number': info['number'],
                'status': 'in_progress', 'priority': 'critical', 'summary': info['summary'],
                'findings': info['findings'], 'started_at': started,
                'estimated_completion': self.today + timedelta(days=10),
            })
            investigation.evidence.all().delete()
            investigation.notes.all().delete()
            for evidence_type, title, description, key in info['evidence']:
                InvestigationEvidence.objects.create(
                    investigation=investigation, evidence_type=evidence_type, title=title,
                    description=description, collected_by=investigator, is_key_evidence=key,
                )
            for content in info['notes']:
                InvestigationNote.objects.create(investigation=investigation, author=investigator, content=content)

    # ----- output -----

    def report(self, claims, results, password):
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Demo claims'))
        stories = {spec['number']: spec['story'] for spec in CLAIMS}
        for claim in claims:
            claim.refresh_from_db()
            result = results.get(claim.claim_number)
            if isinstance(result, Exception):
                ai = 'AI assessment failed'
            elif result is None:
                ai = 'not assessed'
            else:
                cost = f"Rs {float(result.predicted_repair_cost or 0):,.0f}"
                ai = (f'fraud {float(claim.fraud_risk_score):.1f} ({result.risk_level}), '
                      f'total loss {float(claim.total_loss_probability):.1f}%, AI repair estimate {cost}')
            alert = ' [fraud alert]' if FraudAlert.objects.filter(claim=claim).exists() else ''
            self.stdout.write(f'  {claim.claim_number}  {claim.get_status_display():<14} {ai}{alert}')
            self.stdout.write(f'      {stories[claim.claim_number]}')

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Demo logins'))
        self.stdout.write(f'  Staff (Staff login page), password: {password}')
        for spec in STAFF:
            self.stdout.write(f"    {spec['key']:<13} {spec['email']}")
        login = self.customer_login
        self.stdout.write('  Customer (Customer sign-in page uses email + vehicle number + mobile):')
        self.stdout.write(f"    customer      {login['email']}  vehicle {login['plate']}  mobile {login['mobile']}")
        self.stdout.write(f'                  (password for the API login: {password})')
        self.stdout.write(self.style.SUCCESS('Demo data is ready.'))
