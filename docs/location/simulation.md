# Simulation

The web fixture creates 24 devices around Bogotá with current GPS, last-known, historical-estimate and relay evidence; live through stale packets; varied accuracy and battery; stationary and moving states; two SOS packets; relay hops; three rescue units; and two search polygons.

Run with `cd web && npm install && npm run dev`. The header must read `SIMULATION`. Production adapters must replace the fixture at the domain-source boundary, not mutate the presentation model.

