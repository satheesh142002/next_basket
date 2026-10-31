import { useEffect, useState, useRef } from 'react'
import { adminAPI } from '../../api'
import {
  ResponsiveContainer, ComposedChart, LineChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from 'recharts'
import { Brain, Play, CheckCircle, AlertCircle, XCircle, RefreshCw, TrendingUp, Check } from 'lucide-react'

// Read a Server-Sent-Events POST stream and call onEvent for every `data:` frame
async function streamSSE(url, onEvent) {
  const token = localStorage.getItem('token')
  const response = await fetch(url, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, Accept: 'text/event-stream' },
  })
  if (!response.ok) throw new Error(`Server error ${response.status}: ${await response.text()}`)
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try { onEvent(JSON.parse(line.slice(6))) } catch { /* malformed frame */ }
    }
  }
}

// ── Progress bar with the current stage name ─────────────────────────────────
function ProgressBar({ pct, error, running, label }) {
  const colour = error ? 'bg-red-500' : pct >= 100 ? 'bg-green-500' : 'bg-brand-500'
  return (
    <div className="w-full mt-4" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-gray-600 font-medium">{label}</span>
        <span className="text-gray-500 tabular-nums">{pct}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-3.5 overflow-hidden">
        <div
          className={`h-3.5 rounded-full transition-all duration-500 ease-out ${colour} ${running ? 'animate-pulse' : ''}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

// ── Step list: done / active / pending ───────────────────────────────────────
function Stepper({ steps, progress, running, error, finished }) {
  const firstOpen = steps.findIndex(s => progress < s.until)
  const active = finished || firstOpen === -1 ? -1 : firstOpen
  return (
    <ol className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2 mt-4">
      {steps.map((s, i) => {
        const isDone = progress >= s.until && !(error && i === active)
        const isActive = i === active && running
        const isFail = error && (i === (firstOpen === -1 ? steps.length - 1 : firstOpen))
        return (
          <li key={s.key} className={`flex items-start gap-2 border rounded px-3 py-2 text-xs
            ${isFail ? 'border-red-300 bg-red-50' : isActive ? 'border-brand-500 bg-brand-50' : isDone ? 'border-green-200 bg-green-50' : 'border-gray-200'}`}>
            <span className={`mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full text-[10px] font-semibold
              ${isFail ? 'bg-red-500 text-white' : isDone ? 'bg-green-500 text-white' : isActive ? 'bg-brand-500 text-white' : 'bg-gray-200 text-gray-500'}`}>
              {isFail ? '!' : isDone ? <Check size={12} /> : isActive ? <RefreshCw size={11} className="animate-spin" /> : i + 1}
            </span>
            <span>
              <span className="block font-semibold text-ink">{s.label}</span>
              <span className="block text-gray-500">{s.hint}</span>
            </span>
          </li>
        )
      })}
    </ol>
  )
}

function LogLine({ time, text, error }) {
  return (
    <div className={`text-xs font-mono py-0.5 ${error ? 'text-red-500' : 'text-gray-600'}`}>
      <span className="text-gray-400 mr-2">{time}</span>{text}
    </div>
  )
}

const DT_STEPS = [
  { key: 'cats',    label: 'Fetch categories',      hint: 'Product categories become the classes',      until: 10 },
  { key: 'catalog', label: 'Load product catalogue', hint: 'Map every product to its category',          until: 20 },
  { key: 'orders',  label: 'Load order history',     hint: 'All non-cancelled orders',                   until: 35 },
  { key: 'history', label: 'Build purchase history', hint: 'Category counts per customer',               until: 55 },
  { key: 'samples', label: 'Build training samples', hint: 'Features: history + cart, label: next category', until: 70 },
  { key: 'train',   label: 'Train Decision Tree',    hint: 'Fit, test accuracy, save model',             until: 100 },
]

const ARIMA_STEPS = [
  { key: 'load',         label: '1. Collect data',     hint: 'Weekly demand history of one product',        until: 20 },
  { key: 'stationarity', label: '2. Make stationary',  hint: 'ADF test chooses the differencing order d',   until: 40 },
  { key: 'fit',          label: '3. Select and train', hint: 'Search p,q by AICc and fit the best model',   until: 60 },
  { key: 'validate',     label: '4. Back-test',        hint: 'Hold out recent weeks, compare with baselines', until: 80 },
  { key: 'forecast',     label: '5. Forecast',         hint: 'Next 30 days with a 95% interval',            until: 100 },
]

const STAGE_CAPTION = {
  history:      'Stage 1 - Data collection: weekly units sold for the selected product.',
  stationarity: 'Stage 2 - Pre-processing: the raw series (top) and the differenced series (bottom) used to pick d.',
  fit:          'Stage 3 - Select and train: the best ARIMA(p,d,q) found by AICc; dashed = fitted values.',
  validate:     'Stage 4 - Back-test: the model is trained without the last weeks and predicts them (dashed) against what really sold.',
  forecast:     'Stage 5 - Forecast: expected demand for the next 30 days with a 95% prediction band.',
}

const axis = { fontSize: 11 }
const shortDate = d => d.slice(2, 10)

function mergeSeries(parts) {
  const map = new Map()
  for (const [key, rows] of Object.entries(parts)) {
    for (const r of rows || []) {
      const row = map.get(r.date) || { date: r.date }
      row[key] = r.value
      if (r.low !== undefined) { row.low = r.low; row.band = [r.low, r.high] }
      map.set(r.date, row)
    }
  }
  return [...map.values()].sort((a, b) => a.date.localeCompare(b.date))
}

function ArimaChart({ chart }) {
  if (!chart) return null
  if (chart.kind === 'stationarity') {
    return (
      <div className="space-y-2">
        {[['history', 'Original', '#262626'], ['differenced', 'Differenced (stationary)', '#ea6a1f']].map(([k, name, c]) => (
          <ResponsiveContainer key={k} width="100%" height={150}>
            <LineChart data={chart[k].map(r => ({ date: r.date, v: r.value }))}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tickFormatter={shortDate} tick={axis} minTickGap={40} />
              <YAxis tick={axis} />
              <Tooltip />
              <Line type="linear" dataKey="v" name={name} stroke={c} dot={false} strokeWidth={1.5} isAnimationActive={false} />
              <Legend />
            </LineChart>
          </ResponsiveContainer>
        ))}
      </div>
    )
  }
  const data = mergeSeries({ history: chart.history, fitted: chart.fitted, forecast: chart.forecast, actual: chart.actual, predicted: chart.predicted })
  // Join the forecast to the last observed point so the lines connect
  if (chart.history?.length) {
    const last = data.find(r => r.date === chart.history[chart.history.length - 1].date)
    if (last && chart.forecast) last.forecast = last.history
    if (last && chart.actual) { last.actual = last.history; last.predicted = last.history }
  }
  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tickFormatter={shortDate} tick={axis} minTickGap={40} />
        <YAxis tick={axis} />
        <Tooltip />
        <Legend />
        {chart.forecast && <Area type="monotone" dataKey="band" name="95% band" stroke="none" fill="#ea6a1f" fillOpacity={0.15} isAnimationActive={false} />}
        <Line type="linear" dataKey="history" name="Actual demand" stroke="#262626" dot={false} strokeWidth={1.5} isAnimationActive={false} />
        {chart.fitted && <Line type="monotone" dataKey="fitted" name="ARIMA fit" stroke="#ea6a1f" strokeDasharray="5 3" dot={false} strokeWidth={2} isAnimationActive={false} />}
        {chart.actual && <Line type="linear" dataKey="actual" name="Held-out actual" stroke="#262626" dot={{ r: 3 }} strokeWidth={2} isAnimationActive={false} />}
        {chart.predicted && <Line type="linear" dataKey="predicted" name="Back-test prediction" stroke="#ea6a1f" strokeDasharray="5 3" dot={{ r: 3 }} strokeWidth={2} isAnimationActive={false} />}
        {chart.forecast && <Line type="monotone" dataKey="forecast" name="Forecast" stroke="#ea6a1f" dot={{ r: 3 }} strokeWidth={2} isAnimationActive={false} />}
      </ComposedChart>
    </ResponsiveContainer>
  )
}

function Bar({ value, max = 1, colour = 'bg-brand-500' }) {
  return (
    <div className="h-2.5 bg-gray-100 rounded overflow-hidden">
      <div className={`h-2.5 ${colour}`} style={{ width: `${Math.min(100, (value / max) * 100)}%` }} />
    </div>
  )
}

function RecMetrics({ m }) {
  if (!m || m.status !== 'trained') return null
  const base = m.benchmark?.find(b => b.model.startsWith('Majority'))
  const lift = base ? (m.top1 - base.top1) * 100 : null
  const active = m.per_class.filter(c => c.support > 0)
  const showTop3 = active.length > 3
  const cards = [
    ['Top-1 accuracy', `${(m.top1 * 100).toFixed(1)}%`, lift !== null ? `${lift >= 0 ? '+' : ''}${lift.toFixed(1)} pts vs baseline` : ''],
    ...(showTop3 ? [['Top-3 accuracy', `${(m.top3 * 100).toFixed(1)}%`, 'right category in top 3']] : []),
    ['Macro F1', m.macro_f1.toFixed(2), 'balanced across categories'],
    ['CV macro F1', m.cv_macro_f1.toFixed(2), 'tuning, training period'],
    ['Tree', `${m.tree_depth} deep`, `${m.tree_leaves} leaves`],
  ]
  return (
    <div className="mt-5 border border-gray-200 rounded p-4 space-y-5">
      <div>
        <h3 className="text-sm font-semibold mb-1">Model quality</h3>
        <p className="text-xs text-gray-500">
          {m.samples?.toLocaleString()} samples, {m.split}. Tested on {m.test_samples?.toLocaleString()} later orders the model never saw.
        </p>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 text-center">
        {cards.map(([k, v, sub]) => (
          <div key={k} className="border border-gray-200 rounded py-2 px-1">
            <div className="text-lg font-semibold text-ink">{v}</div>
            <div className="text-xs text-gray-600">{k}</div>
            <div className="text-[11px] text-gray-400">{sub}</div>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <h4 className="text-xs font-semibold mb-2">Benchmark (same test orders)</h4>
          <table className="w-full text-xs">
            <thead><tr className="text-left text-gray-500"><th className="font-normal">Model</th><th className="font-normal text-right">Top-1</th><th className="font-normal text-right">Macro F1</th></tr></thead>
            <tbody>
              {m.benchmark.map(b => (
                <tr key={b.model} className={b.deployed ? 'bg-brand-50 font-semibold' : ''}>
                  <td className="py-1">{b.model}{b.deployed ? ' - in use' : ''}</td>
                  <td className="text-right">{(b.top1 * 100).toFixed(1)}%</td>
                  <td className="text-right">{b.macro_f1.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-[11px] text-gray-400 mt-2">The Decision Tree is kept in production because it is explainable and nearly as accurate as the ensembles.</p>
        </div>
        <div>
          <h4 className="text-xs font-semibold mb-2">What the tree relies on</h4>
          <div className="space-y-2">
            {Object.entries(m.importance_groups || {}).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
              <div key={k}>
                <div className="flex justify-between text-xs"><span>{k}</span><span className="tabular-nums">{(v * 100).toFixed(0)}%</span></div>
                <Bar value={v} />
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <h4 className="text-xs font-semibold mb-2">Per-category performance</h4>
          {active.length < m.classes.length && <p className="text-[11px] text-gray-400 mb-2">Only {active.length} of {m.classes.length} categories have orders in the test period.</p>}
          <table className="w-full text-xs">
            <thead><tr className="text-left text-gray-500"><th className="font-normal">Category</th><th className="font-normal text-right">Precision</th><th className="font-normal text-right">Recall</th><th className="font-normal text-right">Test n</th></tr></thead>
            <tbody>
              {active.map(c => (
                <tr key={c.category}><td className="py-0.5">{c.category}</td><td className="text-right">{c.precision.toFixed(2)}</td><td className="text-right">{c.recall.toFixed(2)}</td><td className="text-right">{c.support}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <div>
          <h4 className="text-xs font-semibold mb-2">Top features and tuned settings</h4>
          <ul className="text-xs space-y-1">
            {m.top_features.slice(0, 5).map(f => <li key={f.feature} className="flex justify-between"><span>{f.feature}</span><span className="tabular-nums text-gray-500">{(f.importance * 100).toFixed(1)}%</span></li>)}
          </ul>
          <p className="text-[11px] text-gray-400 mt-2">
            Chosen by grid search: {Object.entries(m.best_params).map(([k, v]) => `${k} = ${v}`).join(', ')}
          </p>
        </div>
      </div>
    </div>
  )
}

// ── Main page ────────────────────────────────────────────────────────────────
export default function MLTraining() {
  const [status, setStatus] = useState(null)

  // Decision tree
  const [training, setTraining] = useState(false)
  const [progress, setProgress] = useState(0)
  const [stageLabel, setStageLabel] = useState('')
  const [logs, setLogs] = useState([])
  const [done, setDone] = useState(false)
  const [hasError, setHasError] = useState(false)
  const [result, setResult] = useState(null)
  const logsRef = useRef(null)

  // ARIMA
  const [aRunning, setARunning] = useState(false)
  const [aProgress, setAProgress] = useState(0)
  const [aLabel, setALabel] = useState('')
  const [aChart, setAChart] = useState(null)
  const [aInfo, setAInfo] = useState(null)
  const [aDone, setADone] = useState(false)
  const [aError, setAError] = useState(false)
  const [aLogs, setALogs] = useState([])

  const loadStatus = async () => {
    try { setStatus((await adminAPI.mlStatus()).data) } catch { /* ignore */ }
  }
  useEffect(() => { loadStatus() }, [])
  useEffect(() => { if (logsRef.current) logsRef.current.scrollTop = logsRef.current.scrollHeight }, [logs])

  const stamp = () => new Date().toLocaleTimeString()

  const handleTrain = async () => {
    setTraining(true); setProgress(0); setLogs([]); setDone(false); setHasError(false); setResult(null)
    setStageLabel('Starting…')
    setLogs([{ id: 0, time: stamp(), text: 'Starting ML training pipeline…' }])
    try {
      await streamSSE('/api/admin/ml/train', evt => {
        setProgress(evt.progress ?? 0)
        setStageLabel(evt.message)
        setLogs(prev => [...prev, { id: prev.length, time: stamp(), text: evt.message, error: evt.error }])
        if (evt.error) setHasError(true)
        if (evt.result) setResult(evt.result)
        if (evt.done) { setDone(true); setTraining(false); loadStatus() }
      })
    } catch (err) {
      setLogs(prev => [...prev, { id: prev.length, time: stamp(), text: err.message, error: true }])
      setHasError(true); setDone(true); setTraining(false)
    }
  }

  const handleArima = async () => {
    setARunning(true); setAProgress(0); setAChart(null); setAInfo(null); setADone(false); setAError(false)
    setALogs([]); setALabel('Starting…')
    try {
      await streamSSE('/api/admin/ml/arima', evt => {
        setAProgress(evt.progress ?? 0)
        setALabel(evt.message)
        setALogs(prev => [...prev, { id: prev.length, time: stamp(), text: evt.message, error: evt.error }])
        if (evt.chart) setAChart(evt.chart)
        if (evt.info) setAInfo(evt.info)
        if (evt.error) setAError(true)
        if (evt.done) { setADone(true); setARunning(false) }
      })
    } catch (err) {
      setALogs(prev => [...prev, { id: prev.length, time: stamp(), text: err.message, error: true }])
      setAError(true); setADone(true); setARunning(false)
    }
  }

  const statusBadge = status?.recommendation_model_trained ? (
    <span className="inline-flex items-center gap-1 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">
      <CheckCircle size={12} /> Model Trained
      {status.trained_at && <span className="text-green-500 font-normal">- {new Date(status.trained_at).toLocaleDateString()}</span>}
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full font-medium">
      <AlertCircle size={12} /> Not Trained
    </span>
  )

  const btnLabel = (busy, idle, icon) => busy
    ? <><RefreshCw size={16} className="animate-spin" /> Running…</>
    : <>{icon} {idle}</>

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-6">
        <Brain className="text-brand-600" size={26} />
        <h1 className="text-2xl font-semibold">Training Phase</h1>
      </div>

      {/* ── Recommendation engine ──────────────────────────────────────── */}
      <div className="card mb-6">
        <h2 className="text-lg font-semibold mb-1 text-brand-600">Recommendation Engine: Build and Train</h2>
        <p className="text-gray-500 text-sm mb-3">
          Trains a Decision Tree classifier on historical order data to predict the next category of products
          for each customer, using purchase history and cart categories as features.
        </p>
        <div className="flex items-center gap-3 mb-3">{statusBadge}</div>

        {status?.categories && (
          <div className="text-xs text-gray-500 mb-4">
            Trained on categories:&nbsp;
            {status.categories.map(c => <span key={c} className="inline-block bg-gray-100 rounded px-1.5 py-0.5 mr-1 mb-1">{c}</span>)}
          </div>
        )}

        <button onClick={handleTrain} disabled={training || aRunning} className="btn-primary flex items-center gap-2 text-sm">
          {btnLabel(training, 'Train Model', <Play size={16} />)}
        </button>

        {(training || done) && (
          <>
            <ProgressBar pct={progress} error={hasError} running={training} label={stageLabel} />
            <Stepper steps={DT_STEPS} progress={progress} running={training} error={hasError} finished={done && !hasError} />
          </>
        )}

        {logs.length > 0 && (
          <div ref={logsRef} className="mt-4 bg-gray-50 border border-gray-200 rounded p-3 max-h-48 overflow-y-auto">
            {logs.map(l => <LogLine key={l.id} time={l.time} text={l.text} error={l.error} />)}
          </div>
        )}

        <RecMetrics m={result?.status === 'trained' ? result : status?.metrics} />
        {done && !hasError && (
          <div className="mt-3 flex items-center gap-2 text-green-700 bg-green-50 border border-green-200 rounded px-3 py-2 text-sm">
            <CheckCircle size={16} /> Training completed.
          </div>
        )}
        {done && hasError && (
          <div className="mt-3 flex items-center gap-2 text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2 text-sm">
            <XCircle size={16} /> Training failed - see the log above.
          </div>
        )}
      </div>

      {/* ── ARIMA ───────────────────────────────────────────────────────── */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-1 text-brand-600">Forecaster Model: Build and Train (ARIMA)</h2>
        <p className="text-gray-500 text-sm mb-3">
          Sellers get ARIMA forecasts live from order history. Run the pipeline here to watch each stage on the
          best-selling product: the chart changes as the model moves from raw data to a 30-day forecast.
        </p>

        <button onClick={handleArima} disabled={aRunning || training} className="btn-primary flex items-center gap-2 text-sm">
          {btnLabel(aRunning, 'Run ARIMA pipeline', <TrendingUp size={16} />)}
        </button>

        {(aRunning || aDone) && (
          <>
            <ProgressBar pct={aProgress} error={aError} running={aRunning} label={aLabel} />
            <Stepper steps={ARIMA_STEPS} progress={aProgress} running={aRunning} error={aError} finished={aDone && !aError} />
          </>
        )}

        {aChart && (
          <div className="mt-5 border border-gray-200 rounded p-3">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
              <p className="text-xs text-gray-600">{STAGE_CAPTION[aChart.kind]}</p>
              {aInfo?.product_name && <span className="text-xs bg-brand-100 text-brand-800 rounded px-2 py-0.5">{aInfo.product_name}</span>}
            </div>
            <ArimaChart chart={aChart} />
            {aInfo && (
              <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-gray-500 mt-2">
                {aInfo.d !== undefined && <span>d: <b>{aInfo.d}</b></span>}
                {aInfo.adf_p_raw !== undefined && <span>ADF p (raw): <b>{aInfo.adf_p_raw}</b></span>}
                {aInfo.adf_p_diff !== undefined && <span>ADF p (differenced): <b>{aInfo.adf_p_diff}</b></span>}
                {aInfo.order && <span>Order: <b>ARIMA({aInfo.order.join(',')})</b></span>}
                {aInfo.aic !== undefined && <span>AIC: <b>{aInfo.aic}</b></span>}
                {aInfo.backtest && <span>Back-test MAE - ARIMA <b>{aInfo.backtest.arima.mae}</b> | mean <b>{aInfo.backtest.naive_mean.mae}</b> | last <b>{aInfo.backtest.naive_last.mae}</b> | used: <b>{aInfo.backtest.chosen === 'arima' ? 'ARIMA' : 'mean baseline'}</b></span>}
                {aInfo.forecast_total !== undefined && <span>30-day demand: <b>{aInfo.forecast_total}</b> / stock <b>{aInfo.current_stock}</b></span>}
              </div>
            )}
          </div>
        )}

        {aLogs.length > 0 && (
          <div className="mt-4 bg-gray-50 border border-gray-200 rounded p-3 max-h-40 overflow-y-auto">
            {aLogs.map(l => <LogLine key={l.id} time={l.time} text={l.text} error={l.error} />)}
          </div>
        )}
        {aDone && aError && (
          <div className="mt-3 flex items-center gap-2 text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2 text-sm">
            <XCircle size={16} /> Pipeline stopped - see the log above.
          </div>
        )}
      </div>
    </div>
  )
}
