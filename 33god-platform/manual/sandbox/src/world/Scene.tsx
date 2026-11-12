import { Environment, Lightformer, OrbitControls } from '@react-three/drei'
import { Canvas, useFrame } from '@react-three/fiber'
import { Bloom, EffectComposer, Vignette } from '@react-three/postprocessing'
import { OVERVIEW } from '../content'
import { step } from '../sim/sim'
import { useWorld } from '../sim/store'
import { Belt } from './Belt'
import { Bulbs, CameraRig, StationLabels } from './Bulbs'
import { Moving } from './Moving'
import { Props } from './Props'

function Sim() {
  useFrame((_, dt) => step(dt))
  return null
}

export function Scene({ fx }: { fx: boolean }) {
  return (
    <Canvas
      shadows
      dpr={[1, 2]}
      camera={{ position: OVERVIEW.pos, fov: 42, near: 0.1, far: 300 }}
      onPointerMissed={() => useWorld.setState({ inspect: null })}
    >
      <color attach="background" args={['#EDE4D3']} />
      <fog attach="fog" args={['#EDE4D3', 55, 120]} />
      <hemisphereLight args={['#FFF8EE', '#B9A98F', 0.9]} />
      <directionalLight
        position={[18, 30, 16]}
        intensity={1.7}
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-32}
        shadow-camera-right={32}
        shadow-camera-top={24}
        shadow-camera-bottom={-24}
        shadow-bias={-0.0004}
      />
      {/* local studio lighting: no network fetch for an HDR */}
      <Environment resolution={256} frames={1}>
        <Lightformer intensity={1.2} position={[0, 10, 10]} scale={[30, 8, 1]} color="#FFF3DD" />
        <Lightformer intensity={0.6} position={[-20, 6, -10]} rotation-y={Math.PI / 2} scale={[20, 6, 1]} color="#DCEBFF" />
        <Lightformer intensity={0.5} position={[20, 6, -10]} rotation-y={-Math.PI / 2} scale={[20, 6, 1]} color="#FFE2C6" />
      </Environment>

      <Props />
      <Belt />
      <Moving />
      <Bulbs />
      <StationLabels />

      <Sim />
      <CameraRig />
      <OrbitControls
        makeDefault
        target={OVERVIEW.target}
        enableDamping
        dampingFactor={0.08}
        minDistance={4}
        maxDistance={70}
        maxPolarAngle={Math.PI / 2.08}
      />
      {fx && (
        <EffectComposer multisampling={4}>
          <Bloom mipmapBlur intensity={0.7} luminanceThreshold={1} luminanceSmoothing={0.2} />
          <Vignette offset={0.25} darkness={0.45} />
        </EffectComposer>
      )}
    </Canvas>
  )
}
