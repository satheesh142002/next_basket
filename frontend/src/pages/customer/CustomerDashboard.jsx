import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { orderAPI, customerAPI } from '../../api'
import { Package, Heart, ShoppingBag, TrendingUp } from 'lucide-react'

export default function CustomerDashboard() {
  const [orders, setOrders] = useState([])
  const [recs, setRecs] = useState([])

  useEffect(() => {
    orderAPI.myOrders().then(res => setOrders(res.data)).catch(() => {})
    customerAPI.recommendations().then(res => setRecs(res.data.recommendations)).catch(() => {})
  }, [])

  const totalSpent = orders.reduce((sum, o) => sum + o.total_amount, 0)

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-800 mb-6">My Dashboard</h1>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="card flex items-center gap-3">
          <ShoppingBag className="text-brand-600" size={32} />
          <div><p className="text-2xl font-bold">{orders.length}</p><p className="text-sm text-gray-500">Total Orders</p></div>
        </div>
        <div className="card flex items-center gap-3">
          <TrendingUp className="text-green-600" size={32} />
          <div><p className="text-2xl font-bold">Rs. {totalSpent.toFixed(2)}</p><p className="text-sm text-gray-500">Total Spent</p></div>
        </div>
        <div className="card flex items-center gap-3">
          <Heart className="text-red-500" size={32} />
          <div><p className="text-2xl font-bold">{recs.length}</p><p className="text-sm text-gray-500">Recommendations</p></div>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-xl font-bold mb-4">Recent Orders</h2>
          {orders.length === 0 ? (
            <p className="text-gray-400">No orders yet. <Link to="/shop" className="text-brand-600">Start shopping</Link></p>
          ) : (
            <div className="space-y-3">
              {orders.slice(0, 5).map(o => (
                <div key={o.id} className="flex items-center justify-between border-b pb-2">
                  <div>
                    <p className="font-medium">{o.items.length} item(s)</p>
                    <p className="text-sm text-gray-500">{new Date(o.created_at).toLocaleDateString()}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold">Rs. {o.total_amount.toFixed(2)}</p>
                    <span className={`badge ${o.status === 'delivered' ? 'badge-green' : o.status === 'cancelled' ? 'badge-red' : 'badge-yellow'}`}>{o.status}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
          <Link to="/orders" className="text-brand-600 text-sm hover:underline mt-3 block">View all orders</Link>
        </div>

        <div className="card">
          <h2 className="text-xl font-bold mb-4">Quick Links</h2>
          <div className="space-y-3">
            <Link to="/shop" className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50">
              <Package className="text-brand-600" /> Browse Products
            </Link>
            <Link to="/recommendations" className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50">
              <Heart className="text-red-500" /> My Recommendations
            </Link>
            <Link to="/cart" className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50">
              <ShoppingBag className="text-green-600" /> View Cart
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
