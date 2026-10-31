import { useEffect, useState } from 'react'
import { sellerAPI } from '../../api'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts'
import { AlertTriangle, TrendingDown } from 'lucide-react'

export default function StockForecast() {
  const [products, setProducts] = useState([])
  const [selected, setSelected] = useState(null)
  const [forecast, setForecast] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    sellerAPI.myProducts().then(res => setProducts(res.data)).catch(() => {})
  }, [])

  const loadForecast = async (productId) => {
    setLoading(true)
    setSelected(productId)
    try {
      const res = await sellerAPI.forecast(productId)
      setForecast(res.data)
    } catch {
      setForecast(null)
    } finally {
      setLoading(false)
    }
  }

  const chartData = forecast ? forecast.forecast_dates.map((d, i) => ({ date: d.slice(5), demand: forecast.forecast_values[i], band: forecast.lower_values ? [forecast.lower_values[i], forecast.upper_values[i]] : undefined })) : []

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-xl font-semibold text-center mb-6">Sales Forecasting (ARIMA)</h1>

      <div className="grid lg:grid-cols-4 gap-6">
        <div className="border border-brand-600 p-3 lg:col-span-1 h-fit">
          <h2 className="text-center text-green-600 mb-3">Forecasting Products</h2>
          <div className="space-y-1 max-h-96 overflow-y-auto">
            {products.map(p => (
              <button key={p.id} onClick={() => loadForecast(p.id)} className={`w-full text-left p-2 rounded-lg ${selected === p.id ? 'bg-brand-100 text-brand-700' : 'hover:bg-gray-50'}`}>
                <span className="text-xs">{p.name} - Available: {p.quantity}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="lg:col-span-3">
          {loading ? (
            <div className="flex justify-center py-20"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600" /></div>
          ) : !forecast ? (
            <div className="card text-center py-12"><p className="text-gray-400">Select a product to view its 30-day stock forecast.</p></div>
          ) : (
            <div className="space-y-4">
              {/* Summary */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="card">
                  <p className="text-sm text-gray-500">Current Stock</p>
                  <p className="text-2xl font-bold">{forecast.current_stock}</p>
                </div>
                <div className="card">
                  <p className="text-sm text-gray-500">Forecasted Demand (30d)</p>
                  <p className="text-2xl font-bold text-brand-600">{forecast.total_forecasted_demand}</p>
                </div>
                <div className={`card ${forecast.shortage_predicted ? 'border-red-300' : 'border-green-300'}`}>
                  <p className="text-sm text-gray-500">Shortage Predicted</p>
                  <p className={`text-2xl font-bold ${forecast.shortage_predicted ? 'text-red-600' : 'text-green-600'}`}>
                    {forecast.shortage_predicted ? 'Yes' : 'No'}
                  </p>
                </div>
                <div className="card">
                  <p className="text-sm text-gray-500">Units Needed</p>
                  <p className="text-2xl font-bold text-orange-600">{forecast.shortage_units}</p>
                </div>
              </div>

              {/* Alert banner */}
              {forecast.shortage_predicted && (
                <div className="card border-l-4 border-red-500 bg-red-50 flex items-center gap-3">
                  <AlertTriangle className="text-red-500" />
                  <p className="text-red-700 font-medium">
                    Stock shortage predicted! You need {forecast.shortage_units} more units to meet the 30-day demand.
                  </p>
                </div>
              )}

              {/* Model quality */}
              <div className="card text-xs text-gray-600 space-y-1">
                <p className="font-semibold text-ink text-sm">How reliable is this forecast?</p>
                <p>
                  Method used: <b>{forecast.method === 'arima' ? `ARIMA${forecast.order ? `(${forecast.order.join(',')})` : ''}` : 'average of recent weeks'}</b>
                  {forecast.method !== 'arima' && forecast.backtest && ' - ARIMA was tested and did not beat this simple average on recent weeks, so it was not used.'}
                </p>
                {forecast.backtest ? (
                  <p>
                    Back-test on the last {forecast.backtest.horizon_weeks} weeks - average error per week:
                    ARIMA <b>{forecast.backtest.arima.mae}</b> units, recent average <b>{forecast.backtest.naive_mean.mae}</b> units, last week <b>{forecast.backtest.naive_last.mae}</b> units (lower is better).
                  </p>
                ) : (
                  <p>Too little order history for a back-test, so a simple average is used. Forecasts improve as orders accumulate.</p>
                )}
                {forecast.lower_values && (
                  <p>The shaded band is the 95% range. Plan stock for the upper end ({Math.round(forecast.upper_values.reduce((a, b) => a + b, 0))} units) if running out is costly.</p>
                )}
              </div>

              {/* Chart */}
              <div className="card">
                <h3 className="font-bold mb-4 flex items-center gap-2"><TrendingDown size={18} /> 30-Day Demand Forecast ({forecast.method === 'arima' ? 'ARIMA' : 'recent average'})</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="demandGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ea6a1f" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#ea6a1f" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    {forecast.lower_values && <Area type="monotone" dataKey="band" name="95% range" stroke="none" fill="#ea6a1f" fillOpacity={0.12} isAnimationActive={false} />}
                    <Area type="monotone" dataKey="demand" stroke="#ea6a1f" fill="url(#demandGrad)" strokeWidth={2} isAnimationActive={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
