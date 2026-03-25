# Installing IP-Adapter Plus for Standalone ComfyUI

Your ComfyUI Installation: **Standalone/Portable Build** (E:\ComfyUI)

For standalone builds, you **must use ComfyUI Manager** to install custom nodes.

## Method 1: Via ComfyUI Manager UI (Recommended)

### Step 1: Open ComfyUI Manager

1. **Open ComfyUI** in your browser: http://127.0.0.1:8188

2. **Look for the Manager button**:
   - Location: Top-right corner of the screen
   - Icon: Usually a cube/box icon 📦 or says "Manager"
   - Click to open ComfyUI Manager

### Step 2: Install IP-Adapter Plus

1. In Manager, click **"Install Custom Nodes"** tab

2. **Search for IP-Adapter**:
   - In the search box, type: `IPAdapter`
   - Or scroll through the list

3. **Find**: `ComfyUI IPAdapter Plus` by **cubiq**

4. **Click "Install"** button

5. **Wait for installation**:
   - You'll see a progress bar
   - Takes about 1-2 minutes
   - Status will change to "Installed"

### Step 3: Restart ComfyUI

**IMPORTANT**: You must restart ComfyUI after installation!

1. **Close ComfyUI**:
   - Close the browser tab
   - Close the ComfyUI window/application

2. **Restart ComfyUI**:
   - Double-click: `ComfyUI.exe` or `run_nvidia_gpu.bat`
   - Wait for it to load
   - Navigate to: http://127.0.0.1:8188

### Step 4: Verify Installation

**Check if IPAdapter node is available:**

```bash
# Run this in your terminal/command prompt
curl -s http://127.0.0.1:8188/object_info > test.json
```

Then check if "IPAdapter" appears in the output, OR try:

1. Open ComfyUI in browser
2. Right-click on canvas → Add Node
3. Search for: `ipadapter`
4. You should see: **IPAdapter** in the list

### Step 5: Download IP-Adapter Model

**Still in ComfyUI Manager:**

1. Go to **"Install Models"** tab

2. Search for: `ipadapter`

3. Look for: **IP-Adapter for Flux** or **ipadapter_flux_sd3**

4. Click **"Install"**

**OR Manual Download:**

1. Visit: https://huggingface.co/h94/IP-Adapter/tree/main

2. Download: `ipadapter_flux_sd3.safetensors`

3. Create folder: `E:\ComfyUI\models\ipadapter\`

4. Move downloaded file to that folder

### Step 6: Test IP-Adapter

1. Open ComfyUI

2. Right-click canvas → Add Node

3. Search for: `IPAdapter`

4. **Expected result**: You should see the IPAdapter node

5. **Verify**: The node should load without errors

## Method 2: Manual Installation (If Manager Fails)

### Prerequisites
- Git installed on your system
- Or ability to download and extract ZIP files

### Option A: Using Git

```bash
# Navigate to ComfyUI directory
cd E:\ComfyUI

# Clone IP-Adapter Plus
git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git custom_nodes/ComfyUI_IPAdapter_plus

# Restart ComfyUI
```

### Option B: Download ZIP

1. **Download from GitHub**:
   - URL: https://github.com/cubiq/ComfyUI_IPAdapter_plus
   - Click "Code" → "Download ZIP"

2. **Extract**:
   - Extract ZIP file
   - Rename folder to: `ComfyUI_IPAdapter_plus`

3. **Move to ComfyUI**:
   - Create folder: `E:\ComfyUI\custom_nodes\`
   - Move extracted folder there

4. **Restart ComfyUI**

## Verification Commands

### Check if IPAdapter is Installed

```bash
# Check object_info for IPAdapter node
curl -s http://127.0.0.1:8188/object_info | findstr IPAdapter
```

**Expected**: Should see "IPAdapter" in the output

### Check Models Directory

```bash
# Check if IP-Adapter models folder exists
dir "E:\ComfyUI\models\ipadapter\"
```

**Expected**: Should list downloaded models

## Troubleshooting

### Issue: Manager Button Not Found

**Solutions**:
1. **Refresh the page** (F5)
2. **Check ComfyUI version** - Should be v0.16.3 or higher
3. **Alternative**: Use manual installation (Method 2)

### Issue: IPAdapter Not in Node List After Installation

**Solutions**:
1. **Did you restart ComfyUI?** - This is required!
2. **Check custom_nodes folder** exists
3. **Check for errors** in ComfyUI console window

### Issue: "Module not found" Error

**Solution**:
- Make sure you're using the correct branch of IP-Adapter Plus
- Check ComfyUI version compatibility
- Try reinstalling via Manager

### Issue: Manager Won't Install

**Solutions**:
1. **Check internet connection**
2. **Try manual installation** (Method 2)
3. **Run ComfyUI as administrator**

## After Installation Success

Once IP-Adapter Plus is installed:

1. ✅ IPAdapter node appears in node list
2. ✅ Download IP-Adapter model
3. ✅ Test workflows:
   - Load `flux_ipadapter_then.json`
   - Upload reference photo
   - Generate image

## Expected File Structure After Installation

```
E:\ComfyUI\
├── custom_nodes\
│   └── ComfyUI_IPAdapter_plus\        ← IP-Adapter Plus
│       ├── __init__.py
│       ├── nodes.py
│       └── ...
├── models\
│   ├── ipadapter\                      ← IP-Adapter models
│   │   └── ipadapter_flux_sd3.safetensors
│   ├── unet\                           ← Flux models
│   ├── clip\                           ← CLIP models
│   └── vae\                            ← VAE models
├── Input\
├── Output\
└── Temp\
```

## Quick Checklist

- [ ] ComfyUI Manager opened
- [ ] Searched for "IPAdapter Plus"
- [ ] Clicked Install
- [ ] Waited for installation to complete
- [ ] Restarted ComfyUI
- [ ] Verified IPAdapter node appears
- [ ] Downloaded IP-Adapter model
- [ ] Moved model to correct folder
- [ ] Tested IPAdapter node loads

## Success Criteria

You'll know it worked when:

1. ✅ **IPAdapter** appears in node search
2. ✅ IPAdapter node loads without errors
3. ✅ No "module not found" errors
4. ✅ IP-Adapter model loads successfully

## Next Steps After Installation

1. **Download IP-Adapter model** (if not done via Manager)
2. **Test THEN workflow** with reference photo
3. **Test NOW workflow** with reference photo
4. **Verify facial consistency** in generated images

---

## Need Help?

If ComfyUI Manager doesn't work or you encounter issues:

### Alternative: Use Full Python ComfyUI Installation

1. **Install Python 3.10+**
2. **Clone ComfyUI**:
   ```bash
   git clone https://github.com/comfyanonymous/ComfyUI
   cd ComfyUI
   ```
3. **Install requirements**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Install IP-Adapter**:
   ```bash
   cd custom_nodes
   git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus
   ```

This gives you full control and easier debugging.

---

**Estimated Time**: 5-10 minutes via Manager
**Difficulty**: Easy
**Required**: YES (for reference image feature)
