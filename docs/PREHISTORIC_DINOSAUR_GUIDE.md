# Prehistoric Dinosaur Documentary Agents

## Overview

The Prehistoric Dinosaur agents create IMAX-scale, Netflix-quality prehistoric documentaries featuring photorealistic dinosaurs shot on Sony Venice 2 with Arri Signature Prime lenses. Perfect for YouTube channels focused on dinosaurs, paleontology, and natural history content.

## Agents

### Story Agent: `prehistoric_dinosaur`
- **Location**: `agents/story/prehistoric_dinosaur.md`
- **Purpose**: Generates epic prehistoric dinosaur documentary narratives
- **Style**: IMAX scale, Netflix documentary, educational yet spectacular
- **Coverage**: Triassic, Jurassic, and Cretaceous periods

### Image Agent: `prehistoric_dinosaur`
- **Location**: `agents/image/prehistoric_dinosaur.md`
- **Purpose**: Creates breathtaking photorealistic dinosaur image prompts
- **Camera**: Sony Venice 2 (8K full-frame cinema camera)
- **Lenses**: Arri Signature Prime lenses (12mm-100mm)
- **Format**: 16:9 widescreen, YouTube/Netflix optimized

## Technical Specifications

### Camera System
- **Primary Camera**: Sony Venice 2
  - Full-frame 8K CMOS sensor
  - 16+ stops of dynamic range
  - Natural color science
  - Cinema-grade quality

- **Lens Package**: Arri Signature Prime
  - 12mm, 16mm (epic wide shots)
  - 21mm, 25mm (environmental shots)
  - 35mm, 50mm (action shots)
  - 75mm, 100mm (intimate portraits)

- **Output Format**: 16:9 widescreen, 8K resolution
- **Quality Standard**: Netflix 4K/8K quality
- **Platform**: YouTube optimized

## Usage

### Option 1: Set as Default in config.py

Edit `config.py`:
```python
# Line ~531
STORY_AGENT = "prehistoric_dinosaur"

# Line ~534
IMAGE_AGENT = "prehistoric_dinosaur"
```

### Option 2: Use On-Demand

When prompted for agent selection, specify:
- Story agent: `prehistoric_dinosaur`
- Image agent: `prehistoric_dinosaur`

## Supported Prehistoric Periods

### Triassic Period (252-201 million years ago)
- First dinosaurs
- Early, smaller species
- Pangaea supercontinent
- Arid environments
- Rise of archosaurs

### Jurassic Period (201-145 million years ago)
- Age of giant sauropods
- Large predators (Allosaurus)
- Lush fern forests
- Breakup of Pangaea
- First birds

### Cretaceous Period (145-66 million years ago)
- T-Rex, Triceratops, Velociraptor
- Flowering plants appear
- Diverse ecosystems
- Highest dinosaur diversity
- Ends with asteroid extinction

## Featured Dinosaurs

### Sauropods (Giant Herbivores)
- **Brachiosaurus**: 80+ feet tall, long neck, forest dweller
- **Argentinosaurus**: One of the largest land animals ever
- **Diplodocus**: Long, whip-like tail, herd animal
- **Camarasaurus**: Common Jurassic sauropod

### Theropods (Predators)
- **Tyrannosaurus Rex**: King of dinosaurs, Cretaceous apex predator
- **Spinosaurus**: Largest carnivorous dinosaur, semi-aquatic
- **Giganotosaurus**: South American giant predator
- **Allosaurus**: Jurassic apex predator
- **Velociraptor**: Small, fast, pack hunter
- **Carnotaurus**: Horned predator, fast runner

### Ceratopsians (Horned Dinosaurs)
- **Triceratops**: Three-horned, iconic Cretaceous herbivore
- **Styracosaurus**: Multiple horns, spectacular frill
- **Torosaurus**: Largest frill of all ceratopsians

### Others
- **Stegosaurus**: Plates and spikes, Jurassic herbivore
- **Ankylosaurus**: Armored tank dinosaur, club tail
- **Pterosaurs**: Flying reptiles (Pteranodon, Quetzalcoatlus)
- **Marine Reptiles**: Mosasaurus, Plesiosaurus, Elasmosaurus

## Example Prompts

Try these ideas with the prehistoric dinosaur agents:

### Epic Encounters
1. "T-Rex hunting Triceratops in Late Cretaceous forest"
2. "Massive Brachiosaurus herd migration across Jurassic plains"
3. "Velociraptor pack hunting strategy in Cretaceous wetlands"
4. "Spinosaurus hunting in prehistoric river system"

