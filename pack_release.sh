#!/usr/bin/env bash
set -e

# Developer ID for notarization (no more "damaged app" warning)
SIGN_IDENTITY="Developer ID Application: Yichen chu (HG5RRBKA8T)"
APPLE_ID="lman@me.com"
TEAM_ID="HG5RRBKA8T"
# App-specific password (from Apple ID settings)
NOTARIZE_PASSWORD="xxit-ihkn-bbmu-vuvm"

# Source directory (in Dropbox — source only)
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

# Build outside Dropbox to avoid Dropbox corrupting Qt framework bundles
BUILD_DIR="/tmp/voicetype4tw-build"

echo "=== [1/9] 同步 source 到 /tmp (避免 Dropbox 污染 framework bundle) ==="
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
rsync -a --delete \
    --exclude=venv/ \
    --exclude=build/ \
    --exclude=dist/ \
    --exclude=release_pack/ \
    --exclude=notarize_upload.zip \
    --exclude="*.zip" \
    --exclude=__pycache__/ \
    --exclude="*.pyc" \
    --exclude=".DS_Store" \
    "$SRC_DIR/" "$BUILD_DIR/"
echo "  Source 同步完成 → $BUILD_DIR"

cd "$BUILD_DIR"

echo "=== [2/9] 建立乾淨的 venv (在 /tmp 外Dropbox) ==="
python3 -m venv venv
VENV_PYTHON="$BUILD_DIR/venv/bin/python"
"$VENV_PYTHON" -m pip install --quiet --upgrade pip
echo "  安裝 py2app 和相依套件..."
"$VENV_PYTHON" -m pip install --quiet py2app modulegraph
"$VENV_PYTHON" -m pip install --quiet -r requirements.txt
echo "  venv 建立完成"

APP="dist/VoiceType4TW-Mac.app"
FRAMEWORKS="$APP/Contents/Frameworks"
SSL_LIB_DIR="/opt/homebrew/lib"

echo "=== [3/9] 使用 py2app 進行打包 ==="
"$VENV_PYTHON" setup.py py2app

echo "=== [4/9] 修復 _ssl.so 的 dylib 連結路徑 ==="
SSL_SO=$(find "$APP" -name "_ssl*.so" | head -1)
if [ -n "$SSL_SO" ]; then
    echo "  找到 _ssl: $SSL_SO"
    install_name_tool -change @executable_path/../Frameworks/libssl.3.dylib "$SSL_LIB_DIR/libssl.3.dylib" "$SSL_SO" 2>/dev/null || true
    install_name_tool -change @executable_path/../Frameworks/libcrypto.3.dylib "$SSL_LIB_DIR/libcrypto.3.dylib" "$SSL_SO" 2>/dev/null || true
    echo "  驗證連結:"
    otool -L "$SSL_SO" | grep -E "ssl|crypto"
fi

echo "=== [4b/9] 修復 MLX dylib (libmlx.dylib 未被 py2app 自動複製) ==="
MLX_SRC_LIB=$(find "$BUILD_DIR/venv/lib" -path "*/mlx/lib/libmlx.dylib" | head -1)
MLX_CORE_SO=$(find "$APP" -name "core.cpython-*.so" -path "*/mlx/*" | head -1)
if [ -n "$MLX_CORE_SO" ] && [ -f "$MLX_SRC_LIB" ]; then
    MLX_LIB_DIR="$(dirname "$MLX_CORE_SO")/lib"
    mkdir -p "$MLX_LIB_DIR"
    cp "$MLX_SRC_LIB" "$MLX_LIB_DIR/libmlx.dylib"
    # 讓 core.so 能在 @loader_path/lib 找到 libmlx.dylib
    install_name_tool -add_rpath "@loader_path/lib" "$MLX_CORE_SO" 2>/dev/null || true
    echo "  ✅ libmlx.dylib → $MLX_LIB_DIR"
    echo "  rpath 驗證:"
    otool -l "$MLX_CORE_SO" | grep -A2 LC_RPATH | grep path | head -5
else
    echo "  ⚠️ 找不到 MLX core.so 或 libmlx.dylib，跳過"
    [ -z "$MLX_CORE_SO" ] && echo "     MLX_CORE_SO: not found in bundle"
    [ ! -f "$MLX_SRC_LIB" ] && echo "     libmlx.dylib: not found at $MLX_SRC_LIB"
fi

echo "=== [5/9] 刪除 bundle 內不需要的副本 ==="
rm -f "$FRAMEWORKS/libssl.3.dylib" "$FRAMEWORKS/libcrypto.3.dylib"
rm -f "$FRAMEWORKS"/libxcb* "$FRAMEWORKS"/libXau* "$FRAMEWORKS"/libX11*

echo "=== [6/9] 簽名 python312.zip 內的二進位 ==="
LIB_DIR="$APP/Contents/Resources/lib"
PYZIP=$(find "$LIB_DIR" -maxdepth 1 -name "python*.zip" | head -1)
if [ -n "$PYZIP" ]; then
    PYZIP_REL="${PYZIP#$BUILD_DIR/}"
    PY_TMP="/tmp/pyzip_sign_$$"
    mkdir -p "$PY_TMP"
    echo "  解壓 $(basename $PYZIP)..."
    cd "$PY_TMP"
    unzip -q "$PYZIP"
    echo "  簽名內部二進位..."
    INNER_SIGNED=0
    while IFS= read -r -d '' bin; do
        codesign --force --sign "$SIGN_IDENTITY" --timestamp "$bin" 2>/dev/null && INNER_SIGNED=$((INNER_SIGNED+1)) || true
    done < <(find . \( -name "*.so" -o -name "*.dylib" \) -print0)
    echo "  已簽名 $INNER_SIGNED 個檔案"
    echo "  重新打包 $(basename $PYZIP)..."
    rm -f "$PYZIP"
    zip -qr "$PYZIP" .
    cd "$BUILD_DIR"
    rm -rf "$PY_TMP"
