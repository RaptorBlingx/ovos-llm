# 🐧 WSL2 Workflow Guide for OVOS Development

**Created:** 2025-11-27  
**Purpose:** Best practices for working with OVOS in WSL2 while maintaining Windows workspace  
**Status:** ✅ Recommended Setup

---

## 🎯 Key Concept: Files Are Synced!

**YES - Files are automatically synced!**

```
Windows Path:  D:\ovos-llm-core\ovos-llm\
WSL2 Path:     /mnt/d/ovos-llm-core/ovos-llm/
                     ↕️
              SAME FILES (real-time sync)
```

**What this means:**
- Editing `D:\ovos-llm-core\ovos-llm\README.md` in Windows VS Code
- Creates/updates `/mnt/d/ovos-llm-core/ovos-llm/README.md` in WSL2
- **Instantly visible in both** (no manual sync needed)

**Technical Details:**
- WSL2 mounts Windows drives under `/mnt/`
- Drive `D:` becomes `/mnt/d/`
- Files are NOT copied - they're the SAME files
- Changes are instant (same filesystem)

---

## ✅ Recommended Workflow (Single VS Code Window)

**RECOMMENDED:** Keep using your current VS Code window at `D:\ovos-llm-core`

### Why This Works Best:

1. **All your files are accessible from both sides:**
   - Edit code in Windows VS Code (native performance)
   - Run OVOS commands in WSL2 terminal (Linux environment)
   - No context switching between windows

2. **VS Code WSL Terminal Integration:**
   - Click `+` → Select "wsl" terminal type
   - Terminal runs Linux bash, files visible at `/mnt/d/...`
   - Can have multiple terminals: PowerShell (Windows) + WSL2 (Linux)

3. **Best of Both Worlds:**
   - Windows: Fast UI, native VS Code, familiar file paths
   - WSL2: Full Linux, OVOS compatibility, audio support via WSLg

---

## 📁 Current Setup Analysis

**Your Current State:**
```
VS Code Window: D:\ovos-llm-core (Workspace root)
Terminals Available:
  1. cmd (Windows)
  2. PowerShell Extension (Windows)
  3. wsl (Linux/Ubuntu) ✅ PERFECT
```

**WSL2 Current Directory:**
```bash
raptorblingx@RAPTORBLINGX:/mnt/d/ovos-llm-core/ovos-llm$
```

**This is CORRECT!** You're already in the right place.

---

## 🛠️ Recommended VS Code Configuration

### Terminal Setup (Current Window)

**Keep 3 terminal types for different tasks:**

1. **PowerShell (Windows)** - For Windows commands
   ```powershell
   # Example: Windows-specific tasks
   pip list  # Windows Python environment
   python scripts\test_skill_chat.py  # Standalone testing
   ```

2. **WSL2 (Linux)** - For OVOS installation and running ✅
   ```bash
   # Example: OVOS commands
   sudo apt update
   pip install ovos-core
   ovos-messagebus run
   ```

3. **cmd (Optional)** - Legacy Windows commands

### How to Add WSL2 Terminal in VS Code:

✅ **You already have it!** (I see "Terminal: wsl" in your setup)

