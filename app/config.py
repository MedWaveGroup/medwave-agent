import os
from dotenv import load_dotenv

load_dotenv()

# Facebook Ads
FB_APP_ID = os.getenv("FB_APP_ID", "")
FB_APP_SECRET = os.getenv("FB_APP_SECRET", "")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN", "")
FB_AD_ACCOUNT_ID = os.getenv("FB_AD_ACCOUNT_ID", "")

# Go High Level
GHL_API_KEY = os.getenv("GHL_API_KEY", "")
GHL_LOCATION_ID = os.getenv("GHL_LOCATION_ID", "")

# MedX
MEDX_API_BASE_URL = os.getenv("MEDX_API_BASE_URL", "")
MEDX_API_KEY = os.getenv("MEDX_API_KEY", "")
