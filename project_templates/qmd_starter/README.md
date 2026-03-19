# QMD Starter Template

This template is designed for project-first markdown workflows using QMD.

## Install QMD

```bash
npm install -g @tobilu/qmd
# or run directly
npx @tobilu/qmd --help
```

## Initialize index in this project

```bash
cd <your-project-root>
qmd --db ./qmd.sqlite collection add ./md/jds --name jds
qmd --db ./qmd.sqlite collection add ./md/notes --name notes
qmd --db ./qmd.sqlite collection add ./md/research --name research
qmd --db ./qmd.sqlite collection add ./md/output --name output
qmd --db ./qmd.sqlite collection add ./md/logs --name logs
```

## Add context (recommended)

```bash
qmd --db ./qmd.sqlite context add qmd://jds "Raw input documents"
qmd --db ./qmd.sqlite context add qmd://notes "Working notes and decisions"
qmd --db ./qmd.sqlite context add qmd://research "Research artifacts"
qmd --db ./qmd.sqlite context add qmd://output "Generated outputs"
qmd --db ./qmd.sqlite context add qmd://logs "Operational logs"
```

## Build embeddings

```bash
qmd --db ./qmd.sqlite embed
```
