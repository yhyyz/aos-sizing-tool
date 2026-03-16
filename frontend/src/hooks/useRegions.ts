import { useState, useEffect } from 'react'
import { api } from '@/lib/api'

export function useRegions() {
  const [regions, setRegions] = useState<string[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.regions()
      .then((res) => {
        setRegions(res.result.list as string[])
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  return { regions, loading }
}
