# agent-voice-soprano

Bloodbank consumer service that autoplays inbound agent messages using local `soprano`.

- Consumes: `agent.*.message.received`
- Queue: `services.agent.voice_soprano`
- Exchange: `bloodbank.events.v1`

## Why this exists

This makes agent responses feel physically present: every inbound message event can be voiced locally, with per-agent voice/model settings.

## Setup

```bash
cd ~/code/33GOD/services/agent-voice-soprano
uv sync
cp .env.example .env
cp voice-profiles.example.yaml voice-profiles.yaml
```

Then edit:
- `.env` for Rabbit/Soprano runtime config
- `voice-profiles.yaml` for per-agent model mappings

## Run

```bash
./run.sh
```

If your host has no CUDA/NVIDIA, keep `.env` at:

```bash
SOPRANO_EXTRA_ARGS="--device cpu"
```

## Smoke test (without speaking)

```bash
VOICE_DRY_RUN=true uv run agent-voice-soprano
```

Then publish a test event with routing key `agent.cack.message.received`.

## Voice profiles

Each agent can use a different Soprano model path once you train/export them.

```yaml
default:
  enabled: true
  mode: stream
  extra_args: "--device cpu"

agents:
  cack:
    model_path: "/models/soprano/cack-v1"
    text_prefix: "Cack says"
```

`text_prefix` is optional, useful while models are still similar.

## Next step for real unique voices

Train one Soprano model per agent using your `soprano-lab` Gradio app and set each `model_path` in `voice-profiles.yaml`.
