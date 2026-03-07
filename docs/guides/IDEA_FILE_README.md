# Loading Video Ideas from Text Files

## Overview

The AI Video Factory supports loading video ideas from text files, providing convenient ways to manage and reuse your video concepts.

## Usage Methods

### Method 1: Command Line (Inline)

Provide your idea directly as a command-line argument:

```bash
python core/main.py --idea "A cat dancing in the rain"
```

**Best for:** Quick tests, short ideas, one-time videos

### Method 2: Default File

Create a file at `input/video_idea.txt`:

```bash
# Create the file
echo "Your video idea here" > input/video_idea.txt

# Run pipeline (automatically loads from file)
python core/main.py
```

**Best for:** Regular workflow, default ideas, quick runs without arguments

### Method 3: Custom File

Use the `--idea-file` or `-f` argument to specify any text file:

```bash
# Load from custom path
python core/main.py --idea-file my_ideas/nature_doc.txt

# Short form
python core/main.py -f ideas/sci_fi_video.txt
```

**Best for:** Multiple idea files, organized projects, sharing ideas between team members

## Priority Order

The system tries methods in this order:

1. **Command line `--idea`** - If provided, uses this (highest priority)
2. **Custom file `--idea-file`** - If provided, reads from specified path
3. **Default file** - Reads from `input/video_idea.txt` (lowest priority)

## File Format

Idea files can be:

- **Plain text (.txt)** - Simple text content
- **Markdown (.md)** - Text with optional formatting
- **Any text format** - Only the text content is used

**Important:** Use UTF-8 encoding

## File Locations

### Default Location
```
input/video_idea.txt
```

### Example Custom Locations
```
ideas/nature_documentary.txt
ideas/sci_fi_video.txt
my_project/concept.txt
```

## Example Idea Files

### Simple Idea (video_idea.txt)
```
A majestic eagle soars through mountain mist at sunrise, hunting for prey in a golden valley below.
Cinematic wildlife documentary with sweeping aerial views.
```

### Detailed Idea (ideas/nature_doc.md)
```
# Nature Documentary - Mountain Wildlife

## Video Concept
Create a cinematic wildlife documentary showing eagles hunting in mountain valleys.

## Style
- Cinematic aerial views
- Golden hour lighting
- Slow-motion capture
- National Geographic style narration

## Key Scenes
1. Eagle soars through mist at sunrise
2. Hunting dive into valley
3. Return to nest with prey
```

### Multiple Ideas (ideas/playlist.txt)
```
Video 1: A dragon flying over castle
Video 2: Underwater coral reef documentary
Video 3: Time-lapse flower blooming
```

## Features

### Logging Support

All file operations are logged:
```
2026-02-14 17:22:50 | INFO | Reading idea from default file: input/video_idea.txt
2026-02-14 17:22:50 | INFO |   Loaded 147 characters from input/video_idea.txt
```

### Error Handling

Clear error messages when files don't exist:
```
[ERROR] Idea file not found: nonexistent.txt
[HINT] Create the file or use --idea 'your idea here'
```

### UTF-8 Support

Reads ideas in any language (UTF-8 encoding):
```
# Chinese example
一只雄伟的老鹰在日出时飞越山雾

# Japanese example
日の出時に山の中を飛ぶ鷲

# Arabic example
نسر محلق عبر ضباب الجبل
```

## Best Practices

### 1. Organize Ideas by Category
```
ideas/
├── nature/
│   ├── wildlife.txt
│   └── landscapes.txt
├── sci-fi/
│   ├── space.txt
│   └── robots.txt
└── documentary/
    ├── history.txt
    └── science.txt
```

### 2. Use Descriptive Filenames
```
❌ idea.txt
✅ wildlife_eagle_hunting.txt
✅ nature_mountain_valley_drone.txt
```

### 3. Include Context in File
```
# Video: Mountain Wildlife Documentary
# Style: Cinematic nature
# Duration target: 60 seconds
# Shot count: 5-8 shots

A majestic eagle soars through mountain mist...
```

### 4. Version Control for Ideas
Track your ideas in Git:
```bash
git add ideas/my_project.txt
git commit -m "Add initial concept for wildlife documentary"
```

