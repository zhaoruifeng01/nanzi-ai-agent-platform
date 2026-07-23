/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // 主色:AntD 蓝 → StaffDeck teal(token)。保留全站在用的所有子键
        // (grep: hover:bg-primary-dark ×54, hover:bg-primary-hover ×6, active:bg-primary-active ×4 …)
        primary: {
          DEFAULT: 'var(--primary)',
          foreground: 'var(--primary-foreground)',
          hover: 'var(--primary-hover)',
          active: 'var(--primary-active)',
          dark: 'var(--primary-dark)', // = active，兼容旧 hover:bg-primary-dark
        },
        // 侧边栏:StaffDeck 白底 + 毛玻璃(Phase 2 切换)
        sidebar: {
          DEFAULT: 'var(--sidebar)',
          foreground: 'var(--sidebar-foreground)',
          border: 'var(--sidebar-border)',
          accent: 'var(--sidebar-accent)',
          'accent-foreground': 'var(--sidebar-accent-foreground)',
        },
        // 以下为 StaffDeck token 新增色，供新代码/后续 Phase 使用
        background: 'var(--background)',
        surface: {
          DEFAULT: 'var(--surface)',
          subtle: 'var(--surface-subtle)',
          muted: 'var(--surface-muted)',
        },
        foreground: 'var(--foreground)',
        'muted-foreground': 'var(--muted-foreground)',
        border: 'var(--border)',
        'border-soft': 'var(--border-soft)',
        accent: {
          DEFAULT: 'var(--accent)',
          soft: 'var(--accent-soft)',
        },
        destructive: 'var(--destructive)',
        success: 'var(--success)',
        warning: 'var(--warning)',
        chrome: {
          border: 'var(--chrome-border)',
          'border-hover': 'var(--chrome-border-hover)',
          muted: 'var(--chrome-muted)',
          'muted-2': 'var(--chrome-muted-2)',
          fg: 'var(--chrome-fg)',
        },
        avatar: {
          bg: 'var(--avatar-bg)',
          fg: 'var(--avatar-fg)',
        },
      },
      borderRadius: {
        DEFAULT: 'var(--radius)',
        sm: 'calc(var(--radius) - 4px)',
        md: 'calc(var(--radius) - 2px)',
        lg: 'var(--radius)',
        xl: 'var(--radius)',
      },
      fontFamily: {
        sans: ['var(--font-sans)'],
        display: ['var(--font-display)'],
        mono: ['var(--font-mono)'],
      },
      boxShadow: {
        raised: 'var(--shadow-raised)',
        overlay: 'var(--shadow-overlay)',
      },
      transitionTimingFunction: {
        out: 'var(--ease-out)',
      },
      transitionDuration: {
        fast: 'var(--duration-fast)',
        base: 'var(--duration-base)',
        slow: 'var(--duration-slow)',
      },
    },
  },
  plugins: [],
}
