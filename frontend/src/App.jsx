import { Route, Routes } from 'react-router-dom'
import { useEffect } from 'react'
import useStore from './contexts/store.js'

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

  return (<>
    <div className="w-full h-full flex flex-col">
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
