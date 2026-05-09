"use client";
import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Webcam from "react-webcam";

type TabType = 'register' | 'overview' | 'calendar' | 'attendance_db' | 'leave_db' | 'settings';

export default function AdminDashboard() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabType>('register');
  const webcamRef = useRef<Webcam>(null);
  const [adminName, setAdminName] = useState("Admin");

  const [regForm, setRegForm] = useState({ student_id: '', name: '', department: '' });
  const [regStatus, setRegStatus] = useState({ message: '', error: false });
  const [isRegistering, setIsRegistering] = useState(false);

  const [settingsForm, setSettingsForm] = useState({ new_username: '', new_password: '', name: '' });
  const [settingsStatus, setSettingsStatus] = useState({ message: '', error: false });

  const [overview, setOverview] = useState<any[]>([]);
  const [calendarData, setCalendarData] = useState<{ calendar: Record<string, any[]>; total_students: number } | null>(null);
  const [allAttendance, setAllAttendance] = useState<any[]>([]);
  const [allLeaves, setAllLeaves] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [resetConfirm, setResetConfirm] = useState(false);
  const [resetMsg, setResetMsg] = useState('');
  const [debugInfo, setDebugInfo] = useState<any>(null);

  useEffect(() => {
    const auth = localStorage.getItem("adminAuth");
    if (!auth) { router.push("/admin"); return; }
    setAdminName(localStorage.getItem("adminName") || "Admin");
    if (activeTab === 'overview') fetchOverview();
    if (activeTab === 'calendar') fetchCalendar();
    if (activeTab === 'attendance_db') fetchAllAttendance();
    if (activeTab === 'leave_db') fetchLeaves();
  }, [router, activeTab]);

  const fetchOverview = async () => { setIsLoading(true); try { const r = await fetch('http://localhost:8000/attendance/overview'); setOverview(await r.json()); } catch {} finally { setIsLoading(false); } };
  const fetchCalendar = async () => { setIsLoading(true); try { const r = await fetch('http://localhost:8000/attendance/calendar'); setCalendarData(await r.json()); } catch {} finally { setIsLoading(false); } };
  const fetchAllAttendance = async () => { setIsLoading(true); try { const r = await fetch('http://localhost:8000/attendance/all'); setAllAttendance(await r.json()); } catch {} finally { setIsLoading(false); } };
  const fetchLeaves = async () => { setIsLoading(true); try { const r = await fetch('http://localhost:8000/leaves/all'); setAllLeaves(await r.json()); } catch {} finally { setIsLoading(false); } };
  const fetchDebug = async () => { try { const r = await fetch('http://localhost:8000/attendance/debug'); setDebugInfo(await r.json()); } catch {} };

  const handleCaptureAndRegister = async () => {
    if (!regForm.student_id || !regForm.name || !regForm.department) { setRegStatus({ message: 'Please fill all fields', error: true }); return; }
    const imageSrc = webcamRef.current?.getScreenshot();
    if (!imageSrc) { setRegStatus({ message: 'Could not capture from webcam', error: true }); return; }
    setIsRegistering(true);
    setRegStatus({ message: 'Detecting face...', error: false });
    try {
      const r = await fetch('http://localhost:8000/students/register_with_face', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...regForm, image_base64: imageSrc }) });
      const d = await r.json();
      if (r.ok) { await fetch('http://localhost:8000/cache/reload'); setRegStatus({ message: `✓ ${d.message} (${d.total_known_faces} faces in system)`, error: false }); setRegForm({ student_id: '', name: '', department: '' }); }
      else { setRegStatus({ message: d.detail || 'Failed', error: true }); }
    } catch { setRegStatus({ message: 'Network error', error: true }); } finally { setIsRegistering(false); }
  };

  const handleSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const r = await fetch('http://localhost:8000/admin/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ current_username: localStorage.getItem("adminAuth"), ...settingsForm }) });
      const d = await r.json();
      if (r.ok) { setSettingsStatus({ message: 'Settings saved', error: false }); localStorage.setItem("adminAuth", d.username); localStorage.setItem("adminName", d.name); setAdminName(d.name); }
      else { setSettingsStatus({ message: d.detail || 'Failed', error: true }); }
    } catch { setSettingsStatus({ message: 'Network error', error: true }); }
  };

  const handleLeaveAction = async (id: number, action: 'approve' | 'reject') => {
    const r = await fetch(`http://localhost:8000/leaves/${id}/${action}`, { method: 'POST' });
    if (r.ok) fetchLeaves(); else { const d = await r.json(); alert(d.detail || 'Failed'); }
  };

  const handleResetToday = async () => {
    const r = await fetch('http://localhost:8000/attendance/reset-today', { method: 'DELETE' });
    const d = await r.json(); setResetMsg(d.message); setResetConfirm(false);
    setTimeout(() => setResetMsg(''), 5000);
  };

  const logout = () => { localStorage.removeItem("adminAuth"); localStorage.removeItem("adminName"); router.push("/admin"); };

  const tabs: { id: TabType; label: string }[] = [
    { id: 'register', label: 'Registration' },
    { id: 'overview', label: 'Shortage Overview' },
    { id: 'calendar', label: 'Calendar' },
    { id: 'attendance_db', label: 'Attendance DB' },
    { id: 'leave_db', label: 'Leave Requests' },
    { id: 'settings', label: 'Settings' },
  ];

  return (
    <div className="space-y-8 pb-12">
      {/* Header */}
      <header className="flex justify-between items-end pb-6 border-b border-gray-200">
        <div>
          <p className="text-xs font-medium text-gray-400 tracking-wide">Welcome back,</p>
          <h1 className="text-3xl font-bold tracking-tight text-[#1a1a1a]">{adminName}</h1>
        </div>
        <button onClick={logout} className="btn-ghost px-5 py-2.5 rounded-xl text-xs uppercase tracking-widest">Logout</button>
      </header>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1.5 bg-gray-100 p-1.5 rounded-2xl w-fit">
        {tabs.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            className={`tab-item ${activeTab === t.id ? 'tab-active' : ''}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* REGISTRATION */}
      {activeTab === 'register' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="card-panel p-7 space-y-5">
            <h2 className="text-lg font-bold text-[#1a1a1a]">New Student Entry</h2>
            {[
              { label: 'Roll No / Student ID', key: 'student_id', placeholder: 'e.g. 231013' },
              { label: 'Full Name', key: 'name', placeholder: 'e.g. Hanan Ashraf' },
              { label: 'Department', key: 'department', placeholder: 'e.g. Computer Science' },
            ].map(f => (
              <div key={f.key}>
                <label className="block text-[11px] font-semibold mb-1.5 text-gray-500">{f.label}</label>
                <input type="text" className="w-full p-3.5 rounded-xl form-input" placeholder={f.placeholder}
                  value={(regForm as any)[f.key]} onChange={e => setRegForm({ ...regForm, [f.key]: e.target.value })} />
              </div>
            ))}
            {regStatus.message && (
              <div className={`p-3 rounded-xl text-xs font-medium ${regStatus.error ? 'bg-red-50 text-red-500 border border-red-100' : 'bg-green-50 text-green-600 border border-green-100'}`}>
                {regStatus.message}
              </div>
            )}
            <button onClick={handleCaptureAndRegister} disabled={isRegistering}
              className="w-full btn-primary py-3.5 rounded-xl">
              {isRegistering ? 'Processing...' : 'Capture & Register'}
            </button>
          </div>

          <div className="space-y-4 flex flex-col items-center">
            <div className="card-panel overflow-hidden w-full max-w-sm aspect-square relative">
              <div className="absolute top-3 left-3 z-10 flex items-center gap-1.5 bg-white/80 backdrop-blur-sm px-2.5 py-1 rounded-lg shadow-sm text-[10px] font-semibold text-gray-600">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500" /> LIVE
              </div>
              <Webcam ref={webcamRef} audio={false} screenshotFormat="image/jpeg" videoConstraints={{ facingMode: "user" }} className="w-full h-full object-cover" />
            </div>
            <button onClick={fetchDebug} className="text-xs text-gray-400 hover:text-[#1a1a1a] transition-colors font-medium">
              Check Face Database →
            </button>
            {debugInfo && (
              <div className="card-panel p-4 text-xs w-full max-w-sm space-y-1">
                <p className="text-gray-500">Embeddings: <span className="text-[#1a1a1a] font-bold">{debugInfo.stored_embeddings}</span></p>
                <p className="text-gray-500">Cached: <span className="text-[#1a1a1a] font-bold">{debugInfo.cached_faces}</span></p>
                <p className="text-gray-500">IDs: <span className="text-[#1a1a1a] font-bold">{debugInfo.cached_ids?.join(', ') || 'None'}</span></p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* SHORTAGE OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="card-panel p-7">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-bold">Attendance Shortage Overview</h2>
            <div className="flex items-center gap-4 text-xs text-gray-400">
              <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-green-400 inline-block" /> ≥ 75%</span>
              <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-orange-400 inline-block" /> &lt; 75%</span>
            </div>
          </div>
          {isLoading ? <p className="text-gray-400 text-center py-10 animate-pulse text-sm">Calculating...</p> :
            overview.length === 0 ? <p className="text-gray-400 text-center py-10 text-sm">No students registered.</p> : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-gray-100 text-gray-400 text-[10px] uppercase tracking-widest">
                      {['Student ID', 'Name', 'Days Present', 'Leaves', 'Attendance %', 'Status'].map(h => <th key={h} className="p-3.5 font-semibold">{h}</th>)}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {overview.map((s, i) => (
                      <tr key={i} className={`hover:bg-gray-50 transition-colors ${s.has_shortage ? 'bg-orange-50/50' : ''}`}>
                        <td className="p-3.5 font-bold text-sm">{s.student_id}</td>
                        <td className="p-3.5 text-gray-600 text-sm">{s.name}</td>
                        <td className="p-3.5 text-gray-500 text-sm text-center">{s.days_present}/{s.total_working_days}</td>
                        <td className="p-3.5 text-sm text-center"><span className={s.leaves_taken >= 15 ? 'text-red-500 font-bold' : 'text-gray-500'}>{s.leaves_taken}/15</span></td>
                        <td className="p-3.5 text-center">
                          <span className={`font-bold text-lg ${s.has_shortage ? 'text-orange-500' : 'text-green-500'}`}>{s.attendance_percentage}%</span>
                        </td>
                        <td className="p-3.5">
                          <span className={`badge ${s.has_shortage ? 'badge-warning' : 'badge-default'}`}>{s.has_shortage ? 'Shortage' : 'Clear'}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
        </div>
      )}

      {/* CALENDAR */}
      {activeTab === 'calendar' && (
        <div className="space-y-6">
          {/* Reset */}
          <div className="card-panel p-5 flex items-center justify-between">
            <div>
              <p className="font-semibold text-sm text-[#1a1a1a]">Reset Today's Attendance</p>
              <p className="text-gray-400 text-xs mt-0.5">Wipes all check-in records for today.</p>
            </div>
            <div className="flex items-center gap-3">
              {resetMsg && <p className="text-green-600 text-xs font-medium">{resetMsg}</p>}
              {!resetConfirm ? (
                <button onClick={() => setResetConfirm(true)} className="btn-ghost px-4 py-2 rounded-xl text-xs uppercase tracking-widest">Reset Today</button>
              ) : (
                <div className="flex gap-2">
                  <button onClick={handleResetToday} className="btn-primary px-4 py-2 rounded-xl">Confirm</button>
                  <button onClick={() => setResetConfirm(false)} className="btn-ghost px-4 py-2 rounded-xl">Cancel</button>
                </div>
              )}
            </div>
          </div>

          <div className="card-panel p-7">
            <h2 className="text-lg font-bold mb-6 text-[#1a1a1a]">Attendance by Date</h2>
            {isLoading ? <p className="text-gray-400 text-center py-10 animate-pulse text-sm">Loading calendar...</p> :
              !calendarData || Object.keys(calendarData.calendar).length === 0 ?
                <p className="text-gray-400 text-center py-10 text-sm">No attendance records found.</p> : (
                <div className="space-y-3">
                  {Object.entries(calendarData.calendar).sort(([a], [b]) => b.localeCompare(a)).map(([day, records]) => {
                    const dateObj = new Date(day + 'T00:00:00');
                    const isOpen = selectedDay === day;
                    const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'short' });
                    const dateStr = dateObj.toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric' });
                    const pct = calendarData.total_students > 0 ? Math.round((records.length / calendarData.total_students) * 100) : 0;
                    return (
                      <div key={day} className="border border-gray-100 rounded-2xl overflow-hidden">
                        <button onClick={() => setSelectedDay(isOpen ? null : day)}
                          className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors text-left">
                          <div className="flex items-center gap-4">
                            <div className="w-11 h-11 rounded-xl bg-gray-100 flex flex-col items-center justify-center">
                              <p className="text-lg font-bold leading-none text-[#1a1a1a]">{dateObj.getDate()}</p>
                              <p className="text-[9px] text-gray-400 font-semibold uppercase">{dayName}</p>
                            </div>
                            <div>
                              <p className="font-semibold text-sm text-[#1a1a1a]">{dateStr}</p>
                              <p className="text-gray-400 text-xs">{records.length} of {calendarData.total_students} students</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-4">
                            <div className="text-right">
                              <p className={`font-bold ${pct >= 75 ? 'text-green-500' : 'text-orange-500'}`}>{pct}%</p>
                              <div className="w-20 h-1.5 bg-gray-100 rounded-full mt-1">
                                <div className={`h-1.5 rounded-full transition-all ${pct >= 75 ? 'bg-green-400' : 'bg-orange-400'}`} style={{ width: `${pct}%` }} />
                              </div>
                            </div>
                            <svg className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                          </div>
                        </button>
                        {isOpen && (
                          <div className="border-t border-gray-100 px-4 py-4 bg-gray-50/50">
                            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2.5">
                              {records.map((r, i) => (
                                <div key={i} className="bg-white rounded-xl p-3 flex items-center gap-2.5 border border-gray-100">
                                  <div className="w-7 h-7 rounded-full bg-[#1a1a1a] flex items-center justify-center text-[10px] font-bold text-white flex-shrink-0">{r.student_id?.charAt(0)}</div>
                                  <div>
                                    <p className="font-semibold text-xs text-[#1a1a1a]">{r.student_id}</p>
                                    <p className="text-[10px] text-gray-400">{r.check_in}</p>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
          </div>
        </div>
      )}

      {/* RAW ATTENDANCE DATABASE */}
      {activeTab === 'attendance_db' && (
        <div className="space-y-6">
          {/* Daily Reset */}
          <div className="card-panel p-5 flex items-center justify-between">
            <div>
              <p className="font-semibold text-sm text-[#1a1a1a]">Reset Today's Attendance</p>
              <p className="text-gray-400 text-xs mt-0.5">Clears all check-in records captured today for re-scanning.</p>
            </div>
            <div className="flex items-center gap-3">
              {resetMsg && <p className="text-green-600 text-xs font-medium">{resetMsg}</p>}
              {!resetConfirm ? (
                <button onClick={() => setResetConfirm(true)} className="btn-ghost px-4 py-2 rounded-xl text-xs uppercase tracking-widest">Reset Today</button>
              ) : (
                <div className="flex gap-2">
                  <button onClick={async () => { await handleResetToday(); fetchAllAttendance(); }} className="btn-primary px-4 py-2 rounded-xl">Confirm</button>
                  <button onClick={() => setResetConfirm(false)} className="btn-ghost px-4 py-2 rounded-xl">Cancel</button>
                </div>
              )}
            </div>
          </div>

          {/* Attendance Table */}
          <div className="card-panel p-7">
            <h2 className="text-lg font-bold mb-6 text-[#1a1a1a]">Attendance Database</h2>
            <div className="overflow-x-auto max-h-[600px] overflow-y-auto custom-scrollbar">
              {isLoading ? <p className="text-gray-400 text-center py-10 animate-pulse text-sm">Loading...</p> :
                allAttendance.length === 0 ? <p className="text-gray-400 text-center py-10 text-sm">No attendance records found.</p> : (
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-gray-100 text-gray-400 text-[10px] uppercase tracking-widest sticky top-0 bg-white">
                        {['Student ID', 'Date', 'Day', 'Check-in', 'Confidence', 'Status'].map(h => <th key={h} className="p-3.5 font-semibold">{h}</th>)}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {allAttendance.map((a, i) => {
                        const dateObj = new Date(a.date + 'T00:00:00');
                        const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'short' });
                        return (
                          <tr key={i} className="hover:bg-gray-50 transition-colors">
                            <td className="p-3.5 font-bold text-sm">{a.student_id}</td>
                            <td className="p-3.5 text-gray-600 text-sm">{a.date}</td>
                            <td className="p-3.5 text-gray-400 text-sm">{dayName}</td>
                            <td className="p-3.5 text-gray-500 text-sm">{new Date(a.check_in).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</td>
                            <td className="p-3.5 text-gray-500 text-sm">{a.confidence ? `${(a.confidence * 100).toFixed(1)}%` : '—'}</td>
                            <td className="p-3.5"><span className="badge badge-default">{a.status}</span></td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                )}
            </div>
          </div>
        </div>
      )}

      {/* LEAVE REQUESTS */}
      {activeTab === 'leave_db' && (
        <div className="card-panel p-7">
          <h2 className="text-lg font-bold mb-6 text-[#1a1a1a]">Leave Requests</h2>
          <div className="overflow-x-auto max-h-[600px] overflow-y-auto custom-scrollbar">
            {isLoading ? <p className="text-gray-400 text-center py-10 animate-pulse text-sm">Loading...</p> :
              allLeaves.length === 0 ? <p className="text-gray-400 text-center py-10 text-sm">No leave requests.</p> : (
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-gray-100 text-gray-400 text-[10px] uppercase tracking-widest sticky top-0 bg-white">
                      {['Student ID', 'Date', 'Sem', 'Reason', 'Status', 'Actions'].map(h => <th key={h} className="p-3.5 font-semibold">{h}</th>)}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {allLeaves.map((l, i) => (
                      <tr key={i} className="hover:bg-gray-50 transition-colors">
                        <td className="p-3.5 font-bold text-sm">{l.student_id}</td>
                        <td className="p-3.5 text-gray-600 text-sm">{l.leave_date}</td>
                        <td className="p-3.5 text-gray-500 text-sm text-center">{l.semester}</td>
                        <td className="p-3.5 text-sm text-gray-500 max-w-[200px] truncate" title={l.reason}>{l.reason}</td>
                        <td className="p-3.5">
                          <span className={`badge ${l.status === 'pending' ? 'bg-yellow-50 text-yellow-600 border border-yellow-100' : l.status === 'approved' ? 'badge-active' : 'bg-red-50 text-red-500 border border-red-100'}`}>
                            {l.status}
                          </span>
                        </td>
                        <td className="p-3.5">
                          {l.status === 'pending' && (
                            <div className="flex gap-2">
                              <button onClick={() => handleLeaveAction(l.id, 'approve')} className="btn-primary px-3 py-1.5 rounded-lg text-[10px]">Approve</button>
                              <button onClick={() => handleLeaveAction(l.id, 'reject')} className="btn-ghost px-3 py-1.5 rounded-lg text-[10px]">Reject</button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
          </div>
        </div>
      )}

      {/* SETTINGS */}
      {activeTab === 'settings' && (
        <div className="card-panel p-7 max-w-lg mx-auto">
          <h2 className="text-lg font-bold mb-6 text-[#1a1a1a]">Admin Settings</h2>
          <form onSubmit={handleSettings} className="space-y-4">
            {[
              { label: 'Display Name', key: 'name', type: 'text', placeholder: 'Your name' },
              { label: 'New Username', key: 'new_username', type: 'text', placeholder: 'New username' },
              { label: 'New Password', key: 'new_password', type: 'password', placeholder: '••••••••' },
            ].map(f => (
              <div key={f.key}>
                <label className="block text-[11px] font-semibold mb-1.5 text-gray-500">{f.label}</label>
                <input type={f.type} className="w-full p-3.5 rounded-xl form-input" placeholder={f.placeholder} required
                  value={(settingsForm as any)[f.key]} onChange={e => setSettingsForm({ ...settingsForm, [f.key]: e.target.value })} />
              </div>
            ))}
            {settingsStatus.message && (
              <div className={`p-3 rounded-xl text-xs font-medium ${settingsStatus.error ? 'bg-red-50 text-red-500 border border-red-100' : 'bg-green-50 text-green-600 border border-green-100'}`}>
                {settingsStatus.message}
              </div>
            )}
            <button type="submit" className="w-full btn-primary py-3.5 rounded-xl">Save Changes</button>
          </form>
        </div>
      )}
    </div>
  );
}
