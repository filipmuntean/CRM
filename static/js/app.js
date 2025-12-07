const API_BASE = '/api';

// Tab navigation
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Remove active class from all nav buttons
    document.querySelectorAll('nav button').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(tabName).classList.add('active');

    // Highlight active nav button
    event.target.classList.add('active');

    // Load data for the tab
    if (tabName === 'dashboard') loadDashboard();
    if (tabName === 'products') loadProducts();
    if (tabName === 'sales') loadSales();
    if (tabName === 'sync') loadSyncStats();
}

// Dashboard
async function loadDashboard() {
    try {
        // Load products stats
        const productsRes = await fetch(`${API_BASE}/products/`);
        const products = await productsRes.json();
        document.getElementById('total-products').textContent = products.length;

        // Load sales stats
        const salesStatsRes = await fetch(`${API_BASE}/sales/stats?days=30`);
        const salesStats = await salesStatsRes.json();
        document.getElementById('total-sales').textContent = salesStats.total_sales;
        document.getElementById('total-revenue').textContent = `€${salesStats.total_revenue.toFixed(2)}`;
        document.getElementById('net-profit').textContent = `€${salesStats.total_profit.toFixed(2)}`;

        // Platform chart
        const platformData = salesStats.by_platform;
        const labels = Object.keys(platformData);
        const data = labels.map(p => platformData[p].revenue);

        const ctx = document.getElementById('platformChart');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Revenue by Platform',
                    data: data,
                    backgroundColor: [
                        'rgba(52, 152, 219, 0.7)',
                        'rgba(46, 204, 113, 0.7)',
                        'rgba(155, 89, 182, 0.7)',
                        'rgba(241, 196, 15, 0.7)'
                    ]
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        // Sync status
        const syncStatsRes = await fetch(`${API_BASE}/sync/stats`);
        const syncStats = await syncStatsRes.json();
        document.getElementById('sync-status-content').innerHTML = `
            <p>Total Listings: ${syncStats.total_listings}</p>
            <p>Needs Sync: ${syncStats.needs_sync}</p>
            <p>Errors: ${syncStats.has_errors}</p>
        `;

    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

// Products
async function loadProducts() {
    try {
        const res = await fetch(`${API_BASE}/products/`);
        const products = await res.json();

        const container = document.getElementById('products-list');
        container.innerHTML = products.map(product => `
            <div class="product-card" onclick="viewProduct(${product.id})">
                ${product.images.length > 0 ? `<img src="${product.images[0]}" alt="${product.title}">` : ''}
                <h4>${product.title}</h4>
                <p class="price">€${product.price.toFixed(2)}</p>
                <span class="status-badge status-${product.status}">${product.status}</span>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading products:', error);
    }
}

function viewProduct(productId) {
    // TODO: Implement product detail view
    alert(`View product ${productId}`);
}

// Add product modal
function showAddProductModal() {
    document.getElementById('add-product-modal').style.display = 'block';
}

function closeAddProductModal() {
    document.getElementById('add-product-modal').style.display = 'none';
}

document.getElementById('add-product-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const productData = {
        title: document.getElementById('product-title').value,
        description: document.getElementById('product-description').value,
        price: parseFloat(document.getElementById('product-price').value),
        category: document.getElementById('product-category').value,
        brand: document.getElementById('product-brand').value,
        size: document.getElementById('product-size').value,
        condition: document.getElementById('product-condition').value,
        images: []
    };

    try {
        // Create product
        const res = await fetch(`${API_BASE}/products/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(productData)
        });

        const product = await res.json();

        // Get selected platforms
        const platforms = Array.from(document.querySelectorAll('input[name="platforms"]:checked'))
            .map(cb => cb.value);

        if (platforms.length > 0) {
            // Cross-post to selected platforms
            await fetch(`${API_BASE}/products/${product.id}/cross-post`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(platforms)
            });
        }

        closeAddProductModal();
        loadProducts();
        alert('Product created successfully!');

    } catch (error) {
        console.error('Error creating product:', error);
        alert('Error creating product');
    }
});

// Sales
async function loadSales() {
    const platform = document.getElementById('sales-platform-filter').value;
    const days = document.getElementById('sales-period-filter').value;

    try {
        let url = `${API_BASE}/sales/?`;
        if (platform) url += `platform=${platform}&`;
        if (days) url += `days=${days}`;

        const res = await fetch(url);
        const sales = await res.json();

        const tbody = document.getElementById('sales-tbody');
        tbody.innerHTML = sales.map(sale => `
            <tr>
                <td>${new Date(sale.sale_date).toLocaleDateString()}</td>
                <td>Product ${sale.product_id}</td>
                <td>${sale.platform}</td>
                <td>€${sale.sale_price.toFixed(2)}</td>
                <td>€${(sale.net_profit || 0).toFixed(2)}</td>
                <td>${sale.synced_to_sheets ? '✓' : '✗'}</td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Error loading sales:', error);
    }
}

function filterSales() {
    loadSales();
}

// Sync
async function loadSyncStats() {
    try {
        const res = await fetch(`${API_BASE}/sync/stats`);
        const stats = await res.json();

        document.getElementById('sync-stats-detail').innerHTML = `
            <h3>Sync Statistics</h3>
            <p>Total Listings: ${stats.total_listings}</p>
            <p>Needs Sync: ${stats.needs_sync}</p>
            <p>Has Errors: ${stats.has_errors}</p>
            <h4>By Platform:</h4>
            <ul>
                ${Object.entries(stats.by_platform).map(([platform, count]) =>
                    `<li>${platform}: ${count}</li>`
                ).join('')}
            </ul>
        `;
    } catch (error) {
        console.error('Error loading sync stats:', error);
    }
}

async function syncAll() {
    if (!confirm('This will sync all products. Continue?')) return;

    try {
        const res = await fetch(`${API_BASE}/sync/all`, { method: 'POST' });
        const result = await res.json();
        alert(result.message || 'Sync completed');
        loadSyncStats();
    } catch (error) {
        console.error('Error syncing:', error);
        alert('Sync failed');
    }
}

async function checkSoldItems() {
    try {
        const res = await fetch(`${API_BASE}/sync/check-sold`, { method: 'POST' });
        const result = await res.json();
        alert(`Found ${result.sold_items?.length || 0} sold items`);
        loadDashboard();
    } catch (error) {
        console.error('Error checking sold items:', error);
    }
}

function refreshSyncStats() {
    loadSyncStats();
}

async function importProducts() {
    const platform = prompt('Enter platform to import from (marktplaats/vinted/depop/facebook_marketplace):');
    if (!platform) return;

    try {
        const res = await fetch(`${API_BASE}/sync/import/${platform}`, { method: 'POST' });
        const result = await res.json();
        alert(result.message);
        loadProducts();
    } catch (error) {
        console.error('Error importing products:', error);
        alert('Import failed');
    }
}

// Settings
function configureMarktplaats() {
    alert('Redirect to Marktplaats OAuth flow - implement OAuth endpoint');
}

function saveVintedCreds() {
    alert('Save to .env or backend config');
}

function saveDepopCreds() {
    alert('Save to .env or backend config');
}

function saveFacebookCreds() {
    alert('Save to .env or backend config');
}

function saveSheetsConfig() {
    alert('Save Google Sheets configuration');
}

// Load dashboard on page load
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
});
