import api from './client'

// ── Auth ──────────────────────────────────────────────────────────────────
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (username, password, role) => {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)
    return api.post('/auth/login', formData, {
      params: role ? { role } : {},
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },
}

// ── Products ────────────────────────────────────────────────────────────────
export const productAPI = {
  list: (params = {}) => api.get('/products', { params }),
  get: (id) => api.get(`/products/${id}`),
  categories: () => api.get('/products/categories'),
  create: (data) => api.post('/products', data),
  update: (id, data) => api.put(`/products/${id}`, data),
  delete: (id) => api.delete(`/products/${id}`),
  reviews: (id) => api.get(`/products/${id}/reviews`),
  addReview: (id, rating, comment) =>
    api.post(`/products/${id}/reviews`, null, { params: { rating, comment } }),
}

// ── Cart ───────────────────────────────────────────────────────────────────
export const cartAPI = {
  get: () => api.get('/cart'),
  add: (productId, quantity) => api.post('/cart/add', { product_id: productId, quantity }),
  update: (itemId, quantity) => api.put(`/cart/${itemId}`, { quantity }),
  remove: (itemId) => api.delete(`/cart/${itemId}`),
  clear: () => api.delete('/cart'),
}

// ── Orders ─────────────────────────────────────────────────────────────────
export const orderAPI = {
  place: (items, totalAmount) => api.post('/orders', { items, total_amount: totalAmount }),
  myOrders: () => api.get('/orders/my'),
  sellerOrders: () => api.get('/orders/seller'),
  updateStatus: (orderId, status) => api.patch(`/orders/${orderId}/status`, { status }),
}

// ── Seller ─────────────────────────────────────────────────────────────────
export const sellerAPI = {
  stats: () => api.get('/seller/stats'),
  analytics: () => api.get('/seller/analytics/sales'),
  myProducts: () => api.get('/seller/products'),
  forecast: (productId) => api.get(`/seller/forecast/${productId}`),
  alerts: () => api.get('/seller/alerts'),
  profile: () => api.get('/seller/profile'),
  updateProfile: (data) => api.put('/seller/profile', data),
}

// ── Customer ──────────────────────────────────────────────────────────────
export const customerAPI = {
  recommendations: () => api.get('/customer/recommendations'),
  profile: () => api.get('/customer/profile'),
  updateProfile: (data) => api.put('/customer/profile', data),
  trackSearch: (keyword) => api.post('/customer/search-track', null, { params: { keyword } }),
}

// ── Admin ─────────────────────────────────────────────────────────────────
export const adminAPI = {
  stats: () => api.get('/admin/stats'),
  sellers: (status) => api.get('/admin/sellers', { params: { status } }),
  approveSeller: (username, approved) =>
    api.patch('/admin/sellers/approve', { username, approved }),
  customers: () => api.get('/admin/customers'),
  toggleUser: (username) => api.patch(`/admin/users/${username}/toggle-active`),
  products: () => api.get('/admin/products'),
  deleteProduct: (id) => api.delete(`/admin/products/${id}`),
  categories: () => api.get('/admin/categories'),
  addCategory: (name) => api.post('/admin/categories', null, { params: { name } }),
  deleteCategory: (name) => api.delete(`/admin/categories/${name}`),
  orders: () => api.get('/admin/orders'),
  trainML: () => api.post('/admin/ml/train'),
  mlStatus: () => api.get('/admin/ml/status'),
}

export default api
