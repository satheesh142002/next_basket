import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { productAPI, cartAPI } from '../../api'
import { useAuth } from '../../context/AuthContext'
import { useCart } from '../../context/CartContext'
import { Star, ShoppingCart, ArrowLeft } from 'lucide-react'

const CATEGORY_COLOURS = {
  'Furniture':       'from-amber-100 to-amber-200',
  'Office Supplies': 'from-blue-100 to-blue-200',
  'Technology':      'from-violet-100 to-violet-200',
}
const CATEGORY_ICONS = {
  'Furniture':       '🪑',
  'Office Supplies': '📎',
  'Technology':      '💻',
}

export default function ProductDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user, isCustomer } = useAuth()
  const { refreshCart } = useCart()
  const [product, setProduct] = useState(null)
  const [reviews, setReviews] = useState([])
  const [quantity, setQuantity] = useState(1)
  const [loading, setLoading] = useState(true)
  const [reviewRating, setReviewRating] = useState(5)
  const [reviewComment, setReviewComment] = useState('')
  const [imgError, setImgError] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        const [pRes, rRes] = await Promise.all([
          productAPI.get(id),
          productAPI.reviews(id),
        ])
        setProduct(pRes.data)
        setReviews(rRes.data)
      } catch {
        navigate('/shop')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id])

  const handleAddToCart = async () => {
    try {
      await cartAPI.add(id, quantity)
      refreshCart()
      alert('Added to cart!')
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to add to cart')
    }
  }

  const handleSubmitReview = async (e) => {
    e.preventDefault()
    try {
      await productAPI.addReview(id, reviewRating, reviewComment)
      const rRes = await productAPI.reviews(id)
      setReviews(rRes.data)
      setReviewComment('')
      alert('Review submitted!')
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to submit review')
    }
  }

  if (loading) return <div className="flex justify-center py-20"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600" /></div>
  if (!product) return null

  const gradient = CATEGORY_COLOURS[product.category] || 'from-gray-100 to-gray-200'
  const icon = CATEGORY_ICONS[product.category] || '📦'
  const showImage = product.image_url && !imgError

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-gray-500 hover:text-brand-600 mb-4">
        <ArrowLeft size={18} /> Back
      </button>

      <div className="grid md:grid-cols-2 gap-8">
        <div className="card">
          <div className={`aspect-square rounded-xl overflow-hidden flex items-center justify-center bg-gradient-to-br ${gradient}`}>
            {showImage ? (
              <img
                src={product.image_url}
                alt={product.name}
                className="w-full h-full object-cover"
                onError={() => setImgError(true)}
              />
            ) : (
              <span className="text-9xl select-none">{icon}</span>
            )}
          </div>
        </div>

        <div className="card">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">{product.name}</h1>
          <p className="text-gray-500 mb-3">{product.category}</p>
          <div className="flex items-center gap-2 mb-4">
            {product.avg_rating > 0 ? (
              <>
                <div className="flex">
                  {[1, 2, 3, 4, 5].map(i => (
                    <Star key={i} size={18} className={i <= Math.round(product.avg_rating) ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'} />
                  ))}
                </div>
                <span className="text-sm text-gray-500">{product.avg_rating} ({product.review_count} reviews)</span>
              </>
            ) : (
              <span className="text-sm text-gray-400">No reviews yet</span>
            )}
          </div>
          <p className="text-3xl font-bold text-brand-700 mb-4">Rs. {product.price.toFixed(2)}</p>
          <p className="text-gray-600 mb-4">{product.description || 'No description available.'}</p>
          <p className={`text-sm mb-4 ${product.quantity > 0 ? 'text-green-600' : 'text-red-600'}`}>
            {product.quantity > 0 ? `${product.quantity} in stock` : 'Out of stock'}
          </p>

          {isCustomer && product.quantity > 0 && (
            <div className="flex items-center gap-4 mb-4">
              <div className="flex items-center border rounded-lg">
                <button className="px-3 py-2 hover:bg-gray-100" onClick={() => setQuantity(Math.max(1, quantity - 1))}>-</button>
                <span className="px-4 py-2">{quantity}</span>
                <button className="px-3 py-2 hover:bg-gray-100" onClick={() => setQuantity(Math.min(product.quantity, quantity + 1))}>+</button>
              </div>
              <button onClick={handleAddToCart} className="btn-primary flex items-center gap-2">
                <ShoppingCart size={18} /> Add to Cart
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Reviews */}
      <div className="mt-8 grid md:grid-cols-2 gap-8">
        <div className="card">
          <h2 className="text-xl font-bold mb-4">Customer Reviews ({reviews.length})</h2>
          {reviews.length === 0 ? (
            <p className="text-gray-400">No reviews yet. Be the first to review!</p>
          ) : (
            <div className="space-y-4">
              {reviews.map(r => (
                <div key={r.id} className="border-b pb-3">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="flex">
                      {[1, 2, 3, 4, 5].map(i => (
                        <Star key={i} size={14} className={i <= r.rating ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'} />
                      ))}
                    </div>
                    <span className="text-sm text-gray-500">{r.customer_username}</span>
                  </div>
                  <p className="text-gray-600 text-sm">{r.comment || 'No comment'}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {isCustomer && (
          <div className="card">
            <h2 className="text-xl font-bold mb-4">Write a Review</h2>
            <form onSubmit={handleSubmitReview} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Rating</label>
                <select className="input" value={reviewRating} onChange={(e) => setReviewRating(Number(e.target.value))}>
                  {[5, 4, 3, 2, 1].map(r => <option key={r} value={r}>{r} stars</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Comment</label>
                <textarea className="input" rows={4} value={reviewComment} onChange={(e) => setReviewComment(e.target.value)} />
              </div>
              <button type="submit" className="btn-primary">Submit Review</button>
            </form>
          </div>
        )}
      </div>
    </div>
  )
}
