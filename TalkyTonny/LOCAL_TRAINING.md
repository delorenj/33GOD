# Local OpenWakeWord Training

Train your "Hey Tonny" wake word model locally instead of using Google Colab.

## Prerequisites

- **mise**: For Python version management (`curl https://mise.run | sh`)
- **uv**: For Python package management (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **git-lfs**: For large file support (`sudo apt install git-lfs`)
- **GPU (optional)**: CUDA-capable GPU recommended; CPU training is very slow

## Quick Start

```bash
# Setup (one-time, ~5 minutes)
mise run setup-training

# Train (~30-60 min on GPU, hours on CPU)
mise run train
```

## Manual Steps

### 1. Setup Environment

```bash
./scripts/setup_local_training.sh
```

This script will:
- Verify iMi project registration
- Install Python 3.10 via mise
- Clone openWakeWord and piper-sample-generator
- Create a uv virtual environment
- Install all dependencies

### 2. Configure Training

Edit `training/hey_tonny.yaml`:

```yaml
model_name: "hey_tonny"
n_samples: 50000        # More samples = better accuracy
steps: 30000            # More steps = better convergence
layer_size: 32          # 32=default, 16=smaller/faster
```

### 3. Run Training

```bash
./scripts/train_local.sh
```

**Note**: First run downloads ~20GB of background noise datasets.

### 4. Deploy to Pi Zero

```bash
# Copy the trained model
scp training/openWakeWord/trained_models/hey_tonny.tflite \
    delorenj@tonny.local:/home/delorenj/custom_wakewords/

# Update satellite service
ssh delorenj@tonny.local
sudo nano /etc/systemd/system/wyoming-satellite.service
# Change: --wake-word-name 'ok_nabu'
# To:     --wake-word-name 'hey_tonny'

# Restart services
sudo systemctl restart wyoming-openwakeword wyoming-satellite
```

### 5. Test

```bash
ssh delorenj@tonny.local "journalctl -u wyoming-satellite -f"
```

Say "Hey Tonny" and watch for detection logs.

## Training Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `n_samples` | 50000 | Synthetic training samples |
| `n_samples_val` | 5000 | Validation samples |
| `steps` | 30000 | Training iterations |
| `batch_size` | 64 | Batch size (lower if OOM) |
| `learning_rate` | 0.001 | Optimizer learning rate |
| `layer_size` | 32 | Model size (16/32/64) |

## Troubleshooting

### Out of Memory

Reduce batch size in config:
```yaml
batch_size: 32  # or 16
```

### Slow Training

- Use a GPU (CUDA)
- Reduce samples/steps for testing:
  ```yaml
  n_samples: 10000
  steps: 5000
  ```

### Missing Dependencies

```bash
cd training/openWakeWord
source .venv/bin/activate
uv pip install -e ".[full]"
```

## Comparison: Local vs Colab

| Aspect | Local | Google Colab |
|--------|-------|--------------|
| Cost | Free (your hardware) | Free (T4 GPU) |
| Speed | Depends on GPU | ~30-60 min |
| Data Privacy | ✅ Local only | Uploaded to Google |
| Setup | One-time setup | None |
| Disk Space | ~25GB | N/A |

## File Structure

```
training/
├── hey_tonny.yaml          # Training configuration
├── openWakeWord/           # Cloned repo + venv
│   ├── .venv/              # Python environment
│   └── trained_models/     # Output .tflite files
└── piper-sample-generator/ # TTS for synthetic data
```

## See Also

- `TRAINING_GUIDE.txt` - Cloud-based training with Google Colab
- `record_samples.sh` - Record real voice samples
- https://github.com/dscripda/openWakeWord
