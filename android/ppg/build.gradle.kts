plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "co.helius.android.ppg"
    compileSdk = 35
    defaultConfig { minSdk = 26 }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation(project(":core"))

    implementation(libs.androidx.camera.core)
    implementation(libs.androidx.camera.camera2)
    implementation(libs.androidx.camera.lifecycle)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.kotlinx.coroutines.guava)

    // Activar cuando exista un modelo aprobado y el adaptador LiteRT se implemente
    // en :android:inference (ver core/signal/ppg/SignalModelRunner.kt).
    // implementation(libs.litert)
}
