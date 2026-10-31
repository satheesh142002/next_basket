import { useEffect, useState } from 'react'
import { orderAPI } from '../../api'
import { Package } from 'lucide-react'

export default function SellerOrders() {
  const [orders, setOrders] = useState([])

  useEffect(() => {
    orderAPI.sellerOrders().then(res => setOrders(res.data)).catch(() => {})
  }, [])

  const handleStatus = async (orderId, status) => {
    await orderAPI.updateStatus(orderId, status)
    const res = await orderAPI.sellerOrders()
    setOrders(res.data)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-800 mb-6">Orders</h1>
      {orders.length === 0 ? (
        <div className="card text-center py-12"><Package size={48} className="mx-auto text-gray-300 mb-4" /><p className="text-gray-400">No orders yet.</p></div>
      ) : (
        <div className="space-y-4">
          {orders.map(o => (
            <div key={o.id} className="card">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <span className="font-semibold">Order #{o.id.slice(-8).toUpperCase()}</span>
                  <span className="text-sm text-gray-500 ml-3">{new Date(o.created_at).toLocaleString()}</span>
                  <span className="text-sm text-gray-500 ml-3">Customer: {o.customer_username}</span>
                </div>
                <select value={o.status} onChange={e => handleStatus(o.id, e.target.value)} className="input w-40 text-sm">
                  <option value="pending">Pending</option>
                  <option value="confirmed">Confirmed</option>
                  <option value="shipped">Shipped</option>
                  <option value="delivered">Delivered</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>
              <div className="space-y-2">
                {o.items.map((item, i) => (
                  <div key={i} className="flex justify-between text-sm">
                    <span>{item.product_name} x {item.quantity}</span>
                    <span>Rs. {(item.price * item.quantity).toFixed(2)}</span>
                  </div>
                ))}
              </div>
              <div className="flex justify-between font-bold pt-3 border-t mt-3"><span>Total</span><span>Rs. {o.total_amount.toFixed(2)}</span></div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
