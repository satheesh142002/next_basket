import { useEffect, useState } from 'react'
import { adminAPI } from '../../api'
import { Check, X, Store } from 'lucide-react'

export default function AdminSellers() {
  const [sellers, setSellers] = useState([])
  const [tab, setTab] = useState('pending')

  const load = async () => {
    const res = await adminAPI.sellers(tab)
    setSellers(res.data)
  }

  useEffect(() => { load() }, [tab])

  const handleApprove = async (username, approved) => {
    await adminAPI.approveSeller(username, approved)
    load()
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-semibold mb-6">Seller Management</h1>

      <div className="flex gap-2 mb-6">
        <button onClick={() => setTab('pending')} className={`btn ${tab === 'pending' ? 'btn-primary' : 'btn-secondary'}`}>Pending</button>
        <button onClick={() => setTab('approved')} className={`btn ${tab === 'approved' ? 'btn-primary' : 'btn-secondary'}`}>Approved</button>
        <button onClick={() => setTab('rejected')} className={`btn ${tab === 'rejected' ? 'btn-primary' : 'btn-secondary'}`}>Rejected</button>
      </div>

      {sellers.length === 0 ? (
        <div className="card text-center py-12"><Store size={48} className="mx-auto text-gray-300 mb-4" /><p className="text-gray-400">No sellers in this category.</p></div>
      ) : (
        <div className="space-y-4">
          {sellers.map(s => (
            <div key={s.id} className="card flex items-center justify-between">
              <div>
                <p className="font-semibold text-lg">{s.name}</p>
                <p className="text-sm text-gray-500">@{s.username} · {s.email} · {s.mobile}</p>
                {s.address && <p className="text-sm text-gray-500">{s.address}, {s.city}</p>}
                <span className={s.approval_status === 'approved' ? 'badge-green' : s.approval_status === 'rejected' ? 'badge-red' : 'badge-yellow'}>{s.approval_status === 'approved' ? 'Approved' : s.approval_status === 'rejected' ? 'Rejected' : 'Pending'}</span>
              </div>
              <div className="flex gap-2">
                {tab === 'pending' && (
                  <>
                    <button onClick={() => handleApprove(s.username, true)} className="btn-success flex items-center gap-1"><Check size={16} /> Approve</button>
                    <button onClick={() => handleApprove(s.username, false)} className="btn-danger flex items-center gap-1"><X size={16} /> Reject</button>
                  </>
                )}
                {tab === 'approved' && (
                  <button onClick={() => handleApprove(s.username, false)} className="btn-danger flex items-center gap-1"><X size={16} /> Reject</button>
                )}
                {tab === 'rejected' && (
                  <button onClick={() => handleApprove(s.username, true)} className="btn-success flex items-center gap-1"><Check size={16} /> Approve</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
