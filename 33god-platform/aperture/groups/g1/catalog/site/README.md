# EventCatalog site mount (catalog profile).

Empty on purpose. EventCatalog renders `catalog/site`; bloodbank populates it
via Holyfields generation output, which Aperture does not ship. Start the
profile with `docker compose --profile catalog up -d` to get a bare catalog UI
waiting for AsyncAPI artifacts.
