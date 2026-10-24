# Host-side boundary

## waxd is not a server container

waxd is a desktop daemon coupled to the user's graphical session and PipeWire.
Its existing systemd **user** unit starts after `pipewire.service`; capture,
hotkeys and desktop session behavior belong to that host. Deploy the existing
HeyMa Debian package from its `debian/` packaging with the host's normal package
management. This bundle neither rebuilds that package nor claims a portable
Linux/macOS desktop installation.

There is **no waxd service/image/stub** in G6. Running a keepalive process named
waxd would not implement capture. Passing the session bus, host socket and
sound devices into a container is not part of this artifact.

## Host → server seam

1. Host waxd captures actual audio using its installed host configuration.
2. The host's intake/sync policy transports completed WAV files. G6 can poll a
   configured S3-compatible bucket, or receive files in its pipeline inbox.
3. G6 verifies and lands bytes with a durable SHA-256 receipt. STT is available
   over the internal Whisper HTTP and Vinyl TCP APIs; automatic dispatch from
   the landed inbox to a workflow is a separate explicit integration.

Syncthing-audio is a host-policy poller/mounted directory, **not a service in
Compose**. An operator may mount a sync folder to `/pipeline/inbox` with a
private overlay, or copy completed files into `god-g6-pipeline`. UID 10001 must
have access. Write to `.partial` and atomically rename to `.wav` when complete.
There are no shipped host-specific paths or adopted desktop state.

## Scope of proof

CPU containers and local intake have real server-side proof. Existing live
voice/transcription services were left running. No desktop capture, Debian
install, microphone, host sync-policy change, driver install, or actual remote
S3 credentials were exercised by this bundle's smoke.
