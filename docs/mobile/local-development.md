# Local Android development

The repository currently does not contain `gradlew.bat` and this environment does not have a global Gradle or ADB installation. Android Studio can import the root Gradle project and provision the configured Gradle distribution. Once the wrapper exists, the expected commands are:

```powershell
adb devices
.\gradlew.bat :android:app:assembleDebug
.\gradlew.bat :android:app:installDebug
```

Use a physical device for accelerometer, gyroscope, torch, and camera validation. The demo login is `usuario` / `123456` and is not production authentication.
