---
name: stagematch-design
description: Frontend development and design for stageMatch. Focus on Midnight Blue & Emerald Green palette, Vanilla CSS refactoring, and UI consistency. Use when improving layouts, components, or colors in HTML/CSS files.
---

# Stagematch Design Skill

This skill guides the refactoring and development of the stageMatch frontend using a modern Midnight Blue and Emerald Green aesthetic.

## Principles

1. **Brand Consistency**: Always use the colors defined in `references/design-system.md`.
2. **Vanilla CSS**: Avoid external libraries. Use CSS variables for everything.
3. **One File per Page**: Each HTML has its own CSS file, but they should share the same design language.

## Workflows

### 1. Refactoring an Existing Page
When asked to "improve" or "refactor" a page:
1. Identify existing color variables (like `--v1`, `--v2`) and replace them with the new brand variables.
2. Load the brand variables from `assets/brand-variables.css` if possible, or copy them into the `:root` of the CSS file.
3. Simplify complex CSS. Many current files are very large; look for redundant styles.
4. Apply the Emerald Green accent to interactive elements (buttons, links, active states).

### 2. Creating New Components
Refer to `references/design-system.md` for code snippets for:
- Buttons (Primary, Secondary)
- Cards and Containers
- Form Inputs

### 3. Adding or Fixing Light Theme Support
When a page needs `data-theme="light"` support, or when the light theme looks broken (invisible text, washed-out surfaces, sections that stay dark):
1. Check/add the `:root[data-theme="light"]` variable block (see "Tema chiaro" in `references/design-system.md`).
2. Grep the whole page CSS for literal `white`/`#fff`/`rgba(255,255,255,*)` used for text or surfaces — these are the near-universal cause of light-theme breakage, not the variable block itself. Replace them with `var(--text)`, `var(--text-muted)`, `var(--surface)`, `var(--surface-hov)`, or `var(--border)`.
3. Toggle `data-theme="light"` and visually check the **entire page**, not just the section you touched — literal colors elsewhere in the file are what cause regressions.

## Reference Files
- [design-system.md](references/design-system.md): The source of truth for colors and UI patterns.

## Assets
- [brand-variables.css](assets/brand-variables.css): The CSS variables to be injected into pages.
