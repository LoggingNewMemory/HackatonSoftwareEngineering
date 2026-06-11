const API_BASE = 'http://localhost:5000/api';

// --- Toast Notifications ---
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    
    toast.textContent = message;
    toast.className = `toast show ${type}`;
    
    setTimeout(() => {
        toast.className = 'toast';
    }, 3000);
}

// --- Format Currency ---
function formatRupiah(number) {
    return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(number);
}

// --- Home/Catalog Page Logic ---
async function loadProducts() {
    const listEl = document.getElementById('product-list');
    if (!listEl) return;

    try {
        const res = await fetch(`${API_BASE}/produk`);
        const products = await res.json();
        
        listEl.innerHTML = '';
        
        products.forEach(p => {
            // Default images based on string matching for MVP aesthetics
            let imgUrl = 'https://images.unsplash.com/photo-1541592102775-7b560ab926e9?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80'; // fallback
            if(p.nama_produk.toLowerCase().includes('nasi') || p.nama_produk.toLowerCase().includes('makanan')) {
                imgUrl = 'https://images.unsplash.com/photo-1565557623262-b51c2513a641?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80';
            } else if(p.nama_produk.toLowerCase().includes('teh') || p.nama_produk.toLowerCase().includes('minum')) {
                imgUrl = 'https://images.unsplash.com/photo-1556679343-c7306c1976bc?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80';
            }

            const isOutOfStock = p.stok <= 0;
            const safeTitle = p.nama_produk.replace(/'/g, "\\'");
            const safeStand = p.nama_stand.replace(/'/g, "\\'");
            
            const card = document.createElement('div');
            card.className = 'product-card';
            card.innerHTML = `
                <div class="product-img" style="background-image: url('${imgUrl}')">
                    <div class="product-badge">${p.stok} in stock</div>
                </div>
                <div class="product-info">
                    <div class="product-title">${p.nama_produk}</div>
                    <div class="product-seller">📍 ${p.nama_stand}</div>
                    <div class="product-price-row">
                        <div class="product-price">${formatRupiah(p.harga)}</div>
                        <button class="btn-add" ${isOutOfStock ? 'disabled' : ''} onclick="prepareCheckout(${p.id_produk}, '${safeTitle}', ${p.harga}, '${safeStand}', '${imgUrl}')">
                            ${isOutOfStock ? '✕' : '+'}
                        </button>
                    </div>
                </div>
            `;
            listEl.appendChild(card);
        });
    } catch (error) {
        listEl.innerHTML = '<p style="color: red;">Failed to load products. Ensure the backend is running.</p>';
        console.error(error);
    }
}

function prepareCheckout(id, name, price, standName, imgUrl) {
    const orderData = { id, name, price, standName, imgUrl, qty: 1 };
    localStorage.setItem('jf_current_order', JSON.stringify(orderData));
    window.location.href = 'checkout.html';
}

// --- Checkout Page Logic ---
function loadCheckoutData() {
    const detailsEl = document.getElementById('order-details');
    if (!detailsEl) return;

    const orderData = JSON.parse(localStorage.getItem('jf_current_order'));
    if (!orderData) {
        detailsEl.innerHTML = '<p>No item selected. <a href="index.html">Go back</a></p>';
        document.getElementById('btn-pay').disabled = true;
        return;
    }

    // Render left column
    detailsEl.innerHTML = `
        <div class="order-item">
            <div class="order-item-img" style="background-image: url('${orderData.imgUrl}')"></div>
            <div class="order-item-details">
                <div class="order-item-title">${orderData.name}</div>
                <div style="color: var(--text-muted); font-size: 0.9rem; margin: 0.5rem 0;">Merchant: ${orderData.standName}</div>
                <div style="font-size: 0.9rem;">Qty: ${orderData.qty}</div>
            </div>
            <div class="order-item-price">${formatRupiah(orderData.price)}</div>
        </div>
    `;

    // Calculate totals
    const fee = 2500;
    const total = Number(orderData.price) + fee;

    document.getElementById('summary-subtotal').textContent = formatRupiah(orderData.price);
    document.getElementById('summary-total').textContent = formatRupiah(total);
    document.getElementById('btn-pay-amount').textContent = formatRupiah(total);
}

async function processPayment() {
    const orderData = JSON.parse(localStorage.getItem('jf_current_order'));
    if (!orderData) return;

    const btn = document.getElementById('btn-pay');
    btn.disabled = true;
    btn.innerHTML = 'Processing...';

    const userStr = localStorage.getItem('jf_user');
    const user = userStr ? JSON.parse(userStr) : null;
    
    const payload = {
        id_pelanggan: user && user.profile ? user.profile.id_pelanggan : 1, 
        id_produk: orderData.id,
        jumlah: orderData.qty
    };

    try {
        const res = await fetch(`${API_BASE}/beli`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const result = await res.json();

        if (res.ok) {
            showToast('Payment successful!', 'success');
            setTimeout(() => {
                window.location.href = 'success.html';
            }, 1000);
        } else {
            showToast(result.message || 'Transaction failed', 'error');
            btn.disabled = false;
            btn.innerHTML = `🔒 Pay Now ${formatRupiah(Number(orderData.price) + 2500)}`;
        }
    } catch (error) {
        showToast('Network error', 'error');
        console.error(error);
        btn.disabled = false;
        btn.innerHTML = `🔒 Pay Now ${formatRupiah(Number(orderData.price) + 2500)}`;
    }
}

// Init Home if we are on index
if(document.getElementById('product-list')) {
    loadProducts();
}

// --- Stalls Page Logic ---
async function loadStalls() {
    const listEl = document.getElementById('stall-list');
    if (!listEl) return;
    try {
        const res = await fetch(`${API_BASE}/stan`);
        const stalls = await res.json();
        listEl.innerHTML = '';
        if (stalls.length === 0) {
            listEl.innerHTML = '<p>No verified stalls currently available.</p>';
            return;
        }
        stalls.forEach(s => {
            listEl.innerHTML += `
                <div class="card" style="margin-bottom: 1rem; padding: 1.5rem; display: flex; align-items: center; gap: 1rem;">
                    <div style="width: 50px; height: 50px; border-radius: 50%; background: var(--primary-color); color: white; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 1.2rem;">
                        ${s.nama_stand.charAt(0)}
                    </div>
                    <div>
                        <h3 style="margin-bottom: 0.2rem;">${s.nama_stand}</h3>
                        <p style="color: var(--success-color); font-size: 0.8rem; font-weight: 600;">✓ Verified MSME</p>
                    </div>
                </div>
            `;
        });
    } catch (e) {
        listEl.innerHTML = '<p style="color: red;">Error loading stalls.</p>';
    }
}

// --- Orders Page Logic ---
async function loadOrders() {
    const listEl = document.getElementById('order-list');
    if (!listEl) return;
    try {
        const userStr = localStorage.getItem('jf_user');
        const user = userStr ? JSON.parse(userStr) : null;
        const id_pelanggan = user && user.profile ? user.profile.id_pelanggan : 1;
        
        const res = await fetch(`${API_BASE}/pesanan/buyer/${id_pelanggan}`);
        const orders = await res.json();
        listEl.innerHTML = '';
        if(orders.length === 0) {
            listEl.innerHTML = '<p>You have no orders yet. Start exploring the Jakarta Fair!</p>';
            return;
        }
        orders.forEach(o => {
            let statusColor = '#6c757d'; // default gray
            if(o.status === 'diproses') statusColor = '#17a2b8'; // blue
            if(o.status === 'siap') statusColor = '#28a745'; // green
            if(o.status === 'selesai') statusColor = '#20c997'; // teal

            listEl.innerHTML += `
                <div class="card" style="margin-bottom: 1.5rem; display: flex; justify-content: space-between; align-items: center; padding: 1.5rem;">
                    <div>
                        <div style="font-weight: 700; font-size: 1.1rem; margin-bottom: 0.2rem;">Order #JF-${o.id_pesanan + 88000}</div>
                        <div style="font-size: 0.9rem; color: var(--text-muted)">${new Date(o.waktu_pesanan).toLocaleString()}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="color: var(--primary-color); font-weight: 700; font-size: 1.2rem;">${formatRupiah(o.total_harga)}</div>
                        <div style="font-size: 0.75rem; padding: 4px 10px; border-radius: 20px; background: ${statusColor}20; color: ${statusColor}; font-weight: 600; display: inline-block; margin-top: 8px;">
                            ${o.status.toUpperCase()}
                        </div>
                    </div>
                </div>
            `;
        });
    } catch (e) {
        listEl.innerHTML = '<p style="color: red;">Error loading orders.</p>';
    }
}

if(document.getElementById('stall-list')) loadStalls();
if(document.getElementById('order-list')) loadOrders();

// --- Login & Role Logic (Design Workflow) ---
async function handleLogin(e) {
    e.preventDefault();
    const u = document.getElementById('username').value;
    const p = document.getElementById('password').value;
    
    try {
        const res = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: u, password: p })
        });
        const result = await res.json();
        
        if(res.ok) {
            localStorage.setItem('jf_user', JSON.stringify(result.user));
            showToast('Login successful!', 'success');
            setTimeout(() => {
                if(result.user.role === 'seller') window.location.href = 'seller_dashboard.html';
                else window.location.href = 'index.html';
            }, 1000);
        } else {
            showToast(result.message || 'Login failed', 'error');
        }
    } catch(err) {
        showToast('Network error', 'error');
    }
}

