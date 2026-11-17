// Docked panels: any panel pinned to a screen edge can be resized by dragging its inner edge and folded away.
// One primitive for every dock in the Factory (the waybill waterfall at the bottom, the inspector on the right),
// so they all drag, fold, take the keyboard and remember their size the same way.
//
// State per dock persists in localStorage under `manual.dock.<id>` as {"size": px, "collapsed": bool}.
// Every storage access is guarded: a private window or blocked storage just means the defaults come back.
import { useCallback, useEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from 'react'

export type Edge = 'bottom' | 'right'

export interface DockOpts {
  /** The edge the panel is pinned to; the grip sits on the opposite (inner) side. */
  edge: Edge
  /** Smallest open size in px. Dragging well below it folds the dock (when `collapsible`). */
  min: number
  /** Largest size in px, read on every render so a window resize re-clamps. */
  max: () => number
  /** Size in px the first time a viewer sees this dock. */
  initial: () => number
  /** Whether the dock may fold away entirely. */
  collapsible?: boolean
}

export interface Dock {
  size: number
  collapsed: boolean
  dragging: boolean
  min: number
  max: number
  edge: Edge
  collapsible: boolean
  setSize: (px: number) => void
  setCollapsed: (c: boolean) => void
  toggle: () => void
  /** Drag plumbing for DockGrip: show a size without saving it, then save once on release. */
  preview: (v: DockState) => void
  persist: (v: DockState) => void
  setDragging: (d: boolean) => void
}

export interface DockState { size: number; collapsed: boolean }

const KEY = (id: string) => `manual.dock.${id}`
/** How far below `min` a drag has to go before the dock folds: a deliberate pull, not a twitch. */
const SNAP = 56
const STEP = 24

function load(id: string): { size?: number; collapsed?: boolean } {
  try {
    const raw = window.localStorage.getItem(KEY(id))
    const v = raw ? JSON.parse(raw) : null
    if (!v || typeof v !== 'object') return {}
    return { size: typeof v.size === 'number' && isFinite(v.size) ? v.size : undefined, collapsed: typeof v.collapsed === 'boolean' ? v.collapsed : undefined }
  } catch { return {} }
}
function save(id: string, size: number, collapsed: boolean) {
  try { window.localStorage.setItem(KEY(id), JSON.stringify({ size: Math.round(size), collapsed })) } catch { /* storage off: the dock still works, it just forgets */ }
}

/** Re-render on window resize so `max()` is re-read and the size re-clamped. */
function useViewport() {
  const [, bump] = useState(0)
  useEffect(() => {
    const f = () => bump((n) => n + 1)
    window.addEventListener('resize', f)
    return () => window.removeEventListener('resize', f)
  }, [])
}

export function useDock(id: string, o: DockOpts): Dock {
  useViewport()
  const [st, setSt] = useState<DockState>(() => {
    const s = load(id)
    return { size: s.size ?? o.initial(), collapsed: !!o.collapsible && !!s.collapsed }
  })
  const [dragging, setDragging] = useState(false)
  const max = Math.max(o.min, o.max())
  const size = Math.min(max, Math.max(o.min, st.size))
  const live = useRef(st)
  live.current = st
  const persist = useCallback((next: DockState) => { setSt(next); save(id, next.size, next.collapsed) }, [id])
  const commit = persist
  const setSize = useCallback((px: number) => commit({ size: px, collapsed: false }), [commit])
  const setCollapsed = useCallback((c: boolean) => commit({ ...live.current, collapsed: !!o.collapsible && c }), [commit, o.collapsible])
  const toggle = useCallback(() => setCollapsed(!live.current.collapsed), [setCollapsed])
  return { size, collapsed: st.collapsed, dragging, min: o.min, max, edge: o.edge, collapsible: !!o.collapsible, setSize, setCollapsed, toggle, preview: setSt, persist, setDragging }
}

/**
 * The grab handle on a dock's inner edge. Drag to resize, double-click (or Enter) to fold and unfold,
 * arrow keys to nudge (Shift for bigger steps), Home / End for smallest / largest.
 * It is a `separator` with a value, so a screen reader hears the size.
 */
export function DockGrip({ dock, label }: { dock: Dock; label: string }) {
  const d = dock
  const from = useRef<{ p: number; size: number; collapsed: boolean; moved: boolean } | null>(null)
  const last = useRef<DockState>({ size: d.size, collapsed: d.collapsed })
  const vertical = d.edge === 'bottom'
  const at = (e: PointerEvent) => (vertical ? e.clientY : e.clientX)

  const onDown = (e: PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return
    e.preventDefault()
    e.currentTarget.setPointerCapture(e.pointerId)
    // a folded dock drags open from its folded height (0 extra), so a short pull up brings it back at `min`
    from.current = { p: at(e), size: d.collapsed ? 0 : d.size, collapsed: d.collapsed, moved: false }
    last.current = { size: d.size, collapsed: d.collapsed }
    d.setDragging(true)
    document.documentElement.classList.add(vertical ? 'dock-drag-y' : 'dock-drag-x')
  }
  const onMove = (e: PointerEvent<HTMLDivElement>) => {
    const f = from.current
    if (!f) return
    const delta = f.p - at(e) // the inner edge moves toward the middle of the screen as the dock grows
    if (!f.moved && Math.abs(delta) < 3) return
    f.moved = true
    const raw = f.size + delta
    const next: DockState = d.collapsible && raw < d.min - SNAP
      ? { size: f.collapsed ? last.current.size : Math.max(d.min, f.size), collapsed: true }
      : { size: Math.min(d.max, Math.max(d.min, raw)), collapsed: false }
    last.current = next
    d.preview(next)
  }
  const onUp = (e: PointerEvent<HTMLDivElement>) => {
    const f = from.current
    if (!f) return
    from.current = null
    if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId)
    d.setDragging(false)
    document.documentElement.classList.remove('dock-drag-y', 'dock-drag-x')
    if (f.moved) d.persist(last.current)
    e.currentTarget.blur() // a mouse drag must not leave the grip holding the keyboard
  }
  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    const grow = vertical ? 'ArrowUp' : 'ArrowLeft'
    const shrink = vertical ? 'ArrowDown' : 'ArrowRight'
    const step = e.shiftKey ? STEP * 4 : STEP
    let handled = true
    if (e.key === grow) d.setSize(d.collapsed ? d.min : Math.min(d.max, d.size + step))
    else if (e.key === shrink) {
      if (d.collapsed) { /* already as small as it goes */ }
      else if (d.collapsible && d.size <= d.min) d.setCollapsed(true)
      else d.setSize(Math.max(d.min, d.size - step))
    }
    else if (e.key === 'Home') d.setSize(d.min)
    else if (e.key === 'End') d.setSize(d.max)
    else if ((e.key === 'Enter' || e.key === ' ') && d.collapsible) d.toggle()
    else handled = false
    if (handled) { e.preventDefault(); e.stopPropagation() }
  }
  // unmounted mid-drag (the inspector closes when playback moves on): no pointerup will come, so end the drag here
  const setDragging = d.setDragging
  useEffect(() => () => {
    if (from.current) { from.current = null; setDragging(false) }
    document.documentElement.classList.remove('dock-drag-y', 'dock-drag-x')
  }, [setDragging])

  return (
    <div
      className={`dock-grip ${d.edge}${d.dragging ? ' on' : ''}`}
      role="separator"
      aria-orientation={vertical ? 'horizontal' : 'vertical'}
      aria-label={label}
      aria-valuemin={d.min}
      aria-valuemax={d.max}
      aria-valuenow={d.collapsed ? 0 : Math.round(d.size)}
      tabIndex={0}
      data-fold={d.collapsible ? '1' : undefined}
      title={`${label}: drag to resize${d.collapsible ? ', double-click to fold' : ''}`}
      onPointerDown={onDown}
      onPointerMove={onMove}
      onPointerUp={onUp}
      onPointerCancel={onUp}
      onDoubleClick={() => d.collapsible && d.toggle()}
      onKeyDown={onKey}
    />
  )
}
