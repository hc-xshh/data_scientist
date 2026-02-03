@echo off
chcp 65001 >nul
pushd "%~dp0..\agent-chat-ui2"
pnpm dev
popd
