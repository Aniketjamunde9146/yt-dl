import instaloader
import os

USERNAME = "aniketwebdev.dev"
PASSWORD = input("Enter Instagram password: ")

L = instaloader.Instaloader()

L.login(USERNAME, PASSWORD)

session_filename = f"session-{USERNAME}"
L.save_session_to_file(session_filename)

print("✔ Session saved as:", session_filename)
