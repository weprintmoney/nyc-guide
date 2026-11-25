#!/bin/sh
# Regenerate data.js from research/ (copy.json overlay applied if present)
cd "$(dirname "$0")" && python3 build.py research/places_given.fixed.json research/places_added.fixed.json \
  --reviews research/diners_given.json research/diners_added.fixed.json \
  --host-picks "Kabawa,Iara,Torrisi,Via Carota,Graciela,Humm,Borgo,Ambassadors Clubhouse,Elder,Aquavit,Jean-Georges,Border Town,Per Se"
