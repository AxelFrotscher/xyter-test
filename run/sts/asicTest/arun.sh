#!/bin/bash
python initEdpbAndElinksSts.py
python setStsTypicalSettings.py 0 0
python sts_xyter_settrim_crate.py
python setGlobalGate.py 0 0 0
python getStatus.py 0 0

