plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "co.helius.android.sensing"
    compileSdk = 35
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }
    defaultConfig { minSdk = 26 }
}

dependencies {
    implementation(project(":core"))
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.kotlinx.coroutines.core)
    // LocationManagerCompat / ContextCompat: backport de getCurrentLocation (API 30)
    // y getMainExecutor (API 28) hasta el minSdk 26 del proyecto.
    implementation(libs.androidx.core.ktx)
}
