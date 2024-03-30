@echo off
cd /d ".\blender-2.80"
start blender.exe -b -P "%~dp0blenderSpecs\__init__.py" -P "%~dp0blenderSpecs\importDae.py" -P "%~dp0blenderSpecs\replaceBSDF.py" -P "%~dp0blenderSpecs\separateAnS.py" -P "%~dp0blenderSpecs\output.py"