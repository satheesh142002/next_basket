import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { cartAPI, orderAPI, customerAPI } from '../../api'
import { useCart } from '../../context/CartContext'
import { formatPrice } from '../../utils/format'

export default function Cart() {
  const { cart, fetchCart } = useCart()
  const navigate = useNavigate()
  const [placing, setPlacing] = useState(false)
  const [qtys, setQtys] = useState({})
  const [recs, setRecs] = useState([])
  const [msg, setMsg] = useState('')

  useEffect(() => {
    fetchCart()
    customerAPI.recommendations().then(res => setRecs(res.data.recommendations || [])).catch(() => {})
  }, [fetchCart])

  useEffect(() => {
    setQtys(Object.fromEntries(cart.items.map(i => [i.id, i.quantity])))
  }, [cart])

  const total = cart.items.reduce((sum, i) => sum + i.price * (Number(qtys[i.id]) || 0), 0)

  // "Check" applies the typed quantities, limited to what is in stock
  const handleCheck = async () => {
    const short = []
    for (const item of cart.items) {
      let q = Math.max(1, parseInt(qtys[item.id], 10) || 1)
      if (q > item.available_quantity) {
        short.push(`${item.product_name} (only ${item.available_quantity} available)`)
        q = item.available_quantity
      }
      if (q !== item.quantity) await cartAPI.update(item.id, q)
    }
    setMsg(short.length ? `Quantity reduced: ${short.join(', ')}` : 'Cart updated')
    fetchCart()
  }

  const handleRemove = async (itemId) => {
    await cartAPI.remove(itemId)
    fetchCart()
  }

  const handleCheckout = async () => {
    setPlacing(true)
    try {
      const items = cart.items.map(i => ({
        product_id: i.product_id,
        product_name: i.product_name,
        quantity: i.quantity,
        price: i.price,
        seller_username: i.seller_username,
      }))
      await orderAPI.place(items, cart.total)
      alert('Order placed successfully!')
      fetchCart()
      navigate('/orders')
    } catch (err) {
      alert(err.response?.data?.detail || 'Checkout failed')
    } finally {
      setPlacing(false)
    }
  }

  const changed = cart.items.some(i => Number(qtys[i.id]) !== i.quantity)

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="page-title">Cart</h1>
      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          {cart.item_count === 0 ? (
            <div className="text-center py-16">
              <p className="text-gray-500 mb-4">Your cart is empty</p>
              <button onClick={() => navigate('/shop')} className="btn-primary">Start Shopping</button>
            </div>
          ) : (
            <>
              <table className="table-dark">
                <thead>
                  <tr><th>Product</th><th>Price</th><th>Quantity</th><th>Total</th><th>Remove</th></tr>
                </thead>
                <tbody>
                  {cart.items.map(item => (
                    <tr key={item.id} className="border-b border-gray-100">
                      <td className="!text-left">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 flex-shrink-0 flex items-center justify-center">
                            {item.image_url
                              ? <img src={item.image_url} alt="" className="max-h-8 max-w-8 object-contain" onError={e => { e.target.style.display = 'none' }} />
                              : <span>📦</span>}
                          </div>
                          <span>{item.product_name}</span>
                        </div>
                      </td>
                      <td>{formatPrice(item.price)}</td>
                      <td>
                        <input
                          type="number" min="1" max={item.available_quantity}
                          className="w-20 border border-gray-300 px-2 py-1 text-sm text-ink"
                          value={qtys[item.id] ?? item.quantity}
                          onChange={e => setQtys({ ...qtys, [item.id]: e.target.value })}
                        />
                      </td>
                      <td>{item.price * (Number(qtys[item.id]) || 0)}</td>
                      <td>
                        <button onClick={() => handleRemove(item.id)} aria-label="Remove"
                          className="bg-red-500 hover:bg-red-600 text-white text-xs w-6 h-6 rounded-sm">✕</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="text-center mt-5">
                <button onClick={handleCheck} className="btn-blue w-64">Check</button>
                {msg && <p className="text-xs text-gray-500 mt-2">{msg}</p>}
              </div>
            </>
          )}
        </div>

        <aside>
          <div className="flex justify-between text-xs mb-2"><span>Total</span><span>Rs. {total}</span></div>
          <button onClick={handleCheckout} disabled={placing || cart.item_count === 0 || changed} className="btn-blue w-full">
            {placing ? 'Placing order...' : 'Buy Now'}
          </button>
          {changed && <p className="text-xs text-gray-400 mt-1">Press Check to confirm the new quantities first.</p>}

          <h2 className="text-sm mt-10 pb-2 border-b border-gray-200">Next Basket Recommendation</h2>
          {recs.length === 0 ? (
            <p className="text-xs text-gray-400 py-3">No recommendations yet.</p>
          ) : (
            recs.slice(0, 6).map(r => (
              <div key={r.id} className="py-2 border-b border-gray-100 text-xs text-gray-600">
                <button onClick={() => navigate(`/product/${r.id}`)} className="text-left hover:text-brand-600">{r.name}</button>
                <div>Price: {formatPrice(r.price)}</div>
              </div>
            ))
          )}
        </aside>
      </div>
    </div>
  )
}
