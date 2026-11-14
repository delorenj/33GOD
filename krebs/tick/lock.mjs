// One tick at a time per host. Candybar does not start a fire while the last
// one runs, but a hand-run `krebs tick` can overlap a scheduled one, and two
// dispatchers reading the same free slot would both fill it.

import { closeSync, mkdirSync, openSync, readFileSync, unlinkSync, writeSync } from "node:fs";
import { dirname } from "node:path";

function alive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (err) {
    return err.code === "EPERM";
  }
}

/** Take the lock, or return null when a live process holds it. A dead holder's lock is taken over. */
export function acquireLock(path) {
  mkdirSync(dirname(path), { recursive: true });
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const fd = openSync(path, "wx");
      writeSync(fd, String(process.pid));
      closeSync(fd);
      return {
        path,
        release() {
          try {
            if (readFileSync(path, "utf8").trim() === String(process.pid)) unlinkSync(path);
          } catch {
            // already gone
          }
        },
      };
    } catch (err) {
      if (err.code !== "EEXIST") throw err;
      let holder = NaN;
      try {
        holder = Number(readFileSync(path, "utf8").trim());
      } catch {
        // vanished between open and read: retry
      }
      if (Number.isInteger(holder) && holder > 0 && alive(holder)) return null;
      try {
        unlinkSync(path);
      } catch {
        // someone else took it over first
      }
    }
  }
  return null;
}
