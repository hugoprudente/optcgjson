# optcg-card-scraper

A scraper and build pipeline for One Piece TCG card data (JSON), made with Python.

![One Piece Trading Card Game Logo](https://static.wikia.nocookie.net/onepiece/images/8/80/One_Piece_Card_Game_Logo.png/revision/latest?cb=20220317022331)

## Pipeline

```bash
pip install -r requirements.txt

# Discover sets on the official site (updates root series_map.yaml)
python -m optcg scrape --refresh-list --lang en

# Scrape + normalize + write output/
python -m optcg all --lang en

# Downstream-friendly series map for punkrecords
python -m optcg series-map --from-output
```

### Published output (downstream contract)

Built artifacts under **`output/`** are committed to git for consumers:

| Path | Description |
|------|-------------|
| `output/{CODE}.json` | Per-set card data (`{meta, data}` envelope, camelCase fields) |
| `output/series_map.yaml` | Flattened set metadata (`name`, `series`, `image`, `releaseDate`) |

Raw scrape cache: `sets/{lang}/*.json` (internal build input — **not** for downstream import; punkrecords uses `output/` only).

Weekly CI commits both `output/` and `sets/` so rebuilds and multi-language merges stay reproducible.

## Downstream: punkrecords

[punkrecords](https://github.com/hugoprudente/punkrecords) imports `output/` weekly (no scraping in that repo). See its [docs/OP_DATA_SYNC.md](https://github.com/hugoprudente/punkrecords/blob/main/docs/OP_DATA_SYNC.md).

Weekly schedule (UTC): optcgjson scrape **03:00** → punkrecords import **06:00** → image CDN sync **07:00**.

## CI

`.github/workflows/weekly-sync.yml` runs the full English pipeline on a schedule and auto-commits when Bandai data changes.

## Legacy

Get all card images [HERE](https://drive.google.com/drive/folders/1_pJdoYT494pofrWDB0M5YWguCYR8K3cb?usp=sharing) if you don't want to scrape them yourself. (Everything up until OP-07)
