import requests
import webbrowser

# ✅ Use the client ID and secret you gave earlier
CLIENT_ID = "1000.BXRZ81X6FLNXHZNXRHU7YC6HBWWBKT"
CLIENT_SECRET = "c55b86d0ae3f6ceaaa8e8d71cf673058e385964c21"
REDIRECT_URI = "http://localhost:8080/"

# Step 1: Generate Zoho authorization URL
auth_url = f"https://accounts.zoho.in/oauth/v2/auth?scope=ZohoBooks.fullaccess.all&client_id={CLIENT_ID}&response_type=code&access_type=offline&redirect_uri={REDIRECT_URI}"

# Step 2: Open login page in your browser
print("👉 Opening Zoho login page...")
webbrowser.open(auth_url)

# Step 3: You paste the code from the URL after login
code = input("\n📋 Paste the 'code' you got from the URL here: ").strip()

# Step 4: Exchange the code for access + refresh tokens
token_url = "https://accounts.zoho.in/oauth/v2/token"
payload = {
    "grant_type": "authorization_code",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri": REDIRECT_URI,
    "code": code
}

print("🔁 Requesting tokens from Zoho...")
response = requests.post(token_url, data=payload)

if response.status_code == 200:
    tokens = response.json()
    print("\n✅ Success!")
    print("\n🔐 ACCESS TOKEN:\n", tokens["access_token"])
    print("\n♻️ REFRESH TOKEN (save this!):\n", tokens["refresh_token"])
else:
    print("\n❌ Failed to get token. Details:\n", response.json())


from zoho_agent import get_access_token

print("🔐 ACCESS TOKEN:")
print(get_access_token())
