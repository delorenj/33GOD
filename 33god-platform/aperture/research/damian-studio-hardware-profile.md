# Damian Studio hardware profile — live readback

Observed UTC: 2026-10-23T18:03:48.838313+00:00
Method: read-only SSH to the already verified Mac Studio, BatchMode and StrictHostKeyChecking enabled, verified HostKeyAlias retained. Native macOS metadata plus allowlisted Docker fields only. No installation, image pull, configuration/resource changes, workload execution or restart.

## Measured facts

- Host: Damian Mac Studio, model Mac15,14.
- OS: macOS 26.3, build 25D125.
- CPU: Apple M3 Ultra; native host architecture arm64.
- Host unified memory: 103079215104 bytes = 96 GiB.
- GPU: integrated Apple M3 Ultra, 60 GPU cores, Metal 4. This is not an NVIDIA/CUDA device; Docker GPU acceleration is NOT proven by host GPU detection.
- Docker client/server: 29.8.2 / 29.8.2.
- Compose: v5.6.0.
- Docker daemon OS/architecture: linux / aarch64 (deployment platform linux/arm64).
- Docker VM: 24 CPUs, 8316473344 bytes memory = 7.745 GiB. This is the configured total, not unused headroom; it is much smaller than host memory.
- Docker storage driver: overlayfs; daemon data root /var/lib/docker (inside Docker VM).
- Host APFS shared capacity: 971350180 KiB = 926.35 GiB.
- Host available space at / and /Users/hellosubconscious: 614263760 KiB = 585.81 GiB. These are shared APFS space, not independent disks/free pools.

## G1 implications for Grolf, not changed defaults

- Target native linux/arm64 image manifests; verify each exact image/tag or digest actually supports it. Host facts do not prove all component images are multi-arch.
- Size resource proposals against Docker VM's 7.745 GiB shared budget, not the 96 GiB host RAM. Existing applications share that VM; G1 idle/load headroom has not been measured in this readback.
- No NVIDIA GPU assumption for G1. Future inference groups need an explicit external/CPU/macOS-native backend decision; do not assume CUDA containers can use the Apple GPU.
- Host free disk is measured. Docker Desktop virtual disk maximum/free capacity was NOT established; do not translate 585+ GiB host free into a promised container-storage budget.
- No resources adopted or created; Grolf's fresh-resource default stays untouched.

## Commands exercised

uname -m; sw_vers; sysctl -n hw.model hw.memsize machdep.cpu.brand_string (issued individually); df -k / /Users/hellosubconscious; system_profiler SPDisplaysDataType -detailLevel mini; /usr/local/bin/docker version with client/server version-only format; /usr/local/bin/docker compose version; /usr/local/bin/docker info with architecture/OS/CPU/memory/storage-driver/data-root-only format.

Live SSH returned exit 0 and empty stderr. An earlier terminal-wrapper call returned exit 255 without diagnostics; a bounded direct subprocess SSH retry produced the successful measurements above. No failure was treated as evidence of missing remote tooling.
