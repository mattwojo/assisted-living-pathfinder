"""Fictional sample communities so search and review work on a fresh database."""

from __future__ import annotations

import struct
import zlib
from datetime import date

from backend.app.db import LOCK, connect, upload_dir
from backend.app.repository import add_photo, create_facility, revalidate
from backend.app.security import hash_password

DEMO_PASSWORD = "pathfinder"


def solid_png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
            chunk(b"IDAT", zlib.compress(raw, 9)),
            chunk(b"IEND", b""),
        ]
    )


def _community(**kwargs):
    base = {
        "description": "",
        "phone": "",
        "email": "",
        "website": "",
        "street": "",
        "state": "WA",
        "postal_code": "",
        "care_levels": [],
        "amenities": [],
        "staff_ratio": "",
        "license_number": "",
        "license_state": "WA",
        "beds_available": None,
        "waitlist": False,
        "availability_notes": "",
        "policies": "Ask the community for the residency agreement, the current assessment, and what happens to the monthly rate if care needs change.",
        "pricing_tiers": [],
        "submit": True,
    }
    base.update(kwargs)
    return base


COMMUNITIES = [
    _community(
        name="Cedar & Birch Memory Care",
        description="A small secured memory care community in Bothell with a garden courtyard, a short walking loop, and a daily rhythm built around meals and music.",
        phone="(425) 555-0148",
        email="hello@cedar-birch.example",
        website="https://example.com/cedar-birch",
        street="18820 101st Ave NE",
        city="Bothell",
        postal_code="98011",
        care_levels=["memory_care"],
        amenities=["Secured memory care unit", "Garden", "Medication management", "Transportation"],
        staff_ratio="1:5",
        license_number="WA-MC-44128",
        beds_available=3,
        pricing_tiers=[
            {
                "name": "Memory care studio",
                "care_level": "memory_care",
                "monthly_min": 5400,
                "monthly_max": 6200,
                "includes": "meals, personal care, activities, and housekeeping",
            }
        ],
        photo_color=(78, 112, 89),
        photo_caption="Garden courtyard at Cedar & Birch",
    ),
    _community(
        name="Northshore Gardens",
        description="Assisted living apartments in Bothell for people who want help with meals, medication, and bathing while keeping a private apartment.",
        phone="(425) 555-0172",
        email="hello@northshore-gardens.example",
        street="10210 Main Street",
        city="Bothell",
        postal_code="98011",
        care_levels=["assisted_living"],
        amenities=["Garden", "Pets welcome", "Private rooms", "Transportation", "Fitness room"],
        staff_ratio="1:8",
        license_number="WA-AL-22019",
        beds_available=6,
        pricing_tiers=[
            {
                "name": "Assisted living one-bedroom",
                "care_level": "assisted_living",
                "monthly_min": 3800,
                "monthly_max": 5200,
                "includes": "meals, housekeeping, and a base care package",
            }
        ],
        verify_all=True,
        photo_color=(90, 122, 148),
        photo_caption="Front walk at Northshore Gardens",
    ),
    _community(
        name="Mill Creek Haven",
        description="Memory care near Bothell with secured doors, a household dining room, and respite stays when a family needs a shorter visit.",
        phone="(425) 555-0190",
        email="hello@millcreek-haven.example",
        street="15322 35th Ave SE",
        city="Mill Creek",
        postal_code="98012",
        care_levels=["memory_care"],
        amenities=["Secured memory care unit", "Respite stays", "Medication management", "Garden"],
        staff_ratio="1:6",
        license_number="WA-MC-11880",
        beds_available=2,
        pricing_tiers=[
            {
                "name": "Memory care suite",
                "care_level": "memory_care",
                "monthly_min": 5600,
                "monthly_max": 6400,
                "includes": "meals, personal care, and activities",
            }
        ],
        photo_color=(122, 96, 72),
        photo_caption="Household dining room",
    ),
    _community(
        name="Evergreen House Memory Care",
        description="A Seattle memory care house with a higher staff presence during the day and a quieter evening routine.",
        phone="(206) 555-0133",
        email="hello@evergreen-house.example",
        street="814 17th Ave E",
        city="Seattle",
        postal_code="98112",
        care_levels=["memory_care"],
        amenities=["Secured memory care unit", "Garden", "Medication management"],
        staff_ratio="1:4",
        license_number="WA-MC-90211",
        beds_available=1,
        pricing_tiers=[
            {
                "name": "Memory care private room",
                "care_level": "memory_care",
                "monthly_min": 7500,
                "monthly_max": 9200,
                "includes": "meals, personal care, and activities",
            }
        ],
        photo_color=(47, 107, 80),
        photo_caption="Evergreen House entry",
    ),
    _community(
        name="Lakeview Court",
        description="Kirkland community with assisted living apartments and a separate memory care neighborhood.",
        phone="(425) 555-0166",
        email="hello@lakeview-court.example",
        street="410 Lake Street",
        city="Kirkland",
        postal_code="98033",
        care_levels=["assisted_living", "memory_care"],
        amenities=["Secured memory care unit", "Fitness room", "Beauty salon", "Transportation"],
        staff_ratio="1:7",
        license_number="WA-AL-77410",
        beds_available=0,
        waitlist=True,
        availability_notes="Memory care has a short wait. Assisted living has no opening this month.",
        pricing_tiers=[
            {
                "name": "Assisted living studio",
                "care_level": "assisted_living",
                "monthly_min": 4800,
                "monthly_max": 5900,
                "includes": "meals and a base care package",
            },
            {
                "name": "Memory care studio",
                "care_level": "memory_care",
                "monthly_min": 6400,
                "monthly_max": 7100,
                "includes": "meals, personal care, and a secured neighborhood",
            },
        ],
        photo_color=(70, 98, 120),
        photo_caption="Courtyard facing the lake path",
    ),
    _community(
        name="Rainier Ridge Senior Living",
        description="Bellevue independent and assisted living with pets welcome, a fitness room, and scheduled transportation.",
        phone="(425) 555-0114",
        email="hello@rainier-ridge.example",
        street="900 112th Ave NE",
        city="Bellevue",
        postal_code="98004",
        care_levels=["independent_living", "assisted_living"],
        amenities=["Pets welcome", "Fitness room", "Transportation", "Private rooms", "Beauty salon"],
        staff_ratio="1:10",
        license_number="WA-AL-33002",
        beds_available=8,
        pricing_tiers=[
            {
                "name": "Independent living",
                "care_level": "independent_living",
                "monthly_min": 3200,
                "monthly_max": 4100,
                "includes": "one meal a day and housekeeping",
            },
            {
                "name": "Assisted living",
                "care_level": "assisted_living",
                "monthly_min": 4500,
                "monthly_max": 5900,
                "includes": "meals, housekeeping, and a base care package",
            },
        ],
        verify_all=True,
        photo_color=(140, 96, 70),
        photo_caption="Lobby at Rainier Ridge",
    ),
    _community(
        name="Harbor Lights Community",
        description="Edmonds memory care listing used to show what a pricing conflict looks like. The community and an older directory disagree.",
        phone="(425) 555-0188",
        email="hello@harbor-lights.example",
        street="220 Walnut Street",
        city="Edmonds",
        postal_code="98020",
        care_levels=["memory_care"],
        amenities=["Secured memory care unit", "Garden"],
        staff_ratio="1:8",
        license_number="WA-MC-55019",
        beds_available=4,
        pricing_tiers=[
            {
                "name": "Memory care suite",
                "care_level": "memory_care",
                "monthly_min": 5200,
                "monthly_max": 6100,
                "includes": "meals and personal care",
            }
        ],
        owned=True,
        photo_color=(92, 108, 122),
        photo_caption="Harbor Lights front porch",
        external_fact={
            "field_key": "pricing:memory_care_suite",
            "label": "Memory care suite",
            "value_text": "$6,900 per month",
            "source_type": "external",
            "source_label": "Sample regional directory, 2023",
            "verification_status": "unverified",
            "last_checked": "2023-01-15",
            "active": 1,
        },
    ),
]


