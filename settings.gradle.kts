rootProject.name = "sismomesh"

pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositories {
        google()
        mavenCentral()
    }
}

// :core es Kotlin Multiplatform con un único target activo (androidMain).
// iosMain se declara vacío y desactivado hasta la Fase 2 (ver docs/roadmap/VERTICAL-SLICES.md, 19bis).
include(":core")

include(":android:app")
include(":android:transport")
include(":android:sensing")
include(":android:ppg")
include(":android:inference")
include(":android:storage")
include(":android:power")
include(":android:testing")

include(":simulators:mesh-sim")
include(":simulators:fake-devices")

project(":android:app").projectDir = file("android/app")
project(":android:transport").projectDir = file("android/transport")
project(":android:sensing").projectDir = file("android/sensing")
project(":android:ppg").projectDir = file("android/ppg")
project(":android:inference").projectDir = file("android/inference")
project(":android:storage").projectDir = file("android/storage")
project(":android:power").projectDir = file("android/power")
project(":android:testing").projectDir = file("android/testing")
project(":simulators:mesh-sim").projectDir = file("simulators/mesh_sim")
project(":simulators:fake-devices").projectDir = file("simulators/fake_devices")
