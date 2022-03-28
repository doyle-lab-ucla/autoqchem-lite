## Autoqchem lite

dev version of autoqchem lite

see test.py for some examples

### known bugs 
- may not allocate enough memory for large basis set (the easy fix is to request a lot of resources, which results in very long wait time on h2 cluster since we are on free plan)
- no automated way to check errors
- extract features not guaranteed to work