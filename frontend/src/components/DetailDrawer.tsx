import { useState, useEffect } from 'react'
import { X, Loader2 } from 'lucide-react'
import { formatPrice } from '@/lib/utils'
import { api } from '@/lib/api'
import type { SizingParams } from '@/lib/api'

type Row = Record<string, unknown>

interface DetailDrawerProps {
  row: Row | null
  sizingParams: SizingParams | null
  onClose: () => void
}

// --------------- helpers ---------------

function num(v: unknown): number {
  return Number(v ?? 0)
}

function str(v: unknown): string {
  return String(v ?? '')
}

function pct(saved: number, total: number): string {
  if (total <= 0) return '0'
  return Math.round((saved / total) * 100).toString()
}

// --------------- component ---------------

export default function DetailDrawer({ row, sizingParams, onClose }: DetailDrawerProps) {
  const [ec2, setEc2] = useState<Row | null>(null)
  const [ec2Loading, setEc2Loading] = useState(false)

  useEffect(() => {
    if (!row || !sizingParams) { setEc2(null); return }

    const instanceType = str(row.INSTANCE_TYPE)
    if (!instanceType) return

    let cancelled = false
    setEc2Loading(true)
    setEc2(null)

    api.ec2Sizing({ ...sizingParams, reqEC2Instance: instanceType })
      .then((res) => {
        if (!cancelled) setEc2(res.result.list[0] ?? null)
      })
      .catch((e) => { if (!cancelled) console.error('EC2 sizing failed:', e) })
      .finally(() => { if (!cancelled) setEc2Loading(false) })

    return () => { cancelled = true }
  }, [row, sizingParams])

  if (!row) return null

  const aosCost = num(row.TOTAL_PRICE_MONTH)
  const ec2Cost = ec2 ? num(ec2.TOTAL_PRICE_MONTH) : 0
  const saved = ec2Cost > 0 ? ec2Cost - aosCost : 0
  const savePct = ec2Cost > 0 ? pct(saved, ec2Cost) : '—'

  const aosRows: [string, string | number, string | number, string | number][] = []

  const masterType = str(row.DEDICATED_MASTER_TYPE)
  if (masterType) {
    aosRows.push([masterType, num(row.MASTER_NUM), formatPrice(num(row.MASTER_PRICE_MONTH)), num(row.MASTER_Upfront)])
  }

  const hotType = str(row.INSTANCE_TYPE)
  if (hotType) {
    aosRows.push([hotType, num(row.HOT_NUM), formatPrice(num(row.HOT_PRICE_MONTH)), num(row.Upfront)])
  }

  const warmType = str(row.WARM_INSTANCE_TYPE)
  if (warmType) {
    aosRows.push([warmType, num(row.WARM_NUM), formatPrice(num(row.WARM_PRICE_MONTH)), ''])
  }

  const warmStorage = num(row.WARM_REQUIRED_STORAGE_TOTAL)
  if (warmStorage > 0) {
    aosRows.push(['Managed Storage (Warm)', `${warmStorage} GB`, formatPrice(num(row.WARM_STORAGE_PRICE_MONTH)), ''])
  }

  const coldStorage = num(row.COLD_REQUIRED_STORAGE)
  if (coldStorage > 0) {
    aosRows.push(['Managed Storage (Cold)', `${coldStorage} GB`, formatPrice(num(row.COLD_STORAGE_PRICE_MONTH)), ''])
  }

  const ebsTotal = num(row.HOT_REQUIRED_EBS_TOTAL)
  if (ebsTotal > 0) {
    aosRows.push(['EBS (GP3)', `${ebsTotal} GB`, formatPrice(num(row.HOT_STORAGE_PRICE_MONTH)), ''])
  }

  const hotS3Storage = num(row.HOT_S3_STORAGE)
  const hotS3Cost = num(row.HOT_S3_STORAGE_PRICE_MONTH)
  if (hotS3Cost > 0) {
    aosRows.push(['Managed Storage (Hot S3)', hotS3Storage > 0 ? `${hotS3Storage} GB` : '', formatPrice(hotS3Cost), ''])
  }

  const ec2Rows: [string, string | number, string | number, string | number][] = []
  if (ec2) {
    const ec2Master = str(ec2.EC2_MASTER_TYPE)
    if (ec2Master) {
      ec2Rows.push([ec2Master, num(ec2.EC2_MASTER_NUM), formatPrice(num(ec2.MASTER_PRICE_MONTH)), num(ec2.MASTER_EC2_Upfront)])
    }

    const ec2Inst = str(ec2.EC2_INSTANCE_TYPE)
    if (ec2Inst) {
      ec2Rows.push([ec2Inst, num(ec2.EC2_NUM), formatPrice(num(ec2.EC2_PRICE_MONTH)), num(ec2.EC2_Upfront)])
    }

    const hotEbs = num(ec2.EC2_REQUIRED_HOT_EBS_TOTAL)
    if (hotEbs > 0) {
      ec2Rows.push(['EBS HOT (SSD GP3)', `${hotEbs} GB`, formatPrice(num(ec2.HOT_STORAGE_PRICE_MONTH)), ''])
    }

    const warmHdd = num(ec2.EC2_REQUIRED_WARM_HDD_TOTAL)
    if (warmHdd > 0) {
      ec2Rows.push(['EBS WARM (HDD)', `${warmHdd} GB`, formatPrice(num(ec2.WARM_STORAGE_PRICE_MONTH)), ''])
    }
  }

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="fixed inset-y-0 right-0 z-50 w-[560px] max-w-[92vw] flex flex-col border-l border-border bg-bg-card shadow-2xl">
        {/* Header */}
        <div className="sticky top-0 flex items-center justify-between border-b border-border bg-bg-card/95 backdrop-blur-lg px-5 py-4 shrink-0">
          <h3 className="text-[15px] font-semibold">Detail</h3>
          <button onClick={onClose} className="rounded-lg p-1.5 text-text-muted hover:bg-bg-elevated hover:text-text transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Cost Summary */}
          <div className="rounded-lg border border-border bg-bg/60 px-4 py-3">
            <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-[13px]">
              <span>
                <span className="text-text-muted">AOS Cost: </span>
                <span className="font-mono font-semibold text-success">${formatPrice(aosCost)}</span>
              </span>
              {ec2Loading ? (
                <span className="flex items-center gap-1.5 text-text-dim">
                  <Loader2 className="h-3 w-3 animate-spin" /> Loading EC2...
                </span>
              ) : ec2 ? (
                <>
                  <span>
                    <span className="text-text-muted">EC2 Cost: </span>
                    <span className="font-mono font-semibold text-warning">${formatPrice(ec2Cost)}</span>
                  </span>
                  {saved > 0 && (
                    <span className="text-success font-semibold">
                      AOS saves {savePct}%
                    </span>
                  )}
                  {saved < 0 && (
                    <span className="text-error font-semibold">
                      EC2 saves {pct(-saved, aosCost)}%
                    </span>
                  )}
                </>
              ) : null}
            </div>
          </div>

          {/* AOS Section */}
          <div>
            <div className="rounded-t-lg bg-emerald-600/90 px-4 py-2.5">
              <h4 className="text-[13px] font-semibold text-white">Amazon OpenSearch Service</h4>
            </div>
            <PriceTable rows={aosRows} total={aosCost} />
          </div>

          {/* EC2 Section */}
          <div>
            <div className="rounded-t-lg bg-amber-600/90 px-4 py-2.5">
              <h4 className="text-[13px] font-semibold text-white">AWS EC2 Self-Managed</h4>
            </div>
            {ec2Loading ? (
              <div className="flex items-center justify-center gap-2 border border-t-0 border-border rounded-b-lg py-8 text-text-dim text-[13px]">
                <Loader2 className="h-4 w-4 animate-spin" /> Calculating EC2 sizing...
              </div>
            ) : ec2 ? (
              <PriceTable rows={ec2Rows} total={ec2Cost} />
            ) : (
              <div className="border border-t-0 border-border rounded-b-lg py-6 text-center text-[13px] text-text-dim">
                EC2 comparison unavailable
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="shrink-0 border-t border-border px-5 py-3">
          <button
            onClick={onClose}
            className="w-full rounded-lg border border-border bg-bg-elevated px-4 py-2 text-[13px] font-medium text-text hover:bg-bg-input transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </>
  )
}

// --------------- PriceTable ---------------

function PriceTable({ rows, total }: { rows: [string, string | number, string | number, string | number][]; total: number }) {
  return (
    <div className="border border-t-0 border-border rounded-b-lg overflow-hidden">
      <table className="w-full text-[12px]">
        <thead>
          <tr className="border-b border-border bg-bg-elevated/60">
            <th className="text-left px-4 py-2 font-semibold text-text-muted">Items</th>
            <th className="text-left px-3 py-2 font-semibold text-text-muted w-[90px]">Number</th>
            <th className="text-right px-3 py-2 font-semibold text-text-muted w-[100px]">Price/mo</th>
            <th className="text-right px-4 py-2 font-semibold text-text-muted w-[80px]">Upfront</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([item, number, price, upfront], i) => (
            <tr key={i} className="border-b border-border/50 hover:bg-bg-elevated/30 transition-colors">
              <td className="px-4 py-2 font-mono text-text">{item}</td>
              <td className="px-3 py-2 text-text-muted">{number}</td>
              <td className="px-3 py-2 text-right font-mono text-text">${price}</td>
              <td className="px-4 py-2 text-right font-mono text-text-muted">{upfront === '' ? '' : num(upfront) === 0 ? '$0' : `$${formatPrice(num(upfront))}`}</td>
            </tr>
          ))}
          <tr className="bg-bg-elevated/40">
            <td className="px-4 py-2.5 font-semibold text-text">Total</td>
            <td></td>
            <td className="px-3 py-2.5 text-right font-mono font-semibold text-success">${formatPrice(total)}</td>
            <td></td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}
