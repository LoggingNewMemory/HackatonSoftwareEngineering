import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling

load_dotenv()

app = Flask(__name__)
CORS(app)

DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_NAME = os.environ.get('DB_NAME', 'stand_bazar')

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
    print(f"Warning: Could not create connection pool on startup: {e}")
    pool = None

def get_db_connection():
    global pool
    if not pool:
        return mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
    return pool.get_connection()

# --- DB INIT LOGIC ---
def init_db_internal():
    """Internal function to initialize DB tables and seed data."""
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD)
        cursor = conn.cursor()
        
        # Drop existing DB to ensure new schema (with Auth and Statuses) is applied cleanly
        cursor.execute(f"DROP DATABASE IF EXISTS {DB_NAME}")
        cursor.execute(f"CREATE DATABASE {DB_NAME}")
        cursor.execute(f"USE {DB_NAME}")
        
        tables = [
            """CREATE TABLE users (
                id_user INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role ENUM('buyer', 'seller') NOT NULL
            ) ENGINE=InnoDB""",
            """CREATE TABLE penjual (
                id_penjual INT AUTO_INCREMENT PRIMARY KEY,
                id_user INT,
                nama_stand VARCHAR(100) NOT NULL,
                is_verified BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (id_user) REFERENCES users(id_user)
            ) ENGINE=InnoDB""",
            """CREATE TABLE pelanggan (
                id_pelanggan INT AUTO_INCREMENT PRIMARY KEY,
                id_user INT,
                nama_pelanggan VARCHAR(100) NOT NULL,
                FOREIGN KEY (id_user) REFERENCES users(id_user)
            ) ENGINE=InnoDB""",
            """CREATE TABLE produk (
                id_produk INT AUTO_INCREMENT PRIMARY KEY,
                id_penjual INT,
                nama_produk VARCHAR(100) NOT NULL,
                harga DECIMAL(10, 2) NOT NULL,
                stok INT NOT NULL,
                FOREIGN KEY (id_penjual) REFERENCES penjual(id_penjual)
            ) ENGINE=InnoDB""",
            """CREATE TABLE pesanan (
                id_pesanan INT AUTO_INCREMENT PRIMARY KEY,
                id_pelanggan INT,
                id_penjual INT,
                waktu_pesanan DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_harga DECIMAL(10, 2),
                status ENUM('pending', 'diproses', 'siap', 'selesai') DEFAULT 'pending',
                FOREIGN KEY (id_pelanggan) REFERENCES pelanggan(id_pelanggan),
                FOREIGN KEY (id_penjual) REFERENCES penjual(id_penjual)
            ) ENGINE=InnoDB""",
            """CREATE TABLE detail_pesanan (
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
            
        # Seed users
        cursor.execute("INSERT INTO users (username, password, role) VALUES ('budi_buyer', 'pass123', 'buyer'), ('ani_buyer', 'pass123', 'buyer'), ('stand_makanan', 'pass123', 'seller'), ('stand_minuman', 'pass123', 'seller')")
        # Seed pelanggan
        cursor.execute("INSERT INTO pelanggan (id_user, nama_pelanggan) VALUES (1, 'Budi'), (2, 'Ani')")
        # Seed penjual (stand 1 is verified, stand 2 is not)
        cursor.execute("INSERT INTO penjual (id_user, nama_stand, is_verified) VALUES (3, 'Stand Makanan', TRUE), (4, 'Stand Minuman', FALSE)")
        # Seed produk
        cursor.execute("INSERT INTO produk (id_penjual, nama_produk, harga, stok) VALUES (1, 'Nasi Goreng', 15000, 10), (2, 'Es Teh', 5000, 20)")
        
        conn.commit()
        print("Database successfully initialized and seeded with Auth, Verification, and Status Tracking schema.")
            
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

# --- AUTHENTICATION ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"status": "error", "message": "Invalid credentials"}), 401
            
        role = user['role']
        profile = None
        if role == 'seller':
            cursor.execute("SELECT * FROM penjual WHERE id_user = %s", (user['id_user'],))
            profile = cursor.fetchone()
        else:
            cursor.execute("SELECT * FROM pelanggan WHERE id_user = %s", (user['id_user'],))
            profile = cursor.fetchone()
            
        return jsonify({
            "status": "success", 
            "user": {
                "id_user": user['id_user'],
                "username": user['username'],
                "role": role,
                "profile": profile
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/api/verify_seller', methods=['POST'])
def verify_seller():
    data = request.json
    id_penjual = data.get('id_penjual')
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE penjual SET is_verified = TRUE WHERE id_penjual = %s", (id_penjual,))
        conn.commit()
        return jsonify({"status": "success", "message": "Seller verified successfully."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# --- SELLER MENU MANAGEMENT ---
@app.route('/api/produk', methods=['POST'])
def add_produk():
    data = request.json
    id_penjual = data.get('id_penjual')
    nama_produk = data.get('nama_produk')
    harga = data.get('harga')
    stok = data.get('stok')
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Diagram Requirement: "Are you verified?"
        cursor.execute("SELECT is_verified FROM penjual WHERE id_penjual = %s", (id_penjual,))
        seller = cursor.fetchone()
        if not seller or not seller['is_verified']:
            return jsonify({"status": "error", "message": "Seller is not verified yet."}), 403
            
        cursor.execute("INSERT INTO produk (id_penjual, nama_produk, harga, stok) VALUES (%s, %s, %s, %s)",
                       (id_penjual, nama_produk, harga, stok))
        conn.commit()
        return jsonify({"status": "success", "message": "Product added successfully."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/api/produk/<int:id_produk>', methods=['PUT'])
def update_produk(id_produk):
    data = request.json
    harga = data.get('harga')
    stok = data.get('stok')
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        if harga is not None:
            updates.append("harga = %s")
            params.append(harga)
        if stok is not None:
            updates.append("stok = %s")
            params.append(stok)
            
        if updates:
            params.append(id_produk)
            query = f"UPDATE produk SET {', '.join(updates)} WHERE id_produk = %s"
            cursor.execute(query, params)
            conn.commit()
            
        return jsonify({"status": "success", "message": "Product updated successfully."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# --- BUYER CATALOG & TRANSACTION (WITH PRD LOCKING) ---
@app.route('/api/stan', methods=['GET'])
def get_stan():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_penjual, nama_stand FROM penjual WHERE is_verified = TRUE")
        stan = cursor.fetchall()
        return jsonify(stan)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/api/produk', methods=['GET'])
def get_produk():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT p.id_produk, p.nama_produk, p.harga, p.stok, s.nama_stand, s.id_penjual FROM produk p JOIN penjual s ON p.id_penjual = s.id_penjual WHERE s.is_verified = TRUE")
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
        # PRD Requirement: Ensure InnoDB transaction
        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)

        # PRD Requirement: SELECT FOR UPDATE (Row-level Locking)
        cursor.execute("SELECT harga, stok, id_penjual FROM produk WHERE id_produk = %s FOR UPDATE", (id_produk,))
        produk = cursor.fetchone()

        if not produk:
            conn.rollback()
            return jsonify({"status": "error", "message": "Produk tidak ditemukan!"}), 400

        if produk['stok'] < int(jumlah):
            conn.rollback()
            return jsonify({"status": "error", "message": "Stok tidak cukup!"}), 400

        harga_satuan = produk['harga']
        total_harga = harga_satuan * int(jumlah)
        id_penjual = produk['id_penjual']

        # Reduce stock
        cursor.execute("UPDATE produk SET stok = stok - %s WHERE id_produk = %s", (int(jumlah), id_produk))

        # Create pesanan (status is 'pending' automatically for seller to process)
        cursor.execute(
            "INSERT INTO pesanan (id_pelanggan, id_penjual, total_harga, status) VALUES (%s, %s, %s, 'pending')",
            (id_pelanggan, id_penjual, total_harga)
        )
        id_pesanan = cursor.lastrowid

        # Create detail_pesanan
        cursor.execute(
            "INSERT INTO detail_pesanan (id_pesanan, id_produk, jumlah, harga_satuan) VALUES (%s, %s, %s, %s)",
            (id_pesanan, id_produk, jumlah, harga_satuan)
        )

        conn.commit()
        return jsonify({"status": "success", "message": "Transaksi berhasil! Pesanan diteruskan ke penjual."})

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# --- ORDER FULFILLMENT & STATUS (SELLER/BUYER TRACKING) ---
@app.route('/api/pesanan/seller/<int:id_penjual>', methods=['GET'])
def get_pesanan_seller(id_penjual):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM pesanan WHERE id_penjual = %s ORDER BY waktu_pesanan DESC", (id_penjual,))
        pesanan = cursor.fetchall()
        return jsonify(pesanan)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        
@app.route('/api/pesanan/buyer/<int:id_pelanggan>', methods=['GET'])
def get_pesanan_buyer(id_pelanggan):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM pesanan WHERE id_pelanggan = %s ORDER BY waktu_pesanan DESC", (id_pelanggan,))
        pesanan = cursor.fetchall()
        return jsonify(pesanan)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/api/pesanan/<int:id_pesanan>/status', methods=['PUT'])
def update_status_pesanan(id_pesanan):
    data = request.json
    new_status = data.get('status') # 'diproses', 'siap', 'selesai'
    
    valid_statuses = ['pending', 'diproses', 'siap', 'selesai']
    if new_status not in valid_statuses:
        return jsonify({"status": "error", "message": "Invalid status"}), 400
        
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE pesanan SET status = %s WHERE id_pesanan = %s", (new_status, id_pesanan))
        conn.commit()
        return jsonify({"status": "success", "message": f"Order status updated to {new_status}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

if __name__ == '__main__':
    # Start the server
    app.run(host='0.0.0.0', port=5000, debug=True)
