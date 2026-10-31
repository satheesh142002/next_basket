import { useEffect, useState } from 'react'
import { adminAPI } from '../../api'
import { Trash2, Package } from 'lucide-react'

export default function AdminProducts() {
  const [products, setProducts] = useState([])

  const load = async () => {
    const res = await adminAPI.products()
    setProducts(res.data)
  }

  useEffect(() => { load() }, [])

  const handleDelete = async (id) => {
    if (confirm('Delete this product?')) {
      await adminAPI.deleteProduct(id)
      load()
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-800 mb-6">All Products</h1>
      {products.length === 0 ? (
        <div className="card text-center py-12"><Package size={48} className="mx-auto text-gray-300 mb-4" /><p className="text-gray-400">No products yet.</p></div>
      ) : (
        <div className="overflow-x-auto card p-0">
          <table className="w-full">
            <thead className="bg-gray-50 text-left text-sm text-gray-500">
              <tr><th className="p-4">Name</th><th className="p-4">Category</th><th className="p-4">Price</th><th className="p-4">Stock</th><th className="p-4">Seller</th><th className="p-4">Action</th></tr>
            </thead>
            <tbody>
              {products.map(p => (
                <tr key={p.id} className="border-t">
                  <td className="p-4 font-medium">{p.name}</td>
                  <td className="p-4 text-gray-500">{p.category}</td>
                  <td className="p-4">Rs. {p.price.toFixed(2)}</td>
                  <td className="p-4"><span className={p.quantity <= 10 ? 'badge-red' : 'badge-green'}>{p.quantity}</span></td>
                  <td className="p-4 text-gray-500">{p.seller_username}</td>
                  <td className="p-4"><button onClick={() => handleDelete(p.id)} className="text-red-500 hover:text-red-700"><Trash2 size={18} /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
