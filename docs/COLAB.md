# HydroVision: Google Colab Training & Dataset Guide

This guide describes how to export the generated hydrodynamic dataset from the local machine (`C:\hydrovision_data\data`), transfer it to Google Drive, and memory-map it on Google Colab for neural surrogate training.

---

## 1. Exporting and Zipping Local Dataset

The dataset generated on the real Copernicus GLO-30 Marathahalli DEM resides at `C:\hydrovision_data\data` (~814 MB uncompressed, float32).

### Option A: Using PowerShell (Built-in)
Run the following in PowerShell:
```powershell
Compress-Archive -Path "C:\hydrovision_data\data\*" -DestinationPath "$HOME\Downloads\hydrovision_data.zip" -CompressionLevel Optimal
```

### Option B: Using Python
```bash
python -c "import shutil; shutil.make_archive('hydrovision_data', 'zip', r'C:\hydrovision_data\data')"
```
This produces `hydrovision_data.zip` (~250-320 MB compressed).

---

## 2. Uploading to Google Drive

1. Open your browser and navigate to [Google Drive](https://drive.google.com).
2. Create or navigate to a folder, e.g. `HydroVision/`.
3. Upload `hydrovision_data.zip` to `My Drive/HydroVision/hydrovision_data.zip`.

---

## 3. Google Colab Setup & Extraction

In your Colab notebook (with GPU runtime, e.g., T4, A100, or V100):

```python
# Cell 1: Mount Google Drive
from google.colab import drive
drive.mount('/content/drive')
```

```bash
# Cell 2: Unzip to local Colab NVMe scratch disk (DO NOT read directly from Drive!)
!mkdir -p /content/data
!unzip -q "/content/drive/MyDrive/HydroVision/hydrovision_data.zip" -d /content/data
!ls -lh /content/data
```

> [!TIP]
> Always extract data to `/content/data` (Colab's local high-speed SSD). Reading directly from `/content/drive` causes major I/O bottlenecks during PyTorch training epochs.

---

## 4. Memory-Mapped Loading in PyTorch

Because each split was saved as uncompressed `.npy` arrays, you can use `mmap_mode='r'` to stream frames directly from disk into GPU memory without blowing through CPU RAM limits.

```python
import json
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader

class HydroMmapDataset(Dataset):
    """Zero-copy memory-mapped dataset for HydroVision flood forecasting."""

    def __init__(self, split_dir: str, horizon_steps: int = 120):
        super().__init__()
        self.split_dir = Path(split_dir)
        
        # Load arrays with zero-copy memory mapping
        self.depth = np.load(self.split_dir / "depth.npy", mmap_mode="r")        # [N, 121, 64, 64] float16
        self.rain = np.load(self.split_dir / "rain.npy", mmap_mode="r")          # [N, 120] float32
        self.drain_m3 = np.load(self.split_dir / "drain_m3.npy", mmap_mode="r")  # [N, 120] float32
        self.params = np.load(self.split_dir / "params.npy", mmap_mode="r")      # [N, 4] float32
        
        self.num_samples = self.depth.shape[0]

    def __len__(self) -> int:
        return self.num_samples

    def __getitem__(self, idx: int):
        # Slice only the requested sample into float32 torch tensors
        d = torch.from_numpy(self.depth[idx].astype(np.float32))    # [121, 64, 64]
        r = torch.from_numpy(self.rain[idx].astype(np.float32))      # [120]
        dr = torch.from_numpy(self.drain_m3[idx].astype(np.float32)) # [120]
        p = torch.from_numpy(self.params[idx].astype(np.float32))    # [4]
        return {"depth": d, "rain": r, "drain_m3": dr, "params": p}

# Example DataLoader
train_dataset = HydroMmapDataset("/content/data/train")
train_loader = DataLoader(
    train_dataset,
    batch_size=8,
    shuffle=True,
    num_workers=2,
    pin_memory=True
)

batch = next(iter(train_loader))
print("Loaded batch depth shape:", batch["depth"].shape)  # [8, 121, 64, 64]
print("Loaded batch rain shape:", batch["rain"].shape)    # [8, 120]
```

---

## 5. Dataset Architecture & Verification

The dataset structure in `/content/data/`:
```text
/content/data/
├── metadata.json
├── train/
│   ├── depth.npy        [280, 121, 64, 64] (float32)
│   ├── rain.npy         [280, 120]         (float32)
│   ├── drain_m3.npy     [280, 120]         (float32)
│   ├── params.npy       [280, 4]           (float32)
│   └── params.json
├── val/
│   ├── depth.npy        [60, 121, 64, 64]  (float32)
│   ├── rain.npy         [60, 120]          (float32)
│   ├── drain_m3.npy     [60, 120]          (float32)
│   ├── params.npy       [60, 4]            (float32)
│   └── params.json
├── test/
│   ├── depth.npy        [60, 121, 64, 64]  (float32)
│   ├── rain.npy         [60, 120]          (float32)
│   ├── drain_m3.npy     [60, 120]          (float32)
│   ├── params.npy       [60, 4]            (float32)
│   └── params.json
└── extrapolation/
    ├── depth.npy        [30, 121, 64, 64]  (float32)
    ├── rain.npy         [30, 120]          (float32)
    ├── drain_m3.npy     [30, 120]          (float32)
    ├── params.npy       [30, 4]            (float32)
    └── params.json
```
