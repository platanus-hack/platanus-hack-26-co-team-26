package co.helius

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.camera.view.PreviewView
import co.helius.android.sensing.AndroidMotionSensorSource
import co.helius.android.sensing.SensorManagerMotionAdapter
import co.helius.android.ppg.CameraPpgCaptureSource
import co.helius.auth.DevAuthRepository
import co.helius.core.application.ports.LocationPermissionState
import co.helius.core.application.ports.MotionSample
import co.helius.core.signal.motion.ActivityState
import co.helius.core.signal.motion.DeterministicActivityClassifier
import co.helius.core.signal.motion.MotionClassification
import co.helius.core.signal.ppg.PpgPipeline
import co.helius.core.signal.ppg.PpgAssessment
import co.helius.core.signal.ppg.PulseEstimate
import co.helius.core.signal.ppg.VerificationStatus
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.launch
import kotlin.math.PI
import kotlin.math.sin

private val Canvas = Color(0xFF0D1518)
private val SurfaceDark = Color(0xFF141E22)
private val Border = Color(0xFF2E3B3F)
private val TextPrimary = Color(0xFFEDF1ED)
private val TextSecondary = Color(0xFFAEB9B6)
private val RescueTeal = Color(0xFF58A69E)
private val Warning = Color(0xFFC89A58)
private val Critical = Color(0xFFD26A66)

private enum class Route { LOGIN, REGISTER, LOCATION_ONBOARDING, HOME, MAP, EMERGENCY, MOTION, PPG, NEARBY, TRUSTED_CONTACTS, PERMISSIONS, DIAGNOSTICS, SETTINGS }

@Composable
fun HeliosMobile() {
    var route by remember { mutableStateOf(Route.LOGIN) }
    var permission by remember { mutableStateOf<LocationPermissionState>(LocationPermissionState.NotRequested) }
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
        permission = when {
            result[Manifest.permission.ACCESS_FINE_LOCATION] == true -> LocationPermissionState.Precise
            result[Manifest.permission.ACCESS_COARSE_LOCATION] == true -> LocationPermissionState.Approximate
            else -> LocationPermissionState.Denied
        }
        route = Route.HOME
    }
    MaterialTheme {
        Surface(color = Canvas, modifier = Modifier.fillMaxSize()) {
            when (route) {
                Route.LOGIN -> LoginScreen(onLogin = { route = Route.LOCATION_ONBOARDING }, onRegister = { route = Route.REGISTER })
                Route.REGISTER -> RegistrationScreen(onRegistered = { route = Route.LOCATION_ONBOARDING }, onBack = { route = Route.LOGIN })
                Route.LOCATION_ONBOARDING -> LocationExplanation(onContinue = { launcher.launch(arrayOf(Manifest.permission.ACCESS_COARSE_LOCATION, Manifest.permission.ACCESS_FINE_LOCATION)) }, onSkip = { route = Route.HOME })
                else -> MainScaffold(route = route, permission = permission, onRoute = { route = it }, onSignOut = { route = Route.LOGIN })
            }
        }
    }
}

