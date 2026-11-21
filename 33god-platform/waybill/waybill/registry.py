"""Which component is this event? The one Python resolver (I-10.2).

`atlas.py render` writes the registry's resolution map into the Factory cast
(manual/sandbox/src/cast.generated.json, key `resolve`); this module and the player's
src/waybill/resolve.ts both read that one file, so the archive builder, the night digest and the
Factory can never disagree about where an event lands. components.yaml documents the rules.

    reg = load()                                          # the committed cast
    r = reg.resolve("pjangler", "bloodbank.crank.binding.created", "urn:33god:service:crank")
    r.id     -> "crank"            the waybill / Factory id (registry id, extra, desk or tenant)
    r.owner  -> "crank"            the registry component that answers for it (None: not a component)
    r.via    -> "source"           which rule matched: source | tenant | desk | producer | id | unknown
    r.key    -> None               the desk profile or tenant slug, when there is one

Order (first match wins): source rules (a relay claim, `source:<ce-source-glob>[#<type-glob>]`), tenant
rules (atlas_ignore rows with `tenant:`), desk families (`hermes-agent:<profile>` -> `hermes-desk:<profile>`),
producer surfaces (exact, then the longest glob), a producer spelled like a registry id / alias / extra,
else `unknown`. Globs are `*` and `?` only (atlas enforces it), so fnmatch here equals the player's matcher.

The Candybar-job / hook-handler credit (`worker_resolver`) lives here too: the night digest and the query
builder both credit work to the component it was done for.
"""
from __future__ import annotations

import fnmatch
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

CAST_PATH = Path(__file__).resolve().parents[2] / "manual" / "sandbox" / "src" / "cast.generated.json"
CAST_FORMAT = "33god.factory-cast"
UNKNOWN = "unknown"

# Hook handlers whose id does not start with their owner's registry id.
HANDLER_OWNERS = {
    "bloodbank-publisher": "agent-hooks", "hub-selftest": "hook-hub", "native-clock-guard": "hook-hub",
    "nanoleaf": "hook-hub", "skill-reminder": "skillex", "skill-lint": "skillex",
    "project-notebook-start": "open-notebook", "project-notebook-end": "open-notebook",
}
# Hook-hub's own plumbing: its handlers run on every hook, so crediting them would only re-light hook-hub.
NO_CREDIT = {"bloodbank-publisher", "hub-selftest", "nanoleaf", "native-clock-guard"}
FIRST_PARTY_ROOT = Path("~/code/33GOD").expanduser()
CANDYBAR_ROOTS = ["~/code", "~/code/33GOD", "~/code/33GOD/bloodbank/services", "~/docker", "~/.config", "~/.agents", "~/HeyMa"]


@dataclass(frozen=True)
class Resolution:
    id: str                 # waybill / Factory id: a registry id, an extra, `hermes-desk:<p>`, `tenant:<slug>` or `unknown`
    owner: str | None       # the registry component that answers for the event (None for tenants, extras, unknown)
    via: str                # source | tenant | desk | producer | id | unknown
    key: str | None = None  # desk profile or tenant slug


def short_type(t: str | None, prefix: str = "bloodbank.") -> str:
    t = t or ""
    return t[len(prefix):] if prefix and t.startswith(prefix) else t


def _strip_glob(pattern: str, value: str) -> str:
    """What a pattern's wildcard part matched: the value minus the pattern's literal head and tail."""
    head = re.split(r"[*?]", pattern, maxsplit=1)[0]
    tail = re.split(r"[*?]", pattern)[-1] if is_glob(pattern) else ""
    out = value[len(head):] if value.startswith(head) else value
    return out[: len(out) - len(tail)] if tail and out.endswith(tail) else out


def is_glob(p: str) -> bool:
    return any(ch in p for ch in "*?")


