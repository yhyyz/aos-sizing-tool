import { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import { FieldLabel, Input, Select, Button, Card, AlertInfo, MultiSelect } from '@/components/FormControls'
import DataTable from '@/components/DataTable'
import DetailDrawer from '@/components/DetailDrawer'
import { useRegions } from '@/hooks/useRegions'
import { api, DEFAULT_PARAMS } from '@/lib/api'
import type { SizingParams } from '@/lib/api'
import { Calculator, RotateCcw, ChevronDown, ChevronUp } from 'lucide-react'

const AOS_COLUMNS = [
  { key: 'TOTAL_PRICE_MONTH', label: 'Monthly Cost', width: '130px' },
  { key: 'DEDICATED_MASTER_TYPE', label: 'Master Type' },
  { key: 'INSTANCE_TYPE', label: 'Instance Type' },
  { key: 'HOT_NUM', label: 'Hot Nodes', width: '90px' },
  { key: 'WARM_INSTANCE_TYPE', label: 'Warm Type' },
  { key: 'WARM_NUM', label: 'Warm Nodes', width: '100px' },
]

const PAYMENT_OPTIONS = [
  { value: 'OD', label: 'On-Demand' },
  { value: 'No Upfront', label: 'No Upfront' },
  { value: 'Partial Upfront', label: 'Partial Upfront' },
  { value: 'All Upfront', label: 'All Upfront' },
]

const RI_OPTIONS = [
  { value: '0yr', label: '0yr (On-Demand)' },
  { value: '1yr', label: '1yr' },
  { value: '3yr', label: '3yr' },
]

const AZ_OPTIONS = [
  { value: '1', label: '1 AZ' },
  { value: '2', label: '2 AZ' },
  { value: '3', label: '3 AZ' },
]

const REPLICA_OPTIONS = [
  { value: '0', label: '0' },
  { value: '1', label: '1' },
  { value: '2', label: '2' },
]

const MASTER_OPTIONS = [
  { value: '0', label: '0 (None)' },
  { value: '3', label: '3' },
]

const WARM_ARCH_OPTIONS = [
  { value: 'ultrawarm', label: 'UltraWarm' },
  { value: 'multi_tier', label: 'Multi-Tier (OpenSearch 3.3+)' },
]

const HOT_FAMILY_OPTIONS = [
  { value: 'or1', label: 'or1' }, { value: 'or2', label: 'or2' },
  { value: 'om2', label: 'om2' }, { value: 'oi2', label: 'oi2' },
  { value: 'r7g', label: 'r7g' }, { value: 'r8g', label: 'r8g' },
  { value: 'm7g', label: 'm7g' }, { value: 'm8g', label: 'm8g' },
  { value: 'c7g', label: 'c7g' }, { value: 'c8g', label: 'c8g' },
]

const HOT_SIZE_OPTIONS = [
  { value: 'medium', label: 'medium' }, { value: 'large', label: 'large' },
  { value: 'xlarge', label: 'xlarge' }, { value: '2xlarge', label: '2xlarge' },
  { value: '4xlarge', label: '4xlarge' }, { value: '8xlarge', label: '8xlarge' },
  { value: '12xlarge', label: '12xlarge' }, { value: '16xlarge', label: '16xlarge' },
]

const ULTRAWARM_SIZE_OPTIONS = [
  { value: 'medium', label: 'medium' }, { value: 'large', label: 'large' },
]

const OI2_WARM_SIZE_OPTIONS = [
  { value: 'large', label: 'large' }, { value: 'xlarge', label: 'xlarge' },
  { value: '2xlarge', label: '2xlarge' }, { value: '4xlarge', label: '4xlarge' },
  { value: '8xlarge', label: '8xlarge' },
]

export default function AOSSizingPage() {
  const { regions } = useRegions()
  const [params, setParams] = useState<SizingParams>({ ...DEFAULT_PARAMS })
  const [allData, setAllData] = useState<Record<string, unknown>[]>([])
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState(true)
  const [showAlert, setShowAlert] = useState(true)
  const [selectedRow, setSelectedRow] = useState<Record<string, unknown> | null>(null)
  const [hotFamilies, setHotFamilies] = useState<string[]>([])
  const [hotSizes, setHotSizes] = useState<string[]>([])
  const [warmSizes, setWarmSizes] = useState<string[]>([])
  const [hasSearched, setHasSearched] = useState(false)

  const set = (key: keyof SizingParams, value: string | number | boolean) => {
    setParams((p) => {
      const next = { ...p, [key]: value }
      if (key === 'paymentOptions' && value !== 'OD' && p.RI === '0yr') next.RI = '1yr'
      if (key === 'RI' && value === '0yr') next.paymentOptions = 'OD'
      if (key === 'warmArchitecture' && value === 'multi_tier') next.coldDays = 0
      return next
    })
    if (key === 'warmArchitecture') setWarmSizes([])
  }

  const warmSizeOptions = params.warmArchitecture === 'multi_tier' ? OI2_WARM_SIZE_OPTIONS : ULTRAWARM_SIZE_OPTIONS

  const filteredData = useMemo(() => {
    if (hotFamilies.length === 0 && hotSizes.length === 0 && warmSizes.length === 0) return allData

    return allData.filter((row) => {
      const instParts = String(row.INSTANCE_TYPE ?? '').split('.')
      const warmParts = String(row.WARM_INSTANCE_TYPE ?? '').split('.')
      const hFamily = instParts[0] ?? ''
      const hSize = instParts[1] ?? ''
      const wSize = warmParts[1] ?? ''

      if (hotFamilies.length > 0 && !hotFamilies.includes(hFamily)) return false
      if (hotSizes.length > 0 && !hotSizes.includes(hSize)) return false
      if (warmSizes.length > 0 && !warmSizes.includes(wSize)) return false
      return true
    })
  }, [allData, hotFamilies, hotSizes, warmSizes])

  const pageCount = Math.max(1, Math.ceil(filteredData.length / pageSize))
  const pagedData = useMemo(() => {
    const start = (page - 1) * pageSize
    return filteredData.slice(start, start + pageSize)
  }, [filteredData, page, pageSize])

  const setHotFamiliesAndReset = useCallback((v: string[]) => { setHotFamilies(v); setPage(1) }, [])
  const setHotSizesAndReset = useCallback((v: string[]) => { setHotSizes(v); setPage(1) }, [])
  const setWarmSizesAndReset = useCallback((v: string[]) => { setWarmSizes(v); setPage(1) }, [])

  const doSearch = useCallback(async () => {
    setLoading(true)
    setHasSearched(true)
    try {
      const res = await api.aosSizing(params)
      setAllData(res.result.list)
      setPage(1)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [params])

  const handleSubmit = () => doSearch()

  const initialFired = useRef(false)
  useEffect(() => {
    if (!initialFired.current) {
      initialFired.current = true
      doSearch()
    }
  }, [doSearch])

  const handleReset = () => {
    setParams({ ...DEFAULT_PARAMS })
    setHotFamilies([])
    setHotSizes([])
    setWarmSizes([])
    setAllData([])
    setPage(1)
    setHasSearched(false)
  }

  const regionOptions = regions.map((r) => ({ value: r, label: r }))

  return (
    <div className="mx-auto max-w-[1440px] space-y-5 px-6 py-6">
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[16px] font-semibold">AOS Sizing Parameters</h2>
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-[12px] text-accent hover:text-accent-hover transition-colors"
          >
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            {expanded ? 'Collapse' : 'Expand'}
          </button>
        </div>

        {expanded && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <FieldLabel>Daily Data Size</FieldLabel>
                <Input type="number" suffix="GB" value={params.dailyDataSize} onChange={(e) => set('dailyDataSize', Number(e.currentTarget.value))} />
              </div>
              <div>
                <FieldLabel tooltip="Number of days data stays in hot tier">Hot Days</FieldLabel>
                <Input type="number" value={params.hotDays} onChange={(e) => set('hotDays', Number(e.currentTarget.value))} />
              </div>
              <div>
                <FieldLabel>Warm Days</FieldLabel>
                <Input type="number" value={params.warmDays} onChange={(e) => set('warmDays', Number(e.currentTarget.value))} />
              </div>
              <div>
                <FieldLabel tooltip={params.warmArchitecture === 'multi_tier' ? 'Cold not supported in Multi-Tier' : undefined}>Cold Days</FieldLabel>
                <Input
                  type="number"
                  value={params.coldDays}
                  disabled={params.warmArchitecture === 'multi_tier'}
                  onChange={(e) => set('coldDays', Number(e.currentTarget.value))}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <FieldLabel>Replica Num</FieldLabel>
                <Select value={String(params.replicaNum)} options={REPLICA_OPTIONS} onChange={(e) => set('replicaNum', Number(e.currentTarget.value))} />
              </div>
              <div>
                <FieldLabel tooltip="Peak write throughput in MB/s">Write Peak</FieldLabel>
                <Input type="number" suffix="MB/s" value={params.writePeak} onChange={(e) => set('writePeak', Number(e.currentTarget.value))} />
              </div>
              <div>
                <FieldLabel>AZ</FieldLabel>
                <Select value={String(params.AZ)} options={AZ_OPTIONS} onChange={(e) => set('AZ', Number(e.currentTarget.value))} />
              </div>
              <div>
                <FieldLabel>Region</FieldLabel>
                <Select value={params.region} options={regionOptions} onChange={(e) => set('region', e.currentTarget.value)} />
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <FieldLabel>Payment</FieldLabel>
                <Select value={params.paymentOptions} options={PAYMENT_OPTIONS} onChange={(e) => set('paymentOptions', e.currentTarget.value)} />
              </div>
              <div>
                <FieldLabel>Reserved Instance</FieldLabel>
                <Select value={params.RI} options={RI_OPTIONS} onChange={(e) => set('RI', e.currentTarget.value)} />
              </div>
              <div>
                <FieldLabel>Master Nodes</FieldLabel>
                <Select value={String(params.master)} options={MASTER_OPTIONS} onChange={(e) => set('master', Number(e.currentTarget.value))} />
              </div>
              <div>
                <FieldLabel>Warm Architecture</FieldLabel>
                <Select value={params.warmArchitecture} options={WARM_ARCH_OPTIONS} onChange={(e) => set('warmArchitecture', e.currentTarget.value)} />
              </div>
            </div>

            <div className="flex items-center gap-3 pt-2">
              <Button onClick={handleSubmit} disabled={loading}>
                <Calculator className="h-4 w-4" />
                Calculate
              </Button>
              <Button variant="secondary" onClick={handleReset}>
                <RotateCcw className="h-4 w-4" />
                Reset
              </Button>
            </div>
          </div>
        )}
      </Card>

      {showAlert && (
        <AlertInfo onClose={() => setShowAlert(false)}>
          When total log storage is less than 6TB, Master nodes can be set to 0. Click each row to view pricing details and EC2 comparison.
        </AlertInfo>
      )}

      <Card className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <MultiSelect
            className="w-48"
            options={HOT_FAMILY_OPTIONS}
            selected={hotFamilies}
            onChange={setHotFamiliesAndReset}
            placeholder="All Families"
          />
          <MultiSelect
            className="w-44"
            options={HOT_SIZE_OPTIONS}
            selected={hotSizes}
            onChange={setHotSizesAndReset}
            placeholder="All Sizes"
          />
          <MultiSelect
            className="w-44"
            options={warmSizeOptions}
            selected={warmSizes}
            onChange={setWarmSizesAndReset}
            placeholder="All Warm Sizes"
          />
          {hasSearched && (
            <span className="text-[12px] text-text-dim ml-auto">
              {filteredData.length} results
              {filteredData.length !== allData.length && ` (${allData.length} total)`}
            </span>
          )}
        </div>

        {hasSearched && (
          <p className="text-[12px] text-accent">
            Click each row to view pricing details
          </p>
        )}

        <DataTable
          columns={AOS_COLUMNS}
          data={pagedData}
          loading={loading}
          page={page}
          pageCount={hasSearched ? pageCount : 0}
          pageSize={pageSize}
          onPageChange={setPage}
          onPageSizeChange={(s) => { setPageSize(s); setPage(1) }}
          onRowClick={(row) => setSelectedRow(row)}
          emptyText={hasSearched
            ? (params.warmArchitecture === 'multi_tier'
              ? 'No results — Multi-Tier requires OI2 warm instances (not available in current data source)'
              : 'No results found')
            : 'Click "Calculate" to start sizing'}
        />
      </Card>

      <DetailDrawer row={selectedRow} sizingParams={params} onClose={() => setSelectedRow(null)} />
    </div>
  )
}
