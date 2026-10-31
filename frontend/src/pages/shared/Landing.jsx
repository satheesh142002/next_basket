import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { TrendingUp, Brain, Package, ShoppingCart, BarChart3 } from 'lucide-react'

export default function Landing() {
  const { user } = useAuth()

  return (
    <div>
      {/* Hero */}
      <section className="hero-bg text-center pt-20 pb-16 px-4">
        <p className="text-sm text-ink/70 max-w-xl mx-auto mb-10">
          Predictive analytics and personalized recommendations for an enhanced e-commerce experience.
          ARIMA-powered sales forecasting meets Decision Tree-driven product recommendations.
        </p>
        <h1 className="text-5xl font-bold text-white drop-shadow-sm leading-tight">GET START<br />YOUR FAVORITE SHOPPING</h1>
        <div className="mt-10">
          <Link
            to={user ? (user.role === 'admin' ? '/admin' : user.role === 'seller' ? '/seller' : '/shop') : '/login?role=customer'}
            className="inline-block bg-ink text-white text-sm font-semibold px-10 py-3 hover:bg-black"
          >
            BUY NOW
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 max-w-7xl mx-auto px-4">
        <h2 className="text-3xl font-bold text-center text-gray-800 mb-12">Key Features</h2>
        <div className="grid md:grid-cols-3 gap-8">
          <div className="card text-center">
            <TrendingUp size={48} className="mx-auto text-brand-600 mb-4" />
            <h3 className="text-xl font-semibold mb-2">ARIMA Sales Forecasting</h3>
            <p className="text-gray-600">
              Predict future stock levels using time-series analysis. Get proactive alerts before shortages happen.
            </p>
          </div>
          <div className="card text-center">
            <Brain size={48} className="mx-auto text-brand-600 mb-4" />
            <h3 className="text-xl font-semibold mb-2">Decision Tree Recommendations</h3>
            <p className="text-gray-600">
              Personalized next-basket suggestions based on browsing behavior, purchase history, and demographics.
            </p>
          </div>
          <div className="card text-center">
            <BarChart3 size={48} className="mx-auto text-brand-600 mb-4" />
            <h3 className="text-xl font-semibold mb-2">Real-time Analytics</h3>
            <p className="text-gray-600">
              Comprehensive dashboards for admins, sellers, and customers with live sales data and insights.
            </p>
          </div>
        </div>
      </section>

      {/* Role cards */}
      <section className="bg-gray-50 py-20">
        <div className="max-w-7xl mx-auto px-4">
          <h2 className="text-3xl font-bold text-center text-gray-800 mb-12">Built for Everyone</h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="card">
              <Package className="text-brand-600 mb-3" size={40} />
              <h3 className="text-xl font-semibold mb-2">Sellers</h3>
              <ul className="text-gray-600 space-y-2 text-sm">
                <li>Manage products and inventory</li>
                <li>View stock forecasts & alerts</li>
                <li>Sales analytics by category & region</li>
                <li>Process and track orders</li>
              </ul>
            </div>
            <div className="card">
              <ShoppingCart className="text-brand-600 mb-3" size={40} />
              <h3 className="text-xl font-semibold mb-2">Customers</h3>
              <ul className="text-gray-600 space-y-2 text-sm">
                <li>Browse and search products</li>
                <li>Personalized recommendations</li>
                <li>Shopping cart & checkout</li>
                <li>Order tracking & reviews</li>
              </ul>
            </div>
            <div className="card">
              <BarChart3 className="text-brand-600 mb-3" size={40} />
              <h3 className="text-xl font-semibold mb-2">Admins</h3>
              <ul className="text-gray-600 space-y-2 text-sm">
                <li>Approve & manage sellers</li>
                <li>Oversee all products & orders</li>
                <li>Trigger ML model training</li>
                <li>Platform-wide statistics</li>
              </ul>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
