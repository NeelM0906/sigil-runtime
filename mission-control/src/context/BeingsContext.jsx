import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { beingsApi } from '../api'

const BeingsContext = createContext(null)

export function BeingsProvider({ children }) {
  const [beings, setBeings] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedBeingId, setSelectedBeingId] = useState(null)

  const fetchBeings = useCallback(async () => {
    try {
      const { beings: fetched } = await beingsApi.list()
      setBeings(fetched)
    } catch (err) {
      console.error('Failed to fetch beings:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchBeings() }, [fetchBeings])

  const getBeingById = useCallback((id) => {
    return beings.find(b => b.id === id) || null
  }, [beings])

  const updateBeingStatus = useCallback(async (id, status) => {
    try {
      const { being } = await beingsApi.update(id, { status })
      setBeings(prev => prev.map(b => b.id === id ? being : b))
    } catch (err) {
      console.error('Failed to update being status:', err)
    }
  }, [])

  const openBeingDetail = useCallback((id) => {
    setSelectedBeingId(id)
  }, [])

  const closeBeingDetail = useCallback(() => {
    setSelectedBeingId(null)
  }, [])

  return (
    <BeingsContext.Provider value={{
      beings,
      loading,
      getBeingById,
      updateBeingStatus,
      fetchBeings,
      selectedBeingId,
      openBeingDetail,
      closeBeingDetail,
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
