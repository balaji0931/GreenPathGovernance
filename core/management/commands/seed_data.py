import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction

from accounts.models import UserProfile, RoleChoices
from governance.models import Village, Ward
from households.models import Household
from waste_collections.models import CollectionRecord, OutcomeChoices, MissedReasonChoices

class Command(BaseCommand):
    help = "Seeds initial demo data for GreenPath Waste Governance System evaluation."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding GreenPath Academic Demo Environment..."))

        with transaction.atomic():
            # 1. Super Admin
            admin_user, created = User.objects.get_or_create(
                username="superadmin",
                defaults={
                    'email': 'admin@greenpath.gov.in',
                    'first_name': 'Chief',
                    'last_name': 'Administrator',
                    'is_staff': True,
                    'is_superuser': True,
                }
            )
            admin_user.set_password("admin123")
            admin_user.save()
            admin_profile, _ = UserProfile.objects.get_or_create(user=admin_user)
            admin_profile.role = RoleChoices.SUPER_ADMIN
            admin_profile.phone_number = "+91 9900000001"
            admin_profile.save()
            self.stdout.write(self.style.SUCCESS("✓ Super Admin: superadmin / admin123"))

            # 2. Village 1: Shivaji Gram Panchayat
            vil_shivaji, _ = Village.objects.get_or_create(
                code="VIL-SHIVAJI-01",
                defaults={
                    'name': 'Shivaji Gram Panchayat',
                    'district': 'Pune',
                    'state': 'Maharashtra',
                    'is_active': True,
                }
            )
            w_sh1, _ = Ward.objects.get_or_create(village=vil_shivaji, ward_number="Ward 01", defaults={'ward_name': 'North Bazaar Sector'})
            w_sh2, _ = Ward.objects.get_or_create(village=vil_shivaji, ward_number="Ward 02", defaults={'ward_name': 'High School Road'})
            w_sh3, _ = Ward.objects.get_or_create(village=vil_shivaji, ward_number="Ward 03", defaults={'ward_name': 'Riverbank Sector'})

            # Village 2: Ganesh Gram Panchayat
            vil_ganesh, _ = Village.objects.get_or_create(
                code="VIL-GANESH-02",
                defaults={
                    'name': 'Ganesh Gram Panchayat',
                    'district': 'Nagpur',
                    'state': 'Maharashtra',
                    'is_active': True,
                }
            )
            w_ga1, _ = Ward.objects.get_or_create(village=vil_ganesh, ward_number="Ward 01", defaults={'ward_name': 'Temple Sector'})
            w_ga2, _ = Ward.objects.get_or_create(village=vil_ganesh, ward_number="Ward 02", defaults={'ward_name': 'Agricultural Mandi'})
            self.stdout.write(self.style.SUCCESS("✓ Villages: Shivaji GP (3 Wards) & Ganesh GP (2 Wards)"))

            # 3. Village Managers
            mgr1, _ = User.objects.get_or_create(
                username="mgr_shivaji",
                defaults={'first_name': 'Ramesh', 'last_name': 'Patil', 'email': 'ramesh@panchayat.in'}
            )
            mgr1.set_password("manager123")
            mgr1.save()
            p1, _ = UserProfile.objects.get_or_create(user=mgr1)
            p1.role = RoleChoices.VILLAGE_MANAGER
            p1.village = vil_shivaji
            p1.phone_number = "+91 9822001122"
            p1.save()

            mgr2, _ = User.objects.get_or_create(
                username="mgr_ganesh",
                defaults={'first_name': 'Suresh', 'last_name': 'Deshmukh', 'email': 'suresh@panchayat.in'}
            )
            mgr2.set_password("manager123")
            mgr2.save()
            p2, _ = UserProfile.objects.get_or_create(user=mgr2)
            p2.role = RoleChoices.VILLAGE_MANAGER
            p2.village = vil_ganesh
            p2.phone_number = "+91 9822003344"
            p2.save()
            self.stdout.write(self.style.SUCCESS("✓ Village Managers: mgr_shivaji / manager123 & mgr_ganesh / manager123"))

            # 4. Waste Collectors
            col1, _ = User.objects.get_or_create(
                username="collector_shivaji1",
                defaults={'first_name': 'Kishore', 'last_name': 'Shinde'}
            )
            col1.set_password("collector123")
            col1.save()
            cp1, _ = UserProfile.objects.get_or_create(user=col1)
            cp1.role = RoleChoices.WASTE_COLLECTOR
            cp1.village = vil_shivaji
            cp1.phone_number = "+91 9765001111"
            cp1.save()

            col2, _ = User.objects.get_or_create(
                username="collector_shivaji2",
                defaults={'first_name': 'Sunil', 'last_name': 'Jadhav'}
            )
            col2.set_password("collector123")
            col2.save()
            cp2, _ = UserProfile.objects.get_or_create(user=col2)
            cp2.role = RoleChoices.WASTE_COLLECTOR
            cp2.village = vil_shivaji
            cp2.phone_number = "+91 9765002222"
            cp2.save()

            col3, _ = User.objects.get_or_create(
                username="collector_ganesh1",
                defaults={'first_name': 'Prakash', 'last_name': 'Bhosale'}
            )
            col3.set_password("collector123")
            col3.save()
            cp3, _ = UserProfile.objects.get_or_create(user=col3)
            cp3.role = RoleChoices.WASTE_COLLECTOR
            cp3.village = vil_ganesh
            cp3.phone_number = "+91 9765003333"
            cp3.save()
            self.stdout.write(self.style.SUCCESS("✓ Waste Collectors: collector_shivaji1 / collector123 (Shivaji GP)"))

            # 5. Resident Users & Households (Shivaji GP)
            households_data = [
                # Ward 01
                ("Balaji Patil", "12-A", w_sh1, "Main Bazaar Road", "+91 9800000001", "resident_shivaji1", True),
                ("Ananya Deshmukh", "14-B", w_sh1, "Near Post Office", "+91 9800000002", "resident_shivaji2", True),
                ("Ganesh Kulkarni", "15-C", w_sh1, "High School Galli", "+91 9800000003", "resident_shivaji3", True),
                ("Meena Kamble", "18-D", w_sh1, "Market Chowk", "+91 9800000004", None, True),
                ("Vijay Salunkhe", "21-E", w_sh1, "Behind Old Temple", "+91 9800000005", None, True),

                # Ward 02
                ("Rohit Sharma", "31-A", w_sh2, "Stadium Road", "+91 9800000006", None, True),
                ("Pooja Sawant", "33-B", w_sh2, "Gram Panchayat Path", "+91 9800000007", None, True),
                ("Deepak Shinde", "35-C", w_sh2, "Vikas Nagar", "+91 9800000008", None, True),
                ("Sunita Gaikwad", "38-D", w_sh2, "Water Tank Road", "+91 9800000009", None, True),
                ("Manoj Chavan", "40-E", w_sh2, "School Colony", "+91 9800000010", None, True),

                # Ward 03
                ("Arun More", "51-A", w_sh3, "River View Sector", "+91 9800000011", None, True),
                ("Kavita Pawar", "53-B", w_sh3, "Fisherman Colony", "+91 9800000012", None, True),
                ("Sanjay Rane", "55-C", w_sh3, "Bund Road", "+91 9800000013", None, True),
                ("Suman Thorat", "58-D", w_sh3, "Canal Edge", "+91 9800000014", None, True),
                ("Vikas Naik", "60-E", w_sh3, "Old Bridge Area", "+91 9800000015", None, False),  # Inactive
            ]

            created_households = []
            for name, h_num, ward, street, phone, res_uname, active in households_data:
                res_user = None
                if res_uname:
                    res_user, _ = User.objects.get_or_create(
                        username=res_uname,
                        defaults={'first_name': name.split()[0], 'last_name': name.split()[-1]}
                    )
                    res_user.set_password("resident123")
                    res_user.save()
                    rp, _ = UserProfile.objects.get_or_create(user=res_user)
                    rp.role = RoleChoices.HOUSEHOLD
                    rp.village = vil_shivaji
                    rp.phone_number = phone
                    rp.save()

                hh, _ = Household.objects.get_or_create(
                    village=vil_shivaji,
                    house_number=h_num,
                    defaults={
                        'ward': ward,
                        'head_name': name,
                        'street_address': street,
                        'phone_number': phone,
                        'resident_user': res_user,
                        'is_active': active,
                    }
                )
                created_households.append(hh)

            self.stdout.write(self.style.SUCCESS(f"✓ Provisioned {len(created_households)} Households in Shivaji GP with unique UIDs and QR codes"))
            self.stdout.write(self.style.SUCCESS("✓ Resident Portal: resident_shivaji1 / resident123 (linked to door #12-A)"))

            # 6. Realistic Collection History (Today & Yesterday)
            today = timezone.localdate()
            yesterday = today - datetime.timedelta(days=1)

            # Clear existing demo records to ensure clean deterministic counts
            CollectionRecord.objects.filter(village=vil_shivaji).delete()

            # Record collections for Yesterday
            for idx, hh in enumerate(created_households[:12]):
                hour = 8 + (idx // 4)
                minute = (idx % 4) * 15
                CollectionRecord.objects.create(
                    household=hh,
                    collector=cp1,
                    village=vil_shivaji,
                    ward=hh.ward,
                    collection_date=yesterday,
                    collection_time=datetime.time(hour, minute),
                    outcome=OutcomeChoices.COLLECTED,
                    is_segregated=True,
                    waste_wet=True,
                    waste_dry=True,
                    segregation_rating=(4 if idx % 2 == 0 else 5),
                    remarks="Routine daily visit"
                )

            # Record collections for Today
            # HH 0: Collected (Pristine 5 stars)
            CollectionRecord.objects.create(
                household=created_households[0],
                collector=cp1,
                village=vil_shivaji,
                ward=created_households[0].ward,
                collection_date=today,
                collection_time=datetime.time(8, 15),
                outcome=OutcomeChoices.COLLECTED,
                is_segregated=True,
                waste_wet=True,
                waste_dry=True,
                waste_sanitary=False,
                segregation_rating=5,
                remarks="Flawless 3-way segregation"
            )

            # HH 1: Collected (Good 4 stars)
            CollectionRecord.objects.create(
                household=created_households[1],
                collector=cp1,
                village=vil_shivaji,
                ward=created_households[1].ward,
                collection_date=today,
                collection_time=datetime.time(8, 25),
                outcome=OutcomeChoices.COLLECTED,
                is_segregated=True,
                waste_wet=True,
                waste_dry=True,
                segregation_rating=4,
                remarks="Clean bins"
            )

            # HH 2: Initially Missed at 08:40 AM (LOCKED), then Revisited & Collected at 11:30 AM (FR-25 deduplication showcase)
            CollectionRecord.objects.create(
                household=created_households[2],
                collector=cp1,
                village=vil_shivaji,
                ward=created_households[2].ward,
                collection_date=today,
                collection_time=datetime.time(8, 40),
                outcome=OutcomeChoices.MISSED,
                missed_reason=MissedReasonChoices.LOCKED,
                remarks="Gate padlocked during first round"
            )
            CollectionRecord.objects.create(
                household=created_households[2],
                collector=cp1,
                village=vil_shivaji,
                ward=created_households[2].ward,
                collection_date=today,
                collection_time=datetime.time(11, 30),
                outcome=OutcomeChoices.COLLECTED,
                is_segregated=True,
                waste_wet=True,
                waste_dry=True,
                segregation_rating=4,
                remarks="Revisited after resident returned home"
            )

            # HH 3: Missed (Waste Not Segregated)
            CollectionRecord.objects.create(
                household=created_households[3],
                collector=cp1,
                village=vil_shivaji,
                ward=created_households[3].ward,
                collection_date=today,
                collection_time=datetime.time(9, 0),
                outcome=OutcomeChoices.MISSED,
                missed_reason=MissedReasonChoices.NOT_SEGREGATED,
                remarks="Plastic mixed inside kitchen waste bucket"
            )

            # HH 5 & 6 (Ward 2): Collected
            for h in [created_households[5], created_households[6]]:
                CollectionRecord.objects.create(
                    household=h,
                    collector=cp2,
                    village=vil_shivaji,
                    ward=h.ward,
                    collection_date=today,
                    collection_time=datetime.time(9, 45),
                    outcome=OutcomeChoices.COLLECTED,
                    is_segregated=True,
                    waste_wet=True,
                    waste_dry=True,
                    segregation_rating=5
                )

            # HH 10 (Ward 3): Collected
            CollectionRecord.objects.create(
                household=created_households[10],
                collector=cp1,
                village=vil_shivaji,
                ward=created_households[10].ward,
                collection_date=today,
                collection_time=datetime.time(10, 15),
                outcome=OutcomeChoices.COLLECTED,
                is_segregated=True,
                waste_wet=True,
                waste_dry=True,
                segregation_rating=4
            )

            # HH 11 (Ward 3): Missed (Resident Refused)
            CollectionRecord.objects.create(
                household=created_households[11],
                collector=cp1,
                village=vil_shivaji,
                ward=created_households[11].ward,
                collection_date=today,
                collection_time=datetime.time(10, 30),
                outcome=OutcomeChoices.MISSED,
                missed_reason=MissedReasonChoices.REFUSED,
                remarks="Resident stated composting at home"
            )

            self.stdout.write(self.style.SUCCESS("✓ Seeded realistic doorstep collection visits for Today and Yesterday"))

        self.stdout.write(self.style.SUCCESS("""
============================================================
GREENPATH DEMO SEEDING COMPLETE!
------------------------------------------------------------
Log in with any of the 4 operational roles:
1. Super Admin:      superadmin           / admin123
2. Village Manager:  mgr_shivaji          / manager123
3. Waste Collector:  collector_shivaji1   / collector123
4. Household User:   resident_shivaji1    / resident123
============================================================
"""))
