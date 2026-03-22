# Bharat Market Pulse

Bharat Market Pulse is a portfolio intelligence pipeline for Indian markets.

It extracts portfolio holdings from screenshots or structured data,
collects signals from trusted financial sources,
analyzes sentiment and triggers,
and produces structured investment intelligence reports.

## Project structure

src/
    Python application

docs/
    Quarto documentation site

tests/
    unit tests

## Quickstart

1. create virtual environment

python -m venv .venv
source .venv/bin/activate

2. install dependencies

pip install -e .

3. configure environment

cp .env.example .env

4. run pipeline

python -m bharat_market_pulse.report_pipeline
