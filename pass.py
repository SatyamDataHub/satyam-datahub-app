from werkzeug.security import generate_password_hash

# --- CHANGE THIS PASSWORD ---
# Enter the password you want for your admin account below.
password_to_hash = "112233"
# -------------------------

hashed_password = generate_password_hash(password_to_hash)

print("\n--- SECURE PASSWORD HASH ---")
print("Copy this entire line and paste it into your SQL command:")
print(hashed_password)
print("----------------------------\n")