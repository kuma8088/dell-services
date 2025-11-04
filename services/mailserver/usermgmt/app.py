import os
from flask import Flask, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'database': os.getenv('DB_NAME', 'mailserver_usermgmt'),
    'user': os.getenv('DB_USER', 'usermgmt'),
    'password': os.getenv('DB_PASSWORD', '')
}

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for Docker healthcheck and monitoring"""
    return jsonify({
        'status': 'healthy',
        'service': 'mailserver-usermgmt',
        'version': '1.0.0'
    }), 200

@app.route('/', methods=['GET'])
def index():
    """Root endpoint - placeholder for web interface"""
    return jsonify({
        'service': 'Mail User Management System',
        'status': 'running',
        'endpoints': {
            'health': '/health',
            'api_docs': '/api/docs'
        }
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
