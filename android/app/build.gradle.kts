plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.compose)
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "co.helius"
    compileSdk = 35
    lint {
        // Evita un crash del detector NullSafeMutableLiveData con Kotlin 2.1;
        // el shell Compose no usa LiveData.
        disable += "NullSafeMutableLiveData"
        disable += "RememberInComposition"
        disable += "FrequentlyChangingValue"
        disable += "AutoboxingStateCreation"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }
    defaultConfig {
        applicationId = "co.helius"
        minSdk = 26 // API 26 mínimo (Sección 2.1)
        targetSdk = 35
    }
    buildFeatures { compose = true }
}

dependencies {
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.camera.view)
    implementation(libs.kotlinx.coroutines.core)
    implementation(project(":core"))
    implementation(project(":android:transport"))
    implementation(project(":android:sensing"))
    implementation(project(":android:ppg"))
    implementation(project(":android:inference"))
    implementation(project(":android:storage"))
    implementation(project(":android:power"))
}
