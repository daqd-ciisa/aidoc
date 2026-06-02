import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark";
const KEY = "aidoc-theme";

function current(): Theme {
  if (typeof document === "undefined") return "light";
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

function apply(theme: Theme) {
  const root = document.documentElement;
  root.classList.toggle("dark", theme === "dark");
  try {
    localStorage.setItem(KEY, theme);
  } catch {
    /* ignore */
  }
}

/**
 * Maneja el tema claro/oscuro. El tema inicial ya lo aplica el script inline
 * de index.html (anti-flash); este hook solo lo sincroniza con React.
 */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(current);

  useEffect(() => {
    apply(theme);
  }, [theme]);

  const toggle = useCallback(() => {
    setTheme((t) => (t === "dark" ? "light" : "dark"));
  }, []);

  return { theme, toggle, isDark: theme === "dark" };
}
