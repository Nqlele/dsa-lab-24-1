from flask import Flask, request, jsonify
import psycopg2
from psycopg2 import pool

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

def get_connection():
    return db_pool.getconn()

def return_connection(conn):
    db_pool.putconn(conn)

@app.route('/load', methods=['POST'])
def load_currency():
    conn = get_connection()
    try:
        data = request.get_json()
        currency_name = data.get('currency_name')
        rate = data.get('rate')
        
        if not currency_name or not rate:
            return jsonify({"message": "Invalid JSON data"}), 400

        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM currencies WHERE currency_name = %s", (currency_name,))
            if cursor.fetchone():
                return jsonify({"message": "Currency already exists"}), 400

            cursor.execute("INSERT INTO currencies (currency_name, rate) VALUES (%s, %s)", (currency_name, rate))
            conn.commit()
            return jsonify({"message": "Currency loaded successfully"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"message": f"Error: {str(e)}"}), 500
    finally:
        return_connection(conn)

@app.route('/update_currency', methods=['POST'])
def update_currency():
    conn = get_connection()
    try:
        data = request.get_json()
        currency_name = data.get('currency_name')
        new_rate = data.get('rate')
        
        if not currency_name or not new_rate:
            return jsonify({"message": "Invalid JSON data"}), 400

        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM currencies WHERE currency_name = %s", (currency_name,))
            if not cursor.fetchone():
                return jsonify({"message": "Currency not found"}), 404

            cursor.execute("UPDATE currencies SET rate = %s WHERE currency_name = %s", (new_rate, currency_name))
            conn.commit()
            return jsonify({"message": "Currency updated successfully"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"message": f"Error: {str(e)}"}), 500
    finally:
        return_connection(conn)

@app.route('/delete', methods=['POST'])
def delete_currency():
    conn = get_connection()
    try:
        data = request.get_json()
        currency_name = data.get('currency_name')
        
        if not currency_name:
            return jsonify({"message": "Invalid JSON data"}), 400

        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM currencies WHERE currency_name = %s", (currency_name,))
            if not cursor.fetchone():
                return jsonify({"message": "Currency not found"}), 404

            cursor.execute("DELETE FROM currencies WHERE currency_name = %s", (currency_name,))
            conn.commit()
            return jsonify({"message": "Currency deleted successfully"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"message": f"Error: {str(e)}"}), 500
    finally:
        return_connection(conn)

if __name__ == '__main__':
    app.run(port=5001)