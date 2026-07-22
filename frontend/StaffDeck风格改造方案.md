# nanzi 前端 StaffDeck 风格改造方案

> 模式:**Redesign - Overhaul**(视觉语言全新对齐 StaffDeck,保留现有内容与信息架构)
> 目标产品参考:`sd.ekuaibao.net/enterprise/dashboard`(StaffDeck 数字员工运营台)
> 适用范围:nanzi 前端(`frontend/`,Vue 3 + Tailwind v3)

---

## 0. 背景与目标

**现状一句话:** nanzi 前端是「Tailwind v3 + 全手写组件 + 仿 AntD 蓝」的通用后台皮,无 token 体系、无字体声明、无公共组件基元,圆角/阴影/边框各页即兴,视图为 3000 至 6800 行的巨型 SFC。

**目标一句话:** 对齐 StaffDeck 的「暖纸底 + 冷色镀铬 + 青绿主色 + 发丝边 + 近无阴影 + cockpit 密度」精密运营台语言,建立可维护的 token 与基元组件体系。

**Design Read:** 企业级 AI 智能体运营台 for 内部运营/管理员,采用精密仪表盘式冷静语言,基于 Tailwind token 体系 + 自研统一组件,暖纸底色配冷色镀铬与青绿主色。

**三旋钮定级:**
| 旋钮 | 估值 | 理由 |
|---|---|---|
| `DESIGN_VARIANCE` | 5 | 非对称分栏、暖冷并置有设计意识,但整体仍是规整后台栅格 |
| `MOTION_INTENSITY` | 3 | 静态为主,仅过渡与 1px 按压 |
| `VISUAL_DENSITY` | 8 | cockpit 级:12px 字、32px 控件、发丝边、近无阴影 |

---

## 1. 技术栈决策

| 项 | 决策 | 理由 |
|---|---|---|
| 框架 | **保留 Vue 3** | 现状即 Vue,不引入 React |
| 样式 | **保留 Tailwind v3**(主方案) | 现状即 v3,迁移 v4 成本高,单独立项。v3 用 CSS 变量 + config 映射即可实现 token |
| 暗色 | **保留 `darkMode: 'class'`** | 现状即 class 模式,在 `<html class="dark">` 时覆盖 token 变量 |
| 组件库 | **不引入 shadcn-vue 等重依赖,自建轻量基元** | 现有大量手写组件,引入重依赖会冲突;借鉴 shadcn 的 token 命名与组件结构,用 Vue + Tailwind 自实现 |
| 字体 | **自托管 Geist Variable + Alimama ShuHeiTi** | 对齐 StaffDeck 字体栈;自托管避免运行时外链 |

> 备选:Tailwind v3 升级 v4。v4 的 `@theme` 与 `--tw-*` 体系更贴近 StaffDeck,但迁移成本不低,**建议 token 体系先在 v3 落地,v4 升级单独立项**。

---

## 2. 设计 Token 规范(核心,可直接落地)

### 2.1 光色 token(`:root`)

