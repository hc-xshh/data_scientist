@echo off
chcp 65001 >nul
pushd "D:\Desktop\data_scientist"
call conda activate data_scientist
langgraph dev
popd
