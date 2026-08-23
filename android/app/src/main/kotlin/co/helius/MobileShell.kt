package co.helius

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ApplicationInfo
import android.net.wifi.WifiManager
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.Canvas as ComposeCanvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.widthIn
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
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.camera.view.PreviewView
import co.helius.android.sensing.AndroidMotionSensorSource
import co.helius.android.sensing.AndroidLocationSource
import co.helius.android.sensing.SensorManagerMotionAdapter
import co.helius.android.ppg.CameraPpgCaptureSource
import co.helius.android.transport.NearbyConnectionsTransport
import co.helius.android.transport.NearbyDiagnostics
import co.helius.android.transport.NearbyEvent
import co.helius.auth.LocalAccountRepository
import co.helius.core.application.ports.LocationPermissionState
import co.helius.core.application.ports.LocationAccuracy
import co.helius.core.application.ports.MotionSample
import co.helius.core.location.LocationSample
import co.helius.core.emergency.AssistanceConfirmation
import co.helius.core.emergency.EmergencyController
import co.helius.core.emergency.EmergencyEvent
import co.helius.core.emergency.EmergencyIncident
import co.helius.core.emergency.HeliosOperationalMode
import co.helius.core.emergency.IncidentSource
import co.helius.core.signal.ppg.PpgPipeline
import co.helius.core.signal.ppg.PpgAssessment
import co.helius.core.signal.ppg.PulseEstimate
import co.helius.core.signal.ppg.VerificationStatus
import co.helius.core.signal.motion.ActivityState
import co.helius.core.signal.motion.DeterministicActivityClassifier
import co.helius.core.signal.motion.MotionClassification
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.math.PI
import kotlin.math.sin

private enum class Route { LOGIN, REGISTER, LOCATION_ONBOARDING, HOME, MAP, EMERGENCY, MOTION, PPG, NEARBY, TRUSTED_CONTACTS, REPORTS, ALERTS, PERMISSIONS, DIAGNOSTICS, NETWORK_LAB, SETTINGS }

@Composable
fun HeliosMobile() {
    val context = LocalContext.current
    val auth = remember { LocalAccountRepository(context) }
    var route by remember { mutableStateOf(if (auth.currentSession() == null) Route.LOGIN else Route.HOME) }
    val nearbyTransport = remember { NearbyConnectionsTransport(context) }
    val emergencyController = remember { EmergencyController() }
    val emergencyMode by emergencyController.mode.collectAsState()
    var permission by remember { mutableStateOf(readLocationPermissionState(context)) }
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
        permission = when {
            result[Manifest.permission.ACCESS_FINE_LOCATION] == true -> LocationPermissionState.Precise
            result[Manifest.permission.ACCESS_COARSE_LOCATION] == true -> LocationPermissionState.Approximate
            else -> LocationPermissionState.Denied
        }
        route = Route.HOME
    }
    val nearbyEnableLauncher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) {
        val state = readNearbyRadioState(context)
        if (state.permissionsGranted && (state.bluetoothEnabled || !state.bluetoothSupported)) nearbyTransport.start()
    }
    val nearbyPermissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
        val state = readNearbyRadioState(context)
        when {
            !state.permissionsGranted -> Unit
            state.bluetoothSupported && !state.bluetoothEnabled -> nearbyEnableLauncher.launch(Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE))
            else -> nearbyTransport.start()
        }
    }
    LaunchedEffect(emergencyMode) {
        when (val mode = emergencyMode) {
            is HeliosOperationalMode.AlertDisplay -> {
                delay(10_000L)
                emergencyController.dispatch(EmergencyEvent.AlertElapsed(System.currentTimeMillis()))
            }
            is HeliosOperationalMode.AwaitingResponse -> {
                val remaining = (mode.deadlineMs - System.currentTimeMillis()).coerceAtLeast(0L)
                delay(remaining)
                emergencyController.dispatch(EmergencyEvent.ResponseTimeout)
            }
            else -> Unit
        }
    }
    LaunchedEffect(emergencyMode) {
        if (emergencyMode is HeliosOperationalMode.Normal) {
            nearbyTransport.stop()
        } else {
            val state = readNearbyRadioState(context)
            when {
                !state.permissionsGranted -> nearbyPermissionLauncher.launch(nearbyPermissions())
                state.bluetoothSupported && !state.bluetoothEnabled -> nearbyEnableLauncher.launch(Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE))
                else -> nearbyTransport.start()
            }
        }
    }
    DisposableEffect(nearbyTransport) {
        onDispose { nearbyTransport.stop() }
    }

    HeliosTheme {
        Surface(color = Canvas, modifier = Modifier.fillMaxSize()) {
            when {
                emergencyMode != HeliosOperationalMode.Normal -> MainScaffold(
                    route = route,
                    permission = permission,
                    nearbyTransport = nearbyTransport,
                    emergencyMode = emergencyMode,
                    onRoute = { route = it },
                    onSignOut = { auth.signOut(); route = Route.LOGIN },
                    onEmergencyEvent = emergencyController::dispatch,
                )
                route == Route.LOGIN -> LoginScreen(
                    auth = auth,
                    onLogin = { route = Route.LOCATION_ONBOARDING },
                    onRegister = { route = Route.REGISTER },
                    onEmergency = { emergencyController.dispatch(EmergencyEvent.ManualSos(localIncident(IncidentSource.MANUAL_SOS))) },
                )
                route == Route.REGISTER -> RegistrationScreen(auth = auth, onRegistered = { route = Route.LOCATION_ONBOARDING }, onBack = { route = Route.LOGIN })
                route == Route.LOCATION_ONBOARDING -> LocationExplanation(onContinue = { launcher.launch(arrayOf(Manifest.permission.ACCESS_COARSE_LOCATION, Manifest.permission.ACCESS_FINE_LOCATION)) }, onSkip = { route = Route.HOME })
                else -> MainScaffold(
                    route = route,
                    permission = permission,
                    nearbyTransport = nearbyTransport,
                    emergencyMode = emergencyMode,
                    onRoute = { route = it },
                    onSignOut = { auth.signOut(); route = Route.LOGIN },
                    onEmergencyEvent = emergencyController::dispatch,
                )
            }
        }
    }
}

