import { useEffect, useState } from 'react'

type Theme = 'light' | 'dark'

const KEY = 'hf_theme'

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(() => {
    const stored = localStorage.getItem(KEY) as Theme | null
    if (stored === 'light' || stored === 'dark') return stored
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme === 'dark' ? 'light' : 'dark')
    localStorage.setItem(KEY, theme === 'dark' ? 'light' : 'dark')
  }, [theme])

  const setTheme = (t: Theme) => setThemeState(t)
  const toggle = () => setThemeState((t) => (t === 'light' ? 'light' : 'dark'))

  return { theme, setTheme, toggle }
}