@Composable
private fun LoginScreen(onLogin: () -> Unit, onRegister: () -> Unit) {
    val auth = remember { DevAuthRepository() }
    var username by remember { mutableStateOf("usuario") }
    var password by remember { mutableStateOf("") }
    var showPassword by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    AuthFrame(title = "Bienvenido a HELIOS", subtitle = "Acceso local de desarrollo · no requiere red") {
        OutlinedTextField(username, { username = it; error = null }, Modifier.fillMaxWidth(), label = { Text("Usuario") }, singleLine = true)
        Spacer(Modifier.height(12.dp))
        OutlinedTextField(password, { password = it; error = null }, Modifier.fillMaxWidth(), label = { Text("Contraseña") }, singleLine = true, visualTransformation = if (showPassword) VisualTransformation.None else PasswordVisualTransformation())
        Row(verticalAlignment = Alignment.CenterVertically) { Checkbox(showPassword, { showPassword = it }); Text("Mostrar contraseña", color = TextSecondary, fontSize = 12.sp) }
        error?.let { Text(it, color = Critical, fontSize = 12.sp) }
        Spacer(Modifier.height(12.dp))
        Button(onClick = { if (auth.login(username, password)) onLogin() else error = "Usa la cuenta de desarrollo: usuario / 123456" }, Modifier.fillMaxWidth(), colors = ButtonDefaults.buttonColors(containerColor = RescueTeal, contentColor = Canvas)) { Text("Iniciar sesión") }
        TextButton(onClick = { error = "La recuperación de contraseña no está conectada en modo local" }, Modifier.fillMaxWidth()) { Text("¿Olvidaste tu contraseña?") }
        TextButton(onClick = onRegister, Modifier.fillMaxWidth()) { Text("Crear cuenta local") }
        Text("Cuenta exclusiva de desarrollo. Conecta autenticación segura antes de publicar.", color = TextSecondary, fontSize = 11.sp)
    }
}

@Composable
private fun RegistrationScreen(onRegistered: () -> Unit, onBack: () -> Unit) {
    val auth = remember { DevAuthRepository() }
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var confirmation by remember { mutableStateOf("") }
    var accepted by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    AuthFrame(title = "Crea tu perfil local", subtitle = "Esta demo no guarda cuentas en un servidor") {
        OutlinedTextField(username, { username = it }, Modifier.fillMaxWidth(), label = { Text("Usuario") }, singleLine = true)
        Spacer(Modifier.height(10.dp))
        OutlinedTextField(password, { password = it }, Modifier.fillMaxWidth(), label = { Text("Contraseña") }, singleLine = true, visualTransformation = PasswordVisualTransformation())
        Spacer(Modifier.height(10.dp))
        OutlinedTextField(confirmation, { confirmation = it }, Modifier.fillMaxWidth(), label = { Text("Confirmar contraseña") }, singleLine = true, visualTransformation = PasswordVisualTransformation())
        Row(verticalAlignment = Alignment.CenterVertically) { Checkbox(accepted, { accepted = it }); Text("Entiendo que es un perfil local de desarrollo", color = TextSecondary, fontSize = 12.sp) }
        error?.let { Text(it, color = Critical, fontSize = 12.sp) }
        Button(onClick = { error = when { !accepted -> "Acepta el aviso del perfil local"; password != confirmation -> "Las contraseñas no coinciden"; !auth.register(username, password) -> "Usa al menos 6 caracteres"; else -> { onRegistered(); null } } }, Modifier.fillMaxWidth(), colors = ButtonDefaults.buttonColors(containerColor = RescueTeal, contentColor = Canvas)) { Text("Registrarme") }
        TextButton(onClick = onBack, Modifier.fillMaxWidth()) { Text("Volver a iniciar sesión") }
    }
}

@Composable
private fun AuthFrame(title: String, subtitle: String, content: @Composable () -> Unit) {
    Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
        Text("HELIOS", color = RescueTeal, fontSize = 14.sp)
        Spacer(Modifier.height(10.dp))
        Text(title, color = TextPrimary, fontSize = 28.sp)
        Text(subtitle, color = TextSecondary, fontSize = 12.sp)
        Spacer(Modifier.height(24.dp))
        content()
    }
}

@Composable
private fun LocationExplanation(onContinue: () -> Unit, onSkip: () -> Unit) {
    Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
        Text("La ubicación apoya la respuesta de emergencia", color = TextPrimary, fontSize = 26.sp)
        Spacer(Modifier.height(12.dp))
        Text("HELIOS usa la ubicación para la última posición utilizable y las instantáneas de emergencia. El historial permanece local por defecto. Puedes continuar sin acceso.", color = TextSecondary, fontSize = 15.sp)
        Spacer(Modifier.height(24.dp))
        Button(onClick = onContinue, Modifier.fillMaxWidth(), colors = ButtonDefaults.buttonColors(containerColor = RescueTeal, contentColor = Canvas)) { Text("Elegir acceso a ubicación") }
        TextButton(onClick = onSkip, Modifier.fillMaxWidth()) { Text("Continuar sin ubicación") }
    }
}

