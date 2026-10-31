// Prices are shown as "Rs. 5000.0" (whole amounts keep one decimal, others up to two)
export const formatPrice = (n) => {
  const v = Number(n) || 0
  return `Rs. ${Number.isInteger(v) ? v.toFixed(1) : +v.toFixed(2)}`
}

// dd-mm-yyyy
export const formatDate = (d) => {
  const t = new Date(d)
  const p = (x) => String(x).padStart(2, '0')
  return `${p(t.getDate())}-${p(t.getMonth() + 1)}-${t.getFullYear()}`
}
