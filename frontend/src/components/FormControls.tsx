import { type ReactNode, type SelectHTMLAttributes, type InputHTMLAttributes, useState, useRef, useEffect, useCallback } from 'react'
import { cn } from '@/lib/utils'
import { Info, Check, ChevronDown } from 'lucide-react'

// --------------- Label ---------------
export function FieldLabel({ children, tooltip }: { children: ReactNode; tooltip?: string }) {
  return (
    <label className="flex items-center gap-1.5 text-[12px] font-medium uppercase tracking-wider text-text-muted mb-1.5">
      {children}
      {tooltip && (
        <span className="group relative cursor-help">
          <Info className="h-3.5 w-3.5 text-text-dim" />
          <span className="pointer-events-none absolute bottom-full left-1/2 z-50 -translate-x-1/2 mb-2 w-48 rounded-lg bg-bg-elevated px-3 py-2 text-[11px] font-normal normal-case tracking-normal text-text-muted opacity-0 shadow-xl transition-opacity group-hover:opacity-100">
            {tooltip}
          </span>
        </span>
      )}
    </label>
  )
}

// --------------- Input ---------------
interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  suffix?: string
}

export function Input({ className, suffix, ...props }: InputProps) {
  return (
    <div className="relative">
      <input
        {...props}
        className={cn(
          'w-full rounded-lg border border-border bg-bg-input px-3 py-2 text-[13px] text-text',
          'placeholder:text-text-dim',
          'focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30',
          'transition-colors duration-150',
          suffix && 'pr-12',
          className
        )}
      />
      {suffix && (
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[11px] font-medium text-text-dim">
          {suffix}
        </span>
      )}
    </div>
  )
}

// --------------- Select ---------------
interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  options: { value: string; label: string }[]
  placeholder?: string
}

export function Select({ className, options, placeholder, ...props }: SelectProps) {
  return (
    <select
      {...props}
      className={cn(
        'w-full rounded-lg border border-border bg-bg-input px-3 py-2 text-[13px] text-text',
        'focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30',
        'transition-colors duration-150 appearance-none cursor-pointer',
        'bg-[url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2212%22%20height%3D%2212%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%235c6078%22%20stroke-width%3D%222%22%3E%3Cpath%20d%3D%22m6%209%206%206%206-6%22%2F%3E%3C%2Fsvg%3E")]',
        'bg-[length:16px] bg-[right_8px_center] bg-no-repeat pr-8',
        className
      )}
    >
      {placeholder && <option value="">{placeholder}</option>}
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  )
}

// --------------- Button ---------------
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost'
  size?: 'sm' | 'md'
}

export function Button({ variant = 'primary', size = 'md', className, children, ...props }: ButtonProps) {
  return (
    <button
      {...props}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-200',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        size === 'sm' && 'px-3 py-1.5 text-[12px]',
        size === 'md' && 'px-4 py-2 text-[13px]',
        variant === 'primary' && 'bg-accent text-white hover:bg-accent-hover shadow-md shadow-accent/20 active:scale-[0.98]',
        variant === 'secondary' && 'border border-border bg-bg-elevated text-text hover:bg-bg-input hover:border-border-hover',
        variant === 'ghost' && 'text-text-muted hover:text-text hover:bg-bg-elevated',
        className
      )}
    >
      {children}
    </button>
  )
}

// --------------- Card ---------------
export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div className={cn('rounded-xl border border-border bg-bg-card p-5', className)}>
      {children}
    </div>
  )
}

// --------------- MultiSelect ---------------
interface MultiSelectProps {
  options: { value: string; label: string }[]
  selected: string[]
  onChange: (selected: string[]) => void
  placeholder?: string
  className?: string
}

export function MultiSelect({ options, selected, onChange, placeholder = 'All', className }: MultiSelectProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const handleClickOutside = useCallback((e: MouseEvent) => {
    if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
  }, [])

  useEffect(() => {
    if (open) document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open, handleClickOutside])

  const toggle = (val: string) => {
    onChange(selected.includes(val) ? selected.filter((v) => v !== val) : [...selected, val])
  }

  const allSelected = selected.length === 0
  const label = allSelected
    ? placeholder
    : selected.length <= 2
      ? selected.join(', ')
      : `${selected.length} selected`

  return (
    <div ref={ref} className={cn('relative', className)}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={cn(
          'w-full flex items-center justify-between rounded-lg border border-border bg-bg-input px-3 py-2 text-[13px] text-text',
          'hover:border-border-hover focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30',
          'transition-colors duration-150',
        )}
      >
        <span className={cn('truncate', allSelected && 'text-text-muted')}>{label}</span>
        <ChevronDown className={cn('h-3.5 w-3.5 text-text-dim shrink-0 ml-2 transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full min-w-[160px] rounded-lg border border-border bg-bg-card shadow-xl overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 border-b border-border/50">
            <button
              type="button"
              onClick={() => onChange([])}
              className="text-[11px] text-accent hover:text-accent-hover transition-colors"
            >
              All
            </button>
            {selected.length > 0 && (
              <button
                type="button"
                onClick={() => onChange([])}
                className="text-[11px] text-text-dim hover:text-text transition-colors"
              >
                Clear
              </button>
            )}
          </div>
          <div className="max-h-[240px] overflow-y-auto py-1">
            {options.map((o) => {
              const checked = selected.includes(o.value)
              return (
                <button
                  key={o.value}
                  type="button"
                  onClick={() => toggle(o.value)}
                  className={cn(
                    'flex w-full items-center gap-2.5 px-3 py-1.5 text-[13px] text-left transition-colors',
                    'hover:bg-bg-elevated/60',
                    checked && 'text-accent',
                  )}
                >
                  <span className={cn(
                    'flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors',
                    checked ? 'border-accent bg-accent' : 'border-border',
                  )}>
                    {checked && <Check className="h-3 w-3 text-white" />}
                  </span>
                  {o.label}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// --------------- AlertInfo ---------------
export function AlertInfo({ children, onClose }: { children: ReactNode; onClose?: () => void }) {
  return (
    <div className="relative rounded-lg border border-accent/20 bg-accent-muted px-4 py-3 text-[13px] text-text-muted">
      <div className="absolute left-0 top-0 bottom-0 w-[3px] rounded-l-lg bg-accent" />
      <div className="flex items-start gap-2.5 pl-2">
        <Info className="h-4 w-4 text-accent mt-0.5 shrink-0" />
        <div className="flex-1">{children}</div>
        {onClose && (
          <button onClick={onClose} className="text-text-dim hover:text-text transition-colors shrink-0">×</button>
        )}
      </div>
    </div>
  )
}