class Registry:
    """The cast's components, extras, aliases and resolution map, with the resolver over them."""

    def __init__(self, cast: dict[str, Any]):
        if cast.get("format") != CAST_FORMAT or cast.get("version") != 1:
            raise ValueError(f"unknown cast format {cast.get('format')} v{cast.get('version')}; run atlas.py render")
        self.cast = cast
        self.components: dict[str, dict[str, Any]] = cast.get("components") or {}
        self.extras: dict[str, dict[str, Any]] = cast.get("extras") or {}
        self.aliases: dict[str, str] = cast.get("aliases") or {}
        res = cast.get("resolve") or {}
        self.type_prefix: str = res.get("type_prefix", "bloodbank.")
        self.unknown: str = res.get("unknown", UNKNOWN)
        self.sources: list[dict[str, Any]] = res.get("sources") or []
        self.tenants: dict[str, Any] = res.get("tenants") or {"prefix": "tenant:", "annex": "tenant-annex", "rules": []}
        self.desks: dict[str, dict[str, Any]] = res.get("desks") or {}
        producers = res.get("producers") or []
        self._exact = {}
        for p in producers:
            if not is_glob(p["producer"]):
                self._exact.setdefault(p["producer"], p["id"])
        self._globs = [(p["producer"], p["id"]) for p in producers if is_glob(p["producer"])]
        self._desk_re = {fam: re.compile(d.get("instance") or ".+") for fam, d in self.desks.items()}
        self._cache: dict[tuple[str, str, str], Resolution] = {}

    # ------------------------------------------------------------ construction

    @classmethod
    def from_records(cls, records: dict[str, dict[str, Any]], desks: dict[str, dict[str, Any]] | None = None,
                     tenants: list[dict[str, str]] | None = None) -> "Registry":
        """A registry from the legacy night shape {id: {name, summary?, first_party, producers, sources?}}, plus
        optional desk families and tenant rules in the cast's `resolve` shape. Tests and old callers use it."""
        comps = {cid: {"name": r.get("name", cid), "summary": r.get("summary", ""), "first_party": r.get("first_party", False),
                       "domain": r.get("domain"), "station": None, "near": None, "aliases": []}
                 for cid, r in records.items()}
        producers = [{"producer": g, "id": cid} for cid, r in sorted(records.items()) for g in r.get("producers") or []]
        producers.sort(key=lambda x: (is_glob(x["producer"]), -len(x["producer"]) if is_glob(x["producer"]) else 0, x["producer"]))
        sources = []
        for cid, r in sorted(records.items()):
            for s in r.get("sources") or []:
                src, _, typ = s.partition("#")
                sources.append({"source": src, "type": typ or None, "id": cid})
        sources.sort(key=lambda x: (x["type"] is None, -len(x["type"] or ""), -len(x["source"])))
        return cls({"format": CAST_FORMAT, "version": 1, "components": comps, "extras": {}, "aliases": {},
                    "resolve": {"sources": sources, "producers": producers, "desks": desks or {},
                                "tenants": {"prefix": "tenant:", "annex": "tenant-annex", "rules": tenants or []}}})

    # ------------------------------------------------------------ lookups

    def canonical(self, cid: str) -> str | None:
        """A registry id, alias or extra (with or without `ext:`) -> its canonical cast id, else None."""
        for k in (cid, cid[4:] if cid.startswith("ext:") else f"ext:{cid}"):
            if k in self.components or k in self.extras:
                return k
            if k in self.aliases:
                return self.aliases[k]
        return None

    def is_registry(self, cid: str) -> bool:
        return cid in self.components

    def name_of(self, cid: str) -> str:
        if cid in self.components:
            return self.components[cid]["name"]
        if cid in self.extras:
            return self.extras[cid]["name"]
        for fam, d in self.desks.items():
            if cid.startswith(fam + ":"):
                key = cid[len(fam) + 1:]
                return f"{d.get('name', fam)} (unnamed)" if key == UNKNOWN else key
        tp = self.tenants.get("prefix", "tenant:")
        if cid.startswith(tp):
            return cid[len(tp):]
        return cid

    @property
    def records(self) -> dict[str, dict[str, Any]]:
        """Legacy night shape: registry id -> {name, summary, first_party, producers}."""
        out = {cid: {"name": c["name"], "summary": c.get("summary", ""), "first_party": bool(c.get("first_party")),
                     "producers": []} for cid, c in self.components.items()}
        for p, cid in [*self._exact.items(), *self._globs]:
            if cid in out:
                out[cid]["producers"].append(p)
        return out

    # ------------------------------------------------------------ the resolver

    def resolve(self, producer: str | None, type: str | None = None, source: str | None = None) -> Resolution:
        key = (producer or "", type or "", source or "")
        hit = self._cache.get(key)
        if hit is None:
            hit = self._cache[key] = self._resolve(*key)
        return hit

    def component(self, producer: str | None, type: str | None = None, source: str | None = None) -> str:
        return self.resolve(producer, type, source).id

    def owner(self, producer: str | None, type: str | None = None, source: str | None = None) -> str | None:
        return self.resolve(producer, type, source).owner

    def _owner_of(self, cid: str) -> str | None:
        return cid if cid in self.components else None

    def _resolve(self, producer: str, etype: str, source: str) -> Resolution:
        t = short_type(etype, self.type_prefix)
        # 1. source rules: a relay claim, whoever published it
        for rule in self.sources:
            if rule.get("type") and not (t and fnmatch.fnmatchcase(t, rule["type"])):
                continue
            if rule["source"] != "*" and not (source and fnmatch.fnmatchcase(source, rule["source"])):
                continue
            return Resolution(rule["id"], self._owner_of(rule["id"]), "source")
        # 2. tenants: product and client projects, one annex keyed by slug
        for rule in self.tenants.get("rules") or []:
            if producer and fnmatch.fnmatchcase(producer, rule["producer"]):
                slug = _strip_glob(rule["producer"], producer) if rule["slug"] == "*" else rule["slug"]
                return Resolution(f"{self.tenants.get('prefix', 'tenant:')}{slug}", None, "tenant", slug)
        # 3. desk families: one desk per instance
        for fam, d in self.desks.items():
            pre = d.get("producer") or ""
            if producer in (d.get("bare") or []):
                return Resolution(f"{fam}:{UNKNOWN}", d.get("owner"), "desk", UNKNOWN)
            if pre and producer.startswith(pre):
                inst = producer[len(pre):]
                for route in d.get("routes") or []:
                    if fnmatch.fnmatchcase(inst, route["instance"]):
                        cid = route["id"]
                        return Resolution(cid, self._owner_of(cid) or d.get("owner"), "desk", inst)
                if inst in (d.get("malformed") or []) or not self._desk_re[fam].search(inst):
                    return Resolution(f"{fam}:{UNKNOWN}", d.get("owner"), "desk", UNKNOWN)
                return Resolution(f"{fam}:{inst}", d.get("owner"), "desk", inst)
        # 4. producer surfaces
        if producer in self._exact:
            cid = self._exact[producer]
            return Resolution(cid, self._owner_of(cid), "producer")
        for g, cid in self._globs:
            if producer and fnmatch.fnmatchcase(producer, g):
                return Resolution(cid, self._owner_of(cid), "producer")
        # 5. a producer named exactly like a component, alias or extra
        if producer:
            cid = self.canonical(producer)
            if cid:
                return Resolution(cid, self._owner_of(cid), "id")
        return Resolution(self.unknown, None, "unknown")


