plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "co.helius.android.transport"
    compileSdk = 35
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }
    defaultConfig { minSdk = 26 }
    kotlinOptions { jvmTarget = "21" }
}

dependencies {
    implementation(project(":core"))
    implementation(libs.androidx.core.ktx)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.play.services.nearby)
    // @RequiresPermission: declara el permiso en la firma para que el lint de AGP
    // lo verifique en el llamador, en vez de silenciarlo con @SuppressLint.
    implementation(libs.androidx.annotation)
}
