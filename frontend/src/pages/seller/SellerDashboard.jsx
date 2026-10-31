import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { sellerAPI } from '../../api'
import { Package, DollarSign, AlertTriangle, ShoppingCart } from 'lucide-react'

export default function SellerDashboard() {
  const [stats, setStats] = useState({})
  const [alerts, setAlerts] = useState([])

  useEffect(() => {
    sellerAPI.stats().then(res => setStats(res.data)).catch(() => {})
    sellerAPI.alerts().then(res => setAlerts(res.data.alerts)).catch(() => {})
  }, [])

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-800 mb-6">Seller Dashboard</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="card flex items-center gap-3">
          <Package className="text-brand-600" size={32} />
          <div><p className="text-2xl font-bold">{stats.total_products || 0}</p><p className="text-sm text-gray-500">Products</p></div>
        </div>
        <div className="card flex items-center gap-3">
          <ShoppingCart className="text-green-600" size={32} />
          <div><p className="text-2xl font-bold">{stats.total_orders || 0}</p><p className="text-sm text-gray-500">Orders</p></div>
        </div>
        <div className="card flex items-center gap-3">
          <DollarSign className="text-green-600" size={32} />
          <div><p className="text-2xl font-bold">Rs. {stats.total_revenue?.toFixed(2) || '0.00'}</p><p className="text-sm text-gray-500">Revenue</p></div>
        </div>
        <div className="card flex items-center gap-3">
          <AlertTriangle className={stats.low_stock_products > 0 ? 'text-red-500' : 'text-gray-400'} size={32} />
          <div><p className="text-2xl font-bold">{stats.low_stock_products || 0}</p><p className="text-sm text-gray-500">Low Stock</p></div>
        </div>
      </div>

      {/* Stock Alerts */}
      {alerts.length > 0 && (
        <div className="card mb-8 border-l-4 border-red-500">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <AlertTriangle className="text-red-500" /> Stock Shortage Alerts
          </h2>
          <div className="space-y-2">
            {alerts.map(a => (
              <div key={a.product_id} className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                <div>
                  <span className="font-medium">{a.product_name}</span>
                  <span className="text-sm text-gray-500 ml-2">Current: {a.current_stock}</span>
                </div>
                <div className="text-right">
                  <span className="text-red-600 font-semibold">Need {a.shortage_units} more</span>
                  <p className="text-xs text-gray-500">30-day forecast: {a.forecasted_demand_30d} units</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Links */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Link to="/seller/products" className="card hover:shadow-md text-center">
          <Package className="mx-auto text-brand-600 mb-2" size={32} />
          <p className="font-medium">Manage Products</p>
        </Link>
        <Link to="/seller/orders" className="card hover:shadow-md text-center">
          <ShoppingCart className="mx-auto text-brand-600 mb-2" size={32} />
          <p className="font-medium">View Orders</p>
        </Link>
        <Link to="/seller/forecast" className="card hover:shadow-md text-center">
          <AlertTriangle className="mx-auto text-brand-600 mb-2" size={32} />
          <p className="font-medium">Stock Forecast</p>
        </Link>
        <Link to="/seller/analytics" className="card hover:shadow-md text-center">
          <DollarSign className="mx-auto text-brand-600 mb-2" size={32} />
          <p className="font-medium">Sales Analytics</p>
        </Link>
      </div>
    </div>
  )
}
