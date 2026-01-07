[app]
title = Trimoney
package.name = trimoney
package.domain = org.tribufum

source.dir = .
source.include_exts = py,kv,png,jpg,ttf

version = 0.1

requirements = python3,kivy

icon.filename = assets/icons/icon.png

orientation = portrait
fullscreen = 1

android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.ndk = 25b

android.archs = arm64-v8a

# 🔴 LINHAS CRÍTICAS (OBRIGATÓRIAS)
android.sdk = $ANDROIDSDK
android.build_tools_version = 30.0.3
android.accept_sdk_license = True
