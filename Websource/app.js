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
                        <button class="btn-add" ${isOutOfStock ? 'disabled' : ''} onclick="prepareCheckout(${p.id_produk}, '${p.nama_produk}', ${p.harga}, '${p.nama_stand}', '${imgUrl}')">
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

    // In a real app, buyer ID is from session. We use 1 (Budi) as per PRD defaults.
    const payload = {
        id_pelanggan: 1, 
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
