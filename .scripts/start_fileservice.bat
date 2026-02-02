@echo off
chcp 65001 >nul
pushd "D:\HAHA\项目\A公司\code\data_scientist"
call conda activate data_scientist
python File_service.py
popd
