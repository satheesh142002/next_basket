import { useState, useEffect } from 'react'
import { customerAPI, cartAPI } from '../../api'
import { useCart } from '../../context/CartContext'
import ProductCard from '../../components/ProductCard'
import { Sparkles } from 'lucide-react'

export default function Recommendations() {
  const { refreshCart } = useCart()
  const [recs, setRecs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    customerAPI.recommendations()
      .then(res => setRecs(res.data.recommendations))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleAddToCart = async (productId) => {
    try {
      await cartAPI.add(productId, 1)
      refreshCart()
      alert('Added to cart!')
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to add')
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-6">
        <Sparkles className="text-brand-600" size={28} />
        <h1 className="text-2xl font-semibold">Your Next Basket</h1>
      </div>
      <p className="text-gray-500 mb-6">
        Personalized recommendations powered by our Decision Tree model, based on your browsing history and purchase patterns.
      </p>

      {loading ? (
        <div className="flex justify-center py-20"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600" /></div>
      ) : recs.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-400 text-lg">No recommendations available yet.</p>
          <p className="text-gray-400 text-sm mt-2">Browse and purchase products to get personalized recommendations!</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {recs.map(p => <ProductCard key={p.id} product={p} onAddToCart={handleAddToCart} />)}
        </div>
      )}
    </div>
  )
}
