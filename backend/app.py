import os
import logging
from flask import Flask, jsonify, render_template, send_from_directory, request, redirect, session
from flask_cors import CORS

from backend.config import Config
from backend.models import db
from backend.routes import api_bp
from backend.services import load_production_model_assets
from backend.utils import print_status


def create_app(config_class=Config):

    base_dir = os.path.dirname(os.path.abspath(__file__))

    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, '../frontend/templates'),
        static_folder=os.path.join(base_dir, '../frontend/static'),
        static_url_path='/static'
    )

    app.config.from_object(config_class)

    CORS(app)

    setup_logging(app)

    db.init_app(app)

    app.register_blueprint(api_bp, url_prefix='/api')

    with app.app_context():
        try:
            db.create_all()
            
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [c['name'] for c in inspector.get_columns('prediction_history')]
            if 'user_id' not in columns:
                with db.engine.begin() as conn:
                    conn.execute(db.text("ALTER TABLE prediction_history ADD COLUMN user_id VARCHAR(36) REFERENCES user(user_id)"))
                print_status("Added user_id column to prediction_history table.", "INFO")
                
            print_status("Database initialized successfully.", "SUCCESS")
            app.logger.info("Database initialized successfully.")
        except Exception as e:
            app.logger.error(f"DB init failed: {str(e)}", exc_info=True)
            print_status(f"DB ERROR: {str(e)}", "ERROR")

    try:
        load_production_model_assets(
            app.config['MODEL_PATH'],
            app.config['PREPROCESSOR_PATH']
        )
        app.logger.info("ML model assets loaded successfully.")
    except Exception as e:
        app.logger.error(f"ML load failed: {str(e)}", exc_info=True)
        print_status(f"MODEL LOAD ERROR: {str(e)}", "ERROR")

    @app.before_request
    def check_login():
        exempt_paths = [
            '/login', '/signup', '/logout',
            '/api/login', '/api/signup', '/api/logout',
            '/api/health', '/api/', '/api/contact', '/contact'
        ]
        
        if request.path.startswith('/static/') or request.path == '/favicon.ico' or request.path in exempt_paths:
            if 'user_id' in session and request.path in ['/login', '/signup']:
                return redirect('/')
            return None
            
        if 'user_id' not in session:
            if request.path.startswith('/api'):
                return jsonify({
                    "success": False,
                    "error_code": "UNAUTHORIZED",
                    "message": "Authentication required."
                }), 401
            return redirect('/login')
            
        return None

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/login')
    def login_page():
        return render_template('login.html')

    @app.route('/signup')
    def signup_page():
        return render_template('signup.html')

    @app.route('/logout')
    def logout_page():
        session.clear()
        return redirect('/login')

    @app.route('/predict')
    def predict_page():
        return render_template('predict.html')

    @app.route('/history')
    def history_page():
        return render_template('history.html')

    @app.route('/dashboard')
    def dashboard_page():
        return render_template('dashboard.html')

    @app.route('/about')
    def about_page():
        return render_template('about.html')

    @app.route('/contact')
    def contact_page():
        return render_template('contact.html')

    try:
        from config.settings import VISUALIZATIONS_DIR
    except Exception:
        VISUALIZATIONS_DIR = os.path.join(base_dir, '../reports/visualizations')

    @app.route('/reports/visualizations/<filename>')
    def serve_visualization(filename):
        return send_from_directory(VISUALIZATIONS_DIR, filename)

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "success": False,
            "error_code": "INVALID_JSON",
            "message": "Request payload must be valid JSON."
        }), 400

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api'):
            return jsonify({
                "success": False,
                "error_code": "ROUTE_NOT_FOUND",
                "message": "API route not found."
            }), 404

        return render_template('index.html')

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            "success": False,
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "Server error occurred."
        }), 500

    return app


def setup_logging(app):
    log_file = app.config.get('LOG_FILE_PATH', 'app.log')
    log_level_str = app.config.get('LOG_LEVEL', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    logging.basicConfig(
        level=log_level,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    app.logger.setLevel(log_level)
    app.logger.info("Logging initialized successfully.")


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)