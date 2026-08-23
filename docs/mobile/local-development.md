# Desarrollo Android local

El repositorio sí contiene `gradlew.bat`. Desde PowerShell, la compilación
verificada en esta integración usa la caché local de Gradle del usuario:

```powershell
.\gradlew.bat -g C:\Users\Admin\.gradle :core:testDebugUnitTest
.\gradlew.bat -g C:\Users\Admin\.gradle :android:app:lintDebug
.\gradlew.bat -g C:\Users\Admin\.gradle :android:app:assembleDebug

$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
& $adb devices -l
& $adb -s SERIAL install -r android\app\build\outputs\apk\debug\app-debug.apk
```

El APK real queda en `android/app/build/outputs/apk/debug/app-debug.apk`.
Usa un dispositivo físico para acelerómetro, giroscopio, flash y cámara. En
DEBUG se siembra la cuenta local `usuario` / `123456`; no representa una cuenta
cloud ni una autenticación remota.
