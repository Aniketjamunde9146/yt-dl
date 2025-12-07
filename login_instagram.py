import instaloader
import getpass
import os

USERNAME = "aniketwebdev.dev"
PASSWORD = getpass.getpass("Enter Instagram Password: ")

L = instaloader.Instaloader()

print("Logging in...")
try:
    L.login(USERNAME, PASSWORD)
    session_file = f"session-{USERNAME}"
    L.save_session_to_file(session_file)
    print(f"✔ Login successful. Session saved as: {session_file}")

except Exception as e:
    print("❌ Login failed:", e)
