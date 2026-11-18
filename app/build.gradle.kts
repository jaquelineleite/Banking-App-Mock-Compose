import java.util.Properties

plugins {
    with(libs.plugins) {
        alias(android.application)
        alias(kotlin.android)
        alias(compose.compiler)
        alias(ksp)
    }
}

val keystorePropertiesFile = rootProject.file("keystore.properties")
val keystoreProperties = keystorePropertiesFile.takeIf { it.isFile }?.let { propertiesFile ->
    Properties().apply {
        propertiesFile.inputStream().use { load(it) }
        val requiredKeys = listOf("keyAlias", "keyPassword", "storeFile", "storePassword")
        val missingKeys = requiredKeys.filter { getProperty(it).isNullOrBlank() }
        if (missingKeys.isNotEmpty()) {
            throw GradleException("Propriedades de assinatura ausentes: ${missingKeys.joinToString()}")
        }
    }
}

android {
    namespace = "by.alexandr7035.banking"
    compileSdk = 35

    keystoreProperties?.let { properties ->
        signingConfigs.create("config") {
            keyAlias = properties.getProperty("keyAlias")
            keyPassword = properties.getProperty("keyPassword")
            storeFile = properties.getProperty("storeFile")?.let { file(it) }
            storePassword = properties.getProperty("storePassword")
        }
    }

    defaultConfig {
        applicationId = "by.alexandr7035.banking"
        minSdk = 23
        targetSdk = 34
        versionCode = 200
        versionName = "1.1"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables.useSupportLibrary = true
    }

    buildTypes {
        getByName("release") {
            signingConfigs.findByName("config")?.let { signingConfig = it }
            isMinifyEnabled = true
            proguardFiles(
                    getDefaultProguardFile("proguard-android-optimize.txt"),
                    "proguard-rules.pro"
            )
        }
        getByName("debug") {
            signingConfigs.findByName("config")?.let { signingConfig = it }
            applicationIdSuffix = ".debug"
            isDebuggable = true
            versionNameSuffix = ".debug"
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }

    packaging {
        resources.excludes.add("/META-INF/{AL2.0,LGPL2.1}")
    }
}

if (keystoreProperties == null) {
    val requireReleaseSigning = tasks.register("requireReleaseSigning") {
        doFirst {
            throw GradleException("Configure keystore.properties para gerar um APK ou AAB release.")
        }
    }
    tasks.matching { it.name in setOf("packageRelease", "packageReleaseBundle") }
        .configureEach { dependsOn(requireReleaseSigning) }
}

dependencies {
    with(libs) {

        // Android core dependencies
        implementation(androidx.core.ktx)
        implementation(androidx.ui)
        implementation(androidx.material3)
        implementation(androidx.core.splashscreen)
        implementation(androidx.work.runtime.ktx)

        // SL
        implementation(bundles.koin)

        // Images
        implementation(bundles.coil)

        // Room
        implementation(bundles.room)
        ksp(room.compiler)

        // Lifecycle
        implementation(lifecycle.runtime.compose)
        implementation(lifecycle.runtime.ktx)

        // Compose
        implementation(platform(compose.bom))
        implementation(compose.activity)
        implementation(compose.shimmer)
        implementation(compose.state.events)
        implementation(compose.navigation)
        implementation(compose.graphics)
        implementation(compose.tooling.preview)
        implementation(compose.fonts)
        implementation(compose.paging)
        implementation(compose.constraintlayout)

        // Security
        implementation(androidx.security.crypto)
        implementation(androidx.biometric.ktx)

        // Utils
        implementation(permissionx)
        implementation(ksprefs)

        // QR code
        with(zxing) {
            //noinspection GradleDependency
            implementation(core)
            implementation(android) {
                isTransitive = false
            }
        }

        // Test dependencies
        testImplementation(junit)
        androidTestImplementation(androidx.junit)
        androidTestImplementation(androidx.espresso.core)
        androidTestImplementation(platform(compose.bom))
        androidTestImplementation(androidx.ui.test.junit4)

        // Debug dependencies
        debugImplementation(compose.tooling)
        debugImplementation(androidx.ui.test.manifest)
    }
}
