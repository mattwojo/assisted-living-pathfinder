"""Shared labels for care, amenities, and geography."""

CARE_LEVELS = {
    "independent_living": "Independent living",
    "assisted_living": "Assisted living",
    "memory_care": "Memory care",
    "skilled_nursing": "Skilled nursing",
}

AMENITIES = [
    "Secured memory care unit",
    "Garden",
    "Medication management",
    "Transportation",
    "Pets welcome",
    "Private rooms",
    "Fitness room",
    "Beauty salon",
    "Respite stays",
    "Physical therapy",
]

# Cities that are a short drive from one another, used when a search says "near".
NEIGHBORS = {
    "bothell": ["kenmore", "woodinville", "mill creek", "kirkland", "lynnwood"],
    "mill creek": ["bothell", "lynnwood", "everett"],
    "kirkland": ["bellevue", "redmond", "bothell", "kenmore"],
    "bellevue": ["kirkland", "redmond", "seattle"],
    "seattle": ["shoreline", "edmonds", "bellevue"],
    "edmonds": ["lynnwood", "shoreline", "seattle"],
    "lynnwood": ["edmonds", "mill creek", "bothell"],
    "redmond": ["bellevue", "kirkland"],
    "kenmore": ["bothell", "kirkland"],
    "woodinville": ["bothell", "redmond"],
    "everett": ["mill creek", "lynnwood"],
    "shoreline": ["seattle", "edmonds"],
}

SOURCE_LABELS = {
    "facility_provided": "Provided by the community",
    "external": "External directory",
    "verified": "Independently verified",
}

STATUS_LABELS = {
    "unverified": "Not yet verified",
    "verified": "Verified",
    "conflict": "Conflicting information",
    "stale": "May be out of date",
    "draft": "Draft",
    "pending_review": "Waiting for review",
}

DISCLAIMER = (
    "This is general information to help you compare communities. "
    "It is not legal, medical, or financial advice. Confirm details "
    "with the community and with a qualified professional before you decide."
)
