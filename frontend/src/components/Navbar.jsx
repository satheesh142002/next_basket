import { Link, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useCart } from '../context/CartContext'
import { useEffect } from 'react'

const linkCls = ({ isActive }) =>
  `text-sm px-2 hover:text-brand-300 ${isActive ? 'text-brand-300' : 'text-white'}`

export default function Navbar() {
  const { user, logout, isAdmin, isSeller, isCustomer } = useAuth()
  const { cart, fetchCart } = useCart()
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    if (isCustomer) fetchCart()
  }, [isCustomer, fetchCart, location.pathname])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="relative z-50">
      <nav className="nav-trapezoid bg-ink mx-auto w-[72%] min-w-[20rem] h-9 flex items-center justify-center gap-5">
        {!user && (
          <>
            <NavLink to="/login?role=customer" className={linkCls}>Customer</NavLink>
            <NavLink to="/login?role=seller" className={linkCls}>Seller</NavLink>
            <NavLink to="/login?role=admin" className={linkCls}>Admin</NavLink>
          </>
        )}
        {isCustomer && (
          <>
            <NavLink to="/shop" className={linkCls}>Home</NavLink>
            <NavLink to="/recommendations" className={linkCls}>Next Basket</NavLink>
            <NavLink to="/cart" className={linkCls}>Cart{cart.item_count > 0 ? ` (${cart.item_count})` : ''}</NavLink>
            <NavLink to="/orders" className={linkCls}>Orders</NavLink>
          </>
        )}
        {isSeller && (
          <>
            <NavLink to="/seller" end className={linkCls}>Home</NavLink>
            <NavLink to="/seller/products" className={linkCls}>Products</NavLink>
            <NavLink to="/seller/orders" className={linkCls}>Orders</NavLink>
            <NavLink to="/seller/forecast" className={linkCls}>Forecasting</NavLink>
            <NavLink to="/seller/analytics" className={linkCls}>Analytics</NavLink>
          </>
        )}
        {isAdmin && (
          <>
            <NavLink to="/admin" end className={linkCls}>Home</NavLink>
            <NavLink to="/admin/sellers" className={linkCls}>Seller Details</NavLink>
            <NavLink to="/admin/products" className={linkCls}>Products</NavLink>
            <NavLink to="/admin/orders" className={linkCls}>Orders</NavLink>
            <NavLink to="/admin/ml" className={linkCls}>Training</NavLink>
          </>
        )}
        {user && (
          <button onClick={handleLogout} className="text-sm px-2 text-white hover:text-brand-300">Logout</button>
        )}
      </nav>
      <Link to="/" className="block text-center text-white text-lg font-medium -mb-7 relative top-1">Next Basket</Link>
    </header>
  )
}
