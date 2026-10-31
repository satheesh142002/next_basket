import { createContext, useContext, useState, useCallback } from 'react'
import { cartAPI } from '../api'

const CartContext = createContext(null)

export function CartProvider({ children }) {
  const [cart, setCart] = useState({ items: [], total: 0, item_count: 0 })
  const [cartLoading, setCartLoading] = useState(false)

  const fetchCart = useCallback(async () => {
    const token = localStorage.getItem('token')
    if (!token) return
    try {
      setCartLoading(true)
      const res = await cartAPI.get()
      setCart(res.data)
    } catch {
      // ignore if not logged in as customer
    } finally {
      setCartLoading(false)
    }
  }, [])

  const refreshCart = useCallback(() => {
    fetchCart()
  }, [fetchCart])

  return (
    <CartContext.Provider value={{ cart, cartLoading, fetchCart, refreshCart }}>
      {children}
    </CartContext.Provider>
  )
}

export function useCart() {
  const ctx = useContext(CartContext)
  if (!ctx) throw new Error('useCart must be used within CartProvider')
  return ctx
}