@Composable
private fun LoginScreen(auth: LocalAccountRepository, onLogin: () -> Unit, onRegister: () -> Unit, onEmergency: () -> Unit) {
    val debugBuild = (LocalContext.current.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
    var username by remember { mutableStateOf(if (debugBuild) LocalAccountRepository.DEMO_USERNAME else "") }
    var password by remember { mutableStateOf("") }
    var showPassword by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    PremiumAuthFrame(title = "Bienvenido a tu red de protección", subtitle = "Orientación, señales y personas importantes en un solo lugar.") {
        Column(
            Modifier.fillMaxWidth().background(GraphiteBlue.copy(alpha = .72f), RoundedCornerShape(18.dp)).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text("Iniciar sesión", color = TextPrimary, style = MaterialTheme.typography.titleLarge)
            OutlinedTextField(username, { username = it; error = null }, Modifier.fillMaxWidth(), label = { Text("Usuario") }, singleLine = true)
            OutlinedTextField(password, { password = it; error = null }, Modifier.fillMaxWidth(), label = { Text("Contraseña") }, singleLine = true, visualTransformation = if (showPassword) VisualTransformation.None else PasswordVisualTransformation())
            Row(verticalAlignment = Alignment.CenterVertically) { Checkbox(showPassword, { showPassword = it }); Text("Mostrar contraseña", color = TextSecondary, fontSize = 12.sp) }
            error?.let { Text(it, color = Critical, fontSize = 12.sp) }
            Button(onClick = { if (auth.login(username, password)) { auth.startSession(username); onLogin() } else error = "Usuario o contraseña no válidos en este dispositivo" }, Modifier.fillMaxWidth().height(52.dp), colors = ButtonDefaults.buttonColors(containerColor = HeliosSolar, contentColor = HeliosInk)) { Text("Entrar a HELIOS") }
            TextButton(onClick = { error = "La recuperación remota requiere un servidor de cuentas conectado" }, Modifier.fillMaxWidth()) { Text("¿Olvidaste tu contraseña?") }
            TextButton(onClick = onRegister, Modifier.fillMaxWidth()) { Text("Crear cuenta en este dispositivo") }
        }
        Spacer(Modifier.height(8.dp))
        OutlinedButton(onClick = onEmergency, Modifier.fillMaxWidth().height(50.dp)) { Text("Necesito ayuda sin iniciar sesión") }
        Text(if (debugBuild) "Cuenta local de prueba · DEBUG · usuario / 123456" else "Cuenta local protegida en este dispositivo", color = TextSecondary, fontSize = 11.sp)
    }
}

@Composable
private fun RegistrationScreen(auth: LocalAccountRepository, onRegistered: () -> Unit, onBack: () -> Unit) {
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var confirmation by remember { mutableStateOf("") }
    var accepted by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    PremiumAuthFrame(title = "Crea tu perfil", subtitle = "Un espacio local para probar la experiencia de Helios.") {
        Column(
            Modifier.fillMaxWidth().background(GraphiteBlue.copy(alpha = .72f), RoundedCornerShape(18.dp)).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text("Cuenta local", color = TextPrimary, style = MaterialTheme.typography.titleLarge)
            OutlinedTextField(username, { username = it }, Modifier.fillMaxWidth(), label = { Text("Usuario") }, singleLine = true)
            OutlinedTextField(password, { password = it }, Modifier.fillMaxWidth(), label = { Text("Contraseña") }, singleLine = true, visualTransformation = PasswordVisualTransformation())
            OutlinedTextField(confirmation, { confirmation = it }, Modifier.fillMaxWidth(), label = { Text("Confirmar contraseña") }, singleLine = true, visualTransformation = PasswordVisualTransformation())
            Row(verticalAlignment = Alignment.CenterVertically) { Checkbox(accepted, { accepted = it }); Text("Entiendo que este perfil es local", color = TextSecondary, fontSize = 12.sp) }
            error?.let { Text(it, color = Critical, fontSize = 12.sp) }
            Button(onClick = { error = when { !accepted -> "Acepta el aviso de cuenta local"; password != confirmation -> "Las contraseñas no coinciden"; !auth.register(username, password) -> "Usa un usuario de 3–32 caracteres y una contraseña de al menos 6"; else -> { auth.startSession(username); onRegistered(); null } } }, Modifier.fillMaxWidth().height(52.dp), colors = ButtonDefaults.buttonColors(containerColor = HeliosSolar, contentColor = HeliosInk)) { Text("Crear cuenta") }
        }
        TextButton(onClick = onBack, Modifier.fillMaxWidth()) { Text("Volver a iniciar sesión") }
    }
}

@Composable
private fun LocationExplanation(onContinue: () -> Unit, onSkip: () -> Unit) {
    HeliosBackdrop {
        Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
            Eyebrow("Segundo paso")
            Text("Una mejor orientación empieza por saber dónde estás", color = TextPrimary, style = MaterialTheme.typography.headlineLarge)
            Spacer(Modifier.height(14.dp))
            HeliosPulse(color = LocationSky)
            Spacer(Modifier.height(12.dp))
            Text("HELIOS usa la ubicación para la última posición utilizable y las instantáneas de emergencia. El historial permanece local por defecto. Puedes continuar sin acceso.", color = TextSecondary, style = MaterialTheme.typography.bodyLarge)
            Spacer(Modifier.height(22.dp))
            StatusPanel("Privacidad", "TÚ DECIDES", "El permiso puede cambiarse después desde Ajustes", LocationSky)
            Spacer(Modifier.height(16.dp))
            Button(onClick = onContinue, Modifier.fillMaxWidth().height(54.dp), colors = ButtonDefaults.buttonColors(containerColor = HeliosSolar, contentColor = HeliosInk)) { Text("Elegir acceso a ubicación") }
            TextButton(onClick = onSkip, Modifier.fillMaxWidth()) { Text("Continuar sin ubicación") }
        }
    }
}

