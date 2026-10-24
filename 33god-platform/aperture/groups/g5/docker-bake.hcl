variable "GOD_PJANGLER_CONTEXT" { default = "../../../../pjangler" }
variable "GOD_MCP_CONTEXT" { default = "../../../../../skillex/mcp-servers/codegraph-voyage-mcp" }
variable "GOD_PJANGLER_IMAGE" { default = "god-g5-pjangler:0.1" }
variable "GOD_SKILLEX_IMAGE" { default = "god-g5-skillex:0.1" }
variable "GOD_MCP_IMAGE" { default = "god-g5-mcp-codegraph:0.1" }
variable "GOD_SKILLEX_VERSION" { default = "0.3.1" }

group "default" { targets = ["pjangler", "skillex", "mcp-codegraph"] }

target "_tool" {
  context = "."
  platforms = ["linux/amd64", "linux/arm64"]
}
target "pjangler" {
  inherits = ["_tool"]
  dockerfile = "Dockerfile.pjangler"
  contexts = { pjangler = GOD_PJANGLER_CONTEXT }
  tags = [GOD_PJANGLER_IMAGE]
}
target "skillex" {
  inherits = ["_tool"]
  dockerfile = "Dockerfile.skillex"
  args = { GOD_SKILLEX_VERSION = GOD_SKILLEX_VERSION }
  tags = [GOD_SKILLEX_IMAGE]
}
target "mcp-codegraph" {
  inherits = ["_tool"]
  dockerfile = "Dockerfile.mcp-codegraph"
  contexts = { codegraph = GOD_MCP_CONTEXT }
  tags = [GOD_MCP_IMAGE]
}
