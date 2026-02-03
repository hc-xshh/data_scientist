@echo off
chcp 65001 >nul
pushd "%~dp0.."
call conda activate data_scientist
python File_service.py
popd
