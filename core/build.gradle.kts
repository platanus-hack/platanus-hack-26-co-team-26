plugins {
    alias(libs.plugins.kotlin.multiplatform)
    alias(libs.plugins.android.library)
}

kotlin {
    androidTarget()

    // iosMain queda declarado y vacío hasta la Fase 2 (docs/roadmap/VERTICAL-SLICES.md, sección 19bis).
    // TODO(fase 2): activar iosTarget() cuando Slice 4 esté demostrado o exista alianza institucional.
    // iosX64(); iosArm64(); iosSimulatorArm64()

    sourceSets {
        val commonMain by getting {
            dependencies {
                implementation(libs.kotlinx.coroutines.core)
                implementation(libs.protobuf.kotlin.lite)
            }
        }
        val commonTest by getting {
            dependencies {
                implementation(kotlin("test"))
            }
        }
        val androidMain by getting
        // val iosMain by getting // vacío, comentado — ver nota arriba
    }
}

android {
    namespace = "co.sismomesh.core"
    compileSdk = 35
    defaultConfig {
        minSdk = 26
    }
}

// Regla verificada por arch-guard (Konsist + .importlinter):
// :core:domain NO importa android.*, androidx.*, io.ktor.*, ni ningún SDK.
// :core:application solo importa :core:domain y sus propios puertos.
