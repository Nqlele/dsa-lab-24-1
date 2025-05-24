from flask import Flask, request, jsonify
from datetime import datetime
import logging
import os
from dotenv import load_dotenv
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)

# Моковые данные курсов валют (в production заменить на реальный API)
CURRENCY_RATES = {
    'USD': 75.50,
    'EUR': 85.20,
}

# API-ключ для защиты (добавьте в .env)
API_KEY = os.getenv('FLASK_API_KEY')

# Мидлварь для проверки API-ключа
@app.before_request
def check_api_key():
    if request.endpoint in ['get_rate', 'add_rate']:
        provided_key = request.headers.get('X-API-KEY') or request.args.get('api_key')
        if provided_key != API_KEY:
            return jsonify({'error': 'Invalid API key'}), 403

@app.route('/rate', methods=['GET'])
def get_rate():
    currency = request.args.get('currency', 'USD').upper()
    
    if currency not in CURRENCY_RATES:
        return jsonify({'error': 'Invalid currency'}), 400
    
    # Здесь можно добавить реальный запрос к API ЦБ или другому источнику
    rate = CURRENCY_RATES[currency]
    
    return jsonify({
        'currency': currency,
        'rate': rate,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@app.errorhandler(500)
def handle_500(error):
    logger.error(f"Server error: {error}")
    return jsonify({"message": "UNEXPECTED ERROR"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)