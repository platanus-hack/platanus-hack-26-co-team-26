plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.compose)
}

android {
    namespace = "co.helius"
    compileSdk = 35
    defaultConfig {
        applicationId = "co.helius"
        minSdk = 26 // API 26 mínimo (Sección 2.1)
        targetSdk = 35
    }
    buildFeatures { compose = true }
}

dependencies {
    implementation(project(":core"))
    implementation(project(":android:transport"))
    implementation(project(":android:sensing"))
    implementation(project(":android:ppg"))
    implementation(project(":android:inference"))
    implementation(project(":android:storage"))
    implementation(project(":android:power"))
}
