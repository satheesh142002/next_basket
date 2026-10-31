import { useEffect, useState } from 'react'
import { sellerAPI } from '../../api'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Legend, PieChart, Pie, Cell } from 'recharts'
import { DollarSign } from 'lucide-react'

const PIE_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']

export default function SellerAnalytics() {
  const [data, setData] = useState({ monthly_sales: [], by_category: [], top_products: [] })

  useEffect(() => {
    sellerAPI.analytics().then(res => setData(res.data)).catch(() => {})
  }, [])

  const totalRevenue = data.monthly_sales.reduce((s, m) => s + m.revenue, 0)

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-800 mb-6">Sales Analytics</h1>

      <div className="card mb-6 flex items-center gap-3">
        <DollarSign className="text-green-600" size={32} />
        <div><p className="text-2xl font-bold">Rs. {totalRevenue.toFixed(2)}</p><p className="text-sm text-gray-500">Total Revenue (12 months)</p></div>
      </div>

      {/* Monthly Revenue */}
      <div className="card mb-6">
        <h3 className="font-bold mb-4">Monthly Sales Trend</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data.monthly_sales}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="revenue" stroke="#3b82f6" strokeWidth={2} name="Revenue" />
            <Line type="monotone" dataKey="units" stroke="#10b981" strokeWidth={2} name="Units Sold" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Revenue by Category */}
        <div className="card">
          <h3 className="font-bold mb-4">Revenue by Category</h3>
          {data.by_category.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={data.by_category} dataKey="revenue" nameKey="category" cx="50%" cy="50%" outerRadius={100} label>
                  {data.by_category.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="text-gray-400 text-center py-20">No data yet.</p>}
        </div>

        {/* Top Products */}
        <div className="card">
          <h3 className="font-bold mb-4">Top Products</h3>
          {data.top_products.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={data.top_products} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="product_name" tick={{ fontSize: 10 }} width={100} />
                <Tooltip />
                <Bar dataKey="units_sold" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-gray-400 text-center py-20">No data yet.</p>}
        </div>
      </div>
    </div>
  )
}
