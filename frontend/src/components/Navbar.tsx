import { cn } from '@/lib/utils'
import { Server } from 'lucide-react'

export default function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-bg-card/80 backdrop-blur-xl">
      <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-6 px-6">
        {/* Logo */}
        <div className="flex items-center gap-3 mr-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-orange to-warning">
            <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5 text-white" stroke="currentColor" strokeWidth={2}>
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
              <polyline points="7.5 4.21 12 6.81 16.5 4.21" />
              <polyline points="7.5 19.79 7.5 14.6 3 12" />
              <polyline points="21 12 16.5 14.6 16.5 19.79" />
              <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
              <line x1="12" y1="22.08" x2="12" y2="12" />
            </svg>
          </div>
          <span className="text-[15px] font-semibold tracking-tight text-text">
            OpenSearch Sizing
          </span>
        </div>

        {/* Nav Links */}
        <nav className="flex items-center gap-1">
          <div
            className={cn(
              'flex items-center gap-2 rounded-lg px-3.5 py-2 text-[13px] font-medium',
              'bg-accent/15 text-accent shadow-sm'
            )}
          >
            <Server className="h-4 w-4" />
            AOS Sizing
          </div>
        </nav>

        <div className="flex-1" />

        {/* Right side: version badge */}
        <div className="flex items-center gap-3">
          <span className="rounded-full bg-bg-elevated px-2.5 py-0.5 text-[11px] font-medium text-text-muted">
            v2.0
          </span>
        </div>
      </div>
    </header>
  )
}
