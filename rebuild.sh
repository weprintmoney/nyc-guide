#!/bin/sh
# Regenerate data.js from research/ (copy.json overlay applied if present)
cd "$(dirname "$0")"
EXTRA=""; REV=""
[ -f research/places_reddit.json ] && EXTRA="research/places_reddit.json"
[ -f research/places_round2.json ] && EXTRA="$EXTRA research/places_round2.json"
[ -f research/places_host.json ] && EXTRA="$EXTRA research/places_host.json"
[ -f research/diners_reddit.json ] && REV="research/diners_reddit.json"
python3 build.py research/places_given.fixed.json research/places_added.fixed.json $EXTRA \
  --reviews research/diners_given.json research/diners_added.fixed.json $REV \
  --host-picks "Kabawa,Iara,Torrisi,Via Carota,Graciela,Humm,Borgo,Ambassadors Clubhouse,Elder,Aquavit,Jean-Georges,Border Town,Per Se,Cafe Wha?"
