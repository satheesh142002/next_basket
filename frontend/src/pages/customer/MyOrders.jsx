import { Fragment, useEffect, useState } from 'react'
import { orderAPI } from '../../api'
import { formatPrice, formatDate } from '../../utils/format'

export default function MyOrders() {
  const [orders, setOrders] = useState([])
  const [open, setOpen] = useState(null)

  useEffect(() => {
    orderAPI.myOrders().then(res => setOrders(res.data)).catch(() => {})
  }, [])

  // Bill IDs count up from the oldest order
  const sorted = [...orders].sort((a, b) => new Date(a.created_at) - new Date(b.created_at))

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <h1 className="page-title">Purchased</h1>
      {orders.length === 0 ? (
        <p className="text-center text-gray-400 py-12">No orders yet.</p>
      ) : (
        <table className="table-yellow">
          <thead>
            <tr><th>Bill ID</th><th>Order Date</th><th>Amount</th><th>Status</th><th>View Order</th></tr>
          </thead>
          <tbody>
            {sorted.map((o, i) => (
              <Fragment key={o.id}>
                <tr>
                  <td>{i + 1}</td>
                  <td>{formatDate(o.created_at)}</td>
                  <td>{o.total_amount}</td>
                  <td className="capitalize">{o.status}</td>
                  <td>
                    <button className="text-ink hover:text-brand-600" onClick={() => setOpen(open === o.id ? null : o.id)}>
                      {open === o.id ? 'Hide' : 'View'}
                    </button>
                  </td>
                </tr>
                {open === o.id && (
                  <tr>
                    <td colSpan={5} className="bg-white">
                      {o.items.map((item, k) => (
                        <div key={k} className="flex justify-between text-xs py-0.5">
                          <span>{item.product_name} x {item.quantity}</span>
                          <span>{formatPrice(item.price * item.quantity)}</span>
                        </div>
                      ))}
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
