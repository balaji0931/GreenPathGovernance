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
    help = "Seeds initial demo data for GreenPath Waste Governance System with auto-assigned IDs."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding GreenPath Academic Demo Environment..."))

        with transaction.atomic():
            # 1. Super Admin (ID: ADMIN, password: Admin123@)
            admin_user, _ = User.objects.get_or_create(
                username="ADMIN",
                defaults={
                    'email': 'admin@greenpath.gov.in',
                    'first_name': 'Chief',
                    'last_name': 'Administrator',
                    'is_staff': True,
                    'is_superuser': True,
                }
            )
            admin_user.set_password("Admin123@")
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save()
            admin_profile, _ = UserProfile.objects.get_or_create(user=admin_user)
            admin_profile.role = RoleChoices.SUPER_ADMIN
            admin_profile.phone_number = "+91 9900000001"
            admin_profile.save()

            # Superadmin alias for tests
            superadmin_alias, _ = User.objects.get_or_create(
                username="superadmin",
                defaults={
                    'email': 'superadmin@greenpath.gov.in',
                    'first_name': 'Super',
                    'last_name': 'Admin',
                    'is_staff': True,
                    'is_superuser': True,
                }
            )
            superadmin_alias.set_password("admin123")
            superadmin_alias.is_staff = True
            superadmin_alias.is_superuser = True
            superadmin_alias.save()
            sp_profile, _ = UserProfile.objects.get_or_create(user=superadmin_alias)
            sp_profile.role = RoleChoices.SUPER_ADMIN
            sp_profile.save()

            self.stdout.write(self.style.SUCCESS("✓ Super Admin: ADMIN / Admin123@ (and superadmin / admin123)"))

            # 2. Village 1: V001 (Shivaji Gram Panchayat)
            vil_shivaji, _ = Village.objects.get_or_create(
                code="V001",
                defaults={
                    'name': 'Shivaji Gram Panchayat',
                    'district': 'Pune',
                    'state': 'Maharashtra',
                    'is_active': True,
                }
            )
            # Also preserve legacy code if existing
            Village.objects.filter(code="VIL-SHIVAJI-01").delete()

            w_sh1, _ = Ward.objects.get_or_create(village=vil_shivaji, ward_number="Ward 01", defaults={'ward_name': 'North Bazaar Sector'})
            w_sh2, _ = Ward.objects.get_or_create(village=vil_shivaji, ward_number="Ward 02", defaults={'ward_name': 'High School Road'})
            w_sh3, _ = Ward.objects.get_or_create(village=vil_shivaji, ward_number="Ward 03", defaults={'ward_name': 'Riverbank Sector'})

            # Village 2: V002 (Ganesh Gram Panchayat)
            vil_ganesh, _ = Village.objects.get_or_create(
                code="V002",
                defaults={
                    'name': 'Ganesh Gram Panchayat',
                    'district': 'Nagpur',
                    'state': 'Maharashtra',
                    'is_active': True,
                }
            )
            Village.objects.filter(code="VIL-GANESH-02").delete()

            w_ga1, _ = Ward.objects.get_or_create(village=vil_ganesh, ward_number="Ward 01", defaults={'ward_name': 'Temple Sector'})
            w_ga2, _ = Ward.objects.get_or_create(village=vil_ganesh, ward_number="Ward 02", defaults={'ward_name': 'Agricultural Mandi'})
            self.stdout.write(self.style.SUCCESS("✓ Villages: V001 (Shivaji GP) & V002 (Ganesh GP)"))

            # 3. Village Managers: V001-M1, V001-M2, V002-M1
            mgr1, _ = User.objects.get_or_create(
                username="V001-M1",
                defaults={'first_name': 'Ramesh', 'last_name': 'Patil', 'email': 'ramesh@panchayat.in'}
            )
            mgr1.set_password("Manager123@")
            mgr1.save()
            p1, _ = UserProfile.objects.get_or_create(user=mgr1)
            p1.role = RoleChoices.VILLAGE_MANAGER
            p1.village = vil_shivaji
            p1.phone_number = "+91 9822001122"
            p1.save()

            mgr2, _ = User.objects.get_or_create(
                username="V002-M1",
                defaults={'first_name': 'Suresh', 'last_name': 'Deshmukh', 'email': 'suresh@panchayat.in'}
            )
            mgr2.set_password("Manager123@")
            mgr2.save()
            p2, _ = UserProfile.objects.get_or_create(user=mgr2)
            p2.role = RoleChoices.VILLAGE_MANAGER
            p2.village = vil_ganesh
            p2.phone_number = "+91 9822003344"
            p2.save()

            # Manager aliases for backward test compatibility
            for uname, v, p_mgr in [("mgr_shivaji", vil_shivaji, mgr1), ("mgr_ganesh", vil_ganesh, mgr2)]:
                u, _ = User.objects.get_or_create(username=uname, defaults={'first_name': p_mgr.first_name, 'last_name': p_mgr.last_name})
                u.set_password("manager123")
                u.save()
                up, _ = UserProfile.objects.get_or_create(user=u)
                up.role = RoleChoices.VILLAGE_MANAGER
                up.village = v
                up.save()

            self.stdout.write(self.style.SUCCESS("✓ Village Managers: V001-M1 / Manager123@ & V002-M1 / Manager123@"))

            # 4. Waste Collectors: V001-C1, V001-C2, V002-C1
            col1, _ = User.objects.get_or_create(
                username="V001-C1",
                defaults={'first_name': 'Kishore', 'last_name': 'Shinde'}
            )
            col1.set_password("Collector123@")
            col1.save()
            cp1, _ = UserProfile.objects.get_or_create(user=col1)
            cp1.role = RoleChoices.WASTE_COLLECTOR
            cp1.village = vil_shivaji
            cp1.phone_number = "+91 9765001111"
            cp1.save()

            col2, _ = User.objects.get_or_create(
                username="V001-C2",
                defaults={'first_name': 'Sunil', 'last_name': 'Jadhav'}
            )
            col2.set_password("Collector123@")
            col2.save()
            cp2, _ = UserProfile.objects.get_or_create(user=col2)
            cp2.role = RoleChoices.WASTE_COLLECTOR
            cp2.village = vil_shivaji
            cp2.phone_number = "+91 9765002222"
            cp2.save()

            col3, _ = User.objects.get_or_create(
                username="V002-C1",
                defaults={'first_name': 'Prakash', 'last_name': 'Bhosale'}
            )
            col3.set_password("Collector123@")
            col3.save()
            cp3, _ = UserProfile.objects.get_or_create(user=col3)
            cp3.role = RoleChoices.WASTE_COLLECTOR
            cp3.village = vil_ganesh
            cp3.phone_number = "+91 9765003333"
            cp3.save()

            # Collector alias for backward test compatibility
            for uname, v, c_obj in [("collector_shivaji1", vil_shivaji, col1), ("col_shivaji", vil_shivaji, col1)]:
                u, _ = User.objects.get_or_create(username=uname, defaults={'first_name': c_obj.first_name, 'last_name': c_obj.last_name})
                u.set_password("password123")
                u.save()
                up, _ = UserProfile.objects.get_or_create(user=u)
                up.role = RoleChoices.WASTE_COLLECTOR
                up.village = v
                up.save()

            self.stdout.write(self.style.SUCCESS("✓ Waste Collectors: V001-C1 / Collector123@ (Shivaji GP) & V002-C1 / Collector123@ (Ganesh GP)"))

            # 5. Resident Users & Households (Shivaji GP: V001-H1, V001-H2...)
            households_data = [
                # Ward 01
                ("Balaji Patil", "12-A", w_sh1, "Main Bazaar Road", "+91 9800000001", True),
                ("Ananya Deshmukh", "14-B", w_sh1, "Near Post Office", "+91 9800000002", True),
                ("Ganesh Kulkarni", "15-C", w_sh1, "High School Galli", "+91 9800000003", True),
                ("Meena Kamble", "18-D", w_sh1, "Market Chowk", "+91 9800000004", False),
                ("Vijay Salunkhe", "21-E", w_sh1, "Behind Old Temple", "+91 9800000005", False),

                # Ward 02
                ("Rohit Sharma", "31-A", w_sh2, "Stadium Road", "+91 9800000006", False),
                ("Pooja Sawant", "33-B", w_sh2, "Gram Panchayat Path", "+91 9800000007", False),
                ("Deepak Shinde", "35-C", w_sh2, "Vikas Nagar", "+91 9800000008", False),
                ("Sunita Gaikwad", "38-D", w_sh2, "Water Tank Road", "+91 9800000009", False),
                ("Manoj Chavan", "40-E", w_sh2, "School Colony", "+91 9800000010", False),

                # Ward 03
                ("Arun More", "51-A", w_sh3, "River View Sector", "+91 9800000011", False),
                ("Kavita Pawar", "53-B", w_sh3, "Fisherman Colony", "+91 9800000012", False),
                ("Sanjay Rane", "55-C", w_sh3, "Bund Road", "+91 9800000013", False),
                ("Suman Thorat", "58-D", w_sh3, "Canal Edge", "+91 9800000014", False),
                ("Vikas Naik", "60-E", w_sh3, "Old Bridge Area", "+91 9800000015", False),
            ]

            created_households = []
            for idx, (name, h_num, ward, street, phone, create_user) in enumerate(households_data, start=1):
                expected_uid = f"V001-H{idx}"

                hh, _ = Household.objects.get_or_create(
                    village=vil_shivaji,
                    house_number=h_num,
                    defaults={
                        'uid': expected_uid,
                        'ward': ward,
                        'head_name': name,
                        'street_address': street,
                        'phone_number': phone,
                        'is_active': (idx != 15),
                    }
                )
                if hh.uid != expected_uid:
                    hh.uid = expected_uid
                    hh.save()

                if create_user:
                    res_user, _ = User.objects.get_or_create(
                        username=expected_uid,
                        defaults={'first_name': name.split()[0], 'last_name': name.split()[-1]}
                    )
                    res_user.set_password("Resident123@")
                    res_user.save()
                    rp, _ = UserProfile.objects.get_or_create(user=res_user)
                    rp.role = RoleChoices.HOUSEHOLD
                    rp.village = vil_shivaji
                    rp.phone_number = phone
                    rp.save()

                    hh.resident_user = res_user
                    hh.save()

                created_households.append(hh)

            # Test backward compatibility alias for resident
            res_alias, _ = User.objects.get_or_create(
                username="resident_shivaji1",
                defaults={'first_name': 'Balaji', 'last_name': 'Patil'}
            )
            res_alias.set_password("resident123")
            res_alias.save()
            rap, _ = UserProfile.objects.get_or_create(user=res_alias)
            rap.role = RoleChoices.HOUSEHOLD
            rap.village = vil_shivaji
            rap.save()

            self.stdout.write(self.style.SUCCESS(f"✓ Provisioned {len(created_households)} Households in V001 (UIDs: V001-H1 to V001-H{len(created_households)})"))
            self.stdout.write(self.style.SUCCESS("✓ Resident Portal: V001-H1 / Resident123@ (linked to door #12-A)"))

            # 6. Realistic Collection History (Today & Yesterday)
            today = timezone.localdate()
            yesterday = today - datetime.timedelta(days=1)

            # Clear existing demo records for V001
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

            # HH 2: Initially Missed at 08:40 AM (LOCKED), then Revisited & Collected at 11:30 AM
            CollectionRecord.objects.create(
                household=created_households[2],
                collector=cp1,
                village=vil_shivaji,
                ward=created_households[2].ward,
                collection_date=today,
                collection_time=datetime.time(8, 40),
                outcome=OutcomeChoices.MISSED,
                missed_reason=MissedReasonChoices.LOCKED,
                remarks="Gate locked with padlock"
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
                remarks="Revisited after resident returned"
            )

            # HH 3 & 4 (Ward 1): Collected
            for idx in [3, 4]:
                CollectionRecord.objects.create(
                    household=created_households[idx],
                    collector=cp1,
                    village=vil_shivaji,
                    ward=created_households[idx].ward,
                    collection_date=today,
                    collection_time=datetime.time(9, 10 + (idx * 5)),
                    outcome=OutcomeChoices.COLLECTED,
                    is_segregated=True,
                    waste_wet=True,
                    waste_dry=(idx == 3),
                    segregation_rating=(5 if idx == 3 else 3),
                    remarks="Daily collection complete"
                )

            # Ward 2 (Collector Sunil cp2): HH 5, 6, 7 collected, HH 8 mixed waste
            for idx in [5, 6, 7]:
                CollectionRecord.objects.create(
                    household=created_households[idx],
                    collector=cp2,
                    village=vil_shivaji,
                    ward=created_households[idx].ward,
                    collection_date=today,
                    collection_time=datetime.time(9, (idx - 5) * 15),
                    outcome=OutcomeChoices.COLLECTED,
                    is_segregated=True,
                    waste_wet=True,
                    waste_dry=True,
                    segregation_rating=4
                )

            # HH 8: Non-segregated (1 star)
            CollectionRecord.objects.create(
                household=created_households[8],
                collector=cp2,
                village=vil_shivaji,
                ward=created_households[8].ward,
                collection_date=today,
                collection_time=datetime.time(9, 45),
                outcome=OutcomeChoices.COLLECTED,
                is_segregated=False,
                waste_wet=True,
                waste_dry=True,
                segregation_rating=1,
                remarks="Mixed unsegregated wet and dry waste"
            )

            # HH 9 (Ward 2): Collected
            CollectionRecord.objects.create(
                household=created_households[9],
                collector=cp2,
                village=vil_shivaji,
                ward=created_households[9].ward,
                collection_date=today,
                collection_time=datetime.time(10, 0),
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
GREENPATH SEEDING COMPLETE!
------------------------------------------------------------
Log in with auto-assigned IDs:
1. Super Admin:      ADMIN        / Admin123@
2. Village Manager:  V001-M1      / Manager123@
3. Waste Collector:  V001-C1      / Collector123@
4. Household User:   V001-H1      / Resident123@
============================================================
"""))