@Composable
private fun MainScaffold(
    route: Route,
    permission: LocationPermissionState,
    nearbyTransport: NearbyConnectionsTransport,
    emergencyMode: HeliosOperationalMode,
    onRoute: (Route) -> Unit,
    onSignOut: () -> Unit,
    onEmergencyEvent: (EmergencyEvent) -> HeliosOperationalMode,
) {
    val showNavigation = emergencyMode is HeliosOperationalMode.Normal || emergencyMode is HeliosOperationalMode.EmergencySupport
    Scaffold(containerColor = Canvas, bottomBar = { if (showNavigation) BottomNav(route, onRoute) }) { padding ->
        Box(Modifier.padding(padding).statusBarsPadding().fillMaxSize()) {
            when (emergencyMode) {
                is HeliosOperationalMode.AlertDisplay -> SeismicAlertScreen(
                    incident = emergencyMode.incident,
                    onNeedsHelp = { onEmergencyEvent(EmergencyEvent.UserNeedsHelp) },
                    onSafe = { onEmergencyEvent(EmergencyEvent.UserSafe) },
                )
                is HeliosOperationalMode.AwaitingResponse -> AssistanceQuestionScreen(
                    onNeedsHelp = { onEmergencyEvent(EmergencyEvent.UserNeedsHelp) },
                    onSafe = { onEmergencyEvent(EmergencyEvent.UserSafe) },
                )
                is HeliosOperationalMode.EmergencySupport -> when (route) {
                    Route.MAP -> MapExperienceScreen(permission, onBack = { onRoute(Route.HOME) }, emergency = true)
                    Route.REPORTS -> OperationalListScreen("Reportes", "Observaciones con fuente, hora y nivel de confianza", "No hay reportes pendientes", onBack = { onRoute(Route.HOME) })
                    Route.ALERTS -> OperationalListScreen("Alertas recibidas", "Señales directas o retransmitidas, sin borrar evidencia", "No has recibido señales de asistencia", onBack = { onRoute(Route.HOME) })
                    Route.NEARBY -> NearbyNetworkScreen(transport = nearbyTransport, onBack = { onRoute(Route.HOME) })
                    Route.PPG -> PpgScreen(onBack = { onRoute(Route.HOME) })
                    else -> EmergencySupportScreen(
                        onRoute = onRoute,
                        onResolve = { onEmergencyEvent(EmergencyEvent.Resolve) },
                    )
                }
                is HeliosOperationalMode.AssistanceRequired -> if (route == Route.PPG) {
                    PpgScreen(onBack = { onRoute(Route.HOME) })
                } else {
                    AssistanceRequiredScreen(
                        confirmation = emergencyMode.confirmation,
                        onSafe = { onEmergencyEvent(EmergencyEvent.UserSafe) },
                        onNeedsHelp = { onEmergencyEvent(EmergencyEvent.UserNeedsHelp) },
                        onPpg = { onRoute(Route.PPG) },
                    )
                }
                HeliosOperationalMode.Normal -> when (route) {
                    Route.HOME -> HomeScreen(permission, onRoute, onEmergencyEvent)
                    Route.MAP -> MapExperienceScreen(permission, onBack = { onRoute(Route.HOME) })
                    Route.EMERGENCY -> EmergencyOverviewScreen(onNeedsHelp = { onEmergencyEvent(EmergencyEvent.ManualSos(localIncident(IncidentSource.MANUAL_SOS))) }, onDemo = { onEmergencyEvent(EmergencyEvent.EarthquakeDetected(localIncident(IncidentSource.DEMO))) })
                    Route.MOTION -> MotionScreen()
                    Route.PPG -> PpgScreen()
                    Route.NEARBY -> NearbyNetworkScreen(transport = nearbyTransport, onBack = { onRoute(Route.HOME) })
                    Route.TRUSTED_CONTACTS -> PeopleScreen(onBack = { onRoute(Route.HOME) })
                    Route.REPORTS -> OperationalListScreen("Reportes", "Observaciones con fuente, hora y nivel de confianza", "No hay reportes pendientes", onBack = { onRoute(Route.HOME) })
                    Route.ALERTS -> OperationalListScreen("Alertas recibidas", "Señales directas o retransmitidas, sin borrar evidencia", "No has recibido señales de asistencia", onBack = { onRoute(Route.HOME) })
                    Route.PERMISSIONS -> PermissionsScreen(permission, onRoute)
                    Route.DIAGNOSTICS -> DiagnosticsScreen(nearbyTransport = nearbyTransport, onOpenLab = { onRoute(Route.NETWORK_LAB) })
                    Route.NETWORK_LAB -> NetworkLabScreen(nearbyTransport, onBack = { onRoute(Route.DIAGNOSTICS) })
                    Route.SETTINGS -> SettingsScreen(onSignOut)
                    else -> HomeScreen(permission, onRoute, onEmergencyEvent)
                }
            }
        }
    }
}

@Composable
private fun HomeScreen(
    permission: LocationPermissionState,
    onRoute: (Route) -> Unit,
    onEmergencyEvent: (EmergencyEvent) -> HeliosOperationalMode,
) {
    val context = LocalContext.current
    val debugBuild = (context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
    val currentLocation = rememberCurrentLocation(permission)
    BoxWithConstraints {
        val contentWidth = if (maxWidth >= 720.dp) 760.dp else maxWidth
        LazyColumn(Modifier.fillMaxSize().widthIn(max = contentWidth).padding(horizontal = 16.dp, vertical = 18.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
                    Column(Modifier.weight(1f)) {
                        Eyebrow("HELIOS · MODO NORMAL")
                        Text("Protección activa", color = TextPrimary, style = MaterialTheme.typography.headlineLarge)
                        Text("Una vista clara de tu posición, tu red y tu preparación.", color = TextSecondary, style = MaterialTheme.typography.bodyMedium)
                    }
                    HeliosPulse(color = HeliosSolar, active = false)
                }
            }
            item { MapPreviewCard(permission, currentLocation, onOpen = { onRoute(Route.MAP) }) }
            item {
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    ReadinessMetric("Ubicación", when (permission) { is LocationPermissionState.Precise -> "Precisa"; is LocationPermissionState.Approximate -> "Aproximada"; else -> "Pendiente" }, if (permission is LocationPermissionState.NotRequested || permission is LocationPermissionState.Denied) Warning else LocationSky, Modifier.weight(1f))
                    ReadinessMetric("Red Helios", "Lista para buscar", AquaSignal, Modifier.weight(1f))
                    ReadinessMetric("Batería", "No disponible", Warning, Modifier.weight(1f))
                }
            }
            item {
                Button(onClick = { onEmergencyEvent(EmergencyEvent.ManualSos(localIncident(IncidentSource.MANUAL_SOS))) }, Modifier.fillMaxWidth().height(58.dp), colors = ButtonDefaults.buttonColors(containerColor = SignalCoral, contentColor = PureWarm), shape = RoundedCornerShape(16.dp)) { Text("NECESITO AYUDA", style = MaterialTheme.typography.labelLarge) }
            }
            item { Text("Acciones rápidas", color = TextSecondary, style = MaterialTheme.typography.labelMedium) }
            item {
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    ActionTile("Movimiento", "Acelerómetro + giroscopio", { onRoute(Route.MOTION) }, Modifier.weight(1f))
                    ActionTile("Fisiología", "Registro PPG", { onRoute(Route.PPG) }, Modifier.weight(1f))
                }
            }
            item {
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    ActionTile("Red Helios", "Dispositivos cercanos y relay", { onRoute(Route.NEARBY) }, Modifier.weight(1f))
                    ActionTile("Permisos", "Privacidad y capacidades", { onRoute(Route.PERMISSIONS) }, Modifier.weight(1f))
                }
            }
            if (debugBuild) {
                item { OutlinedButton(onClick = { onEmergencyEvent(EmergencyEvent.EarthquakeDetected(localIncident(IncidentSource.DEMO))) }, Modifier.fillMaxWidth().height(50.dp), shape = RoundedCornerShape(14.dp)) { Text("Simular alerta sísmica · DEBUG") } }
            }
        }
    }
}

@Composable
private fun MapPreviewCard(permission: LocationPermissionState, location: LocationSample?, onOpen: () -> Unit) {
    Column(Modifier.fillMaxWidth().background(DeepOcean, RoundedCornerShape(20.dp)).border(1.dp, Hairline, RoundedCornerShape(20.dp)).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Eyebrow("ORIENTACIÓN ESPACIAL")
                Text("Posición local", color = TextPrimary, style = MaterialTheme.typography.titleLarge)
                Text(if (location != null) "Señal actual · ±${location.horizontalAccuracyMeters?.toInt() ?: "—"} m" else "Sin lectura actual · no se muestra una coordenada inventada", color = TextSecondary, style = MaterialTheme.typography.bodyMedium)
            }
            TextButton(onClick = onOpen) { Text("Abrir orientación") }
        }
        MapSurface(permission, location, Modifier.fillMaxWidth().height(168.dp), compact = true)
    }
}

