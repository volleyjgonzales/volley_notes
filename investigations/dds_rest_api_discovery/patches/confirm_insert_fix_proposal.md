# Proposed eighth commit: recover the bay confirm clients from a missed discovery

Status: **dropped** (2026-11-04). Committed 2026-11-03 as `073556ea` (later rebased as `e1d24a7c`), deployed on comb,
and it didn't fix the stuck REST API: the participant is stuck, not its clients. Removed from PR #1018 (head `07eb74dd`).
Kept for the record.

## The problem it fixes

The REST API creates one `confirm_insert` and one `confirm_retrieve` client per bay at startup and keeps
them for the life of the process (`rest_api.py:372-379`). Before sending, it waits 2.5 s for the
service (v2 at `rest_api.py:488-493`, v3 at `ros_parking_gateways.py:44-48`). When the REST API and
the bays (re)start together on a deploy, a client can miss discovery of its bay's service. Nothing ever
creates a new client, so every confirm-insert to that bay fails with "timeout waiting for service …
ready" until the REST API restarts. That matches today's failures: two bays, 2 h 16 min apart.
`confirm_retrieve` doesn't wait at all: its request goes nowhere, and the caller times out after 5 s.

## The change

All in `rest_api.py`; the request path and `ros_parking_gateways.py` are unchanged from `main`.

- **A timer.** `refresh_bay_clients` runs every 10 s (`BAY_CLIENT_REFRESH_PERIOD_SEC`) on the node's spin
  thread for the life of the REST API. For each bay client whose `service_is_ready()` is false (a
  non-blocking check), it logs (throttled to once a minute) and swaps in a new client with the same
  `srv_type` and `service_name`. New endpoints get matched again by the discovery server.
- **Deferred destroy.** A replaced client goes on `bay_clients_to_destroy` and is destroyed at the start
  of the next refresh. A request holds a client for at most 2.5 s + 5 s, which is under 10 s, so no
  request has its client destroyed under it, and no lock is needed.
- **Steady state.** Nothing is created or destroyed. Each tick is two non-blocking checks per bay.

### Code

```python
BAY_CLIENT_REFRESH_PERIOD_SEC = 10.0
BayClient: TypeAlias = RosClient[Any, Any]
...
        self.bay_confirm_insert_clients: dict[str, BayClient] = {}
        self.bay_confirm_retrieve_clients: dict[str, BayClient] = {}
...
        self.bay_clients_to_destroy: list[BayClient] = []
        self.create_timer(BAY_CLIENT_REFRESH_PERIOD_SEC, self.refresh_bay_clients)
...
    def refresh_bay_clients(self) -> None:
        for client in self.bay_clients_to_destroy:
            self.destroy_client(client)
        self.bay_clients_to_destroy = []

        for clients in (
            self.bay_confirm_insert_clients,
            self.bay_confirm_retrieve_clients,
        ):
            for bay_name, client in clients.items():
                if client.service_is_ready():
                    continue
                self.get_logger().warning(
                    f"{client.service_name} not discovered, recreating its client",
                    throttle_duration_sec=60.0,
                )
                self.bay_clients_to_destroy.append(client)
                clients[bay_name] = self.create_client(
                    client.srv_type, client.service_name
                )
```

Replacing a value for an existing key while iterating `items()` is allowed; only adding or removing
keys raises. The dicts are updated in place because the v3 gateway holds the same dict.

Earlier versions had a generic helper in `ros_parking_gateways.py` (with a `Protocol` and a `TypeVar`).
It was inlined: with one caller, it meant reading two files to follow ten lines.

### Tests

`test_rest_api_v3.py`, `test_bay_client_refresh_replaces_undiscovered_clients`: the first refresh swaps in
the new retrieve client, leaves the discovered insert client alone and destroys nothing. The second
refresh destroys the replaced client and creates nothing new. The AST loader includes `refresh_bay_clients`.

## Commit message

```
fix(central_api): recreate bay confirm clients that miss service discovery at startup

When the REST API and the bays restart together, a bay's confirm_insert or confirm_retrieve client
can miss discovery of its service and never recover, so every confirm-insert to that bay fails with
"timeout waiting for service ready" until the REST API restarts. A 10 s timer now recreates any bay
client whose service is not discovered, before a patron needs it; a replaced client is destroyed
one refresh later, after any request still holding it has ended. The request path is unchanged.
```

## Checks

- `volley-in-container build central_api`, then `volley-in-container test central_api`. The existing
  v2/v3 discovery-failure tests must still pass, plus the three new ones. The hooks run black.
- CI's simulation system tests, which include patron inserts and blift insert/retrieve.
- On the garage: deploy, then confirm-insert right away. If discovery was missed, the rest_api log
  shows "/bay/bN/confirm_insert not discovered, recreating its client" and the insert succeeds.

## Caveats

- **Whether recreating fixes this race isn't proven yet.** It fixes a client whose endpoints
  were never matched. If the whole REST API participant lost the discovery server, a new client on
  the same participant won't help. The log grep in the findings (section 1.7) on the teammate's run
  settles it: a "recreating client" line followed by success means it works.
- **Overlap with Paula's branch.** `1c529f35` changes the same lines of `rest_api.py`. Whichever lands
  second has a conflict. Worth telling her this PR now carries the fix, so her branch can stay as the
  diagnostic it is.
- **Scope.** This PR becomes scheduler refactor + one REST API fix. Say so in the PR description's
  Testing/Why section.
