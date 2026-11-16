import pluginVue from 'eslint-plugin-vue'
import tseslint from 'typescript-eslint'
import prettier from 'eslint-config-prettier'

export default [
  { ignores: ['dist/**', 'node_modules/**', 'coverage/**'] },
  ...tseslint.configs.recommended,
  ...pluginVue.configs['flat/essential'],
  {
    files: ['**/*.vue'],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
        extraFileExtensions: ['.vue'],
        ecmaVersion: 'latest',
        sourceType: 'module',
      },
    },
  },
  {
    languageOptions: {
      globals: {
        window: 'readonly',
        document: 'readonly',
        localStorage: 'readonly',
        sessionStorage: 'readonly',
        console: 'readonly',
        URL: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
      },
    },
    rules: {
      'vue/multi-word-component-names': 'off',
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      'no-restricted-imports': [
        'error',
        {
          paths: [
            {
              name: 'element-plus',
              message: '前台禁用 Element Plus；仅 views/admin 与已登记基线文件可用',
            },
          ],
        },
      ],
    },
  },
  {
    // 基线遗留：管理端组件与全局注册文件允许使用 Element Plus（见 AGENTS §3.1）。
    files: [
      'src/views/admin/**/*.{vue,ts}',
      'src/main.ts',
      'src/api/request.ts',
      'src/stores/toast.ts',
    ],
    rules: { 'no-restricted-imports': 'off' },
  },
  prettier,
]
