import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminAPI } from '../../api'
import { Users, Store, Package, ShoppingCart, DollarSign, Brain } from 'lucide-react'

export default function AdminDashboard() {
  const [stats, setStats] = useState({})

  useEffect(() => {
    adminAPI.stats().then(res => setStats(res.data)).catch(() => {})
  }, [])

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-800 mb-6">Admin Dashboard</h1>

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        <div className="card flex items-center gap-3">
          <Users className="text-brand-600" size={32} />
          <div><p className="text-2xl font-bold">{stats.total_customers || 0}</p><p className="text-sm text-gray-500">Customers</p></div>
        </div>
        <div className="card flex items-center gap-3">
          <Store className="text-brand-600" size={32} />
          <div><p className="text-2xl font-bold">{stats.total_sellers || 0}</p><p className="text-sm text-gray-500">Sellers</p></div>
        </div>
        <div className="card flex items-center gap-3">
          <Package className="text-brand-600" size={32} />
          <div><p className="text-2xl font-bold">{stats.total_products || 0}</p><p className="text-sm text-gray-500">Products</p></div>
        </div>
        <div className="card flex items-center gap-3">
          <ShoppingCart className="text-brand-600" size={32} />
          <div><p className="text-2xl font-bold">{stats.total_orders || 0}</p><p className="text-sm text-gray-500">Orders</p></div>
        </div>
        <div className="card flex items-center gap-3">
          <DollarSign className="text-green-600" size={32} />
          <div><p className="text-2xl font-bold">Rs. {stats.total_revenue?.toFixed(2) || '0.00'}</p><p className="text-sm text-gray-500">Revenue</p></div>
        </div>
        <div className="card flex items-center gap-3">
          <Store className="text-orange-500" size={32} />
          <div><p className="text-2xl font-bold">{stats.pending_sellers || 0}</p><p className="text-sm text-gray-500">Pending Sellers</p></div>
        </div>
      </div>

      <h2 className="text-xl font-bold mb-4">Management</h2>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Link to="/admin/sellers" className="card hover:shadow-md text-center">
          <Store className="mx-auto text-brand-600 mb-2" size={32} />
          <p className="font-medium">Manage Sellers</p>
          {stats.pending_sellers > 0 && <span className="badge-yellow mt-1">{stats.pending_sellers} pending</span>}
        </Link>
        <Link to="/admin/products" className="card hover:shadow-md text-center">
          <Package className="mx-auto text-brand-600 mb-2" size={32} />
          <p className="font-medium">All Products</p>
        </Link>
        <Link to="/admin/orders" className="card hover:shadow-md text-center">
          <ShoppingCart className="mx-auto text-brand-600 mb-2" size={32} />
          <p className="font-medium">All Orders</p>
        </Link>
        <Link to="/admin/ml" className="card hover:shadow-md text-center">
          <Brain className="mx-auto text-brand-600 mb-2" size={32} />
          <p className="font-medium">ML Training</p>
        </Link>
      </div>
    </div>
  )
}
