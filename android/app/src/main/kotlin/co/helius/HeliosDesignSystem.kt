package co.helius

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas as ComposeCanvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

// Solar Cartography: colores semánticos, no colores decorativos por pantalla.
internal val HeliosInk = Color(0xFF07161E)
internal val DeepOcean = Color(0xFF0D252D)
internal val GraphiteBlue = Color(0xFF173741)
internal val WarmCloud = Color(0xFFF4F1E9)
internal val PureWarm = Color(0xFFFFFCF6)
internal val HeliosSolar = Color(0xFFF4B44A)
internal val AquaSignal = Color(0xFF35C4B2)
internal val LocationSky = Color(0xFF65C4E4)
internal val SafeMint = Color(0xFF69BA8E)
internal val SignalCoral = Color(0xFFED625E)
internal val EvidenceViolet = Color(0xFF9A86C8)
internal val Mist = Color(0xFFB7C8C7)
internal val Hairline = Color(0xFF2C4A53)

// Alias de compatibilidad para el shell actual; todas apuntan a tokens semánticos.
internal val Canvas = HeliosInk
internal val SurfaceDark = DeepOcean
internal val Border = Hairline
internal val TextPrimary = WarmCloud
internal val TextSecondary = Mist
internal val RescueTeal = AquaSignal
internal val Warning = HeliosSolar
internal val Critical = SignalCoral

private val HeliosTypography = Typography(
    displayLarge = TextStyle(fontSize = 38.sp, lineHeight = 42.sp, fontWeight = FontWeight.SemiBold, letterSpacing = (-1.2).sp),
    headlineLarge = TextStyle(fontSize = 30.sp, lineHeight = 34.sp, fontWeight = FontWeight.SemiBold, letterSpacing = (-0.6).sp),
    headlineMedium = TextStyle(fontSize = 24.sp, lineHeight = 29.sp, fontWeight = FontWeight.SemiBold),
    titleLarge = TextStyle(fontSize = 19.sp, lineHeight = 24.sp, fontWeight = FontWeight.SemiBold),
    bodyLarge = TextStyle(fontSize = 16.sp, lineHeight = 23.sp),
    bodyMedium = TextStyle(fontSize = 14.sp, lineHeight = 20.sp),
    labelLarge = TextStyle(fontSize = 14.sp, lineHeight = 18.sp, fontWeight = FontWeight.SemiBold),
    labelMedium = TextStyle(fontSize = 12.sp, lineHeight = 16.sp, fontWeight = FontWeight.Medium),
)

@Composable
internal fun HeliosTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = AquaSignal,
            onPrimary = HeliosInk,
            secondary = HeliosSolar,
            onSecondary = HeliosInk,
            tertiary = LocationSky,
            background = HeliosInk,
            onBackground = WarmCloud,
            surface = DeepOcean,
            onSurface = WarmCloud,
            surfaceVariant = GraphiteBlue,
            onSurfaceVariant = Mist,
            error = SignalCoral,
            onError = PureWarm,
        ),
        typography = HeliosTypography,
        content = content,
    )
}

@Composable
internal fun HeliosBackdrop(modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    Box(
        modifier
            .fillMaxSize()
            .background(Brush.verticalGradient(listOf(HeliosInk, DeepOcean, HeliosInk))),
    ) { content() }
}

/** Motivo de marca: un pulso informa estado, no adorna sin significado. */
@Composable
internal fun HeliosPulse(
    modifier: Modifier = Modifier,
    color: Color = AquaSignal,
    active: Boolean = true,
) {
    val transition = rememberInfiniteTransition(label = "helios-pulse")
    val phase by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(1800), RepeatMode.Restart),
        label = "pulse-phase",
    )
    ComposeCanvas(modifier.size(112.dp)) {
        val center = this.center
        val base = size.minDimension * .24f
        drawCircle(color.copy(alpha = .10f), radius = size.minDimension * .43f)
        if (active) {
            drawCircle(
                color.copy(alpha = .17f * (1f - phase)),
                radius = size.minDimension * (.28f + phase * .18f),
                style = Stroke(width = 2.dp.toPx()),
            )
        }
        drawCircle(color.copy(alpha = .22f), radius = base * 1.8f)
        drawCircle(color, radius = base)
        drawArc(color.copy(alpha = .9f), startAngle = -90f, sweepAngle = 80f + phase * 90f, useCenter = false, style = Stroke(width = 2.dp.toPx()))
    }
}

@Composable
internal fun Eyebrow(text: String) {
    androidx.compose.material3.Text(text.uppercase(), color = HeliosSolar, style = MaterialTheme.typography.labelMedium, letterSpacing = 1.4.sp)
}

@Composable
internal fun PremiumAuthFrame(title: String, subtitle: String, content: @Composable () -> Unit) {
    HeliosBackdrop {
        Column(Modifier.fillMaxSize().statusBarsPadding().padding(horizontal = 24.dp, vertical = 28.dp)) {
            Spacer(Modifier.height(22.dp))
            Eyebrow("Red de protección")
            androidx.compose.material3.Text("HELIOS", color = WarmCloud, style = MaterialTheme.typography.displayLarge)
            androidx.compose.material3.Text(title, color = WarmCloud, style = MaterialTheme.typography.headlineMedium)
            androidx.compose.material3.Text(subtitle, color = Mist, style = MaterialTheme.typography.bodyMedium)
            Spacer(Modifier.height(18.dp))
            HeliosPulse(color = HeliosSolar)
            Spacer(Modifier.height(18.dp))
            content()
        }
    }
}