// --- Register Logic ---
async function handleRegister(e) {
    e.preventDefault();
    const u = document.getElementById('reg-username').value;
    const p = document.getElementById('reg-password').value;
    const r = document.getElementById('reg-role').value;
    const n = document.getElementById('reg-name').value;
    
    try {
        const res = await fetch(`${API_BASE}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: u, password: p, role: r, name: n })
        });
        const result = await res.json();
        
        if(res.ok) {
            showToast('Registration successful! Please login.', 'success');
            setTimeout(() => {
                window.location.href = 'login.html';
            }, 1500);
        } else {
            showToast(result.message || 'Registration failed', 'error');
        }
    } catch(err) {
        showToast('Network error', 'error');
    }
}

function logout() {
    localStorage.removeItem('jf_user');
    window.location.href = 'login.html';
}

// --- Seller Dashboard Logic (Design Workflow) ---
function initSellerDashboard() {
    const userStr = localStorage.getItem('jf_user');
    if(!userStr) {
        window.location.href = 'login.html';
        return;
    }
    const user = JSON.parse(userStr);
    if(user.role !== 'seller') {
        window.location.href = 'index.html';
        return;
    }
    
    document.getElementById('seller-name').textContent = user.profile.nama_stand;
    const statusEl = document.getElementById('seller-status');
    if(user.profile.is_verified) {
        statusEl.innerHTML = '<span style="color: var(--success-color); font-weight: bold;">✓ Verified</span>';
    } else {
        statusEl.innerHTML = '<span style="color: var(--primary-color); font-weight: bold;">✕ Unverified (Please submit verification)</span>';
        document.getElementById('add-product-form').innerHTML = '<p style="color: var(--primary-color);">You must be verified to add menus.</p>';
    }
    
    loadSellerOrders(user.profile.id_penjual);
}

async function handleAddProduct(e) {
    e.preventDefault();
    const user = JSON.parse(localStorage.getItem('jf_user'));
    
    const payload = {
        id_penjual: user.profile.id_penjual,
        nama_produk: document.getElementById('prod-name').value,
        harga: document.getElementById('prod-price').value,
        stok: document.getElementById('prod-stock').value
    };
    
    try {
        const res = await fetch(`${API_BASE}/produk`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        if(res.ok) {
            showToast('Product added! Buyers can now order it.', 'success');
            e.target.reset();
        } else {
            showToast(result.message, 'error');
        }
    } catch(err) {
        showToast('Error adding product', 'error');
    }
}

async function loadSellerOrders(id_penjual) {
    const listEl = document.getElementById('seller-orders');
    try {
        const res = await fetch(`${API_BASE}/pesanan/seller/${id_penjual}`);
        const orders = await res.json();
        listEl.innerHTML = '';
        if(orders.length === 0) {
            listEl.innerHTML = '<p>No orders yet.</p>';
            return;
        }
        
        orders.forEach(o => {
            let nextAction = '';
            if(o.status === 'pending') {
                nextAction = `<button onclick="updateOrderStatus(${o.id_pesanan}, 'diproses')" style="background:#17a2b8; color:white; border:none; padding:8px 15px; border-radius:5px; cursor:pointer; font-weight: bold;">Terima & Proses</button>`;
            } else if(o.status === 'diproses') {
                nextAction = `<button onclick="updateOrderStatus(${o.id_pesanan}, 'siap')" style="background:var(--success-color); color:white; border:none; padding:8px 15px; border-radius:5px; cursor:pointer; font-weight: bold;">Siap (Beri Notif)</button>`;
            } else if(o.status === 'siap') {
                nextAction = `<button onclick="updateOrderStatus(${o.id_pesanan}, 'selesai')" style="background:#20c997; color:white; border:none; padding:8px 15px; border-radius:5px; cursor:pointer; font-weight: bold;">Diambil (Selesai)</button>`;
            } else {
                nextAction = `<span style="color:var(--success-color); font-weight:bold;">✓ Order Completed</span>`;
            }
            
            listEl.innerHTML += `
                <div style="border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 1.5rem; margin-bottom: 1rem; background: ${o.status === 'selesai' ? 'rgba(0,0,0,0.02)' : '#fff'};">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <div style="font-weight: 700; font-size: 1.1rem;">Order #JF-${o.id_pesanan + 88000}</div>
                        <div style="font-size: 0.8rem; padding: 4px 10px; border-radius: 20px; background: rgba(0,0,0,0.05); color: var(--text-muted); font-weight: 600;">
                            ${o.status.toUpperCase()}
                        </div>
                    </div>
                    <div style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1rem;">
                        <strong>Date:</strong> ${new Date(o.waktu_pesanan).toLocaleString()}<br>
                        <strong>Total:</strong> ${formatRupiah(o.total_harga)}
                    </div>
                    <div style="border-top: 1px dashed var(--border-color); padding-top: 1rem; text-align: right;">
                        ${nextAction}
                    </div>
                </div>
            `;
        });
    } catch(err) {
        listEl.innerHTML = '<p style="color: red;">Failed to load orders.</p>';
    }
}

async function updateOrderStatus(id_pesanan, status) {
    try {
        const res = await fetch(`${API_BASE}/pesanan/${id_pesanan}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status })
        });
        if(res.ok) {
            showToast('Status updated!', 'success');
            const user = JSON.parse(localStorage.getItem('jf_user'));
            loadSellerOrders(user.profile.id_penjual);
        } else {
            showToast('Failed to update status', 'error');
        }
    } catch(err) {
        showToast('Error updating status', 'error');
    }
}

// --- Auth UI Logic ---
function updateAuthState() {
    const loginBtn = document.getElementById('nav-login-btn');
    if (!loginBtn) return;
    const userStr = localStorage.getItem('jf_user');
    if (userStr) {
        const user = JSON.parse(userStr);
        loginBtn.textContent = 'Logout';
        loginBtn.href = '#';
        loginBtn.onclick = (e) => {
            e.preventDefault();
            logout();
        };
    }
}
document.addEventListener('DOMContentLoaded', updateAuthState);