@Composable
private fun MainScaffold(route: Route, permission: LocationPermissionState, onRoute: (Route) -> Unit, onSignOut: () -> Unit) {
    Scaffold(containerColor = Canvas, bottomBar = { BottomNav(route, onRoute) }) { padding ->
        Box(Modifier.padding(padding).fillMaxSize()) {
            when (route) {
                Route.HOME -> HomeScreen(permission, onRoute)
                Route.MAP -> PlaceholderScreen("Mapa", "Base MapLibre lista para ubicación actual, precisión, agrupaciones, lugares frecuentes y unidades de rescate.", "El mapa sigue siendo opcional; la vista de radar local siempre está disponible.")
                Route.EMERGENCY -> PlaceholderScreen("Modo de emergencia", "NECESITO AYUDA / ESTOY A SALVO", "El estado de emergencia es explícito y nunca se infiere de sensores. El envío al backend no está conectado en modo local.")
                Route.MOTION -> MotionScreen()
                Route.PPG -> PpgScreen()
                Route.NEARBY -> PlaceholderScreen("Dispositivos cercanos", "Preparación BLE / Wi‑Fi Aware", "La comunicación entre dispositivos requiere software compatible, permisos y radios disponibles.")
                Route.TRUSTED_CONTACTS -> PlaceholderScreen("Contactos de confianza", "No hay contactos configurados", "Añade y administra contactos con consentimiento cuando exista conexión con el backend.")
                Route.PERMISSIONS -> PlaceholderScreen("Centro de permisos", "Ubicación · cámara · dispositivos cercanos · notificaciones", "Los permisos se solicitan de forma contextual y pueden rechazarse sin bloquear la aplicación.")
                Route.DIAGNOSTICS -> DiagnosticsScreen()
                Route.SETTINGS -> SettingsScreen(onSignOut)
                else -> HomeScreen(permission, onRoute)
            }
        }
    }
}

@Composable
private fun HomeScreen(permission: LocationPermissionState, onRoute: (Route) -> Unit) {
    LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item { Text("Tu centro de protección", color = TextSecondary, fontSize = 13.sp); Text("Estado de preparación", color = TextPrimary, fontSize = 26.sp) }
        item { StatusPanel("Preparación de emergencia", "PARCIAL", "Revisa permisos, sensores y conectividad antes de usarla", Warning) }
        item { Button(onClick = { onRoute(Route.EMERGENCY) }, Modifier.fillMaxWidth().height(56.dp), colors = ButtonDefaults.buttonColors(containerColor = Critical, contentColor = TextPrimary)) { Text("NECESITO AYUDA") } }
        item { Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) { StatusPanel("Ubicación", if (permission is LocationPermissionState.Precise) "PRECISA" else if (permission is LocationPermissionState.Approximate) "APROXIMADA" else "NO DISPONIBLE", "Estado del permiso", if (permission is LocationPermissionState.Denied || permission is LocationPermissionState.NotRequested) Warning else RescueTeal, Modifier.weight(1f)); StatusPanel("Batería", "NO DISPONIBLE", "Se conectará al estado del dispositivo", Warning, Modifier.weight(1f)) } }
        item { Text("Funciones disponibles", color = TextSecondary, fontSize = 12.sp) }
        item { ActionRow("Evidencia de movimiento", "Acelerómetro + giroscopio", { onRoute(Route.MOTION) }) }
        item { ActionRow("Evaluación fisiológica", "Señal PPG; no es ECG ni diagnóstico", { onRoute(Route.PPG) }) }
        item { ActionRow("Capacidades del dispositivo", "Revisa sensores, cámara y conectividad", { onRoute(Route.DIAGNOSTICS) }) }
        item { ActionRow("Modo de emergencia", "NECESITO AYUDA / ESTOY A SALVO", { onRoute(Route.EMERGENCY) }) }
        item { ActionRow("Dispositivos cercanos", "Preparación BLE y retransmisión", { onRoute(Route.NEARBY) }) }
        item { ActionRow("Contactos de confianza", "Consentimiento y estado de envío", { onRoute(Route.TRUSTED_CONTACTS) }) }
        item { ActionRow("Centro de permisos", "Revisa ubicación, cámara y dispositivos cercanos", { onRoute(Route.PERMISSIONS) }) }
    }
}

