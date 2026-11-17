import { useEffect, useState } from 'react'

/** True at phone width (the same 720px break the stylesheet uses). */
export function usePhone() {
  const [p, setP] = useState(() => matchMedia('(max-width: 720px)').matches)
  useEffect(() => {
    const m = matchMedia('(max-width: 720px)')
    const f = () => setP(m.matches)
    m.addEventListener('change', f)
    return () => m.removeEventListener('change', f)
  }, [])
  return p
}