**To add more WSL2 terminals:**
1. Click `+` dropdown next to terminal tabs
2. Select "wsl"
3. Or press `` Ctrl+Shift+` `` → Select "wsl" profile

---

## 🎯 File Path Translation (Cheat Sheet)

| Windows Path | WSL2 Path | Notes |
|-------------|-----------|-------|
| `D:\ovos-llm-core\ovos-llm\` | `/mnt/d/ovos-llm-core/ovos-llm/` | Project root |
| `D:\ovos-llm-core\ovos-llm\enms-ovos-skill\` | `/mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill/` | Skill directory |
| `C:\Users\YourUser\` | `/mnt/c/Users/YourUser/` | Windows user home |
| `~` (in WSL2) | `/home/raptorblingx/` | WSL2 user home ⚠️ DIFFERENT |

**⚠️ IMPORTANT:** WSL2 has its OWN home directory separate from Windows:
- Windows home: `C:\Users\RaptorBlingx\`
- WSL2 home: `/home/raptorblingx/` (NOT mounted from Windows)

---

## 🚀 OVOS Development Workflow (Step-by-Step)

### Planning Phase (Current) ✅

**Where:** Current VS Code window (`D:\ovos-llm-core`)  
**Terminal:** PowerShell OR WSL2 (either works for planning)

**Tasks:**
- ✅ Review documentation (OVOS_CORE_INTEGRATION_PLAN.md)
- ✅ Test standalone: `python scripts/test_skill_chat.py` (Windows Python)
- ✅ Prepare code changes (comment out @intent_handlers)

### Installation Phase (Next)

**Where:** Current VS Code window (SAME window)  
**Terminal:** WSL2 terminal ✅ (Linux required for OVOS)

**Commands (all in WSL2 terminal):**
```bash
# Navigate to project (if not already there)
cd /mnt/d/ovos-llm-core/ovos-llm

# Update Ubuntu packages
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv portaudio19-dev pulseaudio

# Create OVOS virtual environment (in WSL2 home)
cd ~
python3 -m venv ovos-env
source ovos-env/bin/activate

# Install OVOS components
pip install ovos-messagebus
pip install ovos-core[mycroft]
pip install ovos-audio[extras]
pip install ovos-dinkum-listener[extras]

# Install skill (navigate back to project)
cd /mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill
pip install -e .
```

### Configuration Phase

**Where:** Current VS Code window  
**Edit:** Use VS Code editor (Windows side is faster)  
**Create:** `~/.config/mycroft/mycroft.conf` in WSL2

**Two options for creating config:**

**Option A: Edit in VS Code (Recommended)**
```bash
# In WSL2 terminal, create directory
mkdir -p ~/.config/mycroft

# Get full path
echo ~/.config/mycroft/mycroft.conf
# Output: /home/raptorblingx/.config/mycroft/mycroft.conf
```

Then in VS Code:
- Open file: `/home/raptorblingx/.config/mycroft/mycroft.conf` (via WSL2 path)
- Or use command: `code ~/.config/mycroft/mycroft.conf` from WSL2 terminal

**Option B: Use nano in WSL2 terminal**
```bash
nano ~/.config/mycroft/mycroft.conf
# Paste config, save with Ctrl+O, exit with Ctrl+X
```

### Running OVOS (4 Terminals)

**Where:** Current VS Code window  
**Terminal Type:** WSL2 (all 4 terminals)

**Setup:**
```
VS Code Window Layout:
┌─────────────────────────────────────────┐
│  Editor: __init__.py (editing code)     │
├─────────────────────────────────────────┤
│  Terminal 1 (WSL2): ovos-messagebus     │
│  Terminal 2 (WSL2): ovos-core           │
│  Terminal 3 (WSL2): ovos-audio          │
│  Terminal 4 (WSL2): ovos-dinkum-listener│
└─────────────────────────────────────────┘
```

**Commands (one per terminal):**
```bash
# Terminal 1 (WSL2)
source ~/ovos-env/bin/activate
ovos-messagebus run

# Terminal 2 (WSL2)
source ~/ovos-env/bin/activate
ovos-core

# Terminal 3 (WSL2)
source ~/ovos-env/bin/activate
ovos-audio

