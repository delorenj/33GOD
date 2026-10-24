#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
: "${GOD_PJANGLER_CONTEXT:=../../../../pjangler}"
: "${GOD_MCP_CONTEXT:=../../../../../skillex/mcp-servers/codegraph-voyage-mcp}"
: "${GOD_COMMONPROJECT_CONTEXT:=../../../../../CommonProject}"
: "${GOD_PJANGLER_IMAGE:=god-g5-pjangler:0.1}"
: "${GOD_SKILLEX_IMAGE:=god-g5-skillex:0.1}"
: "${GOD_MCP_IMAGE:=god-g5-mcp-codegraph:0.1}"
export GOD_PJANGLER_CONTEXT GOD_MCP_CONTEXT
export GOD_PJANGLER_IMAGE GOD_SKILLEX_IMAGE GOD_MCP_IMAGE
pj_context=$(CDPATH= cd -- "$GOD_PJANGLER_CONTEXT" && pwd)
mcp_context=$(CDPATH= cd -- "$GOD_MCP_CONTEXT" && pwd)
template=$(CDPATH= cd -- "$GOD_COMMONPROJECT_CONTEXT" && pwd)
bundle=$(pwd)
arch=$(docker version --format '{{.Server.Arch}}')
: "${GOD_PLATFORM:=linux/$arch}"
case "$GOD_PLATFORM" in linux/amd64|linux/arm64) ;; *) printf '%s\n' 'unsupported smoke platform' >&2; exit 1;; esac
printf '%s\n' "G5 native build: $GOD_PLATFORM"
docker buildx bake --print >/dev/null
printf '%s\n' 'Bake config: valid'
docker buildx bake --allow="fs.read=$pj_context" --allow="fs.read=$mcp_context"   --set "*.platform=$GOD_PLATFORM" --load --progress=plain
printf '%s\n' 'Build: 3 tool images loaded'
# Validate the full multi-architecture plan, not just the native override.
docker buildx bake --print | docker run --rm -i --network=none --entrypoint node "$GOD_SKILLEX_IMAGE" -e '
let data=""; process.stdin.on("data",c=>data+=c); process.stdin.on("end",()=>{
const p=JSON.parse(data); const names=Object.keys(p.target).sort();
if(JSON.stringify(names)!==JSON.stringify(["mcp-codegraph","pjangler","skillex"])) throw Error("targets");
for(const t of Object.values(p.target)) if(JSON.stringify(t.platforms)!==JSON.stringify(["linux/amd64","linux/arm64"])) throw Error("platforms");
console.log("Bake plan: 3 targets, each linux/amd64 + linux/arm64"); });'
for image in "$GOD_PJANGLER_IMAGE" "$GOD_SKILLEX_IMAGE" "$GOD_MCP_IMAGE"; do
  docker run --rm --network=none "$image" --help >/dev/null
  printf '%s\n' "$image --help: exit 0"
  cid=$(docker create --network=none "$image" --help)
  trap 'docker rm -f "$cid" >/dev/null 2>&1 || :' EXIT HUP INT TERM
  docker inspect "$cid" | docker run --rm -i --network=none --entrypoint node "$GOD_SKILLEX_IMAGE" -e '
let data="";process.stdin.on("data",c=>data+=c);process.stdin.on("end",()=>{
const c=JSON.parse(data)[0];
if(c.HostConfig.PublishAllPorts || Object.keys(c.HostConfig.PortBindings||{}).length || Object.values(c.NetworkSettings.Ports||{}).some(Boolean)) throw Error("published ports");
console.log("Container: published host ports=0, network="+c.HostConfig.NetworkMode);});'
  docker rm "$cid" >/dev/null
  trap - EXIT HUP INT TERM
  docker image inspect "$image" | docker run --rm -i --network=none --entrypoint node "$GOD_SKILLEX_IMAGE" -e '
let data=""; process.stdin.on("data",c=>data+=c); process.stdin.on("end",()=>{
const i=JSON.parse(data)[0]; const c=i.Config;
if(!c.User || c.User==="root" || c.User==="0" || Object.keys(c.ExposedPorts||{}).length) throw Error("user/ports");
console.log("Image: user="+c.User+" entrypoint="+JSON.stringify(c.Entrypoint)+" exposed=0 published=0"); });'
done
docker run --rm --network=none "$GOD_PJANGLER_IMAGE" --version
docker run --rm --network=none "$GOD_SKILLEX_IMAGE" --version
docker run --rm -i --network=none --entrypoint python "$GOD_MCP_IMAGE" < smoke/mcp.py
# Source is a template mount, not copied into an image. Prove the exact mount
# location expected by PJangler; no template tasks or user config are executed.
docker run --rm --network=none   --mount "type=bind,src=$template,dst=/opt/pjangler/templates/commonproject,readonly"   --entrypoint node "$GOD_PJANGLER_IMAGE" -e '
const fs=require("fs"),root="/opt/pjangler/templates/commonproject";
for(const f of ["copier.yml","template/.project.json.jinja"]) if(!fs.statSync(root+"/"+f).isFile()) throw Error("template missing");
const mount=fs.readFileSync("/proc/mounts","utf8").split("\n").find(l=>l.split(" ")[1]===root);
if(!mount || !mount.split(" ")[3].split(",").includes("ro")) throw Error("mount not read-only");
console.log("CommonProject: copier.yml + project template present; mount is read-only");'
# Registry inspection requires the network only on the host, not in smoke containers.
refs=$(docker run --rm --network=none --mount "type=bind,src=$bundle,dst=/bundle,readonly"   --entrypoint node "$GOD_SKILLEX_IMAGE" -e '
for(const i of require("/bundle/base-images.json").images) console.log([i.reference,i.platforms["linux/amd64"],i.platforms["linux/arm64"]].join(" "));')
printf '%s\n' "$refs" | while read -r ref amd arm; do
  docker buildx imagetools inspect "$ref" --raw | docker run --rm -i --network=none     --entrypoint node "$GOD_SKILLEX_IMAGE" -e '
let data="";process.stdin.on("data",c=>data+=c);process.stdin.on("end",()=>{
const m=JSON.parse(data).manifests;if(!m) throw Error("not a manifest index");
for(const [arch,digest] of [["amd64",process.argv[2]],["arm64",process.argv[3]]]){
const entry=m.find(i=>i.platform?.os==="linux"&&i.platform.architecture===arch);
if(!entry||entry.digest!==digest) throw Error("manifest mismatch: "+arch);
console.log(process.argv[1]+" linux/"+arch+" "+entry.digest);}});' "$ref" "$amd" "$arm"
done
docker run --rm -i --network=none --mount "type=bind,src=$bundle,dst=/bundle,readonly"   --entrypoint python "$GOD_MCP_IMAGE" < smoke/audit.py
printf '%s\n' 'PASS: G5 smoke; run-only artifacts, zero published host ports'
