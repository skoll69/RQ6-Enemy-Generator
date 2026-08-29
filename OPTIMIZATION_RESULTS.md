### Enemy List Performance Optimization Results

#### Overview
The enemy list view (`/enemies/`) was suffering from a severe N+1 query problem, executing over 9,000 database queries for a single page load with production-scale data (~4,500 templates). Through an incremental backend optimization, the query complexity was reduced to **O(1)**.

#### Performance Metrics
The measurements were taken using a production-scale dataset with **4,491** published enemy templates.

| Metric | Baseline (Initial) | Stage 2 (Refactored) | Stage 3 (Final) |
| :--- | :--- | :--- | :--- |
| **Total Database Queries** | ~9,000 | 4,493 | **2** |
| **Backend Execution Time** | ~2.00s | 0.95s | **0.43s** |
| **Improvement (Time)** | - | 52% | **78%** |
| **Improvement (Queries)** | - | 50% | **99.98%** |

#### Key Optimizations

1.  **Model Method Optimization (`enemygen/models.py`)**
    - `get_tags()`: Modified to utilize the internal Django `_prefetched_objects_cache`.
    - `is_starred()`: Updated to check for a pre-populated `starred` attribute before querying the database.
    - `get_starred()`: Enhanced with `select_related` and `prefetch_related` to batch-fetch related race, owner, and tag data.

2.  **Consolidated View Logic (`enemygen/views_lib.py`)**
    - Refactored `get_enemy_templates` to use a single `QuerySet` instead of multiple list extensions.
    - Used `Q` objects to combine published and user-owned templates in a single SQL statement.
    - Applied `select_related('race', 'owner')` and `prefetch_related('tags')` to handle relationships in O(1) queries.

3.  **Database-Level Annotations**
    - Implemented `annotate(starred=Exists(...))` with `OuterRef` to determine the user's star status directly in the main database query, eliminating the need for a per-template Python loop.

#### Verification
- **Unit Tests**: All 37 tests (28 original + 9 new optimization/regression tests) pass successfully.
- **Large Dataset**: Confirmed performance gains on a dataset with 435,000+ skills and 9,000+ templates.
- **Functionality**: Star icons, tag filtering, and visibility rules (public vs. private) work correctly for both authenticated and anonymous users.

#### Scripts Used
- `dev_tools/measure_performance.py`: Used to measure execution time and query counts.
- `dev_tools/count_rows.py`: Used to verify database scale.
