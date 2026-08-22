import { useState } from "react"

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { AnalysisScreen } from "@/screens/analysis-screen"
import { LoopScreen } from "@/screens/loop-screen"

type Screen = "analysis" | "loop"

const SCREEN_STORAGE_KEY = "harness-compiler:screen"

// Solo recuerda QUE pestana estaba activa (para que un F5 no te mande siempre a Analisis).
// Los datos de una corrida (run_id, eventos, resultados) nunca se guardan aca — cada screen
// sigue montando en limpio, como siempre.
function readStoredScreen(): Screen {
  try {
    const stored = sessionStorage.getItem(SCREEN_STORAGE_KEY)
    return stored === "loop" ? "loop" : "analysis"
  } catch {
    return "analysis"
  }
}

function App() {
  const [screen, setScreen] = useState<Screen>(readStoredScreen)

  function selectScreen(next: Screen) {
    setScreen(next)
    try {
      sessionStorage.setItem(SCREEN_STORAGE_KEY, next)
    } catch {
      // sessionStorage no disponible (privado/bloqueado) -> el estado en memoria sigue andando
    }
  }

  return (
    <>
      {/* Fondo ambiental — ver specs de la corrida del 2026-08-22. El video fuente ya casi
          no se oscurece (antes le bajaba brightness/contrast/saturation fuerte via ffmpeg,
          y encima lo ponia a opacity muy baja -> doble atenuacion, quedaba invisible sobre
          el fondo casi negro del tema). Ahora casi toda la atenuacion la hace la opacity. */}
      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-background">
        <video
          className="h-full w-full object-cover opacity-[0.35]"
          autoPlay
          loop
          muted
          playsInline
          src="/bg-volumetric.mp4"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-background/50 via-transparent to-background/50" />
      </div>

      <div className="mx-auto flex min-h-svh w-full max-w-6xl flex-col gap-8 px-6 py-10">
        <Tabs value={screen} onValueChange={(v) => selectScreen(v as Screen)}>
          <TabsList>
            <TabsTrigger value="analysis">Análisis</TabsTrigger>
            <TabsTrigger value="loop">Loop en vivo</TabsTrigger>
          </TabsList>
        </Tabs>

        {screen === "analysis" ? <AnalysisScreen /> : <LoopScreen />}
      </div>
    </>
  )
}

export default App
