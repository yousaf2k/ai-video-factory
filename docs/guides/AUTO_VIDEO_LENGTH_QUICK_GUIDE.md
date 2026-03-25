# Automatic Video Length Calculation - Quick Guide

## What's New?

The system now automatically calculates how many shots are needed to reach your target video length. No more manual shot counting!

## Basic Configuration

### In `config.py`:

```python
# For automatic 10-minute videos (default)
DEFAULT_MAX_SHOTS = 0           # 0 = use automatic calculation
TARGET_VIDEO_LENGTH = 600       # 600 seconds = 10 minutes
DEFAULT_SHOT_LENGTH = 5         # Each shot is 5 seconds
```

**Result**: System automatically generates 120 shots (600 ÷ 5 = 120)

## How It Works

### Priority Chain (Highest to Lowest):

1. **CLI `--total-length N`** → Calculates shots: `N ÷ shot_length`
2. **CLI `--max-shots N`** → Exact shot count (or 0 for no limit)
3. **Config `DEFAULT_MAX_SHOTS > 0`** → Manual override
4. **Config `TARGET_VIDEO_LENGTH > 0`** → Automatic calculation
5. **None** → Story-driven (no limit)

### Examples:

#### 1. Default Automatic (10-minute video)
```bash
# config.py: TARGET_VIDEO_LENGTH = 600, DEFAULT_MAX_SHOTS = 0
python core/main.py --idea "My documentary"

# Output:
# [INFO] Target video length: 600s (from config)
# [INFO] Automatic calculation: 600s ÷ 5s/shot = 120 shots
# [INFO] Shot distribution: 120 shots across 10 scenes (~12 shots/scene)
```

#### 2. CLI Override (Custom Length)
```bash
python core/main.py --idea "My video" --total-length 120

# Output:
# [INFO] Target video length: 120s (from --total-length)
# [INFO] Automatic calculation: 120s ÷ 5s/shot = 24 shots
```

#### 3. Exact Shot Count
```bash
python core/main.py --idea "My video" --max-shots 50

# Output:
# [INFO] Maximum shots: 50 (from --max-shots CLI override)
```

#### 4. No Limit (Story-Driven)
```bash
python core/main.py --idea "My video" --max-shots 0

# Output:
# [INFO] No shot limit (--max-shots 0)
```

## Configuration Scenarios

### Scenario 1: 10-Minute Documentary (Auto)
```python
DEFAULT_MAX_SHOTS = 0
TARGET_VIDEO_LENGTH = 600  # 10 minutes
```
→ Generates ~120 shots automatically

### Scenario 2: 1-Minute Short (Auto)
```python
DEFAULT_MAX_SHOTS = 0
TARGET_VIDEO_LENGTH = 60  # 1 minute
```
→ Generates ~12 shots automatically

### Scenario 3: Testing (Manual Limit)
```python
DEFAULT_MAX_SHOTS = 10  # Manual override
TARGET_VIDEO_LENGTH = 600  # Ignored
```
→ Generates exactly 10 shots

### Scenario 4: Story-Driven (No Limit)
```python
DEFAULT_MAX_SHOTS = 0
TARGET_VIDEO_LENGTH = 0
```
→ Generates as many shots as story needs

### Scenario 5: Different Shot Lengths
```python
DEFAULT_MAX_SHOTS = 0
TARGET_VIDEO_LENGTH = 600
DEFAULT_SHOT_LENGTH = 3  # 3-second shots
```
→ Generates 200 shots (600 ÷ 3)

## Migration Guide

### If you previously had:
```python
DEFAULT_MAX_SHOTS = 0  # No limit
TARGET_VIDEO_LENGTH = 600  # This was ignored!
```
**Old behavior**: Unlimited shots (TARGET_VIDEO_LENGTH ignored)
**New behavior**: 120 shots automatic (TARGET_VIDEO_LENGTH respected)

### To keep unlimited shots:
```python
DEFAULT_MAX_SHOTS = 0
TARGET_VIDEO_LENGTH = 0  # Set to 0 for no limit
```

## Common Questions

**Q: What if LLM generates more scenes?**
A: Shots are distributed evenly across all scenes. Example: 120 shots ÷ 10 scenes = 12 shots/scene

**Q: Can I still use --max-shots for exact control?**
A: Yes! CLI arguments always take priority over config

**Q: What happens if I set both DEFAULT_MAX_SHOTS and TARGET_VIDEO_LENGTH?**
A: DEFAULT_MAX_SHOTS takes priority (manual override)

**Q: How do I test with just a few shots?**
A: Use `--max-shots 3` or set `DEFAULT_MAX_SHOTS = 3`

**Q: Can I change shot length?**
A: Yes! Use `--shot-length 3` or change `DEFAULT_SHOT_LENGTH` in config

## Logging Examples

### Automatic Calculation:
```
[INFO] Shot length: 5s (from config)
[INFO] Target video length: 600s (from config)
[INFO] Automatic calculation: 600s ÷ 5s/shot = 120 shots
[INFO] Shot distribution: 120 shots across 10 scenes (~12 shots/scene)
[INFO] Target achieved: 120 shots = ~600s video
```

### CLI Override:
```
[INFO] Shot length: 5s (from config)
[INFO] Target video length: 120s (from --total-length)
[INFO] Automatic calculation: 120s ÷ 5s/shot = 24 shots
[INFO] Target achieved: 24 shots = ~120s video
```

### No Limit:
```
[INFO] Shot length: 5s (from config)
[INFO] No shot limit - all story scenes will be generated
[INFO] Final shot count: 87 shots = ~435s video
```

## Tips

- **For consistent video lengths**: Use `TARGET_VIDEO_LENGTH` in config
- **For one-off custom lengths**: Use `--total-length N` CLI flag
- **For testing**: Use `--max-shots N` for exact control
- **For creative freedom**: Use `--max-shots 0` for story-driven
- **To speed up generation**: Reduce `DEFAULT_SHOT_LENGTH` (more shots = longer videos)

## Formula

```
max_shots = int(TARGET_VIDEO_LENGTH / DEFAULT_SHOT_LENGTH)

Examples:
- 600s ÷ 5s = 120 shots (10 minutes)
- 300s ÷ 5s = 60 shots (5 minutes)
- 120s ÷ 5s = 24 shots (2 minutes)
- 60s ÷ 3s = 20 shots (1 minute, faster shots)
```