```css
:root {
  /* 暖纸底色层 */
  --background: #f7f5ef;          /* 应用底,暖奶油纸 */
  --surface: #ffffff;             /* 卡片表面 */
  --surface-subtle: #fbfaf6;      /* 次级表面 */
  --surface-muted: #eeece4;       /* 静音表面 */

  /* 文字 */
  --foreground: #20201d;          /* 正文,暖近黑 */
  --muted-foreground: #6d726e;    /* 次要文字 */

  /* 边框 */
  --border: #ded7cc;              /* 暖米色描边 */
  --border-soft: #e8e2d6;         /* 更淡的分割线 */

  /* 青绿主色 */
  --primary: #0f766e;             /* teal-700 */
  --primary-foreground: #ffffff;
  --primary-hover: #0e6b64;
  --primary-active: #0b5a54;

  /* 强调 */
  --accent: #f6f6f6;              /* hover 底 */
  --accent-soft: #e1f1ed;         /* 薄荷软色,主色淡底 */

  /* 语义 */
  --destructive: #dc2626;
  --success: #04756f;
  --warning: #b45309;

  /* 冷色镀铬层(控件 chrome) */
  --chrome-border: #e3e7f1;       /* 控件发丝边 */
  --chrome-border-hover: #cbd3e6; /* 控件 hover 边 */
  --chrome-muted: #757f9c;        /* 控件标签字 */
  --chrome-muted-2: #8b94aa;      /* Tab 未激活字 */
  --chrome-fg: #18181a;           /* chrome 主字(全页最高频) */

  /* 头像/状态点 */
  --avatar-bg: #eef1fb;
  --avatar-fg: #7e96dc;

  /* 侧边栏 */
  --sidebar: #ffffff;
  --sidebar-foreground: #858b9c;
  --sidebar-border: #f4f4f4;
  --sidebar-accent: #f6f6f6;
  --sidebar-accent-foreground: #18181a;

  /* 圆角 / 间距 */
  --radius: 0.625rem;             /* 10px,统一圆角 */
  --spacing: 0.25rem;             /* 4px 基准 */
  --card-spacing: calc(var(--spacing) * 4); /* 16px */

  /* 阴影(近无阴影,仅极淡抬升) */
  --shadow-raised: 0 -12px 28px rgba(21, 26, 38, 0.04);
  --shadow-overlay: 0 8px 24px rgba(21, 26, 38, 0.06);

  /* 边框粗细 */
  --border-hairline: 0.5px;       /* 发丝边 */

  /* 动效 */
  --ease-out: cubic-bezier(0.32, 0.72, 0, 1);
  --duration-fast: 150ms;
  --duration-base: 200ms;
  --duration-slow: 300ms;         /* 侧边栏展开 */

  /* 字体 */
  --font-sans: "Geist Variable", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  --font-display: "Alimama ShuHeiTi", "Geist Variable", "PingFang SC", sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
}
```

### 2.2 暗色 token(`.dark`)

> 基于 StaffDeck 暗色片段(`#202126`/`#2c2f38`/`#343741`/`#2b2d33`/`#8f98aa`/`#c5ccd8`/`#f0f2f6`)推算,实施时按实际效果微调。

```css
.dark {
  --background: #202126;
  --surface: #2c2f38;
  --surface-subtle: #343741;
  --surface-muted: #3a3e48;

  --foreground: #f0f2f6;
  --muted-foreground: #8f98aa;

  --border: #2b2d33;
  --border-soft: #343741;

  --primary: #14b8a6;             /* 暗色提亮 teal */
  --primary-foreground: #04201d;
  --primary-hover: #2dd4bf;
  --primary-active: #14b8a6;

  --accent: #343741;
  --accent-soft: #113b36;

  --destructive: #ef4444;
  --success: #2dd4bf;

  --chrome-border: #343741;
  --chrome-border-hover: #464c5e;
  --chrome-muted: #8f98aa;
  --chrome-muted-2: #8f98aa;
  --chrome-fg: #f0f2f6;

  --avatar-bg: #2c3344;
  --avatar-fg: #9bb0e8;

  --sidebar: #1a1c20;
  --sidebar-foreground: #8f98aa;
  --sidebar-border: #2b2d33;
  --sidebar-accent: #2c2f38;
  --sidebar-accent-foreground: #f0f2f6;

  --shadow-raised: 0 -12px 28px rgba(0, 0, 0, 0.24);
  --shadow-overlay: 0 8px 24px rgba(0, 0, 0, 0.36);
}
```

### 2.3 `tailwind.config.js` 映射

