import { useEffect, useState } from 'react'
import { projectsApi } from '../api'

const KIND_STYLES = {
  workspace: 'text-accent-cyan bg-accent-cyan/10 border-accent-cyan/20',
  project: 'text-accent-green bg-accent-green/10 border-accent-green/20',
  colosseum: 'text-accent-pink bg-accent-pink/10 border-accent-pink/20',
  dashboard: 'text-accent-blue bg-accent-blue/10 border-accent-blue/20',
  service: 'text-accent-orange bg-accent-orange/10 border-accent-orange/20',
}

function ProjectCard({ project }) {
  const badgeStyle = KIND_STYLES[project.kind] || 'text-text-secondary bg-bg-tertiary border-border'

  return (
    <article className="rounded-xl border border-border bg-bg-secondary/80 p-4 shadow-[0_12px_40px_rgba(0,0,0,0.18)]">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-text-primary">{project.name}</h3>
            <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${badgeStyle}`}>
              {project.kind}
            </span>
          </div>
          <p className="mt-1 text-xs text-text-muted break-all">{project.relative_path || project.path}</p>
        </div>
        <div className="text-[10px] uppercase tracking-wider text-text-muted shrink-0">
          {project.workspace_id || 'shared'}
        </div>
      </div>

      {project.summary && (
        <p className="mt-3 text-xs leading-5 text-text-secondary">{project.summary}</p>
      )}

      {project.entrypoints?.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {project.entrypoints.map(entry => (
            <span key={entry} className="rounded-md bg-bg-tertiary px-2 py-1 text-[11px] text-text-secondary">
              {entry}
            </span>
          ))}
        </div>
      )}

      {project.tags?.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {project.tags.map(tag => (
            <span key={tag} className="rounded-full border border-border px-2 py-0.5 text-[10px] uppercase tracking-wider text-text-muted">
              {tag}
            </span>
          ))}
        </div>
      )}
    </article>
  )
}

export function ProjectsHub() {
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')

  const loadProjects = async () => {
    try {
      setLoading(true)
      setError('')
      const { projects: items } = await projectsApi.list()
      setProjects(items || [])
    } catch (err) {
      setError(err.message || 'Failed to load projects')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProjects()
  }, [])

  const filteredProjects = projects.filter(project => {
    const haystack = [
      project.name,
      project.kind,
      project.path,
      ...(project.tags || []),
      ...(project.entrypoints || []),
    ].join(' ').toLowerCase()
    return haystack.includes(search.trim().toLowerCase())
  })

  return (
    <section className="space-y-4">
      <div className="rounded-xl border border-border bg-bg-secondary/60 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-muted">Projects</p>
            <h2 className="mt-1 text-lg font-semibold text-text-primary">OpenClaw Project Universe</h2>
            <p className="mt-1 text-sm text-text-secondary">
              Repo-contained inventory of the bundled workspaces, imported projects, and both Colosseum surfaces.
            </p>
          </div>
          <div className="flex gap-2">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search projects, tags, entrypoints"
              className="min-w-[260px] rounded-lg border border-border bg-bg-primary px-3 py-2 text-sm text-text-primary outline-none placeholder:text-text-muted"
            />
            <button
              onClick={loadProjects}
              className="rounded-lg border border-border bg-bg-primary px-3 py-2 text-sm text-text-secondary transition-colors hover:text-text-primary"
            >
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {loading && (
          <div className="col-span-full rounded-xl border border-border bg-bg-secondary/60 p-8 text-center text-sm text-text-muted">
            Loading project inventory…
          </div>
        )}
        {!loading && error && (
          <div className="col-span-full rounded-xl border border-accent-pink/30 bg-accent-pink/10 p-6 text-sm text-accent-pink">
            {error}
          </div>
        )}
        {!loading && !error && filteredProjects.length === 0 && (
          <div className="col-span-full rounded-xl border border-border bg-bg-secondary/60 p-8 text-center text-sm text-text-muted">
            No projects matched this filter.
          </div>
        )}
        {!loading && !error && filteredProjects.map(project => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>
    </section>
  )
}