def _insert_user(connection, email: str, name: str, role: str) -> int:
    cursor = connection.execute(
        """
        INSERT INTO users (email, name, password_hash, role, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (email, name, hash_password(DEMO_PASSWORD), role, date.today().isoformat()),
    )
    return cursor.lastrowid


def seed_if_empty() -> None:
    connection = connect()
    try:
        count = connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
    finally:
        connection.close()
    if count:
        return

    with LOCK:
        connection = connect()
        try:
            rep_id = _insert_user(connection, "rep@example.com", "Avery Chen", "representative")
            _insert_user(connection, "family@example.com", "Jordan Blake", "family")
            _insert_user(connection, "admin@example.com", "Matt Wojo", "admin")
            connection.commit()
        finally:
            connection.close()

    for community in COMMUNITIES:
        payload = {key: value for key, value in community.items() if key not in {"photo_color", "photo_caption", "verify_all", "owned", "external_fact"}}
        if community.get("external_fact"):
            payload["existing_facts"] = [community["external_fact"]]
        owner = rep_id if community.get("owned") or community["name"].startswith("Cedar") else None
        saved = create_facility(owner, payload)
        uploads = upload_dir()
        stored_name = f"seed-{saved['id']}.png"
        (uploads / stored_name).write_bytes(solid_png(960, 600, community["photo_color"]))
        add_photo(saved["id"], owner, stored_name, community["photo_caption"])
        if community.get("verify_all"):
            connection = connect()
            try:
                connection.execute(
                    """
                    UPDATE facts
                    SET verification_status = 'verified', last_checked = ?
                    WHERE facility_id = ? AND active = 1 AND value_text != 'Not recorded'
                    """,
                    (date.today().isoformat(), saved["id"]),
                )
                connection.commit()
            finally:
                connection.close()
            revalidate(saved["id"])