@Composable
private fun MapSurface(permission: LocationPermissionState, location: LocationSample?, modifier: Modifier, compact: Boolean = false) {
    Box(modifier.clip(RoundedCornerShape(if (compact) 16.dp else 22.dp)).background(Brush.verticalGradient(listOf(GraphiteBlue, DeepOcean)))) {
        ComposeCanvas(Modifier.fillMaxSize()) {
            val spacing = if (compact) 42.dp.toPx() else 56.dp.toPx()
            var x = 0f
            while (x < size.width) {
                drawLine(Hairline.copy(alpha = .48f), androidx.compose.ui.geometry.Offset(x, 0f), androidx.compose.ui.geometry.Offset(x, size.height), 1.dp.toPx())
                x += spacing
            }
            var y = 0f
            while (y < size.height) {
                drawLine(Hairline.copy(alpha = .48f), androidx.compose.ui.geometry.Offset(0f, y), androidx.compose.ui.geometry.Offset(size.width, y), 1.dp.toPx())
                y += spacing
            }
            val route = Path().apply {
                moveTo(size.width * .08f, size.height * .82f)
                cubicTo(size.width * .28f, size.height * .52f, size.width * .42f, size.height * .68f, size.width * .62f, size.height * .34f)
                cubicTo(size.width * .74f, size.height * .16f, size.width * .82f, size.height * .28f, size.width * .94f, size.height * .12f)
            }
            drawPath(route, LocationSky.copy(alpha = .55f), style = Stroke(width = 3.dp.toPx()))
            drawCircle(HeliosSolar.copy(alpha = .24f), radius = 16.dp.toPx(), center = androidx.compose.ui.geometry.Offset(size.width * .62f, size.height * .34f))
            if (location != null) {
                drawCircle(HeliosSolar, radius = 6.dp.toPx(), center = androidx.compose.ui.geometry.Offset(size.width * .62f, size.height * .34f))
            }
        }
        Column(Modifier.align(Alignment.TopStart).padding(14.dp)) {
            Text("ORIENTACIÓN HELIOS", color = WarmCloud, style = MaterialTheme.typography.labelMedium, letterSpacing = 1.2.sp)
            Text("SUPERFICIE LOCAL · SIN TESELAS", color = Mist, style = MaterialTheme.typography.labelMedium)
        }
        if (location != null) {
            Text("TÚ", Modifier.align(Alignment.Center).background(HeliosSolar, RoundedCornerShape(8.dp)).padding(horizontal = 8.dp, vertical = 4.dp), color = HeliosInk, style = MaterialTheme.typography.labelMedium)
        } else {
            Text("Sin coordenada actual", Modifier.align(Alignment.Center).background(HeliosInk.copy(alpha = .84f), RoundedCornerShape(10.dp)).padding(horizontal = 12.dp, vertical = 8.dp), color = TextSecondary, style = MaterialTheme.typography.labelMedium)
        }
        Text("N", Modifier.align(Alignment.TopEnd).padding(14.dp), color = WarmCloud, style = MaterialTheme.typography.labelMedium)
    }
}

@Composable
private fun rememberCurrentLocation(permission: LocationPermissionState): LocationSample? {
    val context = LocalContext.current
    var location by remember { mutableStateOf<LocationSample?>(null) }
    LaunchedEffect(permission) {
        location = when (permission) {
            LocationPermissionState.Precise -> AndroidLocationSource(context).getCurrentLocation(LocationAccuracy.PRECISE)
            LocationPermissionState.Approximate -> AndroidLocationSource(context).getCurrentLocation(LocationAccuracy.APPROXIMATE)
            else -> null
        }
    }
    return location
}

private fun locationAge(sample: LocationSample): String {
    val ageSeconds = ((System.currentTimeMillis() - sample.timestampEpochMillis).coerceAtLeast(0L) / 1_000L)
    return when {
        ageSeconds < 10 -> "ahora"
        ageSeconds < 60 -> "hace ${ageSeconds}s"
        else -> "hace ${ageSeconds / 60} min"
    }
}

@Composable
private fun ReadinessMetric(title: String, value: String, accent: Color, modifier: Modifier = Modifier) {
    Column(modifier.background(GraphiteBlue.copy(alpha = .74f), RoundedCornerShape(14.dp)).padding(12.dp)) {
        Text(title, color = TextSecondary, style = MaterialTheme.typography.labelMedium)
        Spacer(Modifier.height(4.dp))
        Text(value, color = accent, style = MaterialTheme.typography.labelLarge)
    }
}

@Composable
private fun ActionTile(title: String, detail: String, onClick: () -> Unit, modifier: Modifier = Modifier) {
    OutlinedButton(onClick = onClick, modifier.fillMaxWidth().heightIn(min = 72.dp), shape = RoundedCornerShape(14.dp)) {
        Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, color = TextPrimary, style = MaterialTheme.typography.labelLarge)
            Text(detail, color = TextSecondary, style = MaterialTheme.typography.labelMedium)
        }
    }
}

@Composable
private fun MapExperienceScreen(permission: LocationPermissionState, onBack: () -> Unit, emergency: Boolean = false) {
    var focusMessage by remember { mutableStateOf<String?>(null) }
    val currentLocation = rememberCurrentLocation(permission)
    BoxWithConstraints {
        val wide = maxWidth >= 720.dp
        Column(Modifier.fillMaxSize().padding(horizontal = 16.dp, vertical = 14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Eyebrow(if (emergency) "MODO APOYO · POSICIÓN" else "HELIOS · POSICIÓN")
                    Text("Orientación local", color = TextPrimary, style = MaterialTheme.typography.headlineLarge)
                    Text("Una vista espacial local; la coordenada y su frescura siempre son explícitas.", color = TextSecondary, style = MaterialTheme.typography.bodyMedium)
                }
                TextButton(onClick = onBack) { Text("Volver") }
            }
            if (wide) {
                Row(Modifier.fillMaxWidth().weight(1f), horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                    MapSurface(permission, currentLocation, Modifier.weight(1.4f).fillMaxSize())
                    MapContextPanel(permission, currentLocation, emergency, focusMessage, onRecenter = { focusMessage = if (currentLocation != null) "Centro de tu última señal disponible" else "Concede ubicación para centrar el mapa" })
                }
            } else {
                MapSurface(permission, currentLocation, Modifier.fillMaxWidth().heightIn(min = 260.dp, max = 420.dp))
                MapContextPanel(permission, currentLocation, emergency, focusMessage, onRecenter = { focusMessage = if (currentLocation != null) "Centro de tu última señal disponible" else "Concede ubicación para centrar el mapa" })
            }
        }
    }
}

