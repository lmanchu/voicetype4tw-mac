#!/bin/bash
# VoiceType4TW-Mac 一鍵安裝
# 雙擊此檔案即可自動安裝

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="VoiceType4TW-Mac.app"
APP_SRC="$SCRIPT_DIR/$APP_NAME"
APP_DST="/Applications/$APP_NAME"

if [ ! -d "$APP_SRC" ]; then
    echo "找不到 $APP_NAME，請確認此檔案與 App 在同一個資料夾中。"
    read -p "按 Enter 關閉..."
    exit 1
fi

echo "正在安裝 VoiceType4TW-Mac..."
echo ""

# 移除舊版本
if [ -d "$APP_DST" ]; then
    echo "發現舊版本，正在移除..."
    rm -rf "$APP_DST"
fi

# 複製到 Applications
cp -R "$APP_SRC" "$APP_DST"

# 解除 macOS 隔離標記
xattr -cr "$APP_DST"

echo "安裝完成！正在啟動..."
open "$APP_DST"

echo ""
echo "VoiceType4TW-Mac 已安裝到 /Applications 並啟動。"
echo "之後可以從 Launchpad 或 Finder 直接開啟。"
echo ""
read -p "按 Enter 關閉此視窗..."
