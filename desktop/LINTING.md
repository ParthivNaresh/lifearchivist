# Linting & Code Quality Setup

## Tools Installed

### ESLint 9 (Flat Config)
- **Latest version** with modern flat config format
- TypeScript support via `typescript-eslint`
- React-specific rules and hooks validation
- React Refresh (HMR) support

### Prettier
- Code formatter for consistent style
- Integrated with ESLint to avoid conflicts

### TypeScript
- Strict type checking enabled
- Full type safety across the codebase

## Available Commands

### Linting
```bash
npm run lint              # Check for linting errors (fails on warnings)
npm run lint:fix          # Auto-fix linting issues where possible
```

### Formatting
```bash
npm run format            # Format all code with Prettier
npm run format:check      # Check if code is formatted correctly
```

### Type Checking
```bash
npm run type-check        # Run TypeScript compiler without emitting files
```

### All Checks
```bash
npm run check             # Run type-check + lint + format:check
```

## Configuration Files

### `eslint.config.js`
Modern ESLint 9 flat config with:
- TypeScript type-aware linting
- React and React Hooks rules
- React Refresh (HMR) validation
- Strict best practices
- Prettier integration

### `.prettierrc`
Code formatting rules:
- 2 spaces indentation
- Single quotes
- Semicolons
- 100 character line width
- Trailing commas (ES5)

### `tsconfig.json`
TypeScript configuration:
- Strict mode enabled
- Modern ES2020 target
- React JSX support
- Path aliases support (`@/*`)

## Key Rules Enforced

### TypeScript
- ✅ No unused variables (with `_` prefix exception)
- ✅ Explicit error handling for promises
- ✅ Prefer nullish coalescing (`??`)
- ✅ Prefer optional chaining (`?.`)
- ✅ Consistent type imports
- ⚠️ Warnings for `any` types

### React
- ✅ Hooks rules strictly enforced
- ✅ No missing keys in lists
- ✅ No target="_blank" without rel="noopener noreferrer"
- ✅ Self-closing components
- ✅ Exhaustive deps in useEffect
- ⚠️ Warnings for array index as key

### General
- ✅ Prefer `const` over `let`
- ✅ No `var`
- ✅ Strict equality (`===`)
- ✅ Always use curly braces
- ⚠️ Warnings for `console.log` (allow warn/error)
- ❌ No `debugger` statements
- ❌ No `alert()` calls

## IDE Integration

### VS Code
Install these extensions:
- **ESLint** (dbaeumer.vscode-eslint)
- **Prettier** (esbenp.prettier-vscode)

Add to `.vscode/settings.json`:
```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "eslint.validate": [
    "javascript",
    "javascriptreact",
    "typescript",
    "typescriptreact"
  ]
}
```

## Pre-commit Hooks (Optional)

To enforce linting before commits, install husky:

```bash
npm install --save-dev husky lint-staged
npx husky init
```

Add to `package.json`:
```json
{
  "lint-staged": {
    "*.{ts,tsx}": [
      "eslint --fix",
      "prettier --write"
    ]
  }
}
```

## Troubleshooting

### "Parsing error" messages
- Ensure `tsconfig.json` exists
- Run `npm run type-check` to verify TypeScript setup

### ESLint not finding files
- Check `ignores` patterns in `eslint.config.js`
- Ensure files are in `src/` directory

### Prettier conflicts with ESLint
- `eslint-config-prettier` is already installed
- It disables conflicting ESLint rules

### Performance issues
- ESLint 9 with type-aware linting can be slow on large codebases
- Consider disabling type-aware rules for faster feedback:
  - Comment out `...tseslint.configs.recommendedTypeChecked`
  - Use `...tseslint.configs.recommended` instead

## Best Practices

1. **Run `npm run check` before committing**
2. **Fix linting errors immediately** - don't accumulate technical debt
3. **Use `lint:fix` for auto-fixable issues**
4. **Review warnings** - they indicate potential problems
5. **Keep dependencies updated** - run `npm outdated` regularly

## Version Information

- ESLint: 9.x (Flat Config)
- TypeScript ESLint: 8.x
- Prettier: 3.x
- React: 18.x
- TypeScript: 5.x

All tools are using their latest stable versions as of late 2024/early 2025.
