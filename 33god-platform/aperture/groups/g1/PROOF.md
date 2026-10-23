# G1 bundle — proof of bring-up and round-trip (build host, 2026-10-23)

All commands run on the build host (`delorenj`) from the bundle directory
`33god-platform/aperture/groups/g1/` (branch `aperture/g1-bundle`), with the
production stacks (`bloodbank-nats`, `candystore`, `candystore-daprd`,
`candystore-postgres`, `bloodbank-dapr-placement`, `enricher-daprd`) live
throughout. Docker 29.2.1 / Compose v5.0.2.

## 1. `docker compose config -q` → clean

```
$ docker compose config -q && echo CONFIG_OK
CONFIG_OK

$ docker compose --profile catalog config -q && echo CATALOG_CONFIG_OK
CATALOG_CONFIG_OK
```

Resolved config facts verified before bring-up:

```
candystore             build_context=/home/delorenj/code/33GOD/.worktrees/aperture-g1-bundle/candystore  published_ports=[]
candystore-daprd       published_ports=[]
candystore-postgres    published_ports=[]
dapr-placement         published_ports=[]
nats                   published_ports=[]
nats-init              published_ports=[]
project: god-g1
```

Zero published host ports across all services; the candystore build context
resolves to the initialized `candystore` submodule checkout (relative default
`../../../../candystore` from the bundle dir).

## 2. `docker compose up -d --build` → all services up

```
$ docker compose up -d --build   (tail)
 Container god-g1-candystore-postgres-1  Healthy
 Container god-g1-nats-1                 Healthy
 Container god-g1-nats-init-1            Exited      ← one-shot, exit 0
 Container god-g1-candystore-1           Healthy
 Container god-g1-candystore-daprd-1     Started
```

`docker compose ps -a` (captured mid-proof):

```
NAME                           IMAGE                    STATUS                      PORTS
god-g1-candystore-1            candystore:g1            Up (healthy)                3001/tcp
god-g1-candystore-daprd-1      daprio/daprd:1.13.0      Up
god-g1-candystore-postgres-1   pgvector/pgvector:pg16   Up (healthy)                5432/tcp
god-g1-dapr-placement-1        daprio/dapr:1.13.0       Up
god-g1-nats-1                  nats:2.10-alpine         Up (healthy)                4222/tcp, 6222/tcp, 8222/tcp
god-g1-nats-init-1             natsio/nats-box:0.14.5   Exited (0)
```

State per service (from `docker compose ps -a --format json`):

```
candystore             running  exit 0  healthy
candystore-daprd       running  exit 0
candystore-postgres    running  exit 0  healthy
dapr-placement         running  exit 0
nats                   running  exit 0  healthy
nats-init              exited   exit 0
```

## 3. `bash smoke/smoke.sh` → PASS (10/10)

```
== 1/5 bring-up: waiting for services (project god-g1) ==
PASS: nats is healthy
PASS: nats-init completed with exit 0 (streams applied)
PASS: candystore-postgres is healthy
PASS: candystore is healthy (/readyz)
PASS: candystore-daprd is running
PASS: candystore-daprd :3500/v1.0/healthz responds

== 2/5 JetStream topology: BLOODBANK_EVENTS must exist ==
Information for Stream BLOODBANK_EVENTS created 2026-10-23 18:15:02
              Subjects: bloodbank.evt.>
PASS: stream BLOODBANK_EVENTS present with subject bloodbank.evt.>

== 3/5 publish test CloudEvent straight onto NATS subject bloodbank.evt.aperture.smoke.ping ==
envelope id: 52ebbcb9-e6a7-4ee6-aeab-18bf1716a63b
18:16:08 Published 842 bytes to "bloodbank.evt.aperture.smoke.ping"
PASS: CloudEvent published to bloodbank.evt.aperture.smoke.ping via NATS (nats-box, in-network)

== 4/5 wait for Dapr delivery + storage (poll GET /events/<id>/raw, up to 60s) ==
PASS: query API returned the stored raw envelope for id 52ebbcb9-e6a7-4ee6-aeab-18bf1716a63b

== 5/5 assert round-trip fidelity (envelope served == envelope published) ==
PASS: envelope matches: id, type, subject, correlationid, producer, data.ping

evidence (stream state after publish):
              Subjects: bloodbank.evt.>
              Messages: 3
         Last Sequence: 3 @ 2026-10-23 18:16:08

== verdict ==
passed: 10  failed: 0
SMOKE RESULT: PASS — G1 bus round-trip proven (NATS → JetStream → Dapr → candystore → query API)
```

Stored raw envelope served back by the query API (`GET /events/<id>/raw`,
read through the `candystore-app` network alias):

```json
{
  "id": "52ebbcb9-e6a7-4ee6-aeab-18bf1716a63b",
  "data": { "via": "nats-direct", "ping": true, "sequence": 1, "source_id": "aperture-g1-smoke" },
  "kind": "event",
  "time": "2026-10-23T18:16:08.000Z",
  "type": "bloodbank.evt.aperture.smoke.ping",
  "actor": { "cli": null, "type": "operator", "model": null, "agent_id": "operator:aperture-g1-smoke", "provider": null },
  "domain": "aperture",
  "source": "urn:33god:aperture:g1-smoke",
  "service": "smoke",
  "subject": "bloodbank.evt.aperture.smoke.ping",
  "producer": "aperture-g1-smoke",
  "causationid": "c629496a-596d-4134-a201-c68055334c17",
  "specversion": "1.0",
  "traceparent": "00-00000000000000000000000000000000-0000000000000000-00",
  "ordering_key": "aperture:g1-smoke",
  "correlationid": "c629496a-596d-4134-a201-c68055334c17",
  "datacontenttype": "application/json"
}
```

## 4. Teardown

```
$ docker compose down -v   (proof run: -v to also purge the synthetic smoke data from the host;
                            the README documents plain `down` for operators, which KEEPS god-g1-* volumes)
 Container god-g1-candystore-postgres-1 Stopped/Removed
 Volume god-g1-nats-data Removed
 Volume god-g1-candystore-pgdata Removed
 Network g1-bus Removed
 Network g1-internal Removed

$ docker compose ps -a
NAME      IMAGE     COMMAND   SERVICE   CREATED   STATUS      PORTS          ← empty

$ docker volume ls -q | grep god-g1
no god-g1 volumes remain
```

Production stacks verified untouched before and after the run:

```
$ docker ps --format '{{.Names}}' | grep -E '^(bloodbank-nats|candystore|...)$'
bloodbank-dapr-placement
bloodbank-nats
candystore
candystore-daprd
candystore-postgres
enricher-daprd
```

No god-g1 containers, networks (`g1-bus`, `g1-internal`), or volumes remain on
the host; the production `bloodbank-network` / `candystore-internal` networks
and every live container are exactly as before.
