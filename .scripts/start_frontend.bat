@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
pushd "%~dp0..\agent-chat-ui2"
pnpm dev
popd
