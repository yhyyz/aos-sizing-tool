const BASE = ''

export interface SizingParams {
  dailyDataSize: number
  hotDays: number
  warmDays: number
  coldDays: number
  replicaNum: number
  writePeak: number
  AZ: number
  region: string
  RI: string
  paymentOptions: string
  master: number
  compressionRatio: number
  warmArchitecture: string
  enableCpuShardCheck: boolean
}

export interface EC2SizingParams extends SizingParams {
  reqEC2Instance: string
}

export const DEFAULT_PARAMS: SizingParams = {
  dailyDataSize: 2000,
  hotDays: 1,
  warmDays: 7,
  coldDays: 14,
  replicaNum: 1,
  writePeak: 24,
  AZ: 2,
  region: 'US East (N. Virginia)',
  RI: '0yr',
  paymentOptions: 'OD',
  master: 3,
  compressionRatio: 0.4,
  warmArchitecture: 'ultrawarm',
  enableCpuShardCheck: false,
}

export interface ApiResponse<T> {
  code: number
  result: T
}

export interface ListResult {
  list: Record<string, unknown>[]
}

async function post<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`API Error: ${res.status}`)
  return res.json() as Promise<T>
}

async function get<T>(url: string): Promise<T> {
  const res = await fetch(`${BASE}${url}`)
  if (!res.ok) throw new Error(`API Error: ${res.status}`)
  return res.json() as Promise<T>
}

export const api = {
  aosSizing: (params: SizingParams) =>
    post<ApiResponse<ListResult>>('/v2/sizing/aos', params),

  ec2Sizing: (params: EC2SizingParams) =>
    post<ApiResponse<ListResult>>('/v2/sizing/ec2', params),

  regions: () =>
    get<ApiResponse<{ list: string[] }>>('/v2/regions'),

  instanceFamilies: () =>
    get<ApiResponse<{ aos: unknown[]; ec2: unknown[] }>>('/v2/instance-families'),
}