### 5. Template Files
Create reusable templates:
```
# Template: Wildlife Documentary
Location: [SET LOCATION]
Time of day: [sunrise/sunset/noon]
Weather: [clear/rain/fog]
Subject: [animal name]
Action: [behavior description]

[REPLACE WITH ACTUAL IDEA]
```

## Example Workflow

### Daily Content Creation
```bash
# 1. Morning - Create 3 new idea files
echo "Idea 1" > ideas/monday_1.txt
echo "Idea 2" > ideas/monday_2.txt
echo "Idea 3" > ideas/monday_3.txt

# 2. Generate videos for each idea
for idea in ideas/monday_*.txt; do
  python core/main.py --idea-file "$idea"
done
```

### Team Collaboration
```bash
# Team member A creates ideas
vim ideas/team/concept_001.txt
git commit -am "Author: Alice - New concept"

# Team member B generates video
python core/main.py -f ideas/team/concept_001.txt
git commit -am "Author: Bob - Generated video"
```

### Batch Processing
```bash
# Generate videos for all ideas in a folder
for file in ideas/nature/*.txt; do
  python core/main.py --idea-file "$file" --max-shots 3
done
```

## Integration with Other Tools

### With Text Editors
- **VS Code:** Open folder, edit ideas, run from terminal
- **Notion/Obsidian:** Write ideas, export to text, generate video
- **Google Docs:** Download as .txt, use as input

### With AI Tools
- **ChatGPT/Claude:** Generate idea, save to file, process
- **Script Tools:** Write scripts, save as ideas
- **Brainstorming Apps:** Export concepts as text

### With Build Systems
```bash
# Makefile example
.PHONY: all videos clean

VIDEOS := $(wildcard ideas/*.txt)

all: $(VIDEOS:ideas/%.txt=output/%.mp4)
	@for file in $^; do \
		python core/main.py --idea-file "$file"; \
	done

clean:
	rm -rf output/sessions/
```

## Troubleshooting

### File Not Found
```bash
# Check file exists
ls -la input/video_idea.txt

# Check encoding
file input/video_idea.txt

# Verify path (use absolute path if needed)
python core/main.py --idea-file /full/path/to/idea.txt
```

### Encoding Issues
```bash
# Convert to UTF-8
iconv -f ISO-8859-1 -t UTF-8 input.txt > output.txt

# Or use Python
python -c "open('out.txt', 'w', encoding='utf-8').write(open('in.txt').read())"
```

### Empty Files
```bash
# Check file has content
wc -l input/video_idea.txt
cat input/video_idea.txt

# Should return non-zero line count and show text
```

## Advanced Usage

### Dynamic Idea Selection
```bash
# Interactive selection
select file in ideas/*.txt; do
  echo "Generate video for: $file?"
  select yn in "Yes" "No"; do
    case $yn in
      Yes) python core/main.py --idea-file "$file"; break ;;
      No) break ;;
    esac
  done
done
```

### Idea Templates with Variables
```bash
# Template file
cat > template.txt <<EOF
Video: [VIDEO_TYPE]
Location: [LOCATION]
Style: [STYLE]

[DESCRIPTION]
EOF

# Use with sed
sed -e 's/\[VIDEO_TYPE\]/Documentary/' \
    -e 's/\[LOCATION\]/Mountain/' \
    -e 's/\[STYLE\]/Cinematic/' \
    -e 's/\[DESCRIPTION\]/An eagle soars/' \
    template.txt > final_idea.txt
```

### Integration with Spreadsheets
```bash
# Export column from CSV/Excel to text files
awk -F, 'NR>1 {print $1 > "ideas/"$1".txt}' videos.csv

# Then batch process
for idea in ideas/*.txt; do
  python core/main.py --idea-file "$idea"
done
```

## See Also

- `LOGGING_README.md` - Understanding log files
- `README.md` - General project documentation
- `config.py` - Configuration options

## Command Reference

```bash
# Load from inline argument
python core/main.py --idea "your idea here"

# Load from default file
python core/main.py

# Load from custom file
python core/main.py --idea-file path/to/idea.txt

# Short form
python core/main.py -f path/to/idea.txt
```
