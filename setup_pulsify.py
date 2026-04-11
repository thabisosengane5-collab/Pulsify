import os, json, subprocess, shutil

KEYS = {
    "SUPABASE_URL":         "https://jjvjOAKYjkWCvzMxUcXkzA.supabase.co",
    "SUPABASE_ANON_KEY":    "sb_publishable_jjvjOAKYjkWCvzMxUcXkzA_GMJLbg93",
    "SUPABASE_SERVICE_KEY": "sb_secret_5ZOcK-0FtiyThxVy91mQGA_2uQXej23",
    "MAPBOX_TOKEN":         "pk.eyJ1IjoidGhhY29sbGluMiIsImEiOiJjbW51Mm95cHEwYm8xMnJyMXEzaXgxMDBmIn0.nF80wBOn-jxhjpAIus9anw",
    "PAYSTACK_PUBLIC_KEY":  "pk_test_ef8796acebf766e5dde7cc185b5135551779d78a",
    "TICKETMASTER_API_KEY": "ASnkf0hmmYwDfOKc",
    "EVENTBRITE_TOKEN":     "ASnkf0hmmYwDfOKc",
}

for folder in ["api", "workers", "public", "scripts"]:
    os.makedirs(folder, exist_ok=True)
    print(f"Created: {folder}/")

with open(".env", "w") as f:
    f.write("\n".join([f"{k}={v}" for k, v in KEYS.items()]))
print("Created: .env")

with open(".gitignore", "w") as f:
    f.write(".env\nnode_modules/\n__pycache__/\n.vercel/\n")
print("Created: .gitignore")

vercel = {
    "version": 2,
    "builds": [{"src": "api/index.js", "use": "@vercel/node"}],
    "routes": [
        {"src": "/api/(.*)", "dest": "/api/index.js"},
        {"src": "/(.*)",     "dest": "/index.html"}
    ]
}
with open("vercel.json", "w") as f:
    json.dump(vercel, f, indent=2)
print("Created: vercel.json")

pkg = {
    "name": "pulsify",
    "version": "1.0.0",
    "private": True,
    "dependencies": {"@supabase/supabase-js": "^2.43.0"},
    "devDependencies": {"vercel": "^33.0.0"}
}
with open("package.json", "w") as f:
    json.dump(pkg, f, indent=2)
print("Created: package.json")

print("\nDone. Run: python inject_keys.py")
