import { Route, Routes } from 'react-router-dom'

import Header from './components/layout/Header.jsx'
import Footer from './components/layout/Footer.jsx'
import DashboardHome from './pages/Dashboard.jsx'
import PersistentLogin from './components/PersistentLogin.jsx'
import Test from './components/common/Test.jsx'

function App() {

  return (<>
    <div className="w-full min-h-[95%] flex flex-col">
      <Header />
      <main className="flex-1 p-4">
        <Routes>
          
          {/* Public Routes />*/}
          <Route path="/" element={<DashboardHome/>}/>
          <Route path="test" element={<Test/>}/>

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