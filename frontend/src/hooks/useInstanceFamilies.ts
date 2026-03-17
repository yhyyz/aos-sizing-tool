import { useState, useEffect } from 'react'
import { api } from '@/lib/api'
import type { InstanceFamilyInfo } from '@/lib/api'

export function useInstanceFamilies() {
  const [families, setFamilies] = useState<InstanceFamilyInfo[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.instanceFamilies()
      .then((res) => {
        setFamilies(res.result.aos)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  return { families, loading }
}
