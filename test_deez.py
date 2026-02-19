
import os
from dotenv import load_dotenv
from deezer import Deezer

load_dotenv()
arl = os.getenv('DEEZER_ARL')

try:
    dz = Deezer()
    if arl:
        dz.login_via_arl(arl)
        user = dz.get_user_data()
        print(f"✅ Login successful! User: {user['name']}")
    else:
        print("❌ No ARL found in .env")
except Exception as e:
    print(f"❌ Error logging in: {e}")
