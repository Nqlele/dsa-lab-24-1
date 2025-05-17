from flask import Flask, request, jsonify
import psycopg2
from psycopg2 import pool

# Создаем Flask приложение
app = Flask(__name__)

# Пул соединений с БД
db_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dbname="laba66",
    user="postgres",
    password="postgres",
    host="localhost",
    port="5432"
)

def get_db_connection():
    return db_pool.getconn()

def close_db_connection(conn):
    db_pool.putconn(conn)

@app.route('/convert', methods=['GET'])
def convert_currency():
    currency_name = request.args.get('currency_name')
    amount = request.args.get('amount')

    if not currency_name or not amount:
        return jsonify({"message": "Missing currency_name or amount parameter"}), 400

    try:
        amount = float(amount)
    except ValueError:
        return jsonify({"message": "Invalid amount value"}), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT rate FROM currencies WHERE currency_name = %s", (currency_name,))
            existing_currency = cursor.fetchone()

            if not existing_currency:
                return jsonify({"message": "Currency not found"}), 404

            rate = existing_currency[0]
            converted_amount = amount * float(rate)
            return jsonify({"converted_amount": converted_amount}), 200
    except psycopg2.Error as e:
        return jsonify({"message": f"Database error: {str(e)}"}), 500
    finally:
        if conn:
            close_db_connection(conn)

@app.route('/currencies', methods=['GET'])
def get_currencies():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT currency_name FROM currencies")
            currencies = [row[0] for row in cursor.fetchall()]
            return jsonify({"currencies": currencies}), 200
    except psycopg2.Error as e:
        return jsonify({"message": f"Database error: {str(e)}"}), 500
    finally:
        if conn:
            close_db_connection(conn)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)