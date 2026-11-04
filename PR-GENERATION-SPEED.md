# Optimize enemy generation query performance

## Summary

Reduce database queries during enemy generation through instance-level caching of frequently accessed properties, reverse managers, dice string parsing cache, and combat style weapon caching.

## Benchmarks

### Nandi (501 cults, complex magic user)

| Metric | Before (master) | After (feature) | Improvement |
| :--- | :--- | :--- | :--- |
| **Database Queries** | 356 | 51 | **86% fewer** |
| **Avg Generation Time** | 64.89ms | 13.42ms | **79% faster** |
| **Max Generation Time** | 415.85ms | 24.71ms | **94% faster** |

Note: Query counts vary between runs because different cults are randomly selected each generation.

### Aldrya High Shaman (complex magic user, 8 enemies)

High shamans have many spells, skills, and spirits. This is where the caching optimizations shine.

| Metric | Before (master) | After (feature) | Improvement |
| :--- | :--- | :--- | :--- |
| **Queries per generation** | 148 | 93 | **37% fewer** |
| **Avg time per generation** | 25.82ms | 17.05ms | **34% faster** |
| **Total for 8 enemies** | 206.56ms | 136.40ms | **34% faster** |

### Average Human (simple enemy)

Simple enemy with 1 combat style, 7 stats, 49 skills.

| Metric | Before (master) | After (feature) | Improvement |
| :--- | :--- | :--- | :--- |
| **Queries per generation** | 43 | 16 | **63% fewer** |
| **Avg time** | 8.12ms | 2.78ms | **66% faster** |

### Summary

All enemy types benefit significantly from the caching optimizations. Complex magic users (High Shamans) see 34% faster generation with 37% fewer queries. Simple enemies are 66% faster with 63% fewer queries. Enemies with recursive cult generation (Nandi) see dramatic improvements: 79% faster average and 94% faster worst-case.

## Changes

### 1. Dice parsing cache (`enemygen/dice.py`)

Extracted `_dissect()` from the `Dice` class and wrapped it with `@lru_cache(maxsize=256)`. Common dice strings like `"2D6+3"` or `"STR+DEX"` are parsed once and reused across all rolls.

### 2. Reverse managers for all properties (`enemygen/models.py`)

Changed all 22 `EnemyTemplate` properties from direct ORM queries to Django reverse managers (e.g., `self.enemystat_set.all()` instead of `EnemyStat.objects.filter(enemy_template=self)`).

### 3. Spell property caching (`enemygen/models.py`)

Added instance-level caching to the 4 spell properties (`folk_spells`, `theism_spells`, `sorcery_spells`, `mysticism_spells`). Each property caches its result on first access, avoiding repeated queries for the same template's spells. Cache is invalidated when `EnemySpell` or `CustomSpell` instances are saved or deleted.

### 4. Skills property caching (`enemygen/models.py`)

Added instance-level caching to the `skills` property, which combines `EnemySkill` and `CustomSkill` queries. Cache is invalidated when skills are saved or deleted.

### 5. Feature list items caching (`enemygen/models.py`)

Added instance-level caching to `AdditionalFeatureList.items` and optimized `get_random_item()` to use the cached list. This eliminates repeated queries for the same feature list's items during generation.

### 6. Combat style weapon caching (`enemygen/models.py`)

Added instance-level caching to all 5 `CombatStyle` weapon properties (`one_h_options`, `two_h_options`, `ranged_options`, `shield_options`, `custom_weapons`). During generation, each weapon property was called twice per combat style (once for `len()`, once for `select_random_items()`), triggering 16 redundant queries. Cache is invalidated when `EnemyWeapon` or `CustomWeapon` instances are saved or deleted.

## Evidence

All 615 existing tests pass. Two tests updated:
- `test_additional_feature_list_items` uses `len()` instead of `.count()` since cached items returns a list.
- `test_custom_weapons_property` expects `list` instead of `QuerySet` since cached custom_weapons returns a list.

## Notes

- The remaining queries for Average Human (16) are the minimum needed: 7 one-time template property lookups (stats, skills, features, hit locations, cults, combat styles) and 9 weapon queries (4 weapon types × EnemyWeapon + CustomWeapon, each called once).
- The remaining queries for High Shaman (93) come primarily from **recursive spirit generation**: each of the 7 spirits is a separate template instance with its own spell/skill queries.
- Further optimization would require cross-instance caching or memoizing `generate()` results for repeated spirit/cult templates.
- Cache invalidation ensures that tests and runtime code that modify spells/skills/features/weapons see the updated data.
