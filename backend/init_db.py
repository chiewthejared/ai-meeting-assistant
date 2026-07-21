from app.database import engine, Base
from app.database.models import Meeting

print("🔧 Initializing database...")
print(f"📁 Database URL: {engine.url}")

try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
    
    # Verify by checking if the file was created
    import os
    if "sqlite" in str(engine.url):
        db_file = str(engine.url).replace("sqlite:///", "")
        if os.path.exists(db_file):
            print(f"📄 Database file created: {db_file}")
            print(f"📊 File size: {os.path.getsize(db_file)} bytes")
            
except Exception as e:
    print(f"❌ Error creating database: {e}")