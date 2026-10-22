import os
from app import create_app, db

app = create_app(os.getenv("FLASK_ENV", "production"))

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    from waitress import serve
    port = int(os.getenv("PORT", 5000))
    print(f"Starting production server on port {port}...")
    serve(app, host="0.0.0.0", port=port)