@Composable
private fun MapContextPanel(permission: LocationPermissionState, location: LocationSample?, emergency: Boolean, focusMessage: String?, onRecenter: () -> Unit) {
    Column(Modifier.widthIn(max = 340.dp).background(DeepOcean, RoundedCornerShape(18.dp)).border(1.dp, Hairline, RoundedCornerShape(18.dp)).padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        StatusPanel("Mi ubicación", when { location != null -> "DISPONIBLE"; permission is LocationPermissionState.Denied -> "RECHAZADA"; permission is LocationPermissionState.NotRequested -> "NO SOLICITADA"; else -> "SIN LECTURA" }, location?.let { "±${it.horizontalAccuracyMeters?.toInt() ?: "—"} m · ${locationAge(it)}" } ?: "No se muestra una coordenada inventada", if (location != null) LocationSky else Warning)
        StatusPanel("Datos remotos", "NO CONECTADOS", "La aplicación no inventa personas, calles ni alertas sin una fuente autorizada", AquaSignal)
        if (emergency) StatusPanel("Señales de emergencia", "SIN SEÑALES", "Las alertas recibidas aparecerán con origen, hora y transporte", SignalCoral)
        Text("Leyenda", color = TextPrimary, style = MaterialTheme.typography.labelLarge)
        Text("● Mi ubicación   ● Personas vinculadas   ● Estimación histórica", color = TextSecondary, style = MaterialTheme.typography.labelMedium)
        OutlinedButton(onClick = onRecenter, Modifier.fillMaxWidth()) { Text("Centrar en mi última señal") }
        focusMessage?.let { Text(it, color = LocationSky, style = MaterialTheme.typography.labelMedium) }
    }
}

@Composable
private fun PeopleScreen(onBack: () -> Unit) {
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        TextButton(onClick = onBack) { Text("Volver") }
        Eyebrow("RED HUMANA")
        Text("Personas", color = TextPrimary, style = MaterialTheme.typography.headlineLarge)
        Text("Comparte ubicación solo con relaciones que tú autorices. La API de cuentas todavía no está conectada a este shell.", color = TextSecondary, style = MaterialTheme.typography.bodyMedium)
        StatusPanel("Estado de la red", "SIN VÍNCULOS", "No se muestran personas ni ubicaciones inventadas", Warning)
        Column(Modifier.fillMaxWidth().background(DeepOcean, RoundedCornerShape(18.dp)).padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Cuando el backend esté conectado aquí podrás:", color = TextPrimary, style = MaterialTheme.typography.titleLarge)
            Text("• solicitar compartir ubicación\n• aceptar o rechazar solicitudes\n• detener una relación\n• ver frescura y precisión de cada señal", color = TextSecondary, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
private fun OperationalListScreen(title: String, subtitle: String, emptyMessage: String, onBack: () -> Unit) {
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        TextButton(onClick = onBack) { Text("Volver") }
        Eyebrow("EVIDENCIA OPERATIVA")
        Text(title, color = TextPrimary, style = MaterialTheme.typography.headlineLarge)
        Text(subtitle, color = TextSecondary, style = MaterialTheme.typography.bodyMedium)
        StatusPanel(title, "SIN DATOS", emptyMessage, Warning)
        Text("Los elementos que lleguen desde una fuente real conservarán origen, hora, confianza y estado. Marcar una alerta no borrará su evidencia.", color = TextSecondary, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun EmergencyOverviewScreen(onNeedsHelp: () -> Unit, onDemo: () -> Unit) {
    val context = LocalContext.current
    val debugBuild = (context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
    HeliosBackdrop {
        Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Eyebrow("HELIOS · PREPARACIÓN")
            Text("Modo de emergencia", color = TextPrimary, style = MaterialTheme.typography.headlineLarge)
            Text("Una alerta real, una simulación o un SOS manual pasan por el mismo controlador operativo.", color = TextSecondary, style = MaterialTheme.typography.bodyLarge)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) { HeliosPulse(color = SignalCoral, active = false) }
            StatusPanel("Estado", "NORMAL", "No hay una emergencia activa en este momento", SafeMint)
            Spacer(Modifier.weight(1f))
            Button(onClick = onNeedsHelp, Modifier.fillMaxWidth().height(54.dp), colors = ButtonDefaults.buttonColors(containerColor = SignalCoral, contentColor = PureWarm), shape = RoundedCornerShape(16.dp)) { Text("NECESITO AYUDA") }
            if (debugBuild) {
                OutlinedButton(onClick = onDemo, Modifier.fillMaxWidth().height(50.dp), shape = RoundedCornerShape(14.dp)) { Text("Simular alerta sísmica · DEBUG") }
            }
        }
    }
}

@Composable
private fun PermissionsScreen(permission: LocationPermissionState, onRoute: (Route) -> Unit) {
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        TextButton(onClick = { onRoute(Route.HOME) }) { Text("Volver") }
        Eyebrow("CONTROL Y PRIVACIDAD")
        Text("Permisos", color = TextPrimary, style = MaterialTheme.typography.headlineLarge)
        Text("HELIOS solicita cada capacidad cuando la necesitas. Rechazar una no cancela las demás evidencias.", color = TextSecondary, style = MaterialTheme.typography.bodyMedium)
        StatusPanel("Ubicación", when (permission) { is LocationPermissionState.Precise -> "PRECISA"; is LocationPermissionState.Approximate -> "APROXIMADA"; is LocationPermissionState.Denied -> "RECHAZADA"; else -> "NO SOLICITADA" }, "La solicitud aparece durante el primer acceso o al usar Mapa", if (permission is LocationPermissionState.Precise || permission is LocationPermissionState.Approximate) LocationSky else Warning)
        ActionTile("Dispositivos cercanos", "Permisos Bluetooth/BLE y Wi‑Fi local", { onRoute(Route.NEARBY) })
        ActionTile("Cámara y fisiología", "La cámara se solicita al iniciar PPG", { onRoute(Route.PPG) })
        ActionTile("Diagnóstico", "Comprueba sensores y capacidades sin activar nada", { onRoute(Route.DIAGNOSTICS) })
    }
}

private fun localIncident(source: IncidentSource) = EmergencyIncident(
    id = "local-${System.currentTimeMillis()}",
    source = source,
    detectedAtMs = System.currentTimeMillis(),
    summary = if (source == IncidentSource.DEMO) "Evento sísmico simulado" else "Solicitud manual de asistencia",
)

@Composable
private fun SeismicAlertScreen(
    incident: EmergencyIncident,
    onNeedsHelp: () -> Unit,
    onSafe: () -> Unit,
) {
    HeliosBackdrop {
        Column(Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Box(Modifier.fillMaxWidth().height(10.dp).background(HeliosSolar, RoundedCornerShape(8.dp)))
            Eyebrow(if (incident.source == IncidentSource.DEMO) "SIMULACIÓN · ALERTA" else "ALERTA · HELIOS")
            Text("ALERTA SÍSMICA", color = TextPrimary, style = MaterialTheme.typography.headlineLarge)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) { HeliosPulse(color = HeliosSolar) }
            StatusPanel("Evento", if (incident.source == IncidentSource.DEMO) "SIMULACIÓN" else "DETECTADO", incident.summary, HeliosSolar)
            Text("Se ha detectado un evento que podría afectar tu zona. Mantén la calma y toma medidas de precaución.", color = TextPrimary, style = MaterialTheme.typography.bodyLarge)
            Text("Aléjate de ventanas. Protege cabeza y cuello. No utilices ascensores. Si estás en un lugar seguro, permanece allí mientras pasa el movimiento.", color = TextSecondary, style = MaterialTheme.typography.bodyMedium)
            Spacer(Modifier.weight(1f))
            Button(onClick = onNeedsHelp, Modifier.fillMaxWidth().height(56.dp), colors = ButtonDefaults.buttonColors(containerColor = SignalCoral, contentColor = PureWarm), shape = RoundedCornerShape(16.dp)) { Text("SÍ, NECESITO AYUDA") }
            OutlinedButton(onClick = onSafe, Modifier.fillMaxWidth().height(52.dp), shape = RoundedCornerShape(16.dp)) { Text("NO, ESTOY BIEN") }
            Text("La pregunta continuará disponible mientras se recopila evidencia local.", color = TextSecondary, style = MaterialTheme.typography.labelMedium)
        }
    }
}

@Composable
private fun AssistanceQuestionScreen(
    onNeedsHelp: () -> Unit,
    onSafe: () -> Unit,
) {
    HeliosBackdrop {
        Column(Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Eyebrow("RESPONDE CUANDO PUEDAS")
            Text("¿Necesitas ayuda o asistencia para salir del lugar donde te encuentras?", color = TextPrimary, style = MaterialTheme.typography.headlineMedium)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) { HeliosPulse(color = HeliosSolar) }
            Text("Responde cuando puedas. Si no respondes, Helios iniciará una verificación preventiva sin afirmar que estás atrapado.", color = TextSecondary, style = MaterialTheme.typography.bodyLarge)
            StatusPanel("Mientras decides", "HELIOS SIGUE CONTIGO", "La red cercana y las evidencias disponibles se preparan sin que tengas que gestionar radios", AquaSignal)
            Spacer(Modifier.weight(1f))
            Button(onClick = onNeedsHelp, Modifier.fillMaxWidth().height(58.dp), colors = ButtonDefaults.buttonColors(containerColor = SignalCoral, contentColor = PureWarm), shape = RoundedCornerShape(16.dp)) { Text("SÍ, NECESITO AYUDA") }
            OutlinedButton(onClick = onSafe, Modifier.fillMaxWidth().height(52.dp), shape = RoundedCornerShape(16.dp)) { Text("NO, ESTOY BIEN") }
        }
    }
}

@Composable
private fun EmergencySupportScreen(
    onRoute: (Route) -> Unit,
    onResolve: () -> Unit,
) {
    HeliosBackdrop {
        Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Eyebrow("MODO APOYO")
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
                Column(Modifier.weight(1f)) {
                    Text("Puedes ayudar", color = TextPrimary, style = MaterialTheme.typography.headlineLarge)
                    Text("Estás a salvo según tu respuesta. Mantengamos informadas a las personas relacionadas contigo.", color = TextSecondary, style = MaterialTheme.typography.bodyMedium)
                }
                HeliosPulse(color = SafeMint, active = false)
            }
            StatusPanel("Red Helios", "BUSCANDO CONEXIÓN", "La búsqueda es automática y no requiere gestionar dispositivos", AquaSignal)
            ActionTile("Mapa local", "Tu última señal GPS y su frescura", { onRoute(Route.MAP) })
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                ActionTile("Red Helios", "Búsqueda y retransmisión local", { onRoute(Route.NEARBY) }, Modifier.weight(1f))
                ActionTile("Movimiento", "Evidencia del dispositivo", { onRoute(Route.MOTION) }, Modifier.weight(1f))
            }
            ActionTile("Evaluación fisiológica", "Actualizar evidencia si lo deseas", { onRoute(Route.PPG) })
            Spacer(Modifier.weight(1f))
            OutlinedButton(onClick = onResolve, Modifier.fillMaxWidth().height(50.dp), shape = RoundedCornerShape(14.dp)) { Text("Finalizar modo de apoyo") }
        }
    }
}

