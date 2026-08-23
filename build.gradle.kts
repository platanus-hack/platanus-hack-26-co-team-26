plugins {
    alias(libs.plugins.kotlin.multiplatform) apply false
    alias(libs.plugins.kotlin.android) apply false
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.android.library) apply false
    alias(libs.plugins.compose) apply false
    alias(libs.plugins.ktlint) apply false
    alias(libs.plugins.detekt) apply false
    alias(libs.plugins.konsist) apply false
}

// arch-guard (Section 4, regla no negociable): :core:domain no puede importar
// android.*, androidx.*, io.ktor.*, ni ningún SDK de plataforma.
// Verificado en CI por .github/workflows/arch-guard.yml (Konsist + import-linter).
