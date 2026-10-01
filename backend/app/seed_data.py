"""Reference catalogue used by the seed command: areas, services and pricing options.

Prices are in TZS. These are starting values only — admins manage them afterwards.
"""

from decimal import Decimal as D

CITY = {"name": "Dar es Salaam", "region": "Dar es Salaam", "country_code": "TZ"}

AREAS = [
    "Mikocheni",
    "Masaki",
    "Oysterbay",
    "Kinondoni",
    "Sinza",
    "Mbezi",
    "Mwenge",
    "Upanga",
    "Msasani",
    "Kijitonyama",
]

PROPERTY_TYPES = [
    ("apartment", "Apartment / flat", "Apartment / fleti", D(0), 0),
    ("standalone_house", "Standalone house", "Nyumba ya kujitegemea", D(10000), 30),
    ("villa", "Villa / maisonette", "Villa / ghorofa", D(20000), 60),
]

SERVICES = [
    {
        "slug": "general-home-cleaning",
        "name_en": "General Home Cleaning",
        "name_sw": "Usafi wa Kawaida wa Nyumbani",
        "summary_en": "Regular tidy-up of living areas, kitchen, bedrooms and bathrooms.",
        "summary_sw": "Usafi wa kawaida wa sebule, jiko, vyumba vya kulala na mabafu.",
        "description_en": (
            "Dusting, sweeping and mopping of all rooms, wiping kitchen surfaces and appliances, "
            "cleaning bathrooms and toilets, making beds and taking out the rubbish. "
            "Your cleaner brings all materials and equipment."
        ),
        "description_sw": (
            "Kufuta vumbi, kufagia na kupiga deki vyumba vyote, kusafisha sehemu za jikoni na vifaa, "
            "kusafisha mabafu na vyoo, kutandika vitanda na kutoa taka. "
            "Msafishaji huja na vifaa na dawa zote za usafi."
        ),
        "icon": "home",
        "display_order": 1,
        "base_price": D(35000),
        "base_duration_minutes": 150,
        "uses_rooms": True,
        "included_bedrooms": 1,
        "included_bathrooms": 1,
        "price_per_extra_bedroom": D(8000),
        "price_per_extra_bathroom": D(5000),
        "minutes_per_extra_room": 30,
        "max_rooms": 8,
        "property_types": [(c, en, sw, p * D("0.5"), m // 2) for c, en, sw, p, m in PROPERTY_TYPES],
        "addons": [
            ("inside_fridge", "Inside the fridge", "Ndani ya friji", D(8000), 30, 1),
            ("inside_oven", "Inside the oven", "Ndani ya oveni", D(8000), 30, 1),
            ("interior_windows", "Interior windows", "Madirisha ya ndani", D(10000), 45, 1),
            ("laundry_ironing", "Laundry & ironing (per load)", "Kufua na kunyoosha nguo (kwa mzigo)", D(7000), 45, 4),
            ("balcony", "Balcony / veranda", "Balcony / veranda", D(5000), 20, 1),
        ],
    },
    {
        "slug": "deep-cleaning",
        "name_en": "Deep Cleaning",
        "name_sw": "Usafi wa Kina",
        "summary_en": "Top-to-bottom clean including hard-to-reach areas, grout and fittings.",
        "summary_sw": "Usafi wa kina kuanzia juu hadi chini, ikiwemo sehemu zisizofikika kirahisi.",
        "description_en": (
            "Everything in a general clean plus scrubbing tiles and grout, descaling taps and showers, "
            "cleaning skirting boards, doors, switches, fans and light fittings, and wiping inside "
            "cupboards on request. Ideal every few months or before a special occasion."
        ),
        "description_sw": (
            "Kila kitu kilicho kwenye usafi wa kawaida pamoja na kusugua vigae na maungio yake, kuondoa "
            "ukoko kwenye bomba na bafu, kusafisha milango, swichi, feni na taa. Inafaa kila baada ya "
            "miezi michache au kabla ya sherehe."
        ),
        "icon": "sparkles",
        "display_order": 2,
        "base_price": D(70000),
        "base_duration_minutes": 240,
        "uses_rooms": True,
        "included_bedrooms": 1,
        "included_bathrooms": 1,
        "price_per_extra_bedroom": D(15000),
        "price_per_extra_bathroom": D(10000),
        "minutes_per_extra_room": 45,
        "max_rooms": 8,
        "property_types": [(c, en, sw, p * D("1.5"), m) for c, en, sw, p, m in PROPERTY_TYPES],
        "addons": [
            ("inside_cabinets", "Inside kitchen cabinets", "Ndani ya makabati ya jikoni", D(10000), 45, 1),
            ("inside_fridge", "Inside the fridge", "Ndani ya friji", D(8000), 30, 1),
            ("inside_oven", "Inside the oven", "Ndani ya oveni", D(8000), 30, 1),
            ("wall_spot_cleaning", "Wall spot cleaning", "Kusafisha madoa ukutani", D(12000), 45, 1),
        ],
    },
    {
        "slug": "office-cleaning",
        "name_en": "Office Cleaning",
        "name_sw": "Usafi wa Ofisi",
        "summary_en": "Workspace cleaning for desks, meeting rooms, kitchenettes and washrooms.",
        "summary_sw": "Usafi wa ofisi: meza, vyumba vya mikutano, jiko dogo na vyoo.",
        "description_en": (
            "Dusting and sanitising desks and shared surfaces, vacuuming or mopping floors, cleaning "
            "meeting rooms, washrooms and kitchenettes, and emptying bins. Scheduled around your hours."
        ),
        "description_sw": (
            "Kufuta na kutakasa meza na sehemu za pamoja, kusafisha sakafu, vyumba vya mikutano, "
            "vyoo na jiko dogo, na kumwaga mapipa ya taka. Tunapanga kulingana na saa zenu za kazi."
        ),
        "icon": "building",
        "display_order": 3,
        "base_price": D(60000),
        "base_duration_minutes": 180,
        "uses_rooms": False,
        "included_bedrooms": 0,
        "included_bathrooms": 0,
        "price_per_extra_bedroom": D(0),
        "price_per_extra_bathroom": D(0),
        "minutes_per_extra_room": 0,
        "max_rooms": 1,
        "sizes": [
            ("small", "Small office (up to 100 m²)", "Ofisi ndogo (hadi m² 100)", D(0), 0),
            ("medium", "Medium office (100–250 m²)", "Ofisi ya kati (m² 100–250)", D(40000), 120),
            ("large", "Large office (250–500 m²)", "Ofisi kubwa (m² 250–500)", D(100000), 300),
        ],
        "addons": [
            ("kitchenette", "Kitchenette & pantry", "Jiko dogo na stoo", D(10000), 30, 1),
            ("office_windows", "Interior glass & windows", "Vioo na madirisha ya ndani", D(20000), 60, 1),
        ],
    },
    {
        "slug": "move-in-move-out",
        "name_en": "Move-In / Move-Out Cleaning",
        "name_sw": "Usafi wa Kuhamia / Kuhama",
        "summary_en": "Empty-home clean so you can hand over keys or settle in with confidence.",
        "summary_sw": "Usafi wa nyumba tupu kabla ya kukabidhi funguo au kuhamia.",
        "description_en": (
            "A thorough clean of an empty property: inside wardrobes and cabinets, floors, walls marks, "
            "bathrooms, kitchen, windows and fittings. Perfect for tenants, landlords and agents."
        ),
        "description_sw": (
            "Usafi kamili wa nyumba tupu: ndani ya kabati, sakafu, madoa ukutani, mabafu, jiko, "
            "madirisha na vifaa. Inafaa kwa wapangaji, wenye nyumba na madalali."
        ),
        "icon": "truck",
        "display_order": 4,
        "base_price": D(90000),
        "base_duration_minutes": 300,
        "uses_rooms": True,
        "included_bedrooms": 1,
        "included_bathrooms": 1,
        "price_per_extra_bedroom": D(20000),
        "price_per_extra_bathroom": D(10000),
        "minutes_per_extra_room": 60,
        "max_rooms": 8,
        "property_types": [(c, en, sw, p * D(2), m) for c, en, sw, p, m in PROPERTY_TYPES],
        "addons": [
            ("inside_wardrobes", "Inside wardrobes & cabinets", "Ndani ya kabati za nguo na jikoni", D(15000), 60, 1),
            ("wall_washing", "Wall washing", "Kuosha kuta", D(20000), 90, 1),
        ],
    },
    {
        "slug": "sofa-carpet-cleaning",
        "name_en": "Sofa & Carpet Cleaning",
        "name_sw": "Usafi wa Sofa na Zulia",
        "summary_en": "Shampoo and extraction cleaning for sofas, carpets, rugs and mattresses.",
        "summary_sw": "Kusafisha sofa, mazulia na magodoro kwa shampuu na mashine ya kufyonza.",
        "description_en": (
            "Fabric-safe shampoo and extraction cleaning that lifts stains, dust and odours. "
            "Price includes a sofa of up to 3 seats; add extra seats, rugs or mattresses below."
        ),
        "description_sw": (
            "Usafi salama wa vitambaa kwa shampuu na mashine unaoondoa madoa, vumbi na harufu. "
            "Bei inajumuisha sofa ya hadi viti 3; ongeza viti, mazulia au magodoro hapa chini."
        ),
        "icon": "sofa",
        "display_order": 5,
        "base_price": D(30000),
        "base_duration_minutes": 90,
        "uses_rooms": False,
        "included_bedrooms": 0,
        "included_bathrooms": 0,
        "price_per_extra_bedroom": D(0),
        "price_per_extra_bathroom": D(0),
        "minutes_per_extra_room": 0,
        "max_rooms": 1,
        "addons": [
            ("extra_sofa_seat", "Extra sofa seat", "Kiti cha ziada cha sofa", D(7000), 15, 12),
            ("carpet_rug", "Carpet or rug (up to 6 m²)", "Zulia (hadi m² 6)", D(15000), 30, 10),
            ("mattress", "Mattress", "Godoro", D(20000), 30, 6),
        ],
    },
]