@Composable
private fun AssistanceRequiredScreen(
    confirmation: AssistanceConfirmation,
    onSafe: () -> Unit,
    onNeedsHelp: () -> Unit,
    onPpg: () -> Unit,
) {
    val confirmed = confirmation == AssistanceConfirmation.CONFIRMED_BY_USER
    HeliosBackdrop {
        Column(Modifier.fillMaxSize().padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Eyebrow("MODO ASISTENCIA · SEÑAL ACTIVA")
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) { HeliosPulse(color = SignalCoral, active = true) }
            Text("Tu señal sigue activa", color = TextPrimary, style = MaterialTheme.typography.headlineLarge)
            Text("No necesitas gestionar Bluetooth, Wi‑Fi ni GPS. Helios seguirá buscando dispositivos cercanos y compartiendo la evidencia disponible.", color = TextSecondary, style = MaterialTheme.typography.bodyLarge)
            StatusPanel("Estado de la señal", if (confirmed) "CONFIRMADA" else "SIN RESPUESTA", if (confirmed) "Confirmaste que necesitas ayuda" else "Posible necesidad de asistencia; no se afirma que estés atrapado", SignalCoral)
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                ReadinessMetric("Ubicación", "En preparación", LocationSky, Modifier.weight(1f))
                ReadinessMetric("Movimiento", "Disponible", HeliosSolar, Modifier.weight(1f))
            }
            StatusPanel("Comunicación", "BUSCANDO CONEXIÓN", "Cuando otro Helios reciba el paquete se mostrará como señal enlazada", AquaSignal)
            ActionTile("Evaluación fisiológica", "Actualizar registro sin bloquear la señal SOS", onPpg)
            Text("Cada evidencia se transmite por separado. Ninguna prueba por sí sola determina tu estado vital.", color = TextSecondary, style = MaterialTheme.typography.labelMedium)
            Spacer(Modifier.weight(1f))
            if (!confirmed) {
                Button(onClick = onNeedsHelp, Modifier.fillMaxWidth().height(54.dp), colors = ButtonDefaults.buttonColors(containerColor = SignalCoral, contentColor = PureWarm), shape = RoundedCornerShape(16.dp)) { Text("SÍ, NECESITO AYUDA") }
            }
            OutlinedButton(onClick = onSafe, Modifier.fillMaxWidth().height(52.dp), shape = RoundedCornerShape(16.dp)) { Text("NO, ESTOY BIEN") }
        }
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
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Eyebrow("SEÑAL DEL DISPOSITIVO")
                Text("Movimiento reciente", color = TextPrimary, style = MaterialTheme.typography.headlineLarge)
                Text("El movimiento es evidencia del dispositivo; no demuestra vida ni lesiones.", color = TextSecondary, style = MaterialTheme.typography.bodyMedium)
            }
            HeliosPulse(color = HeliosSolar, active = evidence != null)
        }
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
private fun PpgScreen(onBack: (() -> Unit)? = null) {
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
    HeliosBackdrop {
        Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            onBack?.let { TextButton(onClick = it) { Text("Volver al estado de emergencia") } }
            Eyebrow("EVIDENCIA FISIOLÓGICA")
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Hagamos un registro rápido de cómo estás", color = TextPrimary, style = MaterialTheme.typography.headlineMedium)
                    Text("Coloca la yema de tu dedo índice sobre la cámara trasera y el flash.", color = TextSecondary, style = MaterialTheme.typography.bodyMedium)
                }
                HeliosPulse(color = EvidenceViolet, active = capturing)
            }
            AndroidView(factory = { PreviewView(context).also { previewView = it } }, modifier = Modifier.fillMaxWidth().height(210.dp).clip(RoundedCornerShape(18.dp)))
            StatusPanel("Estado de captura", if (assessment == null) "LISTO" else "COMPLETO", "Solo PPG · el ECG requiere un sensor externo", EvidenceViolet)
            Button(onClick = {
                if (context.checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
                    capture(verification = assessment?.status == VerificationStatus.SECOND_VERIFICATION_REQUIRED)
                } else cameraPermission.launch(Manifest.permission.CAMERA)
            }, Modifier.fillMaxWidth().height(54.dp), enabled = !capturing, colors = ButtonDefaults.buttonColors(containerColor = HeliosSolar, contentColor = HeliosInk), shape = RoundedCornerShape(16.dp)) {
                Text(if (capturing) "Capturando señal…" else if (assessment?.status == VerificationStatus.SECOND_VERIFICATION_REQUIRED) "Realizar segunda verificación" else "CAPTURAR")
            }
            OutlinedButton(onClick = {
                val synthetic = demoPulseSamples()
                firstSamples = synthetic.first
                firstSampleRate = synthetic.second
                assessment = PpgPipeline().assess(synthetic.first, synthetic.second)
            }, Modifier.fillMaxWidth(), enabled = !capturing, shape = RoundedCornerShape(14.dp)) { Text("Ejecutar muestra sintética · DEMO") }
            assessment?.let { checked ->
                val observation = checked.estimate
                val color = when (checked.status) {
                    VerificationStatus.REPEATED_ANOMALY -> Warning
                    VerificationStatus.SECOND_VERIFICATION_REQUIRED, VerificationStatus.INCONCLUSIVE_RECHECK -> Warning
                    VerificationStatus.ACCEPTED -> SafeMint
                }
                StatusPanel("Frecuencia cardíaca estimada", "${observation.bpm.toInt()} BPM", "${checked.status.name} · calidad ${(observation.sqi * 100).toInt()}% · ${observation.method}", color)
                Text(checked.message, color = color, style = MaterialTheme.typography.bodyMedium)
                if (checked.status == VerificationStatus.REPEATED_ANOMALY) {
                    Text("Las lecturas anómalas repetidas son solo una señal de prueba; no confirman bradicardia ni otra condición.", color = TextSecondary, style = MaterialTheme.typography.labelMedium)
                }
            }
            Text("Estimación observacional de una señal; no es un diagnóstico clínico.", color = TextSecondary, style = MaterialTheme.typography.labelMedium)
        }
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

