# Shot Batch Sorting Feature

## Problem
When shots are generated in parallel batches, the `shots.json` file had shots in random order based on which batch completed first. This caused:
- Shots from batch 2 appearing before batch 1
- Non-sequential batch_number values in the JSON file
- Confusion when processing shots sequentially

## Solution
Modified `SessionManager.save_shots()` in `core/session_manager.py` to:

1. **Sort shots by batch_number** before saving
2. **Maintain order within each batch** (preserve original order)
3. **Reindex shots from 1 to n** after sorting

## Implementation

### Modified Function: `save_shots()`

```python
def save_shots(self, session_id, shots):
    """Save shot data (image prompts, motion prompts) and initialize status fields"""
    session_dir = os.path.join(self.sessions_dir, session_id)
    shots_path = os.path.join(session_dir, "shots.json")

    # Sort shots by batch_number, then preserve original order within each batch
    # If batch_number is not present, use the original index
    shots_with_batch = [(i, s) for i, s in enumerate(shots)]
    # Sort by batch_number first, then by original index to maintain order within batches
    shots_with_batch.sort(key=lambda x: (x[1].get('batch_number', x[0] + 1), x[0]))

    # Add status fields to each shot with reindexed values (1 to n)
    shots_with_status = []
    for idx, (original_idx, shot) in enumerate(shots_with_batch, start=1):
        shot_data = {
            'index': idx,  # Reindexed from 1 to n
            'image_prompt': shot.get('image_prompt', ''),
            'motion_prompt': shot.get('motion_prompt', ''),
            'camera': shot.get('camera', ''),
            'narration': shot.get('narration', ''),
            'batch_number': shot.get('batch_number', idx),
            # Status fields
            'image_generated': False,
            'image_path': None,
            'image_paths': [],
            'video_rendered': False,
            'video_path': None
        }
        shots_with_status.append(shot_data)

    # Log batch distribution for debugging
    batch_counts = {}
    for shot in shots_with_status:
        batch_num = shot.get('batch_number', 0)
        batch_counts[batch_num] = batch_counts.get(batch_num, 0) + 1
    logger.info(f"Shots sorted by batch_number: {batch_counts}")

    # Save to shots.json
    with open(shots_path, 'w', encoding='utf-8') as f:
        json.dump(shots_with_status, f, indent=2, ensure_ascii=False)

    # Update metadata
    meta = self.load_session(session_id)
    meta['stats']['total_shots'] = len(shots)
    meta['steps']['shots'] = True
    self._save_meta(session_id, meta)
```

## Key Features

### 1. Sorting Logic
```python
shots_with_batch.sort(key=lambda x: (x[1].get('batch_number', x[0] + 1), x[0]))
```
- Primary sort: by `batch_number`
- Secondary sort: by original index (preserves order within batch)
- Fallback: if no `batch_number`, uses `original index + 1`

### 2. Reindexing
```python
for idx, (original_idx, shot) in enumerate(shots_with_batch, start=1):
    shot_data = {
        'index': idx,  # New sequential index (1, 2, 3, ...)
        'batch_number': shot.get('batch_number', idx),  # Original batch preserved
        ...
    }
```
- After sorting, shots are reindexed from 1 to n
- Original `batch_number` is preserved for reference
- New `index` is sequential and ordered

### 3. Debug Logging
```python
logger.info(f"Shots sorted by batch_number: {batch_counts}")
```
- Logs how many shots are in each batch
- Example output: `Shots sorted by batch_number: {1: 5, 2: 5, 3: 5}`
- Helps verify batch distribution

## Example

### Before (unordered)
```json
[
  {"index": 1, "batch_number": 2, ...},
  {"index": 2, "batch_number": 1, ...},
  {"index": 3, "batch_number": 3, ...},
  {"index": 4, "batch_number": 2, ...},
  {"index": 5, "batch_number": 1, ...}
]
```

### After (sorted by batch_number, reindexed)
```json
[
  {"index": 1, "batch_number": 1, ...},
  {"index": 2, "batch_number": 1, ...},
  {"index": 3, "batch_number": 2, ...},
  {"index": 4, "batch_number": 2, ...},
  {"index": 5, "batch_number": 3, ...}
]
```

## Benefits

1. **Predictable Order**: Shots are always saved in batch order
2. **Sequential Indexes**: `index` field goes from 1 to n without gaps
3. **Batch Tracking**: `batch_number` field preserves which batch a shot came from
4. **Backward Compatible**: Doesn't break existing code that reads shots.json
5. **Debugging**: Logs show batch distribution for verification

## Files Modified

- `core/session_manager.py` - `save_shots()` method

## Testing

To verify the fix works:

1. Generate a session with multiple batches (scene_count > SHOT_GENERATION_BATCH_SIZE)
2. Check `shots.json` - shots should be ordered by batch_number
3. Verify index field is sequential (1, 2, 3, ...)
4. Check logs for batch distribution message