# Terminal 4 (WSL2)
source ~/ovos-env/bin/activate
ovos-dinkum-listener
```

### Testing Phase

**Text Testing (WSL2 terminal):**
```bash
source ~/ovos-env/bin/activate
ovos-cli-client send "recognizer_loop:utterance" '{"utterances": ["factory overview"]}'
```

**Voice Testing (Microphone on Windows):**
- Say "Hey Mycroft" (WSLg forwards audio to WSL2)
- Say "Factory overview"
- Hear response through Windows speakers (WSLg)

---

## 🔍 VS Code Settings for WSL2 Integration

### Remote - WSL Extension (Optional, NOT Required)

**You DON'T need this for your workflow!**

The "Remote - WSL" extension is for opening VS Code INSIDE WSL2 (separate window). You're using the better approach: accessing WSL2 from Windows VS Code terminal.

**When to use Remote - WSL:**
- Large project entirely in `/home/raptorblingx/` (not `/mnt/`)
- Better performance for Linux-native projects
- Full Linux environment in VS Code

**When NOT to use it (your case):**
- Project on Windows drive (`D:\`)
- Editing files frequently in Windows tools
- Running mixed Windows/Linux commands

---

## ⚠️ Common Pitfalls & Solutions

### Pitfall 1: Virtual Environments Confusion

**Problem:** Two Python environments (Windows + WSL2)

**Solution:** Keep them separate
```
Windows Python:
  Location: C:\Users\RaptorBlingx\AppData\Local\Programs\Python\
  Venv: D:\ovos-llm-core\ovos-llm\enms-ovos-skill\venv\ (if exists)
  Use for: Standalone testing (test_skill_chat.py)

WSL2 Python:
  Location: /usr/bin/python3
  Venv: /home/raptorblingx/ovos-env/
  Use for: OVOS installation and running
```

**Rule:** Activate the RIGHT venv in the RIGHT terminal type:
- PowerShell → `.\venv\Scripts\activate` (Windows)
- WSL2 → `source ~/ovos-env/bin/activate` (Linux)

### Pitfall 2: File Permission Issues

**Problem:** WSL2 can't execute Windows files with `rwxrwxrwx` permissions

**Solution:**
```bash
# DON'T store Python venv in /mnt/ (Windows drives)
# Good: ~/ovos-env (WSL2 home)
# Bad: /mnt/d/ovos-llm-core/ovos-env (Windows drive)

# Keep code in /mnt/d/... (can read/write, just not execute from venv)
```

### Pitfall 3: Line Endings (CRLF vs LF)

**Problem:** Git changes line endings, breaks bash scripts in WSL2

**Solution:** Configure Git for cross-platform
```bash
# In WSL2 terminal
git config --global core.autocrlf input

# In PowerShell
git config --global core.autocrlf true
```

### Pitfall 4: Slow File Access

**Problem:** Files in `/mnt/d/` are slower than native Linux filesystem

**Impact:**
- Code editing: NO IMPACT (you edit in Windows VS Code)
- Python imports: MINIMAL IMPACT (~5-10% slower)
- OVOS runtime: NO IMPACT (runs from WSL2 venv)

**When to worry:** Only if you notice significant slowness (unlikely)

**Solution:** Move ONLY performance-critical parts to WSL2 home
```bash
# Keep in /mnt/d/ (current setup - GOOD):
- Source code (enms-ovos-skill/)
- Documentation
- Git repository

# Keep in ~/  (WSL2 home):
- Virtual environment (ovos-env/)
- OVOS config (~/.config/mycroft/)
- Downloaded models (if large)
```

---

## 📊 Comparison: Workflow Options

| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **Current Setup (Single Window, WSL2 Terminal)** | ✅ Files on Windows drive (visible in Explorer)<br>✅ Fast VS Code editing<br>✅ Access WSL2 via terminal<br>✅ No context switching | ⚠️ Slightly slower file I/O in WSL2 (negligible) | ⭐ **RECOMMENDED** |
| **Remote - WSL Extension (Separate Window)** | ✅ Faster file I/O in WSL2<br>✅ Full Linux environment in VS Code | ❌ Files in `/home/`, not visible in Windows Explorer<br>❌ Need to switch between VS Code windows<br>❌ Git confusion (two checkouts) | ❌ NOT for your use case |
| **Copy Project to WSL2 Home** | ✅ Best Linux performance | ❌ Files not synced with Windows<br>❌ Manual copying needed<br>❌ Git conflicts | ❌ NOT recommended |

---

## 🎯 Final Recommendation

**✅ KEEP YOUR CURRENT SETUP:**

```
VS Code Window: D:\ovos-llm-core (open now)
Terminals:
  - PowerShell: For Windows tasks, standalone testing
  - WSL2: For OVOS installation, running, Linux commands

