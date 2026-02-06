"""Maps lab-specific department names to canonical departments."""

DEPARTMENT_MAP = {
    # Apollo (uppercase)
    "BIOCHEMISTRY": "Biochemistry",
    "BIOCHEMISTRY.": "Biochemistry",
    "CLINICAL CHEMISTRY": "Biochemistry",
    "SPECIAL CHEMISTRY": "Biochemistry",
    "HAEMATOLOGY": "Haematology",
    "SEROLOGY": "Serology",
    "ALLERGY": "Allergy",
    "MICROBIOLOGY": "Microbiology",
    "HISTOPATHOLOGY": "Histopathology",
    "GENOMICS AND MOLECULAR DIAGNOSTICS": "Molecular Biology",
    "MOLECULAR BIOLOGY.": "Molecular Biology",
    "MOLECULAR BIOLOGY": "Molecular Biology",
    "CYTOGENETICS": "Cytogenetics",
    "FLOW CYTOMETRY": "Flow Cytometry",
    "IMMUNOLOGY": "Immunology",
    "IMMUNOHISTOCHEMISTRY": "Immunology",
    "COAGULATION": "Haematology",
    "PACKAGE": "Package",
    "CYTOLOGY": "Cytology",
    "CLINICAL PATHOLOGY": "Clinical Pathology",
    "ENDOCRINOLOGY": "Endocrinology",

    # Agilus (mixed case)
    "Bio Chemistry": "Biochemistry",
    "Haemotology": "Haematology",
    "Hematology": "Haematology",
    "Micro Biology": "Microbiology",
    "Histopath": "Histopathology",
    "Eia - Infectious Section": "Serology",
    "Endocrinology": "Endocrinology",
    "Autoimmune-ifa": "Immunology",
    "Eia - Auto Immune": "Immunology",
    "Coe -histopath": "Histopathology",
    "Advanced Molecular Diagnostics R": "Molecular Biology",
    "Molecular Biology": "Molecular Biology",
    "Flow Cytometry": "Flow Cytometry",
    "Cytogenetics": "Cytogenetics",
    "Clinical Pathology": "Clinical Pathology",

    # TRUSTlab (title case)
    "Biochemistry": "Biochemistry",
    "Serology": "Serology",
    "Histopathology": "Histopathology",
    "Haematology": "Haematology",
    "Microbiology": "Microbiology",
    "Cytogenetics": "Cytogenetics",
    "Cytology": "Cytology",
    "Genomics": "Molecular Biology",
    "Allergy": "Allergy",
    "Immunology": "Immunology",
    "Package": "Package",

    # Neuberg service_type
    "Test": "General",
    "Package": "Package",
}

# All canonical department names
CANONICAL_DEPARTMENTS = sorted(set(DEPARTMENT_MAP.values()))


def normalize_department(raw: str | None) -> str | None:
    """Map a raw department string to canonical form."""
    if not raw:
        return None

    stripped = raw.strip()

    # Direct lookup
    if stripped in DEPARTMENT_MAP:
        return DEPARTMENT_MAP[stripped]

    # Case-insensitive lookup
    lower = stripped.lower()
    for key, val in DEPARTMENT_MAP.items():
        if key.lower() == lower:
            return val

    # Fuzzy contains
    for keyword, dept in [
        ("biochem", "Biochemistry"),
        ("haemat", "Haematology"),
        ("hemat", "Haematology"),
        ("serol", "Serology"),
        ("microb", "Microbiology"),
        ("histop", "Histopathology"),
        ("molecul", "Molecular Biology"),
        ("cytogen", "Cytogenetics"),
        ("immuno", "Immunology"),
        ("allerg", "Allergy"),
        ("cytol", "Cytology"),
        ("endocrin", "Endocrinology"),
        ("flow cyto", "Flow Cytometry"),
        ("clinical path", "Clinical Pathology"),
        ("package", "Package"),
    ]:
        if keyword in lower:
            return dept

    return stripped  # Return as-is if no mapping found


def get_all_departments() -> list[dict]:
    """Return list of canonical department records for seeding."""
    return [{"name": d, "slug": d.lower().replace(" ", "-")} for d in CANONICAL_DEPARTMENTS]
