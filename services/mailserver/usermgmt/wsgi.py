"""
WSGI entry point for Gunicorn

This file serves as the WSGI application entry point for production deployment
"""
from app import create_app

# Create Flask application instance
application = create_app()

# Gunicorn will look for 'application' by default
app = application

if __name__ == '__main__':
    application.run(host='0.0.0.0', port=5000, debug=False)
