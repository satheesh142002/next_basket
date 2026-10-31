import { useState } from 'react'
import { Link } from 'react-router-dom'
import { formatPrice } from '../utils/format'

const CATEGORY_ICONS = {
  'Furniture':       '🪑',
  'Office Supplies': '📎',
  'Technology':      '💻',
}

export default function ProductCard({ product, onAddToCart, showAdd = true }) {
  const [imgError, setImgError] = useState(false)
  const icon = CATEGORY_ICONS[product.category] || '📦'
  const showImage = product.image_url && !imgError

  return (
    <div className="bg-white shadow-md p-3 flex flex-col text-center">
      <Link to={`/product/${product.id}`}>
        <h3 className="font-semibold text-ink hover:text-brand-600 line-clamp-2 text-sm leading-snug min-h-[2.5rem]">
          {product.category} - {product.name}
        </h3>
      </Link>
      <p className="text-xs mt-1">
        <span className="text-brand-600">Price</span> {formatPrice(product.price)}
      </p>

      <Link to={`/product/${product.id}`} className="block my-3">
        <div className="h-44 flex items-center justify-center">
          {showImage ? (
            <img src={product.image_url} alt={product.name} className="max-h-full max-w-full object-contain"
              onError={() => setImgError(true)} loading="lazy" />
          ) : (
            <span className="text-6xl select-none">{icon}</span>
          )}
        </div>
      </Link>

      <p className="text-xs text-gray-500 text-left line-clamp-1 min-h-[1rem]">
        {product.recommendation_reason || product.description}
      </p>
      <p className={`text-xs text-left mt-1 ${product.quantity > 0 ? 'text-green-600' : 'text-red-500'}`}>
        {product.quantity > 0 ? `${product.quantity} in stock` : 'Out of stock'}
      </p>

      <div className="flex items-center justify-between mt-2 text-sm">
        {showAdd && onAddToCart && product.quantity > 0 ? (
          <button onClick={() => onAddToCart(product.id)} className="font-semibold text-brand-600 hover:text-brand-700">
            Add to Cart
          </button>
        ) : <span />}
        <Link to={`/product/${product.id}`} className="text-ink hover:text-brand-600">Reviews</Link>
      </div>
    </div>
  )
}