private data class NearbyRadioState(
    val permissionsGranted: Boolean,
    val bluetoothSupported: Boolean,
    val bluetoothEnabled: Boolean,
    val wifiEnabled: Boolean,
)

private fun nearbyPermissions(): Array<String> = buildList {
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        add(Manifest.permission.BLUETOOTH_SCAN)
        add(Manifest.permission.BLUETOOTH_ADVERTISE)
        add(Manifest.permission.BLUETOOTH_CONNECT)
    } else {
        add(Manifest.permission.ACCESS_FINE_LOCATION)
    }
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        add(Manifest.permission.NEARBY_WIFI_DEVICES)
    }
}.toTypedArray()

private fun readLocationPermissionState(context: Context): LocationPermissionState = when {
    ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED -> LocationPermissionState.Precise
    ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED -> LocationPermissionState.Approximate
    else -> LocationPermissionState.NotRequested
}

private fun readNearbyRadioState(context: Context): NearbyRadioState {
    val bluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
    val adapter = bluetoothManager?.adapter
    val bluetoothPermissions = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        listOf(
            Manifest.permission.BLUETOOTH_SCAN,
            Manifest.permission.BLUETOOTH_ADVERTISE,
            Manifest.permission.BLUETOOTH_CONNECT,
        ).all { ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED }
    } else {
        ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
    }
    val nearbyWifiPermission = Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
        ContextCompat.checkSelfPermission(context, Manifest.permission.NEARBY_WIFI_DEVICES) == PackageManager.PERMISSION_GRANTED
    return NearbyRadioState(
        permissionsGranted = bluetoothPermissions && nearbyWifiPermission,
        bluetoothSupported = adapter != null,
        bluetoothEnabled = bluetoothPermissions && adapter?.isEnabled == true,
        wifiEnabled = runCatching {
            (context.getSystemService(Context.WIFI_SERVICE) as? WifiManager)?.isWifiEnabled == true
        }.getOrDefault(false),
    )
}

