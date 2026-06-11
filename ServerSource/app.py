from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Database configuration - in a real app these should come from env vars
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_NAME = os.environ.get('DB_NAME', 'stand_bazar')

# Create a connection pool globally
try:
    dbconfig = {
        "host": DB_HOST,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "database": DB_NAME
    }
    pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="mypool",
        pool_size=5,
        **dbconfig
    )
except Exception as e:
    print(f"Warning: Could not create connection pool on startup (maybe DB doesn't exist yet): {e}")
    pool = None

def get_db_connection():
    global pool
    if not pool:
        # Fallback to direct connection if pool fails or database doesn't exist yet
        return mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
    return pool.get_connection()

@app.route('/api/produk', methods=['GET'])
def get_produk():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT p.id_produk, p.nama_produk, p.harga, p.stok, s.nama_stand FROM produk p JOIN penjual s ON p.id_penjual = s.id_penjual")
        produk = cursor.fetchall()
        return jsonify(produk)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/api/beli', methods=['POST'])
def beli_produk():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    id_pelanggan = data.get('id_pelanggan')
    id_produk = data.get('id_produk')
    jumlah = data.get('jumlah')

    if not all([id_pelanggan, id_produk, jumlah]):
        return jsonify({"status": "error", "message": "Data tidak lengkap"}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        # Ensure we are using InnoDB transactions
        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)

        # SELECT FOR UPDATE to lock the row and prevent race conditions
        cursor.execute("SELECT harga, stok FROM produk WHERE id_produk = %s FOR UPDATE", (id_produk,))
        produk = cursor.fetchone()

        if not produk:
            conn.rollback()
            return jsonify({"status": "error", "message": "Produk tidak ditemukan!"}), 400

        if produk['stok'] < jumlah:
            conn.rollback()
            return jsonify({"status": "error", "message": "Stok tidak cukup!"}), 400

        harga_satuan = produk['harga']
        total_harga = harga_satuan * float(jumlah)

        # Reduce stock
        cursor.execute("UPDATE produk SET stok = stok - %s WHERE id_produk = %s", (jumlah, id_produk))

        # Create pesanan
        cursor.execute(
            "INSERT INTO pesanan (id_pelanggan, total_harga) VALUES (%s, %s)",
            (id_pelanggan, total_harga)
        )
        id_pesanan = cursor.lastrowid

        # Create detail_pesanan
        cursor.execute(
            "INSERT INTO detail_pesanan (id_pesanan, id_produk, jumlah, harga_satuan) VALUES (%s, %s, %s, %s)",
            (id_pesanan, id_produk, jumlah, harga_satuan)
        )

        conn.commit()
        return jsonify({"status": "success", "message": "Transaksi berhasil!"})

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def init_db_internal():
    """Internal function to initialize DB tables and seed data if the DB is empty."""
    conn = None
    cursor = None
    try:
        # Connect without DB to create it if it doesn't exist
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        cursor.execute(f"USE {DB_NAME}")
        
        tables = [
            """CREATE TABLE IF NOT EXISTS penjual (
                id_penjual INT AUTO_INCREMENT PRIMARY KEY,
                nama_stand VARCHAR(100) NOT NULL
            ) ENGINE=InnoDB""",
            """CREATE TABLE IF NOT EXISTS pelanggan (
                id_pelanggan INT AUTO_INCREMENT PRIMARY KEY,
                nama_pelanggan VARCHAR(100) NOT NULL
            ) ENGINE=InnoDB""",
            """CREATE TABLE IF NOT EXISTS produk (
                id_produk INT AUTO_INCREMENT PRIMARY KEY,
                id_penjual INT,
                nama_produk VARCHAR(100) NOT NULL,
                harga DECIMAL(10, 2) NOT NULL,
                stok INT NOT NULL,
                FOREIGN KEY (id_penjual) REFERENCES penjual(id_penjual)
            ) ENGINE=InnoDB""",
            """CREATE TABLE IF NOT EXISTS pesanan (
                id_pesanan INT AUTO_INCREMENT PRIMARY KEY,
                id_pelanggan INT,
                waktu_pesanan DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_harga DECIMAL(10, 2),
                FOREIGN KEY (id_pelanggan) REFERENCES pelanggan(id_pelanggan)
            ) ENGINE=InnoDB""",
            """CREATE TABLE IF NOT EXISTS detail_pesanan (
                id_detail INT AUTO_INCREMENT PRIMARY KEY,
                id_pesanan INT,
                id_produk INT,
                jumlah INT NOT NULL,
                harga_satuan DECIMAL(10, 2) NOT NULL,
                FOREIGN KEY (id_pesanan) REFERENCES pesanan(id_pesanan),
                FOREIGN KEY (id_produk) REFERENCES produk(id_produk)
            ) ENGINE=InnoDB"""
        ]
        
        for table_query in tables:
            cursor.execute(table_query)
            
        # Seed some data if empty
        cursor.execute("SELECT COUNT(*) FROM penjual")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO penjual (nama_stand) VALUES ('Stand Makanan'), ('Stand Minuman')")
            cursor.execute("INSERT INTO pelanggan (nama_pelanggan) VALUES ('Budi'), ('Ani')")
            cursor.execute("INSERT INTO produk (id_penjual, nama_produk, harga, stok) VALUES (1, 'Nasi Goreng', 15000, 10), (2, 'Es Teh', 5000, 20)")
            conn.commit()
            print("Database seeded with initial data.")
        else:
            print("Database already contains data, skipping seed.")
            
        return True, "Database initialized and seeded!"
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False, str(e)
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/api/init_db', methods=['POST'])
def init_db():
    """Helper endpoint to initialize DB tables and seed data if the DB is empty."""
    success, message = init_db_internal()
    if success:
        return jsonify({"status": "success", "message": message})
    else:
        return jsonify({"status": "error", "message": message}), 500

if __name__ == '__main__':
    # Start the server
    app.run(host='0.0.0.0', port=5000, debug=True)
