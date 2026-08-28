# Uncommitted acceptance root cause

Base commit: `0100801087c431c72666b780782bb263d3e5ccec`

De 51/51-run gebruikte noodzakelijke lokale bronwijzigingen, maar de packaginglaag bevatte expliciete `uncommitted`-fallbacks en geen harde clean-tree/exact-SHA grens. Daardoor was functionele acceptance groen, maar het artifact niet cryptografisch aan dezelfde gepushte broncommit gebonden.

Correctie: commit en push uitsluitend reproduceerbare bron, bouw vanuit een fresh exact-SHA checkout, herhaal alle source/packaged/portable/installer-gates en genereer daarna commitgebonden hashes en manifests.