@Composable
private fun MotionScreen() {
    val context = LocalContext.current
    var sample by remember { mutableStateOf<MotionSample?>(null) }
    var evidence by remember { mutableStateOf<MotionClassification?>(null) }
    LaunchedEffect(Unit) { AndroidMotionSensorSource(context).observeMotion().collectLatest { sample = it } }
    // Complemento del stream anterior: el mismo par acelerómetro+giroscopio, pero
    // pasado por DSP (RMS/entropía espectral) y clasificado -- ver
    // core/signal/motion/ActivityEvidenceClassifier.kt. La lectura simple de arriba
    // muestra números crudos; esto muestra si constituyen evidencia de movimiento
    // intencional (y el patrón de ráfagas tipo SOS, si lo hay).
    LaunchedEffect(Unit) {
        val classifier = DeterministicActivityClassifier()
        SensorManagerMotionAdapter(context).observeMotionWindows().collectLatest { window ->
            evidence = classifier.classify(window)
        }
    }
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Evidencia de movimiento", color = TextPrimary, fontSize = 26.sp)
        Text("El movimiento es evidencia del dispositivo; no demuestra vida ni lesiones.", color = TextSecondary)
        StatusPanel("Estado actual", sample?.state?.name ?: "ESPERANDO SENSOR", "Ventana del acelerómetro", RescueTeal)
        sample?.let { SensorValues(it) } ?: StatusPanel("Estado del sensor", "Recopilando", "El dispositivo puede no exponer un acelerómetro", Warning)
        evidence?.let { ActivityEvidencePanel(it) }
    }
}

@Composable
private fun SensorValues(sample: MotionSample) {
    Column(Modifier.fillMaxWidth().background(SurfaceDark, RoundedCornerShape(12.dp)).padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Métricas de la ventana", color = TextPrimary, fontSize = 16.sp)
        Text("RMS ${"%.2f".format(sample.accelerationRms)} · varianza ${"%.2f".format(sample.accelerationVariance)}", color = TextSecondary)
        Text("Giroscopio ${sample.angularVelocityRads?.let { "disponible · %.2f rad/s".format(it) } ?: "no disponible"}", color = TextSecondary)
    }
}

@Composable
private fun ActivityEvidencePanel(evidence: MotionClassification) {
    Column(Modifier.fillMaxWidth().background(SurfaceDark, RoundedCornerShape(12.dp)).padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Evidencia de actividad (entropía espectral + patrón)", color = TextPrimary, fontSize = 16.sp)
        Text(
            evidence.activityState.name,
            color = if (evidence.activityState == ActivityState.PURPOSEFUL_MOTION) RescueTeal else TextSecondary,
        )
        Text("Confianza de movimiento intencional ${"%.0f".format(evidence.purposefulMotionConfidence * 100)}%", color = TextSecondary)
        if (evidence.pattern.isNotEmpty()) {
            Text("Patrón de ráfagas detectado: ${evidence.pattern}", color = RescueTeal)
        }
    }
}

