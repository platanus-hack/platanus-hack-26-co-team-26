plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "co.helius.android.ppg"
    compileSdk = 35
    lint {
        // AndroidX lint 8.7 + Kotlin 2.1 puede romper el detector sobre
        // MotionSampler aunque no haya LiveData en este módulo.
        disable += "NullSafeMutableLiveData"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }
    defaultConfig { minSdk = 26 }
    kotlinOptions { jvmTarget = "21" }
}

dependencies {
    implementation(project(":core"))
    implementation(libs.androidx.camera.core)
    implementation(libs.androidx.camera.camera2)
    implementation(libs.androidx.camera.lifecycle)
    implementation(libs.androidx.camera.view)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.kotlinx.coroutines.core)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.kotlinx.coroutines.guava)

    // Activar cuando exista un modelo aprobado y el adaptador LiteRT se implemente
    // en :android:inference (ver core/signal/ppg/SignalModelRunner.kt).
    // implementation(libs.litert)
}
