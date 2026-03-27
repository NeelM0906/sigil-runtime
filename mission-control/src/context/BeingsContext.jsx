import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react'
import { beingsApi } from '../api'
import { useSharedSSE } from './SSEContext'
import { useAuth } from './AuthContext'

const BeingsContext = createContext(null)

// Operators see beings based on their tenant. Admins see all core beings.
const OPERATOR_ALLOWED_BEINGS = new Set(['prime', 'recovery'])
const RECOVERY_TEAM_BEINGS = new Set(['recovery'])
// These types are hidden from ALL users
const HIDDEN_TYPES = new Set(['voice', 'subagent', 'acti'])

export function BeingsProvider({ children }) {
  const [allBeings, setAllBeings] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedBeingId, setSelectedBeingId] = useState(null)
  const [beingDetail, setBeingDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const { user } = useAuth()

  const fetchBeings = useCallback(async () => {
    try {
      const { beings: fetched } = await beingsApi.list()
      setAllBeings(fetched)
    } catch (err) {
      console.error('Failed to fetch beings:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchBeings() }, [fetchBeings])

  // SSE: live being status updates
  useSharedSSE({
    being_status(data) {
      setAllBeings(prev =>
        prev.map(b =>
          b.id === data.being_id ? { ...b, status: data.status } : b
        )
      )
    },
  })

  // Filter: hide voice/subagent/acti from ALL users, then role/tenant-based
  const beings = useMemo(() => {
    const visible = allBeings.filter(b => !HIDDEN_TYPES.has(b.type))
    if (user?.role === 'admin') return visible
    // Recovery team only sees SAI Recovery
    if (user?.tenant_id?.startsWith('tenant-recovery')) {
      return visible.filter(b => RECOVERY_TEAM_BEINGS.has(b.id))
    }
    return visible.filter(b => OPERATOR_ALLOWED_BEINGS.has(b.id))
  }, [allBeings, user?.role, user?.tenant_id])

  const getBeingById = useCallback((id) => {
    return beings.find(b => b.id === id) || null
  }, [beings])

  const updateBeingStatus = useCallback(async (id, status) => {
    try {
      const { being } = await beingsApi.update(id, { status })
      setAllBeings(prev => prev.map(b => b.id === id ? being : b))
    } catch (err) {
      console.error('Failed to update being status:', err)
    }
  }, [])

  const openBeingDetail = useCallback(async (id) => {
    setSelectedBeingId(id)
    setDetailLoading(true)
    setBeingDetail(null)
    try {
      const detail = await beingsApi.getDetail(id)
      setBeingDetail(detail)
    } catch (err) {
      console.error('Failed to fetch being detail:', err)
    } finally {
      setDetailLoading(false)
    }
  }, [])

  const closeBeingDetail = useCallback(() => {
    setSelectedBeingId(null)
    setBeingDetail(null)
  }, [])

  const fetchBeingFile = useCallback(async (beingId, filePath) => {
    try {
      const { content } = await beingsApi.getFile(beingId, filePath)
      return content
    } catch (err) {
      console.error('Failed to fetch being file:', err)
      return null
    }
  }, [])

  return (
    <BeingsContext.Provider value={{
      beings,
      loading,
      getBeingById,
      updateBeingStatus,
      fetchBeings,
      selectedBeingId,
      beingDetail,
      detailLoading,
      openBeingDetail,
      closeBeingDetail,
      fetchBeingFile,
    }}>
      {children}
    </BeingsContext.Provider>
  )
}

export function useBeings() {
  const ctx = useContext(BeingsContext)
  if (!ctx) throw new Error('useBeings must be used within BeingsProvider')
  return ctx
}