把现有手填的 AntD 蓝替换为 token 引用,让 `bg-surface`、`text-foreground`、`border-border`、`rounded-lg` 等类全部可用且统一。

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
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
        primary: {
          DEFAULT: 'var(--primary)',
          foreground: 'var(--primary-foreground)',
          hover: 'var(--primary-hover)',
          active: 'var(--primary-active)',
        },
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
          fg: 'var(--chrome-fg)',
        },
        avatar: {
          bg: 'var(--avatar-bg)',
          fg: 'var(--avatar-fg)',
        },
        sidebar: {
          DEFAULT: 'var(--sidebar)',
          foreground: 'var(--sidebar-foreground)',
          border: 'var(--sidebar-border)',
          accent: 'var(--sidebar-accent)',
          'accent-foreground': 'var(--sidebar-accent-foreground)',
        },
      },
      borderRadius: {
        DEFAULT: 'var(--radius)',     /* 10px */
        sm: 'calc(var(--radius) - 4px)',
        md: 'calc(var(--radius) - 2px)',
        lg: 'var(--radius)',          /* 统一 10px */
        xl: 'var(--radius)',          /* 收敛,不再 12px */
      },
      fontFamily: {
        sans: ['var(--font-sans)'],
        display: ['var(--font-display)'],
        mono: ['var(--font-mono)'],
      },
      boxShadow: {
        raised: 'var(--shadow-raised)',
        overlay: 'var(--shadow-overlay)',
        none: 'none',
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
```

### 2.4 `style.css` base 层

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root { /* 2.1 的变量贴在这里 */ }
  .dark { /* 2.2 的变量贴在这里 */ }

  * {
    border-color: var(--border);   /* 默认边框统一为 token */
  }

  html {
    font-family: var(--font-sans);
    background-color: var(--background);
    color: var(--foreground);
    -webkit-font-smoothing: antialiased;
  }

  /* 标题用展示字体 */
  h1, h2, h3 {
    font-family: var(--font-display);
  }
}
```

---

## 3. 字体引入方案

**目标栈:** Geist Variable(主力无衬线)+ Alimama ShuHeiTi 阿里妈妈数黑体(品牌/大标题)。生产自托管,禁止 Google Fonts 运行时 `<link>`。

### 3.1 获取字体文件

| 字体 | 来源 | 文件 |
|---|---|---|
| Geist Variable | `npm i @fontsource-variable/geist` 或 https://github.com/vercel/geist-font | `Geist-Variable.woff2`(可变字重,单文件) |
| Alimama ShuHeiTi | Google Fonts「Alimama ShuHeiTi」或阿里妈妈官方 | `AlimamaShuHeiTi-Regular.woff2`(单字重) |

### 3.2 自托管落地(推荐)

把 woff2 放到 `frontend/public/fonts/`,在 `style.css` 顶部声明:

```css
@font-face {
  font-family: "Geist Variable";
  font-style: normal;
  font-weight: 100 900;            /* 可变字重范围 */
  font-display: swap;
  src: url("/fonts/Geist-Variable.woff2") format("woff2-variations");
}

@font-face {
  font-family: "Alimama ShuHeiTi";
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url("/fonts/AlimamaShuHeiTi-Regular.woff2") format("woff2");
}
```

### 3.3 便捷方式(备选)

`main.ts` 中 `import '@fontsource-variable/geist'`,Alimama ShuHeiTi 仍自托管 woff2。注意 npm 方式会增加打包体积,生产建议走 3.2 自托管 + CDN 缓存。

---

## 4. 基元组件设计

在 `frontend/src/components/common/` 下新建基元(现状该目录仅有 `TokenAmount.vue`)。每个基元对齐 StaffDeck 签名:**0.5px 发丝边、10px 圆角、32px 控件、12-14px 字、近无阴影、1px 按压**。

### 4.1 AppButton

```vue
<!-- components/common/AppButton.vue -->
<script setup lang="ts">
interface Props {
  variant?: 'primary' | 'outline' | 'ghost' | 'destructive'
  size?: 'sm' | 'md'              /* sm=28px, md=32px */
  icon?: boolean
}
withDefaults(defineProps<Props>(), { variant: 'outline', size: 'md' })
</script>

<template>
  <button
    class="inline-flex shrink-0 items-center justify-center gap-1 whitespace-nowrap
           rounded-lg border-[0.5px] transition-all duration-base ease-out
           active:translate-y-px disabled:pointer-events-none disabled:opacity-50
           focus-visible:outline-none"
    :class="{
      'h-7 px-3 text-xs': size === 'sm',
      'h-8 px-5 text-xs': size === 'md',
      'bg-primary text-primary-foreground border-primary hover:bg-primary-hover':
        variant === 'primary',
      'bg-white border-chrome-border text-chrome-muted hover:border-chrome-border-hover hover:text-chrome-fg dark:bg-surface dark:border-chrome-border dark:text-chrome-muted dark:hover:text-chrome-fg':
        variant === 'outline',
      'bg-transparent border-transparent text-chrome-muted hover:bg-accent hover:text-chrome-fg':
        variant === 'ghost',
      'bg-destructive text-white border-destructive hover:bg-destructive/90':
        variant === 'destructive',
    }"
  >
    <slot name="icon" />
    <slot />
  </button>
</template>
```

要点:
- 默认 `outline` 变体(白底 + 冷色发丝边 + 灰字),hover 才转深 `--chrome-fg`。这是 StaffDeck 的低存在感按钮。
- `active:translate-y-px` 提供 1px 按压触觉。
- `border-[0.5px]` 发丝边。

### 4.2 AppCard

```vue
<!-- components/common/AppCard.vue -->
<script setup lang="ts">
interface Props { as?: string; padded?: boolean }
withDefaults(defineProps<Props>(), { as: 'div', padded: true })
</script>

<template>
  <component
    :is="as"
    class="rounded-lg bg-surface border-[0.5px] border-chrome-border dark:border-chrome-border"
    :class="padded && 'p-4'"
  >
    <slot />
  </component>
</template>
```

要点:无阴影,靠发丝边 + 白表面对比暖纸底分层。需要抬升时手动加 `shadow-raised`。

### 4.3 AppInput

```vue
<!-- components/common/AppInput.vue -->
<script setup lang="ts">
interface Props { modelValue?: string; placeholder?: string }
defineProps<Props>()
defineEmits<{ 'update:modelValue': [string] }>()
</script>

<template>
  <input
    :value="modelValue"
    :placeholder="placeholder"
    @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    class="h-8 w-full rounded-lg border-[0.5px] border-chrome-border bg-white px-3
           text-xs text-chrome-fg placeholder:text-chrome-muted
           transition-colors duration-base ease-out
           hover:border-chrome-border-hover
           focus:border-chrome-border-hover focus:outline-none
           dark:bg-surface dark:text-chrome-fg"
  />
</template>
```

### 4.4 AppTabs(line 变体)

对齐 StaffDeck:激活项 `rounded-t-lg rounded-b-none`、`font-bold`、`shadow-raised`(顶部极淡抬升,模拟从下方托起),未激活 `text-chrome-muted-2`。

### 4.5 AppSidebar + AppAvatar

- **AppSidebar:** 固定 `inset-y-0`、`bg-sidebar backdrop-blur-[9.5px]`(毛玻璃)、图标栏模式 `w-14`(32px 图标 + padding)、展开 `w-60`;折叠过渡 `duration-slow ease-out`。激活项 `bg-sidebar-accent text-sidebar-accent-foreground`。
- **AppAvatar:** `rounded-full bg-avatar text-avatar-fg size-8` 占位首字。

### 4.6 基元清单(优先级)

| 顺序 | 组件 | 覆盖场景 |
|---|---|---|
| 1 | AppButton | 全站按钮统一 |
| 2 | AppCard | 全站卡片容器 |
| 3 | AppInput | 表单/搜索/筛选 |
| 4 | AppTabs | 详情页 Tab(资料/技能/SOP/日志等) |
| 5 | AppSidebar | 统一 app shell |
| 6 | AppAvatar | 智能体/用户头像 |
| 7 | AppBadge / AppStatusDot | 状态标签(在线/禁用) |

---

## 5. 布局骨架改造

### 5.1 现状问题

`bg-sidebar`/`#001529` 仅 `views/Dashboard.vue` 一处使用,**无统一 app shell**,各视图自渲染 chrome。

### 5.2 目标:统一 AppLayout

新建 `frontend/src/layouts/AppLayout.vue`:

```
┌─────────────────────────────────────────────┐
│ ┌──┐  顶栏(标题/面包屑/操作)               │
│ │  │                                        │
│ │侧│  ┌──────────────┬───────────────────┐ │
│ │边│  │ 左:资料/列表  │ 右:详情/编辑       │ │
│ │栏│  │ 0.72fr       │ 1.28fr            │ │
│ │  │  │              │                   │ │
│ └──┘  └──────────────┴───────────────────┘ │
└─────────────────────────────────────────────┘
```

- 外层 `app-shell flex min-h-screen`,侧边栏 `fixed inset-y-0 w-14`(图标栏默认)/ `w-60`(展开)。
- 主区 `xl:grid-cols-[minmax(320px,0.72fr)_minmax(0,1.28fr)]` 非对称分栏(对齐 StaffDeck 0.72/1.28)。
- 侧边栏从 `Dashboard.vue` 抽出,做成全局持久 chrome。

### 5.3 路由接入

在 `router` 里把需要 app chrome 的视图包进 `AppLayout` 的 `<router-view>` 嵌套;`/embed/*` 仍走现有 `EmbedLayout`。

---

## 6. 分阶段实施计划

### Phase 0:地基(token + 字体)— 1 至 2 天

- [ ] 落地 `style.css` 的 `:root` / `.dark` 变量(2.1 / 2.2)
- [ ] 改造 `tailwind.config.js`(2.3)
- [ ] 自托管 Geist Variable + Alimama ShuHeiTi(第 3 节)
- [ ] 全局 `html` 字体与底色生效,老页面暂不动
- **验收:** 打开任意页面,字体已变 Geist,底色已变暖纸 `#f7f5ef`,且无样式塌陷(老 class 仍可用,因为 token 与旧 utility 共存)

### Phase 1:基元 + 全局收敛 — 3 至 5 天

- [ ] 建 AppButton / AppCard / AppInput(4.1 至 4.3)
- [ ] 全局圆角收敛:`rounded-xl/2xl` -> `rounded-lg`(统一 10px)
- [ ] 全局阴影收敛:`shadow-2xl/xl/lg` -> `shadow-sm` 或 `shadow-none`
- [ ] 全局主色收敛:`text-blue-600` / `bg-blue-50` / `border-blue-300` -> `primary` / `accent-soft` / `primary`
- **验收:** 抽样 3 个页面,圆角/阴影/主色视觉统一,无 `blue-600` 残留

### Phase 2:AppLayout + 侧边栏 — 3 至 5 天

- [ ] 建 `AppLayout.vue` + AppSidebar(4.5)
- [ ] 侧边栏从 `Dashboard.vue` 抽出为全局 chrome
- [ ] 主区非对称分栏落地
- [ ] 暗色模式 token 验证(`.dark` 切换无塌陷)
- **验收:** 全站统一侧边栏,折叠/展开过渡 `duration-slow ease-out` 顺滑,暗色两套都通

### Phase 3:视图逐个迁移(试点 AgentManagement)— 滚动

- [ ] AgentManagement 作为试点:用 AppLayout + AppCard + AppTabs 重写布局,搜索/筛选改 AppInput/AppButton
- [ ] 拆分 3925 行 SFC,把筛选栏、列表、详情抽子组件
- [ ] 试点通过后,按视图优先级滚动迁移:AgentDebug -> KnowledgeBaseManagement -> Users -> SystemConfig -> 其余
- **验收:** 试点视图视觉与 StaffDeck 一致,SFC 行数下降 30% 以上

### Phase 4:动效 + 密度 + 暗色收尾 — 2 至 3 天

- [ ] 删除 `hover:scale-*`、`duration-1000/500`,控件统一 `duration-base ease-out` + `active:translate-y-px`
- [ ] 关键控件收紧到 32px(`h-8`)、字号 12 至 14px
- [ ] 全站暗色双测
- [ ] `prefers-reduced-motion` 兜底(动效降级为瞬切)
- **验收:** 全站无花哨动效,密度对齐 cockpit,暗色完整可用

---

## 7. 迁移策略(处理巨型 SFC)

**原则:不重写,渐进式。**

1. **新页面/新功能**一律用新基元 + token,不再写裸 `rounded-lg border-gray-300 shadow-sm`。
2. **老页面**按 Phase 3 顺序迁移,迁移时顺手把内联 class 换成基元。
3. **巨型 SFC**(EmbedChat 6812 行 / AgentDebug 6168 行)不强求一次拆完,优先抽**重复出现的 UI 片段**(筛选栏、卡片、Tab 面板)为子组件,逐步降体积。
4. **token 与旧 utility 共存**,可随时回滚:旧 `bg-white`/`text-gray-900` 不删,新页面用 `bg-surface`/`text-foreground`,迁移一个替换一个。

---

## 8. 不改的东西(信息架构红线)

> 参考技能 11.F,以下不擅自改:

- URL 结构 / 路由 slug(`/login`、`/embed/*`、各 view 路径不变)
- 主导航标签文案
- 表单字段 name 与顺序(影响 autofill 与既有数据)
- API 接口与字段
- 功能逻辑(只改视觉与结构,不改行为)

---

## 9. 风险与回滚

| 风险 | 应对 |
|---|---|
| 0.5px 发丝边在低 DPR 屏渲染为 0 | 关键控件 fallback 用 `1px`;优先在 Retina 屏验证 |
| 暖纸底 `#f7f5ef` 与既有白卡片对比度不足 | 卡片用 `--surface:#fff`,对比足够;边框靠 `--chrome-border` 分层 |
| 主色从蓝换 teal 影响认知 | 本方案明确对齐 StaffDeck,已确认接受;token 化后色值集中一处,可整体回退 |
| 巨型 SFC 迁移周期长 | 渐进式,token 层先全站生效,视图迁移分批,不影响功能 |
| 暗色 token 为推算值 | Phase 2 实际切暗色验证后微调 |

**回滚:** token 全部集中在 `style.css` + `tailwind.config.js`,任一阶段出问题可单独回退变量值,不影响组件代码。

---

## 10. 验收清单

### 设计语言对齐
- [ ] 全站底色 `--background #f7f5ef`,卡片 `--surface #fff`
- [ ] 主色统一 `--primary #0f766e`(teal),无 `blue-600` 残留
- [ ] 圆角统一 10px(`rounded-lg`),无 `rounded-xl/2xl` 混用
- [ ] 默认无阴影,抬升仅用 `shadow-raised`(4% 不透明度)
- [ ] 控件发丝边 `border-[0.5px]` + `--chrome-border`
- [ ] 字体 Geist Variable + Alimama ShuHeiTi 已自托管生效
- [ ] 控件高度 32px(`h-8`),字号 12 至 14px
- [ ] 动效仅 `transition` + `active:translate-y-px`,无 `hover:scale` / `duration-1000`

### 工程化
- [ ] `style.css` token 层完整(光色 + 暗色)
- [ ] `tailwind.config.js` colors/borderRadius/fontFamily 全部指向变量
- [ ] `components/common/` 至少有 AppButton/AppCard/AppInput/AppTabs/AppSidebar 五个基元
- [ ] `layouts/AppLayout.vue` 统一 app shell,侧边栏全局持久
- [ ] 暗色模式 `.dark` 双测通过
- [ ] `prefers-reduced-motion` 兜底生效

### 不破坏
- [ ] 路由/URL 不变
- [ ] 导航标签文案不变
- [ ] 表单字段 name/顺序不变
- [ ] 功能逻辑不变
- [ ] 既有页面未迁移前不塌陷(token 与旧 utility 共存)

---

## 附:StaffDeck 参考 token 速查

| 分类 | token | 值 |
|---|---|---|
| 底色 | background | `#f7f5ef` |
| 表面 | surface / subtle / muted | `#fff` / `#fbfaf6` / `#eeece4` |
| 文字 | foreground / muted | `#20201d` / `#6d726e` |
| 边框 | border | `#ded7cc` |
| 主色 | primary | `#0f766e` |
| 强调 | accent / accent-soft | `#f6f6f6` / `#e1f1ed` |
| 破坏 | destructive | `#dc2626` |
| chrome | border / muted / fg | `#e3e7f1` / `#757f9c` / `#18181a` |
| 圆角 | radius | `0.625rem`(10px) |
| 动效 | ease-out | `cubic-bezier(0.32, 0.72, 0, 1)` |
| 抬升 | shadow-raised | `0 -12px 28px rgba(21,26,38,0.04)` |
