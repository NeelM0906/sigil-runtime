# Email Arena Audit - 2026-02-28

## Query Scope
- Database: `email_ad.db`
- Filter: `type = 'sequence'`
- Metric: `WR = wins / (wins + losses)`
- Timestamp (local): `2026-02-28 23:50:32 EST`

## Being Counts By Type

| type | count |
| --- | ---: |
| subject_line | 20 |

## Sequence Inventory

| total_sequences | zero_battles |
| ---: | ---: |
| 0 | 0 |

## Top 10 Sequences By WR

| rank | id | content | wins | losses | wr_pct | score | generation |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| - | (no rows) | - | - | - | - | - | - |

## Bottom 10 Sequences By WR

| rank | id | content | wins | losses | wr_pct | score | generation |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| - | (no rows) | - | - | - | - | - | - |

## SQL Used

```sql
SELECT type, COUNT(*) AS count
FROM beings
GROUP BY type
ORDER BY count DESC;

SELECT
  COUNT(*) AS total_sequences,
  COALESCE(SUM(CASE WHEN wins + losses = 0 THEN 1 ELSE 0 END), 0) AS zero_battles
FROM beings
WHERE type = 'sequence';

SELECT
  id,
  type,
  content,
  wins,
  losses,
  ROUND(CASE WHEN wins + losses > 0 THEN 100.0 * wins / (wins + losses) ELSE 0 END, 2) AS wr_pct,
  score,
  generation
FROM beings
WHERE type = 'sequence'
ORDER BY
  CASE WHEN wins + losses > 0 THEN 1.0 * wins / (wins + losses) ELSE 0 END DESC,
  (wins + losses) DESC,
  id ASC
LIMIT 10;

SELECT
  id,
  type,
  content,
  wins,
  losses,
  ROUND(CASE WHEN wins + losses > 0 THEN 100.0 * wins / (wins + losses) ELSE 0 END, 2) AS wr_pct,
  score,
  generation
FROM beings
WHERE type = 'sequence'
ORDER BY
  CASE WHEN wins + losses > 0 THEN 1.0 * wins / (wins + losses) ELSE 0 END ASC,
  (wins + losses) DESC,
  id ASC
LIMIT 10;
```
