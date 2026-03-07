import { Route, Routes } from 'react-router-dom'
import { useEffect } from 'react'
import useStore from './contexts/store.js'
import { useEffect, useRef } from "react";
import toast, { Toaster } from "react-hot-toast";
import { useSocket } from "./hooks/useSocket";

import Header from './components/layout/Header.jsx'
import Footer from './components/layout/Footer.jsx'
import Home from './pages/Home.jsx'
import PersistentLogin from './components/PersistentLogin.jsx'

function App() {

  // const setLogged = useStore((state)=>state.setLogged)

  // useEffect(()=>{
  //   const onStorage = ()=>{
  //     if (!localStorage.getItem("Logged")){
  //       setLogged(false)
  //     }
  //     else if (localStorage.getItem("Logged")==='true'){
  //       setLogged(true)
  //     }
  //   }
  //     window.addEventListener("storage", onStorage)
  //     return ()=>{window.removeEventListener("storage", onStorage)}
  // }, [setLogged]);
  // 2. Add inside App() function before the return()
const { alerts } = useSocket();
const prevCountRef = useRef(0);

useEffect(() => {
  if (alerts.length > prevCountRef.current) {
    const latest = alerts[0];
    const emoji = { HIGH: "🔴", MEDIUM: "🟡", LOW: "🔵" };

    toast(`${emoji[latest.severity] || "⚠️"} ${latest.location} — ${latest.camera_id}`, {
      duration: 6000,
      style: {
        background: "#1e293b",
        color: "#f1f5f9",
        border: "1px solid #ef4444",
        borderRadius: "12px",
        fontSize: "13px",
        fontFamily: "monospace",
      },
    });
  }
  prevCountRef.current = alerts.length;
}, [alerts]);

  return (<>
    <div className="w-full h-full flex flex-col">
      <Toaster position="top-right" />
      <Header />
      <main className="flex-1 p-4">
        <Routes>
          
          {/* Public Routes />*/}
          <Route path="/" element={<Home/>}/>

          {/* Private Routes />*/}
          <Route element={<PersistentLogin />}>
          </Route>

        </Routes>
      </main>
    </div>
    <Footer />
  </>)
}

export default App
