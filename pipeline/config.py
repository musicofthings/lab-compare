import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)))

CSV_FILES = {
    "metropolis": os.path.join(DATA_DIR, "metropolis_tests_directory.csv"),
    "agilus": os.path.join(DATA_DIR, "agilus_tests_directory.csv"),
    "apollo": os.path.join(DATA_DIR, "apollo_tests_directory.csv"),
    "neuberg": os.path.join(DATA_DIR, "neuberg_tests_directory.csv"),
    "trustlab": os.path.join(DATA_DIR, "trustlab_tests_directory.csv"),
}

BATCH_SIZE = 500
MATCH_THRESHOLD = 0.60
HIGH_CONFIDENCE_THRESHOLD = 0.85
