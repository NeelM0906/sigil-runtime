import { useState, useEffect, useCallback, useRef } from 'react'
import { workspaceApi } from '../api'
import { useBeings } from '../context/BeingsContext'

const CATEGORY_ICONS = {
  document: 'DOC',
  spreadsheet: 'XLS',
  image: 'IMG',
  code: '</>',
  text: 'TXT',
  data: 'DAT',
  video: 'VID',
  other: 'FILE',
}

const CATEGORY_COLORS = {
  document: 'text-accent-red',
  spreadsheet: 'text-accent-green',
  image: 'text-accent-purple',
  code: 'text-accent-cyan',
  text: 'text-text-secondary',
  data: 'text-accent-amber',
  video: 'text-accent-orange',
  other: 'text-text-muted',
}

export function WorkspaceManager() {
  const { beings } = useBeings()
  const [selectedBeing, setSelectedBeing] = useState('')
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [preview, setPreview] = useState(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState(null)
  const fileInputRef = useRef(null)

  // Auto-select first being
  useEffect(() => {
    if (beings.length > 0 && !selectedBeing) {
      setSelectedBeing(beings[0].id)
    }
  }, [beings, selectedBeing])

  const fetchFiles = useCallback(async () => {
    if (!selectedBeing) return
    setLoading(true)
    try {
      const data = await workspaceApi.files(selectedBeing)
      setFiles(data.files || [])
    } catch (err) {
      console.error('Failed to fetch workspace files:', err)
    } finally {
      setLoading(false)
    }
  }, [selectedBeing])

  useEffect(() => { fetchFiles() }, [fetchFiles])

  const handleUpload = async (e) => {
    const selected = Array.from(e.target.files || [])
    if (!selected.length) return
    setUploading(true)
    try {
      const data = await workspaceApi.upload(selectedBeing, selected)
      if (data.errors?.length) {
        alert(`Some files failed:\n${data.errors.map(e => `${e.filename}: ${e.error}`).join('\n')}`)
      }
      fetchFiles()
    } catch (err) {
      alert('Upload failed: ' + err.message)
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleDelete = async (filename) => {
    try {
      await workspaceApi.deleteFile(selectedBeing, filename)
      setFiles(prev => prev.filter(f => f.name !== filename))
      setDeleteConfirm(null)
      if (preview?.filename === filename) setPreview(null)
    } catch (err) {
      alert('Delete failed: ' + err.message)
    }
  }

  const handlePreview = async (filename) => {
    if (preview?.filename === filename) {
      setPreview(null)
      return
    }
    setPreviewLoading(true)
    try {
      const data = await workspaceApi.preview(selectedBeing, filename)
      // Append auth token to media URLs so <img>/<video> can load them
      if (data.media_url) {
        try {
          const stored = localStorage.getItem('mc_auth')
          if (stored) {
            const { token } = JSON.parse(stored)
            if (token) data.media_url += `&token=${encodeURIComponent(token)}`
          }
        } catch { /* ignore */ }
      }
      setPreview(data)
    } catch (err) {
      setPreview({ filename, preview: null, message: 'Failed to load preview' })
    } finally {
      setPreviewLoading(false)
    }
  }

  const filtered = files.filter(f =>
    f.name.toLowerCase().includes(search.toLowerCase())
  )

  const totalSize = files.reduce((sum, f) => sum + f.size, 0)

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="rounded-lg border border-border bg-bg-card p-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-sm font-semibold text-text-primary">Workspace Files</h2>
            <p className="text-[11px] text-text-muted mt-0.5">
              Files uploaded here are indexed and available to SAI across all conversations
            </p>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={selectedBeing}
              onChange={(e) => setSelectedBeing(e.target.value)}
              className="bg-bg-primary border border-border rounded px-2 py-1.5 text-xs text-text-primary"
            >
              {beings.map(b => (
                <option key={b.id} value={b.id}>{b.name || b.id}</option>
              ))}
            </select>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={handleUpload}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading || !selectedBeing}
              className="px-3 py-1.5 rounded bg-accent-blue/20 text-accent-blue text-xs font-medium hover:bg-accent-blue/30 transition-colors disabled:opacity-50"
            >
              {uploading ? 'Uploading...' : 'Upload Files'}
            </button>
          </div>
        </div>

        {/* Stats bar */}
        <div className="flex items-center gap-4 text-[11px] text-text-muted">
          <span>{files.length} file{files.length !== 1 ? 's' : ''}</span>
          <span>{formatSize(totalSize)} total</span>
          {selectedBeing && <span className="text-accent-cyan">{selectedBeing}</span>}
        </div>
      </div>

      {/* Search */}
      {files.length > 5 && (
        <input
          type="text"
          placeholder="Search files..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full bg-bg-card border border-border rounded px-3 py-2 text-xs text-text-primary placeholder:text-text-muted"
        />
      )}

      {/* File list */}
      <div className="rounded-lg border border-border bg-bg-card overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-xs text-text-muted">Loading files...</div>
        ) : filtered.length === 0 ? (
          <div className="p-8 text-center">
            <div className="text-text-muted text-xs">
              {files.length === 0 ? 'No files in workspace yet. Upload files to get started.' : 'No files match your search.'}
            </div>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {/* Table header */}
            <div className="grid grid-cols-12 gap-2 px-3 py-2 bg-bg-secondary text-[10px] text-text-muted uppercase tracking-wider font-medium">
              <div className="col-span-6">Name</div>
              <div className="col-span-2">Type</div>
              <div className="col-span-2 text-right">Size</div>
              <div className="col-span-2 text-right">Actions</div>
            </div>
            {filtered.map(file => (
              <FileRow
                key={file.name}
                file={file}
                isPreviewOpen={preview?.filename === file.name}
                deleteConfirm={deleteConfirm}
                onPreview={() => handlePreview(file.name)}
                onDeleteClick={() => setDeleteConfirm(file.name)}
                onDeleteConfirm={() => handleDelete(file.name)}
                onDeleteCancel={() => setDeleteConfirm(null)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Preview panel */}
      {preview && (
        <div className="rounded-lg border border-border bg-bg-card overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 bg-bg-secondary border-b border-border">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-text-primary">{preview.filename}</span>
              {preview.truncated && (
                <span className="text-[10px] text-accent-amber">
                  Showing {formatChars(8000)} of {formatChars(preview.total_chars)}
                </span>
              )}
            </div>
            <button
              onClick={() => setPreview(null)}
              className="text-text-muted hover:text-text-primary text-xs"
            >
              Close
            </button>
          </div>
          <div className="p-3 max-h-[600px] overflow-auto">
            {previewLoading ? (
              <div className="text-xs text-text-muted">Loading preview...</div>
            ) : preview.media_url && preview.category === 'image' ? (
              <img
                src={preview.media_url}
                alt={preview.filename}
                className="max-w-full max-h-[500px] rounded object-contain mx-auto"
              />
            ) : preview.media_url && preview.category === 'video' ? (
              <video
                src={preview.media_url}
                controls
                className="max-w-full max-h-[500px] rounded mx-auto"
              />
            ) : preview.preview ? (
              <pre className="text-[11px] text-text-secondary font-mono whitespace-pre-wrap break-words leading-relaxed">
                {preview.preview}
              </pre>
            ) : (
              <div className="text-xs text-text-muted">{preview.message || 'No preview available'}</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function FileRow({ file, isPreviewOpen, deleteConfirm, onPreview, onDeleteClick, onDeleteConfirm, onDeleteCancel }) {
  const icon = CATEGORY_ICONS[file.category] || CATEGORY_ICONS.other
  const colorClass = CATEGORY_COLORS[file.category] || CATEGORY_COLORS.other
  const isConfirming = deleteConfirm === file.name

  return (
    <div className={`grid grid-cols-12 gap-2 px-3 py-2.5 items-center hover:bg-bg-hover transition-colors ${isPreviewOpen ? 'bg-bg-hover' : ''}`}>
      <div className="col-span-6 flex items-center gap-2 min-w-0">
        <span className="text-sm flex-shrink-0">{icon}</span>
        <button
          onClick={onPreview}
          className="text-xs text-text-primary hover:text-accent-blue truncate text-left transition-colors"
          title={file.name}
        >
          {file.name}
        </button>
        {file.indexed && (
          <span className="flex-shrink-0 text-[9px] px-1 py-0.5 rounded bg-accent-green/15 text-accent-green">indexed</span>
        )}
      </div>
      <div className="col-span-2">
        <span className={`text-[10px] font-medium ${colorClass}`}>
          {file.extension?.replace('.', '').toUpperCase() || '?'}
        </span>
      </div>
      <div className="col-span-2 text-right text-[11px] text-text-muted font-mono">
        {file.size_display}
      </div>
      <div className="col-span-2 flex justify-end gap-1">
        <button
          onClick={onPreview}
          className="px-1.5 py-0.5 rounded text-[10px] text-text-muted hover:text-accent-blue hover:bg-accent-blue/10 transition-colors"
          title="Preview"
        >
          View
        </button>
        {isConfirming ? (
          <div className="flex gap-1">
            <button
              onClick={onDeleteConfirm}
              className="px-1.5 py-0.5 rounded text-[10px] text-accent-red bg-accent-red/10 hover:bg-accent-red/20 transition-colors"
            >
              Yes
            </button>
            <button
              onClick={onDeleteCancel}
              className="px-1.5 py-0.5 rounded text-[10px] text-text-muted hover:bg-bg-hover transition-colors"
            >
              No
            </button>
          </div>
        ) : (
          <button
            onClick={onDeleteClick}
            className="px-1.5 py-0.5 rounded text-[10px] text-text-muted hover:text-accent-red hover:bg-accent-red/10 transition-colors"
            title="Delete"
          >
            Del
          </button>
        )}
      </div>
    </div>
  )
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatChars(n) {
  if (n < 1000) return `${n} chars`
  return `${(n / 1000).toFixed(1)}K chars`
}
