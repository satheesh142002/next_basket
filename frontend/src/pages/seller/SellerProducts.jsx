import { useEffect, useState } from 'react'
import { sellerAPI, productAPI } from '../../api'
import { Plus, Pencil, Trash2, X } from 'lucide-react'

export default function SellerProducts() {
  const [products, setProducts] = useState([])
  const [categories, setCategories] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({ name: '', category: '', price: 0, quantity: 0, description: '', image_url: '' })

  const load = async () => {
    const res = await sellerAPI.myProducts()
    setProducts(res.data)
  }

  useEffect(() => {
    load()
    productAPI.categories().then(res => setCategories(res.data)).catch(() => {})
  }, [])

  const openAdd = () => {
    setEditing(null)
    setForm({ name: '', category: categories[0] || '', price: 0, quantity: 0, description: '', image_url: '' })
    setShowForm(true)
  }

  const openEdit = (p) => {
    setEditing(p.id)
    setForm({ name: p.name, category: p.category, price: p.price, quantity: p.quantity, description: p.description || '', image_url: p.image_url || '' })
    setShowForm(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (editing) {
      await productAPI.update(editing, form)
    } else {
      await productAPI.create(form)
    }
    setShowForm(false)
    load()
  }

  const handleDelete = async (id) => {
    if (confirm('Delete this product?')) {
      await productAPI.delete(id)
      load()
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">My Products</h1>
        <button onClick={openAdd} className="btn-primary flex items-center gap-2 text-sm"><Plus size={16} /> Add Product</button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="form-card mb-8">
          <div className="flex items-center justify-between">
            <h2>{editing ? 'Edit Product' : 'Add Product'}</h2>
            <button type="button" onClick={() => setShowForm(false)} aria-label="Close"><X size={16} /></button>
          </div>
          <div className="form-row"><label>Category</label>
            <select className="form-input" value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} required>
              {categories.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="form-row"><label>Product</label><input className="form-input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required /></div>
          <div className="form-row"><label>Price</label><input type="number" step="0.01" className="form-input" value={form.price} onChange={e => setForm({ ...form, price: parseFloat(e.target.value) })} required /></div>
          <div className="form-row"><label>Quantity</label><input type="number" className="form-input" value={form.quantity} onChange={e => setForm({ ...form, quantity: parseInt(e.target.value) })} required /></div>
          <div className="form-row"><label>Photo (URL)</label><input className="form-input" value={form.image_url} onChange={e => setForm({ ...form, image_url: e.target.value })} placeholder="https://..." /></div>
          <div className="form-row"><label>Description</label><textarea className="form-input" rows={2} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></div>
          <div className="form-row"><span /><button type="submit" className="btn-form">{editing ? 'Update' : 'Add'}</button></div>
        </form>
      )}

      {products.length === 0 ? (
        <p className="text-center text-gray-400 py-12">No products yet. Click "Add Product" to get started.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="table-yellow">
            <thead>
              <tr><th>Name</th><th>Category</th><th>Price</th><th>Stock</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {products.map(p => (
                <tr key={p.id}>
                  <td >{p.name}</td>
                  <td >{p.category}</td>
                  <td>Rs. {p.price.toFixed(2)}</td>
                  <td><span className={p.quantity <= 10 ? 'badge-red' : 'badge-green'}>{p.quantity}</span></td>
                  <td className="flex gap-2">
                    <button onClick={() => openEdit(p)} className="text-brand-600 hover:text-brand-700"><Pencil size={18} /></button>
                    <button onClick={() => handleDelete(p.id)} className="text-red-500 hover:text-red-700"><Trash2 size={18} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
