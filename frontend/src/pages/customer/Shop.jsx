import { useState, useEffect, useCallback } from 'react'
import { productAPI, cartAPI, customerAPI } from '../../api'
import { useCart } from '../../context/CartContext'
import ProductCard from '../../components/ProductCard'
import { Search } from 'lucide-react'

export default function Shop() {
  const { refreshCart } = useCart()
  const [products, setProducts] = useState([])
  const [categories, setCategories] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [loading, setLoading] = useState(true)

  const loadProducts = useCallback(async () => {
    setLoading(true)
    const params = { page, page_size: 12 }
    if (search) params.search = search
    if (category) params.category = category
    const res = await productAPI.list(params)
    setProducts(res.data.products)
    setTotal(res.data.total)
    setLoading(false)
  }, [page, search, category])

  useEffect(() => {
    productAPI.categories().then(res => setCategories(res.data)).catch(() => {})
  }, [])

  useEffect(() => {
    const t = setTimeout(loadProducts, 300)
    return () => clearTimeout(t)
  }, [loadProducts])

  const handleAddToCart = async (productId) => {
    try {
      await cartAPI.add(productId, 1)
      refreshCart()
      alert('Added to cart!')
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to add')
    }
  }

  const handleSearch = (e) => {
    setSearch(e.target.value)
    setPage(1)
    if (e.target.value) {
      customerAPI.trackSearch(e.target.value).catch(() => {})
    }
  }

  const totalPages = Math.ceil(total / 12)

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-center text-2xl font-semibold mb-6">Products</h1>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 text-gray-400" size={20} />
          <input className="input pl-10" placeholder="Search products..." value={search} onChange={handleSearch} />
        </div>
        <select className="input sm:w-48" value={category} onChange={(e) => { setCategory(e.target.value); setPage(1) }}>
          <option value="">All Categories</option>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600" /></div>
      ) : products.length === 0 ? (
        <p className="text-center text-gray-400 py-20">No products found.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {products.map(p => <ProductCard key={p.id} product={p} onAddToCart={handleAddToCart} />)}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-8">
          <button className="btn-secondary" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Prev</button>
          <span className="px-4 py-2 text-gray-600">Page {page} of {totalPages}</span>
          <button className="btn-secondary" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</button>
        </div>
      )}
    </div>
  )
}
