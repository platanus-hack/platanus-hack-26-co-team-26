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
            }
        }
        val commonTest by getting {
            dependencies {
                implementation(kotlin("test"))
                implementation(libs.kotlinx.coroutines.test)
            }
        }
        val androidMain by getting {
            dependencies {
                // Código generado por protobuf (java_out + kotlin_out) es JVM-only,
                // vive en androidMain — ver core/src/androidMain/kotlin/co/sismomesh/core/protocol/README.md.
                implementation(libs.protobuf.java)
                implementation(libs.protobuf.kotlin)
            }
        }
        val androidUnitTest by getting {
            dependencies {
                // Corre en la JVM local (no Robolectric): valida core/crypto,
                // core/protocol/* y el resto de androidMain sin ningún teléfono.
                implementation(kotlin("test"))
            }
        }
        // val iosMain by getting // vacío, comentado — ver nota arriba
    }
}

android {
    namespace = "co.sismomesh.core"
    compileSdk = 35
    defaultConfig {
        minSdk = 26
    }
    sourceSets {
        getByName("main") {
            // Clases Java generadas por protoc (protocol/codegen/gen_kotlin.sh --java_out).
            java.srcDir("src/androidMain/java")
        }
    }
}

// Regla verificada por arch-guard (Konsist + .importlinter):
// :core:domain NO importa android.*, androidx.*, io.ktor.*, ni ningún SDK.
// :core:application solo importa :core:domain y sus propios puertos.