@Composable
private fun PpgScreen() {
    var assessment by remember { mutableStateOf<PpgAssessment?>(null) }
    var firstSamples by remember { mutableStateOf<DoubleArray?>(null) }
    var firstSampleRate by remember { mutableStateOf(30.0) }
    var capturing by remember { mutableStateOf(false) }
    val context = LocalContext.current
    val lifecycleOwner = androidx.lifecycle.compose.LocalLifecycleOwner.current
    var previewView by remember { mutableStateOf<PreviewView?>(null) }
    val scope = rememberCoroutineScope()
    fun capture(verification: Boolean) {
        scope.launch {
            capturing = true
            val captured = runCatching { capturePpg(context, lifecycleOwner, previewView) }.getOrNull()
            capturing = false
            if (captured == null) {
                assessment = PpgPipeline().assess(DoubleArray(0), 30.0)
                return@launch
            }
            val (samples, sampleRate) = captured
            if (verification && firstSamples != null) {
                assessment = PpgPipeline().assess(firstSamples!!, firstSampleRate, samples)
            } else {
                firstSamples = samples
                firstSampleRate = sampleRate
                assessment = PpgPipeline().assess(samples, sampleRate)
            }
        }
    }
    val cameraPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) capture(verification = false)
    }
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Evaluación fisiológica", color = TextPrimary, fontSize = 26.sp)
        Text("Coloca suavemente la yema del dedo sobre la cámara trasera y el flash. Una lectura inusual siempre solicita una segunda verificación.", color = TextSecondary)
        AndroidView(factory = { PreviewView(context).also { previewView = it } }, modifier = Modifier.fillMaxWidth().height(210.dp))
        StatusPanel("Estado de captura", if (assessment == null) "LISTO" else "COMPLETO", "Solo PPG · el ECG requiere un sensor externo", RescueTeal)
        Button(onClick = {
            if (context.checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
                capture(verification = assessment?.status == VerificationStatus.SECOND_VERIFICATION_REQUIRED)
            } else cameraPermission.launch(Manifest.permission.CAMERA)
        }, Modifier.fillMaxWidth(), enabled = !capturing, colors = ButtonDefaults.buttonColors(containerColor = RescueTeal, contentColor = Canvas)) {
            Text(if (capturing) "Capturando señal de 12 segundos…" else if (assessment?.status == VerificationStatus.SECOND_VERIFICATION_REQUIRED) "Realizar segunda verificación" else "Capturar con cámara y flash")
        }
        OutlinedButton(onClick = {
            val synthetic = demoPulseSamples()
            firstSamples = synthetic.first
            firstSampleRate = synthetic.second
            assessment = PpgPipeline().assess(synthetic.first, synthetic.second)
        }, Modifier.fillMaxWidth(), enabled = !capturing) { Text("Ejecutar muestra sintética local") }
        assessment?.let { checked ->
            val observation = checked.estimate
            val color = when (checked.status) {
                VerificationStatus.REPEATED_ANOMALY -> Warning
                VerificationStatus.SECOND_VERIFICATION_REQUIRED, VerificationStatus.INCONCLUSIVE_RECHECK -> Warning
                VerificationStatus.ACCEPTED -> RescueTeal
            }
            StatusPanel("Frecuencia cardíaca estimada", "${observation.bpm.toInt()} BPM", "${checked.status.name} · calidad ${(observation.sqi * 100).toInt()}% · ${observation.method}", color)
            Text(checked.message, color = color, fontSize = 13.sp)
            if (checked.status == VerificationStatus.REPEATED_ANOMALY) {
                Text("Las lecturas anómalas repetidas son solo una señal de prueba; no confirman bradicardia ni otra condición.", color = TextSecondary, fontSize = 12.sp)
            }
        }
        Text("Estimación observacional de una señal; no es un diagnóstico clínico.", color = TextSecondary, fontSize = 12.sp)
    }
}

private suspend fun capturePpg(
    context: Context,
    lifecycleOwner: androidx.lifecycle.LifecycleOwner,
    previewView: PreviewView?,
): Pair<DoubleArray, Double>? {
    val frames = CameraPpgCaptureSource(context, lifecycleOwner, previewView).captureSession(12).toList()
    if (frames.size < 30) return null
    return frames.map { it.green }.toDoubleArray() to (frames.size / 12.0)
}

private fun demoPulseSamples(): Pair<DoubleArray, Double> {
    val fs = 30.0
    val samples = DoubleArray(360) { index -> 0.5 + 0.1 * sin(2 * PI * 1.2 * index / fs) }
    return samples to fs
}

