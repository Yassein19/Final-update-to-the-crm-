import sys
import os
import subprocess
import threading
import time
import webbrowser

def check_and_install_dependencies():
    required_packages = ["fastapi", "uvicorn", "sqlalchemy", "pandas", "openpyxl"]
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
            
    if missing_packages:
        print(f"Missing required packages: {missing_packages}. Installing them now...")
        try:
            # Install using pip (or uv pip if uv is active, but simple pip works globally/venv)
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing_packages])
            print("All dependencies successfully installed!")
        except Exception as e:
            print(f"Error installing dependencies: {e}")
            print("Please run: pip install fastapi uvicorn sqlalchemy pandas openpyxl")
            sys.exit(1)
    else:
        print("All dependencies are already installed.")

def init_db_and_import():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crm.db")
    if not os.path.exists(db_path):
        print("Database crm.db not found. Initializing schema and importing legacy Excel data...")
        try:
            from app.database import Base, engine
            from app.sync import import_from_excel
            
            # Create tables
            Base.metadata.create_all(bind=engine)
            print("SQLite tables created.")
            
            # Import Excel
            import_from_excel()
            print("Initial Excel data imported successfully.")
        except Exception as e:
            print(f"Failed to initialize database: {e}")
            sys.exit(1)
    else:
        print("Database crm.db found. Skipping import.")

def open_browser():
    time.sleep(1.5)
    url = "http://127.0.0.1:8000"
    print(f"Opening browser at {url}...")
    webbrowser.open(url)

if __name__ == "__main__":
    print("=== TEAM Engineering CRM Launcher ===")
    check_and_install_dependencies()
    init_db_and_import()
    
    # Start web browser in a separate thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Launch FastAPI Server
    import uvicorn
    print("Starting CRM Server. Press Ctrl+C to stop...")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
