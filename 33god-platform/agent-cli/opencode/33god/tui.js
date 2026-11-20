// 33GOD commands for OpenCode (v2 TUI plugin). Source of truth: 33god-platform/agent-cli/opencode/33god/;
// installed as a symlink at ~/.config/opencode/plugins/33god (33god-hub sub-skill `agent-cli-extensions`).
//
//   /identity             a menu of every agent the session's project declares (.project.json), each labelled with
//                         the prompt's own words (`id v1 5/6`); picking one shows its identity points
//   /identity <employee>  that employee's identity points directly
//
// A thin adapter: the data and the view are `flume identity manifest [employee] [--json]`. Runs locally in the TUI:
// no model turn, nothing added to the session.
import { execFile } from "node:child_process";

const FLUME_TIMEOUT_MS = 30000;

function flume(args, cwd) {
  return new Promise((resolve) => {
    execFile("flume", args, { cwd, timeout: FLUME_TIMEOUT_MS, maxBuffer: 4 * 1024 * 1024 }, (error, stdout, stderr) => {
      resolve({ ok: !error, stdout: String(stdout || ""), stderr: String(stderr || ""), error });
    });
  });
}

/** The directory the current session runs in, as the built-in /cd reads it. */
function sessionDirectory(ctx) {
  try {
    const route = ctx.ui.router.current();
    const sessionID = route?.type === "session" ? route.sessionID : undefined;
    const dir = sessionID ? ctx.data?.session?.get?.(sessionID)?.location?.directory : undefined;
    if (typeof dir === "string" && dir) return dir;
  } catch { /* fall through */ }
  const here = ctx.location?.directory;
  return typeof here === "string" && here ? here : process.cwd();
}

async function showEmployee(ctx, employee, cwd) {
  const run = await flume(["identity", "manifest", employee], cwd);
  ctx.ui.dialog.set?.({ size: "xlarge" });
  await ctx.ui.dialog.alert({ title: `Identity · ${employee}`, message: (run.stdout || run.stderr || `flume failed: ${run.error?.message}`).trimEnd() });
}

async function identity(ctx, argString) {
  const cwd = sessionDirectory(ctx);
  const employee = (argString ?? "").trim();
  if (employee) return showEmployee(ctx, employee, cwd);

  const run = await flume(["identity", "manifest", "--json"], cwd);
  let result;
  try { result = JSON.parse(run.stdout); } catch { result = { ok: false, error: run.stderr || run.error?.message || "flume returned no JSON" }; }
  if (!result.ok) {
    await ctx.ui.dialog.alert({ title: "Identity", message: `${result.error ?? "flume identity manifest failed"}\n\nName one: /identity <employee>` });
    return;
  }
  if (!result.agents?.length) {
    await ctx.ui.dialog.alert({ title: "Identity", message: `${result.project.file} (${result.project.slug}) declares no agents. Name one: /identity <employee>` });
    return;
  }
  const picked = await ctx.ui.dialog.select({
    title: `Identity · ${result.project.slug}${result.pm ? ` · PM ${result.pm}` : ""}`,
    options: result.agents.map((agent) => ({
      title: agent.employee,
      value: agent.employee,
      description: `${agent.role} · ${agent.prompt}${agent.ok ? "" : ` · ${agent.error}`}`,
      category: agent.employee === result.pm ? "PM" : "Agents",
    })),
  });
  if (picked) await showEmployee(ctx, picked, cwd);
}

async function setup(ctx) {
  // layer takes an accessor (a function returning the layer), as the built-in /cd's createLayer does.
  ctx.keymap.layer(() => ({
    mode: "global",
    commands: [{
      id: "33god.identity",
      title: "33GOD identity",
      desc: "Identity manifest points for this project's agents, or a named employee",
      group: "33GOD",
      palette: true,
      bind: false,
      slash: { name: "identity", arguments: true },
      run: (argString) => identity(ctx, argString).catch((error) =>
        ctx.ui.toast.show({ variant: "error", title: "/identity", message: String(error?.message ?? error) })),
    }],
  }));
}

export default { id: "33god", setup };