@Composable
private fun DiagnosticsScreen() {
    val context = LocalContext.current
    val manager = remember { context.getSystemService(Context.SENSOR_SERVICE) as android.hardware.SensorManager }
    val packageManager = context.packageManager
    val capabilities = listOf(
        "GPS" to packageManager.hasSystemFeature("android.hardware.location.gps"),
        "Acelerómetro" to (manager.getDefaultSensor(android.hardware.Sensor.TYPE_ACCELEROMETER) != null),
        "Giroscopio" to (manager.getDefaultSensor(android.hardware.Sensor.TYPE_GYROSCOPE) != null),
        "Cámara" to packageManager.hasSystemFeature("android.hardware.camera"),
        "Bluetooth LE" to packageManager.hasSystemFeature("android.hardware.bluetooth_le"),
    )
    LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        item { Text("Capacidades del dispositivo", color = TextPrimary, fontSize = 26.sp); Text("No se asume hardware; los sensores no disponibles degradan de forma segura.", color = TextSecondary) }
        items(capabilities.size) { index -> StatusPanel(capabilities[index].first, if (capabilities[index].second) "DISPONIBLE" else "NO DISPONIBLE", "Capacidad en tiempo de ejecución", if (capabilities[index].second) RescueTeal else Warning) }
    }
}

@Composable
private fun SettingsScreen(onSignOut: () -> Unit) {
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Privacidad y configuración", color = TextPrimary, fontSize = 26.sp)
        StatusPanel("Historial de ubicación", "LOCAL POR DEFECTO", "Puedes borrarlo del dispositivo", RescueTeal)
        StatusPanel("Envío de emergencia", "APAGADO", "Solo se comparte un resumen con consentimiento", Warning)
        StatusPanel("Envío fisiológico", "APAGADO", "La señal PPG cruda permanece local", Warning)
        OutlinedButton(onClick = onSignOut, Modifier.fillMaxWidth()) { Text("Cerrar sesión") }
    }
}

@Composable
private fun PlaceholderScreen(title: String, value: String, detail: String) {
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text(title, color = TextPrimary, fontSize = 26.sp)
        StatusPanel(title, value, detail, RescueTeal)
        Text("Esta pantalla base es local y determinista. Conecta el repositorio o adaptador del backend sin cambiar el contrato de UI.", color = TextSecondary, fontSize = 12.sp)
    }
}

@Composable
private fun BottomNav(route: Route, onRoute: (Route) -> Unit) {
    Row(Modifier.fillMaxWidth().background(SurfaceDark).navigationBarsPadding().padding(8.dp), horizontalArrangement = Arrangement.SpaceEvenly) {
        listOf(Route.HOME to "Inicio", Route.MAP to "Mapa", Route.MOTION to "Movimiento", Route.PPG to "Fisiología", Route.SETTINGS to "Perfil").forEach { (target, label) -> TextButton(onClick = { onRoute(target) }) { Text(if (route == target) "• $label" else label, color = if (route == target) RescueTeal else TextSecondary, fontSize = 11.sp) } }
    }
}

@Composable
private fun ActionRow(title: String, detail: String, onClick: () -> Unit) {
    OutlinedButton(onClick = onClick, Modifier.fillMaxWidth(), shape = RoundedCornerShape(10.dp)) { Column(Modifier.fillMaxWidth()) { Text(title, color = TextPrimary); Text(detail, color = TextSecondary, fontSize = 11.sp) } }
}

@Composable
private fun StatusPanel(title: String, value: String, detail: String, accent: Color, modifier: Modifier = Modifier) {
    Column(modifier.fillMaxWidth().background(SurfaceDark, RoundedCornerShape(12.dp)).border(1.dp, Border, RoundedCornerShape(12.dp)).padding(14.dp)) { Text(title, color = TextSecondary, fontSize = 11.sp); Spacer(Modifier.height(5.dp)); Text(value, color = accent, fontSize = 18.sp); Text(detail, color = TextSecondary, fontSize = 11.sp) }
}
