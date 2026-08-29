import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'

const navItemClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm font-medium transition-colors ${
    isActive
      ? 'bg-graphite-800 text-ink-100'
      : 'text-ink-400 hover:bg-graphite-800 hover:text-ink-100'
  }`

function NavGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 px-2.5 text-[10.5px] font-medium tracking-wider text-ink-600 uppercase">
        {label}
      </div>
      <nav className="flex flex-col gap-0.5">{children}</nav>
    </div>
  )
}

export function Sidebar() {
  return (
    <aside className="flex w-[248px] flex-none flex-col gap-7 border-r border-line bg-graphite-900 p-4">
      <div className="flex items-center gap-2.5 px-1.5">
        <div className="h-7 w-7 flex-none rounded-md bg-gradient-to-br from-amber to-ember" />
        <div>
          <div className="font-display text-[15px] font-semibold">Breakpoint</div>
          <div className="mt-0.5 text-[10px] tracking-wide text-ink-400 uppercase">
            Attack → Action
          </div>
        </div>
      </div>

      <NavGroup label="Analyse">
        <NavLink to="/" end className={navItemClass}>
          Dashboard
        </NavLink>
        <NavLink to="/engagements" className={navItemClass}>
          Engagements
        </NavLink>
        <NavLink to="/analyzer" className={navItemClass}>
          ATT&amp;CK Analyzer
        </NavLink>
        <NavLink to="/techniques" className={navItemClass}>
          Alle Techniken
        </NavLink>
      </NavGroup>

      <NavGroup label="Portfolio">
        <NavLink to="/portfolio" className={navItemClass}>
          Technologie-Mapping
        </NavLink>
      </NavGroup>

      <NavGroup label="Wissen">
        <NavLink to="/knowledge" className={navItemClass}>
          Knowledge Base
        </NavLink>
        <NavLink to="/reports" className={navItemClass}>
          Reports
        </NavLink>
      </NavGroup>

      <div className="mt-auto rounded-md border border-line-soft bg-graphite-850 p-3">
        <div className="text-[12.5px] font-semibold text-ink-100">Schritt 3 · Frontend-Anbindung</div>
        <div className="mt-1 text-[11.5px] leading-relaxed text-ink-400">
          Portfolio-Fit, Sales-Briefing und Admin-Bereich folgen in Schritt 4+.
        </div>
      </div>
    </aside>
  )
}
