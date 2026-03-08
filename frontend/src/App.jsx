import { Route, Routes } from 'react-router-dom'
import { useState } from 'react'
import Header from './components/layout/Header.jsx'
import Footer from './components/layout/Footer.jsx'
import DashboardHome from './pages/Dashboard.jsx'
import PersistentLogin from './components/PersistentLogin.jsx'
import Test from './components/common/Test.jsx'
import useAlertWS from './hooks/useAlertWS.js'

function App() {
  const [alert, setAlert] = useState(null)

  useAlertWS({
    onMessage: (data) => {
      // Only trigger red screen when backend sends type === "event"
      if (data?.type === 'event') {
        setAlert(data.event)
        console.log("alerted")

        // Beep using Web Audio API — no library or file needed
        try {
          const ctx = new AudioContext()
          const oscillator = ctx.createOscillator()
          const gain = ctx.createGain()
          oscillator.connect(gain)
          gain.connect(ctx.destination)
          oscillator.type = 'square'
          oscillator.frequency.setValueAtTime(880, ctx.currentTime)
          gain.gain.setValueAtTime(0.3, ctx.currentTime)
          gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.8)
          oscillator.start(ctx.currentTime)
          oscillator.stop(ctx.currentTime + 0.8)
        } catch (e) {
          console.warn('Audio failed:', e)
        }

        // Auto-dismiss after 8 seconds
        setTimeout(() => setAlert(null), 8000)
      }
    }
  })

  return (<>
    <div className="w-full min-h-[95%] flex flex-col">
      <Header />
      <main className="flex-1 p-4">
        <Routes>
          <Route path="/" element={<DashboardHome />} />
          <Route path="test" element={<Test />} />
          <Route element={<PersistentLogin />}></Route>
        </Routes>
      </main>
    </div>
    <Footer />

    {/* RED ALERT OVERLAY — renders only when type === "event" received */}
    {alert && (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm"
        style={{ animation: 'flashRed 0.5s ease-in-out 3', backgroundColor: 'rgba(220,38,38,0.85)' }}
      >
        <div className="bg-white rounded-2xl shadow-2xl p-10 max-w-md w-full mx-4 text-center border-4 border-red-600">
          <div className="text-6xl mb-4">🚨</div>
          <h1 className="text-3xl font-black text-red-600 uppercase tracking-widest mb-2">
            Alert
          </h1>
          <p className="text-xl font-bold text-gray-800 mb-1">
            Suspicious Activity Detected
          </p>
          <p className="text-gray-500 text-sm mb-1">
            {alert?.event_type || 'Unknown event'}
          </p>
          <p className="text-gray-500 text-sm mb-6">
            {alert?.name || 'Unknown location'}
          </p>
          <button
            onClick={() => setAlert(null)}
            className="bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-8 rounded-xl text-lg transition-all"
          >
            Dismiss
          </button>
        </div>

        <style>{`
          @keyframes flashRed {
            0%, 100% { background-color: rgba(220, 38, 38, 0.85); }
            50% { background-color: rgba(239, 68, 68, 0.5); }
          }
        `}</style>
      </div>
    )}
  </>)
}

export default App