### Environmental Spectacles
5. "Dawn in the Jurassic - sunrise over ancient fern forest"
6. "Cretaceous swamp ecosystem - diverse dinosaur life"
7. "Triassic arid landscape - early dinosaurs struggling to survive"
8. "Late Cretaceous coastal plain - multiple species interaction"

### Behavioral Stories
9. "T-Rex family raising hatchlings in nest"
10. "Triceratops herd defending against predator attack"
11. "Sauropod nesting ground - hundreds of giant eggs"
12. "Dinosaur migration across prehistoric continent"

### Extinction Events
13. "K-Pg asteroid impact - day the dinosaurs died"
14. "Last days of the dinosaurs - prehistoric world ending"
15. "Post-apocalyptic landscape - immediate aftermath of impact"

### Special Themes
16. "Night in the Cretaceous - nocturnal dinosaur activity"
17. "Volcanic eruption during Jurassic period"
18. "Prehistoric flood - dinosaurs surviving natural disaster"
19. "Dinosaur courtship and mating rituals"
20. "Life of a dinosaur from egg to adult"

## Output Characteristics

### Story Output
- **IMAX Scale**: Epic descriptions emphasizing size and grandeur
- **Scientific Accuracy**: Real dinosaur names, behaviors, time periods
- **Narrative Arc**: Engaging stories with emotional investment
- **Netflix Quality**: Professional documentary narration style
- **Educational Value**: Paleontological facts woven into narrative
- **Cinematic Language**: Grand, sweeping phrases matching visual spectacle

### Image Output
- **Photorealistic**: Realistic dinosaurs based on current science
- **Sony Venice 2**: 8K resolution, cinema-grade quality
- **Arri Signature Prime**: Cinematic shallow depth of field, beautiful bokeh
- **IMAX Composition**: Epic wide shots, massive scale
- **Environmental Detail**: Lush prehistoric flora and landscapes
- **16:9 Widescreen**: YouTube/Netflix optimized format

## Shot Types

Each scene includes varied IMAX-scale shots:

1. **Epic Wide/Establishing**: Massive landscapes, herds to horizon
2. **Creature Close-Ups**: Detailed portraits, eye-level perspectives
3. **Herd Migration Shots**: Thousands of dinosaurs on the move
4. **Action Sequences**: Hunts, battles, dynamic moments
5. **Environmental Detail**: Prehistoric flora, atmospheric effects
6. **Intimate Behavior**: Parenting, social interactions, nesting

## Technical Prompt Elements

Every image prompt includes:
- "Shot on Sony Venice 2"
- "Arri Signature Prime lenses" (with focal length)
- "8K resolution"
- "16:9 widescreen format"
- "Netflix quality documentary"
- "Photorealistic"
- "IMAX scale"

## Sample Workflow

```bash
# 1. Set agents in config.py
STORY_AGENT="prehistoric_dinosaur"
IMAGE_AGENT="prehistoric_dinosaur"

# 2. Generate story
python generate_story.py "T-Rex family hunting and raising young in Late Cretaceous forest"

# 3. Generate shots with epic IMAX scale
python shot_planner.py

# 4. Generate photorealistic images
python generate_images.py

# 5. Render documentary-quality videos
python render_videos.py

# 6. Add narration
python generate_narration.py
```

## Video Structure

### Typical 8-Scene Documentary

**Scene 1**: Epic Establishing (7-8 shots)
- Wide shot of prehistoric landscape
- Environmental introduction
- Atmospheric beauty

**Scene 2**: Introduce Key Species (6-7 shots)
- Hero shots of main dinosaurs
- Size and scale emphasis
- Behavior introduction

**Scene 3**: Daily Life (6-7 shots)
- Feeding, social behavior
- Environmental interaction
- Herd dynamics

**Scene 4**: Build Tension (7-8 shots)
- Predator introduction
- Threat escalation
- Environmental challenges

**Scene 5**: Confrontation (8 shots)
- Epic action sequence
- Predator-prey dynamics
- Maximum spectacle

**Scene 6**: Aftermath (6-7 shots)
- Survival and consequence
- Natural balance
- Emotional resolution

**Scene 7**: Broader Context (6-7 shots)
- Ecosystem overview
- Multiple species
- Environmental richness

**Scene 8**: Reflection/Conclusion (7-8 shots)
- Scientific significance
- Connection to modern understanding
- Epic closing imagery

**Total**: ~55-60 shots for 8-minute documentary

## Tips for Best Results

