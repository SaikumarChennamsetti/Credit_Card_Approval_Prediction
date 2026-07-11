import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from backend import create_app
from backend.utils import print_status

def main():
    print_status("Starting Flask REST API Server...", "INFO")
    
    try:
        app = create_app()
        print_status("Flask server started successfully.", "SUCCESS")
        print_status("Registered API Endpoints:", "INFO")
        print("  -> GET  /            : Basic project information")
        print("  -> GET  /api/        : Base API details")
        print("  -> GET  /api/health  : Server status and model load check")
        print("  -> POST /api/predict : Execute prediction models (takes JSON payload)")
        print_status("Server URL: http://127.0.0.1:5000", "SUCCESS")
        print_status("API ready for requests.", "SUCCESS")
        
        app.run(host='0.0.0.0', port=5000, debug=False)
        
    except Exception as e:
        print_status(f"Server start failed: {str(e)}", "ERROR")
        sys.exit(1)

if __name__ == '__main__':
    main()