fi

echo "=== [7/9] 全面簽名所有二進位 (inside-out) ==="
# 簽名順序：最深層 → 外層 bundle，最後整個 app

# 1. 簽名 Frameworks/ 下的 dylib（嘗試刪除無法簽名者）
SIGN_FAIL=0
for f in "$FRAMEWORKS"/*.dylib; do
    [ -f "$f" ] || continue
    codesign --force --sign "$SIGN_IDENTITY" --timestamp "$f" 2>/dev/null && true || {
        echo "  ⚠️ 無法簽名: $(basename $f)，嘗試刪除..."
        rm -f "$f"
        SIGN_FAIL=$((SIGN_FAIL+1))
    }
done

# 2. 簽名所有 .dylib（遞迴）
while IFS= read -r -d '' f; do
    codesign --force --sign "$SIGN_IDENTITY" --timestamp "$f" 2>/dev/null || true
done < <(find "$APP" -name "*.dylib" -not -path "*/Frameworks/*.dylib" -print0 2>/dev/null)

# 3. 簽名所有 .so（遞迴）
while IFS= read -r -d '' f; do
    codesign --force --sign "$SIGN_IDENTITY" --timestamp "$f" 2>/dev/null || true
done < <(find "$APP" -name "*.so" -print0 2>/dev/null)

# 4. 簽名 Qt framework 可執行二進位（Versions/A/* 無副檔名的 Mach-O）
while IFS= read -r -d '' vdir; do
    for bin in "$vdir"/*; do
        [ -f "$bin" ] || continue
        # 只處理無副檔名的檔案（Qt 可執行二進位）
        case "$(basename "$bin")" in
            *.*)  continue ;;  # 有副檔名的跳過
        esac
        codesign --force --sign "$SIGN_IDENTITY" --timestamp "$bin" 2>/dev/null || true
    done
done < <(find "$APP" -path "*/Qt6/lib/*.framework/Versions/A" -type d -print0 2>/dev/null)

# 5. 簽名 Contents/MacOS 目錄下的 python 及其他二進位
while IFS= read -r -d '' f; do
    codesign --force --sign "$SIGN_IDENTITY" --timestamp "$f" 2>/dev/null || true
done < <(find "$APP/Contents/MacOS" -type f -print0 2>/dev/null)

# 6. 簽名 Qt framework bundles（作為整體）
while IFS= read -r -d '' fw; do
    codesign --force --sign "$SIGN_IDENTITY" --timestamp "$fw" 2>/dev/null || true
done < <(find "$APP/Contents/Resources/lib" -name "*.framework" -type d -print0 2>/dev/null)

# 7. 簽名 Python.framework
codesign --force --sign "$SIGN_IDENTITY" --timestamp "$FRAMEWORKS/Python.framework" 2>/dev/null || true

echo "  已排除 $SIGN_FAIL 個問題 dylib"

echo "=== [8/9] 使用 Developer ID 簽名整個 App bundle ==="
codesign --force --sign "$SIGN_IDENTITY" --timestamp --options runtime --entitlements entitlements.plist "$APP" 2>&1

echo "=== [8b/9] 驗證簽名 ==="
codesign -dvvv "$APP" 2>&1 | grep -E "Identifier|Format|Signature|Sealed|Entitlements|TeamIdentifier"

echo "=== [9/9] 建立 ZIP + Notarize ==="
xattr -cr "$APP"
mkdir -p release_pack
cp -R "$APP" release_pack/

# Zip for notarization
ditto -c -k --keepParent release_pack/VoiceType4TW-Mac.app notarize_upload.zip

echo "  上傳 Notarization..."
if xcrun notarytool submit notarize_upload.zip \
    --apple-id "$APPLE_ID" \
    --team-id "$TEAM_ID" \
    --password "$NOTARIZE_PASSWORD" \
    --wait 2>&1; then
    echo "  Notarization 成功！Staple ticket..."
    xcrun stapler staple release_pack/VoiceType4TW-Mac.app
    echo "  Staple 完成 ✅"
else
    echo "  ⚠️ Notarization 失敗或跳過 — 使用已簽名但未 notarize 版本"
fi

rm -f notarize_upload.zip
cp "$SRC_DIR/首次開啟必看_解除損毀警告.md" release_pack/ 2>/dev/null || true
cp "$SRC_DIR/install.command" release_pack/

cd release_pack
zip -ry ../VoiceType4TW-Mac-Release.zip *
cd ..

# 把最終 ZIP 複製回 Dropbox
cp VoiceType4TW-Mac-Release.zip "$SRC_DIR/"

ls -lh VoiceType4TW-Mac-Release.zip
echo "✅ 打包完成！輸出：$SRC_DIR/VoiceType4TW-Mac-Release.zip"