1. **Be Specific with Time Periods**: Specify Cretaceous, Jurassic, or Triassic for accurate environments and species

2. **Include Multiple Species**: More complex ecosystems create richer visuals

3. **Emphasize Scale**: Use phrases like "massive herd," "towering predator," "stretches to horizon"

4. **Include Environmental Detail**: Mention time of day, weather, atmosphere for mood

5. **Balance Education and Entertainment**: Good dinosaur documentaries inform while spectacularizing

6. **Use Scientific Names**: T-Rex, Triceratops, Brachiosaurus - specific species generate better results

7. **Consider Action vs. Behavior**: Hunting scenes create drama, nesting scenes create emotion

8. **Think in IMAX Terms**: Always consider "How would this look on a giant screen?"

## Advanced Customization

### Modify Storytelling Style

Edit `agents/story/prehistoric_dinosaur.md`:
- Adjust narration tone (more scientific vs. more dramatic)
- Add custom dinosaur species
- Modify scene structure
- Include specific paleontological facts

### Modify Visual Style

Edit `agents/image/prehistoric_dinosaur.md`:
- Adjust camera settings and lens choices
- Customize lighting preferences
- Add specific environmental details
- Modify color palettes

## Camera Movement Recommendations

For epic dinosaur documentaries:
- **slow pan**: For establishing shots and landscapes
- **dolly**: For dramatic reveals and creature close-ups
- **drone**: For aerial herd shots and environmental sweeps
- **tracking**: For following hunting sequences
- **orbit**: For showcasing creature size and scale
- **static**: For intimate behavioral moments

## Quality Assurance Checklist

Before rendering final videos:
- ✅ All prompts include "Sony Venice 2" and "Arri Signature Prime"
- ✅ 16:9 aspect ratio maintained throughout
- ✅ IMAX scale composition emphasized
- ✅ Scientific accuracy in species and environments
- ✅ Varied shot types in each scene
- ✅ Epic, cinematic narration style
- ✅ Photorealistic quality keywords included

## Troubleshooting

**Issue**: Generated dinosaurs don't look realistic
- **Solution**: Verify `IMAGE_AGENT = "prehistoric_dinosaur"` is set

**Issue**: Shots lack IMAX scale feel
- **Solution**: Check that image prompts include "IMAX scale" and wide lens specs (12mm, 16mm)

**Issue**: Narration too formal/academic
- **Solution**: Ensure `STORY_AGENT = "prehistoric_dinosaur"` is configured correctly

**Issue**: Wrong time period environment
- **Solution**: Be specific about Triassic/Jurassic/Cretaceous in your prompt

**Issue**: All shots look similar
- **Solution**: The agent automatically varies lenses (12mm-100mm) and shot types

## YouTube Optimization

These agents are designed for YouTube success:
- **Engaging Openings**: Hook viewers in first 30 seconds
- **Spectacle**: Shareable IMAX-quality moments
- **Education**: Informative content that encourages watch time
- **Visual Variety**: Keeps viewers engaged throughout
- **Quality**: 8K, 16:9 format perfect for modern YouTube

## Netflix Style

Production values matching Netflix dinosaur documentaries:
- Blue Planet II cinematography
- Planet Earth scale and scope
- Walking with Dinosaurs photorealism
- Prehistoric Planet quality standards
- Apple TV's Prehistoric Planet visuals

## Next Steps

1. Create your first dinosaur documentary with a specific era and species
2. Experiment with different time periods (Triassic/Jurassic/Cretaceous)
3. Build series around different dinosaur groups (sauropods, theropods, etc.)
4. Add actual paleontological facts to enhance educational value
5. Consider creating multi-episode series for consistent audience

## Example Full Workflow

```bash
# Episode 1: The King - T-Rex Documentary
python generate_story.py "Life and times of Tyrannosaurus Rex - apex predator of Late Cretaceous, from hatchling to adult"

# Episode 2: The Giants - Sauropod Documentary
python generate_story.py "Brachiosaurus and Diplodocus - the largest animals to ever walk the Earth, Jurassic giants"

# Episode 3: The Hunt - Predator-Prey Dynamics
python generate_story.py "The eternal struggle - Velociraptor pack hunting strategies in Cretaceous period"
```

## Resources

- **Paleontology Reference**: Use current scientific sources for accurate species info
- **Dinosaur Database**: Natural History Museum, Smithsonian, etc.
- **Cinematography Inspiration**: BBC Planet Earth, Netflix Our Planet, Apple Prehistoric Planet

---

Create breathtaking dinosaur documentaries that rival major streaming network quality!
