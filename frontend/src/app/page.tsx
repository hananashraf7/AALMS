"use client";
import { useEffect, useState, useRef, useCallback } from "react";
import Webcam from "react-webcam";

export default function Home() {
  const [attendances, setAttendances] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const webcamRef = useRef<Webcam>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isActive, setIsActive] = useState(false);
  const [lastDetection, setLastDetection] = useState<string | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const [leaveForm, setLeaveForm] = useState({ student_id: '', leave_date: '', reason: '', semester: 1 });
  const [leaveMessage, setLeaveMessage] = useState({ text: '', error: false });

  const fetchAttendances = async () => {
    try { const r = await fetch('http://localhost:8000/attendance/today'); setAttendances(await r.json()); }
    catch {} finally { setIsLoading(false); }
  };

  useEffect(() => {
    fetchAttendances();
    const poll = setInterval(fetchAttendances, 5000);
    return () => clearInterval(poll);
  }, []);

  const captureAndProcess = useCallback(async () => {
    if (isProcessing) return;
    const imageSrc = webcamRef.current?.getScreenshot();
    if (!imageSrc) return;
    setIsProcessing(true);
    try {
      const res = await fetch('http://localhost:8000/attendance/process_frame', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_base64: imageSrc })
      });
      const data = await res.json();
      const video = webcamRef.current?.video;
      const canvas = canvasRef.current;
      if (video && canvas && data.results) {
        canvas.width = video.videoWidth; canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          let someoneMarked = false;
          data.results.forEach((face: any) => {
            const [top, right, bottom, left] = face.location;
            const isKnown = !face.is_unknown;
            // Thin clean bounding box
            ctx.strokeStyle = isKnown ? '#1a1a1a' : '#ccc';
            ctx.lineWidth = 2;
            ctx.strokeRect(left, top, right - left, bottom - top);
            // Label background
            const label = isKnown ? `${face.person_id}  ${(face.confidence*100).toFixed(0)}%` : 'Unknown';
            ctx.font = 'bold 11px Inter, sans-serif';
            const labelW = ctx.measureText(label).width + 14;
            ctx.fillStyle = isKnown ? '#1a1a1a' : '#e0e0e0';
            ctx.beginPath(); ctx.roundRect(left, top - 26, labelW, 22, 6); ctx.fill();
            ctx.fillStyle = isKnown ? '#fff' : '#666';
            ctx.fillText(label, left + 7, top - 10);
            if (face.marked_just_now) { someoneMarked = true; setLastDetection(face.person_id); }
          });
          if (someoneMarked) fetchAttendances();
        }
      }
    } catch {} finally { setIsProcessing(false); }
  }, [isProcessing]);

  useEffect(() => {
    if (isActive) { intervalRef.current = setInterval(captureAndProcess, 1200); }
    else { if (intervalRef.current) clearInterval(intervalRef.current); const c = canvasRef.current; if (c) c.getContext('2d')?.clearRect(0, 0, c.width, c.height); }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [isActive, captureAndProcess]);

  const handleLeaveSubmit = async (e: any) => {
    e.preventDefault();
    try {
      const r = await fetch('http://localhost:8000/leaves/apply/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(leaveForm) });
      const d = await r.json();
      if (r.ok) { setLeaveMessage({ text: 'Leave submitted for admin approval.', error: false }); setLeaveForm({ student_id: '', leave_date: '', reason: '', semester: 1 }); }
      else { setLeaveMessage({ text: d.detail || 'Failed', error: true }); }
    } catch { setLeaveMessage({ text: 'Network error.', error: true }); }
    setTimeout(() => setLeaveMessage({ text: '', error: false }), 6000);
  };

  return (
    <div className="space-y-10">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-[#1a1a1a]">Live Kiosk</h1>
          <p className="mt-1 text-gray-400 text-sm">Facial Recognition · Auto Check-in</p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-gray-200 shadow-sm">
          <span className={`w-2 h-2 rounded-full ${isActive ? 'bg-green-500' : 'bg-gray-300'}`} />
          <span className="text-xs font-semibold text-gray-500">{isActive ? 'Scanning' : 'Standby'}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 items-start">
        {/* Left: Camera + Leave */}
        <div className="lg:col-span-3 space-y-6">
          {/* Camera */}
          <div className="card-panel overflow-hidden">
            <div className="relative" style={{ aspectRatio: '4/3', maxHeight: '340px' }}>
              <Webcam ref={webcamRef} audio={false} screenshotFormat="image/jpeg" videoConstraints={{ facingMode: "user" }}
                className="w-full h-full object-cover" />
              <canvas ref={canvasRef} className="absolute top-0 left-0 w-full h-full object-cover z-10" />
              {/* Paused overlay */}
              {!isActive && (
                <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-white/70 backdrop-blur-sm">
                  <div className="w-14 h-14 rounded-full bg-[#1a1a1a] flex items-center justify-center mb-3 shadow-lg">
                    <svg className="w-5 h-5 text-white ml-0.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                  </div>
                  <p className="text-sm text-gray-400 font-medium">Press Start to begin scanning</p>
                </div>
              )}
              {/* Toast */}
              {isActive && lastDetection && (
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-30 bg-[#1a1a1a] text-white px-5 py-2 rounded-full text-xs font-bold tracking-wide shadow-lg">
                  ✓ {lastDetection} checked in
                </div>
              )}
            </div>
            {/* Start/Stop */}
            <div className="p-4 border-t border-gray-100">
              <button onClick={() => { setIsActive(v => !v); setLastDetection(null); }}
                className={`w-full py-3 rounded-xl font-bold text-xs uppercase tracking-widest transition-all ${isActive ? 'btn-ghost' : 'btn-primary'}`}>
                {isActive ? '■  Stop Detection' : '▶  Start Detection'}
              </button>
            </div>
          </div>

          {/* Leave Form */}
          <div className="card-panel p-7 space-y-5">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-lg font-bold text-[#1a1a1a]">Apply for Leave</h2>
                <p className="text-xs text-gray-400 mt-0.5">Admin approval required · Max 15 per semester</p>
              </div>
              <span className="badge badge-default">15 max</span>
            </div>
            <form onSubmit={handleLeaveSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[11px] font-semibold mb-1.5 text-gray-500">Student ID</label>
                  <input type="text" className="w-full p-3 rounded-xl form-input" placeholder="e.g. 231013" value={leaveForm.student_id} onChange={e => setLeaveForm({...leaveForm, student_id: e.target.value})} required />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold mb-1.5 text-gray-500">Semester</label>
                  <input type="number" min="1" max="8" className="w-full p-3 rounded-xl form-input" value={leaveForm.semester} onChange={e => setLeaveForm({...leaveForm, semester: parseInt(e.target.value)})} required />
                </div>
              </div>
              <div>
                <label className="block text-[11px] font-semibold mb-1.5 text-gray-500">Leave Date</label>
                <input type="date" className="w-full p-3 rounded-xl form-input" value={leaveForm.leave_date} onChange={e => setLeaveForm({...leaveForm, leave_date: e.target.value})} required />
              </div>
              <div>
                <label className="block text-[11px] font-semibold mb-1.5 text-gray-500">Reason</label>
                <textarea className="w-full p-3 rounded-xl form-input h-20 resize-none" placeholder="Describe the reason for leave..." value={leaveForm.reason} onChange={e => setLeaveForm({...leaveForm, reason: e.target.value})} required />
              </div>
              <button type="submit" className="w-full btn-primary py-3 rounded-xl">Submit for Approval</button>
              {leaveMessage.text && (
                <div className={`p-3 rounded-xl text-xs text-center font-medium ${leaveMessage.error ? 'bg-red-50 text-red-500 border border-red-100' : 'bg-green-50 text-green-600 border border-green-100'}`}>
                  {leaveMessage.text}
                </div>
              )}
            </form>
          </div>
        </div>

        {/* Right: Today's Check-ins */}
        <div className="lg:col-span-2 card-panel p-5 flex flex-col" style={{ maxHeight: 'calc(100vh - 8rem)', position: 'sticky', top: '5rem' }}>
          <div className="flex items-center justify-between mb-5 pb-3 border-b border-gray-100">
            <h3 className="text-sm font-bold text-[#1a1a1a]">Today's Check-ins</h3>
            <span className="text-xs font-medium text-gray-400">{attendances.length}</span>
          </div>
          <div className="flex-1 overflow-y-auto space-y-2 custom-scrollbar pr-1">
            {isLoading ? (
              <div className="space-y-3">{[1,2,3].map(i=><div key={i} className="h-14 bg-gray-100 rounded-xl animate-pulse"/>)}</div>
            ) : attendances.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-40 text-center">
                <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center mb-2">
                  <svg className="w-5 h-5 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0"/></svg>
                </div>
                <p className="text-xs text-gray-400">No check-ins yet today</p>
              </div>
            ) : (
              attendances.map((a: any, i) => (
                <div key={i} className="flex items-center justify-between p-3.5 bg-gray-50 rounded-2xl hover:bg-gray-100 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-[#1a1a1a] flex items-center justify-center text-xs font-bold text-white">
                      {a.student_id?.charAt(0)}
                    </div>
                    <div>
                      <p className="font-semibold text-sm text-[#1a1a1a]">{a.student_id}</p>
                      <p className="text-[10px] text-gray-400 mt-0.5">{new Date(a.check_in).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                    </div>
                  </div>
                  <span className="w-2 h-2 rounded-full bg-green-400" />
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