@Composable
private fun NearbyNetworkScreen(transport: NearbyConnectionsTransport, onBack: () -> Unit) {
    val context = LocalContext.current
    var refreshToken by remember { mutableStateOf(0) }
    var transportRunning by remember { mutableStateOf(false) }
    var transportStatus by remember { mutableStateOf("NO INICIADO") }
    var discoveredPeers by remember { mutableStateOf(emptySet<String>()) }
    var connectedPeers by remember { mutableStateOf(emptySet<String>()) }
    var lastPayload by remember { mutableStateOf<String?>(null) }
    val state = remember(refreshToken) { readNearbyRadioState(context) }
    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
        refreshToken++
    }
    val bluetoothLauncher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) {
        refreshToken++
    }
    LaunchedEffect(transport) {
        transport.events.collect { event ->
            when (event) {
                NearbyEvent.AdvertisingStarted, NearbyEvent.DiscoveryStarted -> {
                    transportRunning = true
                    transportStatus = "BUSCANDO DISPOSITIVOS HELIOS"
                }
                is NearbyEvent.Discovered -> {
                    discoveredPeers = discoveredPeers + event.endpointId
                    transportStatus = "DISPOSITIVO ENCONTRADO"
                }
                is NearbyEvent.Connected -> {
                    connectedPeers = connectedPeers + event.endpointId
                    transportStatus = "CONECTADO · ${connectedPeers.size + 1} DISPOSITIVO(S)"
                }
                is NearbyEvent.Disconnected -> {
                    connectedPeers = connectedPeers - event.endpointId
                    transportStatus = if (connectedPeers.isEmpty()) "BUSCANDO DISPOSITIVOS HELIOS" else "CONECTADO"
                }
                is NearbyEvent.Lost -> discoveredPeers = discoveredPeers - event.endpointId
                is NearbyEvent.PayloadReceived -> lastPayload = event.bytes.decodeToString()
                is NearbyEvent.Error -> transportStatus = event.message
            }
        }
    }
    fun prepareNearbyNetwork() {
        when {
            !state.permissionsGranted -> permissionLauncher.launch(nearbyPermissions())
            state.bluetoothSupported && !state.bluetoothEnabled -> bluetoothLauncher.launch(Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE))
            !state.bluetoothEnabled && !state.wifiEnabled -> bluetoothLauncher.launch(Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE))
            else -> {
                transport.start()
                transportRunning = true
                transportStatus = "INICIANDO BÚSQUEDA"
            }
        }
    }

    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        TextButton(onClick = onBack) { Text("Volver", color = RescueTeal) }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Eyebrow("RED HELIOS")
                Text("Dispositivos cercanos", color = TextPrimary, style = MaterialTheme.typography.headlineLarge)
                Text("HELIOS busca otros dispositivos compatibles y usa el medio disponible sin exponerte a jerga técnica.", color = TextSecondary, style = MaterialTheme.typography.bodyMedium)
            }
            HeliosPulse(color = AquaSignal, active = transportRunning)
        }
        StatusPanel("Permisos de dispositivos cercanos", if (state.permissionsGranted) "CONCEDIDOS" else "PENDIENTES", "Bluetooth Scan · Advertise · Connect · Wi‑Fi cercano", if (state.permissionsGranted) RescueTeal else Warning)
        StatusPanel("Bluetooth", when { !state.bluetoothSupported -> "NO DISPONIBLE"; state.bluetoothEnabled -> "ACTIVO"; else -> "APAGADO" }, "Se usa para advertising, búsqueda y enlace GATT", if (state.bluetoothEnabled) RescueTeal else Warning)
        StatusPanel("Wi‑Fi", if (state.wifiEnabled) "ACTIVO" else "APAGADO", "Se usa para proximidad o Internet cuando el sistema lo permita", if (state.wifiEnabled) RescueTeal else Warning)
        StatusPanel("Estado de búsqueda", transportStatus, "Encontrados: ${discoveredPeers.size} · Conectados: ${connectedPeers.size}", if (connectedPeers.isNotEmpty()) RescueTeal else Warning)
        Button(onClick = ::prepareNearbyNetwork, Modifier.fillMaxWidth(), enabled = !transportRunning) {
            Text(if (!state.permissionsGranted) "Conceder permisos cercanos" else "Iniciar búsqueda HELIOS")
        }
        if (transportRunning) {
            OutlinedButton(onClick = { transport.stop(); transportRunning = false; transportStatus = "DETENIDO" }, Modifier.fillMaxWidth()) { Text("Detener búsqueda") }
            OutlinedButton(onClick = { transport.send("HELIOS|PAQUETE_DE_PRUEBA|${transport.deviceId}|${System.currentTimeMillis()}".encodeToByteArray()) }, Modifier.fillMaxWidth()) { Text("Encolar paquete de prueba") }
        }
        lastPayload?.let { StatusPanel("Último paquete recibido", it, "Contenido de demostración; los paquetes operativos usarán el contrato DTN.", RescueTeal) }
        Text("Android exige consentimiento para encender Bluetooth y no permite a una aplicación activar o desactivar Wi‑Fi silenciosamente. HELIOS abrirá el diálogo o panel oficial y conservará el estado si el usuario lo rechaza.", color = TextSecondary, fontSize = 12.sp)
    }
}

@Composable
private fun DiagnosticsScreen(nearbyTransport: NearbyConnectionsTransport, onOpenLab: () -> Unit) {
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
        if ((context.applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0) {
            item {
                ActionRow("Laboratorio de red", "Solo DEBUG · peers, paquetes y retransmisión real", onOpenLab)
            }
        }
    }
}

@Composable
private fun NetworkLabScreen(nearbyTransport: NearbyConnectionsTransport, onBack: () -> Unit) {
    val diagnostics by nearbyTransport.diagnostics.collectAsState()
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        TextButton(onClick = onBack) { Text("Volver", color = RescueTeal) }
        Text("Laboratorio de red", color = TextPrimary, fontSize = 28.sp)
        Text("Solo DEBUG. Los contadores describen esta sesión local; no sustituyen una prueba física de tres dispositivos.", color = TextSecondary, fontSize = 12.sp)
        StatusPanel("Device ID", diagnostics.deviceId, "Identidad local del dispositivo", RescueTeal)
        StatusPanel("Rol operativo", diagnostics.role, "Un dispositivo puede originar y retransmitir", RescueTeal)
        StatusPanel("Peers cercanos", "${diagnostics.discoveredPeers} encontrados · ${diagnostics.connectedPeers} conectados", "La búsqueda permanece activa mientras haya emergencia", if (diagnostics.connectedPeers > 0) RescueTeal else Warning)
        StatusPanel("Transportes disponibles", diagnostics.availableTransports.joinToString().ifBlank { "No iniciado" }, "Nearby Connections negocia Bluetooth/BLE o Wi‑Fi local; no implica Internet", if (diagnostics.availableTransports.isNotEmpty()) RescueTeal else Warning)
        StatusPanel("Paquetes", "${diagnostics.packetsCreated} creados · ${diagnostics.packetsReceived} recibidos · ${diagnostics.packetsForwarded} reenviados", "La retransmisión se deduplica por hash SHA‑256 de la carga", RescueTeal)
        StatusPanel("Deduplicación", "${diagnostics.packetsDeduplicated}", "Duplicados ignorados en esta sesión", RescueTeal)
        StatusPanel("Pendientes", "${diagnostics.pendingPackets}", "Cola local en memoria; no sobrevive al cierre de la aplicación", if (diagnostics.pendingPackets > 0) Warning else RescueTeal)
        StatusPanel("ACK técnicos", "${diagnostics.acknowledgements}", "Confirman recepción técnica del paquete; no son confirmación de rescate", Warning)
        diagnostics.lastPacket?.let {
            StatusPanel("Último paquete", it, "Origen: ${diagnostics.lastOrigin ?: "no disponible"} · saltos: ${diagnostics.lastHopCount?.toString() ?: "no disponible"}", RescueTeal)
        }
        StatusPanel("Último transporte / relay", diagnostics.lastTransport ?: "no disponible", diagnostics.lastRelay ?: "Sin relay confirmado", RescueTeal)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            OutlinedButton(onClick = nearbyTransport::clearDiagnostics, modifier = Modifier.weight(1f)) { Text("Limpiar métricas") }
            OutlinedButton(onClick = { nearbyTransport.send("HELIOS|DEBUG|${nearbyTransport.deviceId}|${System.currentTimeMillis()}|hop=0".encodeToByteArray()) }, modifier = Modifier.weight(1f)) { Text("Encolar paquete") }
        }
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
private fun BottomNav(route: Route, onRoute: (Route) -> Unit) {
    Row(Modifier.fillMaxWidth().background(DeepOcean).navigationBarsPadding().padding(horizontal = 6.dp, vertical = 7.dp), horizontalArrangement = Arrangement.SpaceEvenly) {
        listOf(Route.HOME to "Inicio", Route.MAP to "Mapa", Route.NEARBY to "Red", Route.SETTINGS to "Perfil").forEach { (target, label) ->
            val selected = route == target
            TextButton(onClick = { onRoute(target) }, Modifier.weight(1f).height(58.dp)) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(5.dp)) {
                    Text(label, color = if (selected) WarmCloud else TextSecondary, style = MaterialTheme.typography.labelMedium)
                    Box(Modifier.widthIn(min = 24.dp).height(3.dp).background(if (selected) HeliosSolar else Color.Transparent, RoundedCornerShape(3.dp)))
                }
            }
        }
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
