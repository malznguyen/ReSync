# Redis Storage Conventions

Phase 1 reserves these Redis names for cache and channel usage:

- `cam:{id}:frames`: live camera frame channel/stream name for ingestion-to-worker fanout.
- `track:{id}:state`: JSON track state cache. TTL is 300 seconds.
- `zone:config:cache`: zone configuration cache namespace. Zone cache entries do not expire automatically; analytics still refreshes from Postgres every 60 seconds.

TTL policy:

- Track state keys expire after 300 seconds so stale tracks cannot survive service restarts.
- Camera frame data is overwritten by producers and consumers must check frame timestamps before processing.
- Zone config is invalidated explicitly and periodically refreshed from Postgres.

Keyspace notifications:

- Redis is configured with `notify-keyspace-events Ex` so services can subscribe to expired-key events when track TTLs lapse.
- Keyspace notifications are an optimization, not a source of truth. Services must still tolerate missed Pub/Sub events and perform periodic Postgres refreshes.
