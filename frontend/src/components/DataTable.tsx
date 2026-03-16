import { cn, formatPrice } from '@/lib/utils'
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'

interface Column {
  key: string
  label: string
  width?: string
  render?: (value: unknown, row: Record<string, unknown>) => React.ReactNode
}

interface DataTableProps {
  columns: Column[]
  data: Record<string, unknown>[]
  loading?: boolean
  page: number
  pageCount: number
  pageSize: number
  onPageChange: (page: number) => void
  onPageSizeChange: (size: number) => void
  onRowClick?: (row: Record<string, unknown>) => void
  emptyText?: string
}

export default function DataTable({
  columns,
  data,
  loading,
  page,
  pageCount,
  pageSize,
  onPageChange,
  onPageSizeChange,
  onRowClick,
  emptyText = 'No data',
}: DataTableProps) {
  return (
    <div className="overflow-hidden rounded-xl border border-border">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr className="bg-bg-elevated/60">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="whitespace-nowrap px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-text-muted"
                  style={col.width ? { width: col.width } : undefined}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-12 text-center text-text-dim">
                  <div className="flex items-center justify-center gap-2">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />
                    Loading...
                  </div>
                </td>
              </tr>
            ) : data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-12 text-center text-text-dim">
                  {emptyText}
                </td>
              </tr>
            ) : (
              data.map((row, i) => (
                <tr
                  key={i}
                  onClick={() => onRowClick?.(row)}
                  className={cn(
                    'border-t border-border/50 transition-colors duration-100',
                    onRowClick && 'cursor-pointer',
                    'hover:bg-bg-elevated/40'
                  )}
                >
                  {columns.map((col) => (
                    <td key={col.key} className="whitespace-nowrap px-4 py-3">
                      {col.render
                        ? col.render(row[col.key], row)
                        : renderDefaultCell(col.key, row[col.key])}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {pageCount > 0 && (
        <div className="flex items-center justify-between border-t border-border px-4 py-3 text-[12px] text-text-muted">
          <div className="flex items-center gap-2">
            <span>Rows per page</span>
            <select
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              className="rounded-md border border-border bg-bg-input px-2 py-1 text-[12px] text-text focus:outline-none"
            >
              {[10, 20, 50, 100].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1">
            <span className="mr-2">
              Page {page} of {pageCount}
            </span>
            <PagBtn onClick={() => onPageChange(1)} disabled={page <= 1}>
              <ChevronsLeft className="h-3.5 w-3.5" />
            </PagBtn>
            <PagBtn onClick={() => onPageChange(page - 1)} disabled={page <= 1}>
              <ChevronLeft className="h-3.5 w-3.5" />
            </PagBtn>
            <PagBtn onClick={() => onPageChange(page + 1)} disabled={page >= pageCount}>
              <ChevronRight className="h-3.5 w-3.5" />
            </PagBtn>
            <PagBtn onClick={() => onPageChange(pageCount)} disabled={page >= pageCount}>
              <ChevronsRight className="h-3.5 w-3.5" />
            </PagBtn>
          </div>
        </div>
      )}
    </div>
  )
}

function PagBtn({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-border text-text-muted transition-colors hover:bg-bg-elevated hover:text-text disabled:opacity-30 disabled:cursor-not-allowed"
    >
      {children}
    </button>
  )
}

function renderDefaultCell(key: string, value: unknown) {
  if (value == null) return <span className="text-text-dim">—</span>

  const s = String(value)
  const lower = key.toLowerCase()

  if (lower.includes('price') || lower.includes('cost')) {
    const n = Number(value)
    if (!isNaN(n)) {
      return <span className="font-mono font-medium text-success">${formatPrice(n)}</span>
    }
  }

  if (lower.includes('num') || lower.includes('count') || lower.includes('node')) {
    const n = Number(value)
    if (!isNaN(n)) {
      return <span className="font-mono">{n}</span>
    }
  }

  if (lower.includes('type') || lower.includes('instance')) {
    return (
      <span className="inline-flex rounded-md bg-bg-elevated px-2 py-0.5 font-mono text-[12px] text-accent">
        {s}
      </span>
    )
  }

  return <span>{s}</span>
}
