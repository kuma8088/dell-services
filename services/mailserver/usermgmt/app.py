"""
Main entry point for mailserver usermgmt application

Uses application factory pattern for Flask app creation
"""
from flask import jsonify
from app import create_app

# Create Flask application
app = create_app()


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for Docker healthcheck and monitoring"""
    return jsonify({
        'status': 'healthy',
        'service': 'mailserver-usermgmt',
        'version': '0.5.0'  # MVP完了 (Phase 5)
    }), 200


@app.route('/', methods=['GET'])
def index():
    """Root endpoint - API information"""
    return jsonify({
        'service': 'Mail User Management System',
        'status': 'running',
        'version': '0.5.0',  # MVP完了 (Phase 5)
        'endpoints': {
            'health': '/health',
            'login': '/auth/login',
            'logout': '/auth/logout',
            'dashboard': '/',
            'users': '/users',
            'api_docs': '/api/docs'
        }
    }), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
