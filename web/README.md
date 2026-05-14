# React + TypeScript + Vite

## HouseInsight Web：手动验证清单

在改 UI / 无障碍 / 样式后，建议按下列项做一次抽样检查（与 `frontend-ui-engineering` 的 Verification 对齐）。

- **键盘与焦点**：从页面顶部开始用 `Tab` 顺序遍历所有可聚焦控件（按钮、文件选择、文本框、数字框）；确认可见焦点环（`focus-visible`）清晰；`Shift+Tab` 反向无陷阱。
- **读屏与实时区域**：启动一次分析后，确认「事件流」区域对追加事件有适度播报（`aria-live="polite"`）；运行中主表单或「开始分析」按钮带有忙碌语义（`aria-busy`）。
- **视口宽度**：在开发者工具中将宽度分别设为 **320px**、**768px**、**1024px**，确认步骤条换行、双栏变单栏、表单与日志无重叠或横向溢出。
- **Lighthouse**：Chrome DevTools → Lighthouse → 勾选 **Accessibility**，对当前页跑一次抽样；关注对比度、名称/标签、ARIA 相关提示并逐项核对。

---

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
