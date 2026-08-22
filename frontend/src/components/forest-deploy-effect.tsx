import { useEffect, useRef } from "react"
import { animate, createTimer } from "animejs"
import { getInstances } from "animejs/adapters/three"
import * as THREE from "three"

import { ACCENT_HEX, DEPTH_GAP, NODE_H, SIBLING_GAP, type Accent, type PositionedNode } from "@/lib/forest"

/**
 * Efecto de "deploy" una sola vez al montar: arranca como un bloque compacto, se despliega
 * en 3D con una pequena rotacion, y SE ORGANIZA en la posicion real del arbol (no vuelve a
 * compactarse). Es puramente decorativo — el grafo 2D interactivo (click, seleccion) sigue
 * viviendo en forest-graph.tsx; este componente nunca maneja input.
 *
 * Usa una unica THREE.InstancedMesh (no un Mesh por nodo) para escalar de pocos nodos a un
 * arbol grande sin costo extra de geometria/material por nodo, animada via el adapter de
 * Three.js de anime.js (`getInstances`, ver animejs/adapters/three).
 */
export function ForestDeployEffect({
  nodes,
  width,
  height,
  accent,
  onDone,
}: {
  nodes: PositionedNode<unknown>[]
  width: number
  height: number
  accent: Accent
  onDone: () => void
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || nodes.length === 0 || width === 0 || height === 0) {
      onDone()
      return
    }

    const fovDeg = 50
    const cameraZ = 6
    const aspect = width / height
    const visibleHeight = 2 * Math.tan((fovDeg / 2) * (Math.PI / 180)) * cameraZ
    const visibleWidth = visibleHeight * aspect

    // Pixel-space (mismo sistema que forest-graph.tsx) -> unidades locales de la escena.
    function toLocal(px: number, py: number) {
      return {
        x: (px / width - 0.5) * visibleWidth,
        y: -(py / height - 0.5) * visibleHeight,
      }
    }

    const targets = nodes.map((n) => {
      const centerPxX = n.x * SIBLING_GAP + SIBLING_GAP / 2
      const centerPxY = n.y * DEPTH_GAP + NODE_H / 2
      return toLocal(centerPxX, centerPxY)
    })

    const count = nodes.length
    const unit = Math.max(0.14, Math.min(0.42, (visibleWidth / Math.max(1, count)) * 0.55))

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(fovDeg, aspect, 0.1, 100)
    camera.position.z = cameraZ

    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true })
    renderer.setSize(width, height, false)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))

    scene.add(new THREE.AmbientLight(0xffffff, 0.55))
    const key = new THREE.PointLight(0xffffff, 6, 20, 0.5)
    key.position.set(1, 1.5, 3)
    scene.add(key)
    const rim = new THREE.DirectionalLight(0xffffff, 0.8)
    rim.position.set(-2, -1, 2)
    scene.add(rim)

    const geometry = new THREE.BoxGeometry(unit, unit * 0.62, unit * 0.62)
    const material = new THREE.MeshStandardMaterial({
      color: ACCENT_HEX[accent],
      roughness: 0.35,
      metalness: 0.15,
    })
    const mesh = new THREE.InstancedMesh(geometry, material, count)
    scene.add(mesh)

    const instances = getInstances(mesh)
    // Fase 0 (instante): bloque compacto, apretado alrededor del origen.
    instances.forEach((inst) => {
      if (!inst) return
      inst.x = (Math.random() - 0.5) * unit * 1.4
      inst.y = (Math.random() - 0.5) * unit * 1.4
      inst.z = (Math.random() - 0.5) * unit * 1.4
      inst.scale = 0
    })

    const timer = createTimer({ onUpdate: () => renderer.render(scene, camera) })

    let cancelled = false
    const staggerStep = Math.min(38, 640 / count)

    function animateAll(
      fn: (i: number) => Promise<unknown>
    ): Promise<void> {
      return Promise.all(instances.map((inst, i) => (inst ? fn(i) : Promise.resolve()))).then(
        () => undefined
      )
    }

    async function run() {
      // Fase 1 — aparece como bloque compacto (< 1s en total con la pausa de abajo).
      await animateAll(
        (i) =>
          new Promise((resolve) => {
            const inst = instances[i]!
            animate(inst, {
              scale: 1,
              duration: 220,
              delay: i * staggerStep * 0.4,
              ease: "outBack",
            }).then(() => resolve(undefined))
          })
      )
      if (cancelled) return
      await new Promise((r) => setTimeout(r, 260))
      if (cancelled) return

      // Fase 2 — despliegue 3D: se dispersan hacia afuera con una rotacion.
      await animateAll(
        (i) =>
          new Promise((resolve) => {
            const inst = instances[i]!
            const scatter = {
              x: (Math.random() - 0.5) * visibleWidth * 0.7,
              y: (Math.random() - 0.5) * visibleHeight * 0.6,
              z: (Math.random() - 0.5) * 2.4 - 0.6,
            }
            animate(inst, {
              x: scatter.x,
              y: scatter.y,
              z: scatter.z,
              rotateX: 360 + Math.random() * 180,
              rotateY: 360 + Math.random() * 180,
              duration: 520,
              delay: i * staggerStep,
              ease: "inOutQuad",
            }).then(() => resolve(undefined))
          })
      )
      if (cancelled) return

      // Fase 3 — se organiza en la estructura real del arbol (no vuelve a compactarse).
      await animateAll(
        (i) =>
          new Promise((resolve) => {
            const inst = instances[i]!
            const t = targets[i]
            animate(inst, {
              x: t.x,
              y: t.y,
              z: 0,
              rotateX: 0,
              rotateY: 0,
              duration: 620,
              delay: i * staggerStep,
              ease: "inOutExpo",
            }).then(() => resolve(undefined))
          })
      )
      if (!cancelled) onDone()
    }

    run()

    return () => {
      cancelled = true
      timer.pause()
      geometry.dispose()
      material.dispose()
      renderer.dispose()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, width, height, accent])

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none absolute inset-0"
      width={width}
      height={height}
      aria-hidden
    />
  )
}
