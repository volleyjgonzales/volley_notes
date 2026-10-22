# Lenovo Legion Pro 7 16IAX10H on Ubuntu 24.04: Fixes and Lessons Learned

**Machine:** Lenovo Legion Pro 7 16IAX10H (product 83F5), Intel Core Ultra, NVIDIA RTX 5080 Laptop GPU
**OS:** Ubuntu 24.04 LTS, HWE kernel 7.0.0-38-generic, X11 session
**NVIDIA driver:** nvidia-driver-595-open (595.99.02)

---

## 1. Chrome: "WebGL not available" in Google Meet

### Symptom
Google Meet reported WebGL unavailable. `chrome://gpu` showed WebGL disabled and the GPU vendor as `0x0000`.

### Root cause
Chrome's GPU process crashed four times in a short window (`GL_GUILTY_CONTEXT_RESET`, context lost). After repeated GPU crashes, Chrome **disables hardware acceleration for the rest of that browser session**. The browser had been running since the previous day, so it stayed stuck in software mode. The resets themselves are typical of the NVIDIA driver losing state, often after suspend/resume.

### Fix
1. Fully quit Chrome (closing the window isn't enough if background apps are enabled):
   ```bash
   pkill -f chrome
   ```
2. Reopen Chrome and confirm `chrome://gpu` shows WebGL as "Hardware accelerated".

### Prevention (if crashes follow sleep/lid-close)
Have the NVIDIA driver preserve video memory across suspend:
```bash
sudo systemctl enable nvidia-suspend nvidia-resume nvidia-hibernate
echo 'options nvidia NVreg_PreserveVideoMemoryAllocations=1' | sudo tee /etc/modprobe.d/nvidia-power.conf
sudo update-initramfs -u
```
Reboot afterward.

### General diagnostic path for WebGL issues
`chrome://gpu` → check "Problems Detected" → confirm hardware acceleration is on in `chrome://settings/system` → check the NVIDIA driver (`nvidia-smi`) and PRIME mode (`prime-select query`) → clear Chrome GPU caches if needed.

---

## 2. Wayland vs. X11

- Switching display servers would **not** have fixed the WebGL issue; that was driver resets, not the session type.
- **X11:** historically the safer choice for Chrome GPU acceleration, screen sharing and video calls on NVIDIA hybrid laptops.
- **Wayland:** the long-term direction for GNOME/Ubuntu, with better fractional scaling and smoother high-refresh displays. NVIDIA support is good on drivers 555+.
- Chrome was launched with `--ozone-platform=x11`. If you move to Wayland, remove that flag or set `chrome://flags` → "Preferred Ozone platform" to Auto. Switching back is just a choice at the login screen.

---

## 3. Internal speakers sound thin, quiet and tinny

### Symptom
Speakers sounded tinny with no bass. Headphones and HDMI audio were fine.

### Diagnosis
```bash
cat /proc/asound/card*/codec* | grep -i codec      # Realtek ALC287 (actually an ALC3306)
sudo dmesg | grep -i -E "aw88399|snd_hda"           # no amplifier driver loading
cat /sys/class/dmi/id/product_version               # Legion Pro 7 16IAX10H
```

### Root cause
The 16IAX10H drives its **woofers through two Awinic AW88399 smart amplifiers** connected over I2C. Kernels before 7.3 have no HDA side-codec driver for these amps, so only the tweeters play. This is a driver problem, not a hardware fault.

- Upstream fix: merged into Linux **7.3**. On 7.3+ you only need the `aw88399_acf.bin` firmware in `/lib/firmware`.
- Until then: build a kernel with the community patch from [nadimkobeissi/16iax10h-linux-sound-saga](https://github.com/nadimkobeissi/16iax10h-linux-sound-saga).
- Not used: the DKMS-only variant. It requires `snd_intel_dspcfg.dsp_driver=3`, which can disable the internal mic with Ubuntu 24.04's older `alsa-ucm-conf`.

### Issues hit along the way (all avoided in the clean workflow below)
| Problem | Cause | Avoidance |
|---|---|---|
| Custom kernel would lack an NVIDIA driver | Only Ubuntu's prebuilt `linux-modules-nvidia-*` was installed (tied to Ubuntu kernels) | Install `nvidia-dkms-<ver>-open` first |
| `dkms status` "Diff between built and installed module" warning | Prebuilt and DKMS copies both exist for the stock kernel | Harmless; ignore |
| Patch file not found | Patch is named for an exact point release (e.g. 7.2.9) | List `fix/patches/` first, download the matching kernel |
| `Unmet build dependencies: libdw-dev` | Missing package | Included in the dependency list |
| `gawk: not found` late in the build | Ubuntu ships mawk by default | Included in the dependency list |
| `symbol value 'm' invalid` config warnings | Ubuntu-only tristate options don't exist in mainline | Harmless; `make olddefconfig` corrects them |
| Build ran into working hours | Ubuntu config builds thousands of modules | Run with `nice -n 19` or overnight; `make` resumes where it stopped |
| "modules won't be signed" during install | Secure Boot is off, so signing is irrelevant | Harmless |

---

## 4. Clean workflow: audio fix via patched kernel (Ubuntu 24.04)

Your stock kernel stays installed the whole time. Rollback is choosing it from the boot menu.

### Step 0: Pre-flight
```bash
cat /sys/class/dmi/id/product_version        # must be: Legion Pro 7 16IAX10H
mokutil --sb-state                           # must be: SecureBoot disabled (otherwise disable in BIOS, F2)
dpkg -l | grep nvidia-driver-                # note your driver series, e.g. 595-open
df -h ~                                      # need ~30 GB free
```

### Step 1: NVIDIA DKMS + build dependencies
```bash
sudo apt install nvidia-dkms-595-open        # match your driver series and version exactly
dkms status                                  # nvidia ... installed (diff warning is OK)

sudo apt install build-essential libncurses-dev bison flex libssl-dev libelf-dev libdw-dev \
  bc dwarves debhelper rsync git curl zstd cpio kmod gawk
```
Before confirming any `apt install`, check that it says **0 to remove**.

### Step 2: Source, patch and firmware
```bash
mkdir -p ~/legion-kernel && cd ~/legion-kernel
git clone https://github.com/nadimkobeissi/16iax10h-linux-sound-saga.git
ls 16iax10h-linux-sound-saga/fix/patches/    # find 16iax10h-audio-linux-X.Y.Z.patch

KVER=7.2.9                                   # set to the version in the patch filename
curl -LO https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-$KVER.tar.xz
tar xf linux-$KVER.tar.xz && cd linux-$KVER
patch -p1 < ../16iax10h-linux-sound-saga/fix/patches/16iax10h-audio-linux-$KVER.patch
# expect ~14 "patching file" lines and no "FAILED"

sudo cp ../16iax10h-linux-sound-saga/fix/firmware/aw88399_acf.bin /lib/firmware/
```
Ignore `afr10-*.patch`; that's for the AMD model.

### Step 3: Configure
```bash
cp /boot/config-$(uname -r) .config
echo "CONFIG_SND_HDA_SCODEC_AW88399=m"     >> .config
echo "CONFIG_SND_HDA_SCODEC_AW88399_I2C=m" >> .config
scripts/config --disable SYSTEM_TRUSTED_KEYS --disable SYSTEM_REVOCATION_KEYS
scripts/config --disable DEBUG_INFO --enable DEBUG_INFO_NONE
make olddefconfig
grep AW88399 .config                         # both SND_HDA_SCODEC_AW88399 lines must be =m
```

### Step 4: Build `.deb` packages (nothing is installed yet)
```bash
nice -n 19 make -j$(nproc) bindeb-pkg LOCALVERSION=-legion-audio 2>&1 | tee ~/legion-kernel/build.log
```
This takes 30+ minutes. If you stop it, rerun the same command and it resumes.

### Step 5: Verify the build
```bash
grep -nE "Error [0-9]|error:" ~/legion-kernel/build.log      # no output = clean
cd ~/legion-kernel && ls *.deb
dpkg-deb -c linux-image-*legion-audio_*_amd64.deb | grep -E "vmlinuz|aw88399"
```

### Step 6: Make the boot menu visible (rollback safety net)
```bash
sudo sed -i 's/^GRUB_TIMEOUT_STYLE=.*/GRUB_TIMEOUT_STYLE=menu/; s/^GRUB_TIMEOUT=.*/GRUB_TIMEOUT=5/' /etc/default/grub
grep -E "^GRUB_TIMEOUT" /etc/default/grub
```

### Step 7: Install only the image and headers
```bash
cd ~/legion-kernel
sudo apt install ./linux-image-*legion-audio_*_amd64.deb ./linux-headers-*legion-audio_*_amd64.deb
dkms status                                  # nvidia ... <KVER>-legion-audio ... installed
ls /boot/*legion-audio*                      # vmlinuz + initrd.img present
```
Do **not** install the `-dbg` or `linux-libc-dev` packages.

### Step 8: Reboot and verify
```bash
uname -r                                     # <KVER>-legion-audio
sudo dmesg | grep -i aw88399                 # both amps "registered" and "Bound", channels 0 and 1
nvidia-smi                                   # GPU visible
```
Play audio; full-range sound with bass confirms the fix.

**Note:** `nvidia-smi` may show an impossible idle power reading (e.g. 428 W / 80 W). This is a sensor reporting glitch and is cosmetic.

---

## 5. Rollback and maintenance

- **One-time fallback:** GRUB → *Advanced options for Ubuntu* → `7.0.0-xx-generic`.
- **Remove the custom kernel:**
  ```bash
  sudo apt remove linux-image-*legion-audio linux-headers-*legion-audio
  sudo update-grub
  ```
- **Cleanup:** delete `~/legion-kernel/linux-<KVER>` (~25 GB). Keep the `.deb` files and the saga repo.
- **Security:** this kernel gets no Ubuntu security updates. It's a bridge.
- **Exit plan:** when Ubuntu offers a 7.3+ kernel, switch to it (the driver is upstream there; the firmware is already installed) and remove the custom kernel.