_LOADED: dict[Path, Registry] = {}


def load(path: Path | str = CAST_PATH) -> Registry:
    """The committed cast's registry (cached per path)."""
    p = Path(path)
    if p not in _LOADED:
        _LOADED[p] = Registry(json.loads(p.read_text(encoding="utf-8")))
    return _LOADED[p]


def _as_registry(registry: "Registry | dict[str, dict]") -> Registry:
    return registry if isinstance(registry, Registry) else Registry.from_records(registry)


def load_registry(path: Path | str = CAST_PATH) -> dict[str, dict]:
    """Legacy night shape: registry id -> {name, summary, first_party, producers}."""
    return load(path).records


def resolver(registry: "Registry | dict[str, dict]") -> Callable[..., str | None]:
    """(producer, type=None, source=None) -> the registry component that answers for it, or None."""
    return _as_registry(registry).owner


# ---------------------------------------------------------------- work credit (Candybar jobs, hook handlers)

def candybar_manifests(roots: list[str] = CANDYBAR_ROOTS) -> dict[str, str]:
    """job name -> path of the repo whose .candybars/ holds its manifest (worktrees skipped)."""
    out: dict[str, str] = {}
    for r in roots:
        base = Path(r).expanduser()
        for d in [base / ".candybars", *base.glob("*/.candybars")]:
            if ".worktrees" in d.parts or not d.is_dir():
                continue
            for f in d.glob("*.candybar.toml"):
                out.setdefault(f.name[: -len(".candybar.toml")], str(d.parent))
    return out


def worker_resolver(registry: dict[str, dict], resolve, manifests: dict[str, str], owners: dict[str, str]):
    """A job or handler name -> the component it works for, or None (it stays with Candybar / hook-hub).

    Order: explicit owner, producer surface or exact id, the repo its manifest lives in, then the
    longest registry-id prefix (first-party ids before third-party ones, so `hindsight-turn` lights
    Hindsight but `bloodbank-x` never lands on a service named `bloodbank`-something else). A manifest
    in a repo that is neither a registry component nor under ~/code/33GOD is a client job, and no name
    prefix can claim it."""
    ids = (sorted((c for c in registry if registry[c]["first_party"]), key=len, reverse=True)
           + sorted((c for c in registry if not registry[c]["first_party"]), key=len, reverse=True))

    def who(name: str) -> str | None:
        if not name:
            return None
        if name in owners and owners[name] in registry:
            return owners[name]
        cid = resolve(name)
        if cid:
            return cid
        repo = manifests.get(name)
        if repo:
            base = Path(repo).name
            for cand in (base, base.lower()):
                if cand in registry:
                    return cand
            rp = Path(repo).expanduser()
            if rp.is_absolute() and rp != FIRST_PARTY_ROOT and FIRST_PARTY_ROOT not in rp.parents:
                return None     # a client project's job
        for i in ids:
            if name.startswith(i + "-"):
                return i
        return None
    return who
