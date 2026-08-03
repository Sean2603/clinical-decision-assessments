# Remote engine parity repair

Extract this ZIP into the root of:

C:\Users\McG\Documents\GitHub\clinical-decision-assessments

Then run:

python tool/repair_remote_parity_cases.py
python tool/validate_remote_engines.py
python tool/validate_content.py
python tool/validate_clinical_reliability.py
python tool/validate_references.py
python tool/generate_reference_usage.py
python tool/sync_manifest.py
python tool/validate_content.py
python tool/validate_remote_engines.py

The repair script:
- changes only missing parityCases fields;
- does not alter scoring criteria, thresholds, results, calculations, or clinical text;
- creates backups in the Windows temporary directory;
- reports every modified file.

After all validators pass, retry the existing Urea and Electrolytes 1.0.1 publication.
Do not create version 1.0.2 merely because the previous repository transaction failed.
