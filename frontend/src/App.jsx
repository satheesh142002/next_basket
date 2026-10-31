import { Routes, Route } from 'react-router-dom'
import { Analytics } from '@vercel/analytics/react'
import Navbar from './components/Navbar'
import Footer from './components/Footer'
import ProtectedRoute from './components/ProtectedRoute'

// Shared pages
import Login from './pages/shared/Login'
import Register from './pages/shared/Register'
import ProductDetail from './pages/shared/ProductDetail'
import Landing from './pages/shared/Landing'

// Customer pages
import Shop from './pages/customer/Shop'
import Cart from './pages/customer/Cart'
import CustomerDashboard from './pages/customer/CustomerDashboard'
import Recommendations from './pages/customer/Recommendations'
import MyOrders from './pages/customer/MyOrders'

// Seller pages
import SellerDashboard from './pages/seller/SellerDashboard'
import SellerProducts from './pages/seller/SellerProducts'
import SellerOrders from './pages/seller/SellerOrders'
import StockForecast from './pages/seller/StockForecast'
import SellerAnalytics from './pages/seller/SellerAnalytics'

// Admin pages
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminSellers from './pages/admin/AdminSellers'
import AdminProducts from './pages/admin/AdminProducts'
import AdminOrders from './pages/admin/AdminOrders'
import MLTraining from './pages/admin/MLTraining'

export default function App() {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Navbar />
      <div className="flex-1">
      <Routes>
        {/* Public */}
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/product/:id" element={<ProductDetail />} />

        {/* Customer */}
        <Route path="/shop" element={<ProtectedRoute roles={['customer']}><Shop /></ProtectedRoute>} />
        <Route path="/cart" element={<ProtectedRoute roles={['customer']}><Cart /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute roles={['customer']}><CustomerDashboard /></ProtectedRoute>} />
        <Route path="/recommendations" element={<ProtectedRoute roles={['customer']}><Recommendations /></ProtectedRoute>} />
        <Route path="/orders" element={<ProtectedRoute roles={['customer']}><MyOrders /></ProtectedRoute>} />

        {/* Seller */}
        <Route path="/seller" element={<ProtectedRoute roles={['seller']}><SellerDashboard /></ProtectedRoute>} />
        <Route path="/seller/products" element={<ProtectedRoute roles={['seller']}><SellerProducts /></ProtectedRoute>} />
        <Route path="/seller/orders" element={<ProtectedRoute roles={['seller']}><SellerOrders /></ProtectedRoute>} />
        <Route path="/seller/forecast" element={<ProtectedRoute roles={['seller']}><StockForecast /></ProtectedRoute>} />
        <Route path="/seller/analytics" element={<ProtectedRoute roles={['seller']}><SellerAnalytics /></ProtectedRoute>} />

        {/* Admin */}
        <Route path="/admin" element={<ProtectedRoute roles={['admin']}><AdminDashboard /></ProtectedRoute>} />
        <Route path="/admin/sellers" element={<ProtectedRoute roles={['admin']}><AdminSellers /></ProtectedRoute>} />
        <Route path="/admin/products" element={<ProtectedRoute roles={['admin']}><AdminProducts /></ProtectedRoute>} />
        <Route path="/admin/orders" element={<ProtectedRoute roles={['admin']}><AdminOrders /></ProtectedRoute>} />
        <Route path="/admin/ml" element={<ProtectedRoute roles={['admin']}><MLTraining /></ProtectedRoute>} />
      </Routes>
      </div>
      <Footer />
      <Analytics />
    </div>
  )
}
