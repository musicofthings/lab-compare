"""Text preprocessing for test name matching."""
import re

# Medical abbreviation expansions
ABBREVIATIONS = {
    "cbc": "complete blood count",
    "esr": "erythrocyte sedimentation rate",
    "lft": "liver function test",
    "kft": "kidney function test",
    "rft": "renal function test",
    "tft": "thyroid function test",
    "hba1c": "glycated hemoglobin",
    "fbs": "fasting blood sugar",
    "ppbs": "post prandial blood sugar",
    "rbs": "random blood sugar",
    "tsh": "thyroid stimulating hormone",
    "ft3": "free triiodothyronine",
    "ft4": "free thyroxine",
    "t3": "triiodothyronine",
    "t4": "thyroxine",
    "psa": "prostate specific antigen",
    "afp": "alpha fetoprotein",
    "hiv": "human immunodeficiency virus",
    "hbsag": "hepatitis b surface antigen",
    "crp": "c reactive protein",
    "ana": "antinuclear antibody",
    "anca": "anti neutrophil cytoplasmic antibody",
    "apla": "anti phospholipid antibody",
    "mp": "malarial parasite",
    "g6pd": "glucose 6 phosphate dehydrogenase",
    "ldh": "lactate dehydrogenase",
    "sgot": "aspartate aminotransferase",
    "sgpt": "alanine aminotransferase",
    "ast": "aspartate aminotransferase",
    "alt": "alanine aminotransferase",
    "ggt": "gamma glutamyl transferase",
    "alp": "alkaline phosphatase",
    "bun": "blood urea nitrogen",
    "cea": "carcinoembryonic antigen",
    "ca125": "cancer antigen 125",
    "ca199": "cancer antigen 19 9",
    "hcg": "human chorionic gonadotropin",
    "bhcg": "beta human chorionic gonadotropin",
    "ige": "immunoglobulin e",
    "igg": "immunoglobulin g",
    "igm": "immunoglobulin m",
    "iga": "immunoglobulin a",
    "pt": "prothrombin time",
    "inr": "international normalized ratio",
    "aptt": "activated partial thromboplastin time",
    "bnp": "brain natriuretic peptide",
    "cpk": "creatine phosphokinase",
    "ck": "creatine kinase",
    "acth": "adrenocorticotropic hormone",
    "dhea": "dehydroepiandrosterone",
    "fsh": "follicle stimulating hormone",
    "lh": "luteinizing hormone",
    "amh": "anti mullerian hormone",
    "vdrl": "venereal disease research laboratory",
    "widal": "widal",
    "rbc": "red blood cell",
    "wbc": "white blood cell",
    "hb": "hemoglobin",
    "plt": "platelet",
    "mcv": "mean corpuscular volume",
    "mch": "mean corpuscular hemoglobin",
    "mchc": "mean corpuscular hemoglobin concentration",
    "rdw": "red cell distribution width",
    "mpv": "mean platelet volume",
    "pcv": "packed cell volume",
    "aso": "anti streptolysin o",
    "rf": "rheumatoid factor",
    "dna": "deoxyribonucleic acid",
    "rna": "ribonucleic acid",
    "pcr": "polymerase chain reaction",
    "fish": "fluorescence in situ hybridization",
    "ihc": "immunohistochemistry",
    "elisa": "enzyme linked immunosorbent assay",
    "clia": "chemiluminescence immunoassay",
    "hplc": "high performance liquid chromatography",
    "gc ms": "gas chromatography mass spectrometry",
    "lc ms": "liquid chromatography mass spectrometry",
}

# Specimen suffixes to strip for matching
SPECIMEN_SUFFIXES = [
    r",?\s*(edta\s+)?(whole\s+)?blood\s*$",
    r",?\s*serum\s*$",
    r",?\s*plasma\s*$",
    r",?\s*urine(\s+24\s*hrs?)?\s*$",
    r",?\s*heparin\s+(blood|bone\s+marrow)\s*$",
    r",?\s*citrate\s+plasma\s*$",
    r",?\s*csf\s*$",
    r",?\s*stool\s*$",
    r",?\s*sputum\s*$",
    r",?\s*tissue\s*$",
    r",?\s*dried\s+blood\s+spot\s*$",
    r",?\s*edta\s+plasma\s*$",
    r",?\s*fluoride\s+plasma\s*$",
    r",?\s*body\s+fluid\s*$",
    r",?\s*synovial\s+fluid\s*$",
    r",?\s*peritoneal\s+fluid\s*$",
    r",?\s*pleural\s+fluid\s*$",
]

# Noise patterns to remove
NOISE_PATTERNS = [
    r"\s*package\s+in\s+new\s*delhi\s*",
    r"\s*\*+\s*",
    r"\s*\(quantitative\)\s*",
    r"\s*\(qualitative\)\s*",
    r"\s*-\s*quantitative\s*$",
    r"\s*-\s*qualitative\s*$",
]


def normalize_test_name(name: str) -> str:
    """Clean and normalize a test name for comparison."""
    text = name.lower().strip()

    # Remove noise
    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    # Remove specimen suffixes
    for pattern in SPECIMEN_SUFFIXES:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Normalize punctuation: remove commas, dashes, parens, slashes
    text = re.sub(r"[,\-/():\[\]{}\"']+", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def expand_abbreviations(name: str) -> str:
    """Expand known medical abbreviations in a normalized name."""
    words = name.lower().split()
    expanded = []
    for w in words:
        if w in ABBREVIATIONS:
            expanded.append(ABBREVIATIONS[w])
        else:
            expanded.append(w)
    return " ".join(expanded)


def tokenize(name: str) -> set[str]:
    """Split a normalized name into meaningful tokens."""
    text = normalize_test_name(name)
    # Only keep tokens with 2+ chars, skip pure numbers
    tokens = {t for t in re.findall(r"[a-z]{2,}", text)}
    return tokens


def tokenize_expanded(name: str) -> set[str]:
    """Tokenize with abbreviation expansion."""
    norm = normalize_test_name(name)
    expanded = expand_abbreviations(norm)
    return {t for t in re.findall(r"[a-z]{2,}", expanded)}
