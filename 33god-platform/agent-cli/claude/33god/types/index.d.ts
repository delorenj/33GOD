// The 33god plugin's $.state contract. Change a shape tag in hooks/register.tsx
// when a value's fields change.

/** One row of the /identity agent menu: what `flume identity manifest --json` lists. */
export type IdentityAgent = { employee: string; role: string; prompt: string }

/** The open /identity pane: the project's agents, the one picked, and flume's text per agent. */
export type IdentityMenu = {
  project: string
  agents: IdentityAgent[]
  selected?: string
  detail: { [employee: string]: string }
}

declare module 'claude-code' {
  interface PluginState {
    '33god': { identityMenu: Shaped<IdentityMenu> }
  }
}
