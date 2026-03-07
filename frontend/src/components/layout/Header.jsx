const Header = () => {
    return (

      <header className="border-b border-slate-800 px-6 py-4 flex items-center justify-between
        bg-slate-950/80 backdrop-blur-sm sticky top-0 z-10">

        <div className="flex items-center gap-3">
          {/* Logo / brand */}
          <div className="w-8 h-8 rounded-lg bg-blue-500 flex items-center justify-center text-sm font-bold">
            🚇
          </div>
          <div>
            <h1 className="text-white font-bold text-base tracking-tight">SubGuard</h1>
            <p className="text-slate-500 text-xs">Transit Safety Dashboard</p>
          </div>
        </div>

        {/* Right side of header: current time */}
        <div className="text-slate-400 text-xs font-mono">
          {new Date().toLocaleDateString("en-CA", {
            weekday: "short", year: "numeric", month: "short", day: "numeric"
          })}
        </div>
      </header>
    )
}

export default Header;