Project Location: D:\ovos-llm-core\ovos-llm\
WSL2 Access: /mnt/d/ovos-llm-core/ovos-llm/
OVOS Venv: /home/raptorblingx/ovos-env/ (will create)
OVOS Config: /home/raptorblingx/.config/mycroft/
```

**Workflow:**
1. ✅ **Edit code** → VS Code editor (Windows side, current window)
2. ✅ **Install OVOS** → WSL2 terminal (in current window)
3. ✅ **Run OVOS** → WSL2 terminals (4 tabs in current window)
4. ✅ **Test voice** → WSL2 terminal + Windows microphone (WSLg handles audio)
5. ✅ **Commit changes** → PowerShell OR WSL2 (both see same Git repo)

**DO NOT:**
- ❌ Open new VS Code window in WSL2 mode
- ❌ Copy project to `/home/raptorblingx/`
- ❌ Install OVOS in Windows PowerShell (won't work well)

---

## 🔧 Quick Commands Reference

### Navigation

```bash
# WSL2 Terminal: Go to project
cd /mnt/d/ovos-llm-core/ovos-llm

# PowerShell: Go to project
cd D:\ovos-llm-core\ovos-llm
```

### Activate Virtual Environments

```bash
# WSL2: Activate OVOS venv
source ~/ovos-env/bin/activate

# PowerShell: Activate Windows venv (if exists)
.\venv\Scripts\activate
```

### Check Which Environment

```bash
# WSL2:
which python  # Should show: /home/raptorblingx/ovos-env/bin/python
pwd           # Shows: /mnt/d/ovos-llm-core/ovos-llm

# PowerShell:
where.exe python  # Shows Windows Python path
pwd               # Shows: D:\ovos-llm-core\ovos-llm
```

### Open Files in VS Code

```bash
# From WSL2 terminal (opens in current VS Code window):
code /mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill/__init__.py

# From PowerShell:
code D:\ovos-llm-core\ovos-llm\enms-ovos-skill\__init__.py
```

---

## 📚 Next Steps (From Planning to Implementation)

### Phase 1: Verify Current Setup ✅
- [x] WSL2 installed and accessible
- [x] WSL2 terminal working in VS Code
- [x] Write access confirmed (`/mnt/d/` is writable)
- [x] File sync verified (same files in both)

### Phase 2: Update Integration Plan
- [ ] Update `OVOS_CORE_INTEGRATION_PLAN.md` with WSL2-specific instructions
- [ ] Add WSL2 paths to installation commands
- [ ] Clarify virtual environment locations

### Phase 3: Pre-Installation Checklist
- [ ] Test standalone skill one last time (PowerShell)
- [ ] Comment out `@intent_handler` decorators in `__init__.py`
- [ ] Commit current working state to Git
- [ ] Create new branch for OVOS integration

### Phase 4: OVOS Installation (WSL2 Terminal)
- [ ] Install Ubuntu packages: `sudo apt install python3-pip portaudio19-dev pulseaudio`
- [ ] Create venv in WSL2 home: `python3 -m venv ~/ovos-env`
- [ ] Install OVOS components
- [ ] Install skill: `pip install -e /mnt/d/ovos-llm-core/ovos-llm/enms-ovos-skill`

### Phase 5: Testing
- [ ] Start OVOS services (4 WSL2 terminals)
- [ ] Test text input with `ovos-cli-client`
- [ ] Test voice input (Hey Mycroft → query)
- [ ] Verify responses match standalone

---

**Last Updated:** 2025-11-27  
**Author:** GitHub Copilot  
**Status:** ✅ Ready for OVOS Installation in WSL2
